import json
import logging
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from AI.Pipeline import (  # noqa: E402
    OccupationSelectionError,
    ResumeValidationError,
    process_resume,
)
from Core.database import SessionLocal  # noqa: E402
from Models.pipeline_run import PipelineRun  # noqa: E402
from Models.resume import Resume  # noqa: E402
from Models.skill_gap import SkillGap  # noqa: E402
from Models.user import User  # noqa: E402
from Services.file_service import UPLOAD_DIRECTORY  # noqa: E402


logger = logging.getLogger(__name__)
_WINDOWS_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/](?:[^\\/\s\"'<>|]+[\\/])*[^\\/\s\"'<>|]*"
    r"|\\\\[^\\/\s\"'<>|]+[\\/][^\\/\s\"'<>|]+(?:[\\/][^\\s\"'<>|]*)*)"
)
_POSIX_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9:/])/(?!/)[^\s\"'<>]+"
)
_FILE_URL_PATTERN = re.compile(r"\bfile:(?://)?[^\s\"'<>]+", re.IGNORECASE)


class ResumeOwnershipError(ValueError):
    """Raised when a resume does not belong to the supplied user."""


class ResumeFileValidationError(ValueError):
    """Raised when a resume path is invalid or outside the upload directory."""


def run_pipeline_for_resume(
    user: User,
    resume: Resume,
    target_occupation: str | None = None,
    *,
    auto_select_top_occupation: bool = False,
) -> PipelineRun:
    """Run the unified pipeline and persist its result independently of API transactions."""
    user_id = user.id
    resume_id = resume.id

    creation_session = SessionLocal()
    run_id: int | None = None
    start_error: Exception | None = None
    try:
        owned_resume = (
            creation_session.query(Resume)
            .filter(Resume.id == resume_id, Resume.user_id == user_id)
            .first()
        )
        if owned_resume is None:
            raise ResumeOwnershipError(
                "Resume does not belong to the authenticated user."
            )

        resume_path = _validate_resume_path(owned_resume.file_path)
        safe_original_name = _safe_filename(owned_resume.original_name)
        run = PipelineRun(
            user_id=user_id,
            resume_id=resume_id,
            selection_mode=(
                "auto_selected"
                if target_occupation is None and auto_select_top_occupation
                else "explicit"
            ),
            status="pending",
        )
        creation_session.add(run)
        creation_session.flush()
        run_id = run.id
        creation_session.commit()

        run.status = "running"
        creation_session.commit()
    except Exception as exc:
        creation_session.rollback()
        if run_id is None:
            raise
        logger.exception(
            "Could not start pipeline run %s",
            run_id,
        )
        start_error = exc
    finally:
        creation_session.close()

    if start_error is not None:
        assert run_id is not None
        code, stage, message = _exception_failure(start_error)
        try:
            return _persist_failure(
                run_id,
                error_code=code,
                error_stage=stage,
                error_message=message,
            )
        except Exception as exc:
            logger.exception(
                "Could not persist failed pipeline run %s after startup error",
                run_id,
            )
            raise RuntimeError(
                f"Could not persist pipeline run {run_id} failure state."
            ) from exc

    try:
        result = process_resume(
            resume_path=resume_path,
            target_occupation=target_occupation,
            auto_select_top_occupation=auto_select_top_occupation,
            output_format="none",
        )
        canonical_output = result.to_canonical_dict()
        if not isinstance(canonical_output, dict):
            raise TypeError("Pipeline returned a non-object canonical result.")

        canonical_output = _sanitize_canonical_output(
            canonical_output,
            safe_original_name,
            resume_path,
        )
        json.dumps(canonical_output, allow_nan=False)
        metadata = _mapping(canonical_output.get("metadata"))
        pipeline_status = metadata.get("status")
        if pipeline_status not in {"success", "warning", "error"}:
            raise ValueError("Pipeline returned an unsupported result status.")

        if pipeline_status == "error":
            error = _structured_error(canonical_output)
            return _persist_failure(
                run_id,
                error_code=error[0],
                error_stage=error[1],
                error_message=error[2],
                canonical_output=canonical_output,
            )

        return _persist_success(
            run_id,
            canonical_output,
            safe_original_name,
        )
    except Exception as exc:
        logger.exception("Unified pipeline execution failed for run %s", run_id)
        code, stage, message = _exception_failure(exc)
        return _persist_failure(
            run_id,
            error_code=code,
            error_stage=stage,
            error_message=message,
        )


