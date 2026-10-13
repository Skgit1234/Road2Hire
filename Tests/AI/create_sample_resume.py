from pathlib import Path

import pymupdf


OUTPUT_PATH = Path("Tests/AI/sample_resume.pdf")

RESUME_TEXT = """
Alex Morgan
alex.morgan@example.com | +1-555-010-2040
Pune, India

PROFESSIONAL SUMMARY
Computer science graduate interested in software development
and data analysis.

EDUCATION
Bachelor of Technology in Computer Science
Example Institute | 2022 - 2026

EXPERIENCE
Software Development Intern
Example Technologies | January 2026 - June 2026
- Developed Python scripts for data processing.
- Used Git for version control.

SKILLS
Python, SQL, Git, REST APIs, Data Analysis

PROJECTS
Roadmap Planner
- Built a project planner using Python.
- Created structured outputs for project reports.

CERTIFICATIONS
Python Programming Certificate
Example Learning Academy | 2025
""".strip()


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    document = pymupdf.open()
    page = document.new_page()
    page.insert_textbox(
        pymupdf.Rect(50, 50, 545, 790),
        RESUME_TEXT,
        fontsize=11,
        lineheight=1.3,
    )
    document.save(OUTPUT_PATH)
    document.close()

    print(f"Sample resume created: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()