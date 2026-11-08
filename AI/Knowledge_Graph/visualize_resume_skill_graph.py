import json
from html import escape
from pathlib import Path

from AI.Resume_Processing.resume_pipeline import process_resume
from AI.Skill_Extraction.skill_extractor import extract_skills
from AI.Knowledge_Graph.skill_graph_matcher import load_skill_graph


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RESUME_PATH = PROJECT_ROOT / "Tests" / "AI" / "sample_resume.pdf"
GRAPH_PATH = PROJECT_ROOT / "AI" / "Knowledge_Graph" / "skill_graph_v1.json"
OUTPUT_PATH = PROJECT_ROOT / "Tests" / "AI" / "resume_skill_graph.svg"
RESULT_PATH = PROJECT_ROOT / "Tests" / "AI" / "resume_detected_skills.json"


def main():
    # 1. Process the sample resume PDF.
    resume = process_resume(RESUME_PATH)

    if resume["extraction_status"] != "success":
        raise ValueError(
            "No readable text was extracted from the PDF. OCR may be required."
        )

    # 2. Extract skills from the resume.
    extraction = extract_skills(resume)

    detected_names = {
        item["skill"].casefold()
        for item in extraction["skills"]
    }

    # 3. Load the existing knowledge graph.
    graph = load_skill_graph(GRAPH_PATH)

    detected_nodes = [
        skill
        for skill in graph["skills"]
        if skill["name"].casefold() in detected_names
    ]

    detected_ids = {skill["id"] for skill in detected_nodes}

    # 4. Find relationships touching detected skills.
    relationships = [
        edge
        for edge in graph["relationships"]
        if edge["source"] in detected_ids
        or edge["target"] in detected_ids
    ]

    # Include the other endpoint of each relevant relationship.
    related_ids = {
        edge["source"] for edge in relationships
    } | {
        edge["target"] for edge in relationships
    }

    # Keep only graph nodes involved in the displayed relationships.
    all_nodes = [
        skill
        for skill in graph["skills"]
        if skill["id"] in related_ids
    ]

    related_only_ids = related_ids - detected_ids

    # 5. Arrange the displayed nodes in a grid.
    width = 1000
    node_width = 200
    node_height = 64
    columns = 3

    rows = max(1, (len(all_nodes) + columns - 1) // columns)
    height = max(300, 180 + rows * 150)

    positions = {
        skill["id"]: (
            180 + (index % columns) * 320,
            130 + (index // columns) * 150,
        )
        for index, skill in enumerate(all_nodes)
    }

    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),
        f'<rect width="{width}" height="{height}" fill="#f8fafc"/>',
        (
            '<text x="500" y="38" text-anchor="middle" '
            'font-family="Arial" font-size="24" font-weight="bold" '
            'fill="#172554">Resume Skill Relationship Graph</text>'
        ),
        (
            '<text x="500" y="68" text-anchor="middle" '
            'font-family="Arial" font-size="14" fill="#475569">'
            f'{escape(RESUME_PATH.name)} | '
            f'{len(detected_nodes)} matched graph skills | '
            f'{len(related_only_ids)} related skills'
            '</text>'
        ),
        (
            '<defs><marker id="arrow" markerWidth="9" markerHeight="9" '
            'refX="8" refY="3" orient="auto">'
            '<path d="M0,0 L0,6 L9,3 z" fill="#475569"/>'
            '</marker></defs>'
        ),
    ]

    # 6. Draw relationships and their labels.
    for edge in relationships:
        source_id = edge["source"]
        target_id = edge["target"]

        if source_id not in positions or target_id not in positions:
            continue

        x1, y1 = positions[source_id]
        x2, y2 = positions[target_id]

        parts.append(
            f'<line x1="{x1}" y1="{y1}" '
            f'x2="{x2}" y2="{y2}" '
            'stroke="#475569" stroke-width="2" '
            'marker-end="url(#arrow)"/>'
        )

        label = escape(edge["relationship"])
        label_x = (x1 + x2) / 2
        label_y = (y1 + y2) / 2 - 8

        parts.append(
            f'<text x="{label_x}" y="{label_y}" '
            'text-anchor="middle" font-family="Arial" '
            'font-size="12" fill="#9a3412">'
            f'{label}</text>'
        )

    # 7. Draw detected and related skill nodes.
    for skill in all_nodes:
        x, y = positions[skill["id"]]

        if skill["id"] in detected_ids:
            fill = "#bbf7d0"
            stroke = "#15803d"
            text_color = "#14532d"
        else:
            fill = "#dbeafe"
            stroke = "#2563eb"
            text_color = "#1e3a8a"

        parts.append(
            f'<rect x="{x - node_width / 2}" '
            f'y="{y - node_height / 2}" '
            f'width="{node_width}" height="{node_height}" '
            f'rx="12" fill="{fill}" stroke="{stroke}" '
            'stroke-width="2"/>'
        )

        parts.append(
            f'<text x="{x}" y="{y + 5}" '
            'text-anchor="middle" font-family="Arial" '
            'font-size="15" '
            f'fill="{text_color}">'
            f'{escape(skill["name"])}</text>'
        )

    # 8. Add a legend.
    legend_y = height - 55

    parts.append(
        f'<rect x="25" y="{legend_y - 12}" width="16" height="16" '
        'rx="3" fill="#bbf7d0" stroke="#15803d"/>'
        f'<text x="48" y="{legend_y}" font-family="Arial" '
        'font-size="13" fill="#14532d">'
        'Detected in resume</text>'
    )

    parts.append(
        f'<rect x="230" y="{legend_y - 12}" width="16" height="16" '
        'rx="3" fill="#dbeafe" stroke="#2563eb"/>'
        f'<text x="253" y="{legend_y}" font-family="Arial" '
        'font-size="13" fill="#1e3a8a">'
        'Related skill</text>'
    )

    # 9. Add an explanatory message.
    if not detected_nodes:
        message = "No skills from the current graph were detected."
    elif not relationships:
        message = "Detected skills have no relationships in this graph."
    else:
        message = (
            f"{len(relationships)} relationships shown, including "
            f"{len(detected_nodes)} detected skills and "
            f"{len(related_only_ids)} related skills."
        )

    parts.append(
        f'<text x="25" y="{height - 25}" '
        'font-family="Arial" font-size="13" fill="#475569">'
        f'{escape(message)} Relationships come from skill_graph_v1.json.'
        '</text>'
    )

    parts.append("</svg>")

    # 10. Save the SVG graph.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(parts), encoding="utf-8")

    # 11. Save detected skills, related skills, and relationships as JSON.
    result = {
        "resume": RESUME_PATH.name,
        "detected_skills": [
            {"id": skill["id"], "name": skill["name"]}
            for skill in detected_nodes
        ],
        "related_skills": [
            {"id": skill["id"], "name": skill["name"]}
            for skill in all_nodes
            if skill["id"] in related_only_ids
        ],
        "relationships": relationships,
        "detected_skill_count": len(detected_nodes),
        "related_skill_count": len(related_only_ids),
        "relationship_count": len(relationships),
    }

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(result, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    # 12. Print results.
    print(f"Resume processed: {RESUME_PATH}")
    print(f"Detected graph skills: {len(detected_nodes)}")

    for skill in detected_nodes:
        print(f"  - {skill['name']}")

    print(f"Related skills: {len(related_only_ids)}")

    for skill in all_nodes:
        if skill["id"] in related_only_ids:
            print(f"  - {skill['name']} (related)")

    print(f"Relationships shown: {len(relationships)}")
    print(f"SVG created: {OUTPUT_PATH}")
    print(f"Skill results saved: {RESULT_PATH}")


if __name__ == "__main__":
    main()
