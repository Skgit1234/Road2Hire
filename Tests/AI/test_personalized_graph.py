"""Tests for Road2Hire M3 Personalized Knowledge Graph Construction.

Covers:
- Candidate-specific graph construction from structured profile
- Node types (candidate, education, experience, project, certification, candidate_skill, esco_skill, occupation)
- Edge types (profile components, provenance, taxonomy grounding, career goals, requirements, skill gap)
- Distinct representation of matched, partially matched, missing, and surplus skills
- Preservation of ESCO taxonomy relationships (broader, narrower, related)
- Incomplete and empty candidate profiles (freshers / zero skills)
- Duplicate node and edge prevention with multi-relation merging
- Graph serialization to dictionary / JSON-compatible format
- Integration with central Road2HireModel pipeline
"""

import json
from pathlib import Path
import unittest

from AI.Candidate_Profile.profile_schema import CandidateProfile
from AI.Knowledge_Graph.esco_graph import get_esco_graph
from AI.Knowledge_Graph.personalized_graph import (
    PersonalizedKnowledgeGraph,
    build_personalized_graph,
)
from AI.Skill_Extraction.esco_taxonomy import get_esco_taxonomy

SAMPLE_RESUME_PDF = Path("Tests/AI/sample_resume.pdf")


class TestPersonalizedKnowledgeGraph(unittest.TestCase):
    """Unit and integration tests for PersonalizedKnowledgeGraph."""

    @classmethod
    def setUpClass(cls):
        cls.taxonomy = get_esco_taxonomy()
        cls.esco_graph = get_esco_graph(cls.taxonomy)

        # Mock structured profile conforming to schema v1.1.0
        cls.sample_profile: CandidateProfile = {
            "schema_version": "1.1.0",
            "source_file": "sample_candidate.pdf",
            "candidate": {
                "name": "Alex Mercer",
                "email": "alex.mercer@example.com",
                "phone": "+1 555-0199",
                "location": "New York, NY",
                "summary": "Experienced software engineer specializing in backend APIs and data systems.",
                "raw_contact_information": "Alex Mercer\nalex.mercer@example.com",
                "raw_summary": "Experienced software engineer specializing in backend APIs and data systems.",
            },
            "skills": [
                {
                    "skill": "Python (computer programming)",
                    "ESCO_Skill_Id": "http://data.europa.eu/esco/skill/4c5b2a62-5a76-4d99-a7a8-cbf04e9e8d1e",
                    "ESCO_Skill_Name": "Python (computer programming)",
                },
                {
                    "skill": "SQL",
                    "ESCO_Skill_Id": "http://data.europa.eu/esco/skill/25078512-32b0-466c-bb6f-87063d81b183",
                    "ESCO_Skill_Name": "SQL",
                },
                {
                    "skill": "baking bread",
                    "ESCO_Skill_Id": "",
                    "ESCO_Skill_Name": "",
                },
            ],
            "education": [
                {
                    "degree": "Bachelor of Science",
                    "field_of_study": "Computer Science",
                    "institution": "State University",
                    "start_year": 2018,
                    "end_year": 2022,
                    "cgpa": 3.85,
                    "academic_level": "bachelor",
                    "raw_text": "B.S. Computer Science, State University, 2018-2022, CGPA: 3.85",
                }
            ],
            "experience": [
                {
                    "job_title": "Backend Developer",
                    "organization": "Acme Corp",
                    "employment_type": "full-time",
                    "start_date": "2022-06",
                    "end_date": "2024-08",
                    "responsibilities": ["Developed REST services using Python and SQL"],
                    "skills_used": ["Python (computer programming)", "SQL"],
                    "raw_text": "Backend Developer at Acme Corp",
                }
            ],
            "projects": [
                {
                    "project_name": "Data Analytics Service",
                    "description": "High performance ingestion engine",
                    "technologies": ["Python (computer programming)", "SQL"],
                    "responsibilities": ["Architecture"],
                    "related_skills": ["Python (computer programming)"],
                    "raw_text": "Data Analytics Service project description",
                }
            ],
            "certifications": [
                {
                    "name": "Certified Professional Programmer",
                    "issuing_organization": "Tech Alliance",
                    "issue_date": "2023-01",
                    "expiration_date": "2026-01",
                    "credential_id": "CERT-12345",
                    "raw_text": "Certified Professional Programmer",
                }
            ],
            "metadata": {
                "generated_at": "2026-11-04T12:00:00Z",
                "total_skills_detected": 3,
                "sections_detected": ["education", "experience", "skills", "projects", "certifications"],
            },
        }

    def test_graph_construction_nodes_and_edges(self):
        """Verify that all profile components and target occupation are converted to nodes and edges."""
        pkg = PersonalizedKnowledgeGraph(
            candidate=self.sample_profile,
            target_occupation="software developer",
            esco_graph=self.esco_graph,
            taxonomy=self.taxonomy,
        )

        G = pkg.graph
        self.assertGreater(G.number_of_nodes(), 0)
        self.assertGreater(G.number_of_edges(), 0)

        # 1. Candidate root node
        self.assertTrue(G.has_node("candidate:root"))
        root_data = G.nodes["candidate:root"]
        self.assertEqual(root_data["kind"], "candidate")
        self.assertEqual(root_data["name"], "Alex Mercer")
        self.assertEqual(root_data["email"], "alex.mercer@example.com")

        # 2. Profile component nodes
        self.assertTrue(G.has_node("candidate:education:0"))
        self.assertEqual(G.nodes["candidate:education:0"]["kind"], "education")
        self.assertEqual(G.nodes["candidate:education:0"]["degree"], "Bachelor of Science")

        self.assertTrue(G.has_node("candidate:experience:0"))
        self.assertEqual(G.nodes["candidate:experience:0"]["kind"], "experience")
        self.assertEqual(G.nodes["candidate:experience:0"]["job_title"], "Backend Developer")

        self.assertTrue(G.has_node("candidate:project:0"))
        self.assertEqual(G.nodes["candidate:project:0"]["kind"], "project")
        self.assertEqual(G.nodes["candidate:project:0"]["project_name"], "Data Analytics Service")

        self.assertTrue(G.has_node("candidate:certification:0"))
        self.assertEqual(G.nodes["candidate:certification:0"]["kind"], "certification")

        # 3. Candidate skills
        py_node = "candidate:skill:python (computer programming)"
        self.assertTrue(G.has_node(py_node))
        self.assertEqual(G.nodes[py_node]["kind"], "candidate_skill")
        self.assertTrue(G.nodes[py_node]["is_esco_mapped"])

        # 4. Target occupation node
        occ_uri = self.esco_graph.resolve_occupation_uri("software developer")
        self.assertIsNotNone(occ_uri)
        self.assertTrue(G.has_node(occ_uri))
        self.assertEqual(G.nodes[occ_uri]["kind"], "occupation")

        # 5. Root edges
        self.assertTrue(G.has_edge("candidate:root", "candidate:education:0"))
        self.assertTrue(G.has_edge("candidate:root", "candidate:experience:0"))
        self.assertTrue(G.has_edge("candidate:root", "candidate:project:0"))
        self.assertTrue(G.has_edge("candidate:root", "candidate:certification:0"))
        self.assertTrue(G.has_edge("candidate:root", py_node))
        self.assertTrue(G.has_edge("candidate:root", occ_uri))

    def test_provenance_edges_from_components_to_skills(self):
        """Experience and Project nodes must link to candidate skills with applies_skill/uses_skill."""
        pkg = PersonalizedKnowledgeGraph(
            candidate=self.sample_profile,
            target_occupation="software developer",
            esco_graph=self.esco_graph,
            taxonomy=self.taxonomy,
        )
        G = pkg.graph
        py_node = "candidate:skill:python (computer programming)"
        sql_node = "candidate:skill:sql"

        # Experience -> applies_skill -> Python and SQL
        self.assertTrue(G.has_edge("candidate:experience:0", py_node))
        self.assertIn("applies_skill", G.edges["candidate:experience:0", py_node]["relation_names"])

        self.assertTrue(G.has_edge("candidate:experience:0", sql_node))
        self.assertIn("applies_skill", G.edges["candidate:experience:0", sql_node]["relation_names"])

        # Project -> uses_skill -> Python and SQL
        self.assertTrue(G.has_edge("candidate:project:0", py_node))
        self.assertIn("uses_skill", G.edges["candidate:project:0", py_node]["relation_names"])

    def test_distinct_gap_representation_matched_missing_surplus(self):
        """Matched, partially matched, missing, and surplus skills must have distinct statuses and edges."""
        pkg = PersonalizedKnowledgeGraph(
            candidate=self.sample_profile,
            target_occupation="software developer",
            esco_graph=self.esco_graph,
            taxonomy=self.taxonomy,
        )

        matched = pkg.get_matched_skills()
        missing = pkg.get_missing_skills()
        self.assertGreater(len(matched), 0, "Expected at least 1 matched skill (Python/SQL).")
        self.assertGreater(len(missing), 0, "Expected missing requirements for software developer.")

        # Check matched edge attributes
        first_match = matched[0]
        self.assertIn("credit_assigned", first_match)
        self.assertIn("tier", first_match)
        self.assertIn("explanation", first_match)

        # Check missing skills are marked as missing on nodes and connected to occupation
        occ_uri = self.esco_graph.resolve_occupation_uri("software developer")
        for m in missing:
            self.assertEqual(pkg.graph.nodes[m["uri"]]["gap_status"], "missing")
            self.assertTrue(pkg.graph.has_edge(occ_uri, m["uri"]))
            self.assertIn("has_missing_skill", pkg.graph.edges[occ_uri, m["uri"]]["relation_names"])

        # Surplus skill check: 'baking bread' should be tagged as surplus
        bread_node = "candidate:skill:baking bread"
        self.assertTrue(pkg.graph.has_node(bread_node))
        self.assertEqual(pkg.graph.nodes[bread_node]["gap_status"], "surplus")
        self.assertTrue(pkg.graph.has_edge("candidate:root", bread_node))
        self.assertIn("has_surplus_skill", pkg.graph.edges["candidate:root", bread_node]["relation_names"])

    def test_empty_candidate_profile_freshers(self):
        """Freshers with no skills or experiences should receive a valid graph with 100% missing requirements."""
        empty_profile: CandidateProfile = {
            "schema_version": "1.1.0",
            "source_file": "fresher.pdf",
            "candidate": {"name": "Fresher Candidate"},
            "skills": [],
            "education": [],
            "experience": [],
            "projects": [],
            "certifications": [],
            "metadata": {},
        }

        pkg = PersonalizedKnowledgeGraph(
            candidate=empty_profile,
            target_occupation="software developer",
            esco_graph=self.esco_graph,
            taxonomy=self.taxonomy,
        )

        summary = pkg.get_summary()
        self.assertEqual(summary["overall_skill_coverage_score"], 0.0)
        self.assertEqual(len(pkg.get_matched_skills()), 0)
        self.assertGreater(len(pkg.get_missing_skills()), 0)
        self.assertEqual(summary["node_counts_by_kind"].get("candidate_skill", 0), 0)

    def test_incomplete_profile_graceful_handling(self):
        """Profiles with omitted or None sections construct cleanly without errors."""
        incomplete_profile = {
            "candidate": {"name": "Jane Doe"},
            "skills": ["Python (computer programming)"],
        }

        pkg = PersonalizedKnowledgeGraph(
            candidate=incomplete_profile,
            target_occupation="software developer",
            esco_graph=self.esco_graph,
            taxonomy=self.taxonomy,
        )
        self.assertTrue(pkg.graph.has_node("candidate:root"))
        self.assertEqual(len(pkg.get_matched_skills()), 1)

    def test_duplicate_prevention_and_multi_relation_merging(self):
        """Adding duplicate edges merges relationship information without overwriting existing data."""
        pkg = PersonalizedKnowledgeGraph(
            candidate={"skills": []},
            target_occupation="software developer",
            esco_graph=self.esco_graph,
            taxonomy=self.taxonomy,
        )

        # Add initial edge
        pkg._add_or_merge_edge("candidate:root", "test_target", relation="initial_relation", score=0.8)
        self.assertEqual(pkg.graph.edges["candidate:root", "test_target"]["relation_names"], ["initial_relation"])

        # Add second edge between same directed nodes with different relation
        pkg._add_or_merge_edge("candidate:root", "test_target", relation="second_relation", priority="high")
        edge_data = pkg.graph.edges["candidate:root", "test_target"]
        self.assertIn("initial_relation", edge_data["relation_names"])
        self.assertIn("second_relation", edge_data["relation_names"])
        self.assertEqual(len(edge_data["relations"]), 2)

        # Re-adding identical relation should not create duplicate entries
        pkg._add_or_merge_edge("candidate:root", "test_target", relation="initial_relation")
        self.assertEqual(len(edge_data["relations"]), 2)

    def test_esco_skill_relationship_preservation(self):
        """Hierarchical and semantic relations between ESCO skills in the graph must be preserved."""
        # Find two skills with a broader/narrower relation
        narrower_uri = "http://data.europa.eu/esco/skill/0007bdc2-dd15-4824-b7d6-416522c46f35"
        broader_uri = "http://data.europa.eu/esco/skill/23033c54-cc98-47dc-b972-4a8d1646754d"

        candidate = {
            "skills": [
                {
                    "skill": "control compliance of railway vehicles regulations",
                    "ESCO_Skill_Id": narrower_uri,
                    "ESCO_Skill_Name": "control compliance of railway vehicles regulations",
                },
                {
                    "skill": "inspect manufacture of rolling stock",
                    "ESCO_Skill_Id": broader_uri,
                    "ESCO_Skill_Name": "inspect manufacture of rolling stock",
                },
            ]
        }

        pkg = PersonalizedKnowledgeGraph(
            candidate=candidate,
            target_occupation="software developer",
            esco_graph=self.esco_graph,
            taxonomy=self.taxonomy,
        )

        # Both ESCO nodes exist in the graph
        self.assertTrue(pkg.graph.has_node(narrower_uri))
        self.assertTrue(pkg.graph.has_node(broader_uri))

        # Check preserved ESCO edges
        self.assertTrue(
            pkg.graph.has_edge(narrower_uri, broader_uri) or pkg.graph.has_edge(broader_uri, narrower_uri)
        )
        if pkg.graph.has_edge(narrower_uri, broader_uri):
            edge_data = pkg.graph.edges[narrower_uri, broader_uri]
            self.assertIn("broader_skill", edge_data["relation_names"])

    def test_serialization_to_dict_and_json(self):
        """Graph can be serialized to a dictionary and valid JSON for API consumption."""
        pkg = PersonalizedKnowledgeGraph(
            candidate=self.sample_profile,
            target_occupation="software developer",
            esco_graph=self.esco_graph,
            taxonomy=self.taxonomy,
        )
        data = pkg.to_dict()
        self.assertIn("summary", data)
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertGreater(len(data["nodes"]), 0)
        self.assertGreater(len(data["edges"]), 0)

        # Ensure JSON serializable
        json_str = json.dumps(data)
        self.assertIsInstance(json_str, str)


