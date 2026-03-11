from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ailocaltools.models import RequestEnvelope
from ailocaltools.validation import validate_device


class ValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_validate_device_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixtures = Path(temp_dir) / "fixtures"
            fixtures.mkdir()
            for name in [
                "clipboard_input.txt",
                "sample_notes.md",
                "embedded_text.pdf",
                "ocr_only.pdf",
                "screenshot.png",
                "photo.jpg",
                "archive.zip",
            ]:
                (fixtures / name).write_text(f"fixture:{name}", encoding="utf-8")
            report_path = Path(temp_dir) / "report.json"

            async def fake_handler(envelope: RequestEnvelope) -> dict:
                if envelope.type == "CheckEnvironment":
                    return {
                        "shell_supported": True,
                        "ai_supported": True,
                        "reason": "ok",
                        "os_version": "26.0",
                    }
                if envelope.type in {"SummarizeClipboard", "SummarizeFile"}:
                    return {
                        "title": "title",
                        "style": "bullets",
                        "length": "short",
                        "summary_text": "要約あり",
                        "source_kind": "text",
                        "created_at": "2026-03-11T00:00:00+00:00",
                    }
                if envelope.type == "ScanFolder":
                    path = Path(envelope.payload["path"])
                    suggestions = [
                        {
                            "source_path": str(item),
                            "target_folder_name": "Documents",
                            "is_new_folder": True,
                            "reason_ja": "分類",
                            "evidence_summary": "evidence",
                            "confidence": 0.8,
                        }
                        for item in sorted(path.iterdir())
                    ]
                    return {
                        "source_root": str(path),
                        "started_at": "2026-03-11T00:00:00+00:00",
                        "suggestions": suggestions,
                    }
                raise AssertionError(f"Unexpected envelope: {envelope.type}")

            def fake_ingest_path(path: Path) -> mock.Mock:
                target = Path(path)
                content = mock.Mock()
                if target.name in {"ocr_only.pdf", "screenshot.png"}:
                    content.text = "recognized text"
                else:
                    content.text = "text"
                content.evidence_summary = "evidence"
                return content

            with mock.patch("ailocaltools.validation.ingest_path", side_effect=fake_ingest_path):
                report = await validate_device(
                    report_path=report_path,
                    fixtures_dir=fixtures,
                    request_handler=fake_handler,
                )

            self.assertEqual(report.summary.failed, 0)
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["summary"]["passed"], saved["summary"]["total"])
            self.assertEqual(saved["environment"]["ai_supported"], True)

    async def test_validate_device_aggregates_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixtures = Path(temp_dir) / "fixtures"
            fixtures.mkdir()
            for name in [
                "clipboard_input.txt",
                "sample_notes.md",
                "embedded_text.pdf",
                "ocr_only.pdf",
                "screenshot.png",
                "photo.jpg",
                "archive.zip",
            ]:
                (fixtures / name).write_text(f"fixture:{name}", encoding="utf-8")
            report_path = Path(temp_dir) / "report.json"

            async def fake_handler(envelope: RequestEnvelope) -> dict:
                if envelope.type == "CheckEnvironment":
                    return {
                        "shell_supported": True,
                        "ai_supported": True,
                        "reason": "ok",
                        "os_version": "26.0",
                    }
                if envelope.type == "SummarizeFile" and envelope.payload["path"].endswith("photo.jpg"):
                    raise RuntimeError("image failure")
                if envelope.type in {"SummarizeClipboard", "SummarizeFile"}:
                    return {
                        "title": "title",
                        "style": "bullets",
                        "length": "short",
                        "summary_text": "要約あり",
                        "source_kind": "text",
                        "created_at": "2026-03-11T00:00:00+00:00",
                    }
                if envelope.type == "ScanFolder":
                    path = Path(envelope.payload["path"])
                    suggestions = [
                        {
                            "source_path": str(item),
                            "target_folder_name": "Documents",
                            "is_new_folder": True,
                            "reason_ja": "分類",
                            "evidence_summary": "evidence",
                            "confidence": 0.8,
                        }
                        for item in sorted(path.iterdir())
                    ]
                    return {
                        "source_root": str(path),
                        "started_at": "2026-03-11T00:00:00+00:00",
                        "suggestions": suggestions,
                    }
                raise AssertionError(f"Unexpected envelope: {envelope.type}")

            with mock.patch("ailocaltools.validation.ingest_path") as fake_ingest:
                fake_ingest.return_value = mock.Mock(text="recognized text", evidence_summary="evidence")
                report = await validate_device(
                    report_path=report_path,
                    fixtures_dir=fixtures,
                    request_handler=fake_handler,
                )

            self.assertGreater(report.summary.failed, 0)
            self.assertTrue(any(not item.ok for item in report.checks))
