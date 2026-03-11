from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from .bridge import handle_request
from .ingest import ingest_path
from .models import (
    EnvironmentStatus,
    RequestEnvelope,
    ValidationCheck,
    ValidationReport,
    ValidationSummary,
    to_dict,
)

RequestHandler = Callable[[RequestEnvelope], Awaitable[dict[str, Any]]]


async def validate_device(
    report_path: str | Path,
    fixtures_dir: str | Path,
    samples_dir: str | Path | None = None,
    request_handler: RequestHandler = handle_request,
) -> ValidationReport:
    fixtures = Path(fixtures_dir).expanduser().resolve()
    if not fixtures.exists():
        raise FileNotFoundError(f"Fixtures directory not found: {fixtures}")

    sample_root: Path | None = None
    if samples_dir:
        candidate = Path(samples_dir).expanduser().resolve()
        if candidate.exists():
            sample_root = candidate

    environment_data = await request_handler(RequestEnvelope(type="CheckEnvironment"))
    environment = EnvironmentStatus(**environment_data)
    report = ValidationReport(
        started_at=_now_iso(),
        environment=environment,
    )

    report.checks.append(await _run_clipboard_check(fixtures, request_handler))

    summary_targets = [
        ("sample_notes.md", "text"),
        ("embedded_text.pdf", "pdf"),
        ("ocr_only.pdf", "pdf"),
        ("screenshot.png", "image"),
        ("photo.jpg", "image"),
    ]
    for name, input_kind in summary_targets:
        report.checks.append(
            await _run_summary_file_check(fixtures / name, input_kind, request_handler)
        )

    report.checks.append(
        _run_ocr_coverage_check(
            [
                (fixtures / "ocr_only.pdf", "pdf-ocr"),
                (fixtures / "screenshot.png", "image-ocr"),
            ]
        )
    )
    report.checks.append(await _run_scan_check(fixtures, request_handler))

    if sample_root:
        for path in sorted(sample_root.iterdir()):
            if path.is_dir() or path.name.startswith("."):
                continue
            report.checks.append(
                await _run_summary_file_check(path, "sample", request_handler)
            )

    passed = sum(1 for check in report.checks if check.ok)
    failed = len(report.checks) - passed
    report.summary = ValidationSummary(
        total=len(report.checks),
        passed=passed,
        failed=failed,
    )

    target = Path(report_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(to_dict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def validate_device_sync(
    report_path: str | Path,
    fixtures_dir: str | Path,
    samples_dir: str | Path | None = None,
) -> ValidationReport:
    return asyncio.run(
        validate_device(
            report_path=report_path,
            fixtures_dir=fixtures_dir,
            samples_dir=samples_dir,
        )
    )


async def _run_clipboard_check(
    fixtures_dir: Path,
    request_handler: RequestHandler,
) -> ValidationCheck:
    fixture = fixtures_dir / "clipboard_input.txt"
    with _temporary_env({"APPLE_LOCAL_AI_CLIPBOARD_FILE": str(fixture)}):
        started = time.perf_counter()
        try:
            result = await request_handler(
                RequestEnvelope(
                    type="SummarizeClipboard",
                    payload={"style": "bullets", "length": "short"},
                )
            )
            summary_text = str(result.get("summary_text", "")).strip()
            ok = bool(summary_text)
            return ValidationCheck(
                name="summarize-clipboard",
                input_kind="clipboard",
                ok=ok,
                duration_ms=_duration_ms(started),
                details={"summary_length": len(summary_text)},
                error=None if ok else "Summary result was empty.",
            )
        except Exception as exc:
            return ValidationCheck(
                name="summarize-clipboard",
                input_kind="clipboard",
                ok=False,
                duration_ms=_duration_ms(started),
                details={},
                error=str(exc),
            )


async def _run_summary_file_check(
    path: Path,
    input_kind: str,
    request_handler: RequestHandler,
) -> ValidationCheck:
    started = time.perf_counter()
    try:
        result = await request_handler(
            RequestEnvelope(
                type="SummarizeFile",
                payload={
                    "path": str(path),
                    "style": "bullets",
                    "length": "short",
                },
            )
        )
        summary_text = str(result.get("summary_text", "")).strip()
        ok = bool(summary_text)
        return ValidationCheck(
            name=f"summarize-{path.name}",
            input_kind=input_kind,
            ok=ok,
            duration_ms=_duration_ms(started),
            details={"summary_length": len(summary_text)},
            error=None if ok else "Summary result was empty.",
        )
    except Exception as exc:
        return ValidationCheck(
            name=f"summarize-{path.name}",
            input_kind=input_kind,
            ok=False,
            duration_ms=_duration_ms(started),
            details={},
            error=str(exc),
        )


def _run_ocr_coverage_check(
    targets: list[tuple[Path, str]],
) -> ValidationCheck:
    started = time.perf_counter()
    details: dict[str, Any] = {"sources": {}}
    any_ok = False
    try:
        for path, input_kind in targets:
            content = ingest_path(path)
            extracted_text = content.text.strip()
            source_ok = bool(extracted_text)
            any_ok = any_ok or source_ok
            details["sources"][path.name] = {
                "input_kind": input_kind,
                "evidence_nonempty": source_ok,
                "evidence_length": len(extracted_text),
            }
        details["evidence_nonempty"] = any_ok
        return ValidationCheck(
            name="ocr-evidence-coverage",
            input_kind="ocr",
            ok=any_ok,
            duration_ms=_duration_ms(started),
            details=details,
            error=None
            if any_ok
            else "No OCR/extracted text was produced for OCR-only PDF or screenshot input.",
        )
    except Exception as exc:
        return ValidationCheck(
            name="ocr-evidence-coverage",
            input_kind="ocr",
            ok=False,
            duration_ms=_duration_ms(started),
            details=details,
            error=str(exc),
        )


async def _run_scan_check(
    fixtures_dir: Path,
    request_handler: RequestHandler,
) -> ValidationCheck:
    started = time.perf_counter()
    target_names = [
        "sample_notes.md",
        "embedded_text.pdf",
        "ocr_only.pdf",
        "screenshot.png",
        "photo.jpg",
        "archive.zip",
    ]
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir) / "scan-fixtures"
        temp_root.mkdir(parents=True, exist_ok=True)
        for name in target_names:
            shutil.copy2(fixtures_dir / name, temp_root / name)
        before = sorted(path.name for path in temp_root.iterdir())
        try:
            result = await request_handler(
                RequestEnvelope(
                    type="ScanFolder",
                    payload={"path": str(temp_root)},
                )
            )
        except Exception as exc:
            return ValidationCheck(
                name="scan-folder-fixtures",
                input_kind="organizer",
                ok=False,
                duration_ms=_duration_ms(started),
                details={},
                error=str(exc),
            )
        after = sorted(path.name for path in temp_root.iterdir())
        suggestions = result.get("suggestions", [])
        suggestion_count = len(suggestions)
        ok = suggestion_count == len(before) and before == after
        return ValidationCheck(
            name="scan-folder-fixtures",
            input_kind="organizer",
            ok=ok,
            duration_ms=_duration_ms(started),
            details={
                "input_count": len(before),
                "suggestion_count": suggestion_count,
                "target_folders": sorted(
                    {str(item.get("target_folder_name", "")) for item in suggestions}
                ),
                "directory_unchanged": before == after,
            },
            error=None
            if ok
            else "Organizer suggestions did not match input count or directory contents changed.",
        )


@contextmanager
def _temporary_env(values: dict[str, str]) -> Any:
    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            os.environ[key] = value
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def _duration_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
