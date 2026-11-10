from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException

from Api import profile as profile_api
from Api import resume as resume_api
from Models import CandidateProfile, Resume, User


def _create_user(db, email="candidate@example.test"):
    user = User(name="Candidate", email=email, password_hash="unused")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_authentication_accepts_valid_token_and_rejects_invalid_token(
    api_client,
    sqlite_session,
    auth_headers,
):
    user = _create_user(sqlite_session)

    response = api_client.get("/profile", headers=auth_headers(user.email))
    assert response.status_code == 200
    assert response.json()["id"] == user.id

    invalid = api_client.get(
        "/profile",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert invalid.status_code == 401

    missing = api_client.get("/profile")
    assert missing.status_code == 401


def test_profile_retrieval_and_update_are_persisted(
    api_client,
    sqlite_session,
    auth_headers,
):
    user = _create_user(sqlite_session)
    headers = auth_headers(user.email)

    updated = api_client.patch(
        "/profile",
        headers=headers,
        json={"name": "  Updated Candidate  "},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Candidate"

    retrieved = api_client.get("/profile", headers=headers)
    assert retrieved.status_code == 200
    assert retrieved.json()["name"] == "Updated Candidate"
    assert sqlite_session.get(User, user.id).name == "Updated Candidate"

    empty_update = api_client.patch("/profile", headers=headers, json={})
    assert empty_update.status_code == 400


def test_resume_upload_persists_metadata(
    api_client,
    sqlite_session,
    auth_headers,
    monkeypatch,
    tmp_path,
):
    user = _create_user(sqlite_session)
    saved_file = tmp_path / "stored-resume.pdf"

    def save_resume(contents):
        saved_file.write_bytes(contents)
        return saved_file.name, str(saved_file)

    monkeypatch.setattr(resume_api, "save_resume_file", save_resume)
    response = api_client.post(
        "/resume/upload",
        headers=auth_headers(user.email),
        data={"user_id": str(user.id)},
        files={"file": ("resume.pdf", b"%PDF-1.7 valid test content", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["resume"]["user_id"] == user.id
    assert payload["resume"]["original_name"] == "resume.pdf"
    assert sqlite_session.query(Resume).filter_by(user_id=user.id).count() == 1
    assert saved_file.read_bytes().startswith(b"%PDF-")


@pytest.mark.parametrize(
    ("filename", "content_type", "contents", "form_user_id", "expected_status"),
    [
        ("resume.txt", "application/pdf", b"%PDF-1.7", 1, 400),
        ("resume.pdf", "text/plain", b"%PDF-1.7", 1, 400),
        ("resume.pdf", "application/pdf", b"not a pdf", 1, 400),
        (
            "resume.pdf",
            "application/pdf",
            b"%PDF-" + b"x" * (resume_api.MAX_FILE_SIZE + 1),
            1,
            413,
        ),
        ("resume.pdf", "application/pdf", b"%PDF-1.7", 999, 403),
    ],
)
def test_resume_upload_validation_rejects_invalid_requests(
    api_client,
    sqlite_session,
    auth_headers,
    monkeypatch,
    filename,
    content_type,
    contents,
    form_user_id,
    expected_status,
):
    user = _create_user(sqlite_session)
    monkeypatch.setattr(
        resume_api,
        "save_resume_file",
        lambda _contents: pytest.fail("invalid upload must not be stored"),
    )

    response = api_client.post(
        "/resume/upload",
        headers=auth_headers(user.email),
        data={"user_id": str(form_user_id)},
        files={"file": (filename, contents, content_type)},
    )

    assert response.status_code == expected_status
    assert sqlite_session.query(Resume).count() == 0


def test_delete_resume_preserves_profile_and_enforces_ownership(
    api_client,
    sqlite_session,
    auth_headers,
    monkeypatch,
    tmp_path,
):
    user = _create_user(sqlite_session, "owner@example.test")
    other_user = _create_user(sqlite_session, "other@example.test")
    user_file = tmp_path / "owner-resume.pdf"
    other_file = tmp_path / "other-resume.pdf"
    user_file.write_bytes(b"%PDF-1.7 owner")
    other_file.write_bytes(b"%PDF-1.7 other")
    user_resume = Resume(
        user_id=user.id,
        original_name="owner.pdf",
        stored_name="owner.pdf",
        file_path=str(user_file),
    )
    other_resume = Resume(
        user_id=other_user.id,
        original_name="other.pdf",
        stored_name="other.pdf",
        file_path=str(other_file),
    )
    sqlite_session.add_all([user_resume, other_resume])
    sqlite_session.commit()
    user_profile = CandidateProfile(
        user_id=user.id,
        resume_id=user_resume.id,
        skills=["Python"],
        education=[],
        experience=[],
        projects=[],
        certifications=[],
    )
    other_profile = CandidateProfile(
        user_id=other_user.id,
        resume_id=other_resume.id,
        skills=["SQL"],
        education=[],
        experience=[],
        projects=[],
        certifications=[],
    )
    sqlite_session.add_all([user_profile, other_profile])
    sqlite_session.commit()

    monkeypatch.setattr(resume_api, "get_resume_file_path", Path)
    monkeypatch.setattr(
        resume_api,
        "remove_resume_file",
        lambda path: Path(path).unlink(missing_ok=True),
    )

    forbidden = api_client.delete(
        f"/resumes/{user_resume.id}",
        headers=auth_headers(other_user.email),
    )
    assert forbidden.status_code == 404
    assert sqlite_session.get(Resume, user_resume.id) is not None
    assert (
        sqlite_session.get(CandidateProfile, user_profile.id).resume_id
        == user_resume.id
    )

    deleted = api_client.delete(
        f"/resumes/{user_resume.id}",
        headers=auth_headers(user.email),
    )
    assert deleted.status_code == 200
    assert sqlite_session.get(Resume, user_resume.id) is None
    retained_profile = sqlite_session.get(CandidateProfile, user_profile.id)
    assert retained_profile is not None
    assert retained_profile.resume_id is None

    assert sqlite_session.get(Resume, other_resume.id) is not None
    assert (
        sqlite_session.get(CandidateProfile, other_profile.id).resume_id
        == other_resume.id
    )
    assert other_file.exists()


def test_candidate_profile_analysis_refreshes_latest_resume(
    fake_session,
    test_user,
    monkeypatch,
    tmp_path,
):
    resume_path = tmp_path / "resume.pdf"
    resume_path.write_bytes(b"%PDF-test")
    resume = Resume(
        id=11,
        user_id=test_user.id,
        original_name="resume.pdf",
        stored_name="resume-test",
        file_path=str(resume_path),
    )
    db = fake_session({Resume: [resume]})
    sections = {
        "education": "BSc Computer Science\nUniversity A",
        "experience": "Developer at Company B",
        "projects": "Resume Analyzer",
        "certifications": "Certificate C",
    }
    monkeypatch.setattr(
        resume_api,
        "process_resume",
        lambda _path: {
            "extraction_status": "completed",
            "pipeline_version": "test",
            "page_count": 1,
            "sections": sections,
            "detected_section_names": list(sections),
        },
    )
    monkeypatch.setattr(
        resume_api,
        "extract_skills",
        lambda _result: {
            "skills": [{"skill": "Python"}],
            "skill_count": 1,
            "extraction_method": "test",
        },
    )

    result = resume_api.analyze_resume(resume.id, db=db, user=test_user)
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == test_user.id
    ).first()

    assert result["status"] == "completed"
    assert profile.resume_id == resume.id
    assert profile.skills == [{"skill": "Python"}]
    assert profile.education == ["BSc Computer Science", "University A"]
    assert profile.experience == ["Developer at Company B"]

    next_resume = Resume(
        id=12,
        user_id=test_user.id,
        original_name="next.pdf",
        stored_name="next-test",
        file_path=str(resume_path),
    )
    db.add(next_resume)
    monkeypatch.setattr(
        resume_api,
        "process_resume",
        lambda _path: {
            "extraction_status": "completed",
            "pipeline_version": "test",
            "page_count": 1,
            "sections": {"projects": "Updated project"},
            "detected_section_names": ["projects"],
        },
    )
    resume_api.analyze_resume(next_resume.id, db=db, user=test_user)

    updated_profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == test_user.id
    ).first()
    assert updated_profile.id == profile.id
    assert updated_profile.resume_id == next_resume.id
    assert updated_profile.projects == ["Updated project"]
    assert updated_profile.education == []

    with pytest.raises(HTTPException) as error:
        resume_api.analyze_resume(
            resume.id,
            db=db,
            user=User(id=2, name="Other", email="other@example.test"),
        )
    assert error.value.status_code == 404


def test_candidate_profile_retrieval_handles_missing_profile(
    fake_session,
    test_user,
):
    profile = CandidateProfile(
        id=5,
        user_id=test_user.id,
        resume_id=11,
        skills=[],
        education=[],
        experience=[],
        projects=[],
        certifications=[],
        updated_at=datetime.now(timezone.utc),
    )
    db = fake_session({CandidateProfile: [profile]})

    assert profile_api.get_candidate_profile(user=test_user, db=db).id == profile.id

    with pytest.raises(HTTPException) as error:
        profile_api.get_candidate_profile(
            user=User(id=2, name="Other", email="other@example.test"),
            db=db,
        )
    assert error.value.status_code == 404
