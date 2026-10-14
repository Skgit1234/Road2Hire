# Road2Hire Skill Taxonomy Strategy

## Purpose

The Road2Hire skill taxonomy provides a standardized foundation for resume skill extraction, skill normalization, skill gap detection, career recommendation, and personalized learning roadmap generation.

The taxonomy will be based primarily on the ESCO and O*NET occupational classification systems.

## Skill Categories

1. Programming Languages
   - Python, Java, C++, JavaScript, TypeScript

2. Frontend Development
   - HTML, CSS, React, Angular, Next.js

3. Backend Development
   - Node.js, Django, FastAPI, Spring Boot

4. Databases
   - PostgreSQL, MySQL, MongoDB, Redis

5. AI & Machine Learning
   - TensorFlow, PyTorch, NLP, Scikit-learn

6. Data Analytics
   - Pandas, NumPy, SQL, Power BI, Tableau

7. Cloud Computing
   - AWS, Azure, Google Cloud

8. DevOps
   - Docker, Kubernetes, GitHub Actions, Jenkins

9. Developer Tools
   - Git, Linux, VS Code, Postman

10. Soft Skills
    - Communication, Leadership, Teamwork, Problem Solving

## Data Sources

### ESCO

ESCO provides skills, occupations, skill groups, and occupation-skill relationships. It will provide the primary European occupational taxonomy and skill relationships for Road2Hire.

### O*NET

O*NET provides occupational information including skills, knowledge, abilities, transferable skills, and technology skills. It will complement ESCO and provide additional occupational skill information.

## Normalization Strategy

Skills extracted from resumes and job descriptions will be normalized against the master taxonomy.

Examples:

- ReactJS → React
- Java Script → JavaScript
- PostgreSQL DB → PostgreSQL
- ML → Machine Learning

Each normalized skill will have a unique `Skill_Id` and may contain corresponding ESCO and O*NET identifiers.

## Master Taxonomy Schema

The processed taxonomy will use the following fields:

- Skill_Id
- Skill_Name
- Category
- Sub_Category
- ESCO_Id
- ONET_Id
- Aliases

## Intended Use

The taxonomy will support:

- Resume Skill Extraction
- Skill Normalization
- Skill Gap Detection
- Career Recommendation
- Career Readiness Scoring
- Personalized Learning Roadmap Generation