class TestPersonalizedGraphIntegrationWithModel(unittest.TestCase):
    """Test build_personalized_graph through central Road2HireModel."""

    @classmethod
    def setUpClass(cls):
        from AI.road2hire_model import Road2HireModel

        cls.model = Road2HireModel()

    def test_build_personalized_graph_from_pdf_resume(self):
        pkg = self.model.build_personalized_graph(
            resume_or_profile=SAMPLE_RESUME_PDF,
            target_occupation="software developer",
        )
        self.assertIsInstance(pkg, PersonalizedKnowledgeGraph)
        summary = pkg.get_summary()
        self.assertGreater(summary["total_nodes"], 0)
        self.assertGreater(summary["total_edges"], 0)
        self.assertGreater(len(pkg.get_missing_skills()), 0)

    def test_predict_remains_unmodified(self):
        """Ensure predict() output schema remains 100% backward-compatible."""
        result = self.model.predict(SAMPLE_RESUME_PDF)
        expected_keys = {
            "status", "pipeline_version", "source_file", "page_count",
            "extraction_status", "sections", "section_count", "detected_headings",
            "extracted_skills", "skill_count", "esco_mappings", "mapped_skill_count",
            "occupation_matches", "candidate_profile", "profile_validation_errors",
            "warnings", "errors",
        }
        self.assertEqual(expected_keys - result.keys(), set())


if __name__ == "__main__":
    unittest.main()

