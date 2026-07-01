from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.models import (
    ApplicationPackageRequest,
    ApplicationPackageResponse,
    ExportRequest,
    GeneratedFile,
    PdfMergeRequest,
    PdfOperationResponse,
    PdfOrganizeRequest,
    UserProfile,
)
from app.services.document_builder import COVER_LETTER_STORE
from app.services.document_service import UPLOAD_DIR, get_document
from app.services.serialization import model_dump
from app.services.storage import DATA_DIR, JsonStore


GENERATED_STORE = JsonStore("generated_files.json", [])
GENERATED_DIR = DATA_DIR / "generated"
PACKAGE_DIR = DATA_DIR / "packages"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_name(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_", " "} else "_" for char in value)
    return "_".join(cleaned.split()) or "Application"


def list_generated_files() -> list[GeneratedFile]:
    return [GeneratedFile(**item) for item in GENERATED_STORE.read()]


def get_generated_file(file_id: str) -> GeneratedFile | None:
    for file in list_generated_files():
        if file.id == file_id:
            return file
    return None


def _remember_file(path: Path, mime_type: str, kind: str) -> GeneratedFile:
    file = GeneratedFile(
        id=str(uuid4()),
        filename=path.name,
        path=str(path),
        mime_type=mime_type,
        kind=kind,
        created_at=_now(),
    )
    files = [model_dump(item) for item in list_generated_files()]
    files.insert(0, model_dump(file))
    GENERATED_STORE.write(files)
    return file


def _cover_letter_text(cover_letter_id: str | None, fallback: str) -> str:
    if cover_letter_id:
        for item in COVER_LETTER_STORE.read():
            if item.get("id") == cover_letter_id:
                return item.get("text", "")
    return fallback


def export_cover_letter(payload: ExportRequest) -> GeneratedFile:
    text = _cover_letter_text(payload.cover_letter_id, payload.text)
    if not text.strip():
        text = "Cover letter draft is empty."
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    stem = _safe_name(payload.filename)
    if payload.format == "txt":
        path = GENERATED_DIR / f"{stem}.txt"
        path.write_text(text, encoding="utf-8")
        return _remember_file(path, "text/plain", "cover_letter")
    if payload.format == "docx":
        return _write_docx(GENERATED_DIR / f"{stem}.docx", text, "cover_letter")
    return _write_pdf(GENERATED_DIR / f"{stem}.pdf", text, "cover_letter")


def build_application_package(
    payload: ApplicationPackageRequest,
    profile: UserProfile,
) -> ApplicationPackageResponse:
    date = datetime.now().strftime("%Y-%m-%d")
    folder = PACKAGE_DIR / f"{_safe_name(payload.application_name)}_{date}"
    folder.mkdir(parents=True, exist_ok=True)

    files: list[GeneratedFile] = []
    cv_text = _document_text(payload.cv_document_id) or profile.cv_summary or "CV text is not available."
    files.append(_write_pdf(folder / "CV.pdf", cv_text, "package_cv"))

    cover_text = _cover_letter_text(payload.cover_letter_id, "")
    if not cover_text and payload.job:
        cover_text = f"Cover letter for {payload.job.title} at {payload.job.company or 'the company'}."
    files.append(_write_pdf(folder / "CoverLetter.pdf", cover_text or "Cover letter is not available.", "package_cover_letter"))

    certificate_texts = [
        _document_text(document_id)
        for document_id in payload.certificate_document_ids
        if _document_text(document_id)
    ]
    files.append(
        _write_pdf(
            folder / "Certificates.pdf",
            "\n\n".join(certificate_texts) or "No certificates were selected.",
            "package_certificates",
        )
    )

    summary = _package_summary(payload, profile)
    summary_path = folder / "Summary.txt"
    summary_path.write_text(summary, encoding="utf-8")
    files.append(_remember_file(summary_path, "text/plain", "package_summary"))

    return ApplicationPackageResponse(folder=str(folder), files=files, summary=summary)


def merge_pdfs(payload: PdfMergeRequest) -> PdfOperationResponse:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise RuntimeError("Install pypdf to merge PDFs.") from exc

    writer = PdfWriter()
    for path in _pdf_paths(payload):
        reader = PdfReader(str(path))
        for page in reader.pages:
            writer.add_page(page)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    path = GENERATED_DIR / f"{_safe_name(payload.filename)}.pdf"
    with path.open("wb") as file:
        writer.write(file)
    return PdfOperationResponse(file=_remember_file(path, "application/pdf", "merged_pdf"))


def organize_pdf(payload: PdfOrganizeRequest) -> PdfOperationResponse:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise RuntimeError("Install pypdf to organize PDFs.") from exc

    source = _source_pdf_path(payload.document_id, payload.generated_file_id)
    if not source:
        raise RuntimeError("No source PDF was found.")
    reader = PdfReader(str(source))
    writer = PdfWriter()
    deleted = set(payload.delete_pages)
    order = payload.page_order or list(range(len(reader.pages)))
    for page_index in order:
        if page_index in deleted or page_index < 0 or page_index >= len(reader.pages):
            continue
        page = reader.pages[page_index]
        rotation = payload.rotate_pages.get(page_index) or payload.rotate_pages.get(str(page_index))
        if rotation:
            page.rotate(rotation)
        writer.add_page(page)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    path = GENERATED_DIR / f"{_safe_name(payload.filename)}.pdf"
    with path.open("wb") as file:
        writer.write(file)
    return PdfOperationResponse(file=_remember_file(path, "application/pdf", "organized_pdf"))


def _pdf_paths(payload: PdfMergeRequest) -> list[Path]:
    paths: list[Path] = []
    for document_id in payload.document_ids:
        document = get_document(document_id)
        path = _upload_path(document_id, document.filename if document else "")
        if path and path.suffix.lower() == ".pdf":
            paths.append(path)
    for file_id in payload.generated_file_ids:
        generated = get_generated_file(file_id)
        if generated and generated.mime_type == "application/pdf":
            paths.append(Path(generated.path))
    return paths


def _source_pdf_path(document_id: str | None, generated_file_id: str | None) -> Path | None:
    if document_id:
        document = get_document(document_id)
        path = _upload_path(document_id, document.filename if document else "")
        if path and path.suffix.lower() == ".pdf":
            return path
    if generated_file_id:
        generated = get_generated_file(generated_file_id)
        if generated and generated.mime_type == "application/pdf":
            return Path(generated.path)
    return None


def _document_text(document_id: str | None) -> str:
    if not document_id:
        return ""
    document = get_document(document_id)
    return document.text if document else ""


def _upload_path(document_id: str, filename: str) -> Path | None:
    exact = UPLOAD_DIR / f"{document_id}-{filename}"
    if exact.exists():
        return exact
    matches = list(UPLOAD_DIR.glob(f"{document_id}-*"))
    return matches[0] if matches else None


def _write_pdf(path: Path, text: str, kind: str) -> GeneratedFile:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError("Install reportlab to export PDFs.") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    x = 54
    y = height - 54
    line_height = 14
    for paragraph in text.splitlines() or [""]:
        lines = _wrap_line(paragraph, 95) or [""]
        for line in lines:
            if y < 54:
                pdf.showPage()
                y = height - 54
            pdf.drawString(x, y, line)
            y -= line_height
        y -= 6
    pdf.save()
    return _remember_file(path, "application/pdf", kind)


def _write_docx(path: Path, text: str, kind: str) -> GeneratedFile:
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError("Install python-docx to export DOCX.") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    for paragraph in text.splitlines() or [""]:
        document.add_paragraph(paragraph)
    document.save(str(path))
    return _remember_file(path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", kind)


def _wrap_line(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        next_line = f"{current} {word}".strip()
        if len(next_line) > width and current:
            lines.append(current)
            current = word
        else:
            current = next_line
    if current:
        lines.append(current)
    return lines


def _package_summary(payload: ApplicationPackageRequest, profile: UserProfile) -> str:
    job = payload.job
    return "\n".join(
        [
            f"Application: {payload.application_name}",
            f"Job: {job.title if job else 'Not specified'}",
            f"Company: {job.company if job and job.company else 'Not specified'}",
            f"Generated: {_now()}",
            "",
            f"Skills: {', '.join(profile.skills)}",
            f"Languages: {', '.join(profile.languages)}",
            f"Target roles: {', '.join(profile.target_roles)}",
        ]
    )
