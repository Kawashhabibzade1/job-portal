import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models import ApplicationCreate, JobPosting, JobSearchResponse, ProfileUpdate, UploadedDocument, UserProfile
from app import env as app_env
from app.services import artifact_service, document_builder, document_service, profile_service
from app.services.agent_orchestrator import classify_intent
from app.services.ai_search import smart_filter_jobs, translated_query_variants
from app.services.matching_service import rank_jobs


class CareerAssistantTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        profile_service.PROFILE_STORE.path = root / "profile.json"
        document_service.DOCUMENT_STORE.path = root / "documents.json"
        document_service.UPLOAD_DIR = root / "uploads"
        artifact_service.GENERATED_STORE.path = root / "generated_files.json"
        artifact_service.GENERATED_DIR = root / "generated"
        artifact_service.PACKAGE_DIR = root / "packages"
        document_builder.COVER_LETTER_STORE.path = root / "cover_letters.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_intent_classification(self):
        self.assertEqual(classify_intent("Find me Python jobs"), "search")
        self.assertEqual(classify_intent("Check my chances for this job"), "match")
        self.assertEqual(classify_intent("Can I apply for this job?"), "match")
        self.assertEqual(classify_intent("Write my cover letter"), "cover_letter")
        self.assertEqual(classify_intent("Show applications"), "tracker")
        self.assertEqual(
            classify_intent("what fields can i work according to my skills and experience"),
            "career_advice",
        )

    def test_profile_update_persists(self):
        profile = profile_service.update_profile(
            ProfileUpdate(skills=["Python", "React"], target_roles=["Developer"])
        )

        self.assertEqual(profile.skills, ["Python", "React"])
        self.assertEqual(profile_service.get_profile().target_roles, ["Developer"])

    def test_document_profile_inference(self):
        document = UploadedDocument(
            id="doc-1",
            filename="cv.txt",
            content_type="text/plain",
            document_type="cv",
            text="Python React English research assistant curriculum vitae",
            status="processed",
            created_at="2026-01-01T00:00:00Z",
        )

        profile = profile_service.infer_profile_from_document(document)

        self.assertIn("Python", profile.skills)
        self.assertIn("English", profile.languages)
        self.assertTrue(profile.cv_summary)

    def test_matching_scores_obvious_fit_higher(self):
        profile = UserProfile(skills=["Python", "React"], target_roles=["Developer"])
        strong = JobPosting(
            title="Python React Developer",
            company="Acme",
            source="Test",
            description="Build Python and React software.",
        )
        weak = JobPosting(
            title="Retail Assistant",
            company="Shop",
            source="Test",
            description="Customer support and store operations.",
        )

        matches = rank_jobs([weak, strong], profile)

        self.assertEqual(matches[0].job.title, "Python React Developer")
        self.assertGreater(matches[0].score, matches[1].score)

    @patch("app.services.ai_search.LlmAdapter.available_providers", return_value=[])
    def test_translated_query_variants_include_local_language(self, _mocked_providers):
        variants = translated_query_variants("embryologist", ["de", "tr"])

        self.assertIn("embryologist", variants)
        self.assertIn("embryologe", variants)
        self.assertIn("embriyolog", variants)

    @patch("app.services.ai_search.LlmAdapter.available_providers", return_value=[])
    def test_smart_filter_removes_obvious_irrelevant_jobs(self, _mocked_providers):
        relevant = JobPosting(
            title="Clinical Embryologist",
            company="Fertility Clinic",
            source="Test",
            description="IVF laboratory and embryo culture role.",
        )
        irrelevant = JobPosting(
            title="Retail Sales Assistant",
            company="Shop",
            source="Test",
            description="Customer service and warehouse duties.",
        )

        result = smart_filter_jobs([irrelevant, relevant], "embryologist", ["gb"])

        self.assertEqual([job.title for job in result.jobs], ["Clinical Embryologist"])
        self.assertEqual(result.provider, "local")

    def test_apply_creates_prepared_record_not_submission(self):
        job = JobPosting(title="Developer", company="Acme", source="Test")
        application = profile_service.create_application(
            ApplicationCreate(job=job, status="prepared", notes="Needs confirmation.")
        )

        self.assertEqual(application.status, "prepared")
        self.assertEqual(len(profile_service.list_applications()), 1)


class CareerAssistantApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        profile_service.PROFILE_STORE.path = root / "profile.json"
        document_service.DOCUMENT_STORE.path = root / "documents.json"
        document_service.UPLOAD_DIR = root / "uploads"
        artifact_service.GENERATED_STORE.path = root / "generated_files.json"
        artifact_service.GENERATED_DIR = root / "generated"
        artifact_service.PACKAGE_DIR = root / "packages"
        document_builder.COVER_LETTER_STORE.path = root / "cover_letters.json"
        self.original_env_file = app_env.LOCAL_ENV_FILE
        app_env.LOCAL_ENV_FILE = root / ".env"
        self.client = TestClient(app)

    def tearDown(self):
        app_env.LOCAL_ENV_FILE = self.original_env_file
        self.temp_dir.cleanup()

    def test_upload_txt_document(self):
        response = self.client.post(
            "/api/documents/upload",
            files={"file": ("cv.txt", b"Python English CV", "text/plain")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "processed")
        self.assertIn("Python", response.json()["text"])

    def test_match_endpoint_accepts_job_shape(self):
        response = self.client.post(
            "/api/jobs/match",
            json={
                "jobs": [
                    {
                        "title": "Python Developer",
                        "company": "Acme",
                        "source": "Test",
                        "description": "Python APIs",
                    }
                ],
                "cv_text": "Python developer",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_chat_can_call_existing_search(self):
        fake_job = JobPosting(title="Python Developer", company="Acme", source="Test")

        with (
            patch("app.main.search_jobs") as mocked_search,
            patch("app.services.agent_orchestrator.LlmAdapter.available_providers", return_value=[]),
        ):
            mocked_search.return_value = JobSearchResponse(
                query="python",
                location="",
                country="all",
                count=1,
                jobs=[fake_job],
                sources={"test": 1},
                errors={},
            )
            response = self.client.post("/api/chat", json={"message": "Find Python jobs"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["actions"][0]["type"], "job_search")

    def test_chat_search_uses_profile_terms_for_skill_search(self):
        profile_service.update_profile(
            ProfileUpdate(skills=["Embryology", "IVF"], target_roles=["Embryologist"])
        )
        fake_job = JobPosting(title="Embryologist", company="Clinic", source="Test")

        with (
            patch("app.main.search_jobs") as mocked_search,
            patch("app.services.agent_orchestrator.LlmAdapter.available_providers", return_value=[]),
        ):
            mocked_search.return_value = JobSearchResponse(
                query="Embryologist Embryology IVF",
                location="",
                country="all",
                count=1,
                jobs=[fake_job],
                sources={"test": 1},
                errors={},
            )
            response = self.client.post(
                "/api/chat",
                json={"message": "Find jobs according to my skills"},
            )

        self.assertEqual(response.status_code, 200)
        mocked_search.assert_called_once()
        self.assertIn("Embryologist", mocked_search.call_args.kwargs["query"])
        self.assertEqual(response.json()["actions"][0]["type"], "job_search")

    def test_chat_cover_letter_auto_searches_when_no_job_selected(self):
        profile_service.update_profile(ProfileUpdate(target_roles=["Embryologist"]))
        fake_job = JobPosting(title="Embryologist", company="Clinic", source="Test")

        with (
            patch("app.main.search_jobs") as mocked_search,
            patch("app.services.agent_orchestrator.LlmAdapter.available_providers", return_value=[]),
        ):
            mocked_search.return_value = JobSearchResponse(
                query="Embryologist",
                location="",
                country="all",
                count=1,
                jobs=[fake_job],
                sources={"test": 1},
                errors={},
            )
            response = self.client.post(
                "/api/chat",
                json={"message": "Make a cover letter according to my skills"},
            )

        self.assertEqual(response.status_code, 200)
        action_types = [action["type"] for action in response.json()["actions"]]
        self.assertIn("job_search", action_types)
        self.assertIn("cover_letter", action_types)

    def test_chat_stream_returns_live_events(self):
        with self.client.stream(
            "POST",
            "/api/chat/stream",
            json={"message": "Show applications"},
        ) as response:
            body = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn('"event": "conversation"', body)
        self.assertIn('"event": "status"', body)
        self.assertIn('"event": "chunk"', body)
        self.assertIn('"event": "response"', body)

    def test_llm_status_reports_configured_providers(self):
        with patch.dict(
            "os.environ",
            {"GROK_API_KEY": "test-grok-key", "GEMINI_API_KEY": "test-gemini-key"},
            clear=False,
        ):
            response = self.client.get("/api/llm/status")

        self.assertEqual(response.status_code, 200)
        self.assertIn("grok", response.json()["available"])
        self.assertIn("gemini", response.json()["available"])

    def test_llm_settings_store_keys_without_echoing_them(self):
        with patch.dict("os.environ", {}, clear=False):
            response = self.client.put(
                "/api/llm/settings",
                json={
                    "GEMINI_API_KEY": "test-gemini-key",
                    "GROK_API_KEY": "test-grok-key",
                    "LLM_PROVIDER": "gemini",
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("gemini", data["available"])
        self.assertIn("grok", data["available"])
        self.assertNotIn("test-gemini-key", response.text)
        self.assertIn("GEMINI_API_KEY=test-gemini-key", app_env.LOCAL_ENV_FILE.read_text())

    def test_general_chat_uses_configured_llm_adapter(self):
        with (
            patch.dict("os.environ", {"GEMINI_API_KEY": "test-gemini-key"}, clear=False),
            patch(
                "app.services.llm_adapter.LlmAdapter.ask_default",
                return_value=("Focus on embryology and IVF lab roles.", "gemini"),
            ) as mocked_llm,
        ):
            response = self.client.post(
                "/api/chat",
                json={"message": "Hello, what should I focus on next?"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Focus on embryology and IVF lab roles.")
        self.assertEqual(response.json()["actions"][0]["type"], "llm_response")
        mocked_llm.assert_called_once()

    def test_chat_apply_requires_confirmation(self):
        job = {
            "title": "Python Developer",
            "company": "Acme",
            "source": "Test",
        }
        response = self.client.post(
            "/api/chat",
            json={"message": "Apply for this job", "context": {"jobs": [job]}},
        )

        self.assertEqual(response.status_code, 200)
        action = response.json()["actions"][0]
        self.assertEqual(action["status"], "needs_confirmation")
        self.assertIn("will not submit", response.json()["message"].lower())

    def test_debate_endpoint_calls_grok_gemini_and_judge(self):
        job = {
            "title": "Python Developer",
            "company": "Acme",
            "source": "Test",
            "description": "Python APIs and React interfaces",
        }
        grok_answer = (
            '{"summary":"Grok sees a strong technical fit.","recommendation":"apply",'
            '"confidence":82,"strengths":["Python"],"gaps":["Cloud"]}'
        )
        gemini_answer = (
            '{"summary":"Gemini agrees but notes one gap.","recommendation":"apply",'
            '"confidence":78,"strengths":["React"],"gaps":["Cloud"]}'
        )
        judge_answer = (
            '{"summary":"Apply, with a note about cloud learning.","recommendation":"apply",'
            '"confidence":84,"strengths":["Python","React"],"gaps":["Cloud"]}'
        )

        with (
            patch("app.services.llm_adapter.LlmAdapter.ask_grok", return_value=grok_answer),
            patch("app.services.llm_adapter.LlmAdapter.ask_gemini", side_effect=[gemini_answer, judge_answer]),
        ):
            response = self.client.post(
                "/api/agents/debate",
                json={"job": job, "question": "Can I apply?", "cv_text": "Python React"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["grok"]["recommendation"], "apply")
        self.assertEqual(data["gemini"]["recommendation"], "apply")
        self.assertEqual(data["judge"]["recommendation"], "apply")

    def test_chat_can_i_apply_returns_agent_debate(self):
        job = {
            "title": "Python Developer",
            "company": "Acme",
            "source": "Test",
            "description": "Python APIs and React interfaces",
        }
        answer = (
            '{"summary":"Good fit.","recommendation":"apply","confidence":80,'
            '"strengths":["Python"],"gaps":[]}'
        )

        with (
            patch("app.services.llm_adapter.LlmAdapter.ask_grok", return_value=answer),
            patch("app.services.llm_adapter.LlmAdapter.ask_gemini", side_effect=[answer, answer]),
        ):
            response = self.client.post(
                "/api/chat",
                json={"message": "Can I apply for this job?", "context": {"jobs": [job]}},
            )

        self.assertEqual(response.status_code, 200)
        action_types = [action["type"] for action in response.json()["actions"]]
        self.assertIn("agent_debate", action_types)

    def test_chat_answers_career_field_question(self):
        profile_service.update_profile(
            ProfileUpdate(
                skills=["Laboratory", "Ivf", "Embryology", "Research"],
                languages=["English", "Deutsch"],
                target_roles=["Embryologist"],
            )
        )

        response = self.client.post(
            "/api/chat",
            json={
                "message": (
                    "so what do you think about my field related jobs in which fields "
                    "i can work according to my skills and experience"
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["actions"][0]["type"], "career_advice")
        self.assertIn("embryology", data["message"].lower())

    def test_export_cover_letter_txt_and_package(self):
        job = {"title": "Embryologist", "company": "Clinic", "source": "Test"}
        letter = self.client.post(
            "/api/documents/cover-letter",
            json={"job": job, "language": "en"},
        )
        self.assertEqual(letter.status_code, 200)

        export = self.client.post(
            "/api/documents/export-cover-letter",
            json={
                "format": "txt",
                "cover_letter_id": letter.json()["id"],
                "filename": "test-cover-letter",
            },
        )
        self.assertEqual(export.status_code, 200)
        self.assertTrue(Path(export.json()["path"]).exists())

        package = self.client.post(
            "/api/documents/application-package",
            json={
                "application_name": "Clinic Embryologist",
                "job": job,
                "cover_letter_id": letter.json()["id"],
            },
        )
        self.assertEqual(package.status_code, 200)
        self.assertEqual(len(package.json()["files"]), 4)

    def test_document_update_and_pdf_organize(self):
        upload = self.client.post(
            "/api/documents/upload",
            files={"file": ("cv.txt", b"Original CV text", "text/plain")},
        )
        self.assertEqual(upload.status_code, 200)
        updated = self.client.patch(
            f"/api/documents/{upload.json()['id']}",
            json={"document_type": "certificate", "text": "Edited certificate text"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["document_type"], "certificate")

        exported = self.client.post(
            "/api/documents/export-cover-letter",
            json={"format": "pdf", "text": "One page PDF", "filename": "organize-source"},
        )
        self.assertEqual(exported.status_code, 200)
        organized = self.client.post(
            "/api/pdf/organize",
            json={
                "generated_file_id": exported.json()["id"],
                "filename": "organized-output",
                "page_order": [0],
            },
        )
        self.assertEqual(organized.status_code, 200)
        self.assertTrue(Path(organized.json()["file"]["path"]).exists())

    def test_cv_interview_feedback_roadmap_and_apply_automation(self):
        job = {
            "title": "Embryologist",
            "company": "Clinic",
            "source": "Test",
            "apply_url": "https://example.com/apply",
            "description": "IVF laboratory and quality control",
        }

        improve = self.client.post("/api/cv/improve", json={"target_role": "Embryologist"})
        self.assertEqual(improve.status_code, 200)
        self.assertIn("improved_text", improve.json())

        interview = self.client.post("/api/interview/prepare", json={"role": "Embryologist"})
        self.assertEqual(interview.status_code, 200)
        self.assertTrue(interview.json()["technical_questions"])

        feedback = self.client.post(
            "/api/feedback/rejection",
            json={"rejection_text": "We selected candidates with more experience."},
        )
        self.assertEqual(feedback.status_code, 200)
        self.assertTrue(feedback.json()["improvements"])

        roadmap = self.client.post("/api/roadmap/skills", json={"target_role": "Embryologist"})
        self.assertEqual(roadmap.status_code, 200)
        self.assertTrue(roadmap.json()["plan"])

        apply = self.client.post(
            "/api/apply/automation",
            json={"job": job, "confirm_submit": False},
        )
        self.assertEqual(apply.status_code, 200)
        self.assertEqual(apply.json()["status"], "needs_confirmation")


if __name__ == "__main__":
    unittest.main()