def get_pipeline_output_section(
    run: PipelineRun,
    section: str,
) -> Any | None:
    """Return one top-level section from a run's canonical output, if present."""
    if not isinstance(run.canonical_output, dict):
        return None
    return run.canonical_output.get(section)


def _persist_success(
    run_id: int,
    canonical_output: dict[str, Any],
    original_name: str,
) -> PipelineRun:
    session = SessionLocal()
    try:
        run = session.query(PipelineRun).filter(PipelineRun.id == run_id).one()
        run.canonical_output = canonical_output
        metadata = _mapping(canonical_output.get("metadata"))
        run.pipeline_version = _string_or_default(
            metadata.get("pipeline_version"),
            run.pipeline_version,
        )
        run.schema_version = _string_or_default(
            canonical_output.get("schema_version")
            or metadata.get("schema_version"),
            run.schema_version,
        )
        _populate_run_summary(run, canonical_output)

        _add_skill_gap_summary(session, run, canonical_output)
        session.flush()

        run.status = "completed"
        run.error_code = None
        run.error_stage = None
        run.error_message = None
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        return _detach_committed_run(session, run)
    except Exception:
        session.rollback()
        logger.exception("Could not persist successful pipeline run %s", run_id)
        raise
    finally:
        session.close()


def _persist_failure(
    run_id: int,
    *,
    error_code: str,
    error_stage: str,
    error_message: str,
    canonical_output: dict[str, Any] | None = None,
) -> PipelineRun:
    session = SessionLocal()
    try:
        run = session.query(PipelineRun).filter(PipelineRun.id == run_id).one()
        _set_run_failure(
            run,
            error_code,
            error_stage,
            error_message,
            canonical_output,
        )
        session.query(SkillGap).filter(SkillGap.pipeline_run_id == run_id).delete(
            synchronize_session=False
        )
        session.commit()
        return _detach_committed_run(session, run)
    except Exception:
        session.rollback()
        logger.exception("Could not persist failed pipeline run %s", run_id)
        raise
    finally:
        session.close()


def _detach_committed_run(session: Session, run: PipelineRun) -> PipelineRun:
    session.refresh(run)
    session.expunge(run)
    return run


def _populate_run_summary(
    run: PipelineRun,
    canonical_output: dict[str, Any],
) -> None:
    target = _mapping(canonical_output.get("target_occupation"))
    skill_gap = _mapping(canonical_output.get("skill_gap"))
    gap_target = _mapping(skill_gap.get("target_occupation"))
    readiness = _mapping(canonical_output.get("readiness"))

    run.target_occupation_uri = _string_or_none(
        target.get("occupation_uri") or gap_target.get("uri")
    )
    run.target_occupation_title = _string_or_none(
        target.get("occupation_label") or gap_target.get("preferred_label")
    )
    run.overall_skill_coverage_score = _number_or_none(
        skill_gap.get("overall_skill_coverage_score")
    )
    run.essential_skill_coverage_score = _number_or_none(
        skill_gap.get("essential_skill_coverage_score")
    )
    run.optional_skill_coverage_score = _number_or_none(
        skill_gap.get("optional_skill_coverage_score")
    )
    run.readiness_class = _string_or_none(readiness.get("predicted_class"))
    is_ood = readiness.get("is_ood")
    run.is_ood = is_ood if isinstance(is_ood, bool) else False


def _add_skill_gap_summary(
    session: Session,
    run: PipelineRun,
    canonical_output: dict[str, Any],
) -> None:
    gap = _mapping(canonical_output.get("skill_gap"))
    target = _mapping(gap.get("target_occupation"))
    canonical_target = _mapping(canonical_output.get("target_occupation"))
    uri = _string_or_none(
        canonical_target.get("occupation_uri") or target.get("uri")
    )
    title = _string_or_none(
        canonical_target.get("occupation_label") or target.get("preferred_label")
    )
    overall_score = _number_or_none(gap.get("overall_skill_coverage_score"))
    essential_score = _number_or_none(gap.get("essential_skill_coverage_score"))
    optional_score = _number_or_none(gap.get("optional_skill_coverage_score"))
    matching_summary = _mapping(gap.get("matching_summary"))

    counts = (
        _nonnegative_count(matching_summary.get("matched_skills_count")),
        _nonnegative_count(matching_summary.get("missing_essential_skills_count")),
        _nonnegative_count(matching_summary.get("missing_optional_skills_count")),
    )
    if (
        uri is None
        or title is None
        or overall_score is None
        or essential_score is None
        or optional_score is None
        or any(count is None for count in counts)
    ):
        return

    session.add(
        SkillGap(
            pipeline_run_id=run.id,
            target_occupation_uri=uri,
            target_occupation_title=title,
            overall_skill_coverage_score=overall_score,
            essential_skill_coverage_score=essential_score,
            optional_skill_coverage_score=optional_score,
            matched_skill_count=counts[0],
            missing_essential_skill_count=counts[1],
            missing_optional_skill_count=counts[2],
        )
    )


