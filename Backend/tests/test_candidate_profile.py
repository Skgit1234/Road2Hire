import asyncio
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import configure_mappers, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers, UploadFile

from Core.database import Base
from Core.security import ALGORITHM, SECRET_KEY
from Models import CandidateProfile, Resume, User
from Schemas.candidate_profile import CandidateProfileResponse
from Api import profile as profile_api
from Api import resume as resume_api
from Api import skill_gaps as skill_gap_api
from AI.Skill_Extraction.skill_extractor import extract_skills


class CandidateProfileApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_mappers()

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = User(
            name="Candidate",
            email="candidate@example.test",
            password_hash="hash",
        )
        self.other_user = User(
            name="Other Candidate",
            email="other@example.test",
            password_hash="hash",
        )
        self.db.add_all([self.user, self.other_user])
        self.db.commit()
        self.temp_directory = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.upload_directory = Path(self.temp_directory.name)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        self.temp_directory.cleanup()

    def _save_upload(self, contents):
        file_path = self.upload_directory / "uploaded.pdf"
        file_path.write_bytes(contents)
        return file_path.name, str(file_path)

    def _upload(self, user_id):
        return asyncio.run(
            resume_api.upload_resume(
                user_id=user_id,
                file=UploadFile(
                    file=BytesIO(b"%PDF-test"),
                    filename="resume.pdf",
                    headers=Headers({"content-type": "application/pdf"}),
                ),
                db=self.db,
                user=self.user,
            )
        )

    def test_upload_analysis_reprocessing_and_ownership(self):
        with patch.object(resume_api, "save_resume_file", self._save_upload):
            upload = self._upload(self.user.id)
            resume_id = upload["resume"].id

            with self.assertRaises(HTTPException) as error:
                self._upload(self.other_user.id)
            self.assertEqual(error.exception.status_code, 403)

        extracted_skills = [
            {
                "skill": "Python",
                "source_sections": ["skills"],
                "occurrences": [
                    {
                        "section": "skills",
                        "text": "Python",
                        "start": 0,
                        "end": 6,
                    }
                ],
            }
        ]
        sections = {
            "education": "BSc Computer Science\nUniversity A",
            "experience": "Developer at Company B",
            "projects": "Resume Analyzer",
            "certifications": "Certificate C",
            "skills": "Python",
        }
        process_result = {
            "extraction_status": "completed",
            "pipeline_version": "test",
            "page_count": 1,
            "sections": sections,
            "detected_section_names": list(sections),
        }
        with (
            patch.object(resume_api, "process_resume", return_value=process_result),
            patch.object(
                resume_api,
                "extract_skills",
                return_value={
                    "skills": extracted_skills,
                    "skill_count": 1,
                    "extraction_method": "test",
                },
            ),
        ):
            result = resume_api.analyze_resume(
                resume_id,
                db=self.db,
                user=self.user,
            )

        profile = self.db.query(CandidateProfile).filter_by(
            user_id=self.user.id
        ).one()
        profile_id = profile.id
        self.assertEqual(result["status"], "completed")
        self.assertEqual(profile.resume_id, resume_id)
        self.assertEqual(profile.skills, extracted_skills)
        self.assertEqual(
            profile.education,
            ["BSc Computer Science", "University A"],
        )
        self.assertEqual(profile.experience, ["Developer at Company B"])
        self.assertEqual(profile.projects, ["Resume Analyzer"])
        self.assertEqual(profile.certifications, ["Certificate C"])
        self.assertEqual(
            CandidateProfileResponse.model_validate(profile).resume_id,
            resume_id,
        )

        next_resume = Resume(
            user_id=self.user.id,
            original_name="next.pdf",
            stored_name="next-test-resume",
            file_path=str(self.upload_directory / "uploaded.pdf"),
        )
        self.db.add(next_resume)
        self.db.commit()
        next_result = {
            **process_result,
            "sections": {"projects": "Updated project"},
            "detected_section_names": ["projects"],
        }
        with (
            patch.object(resume_api, "process_resume", return_value=next_result),
            patch.object(
                resume_api,
                "extract_skills",
                return_value={
                    "skills": [],
                    "skill_count": 0,
                    "extraction_method": "test",
                },
            ),
        ):
            resume_api.analyze_resume(
                next_resume.id,
                db=self.db,
                user=self.user,
            )

        updated_profile = self.db.query(CandidateProfile).filter_by(
            user_id=self.user.id
        ).one()
        self.assertEqual(updated_profile.id, profile_id)
        self.assertEqual(updated_profile.resume_id, next_resume.id)
        self.assertEqual(updated_profile.projects, ["Updated project"])
        self.assertEqual(updated_profile.education, [])

        with self.assertRaises(HTTPException) as error:
            resume_api.analyze_resume(
                resume_id,
                db=self.db,
                user=self.other_user,
            )
        self.assertEqual(error.exception.status_code, 404)

        self.assertEqual(
            profile_api.get_candidate_profile(
                user=self.user,
                db=self.db,
            ).id,
            profile_id,
        )
        with self.assertRaises(HTTPException) as error:
            profile_api.get_candidate_profile(
                user=self.other_user,
                db=self.db,
            )
        self.assertEqual(error.exception.status_code, 404)

    def test_jwt_existing_profile_and_skill_gap_apis(self):
        token = jwt.encode(
            {"sub": self.user.email},
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        authenticated_user = profile_api.get_current_user(
            HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=token,
            ),
            db=self.db,
        )
        self.assertEqual(authenticated_user.id, self.user.id)

        with self.assertRaises(HTTPException) as error:
            profile_api.get_current_user(
                HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials="invalid-token",
                ),
                db=self.db,
            )
        self.assertEqual(error.exception.status_code, 401)

        self.assertEqual(profile_api.get_profile(user=self.user).id, self.user.id)
        profile_api.update_profile(
            profile_api.ProfileUpdate(name="Updated Candidate"),
            user=self.user,
            db=self.db,
        )
        self.assertEqual(self.user.name, "Updated Candidate")

        resume_path = self.upload_directory / "skill-gap.pdf"
        resume_path.write_bytes(b"%PDF-test")
        resume = Resume(
            user_id=self.user.id,
            original_name="skill-gap.pdf",
            stored_name="skill-gap-test",
            file_path=str(resume_path),
        )
        self.db.add(resume)
        self.db.commit()

        skills = extract_skills(
            {"sections": {"skills": "Python and React"}},
            vocabulary=["Python", "React"],
        )
        self.assertEqual(
            {item["skill"] for item in skills["skills"]},
            {"Python", "React"},
        )

        with (
            patch.object(
                skill_gap_api,
                "process_resume",
                return_value={
                    "extraction_status": "completed",
                    "sections": {"skills": "Python"},
                },
            ),
            patch.object(
                skill_gap_api,
                "extract_skills",
                return_value={"skills": [{"skill": "Python"}]},
            ),
        ):
            analysis = skill_gap_api.get_skill_gaps(
                resume_id=resume.id,
                target_role="Backend Developer",
                required_skills=["Python", "SQL"],
                current_user=self.user,
                db=self.db,
            )
            cached = skill_gap_api.get_skill_gaps(
                resume_id=resume.id,
                target_role="Backend Developer",
                required_skills=["Python", "SQL"],
                current_user=self.user,
                db=self.db,
            )

        history = skill_gap_api.get_skill_gap_history(
            limit=20,
            offset=0,
            current_user=self.user,
            db=self.db,
        )
        self.assertFalse(analysis["cached"])
        self.assertTrue(cached["cached"])
        self.assertEqual(history["total"], 1)

    def test_candidate_and_existing_profile_routes_are_registered(self):
        from Main import app

        paths = app.openapi()["paths"]
        self.assertIn("/profile/candidate", paths)
        self.assertIn("get", paths["/profile/candidate"])
        self.assertIn("/profile", paths)
        self.assertIn("get", paths["/profile"])
        self.assertIn("patch", paths["/profile"])
        self.assertTrue(paths["/profile/candidate"]["get"].get("security"))


if __name__ == "__main__":
    unittest.main()
