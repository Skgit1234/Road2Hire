# Road2Hire Backend Tests

Run from the repository root:

```powershell
python -m pytest Tests/Backend/ -v
```

The tests in this folder are aligned with the backend routes observed in the
current `issue15/build-processing-apis` branch.

## Test files

- `test_auth.py` — authentication route registration.
- `test_resume.py` — resume upload, analysis, download and resume-list route registration.
- `test_profile.py` — existing profile GET/PATCH route registration.
- `test_candidate_profile.py` — candidate-profile model registration and schema metadata.
- `test_skill_gaps.py` — skill-gap route registration.
- `test_learning_tasks.py` — learning-task progress route registration.

## Scope

The current API route listing used to prepare these tests did not include
`GET /profile/candidate` or `POST /resume/{resume_id}/analyze`.
The tests therefore do not assume those endpoints exist. The candidate-profile
test checks model registration only; it does not claim that a candidate-profile
API endpoint is available.

These are basic smoke/schema tests. They do not replace full endpoint behavior,
authorization, database integration, or file-validation tests.