def _set_run_failure(
    run: PipelineRun,
    error_code: str,
    error_stage: str,
    error_message: str,
    canonical_output: dict[str, Any] | None,
) -> None:
    run.status = "failed"
    run.target_occupation_uri = None
    run.target_occupation_title = None
    run.overall_skill_coverage_score = None
    run.essential_skill_coverage_score = None
    run.optional_skill_coverage_score = None
    run.readiness_class = None
    run.is_ood = False
    run.error_code = error_code
    run.error_stage = error_stage
    run.error_message = error_message
    run.completed_at = None
    run.canonical_output = canonical_output or {
        "schema_version": run.schema_version,
        "status": "error",
        "error": {
            "code": error_code,
            "message": error_message,
            "stage": error_stage,
        },
    }


def _structured_error(
    canonical_output: dict[str, Any],
) -> tuple[str, str, str]:
    errors = canonical_output.get("errors")
    messages = (
        [_safe_error_text(item) for item in errors]
        if isinstance(errors, list)
        else []
    )
    message = "; ".join(item for item in messages if item)[:4000]
    return "PIPELINE_RESULT_ERROR", "pipeline_execution", (
        message or "Pipeline returned an error result."
    )


def _exception_failure(exc: Exception) -> tuple[str, str, str]:
    if isinstance(exc, OccupationSelectionError):
        return (
            "OCCUPATION_SELECTION_REQUIRED",
            "occupation_resolution",
            "A valid target occupation is required.",
        )
    if isinstance(exc, ResumeValidationError):
        code = (
            "RESUME_NOT_FOUND"
            if "not found" in str(exc).casefold()
            else "RESUME_PARSE_FAILED"
        )
        message = (
            "Resume file was not found."
            if code == "RESUME_NOT_FOUND"
            else "The resume could not be processed."
        )
        return code, "input_validation", message
    return (
        "PIPELINE_EXECUTION_ERROR",
        "pipeline_execution",
        "Pipeline execution failed.",
    )


def _validate_resume_path(file_path: str) -> Path:
    try:
        upload_root = UPLOAD_DIRECTORY.resolve(strict=True)
        resolved_path = Path(file_path).resolve(strict=True)
        resolved_path.relative_to(upload_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ResumeFileValidationError(
            "Resume file path is invalid or outside the upload directory."
        ) from exc

    if not resolved_path.is_file():
        raise ResumeFileValidationError(
            "Resume path does not identify a regular file."
        )
    return resolved_path


def _safe_filename(filename: str) -> str:
    return Path(PureWindowsPath(filename).name).name or "resume.pdf"


def _sanitize_canonical_output(
    canonical_output: dict[str, Any],
    original_name: str,
    resume_path: Path,
) -> dict[str, Any]:
    sanitized = _sanitize_value(
        canonical_output,
        original_name=original_name,
        resume_path=resume_path,
    )
    metadata = _mapping(sanitized.get("metadata"))
    metadata["source_file"] = original_name
    sanitized["metadata"] = metadata
    return sanitized


def _sanitize_value(
    value: Any,
    *,
    original_name: str,
    resume_path: Path,
) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize_value(
                item,
                original_name=original_name,
                resume_path=resume_path,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _sanitize_value(
                item,
                original_name=original_name,
                resume_path=resume_path,
            )
            for item in value
        ]
    if not isinstance(value, str):
        return value

    sanitized = value.replace(str(resume_path), original_name)
    sanitized = _FILE_URL_PATTERN.sub("[local path]", sanitized)
    sanitized = _WINDOWS_PATH_PATTERN.sub("[local path]", sanitized)
    return _POSIX_PATH_PATTERN.sub("[local path]", sanitized)


def _safe_error_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _nonnegative_count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _string_or_default(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value else default
