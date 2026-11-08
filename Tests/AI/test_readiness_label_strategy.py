"""Unit tests for M4.3 Career Readiness Label Strategy & Schema contracts.

Validates:
- Loading and structural integrity of readiness_label_schema.json
- Exact three-class readiness taxonomy ('Not Ready', 'Developing', 'Job Ready')
- Conformance of sample annotation records
- Required independent evidence dimensions (skills, experience, projects, education)
- Verification that skill coverage scores are not conflated with readiness labels
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "AI"
    / "Dataset_Preparation"
    / "readiness_label_schema.json"
)
GUIDELINES_PATH = (
    Path(__file__).resolve().parents[2]
    / "AI"
    / "Dataset_Preparation"
    / "readiness_annotation_guidelines.md"
)


class TestReadinessLabelSchema:
    """Tests for readiness_label_schema.json specification."""

    def test_schema_file_exists_and_loads(self):
        assert SCHEMA_PATH.exists()
        with SCHEMA_PATH.open("r", encoding="utf-8") as f:
            schema = json.load(f)
        assert isinstance(schema, dict)
        assert schema.get("title") == "Road2HireCareerReadinessAnnotationRecord"

    def test_readiness_classes_exact_enumeration(self):
        with SCHEMA_PATH.open("r", encoding="utf-8") as f:
            schema = json.load(f)

        expected_classes = ["Not Ready", "Developing", "Job Ready"]
        non_null_classes = [
            c for c in schema["properties"]["readiness_label"]["enum"] if c is not None
        ]
        assert non_null_classes == expected_classes
        assert None in schema["properties"]["readiness_label"]["enum"]

    def test_evidence_sub_schema_requirements(self):
        with SCHEMA_PATH.open("r", encoding="utf-8") as f:
            schema = json.load(f)

        evidence_schema = schema["properties"]["evidence"]
        required_evidence_fields = evidence_schema["required"]

        assert "essential_skill_proficiency" in required_evidence_fields
        assert "work_experience_relevance" in required_evidence_fields
        assert "practical_application_evidence" in required_evidence_fields
        assert "education_relevance" in required_evidence_fields
        assert "key_evidence_summary" in required_evidence_fields

    def test_sample_job_ready_record_conformance(self):
        with SCHEMA_PATH.open("r", encoding="utf-8") as f:
            schema = json.load(f)

        record = {
            "annotation_id": "mr_12__software_developer__ann",
            "pair_id": "mr_12__http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1",
            "candidate_id": "mr_12",
            "candidate_source": "master_resumes",
            "target_occupation_uri": "http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1",
            "target_occupation_title": "software developer",
            "readiness_label": "Job Ready",
            "confidence": "High",
            "evidence": {
                "essential_skill_proficiency": "Proficient",
                "work_experience_relevance": "Substantial_and_Direct",
                "practical_application_evidence": "Production_or_EndToEnd_Systems",
                "education_relevance": "Directly_Aligned_Degree",
                "certifications_observed": [],
                "key_evidence_summary": "3 years direct software engineer experience with 2 full-stack projects.",
            },
            "reviewer_status": "Verified",
            "annotator_id": "expert_01",
            "annotation_timestamp": "2026-11-05T12:00:00Z",
            "annotation_notes": "Meets all criteria for autonomous software engineering contribution.",
        }

        # Check top-level required fields
        for field in schema["required"]:
            assert field in record

        # Check enum constraints
        assert record["readiness_label"] in schema["properties"]["readiness_label"]["enum"]
        assert record["confidence"] in schema["properties"]["confidence"]["enum"]
        assert record["reviewer_status"] in schema["properties"]["reviewer_status"]["enum"]

        # Check evidence enum constraints
        ev_props = schema["properties"]["evidence"]["properties"]
        assert record["evidence"]["essential_skill_proficiency"] in ev_props["essential_skill_proficiency"]["enum"]
        assert record["evidence"]["work_experience_relevance"] in ev_props["work_experience_relevance"]["enum"]
        assert record["evidence"]["practical_application_evidence"] in ev_props["practical_application_evidence"]["enum"]

    def test_sample_developing_record_conformance(self):
        with SCHEMA_PATH.open("r", encoding="utf-8") as f:
            schema = json.load(f)

        record = {
            "annotation_id": "mr_55__data_scientist__ann",
            "pair_id": "mr_55__http://data.europa.eu/esco/occupation/258e46f9-0075-4a2e-adae-1ff0477e0f30",
            "candidate_id": "mr_55",
            "candidate_source": "master_resumes",
            "target_occupation_uri": "http://data.europa.eu/esco/occupation/258e46f9-0075-4a2e-adae-1ff0477e0f30",
            "target_occupation_title": "data scientist",
            "readiness_label": "Developing",
            "confidence": "Medium",
            "evidence": {
                "essential_skill_proficiency": "Foundational",
                "work_experience_relevance": "Partial_or_Junior",
                "practical_application_evidence": "Academic_or_Demo_Projects",
                "education_relevance": "Related_Degree",
                "certifications_observed": [],
                "key_evidence_summary": "6 months junior experience with academic Python/EDA coursework.",
            },
            "reviewer_status": "Reviewed",
            "annotator_id": "expert_02",
            "annotation_timestamp": "2026-11-05T12:30:00Z",
            "annotation_notes": "Junior data analyst transitioning to data science; lacks deployment skills.",
        }

        for field in schema["required"]:
            assert field in record
        assert record["readiness_label"] == "Developing"

    def test_draft_pilot_record_conformance(self):
        with SCHEMA_PATH.open("r", encoding="utf-8") as f:
            schema = json.load(f)

        draft_record = {
            "annotation_id": "mr_101__software_developer__ann",
            "pair_id": "mr_101__http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1",
            "candidate_id": "mr_101",
            "candidate_source": "master_resumes",
            "target_occupation_uri": "http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1",
            "target_occupation_title": "software developer",
            "readiness_label": None,
            "confidence": None,
            "evidence": {
                "essential_skill_proficiency": None,
                "work_experience_relevance": None,
                "practical_application_evidence": None,
                "education_relevance": None,
                "certifications_observed": [],
                "key_evidence_summary": None,
                "candidate_profile_summary": {
                    "skills": ["Python", "Flask", "PostgreSQL"],
                    "experience_summary": ["Software Engineer at TechCorp (2 yrs)"],
                    "projects_summary": ["E-commerce API: REST service with Flask"],
                    "education_summary": ["B.Sc. in Computer Science"],
                },
            },
            "reviewer_status": "Draft",
            "annotator_id": "",
            "annotation_timestamp": "",
            "annotation_notes": "",
        }

        for field in schema["required"]:
            assert field in draft_record
        assert draft_record["readiness_label"] is None
        assert draft_record["confidence"] is None
        assert draft_record["reviewer_status"] == "Draft"

    def test_guidelines_document_exists_and_contains_core_rubric(self):
        assert GUIDELINES_PATH.exists()
        text = GUIDELINES_PATH.read_text(encoding="utf-8")

        assert "Job Ready" in text
        assert "Developing" in text
        assert "Not Ready" in text
        assert "Anti-Circularity Mandate" in text
        assert "Candidate-Job Compatibility" in text
        assert "Skill Coverage" in text
        assert "ESCO Occupation Expectations" in text


PILOT_DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "Datasets"
    / "Processed"
    / "readiness_annotation_pilot.jsonl"
)
PILOT_REPORT_PATH = (
    Path(__file__).resolve().parents[2]
    / "AI"
    / "Dataset_Preparation"
    / "readiness_annotation_pilot_report.md"
)


class TestPilotAnnotationDatasetValidation:
    """Validates the 100 pilot records in readiness_annotation_pilot.jsonl."""

    def test_pilot_file_exists_and_has_exactly_100_records(self):
        assert PILOT_DATASET_PATH.exists()
        lines = PILOT_DATASET_PATH.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 100

    def test_all_100_pilot_records_conform_to_schema(self):
        with SCHEMA_PATH.open("r", encoding="utf-8") as f:
            schema = json.load(f)

        required_keys = set(schema["required"])
        required_evidence = set(schema["properties"]["evidence"]["required"])

        with PILOT_DATASET_PATH.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                record = json.loads(line)
                # Check top-level required fields
                missing_top = required_keys - set(record.keys())
                assert not missing_top, f"Record {idx} missing keys: {missing_top}"

                # Check strict constraints
                assert record["candidate_source"] == "master_resumes"
                assert record["readiness_label"] is None
                assert record["confidence"] is None
                assert record["reviewer_status"] == "Draft"
                assert record["annotator_id"] == ""
                assert record["annotation_timestamp"] == ""
                assert record["annotation_notes"] == ""

                # Check evidence structure
                ev = record["evidence"]
                missing_ev = required_evidence - set(ev.keys())
                assert not missing_ev, f"Record {idx} evidence missing keys: {missing_ev}"

                # Check summary snapshot populated for human annotators
                snapshot = ev.get("candidate_profile_summary", {})
                assert len(snapshot.get("skills", [])) > 0
                assert len(snapshot.get("experience_summary", [])) > 0
                assert len(snapshot.get("projects_summary", [])) > 0
                assert len(snapshot.get("education_summary", [])) > 0

    def test_pilot_dataset_has_varied_occupations(self):
        occ_counts = {}
        with PILOT_DATASET_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                title = rec["target_occupation_title"]
                occ_counts[title] = occ_counts.get(title, 0) + 1

        assert len(occ_counts) >= 5
        assert "software developer" in occ_counts
        assert "cloud DevOps engineer" in occ_counts
        assert "data scientist" in occ_counts
        assert "ICT system administrator" in occ_counts
        assert sum(occ_counts.values()) == 100

    def test_pilot_report_exists_and_contains_statistics(self):
        assert PILOT_REPORT_PATH.exists()
        report_text = PILOT_REPORT_PATH.read_text(encoding="utf-8")
        assert "100 records" in report_text
        assert "master_resumes" in report_text
        assert "Zero Label Pre-Population" in report_text
        assert "Software Developer" in report_text


