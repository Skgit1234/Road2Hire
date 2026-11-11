# Backend development dependencies

Install the backend runtime dependencies and ordinary test dependencies from the repository root:

```powershell
python -m pip install -r Backend/Requirements-dev.txt
```

This manifest includes `Backend/Requirements.txt` and the test client dependencies. The embedding tests
in `Tests/AI/test_skill_extractor.py` additionally import `sentence-transformers`. Install the optional
AI test manifest to run them:

```powershell
python -m pip install -r Backend/Requirements-ai-test.txt
python -m pytest Tests/AI/test_skill_extractor.py
```

The first embedding test run may download the `sentence-transformers/all-MiniLM-L6-v2` model data.
This dependency and model are not required by the ordinary backend runtime manifest.

## Runtime dependency manifest review

`Backend/Requirements.txt` is UTF-8. The prior manifest's 14 entries are preserved unchanged:

- `annotated-doc==0.0.5`
- `annotated-types==0.8.0`
- `anyio==4.14.2`
- `click==8.4.2`
- `colorama==0.4.6`
- `fastapi==0.141.1`
- `h11==0.16.0`
- `idna==3.18`
- `pydantic==2.13.4`
- `pydantic_core==2.46.4`
- `starlette==1.6.0`
- `typing-inspection==0.4.3`
- `typing_extensions==4.16.0`
- `uvicorn==0.52.1`

The following runtime entries were added to that prior set:

- `SQLAlchemy==2.1.5`
- `alembic==1.20.0`
- `psycopg[binary]==3.3.6`
- `python-dotenv==1.2.4`
- `python-multipart==0.0.32`
- `python-jose[cryptography]==3.5.0`
- `passlib[bcrypt]==1.7.4`
- `bcrypt==4.0.1`
- `email-validator==2.3.0`
- `PyMuPDF==1.28.2`

No previous runtime entries were removed or version-changed. Ordinary test-only packages are in
`Backend/Requirements-dev.txt`; `sentence-transformers==5.1.2` is isolated in
`Backend/Requirements-ai-test.txt`.
