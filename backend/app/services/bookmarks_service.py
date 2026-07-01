from datetime import datetime, timezone
from uuid import uuid4

from app.models import BookmarkedJob, JobPosting
from app.services.storage import JsonStore
from app.services.serialization import model_dump


BOOKMARKS_STORE = JsonStore("bookmarks.json", [])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_bookmarks() -> list[BookmarkedJob]:
    return [BookmarkedJob(**item) for item in BOOKMARKS_STORE.read()]


def add_bookmark(job: JobPosting, note: str = "") -> BookmarkedJob:
    bookmarks = list_bookmarks()
    # Avoid duplicates by apply_url or title+company
    for bm in bookmarks:
        if bm.job.apply_url and bm.job.apply_url == job.apply_url:
            return bm
        if bm.job.title == job.title and bm.job.company == job.company:
            return bm
    bookmark = BookmarkedJob(
        id=str(uuid4()),
        job=job,
        note=note,
        created_at=_now_iso(),
    )
    bookmarks.insert(0, bookmark)
    BOOKMARKS_STORE.write([model_dump(bm) for bm in bookmarks])
    return bookmark


def remove_bookmark(bookmark_id: str) -> bool:
    bookmarks = list_bookmarks()
    filtered = [bm for bm in bookmarks if bm.id != bookmark_id]
    if len(filtered) == len(bookmarks):
        return False
    BOOKMARKS_STORE.write([model_dump(bm) for bm in filtered])
    return True
