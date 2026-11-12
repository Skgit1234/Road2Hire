
import json
from html import escape
from pathlib import Path


HERE = Path(__file__).resolve().parent
GRAPH_PATH = HERE / "skill_graph_v1.json"
OUTPUT_PATH = HERE / "skill_graph_v1.svg"


def main():
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    skills = graph["skills"]
    relationships = graph["relationships"]

    width, height = 1100, 700
    positions = {
        skill["id"]: (
            180 + (index % 3) * 370,
            150 + (index // 3) * 190,
        )
        for index, skill in enumerate(skills)
    }

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="550" y="42" text-anchor="middle" '
        'font-size="25" font-family="Arial" font-weight="bold" '
        'fill="#172554">Road2Hire Skill Knowledge Graph V1</text>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" '
        'refX="8" refY="3" orient="auto">'
        '<path d="M0,0 L0,6 L9,3 z" fill="#475569"/></marker></defs>',
    ]

    # Draw directed relationships and labels.
    for edge in relationships:
        x1, y1 = positions[edge["source"]]
        x2, y2 = positions[edge["target"]]
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            'stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>'
        )
        label = escape(edge["relationship"])
        parts.append(
            f'<text x="{(x1+x2)/2}" y="{(y1+y2)/2-10}" '
            'text-anchor="middle" font-family="Arial" font-size="14" '
            'fill="#9a3412">'
            f'{label}</text>'
        )

    # Draw skill nodes.
    for skill in skills:
        x, y = positions[skill["id"]]
        name = escape(skill["name"])
        parts.append(
            f'<rect x="{x-100}" y="{y-30}" width="200" height="60" '
            'rx="12" fill="#dbeafe" stroke="#2563eb" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{x}" y="{y+5}" text-anchor="middle" '
            'font-family="Arial" font-size="16" fill="#1e3a8a">'
            f'{name}</text>'
        )

    parts.append(
        '<text x="30" y="675" font-family="Arial" font-size="13" '
        'fill="#475569">Arrows show relationship direction. '
        'All nodes and edges come from skill_graph_v1.json.</text>'
    )
    parts.append("</svg>")

    OUTPUT_PATH.write_text("\n".join(parts), encoding="utf-8")
    print(f"Visualization created: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
