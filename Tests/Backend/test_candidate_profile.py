from Core.database import Base
from Models import CandidateProfile


def test_candidate_profile_model_is_registered():
    assert CandidateProfile.__tablename__ == "candidate_profiles"
    assert "candidate_profiles" in Base.metadata.tables


def test_candidate_profile_has_expected_columns():
    expected_columns = {
        "id",
        "user_id",
        "resume_id",
        "skills",
        "education",
        "experience",
        "projects",
        "certifications",
        "updated_at",
    }
    actual_columns = set(CandidateProfile.__table__.columns.keys())
    assert expected_columns.issubset(actual_columns)
