import logging
from pathlib import Path
from uuid import uuid4


logger = logging.getLogger(__name__)
UPLOAD_DIRECTORY = Path(__file__).resolve().parents[1] / "uploads"


def get_resume_file_path(file_path: str) -> Path:
    resolved_path = Path(file_path).resolve()
    if resolved_path.parent != UPLOAD_DIRECTORY.resolve():
        raise ValueError("Resume file is outside the upload directory")
    return resolved_path


def save_resume_file(contents: bytes) -> tuple[str, str]:
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}.pdf"
    file_path = (UPLOAD_DIRECTORY / stored_name).resolve()
    try:
        file_path.write_bytes(contents)
    except OSError:
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove incomplete uploaded resume")
        raise
    return stored_name, str(file_path)


def remove_resume_file(file_path: str) -> None:
    get_resume_file_path(file_path).unlink(missing_ok=True)
