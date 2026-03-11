from __future__ import annotations

import mimetypes
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".rtf"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".heic"}


@dataclass(slots=True)
class IngestedContent:
    source_kind: str
    text: str
    evidence_summary: str
    metadata: dict[str, str] = field(default_factory=dict)


def read_clipboard() -> str:
    if os.getenv("APPLE_LOCAL_AI_CLIPBOARD_TEXT") is not None:
        return os.environ["APPLE_LOCAL_AI_CLIPBOARD_TEXT"]
    override_file = os.getenv("APPLE_LOCAL_AI_CLIPBOARD_FILE")
    if override_file:
        return Path(override_file).read_text(encoding="utf-8")
    result = subprocess.run(
        ["pbpaste"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def ingest_clipboard() -> IngestedContent:
    text = read_clipboard().strip()
    return IngestedContent(
        source_kind="clipboard",
        text=text,
        evidence_summary=f"クリップボード入力。文字数 {len(text)}。",
    )


def ingest_text(text: str, source_kind: str = "text") -> IngestedContent:
    cleaned = text.strip()
    return IngestedContent(
        source_kind=source_kind,
        text=cleaned,
        evidence_summary=f"{source_kind} 入力。文字数 {len(cleaned)}。",
    )


def ingest_path(path: str | Path) -> IngestedContent:
    target = Path(path).expanduser().resolve()
    if not target.exists():
        raise FileNotFoundError(f"Input file not found: {target}")

    suffix = target.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        text = target.read_text(encoding="utf-8", errors="ignore").strip()
        kind = "markdown" if suffix in {".md", ".markdown"} else "text"
        return IngestedContent(
            source_kind=kind,
            text=text,
            evidence_summary=_build_file_evidence(target, text),
            metadata=_basic_metadata(target),
        )
    if suffix in PDF_EXTENSIONS:
        text = _extract_pdf_text(target)
        return IngestedContent(
            source_kind="pdf",
            text=text.strip(),
            evidence_summary=_build_file_evidence(target, text),
            metadata=_basic_metadata(target),
        )
    if suffix in IMAGE_EXTENSIONS:
        extracted_text, labels = _extract_image_evidence(target)
        evidence = _build_image_evidence(target, extracted_text, labels)
        return IngestedContent(
            source_kind="image",
            text=extracted_text.strip(),
            evidence_summary=evidence,
            metadata=_basic_metadata(target),
        )

    mime, _ = mimetypes.guess_type(target.name)
    metadata = _basic_metadata(target)
    metadata["mime"] = mime or "application/octet-stream"
    return IngestedContent(
        source_kind="file",
        text="",
        evidence_summary=_build_file_evidence(target, "", fallback_only=True),
        metadata=metadata,
    )


def _basic_metadata(path: Path) -> dict[str, str]:
    stat = path.stat()
    return {
        "name": path.name,
        "suffix": path.suffix.lower(),
        "size_bytes": str(stat.st_size),
        "parent": str(path.parent),
    }


def _build_file_evidence(path: Path, text: str, fallback_only: bool = False) -> str:
    stat = path.stat()
    parts = [
        f"ファイル名: {path.name}",
        f"拡張子: {path.suffix.lower() or 'なし'}",
        f"サイズ: {stat.st_size} bytes",
    ]
    if text and not fallback_only:
        snippet = re.sub(r"\s+", " ", text).strip()[:240]
        parts.append(f"本文抜粋: {snippet}")
    return " / ".join(parts)


def _build_image_evidence(path: Path, extracted_text: str, labels: list[str]) -> str:
    parts = [
        f"ファイル名: {path.name}",
        f"拡張子: {path.suffix.lower()}",
    ]
    if labels:
        parts.append(f"画像ラベル: {', '.join(labels[:3])}")
    if extracted_text:
        snippet = re.sub(r"\s+", " ", extracted_text).strip()[:180]
        parts.append(f"OCR抜粋: {snippet}")
    if not labels and not extracted_text:
        parts.append("画像内容はメタデータのみ取得")
    return " / ".join(parts)


def _extract_pdf_text(path: Path) -> str:
    text = _extract_pdf_text_with_quartz(path)
    if text.strip():
        return text
    text = _extract_pdf_text_with_preview_ocr(path)
    if text.strip():
        return text
    text = _extract_pdf_text_with_strings(path)
    if text.strip():
        return text
    return ""


def _extract_pdf_text_with_quartz(path: Path) -> str:
    try:
        import Foundation  # type: ignore
        import Quartz  # type: ignore
    except Exception:
        return ""

    try:
        url = Foundation.NSURL.fileURLWithPath_(str(path))
        document = Quartz.PDFDocument.alloc().initWithURL_(url)
        if not document:
            return ""
        extracted = document.string() or ""
        return str(extracted)
    except Exception:
        return ""


def _extract_pdf_text_with_strings(path: Path) -> str:
    try:
        result = subprocess.run(
            ["strings", "-n", "5", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ""
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return "\n".join(lines[:60])


def _extract_pdf_text_with_preview_ocr(path: Path) -> str:
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            subprocess.run(
                [
                    "qlmanage",
                    "-t",
                    "-s",
                    "1600",
                    "-o",
                    str(output_dir),
                    str(path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            preview = next(output_dir.glob("*.png"), None)
            if not preview:
                return ""
            return _extract_image_text_with_vision(preview)
    except Exception:
        return ""


def _extract_image_evidence(path: Path) -> tuple[str, list[str]]:
    ocr_text = _extract_image_text_with_vision(path)
    labels = _classify_image_with_vision(path)
    return ocr_text, labels


def _extract_image_text_with_vision(path: Path) -> str:
    try:
        import Foundation  # type: ignore
        import Vision  # type: ignore
    except Exception:
        return ""

    try:
        request = Vision.VNRecognizeTextRequest.alloc().init()
        if hasattr(request, "setRecognitionLanguages_"):
            request.setRecognitionLanguages_(["ja-JP", "en-US"])
        if hasattr(request, "setUsesLanguageCorrection_"):
            request.setUsesLanguageCorrection_(True)
        url = Foundation.NSURL.fileURLWithPath_(str(path))
        handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, {})
        handler.performRequests_error_([request], None)
        results = request.results() or []
        collected: list[str] = []
        for item in results:
            candidates = item.topCandidates_(1)
            if candidates:
                collected.append(str(candidates[0].string()))
        return "\n".join(collected[:20])
    except Exception:
        return ""


def _classify_image_with_vision(path: Path) -> list[str]:
    try:
        import Foundation  # type: ignore
        import Vision  # type: ignore
    except Exception:
        return []

    try:
        request = Vision.VNClassifyImageRequest.alloc().init()
        url = Foundation.NSURL.fileURLWithPath_(str(path))
        handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, {})
        handler.performRequests_error_([request], None)
        results = request.results() or []
        labels: list[str] = []
        for item in results[:3]:
            identifier = item.identifier()
            if identifier:
                labels.append(str(identifier))
        return labels
    except Exception:
        return []
