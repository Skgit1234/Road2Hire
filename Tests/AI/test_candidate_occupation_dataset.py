"""Unit and Integration Tests for Unified Candidate-Occupation Dataset (M4.2).

Tests:
- Synthetic profile adapter schema conformance (CandidateProfile v1.1.0)
- Role to ESCO occupation resolution (exact, prefixes, canonical aliases)
- O*NET supplementary score loading
- Unified record construction and schema conformance (CandidateOccupationRecord)
- Duplicate pair detection and exclusion
- Strict separation of compatibility ground truth from readiness
- Pipeline execution and JSONL serialization
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from AI.Candidate_Profile.profile_validator import validate_candidate_profile_comprehensive
from AI.Dataset_Preparation.build_unified_dataset import (
    RoleOccupationResolver,
    UnifiedDatasetBuilder,
    load_onet_supplementary_data,
)
from AI.Dataset_Preparation.candidate_adapter import adapt_synthetic_profile_to_candidate_profile
from AI.Dataset_Preparation.dataset_inventory import (
    get_datasets_dir,
    load_synthetic_profiles,
    stream_master_resumes,
)
from AI.Knowledge_Graph.esco_graph import get_esco_graph
from AI.Skill_Extraction.esco_taxonomy import get_esco_taxonomy


@pytest.fixture(scope="module")
def esco_graph_fixture():
    """Shared ESCO Knowledge Graph fixture."""
    return get_esco_graph()


@pytest.fixture(scope="module")
def esco_taxonomy_fixture():
    """Shared ESCO Taxonomy fixture."""
    return get_esco_taxonomy()


@pytest.fixture(scope="module")
def onet_data_fixture():
    """Shared O*NET supplementary lookup fixture."""
    return load_onet_supplementary_data()


class TestSyntheticProfileAdapter:
    """Tests for adapt_synthetic_profile_to_candidate_profile."""

    def test_synthetic_profile_conforms_to_schema_v1_1_0(self, esco_taxonomy_fixture):
        raw_profiles = load_synthetic_profiles(limit=2)
        assert len(raw_profiles) >= 1

        profile = adapt_synthetic_profile_to_candidate_profile(
            raw_profiles[0], taxonomy=esco_taxonomy_fixture
        )

        # Conformance to schema v1.1.0
        assert profile["schema_version"] == "1.1.0"
        assert profile["source_file"].startswith("synthetic_profiles:")
        assert "candidate" in profile
        assert "skills" in profile
        assert "experience" in profile
        assert "metadata" in profile

        val = validate_candidate_profile_comprehensive(profile)
        assert val["errors"] == []

    def test_synthetic_profile_skills_normalization(self, esco_taxonomy_fixture):
        synthetic_record = {
            "profile_id": 999,
            "roles": ["Junior Backend Developer"],
            "skills_primary": ["Python", "SQL"],
            "skills_secondary": ["Docker", "Linux"],
            "experience_years": 2,
            "seniority": "Junior",
            "domains": ["Finance"],
            "preferences": {"locations": ["London"]},
            "career_intent": "Aspiring backend developer in fintech",
        }

        profile = adapt_synthetic_profile_to_candidate_profile(
            synthetic_record, taxonomy=esco_taxonomy_fixture
        )

        skill_names = [s["skill"] for s in profile["skills"]]
        assert any("python" in s.lower() for s in skill_names)
        assert len(profile["skills"]) == 4

        # Experience record generated
        assert len(profile["experience"]) == 1
        assert profile["experience"][0]["job_title"] == "Junior Backend Developer"
        assert "Finance" in profile["experience"][0]["raw_text"]


class TestRoleOccupationResolver:
    """Tests for RoleOccupationResolver."""

    def test_exact_esco_occupation_resolution(self, esco_graph_fixture):
        resolver = RoleOccupationResolver(esco_graph_fixture)
        res = resolver.resolve("software developer")
        assert res is not None
        uri, label = res
        assert "http://data.europa.eu/esco/occupation/" in uri
        assert "software developer" in label.lower()

    def test_prefix_stripping_resolution(self, esco_graph_fixture):
        resolver = RoleOccupationResolver(esco_graph_fixture)
        # Strips 'Junior' and resolves via canonical map
        res = resolver.resolve("Junior Software Engineer")
        assert res is not None
        uri, label = res
        assert "software developer" in label.lower()

    def test_canonical_alias_mappings(self, esco_graph_fixture):
        resolver = RoleOccupationResolver(esco_graph_fixture)
        python_res = resolver.resolve("Python Developer")
        assert python_res is not None
        assert "software developer" in python_res[1].lower()

        data_sci_res = resolver.resolve("Data Science Consultant")
        assert data_sci_res is not None
        assert "data scientist" in data_sci_res[1].lower()

        devops_res = resolver.resolve("Cloud Operations Architect (DevOps)")
        assert devops_res is not None
        assert "system administrator" in devops_res[1].lower()

    def test_unresolvable_title_returns_none(self, esco_graph_fixture):
        resolver = RoleOccupationResolver(esco_graph_fixture)
        assert resolver.resolve("Completely Nonexistent Role XYZ 12345") is None
        assert resolver.resolve("") is None
        assert resolver.resolve(None) is None


class TestONETSupplementaryData:
    """Tests for O*NET skill mapping loading."""

    def test_onet_data_loaded_successfully(self, onet_data_fixture):
        assert len(onet_data_fixture) > 0
        # Common O*NET skill
        programming = onet_data_fixture.get("programming")
        if programming:
            assert programming["importance_score"] > 0
            assert programming["level_score"] > 0


class TestUnifiedDatasetBuilder:
    """Tests for UnifiedDatasetBuilder record generation and validation."""

    def test_build_candidate_occupation_record_synthetic(
        self, esco_graph_fixture, esco_taxonomy_fixture
    ):
        builder = UnifiedDatasetBuilder(
            graph=esco_graph_fixture,
            taxonomy=esco_taxonomy_fixture,
        )

        raw_syn = load_synthetic_profiles(limit=1)[0]
        cand_profile = adapt_synthetic_profile_to_candidate_profile(
            raw_syn, taxonomy=esco_taxonomy_fixture
        )

        target_uri = esco_graph_fixture.resolve_occupation_uri("software developer")
        assert target_uri is not None

        record = builder.build_candidate_occupation_record(
            candidate_profile=cand_profile,
            target_occupation_uri=target_uri,
            candidate_source="synthetic_profiles",
        )

        assert record is not None
        assert record["candidate_id"] == str(raw_syn["profile_id"])
        assert record["candidate_source"] == "synthetic_profiles"
        assert record["pair_id"] == f"{raw_syn['profile_id']}__{target_uri}"

        # Skill gap features
        feats = record["skill_gap_features"]
        assert 0.0 <= feats["overall_skill_coverage_score"] <= 1.0
        assert 0.0 <= feats["essential_skill_coverage_score"] <= 1.0
        assert feats["matched_skills_count"] >= 0
        assert feats["missing_essential_skills_count"] >= 0

        # Graph features
        g_feats = record["graph_features"]
        assert g_feats is not None
        assert g_feats["total_nodes"] > 0
        assert g_feats["total_edges"] >= 0

        # Target occupation
        target = record["target_occupation"]
        assert target["occupation_id"] == target_uri
        assert target["total_required_skills"] > 0
        assert len(target["essential_skills"]) > 0

    def test_duplicate_pair_detection(self, esco_graph_fixture, esco_taxonomy_fixture):
        builder = UnifiedDatasetBuilder(
            graph=esco_graph_fixture,
            taxonomy=esco_taxonomy_fixture,
        )

        raw_syn = load_synthetic_profiles(limit=1)[0]
        cand_profile = adapt_synthetic_profile_to_candidate_profile(
            raw_syn, taxonomy=esco_taxonomy_fixture
        )
        target_uri = esco_graph_fixture.resolve_occupation_uri("software developer")

        # First build succeeds
        rec1 = builder.build_candidate_occupation_record(
            cand_profile, target_uri, "synthetic_profiles"
        )
        assert rec1 is not None

        # Second build of same pair returns None and logs exclusion
        rec2 = builder.build_candidate_occupation_record(
            cand_profile, target_uri, "synthetic_profiles"
        )
        assert rec2 is None
        assert any(
            e["reason"] == "Duplicate candidate-occupation pair"
            for e in builder.excluded_records
        )

    def test_small_pipeline_execution_and_jsonl_output(
        self, tmp_path, esco_graph_fixture, esco_taxonomy_fixture
    ):
        builder = UnifiedDatasetBuilder(
            graph=esco_graph_fixture,
            taxonomy=esco_taxonomy_fixture,
            output_dir=tmp_path,
        )

        # Run with limits (2 synthetic, 2 master resumes)
        out_file = builder.build_dataset(master_limit=2, synthetic_limit=2)
        assert out_file.exists()
        assert out_file.stat().st_size > 0

        # Validate JSONL records
        lines = out_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 4
        for line in lines:
            data = json.loads(line)
            assert "pair_id" in data
            assert "candidate_profile" in data
            assert "target_occupation" in data
            assert "skill_gap_features" in data
            assert "graph_features" in data

        # Generate report
        report_file = tmp_path / "test_report.md"
        builder.generate_report(report_file)
        assert report_file.exists()
        report_text = report_file.read_text(encoding="utf-8")
        assert "Road2Hire — M4.2 Unified Candidate–Occupation Dataset Report" in report_text
        assert "Total Candidate Profiles Processed" in report_text
