"""Opt-in HTTP smoke tests for the existing FastAPI resume workflow.

The health and invalid-upload checks are non-writing. The complete workflow
creates resume rows/files and is deliberately gated on explicit confirmation
that the local backend uses an isolated database.
"""

import json
import os
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid


BASE_URL = os.environ.get("ROAD2HIRE_SMOKE_BASE_URL", "").strip().rstrip("/")
BEARER_TOKEN = os.environ.get("ROAD2HIRE_SMOKE_BEARER_TOKEN", "").strip()
ALLOW_WRITES = os.environ.get("ROAD2HIRE_SMOKE_ALLOW_WRITES") == "1"
DATABASE_ISOLATED = os.environ.get("ROAD2HIRE_SMOKE_DATABASE_ISOLATED") == "1"


def _is_local_base_url() -> bool:
    if not BASE_URL:
        return False
    parsed = urllib.parse.urlparse(BASE_URL)
    return parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}


def _full_workflow_enabled() -> bool:
    return _is_local_base_url() and bool(BEARER_TOKEN) and ALLOW_WRITES and DATABASE_ISOLATED


def _request(path: str, method: str = "GET", headers: dict[str, str] | None = None, body: bytes | None = None):
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers or {"Accept": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.status
            raw = response.read()
    except urllib.error.HTTPError as error:
        status = error.code
        raw = error.read()

    try:
        payload = json.loads(raw) if raw else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = None
    return status, payload


def _multipart(user_id: int, filename: str, file_bytes: bytes) -> tuple[str, bytes]:
    boundary = f"road2hire-smoke-{uuid.uuid4().hex}"
    body = b"".join(
        [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"user_id\"\r\n\r\n{user_id}\r\n".encode(),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: application/pdf\r\n\r\n".encode(),
            file_bytes,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    return boundary, body


def _create_pdf(text: str) -> bytes:
    lines = [
        "BT",
        "/F1 12 Tf",
        "72 720 Td",
    ]
    for index, line in enumerate(text.splitlines()):
        if index:
            lines.append("0 -16 Td")
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        lines.append(f"({escaped}) Tj")
    lines.append("ET")
    stream = "\n".join(lines).encode("ascii")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for object_id, obj in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{object_id} 0 obj\n".encode("ascii"))
        document.extend(obj)
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(document)


@unittest.skipUnless(_is_local_base_url(), "Set ROAD2HIRE_SMOKE_BASE_URL to opt in to local HTTP checks.")
class ResumeHttpValidationSmokeTests(unittest.TestCase):
    def test_live_health_and_invalid_pdf_validation(self):
        status, payload = _request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "healthy"})

        boundary, body = _multipart(1, "invalid-resume.pdf", b"not a PDF")
        status, payload = _request(
            "/resume/upload",
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            body=body,
        )
        self.assertEqual(status, 401)
        self.assertEqual(payload, {"detail": "Not authenticated"})


@unittest.skipUnless(
    _full_workflow_enabled(),
    "Full resume smoke test writes data; configure a local isolated database, bearer token, and explicit write opt-in.",
)
class ResumeWorkflowHttpSmokeTests(unittest.TestCase):
    def test_upload_list_analysis_processing_error_and_cleanup(self):
        token_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {BEARER_TOKEN}",
        }
        created_resume_ids: list[int] = []

        try:
            status, profile = _request("/profile", headers=token_headers)
            self.assertEqual(status, 200)
            self.assertIsInstance(profile, dict)
            user_id = profile.get("id")
            self.assertIsInstance(user_id, int)
            self.assertGreater(user_id, 0)

            # This validation path must reject before querying or writing a row.
            invalid_boundary, invalid_body = _multipart(
                user_id, "invalid-resume.pdf", b"not a PDF"
            )
            invalid_headers = {
                **token_headers,
                "Content-Type": f"multipart/form-data; boundary={invalid_boundary}",
            }
            status, payload = _request(
                "/resume/upload",
                method="POST",
                headers=invalid_headers,
                body=invalid_body,
            )
            self.assertEqual(status, 400)
            self.assertEqual(payload, {"detail": "File does not have a valid PDF signature"})

            filename = f"road2hire-smoke-{uuid.uuid4().hex}.pdf"
            boundary, body = _multipart(
                user_id,
                filename,
                _create_pdf("Skills\nPython SQL\nProjects\nBuilt a smoke-test project."),
            )
            upload_headers = {
                **token_headers,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            }
            status, upload = _request(
                "/resume/upload", method="POST", headers=upload_headers, body=body
            )
            self.assertEqual(status, 200)
            self.assertIsInstance(upload, dict)
            self.assertEqual(upload.get("message"), "Resume uploaded successfully")
            self.assertIsInstance(upload.get("resume"), dict)
            resume_id = upload["resume"].get("id")
            self.assertIsInstance(resume_id, int)
            self.assertGreater(resume_id, 0)
            created_resume_ids.append(resume_id)

            status, resumes = _request("/resumes", headers=token_headers)
            self.assertEqual(status, 200)
            self.assertTrue(any(item.get("id") == resume_id for item in resumes))

            status, analysis = _request(
                f"/resume/{resume_id}/analysis", headers=token_headers
            )
            self.assertEqual(status, 200)
            self.assertEqual(analysis.get("resume_id"), resume_id)
            self.assertEqual(analysis.get("status"), "completed")
            self.assertEqual(analysis.get("extraction_status"), "success")
            self.assertIn("projects", analysis.get("sections", {}))
            self.assertGreater(analysis.get("page_count", 0), 0)

            empty_filename = f"road2hire-smoke-empty-{uuid.uuid4().hex}.pdf"
            empty_boundary, empty_body = _multipart(user_id, empty_filename, _create_pdf(""))
            empty_headers = {
                **token_headers,
                "Content-Type": f"multipart/form-data; boundary={empty_boundary}",
            }
            status, empty_upload = _request(
                "/resume/upload", method="POST", headers=empty_headers, body=empty_body
            )
            self.assertEqual(status, 200)
            empty_resume_id = empty_upload["resume"]["id"]
            self.assertIsInstance(empty_resume_id, int)
            created_resume_ids.append(empty_resume_id)

            status, failure = _request(
                f"/resume/{empty_resume_id}/analysis", headers=token_headers
            )
            self.assertEqual(status, 422)
            self.assertEqual(
                failure,
                {"detail": "This PDF contains no extractable text. OCR is required."},
            )
        finally:
            cleanup_failures = []
            for resume_id in created_resume_ids:
                status, _ = _request(
                    f"/resumes/{resume_id}", method="DELETE", headers=token_headers
                )
                if status != 200:
                    cleanup_failures.append(resume_id)
            if cleanup_failures:
                self.fail("Smoke test cleanup did not remove every created resume record.")


if __name__ == "__main__":
    unittest.main()
