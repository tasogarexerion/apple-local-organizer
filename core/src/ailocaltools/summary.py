from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from .ingest import IngestedContent
from .models import SummaryResult

PROMPT_TEMPLATES = {
    "plain": (
        "Summarize the following text in clear Japanese. "
        "Keep factual details, remove repetition, and do not invent information."
    ),
    "bullets": (
        "Summarize the following text in Japanese bullet points. "
        "Keep the result compact, concrete, and easy to scan."
    ),
    "action-items": (
        "Read the following text and extract only actionable next steps in Japanese. "
        "If there are no clear actions, say so briefly. Do not invent tasks."
    ),
    "title-and-summary": (
        "Create a short Japanese title and then a concise Japanese summary for the following text. "
        "Do not add information not present in the text."
    ),
}

LENGTH_HINTS = {
    "short": "Target length: about 3 to 5 lines.",
    "medium": "Target length: about 6 to 10 lines.",
    "long": "Target length: about 10 to 16 lines.",
}


@dataclass(slots=True)
class SummaryConfig:
    style: str = "bullets"
    length: str = "short"
    system_prompt: str | None = None


class SummaryClient(Protocol):
    async def summarize(self, prompt: str) -> str: ...


class AppleFoundationModelClient:
    async def summarize(self, prompt: str) -> str:
        import apple_fm_sdk as fm  # type: ignore

        model = fm.SystemLanguageModel()
        available = model.is_available()
        if isinstance(available, tuple):
            ok = bool(available[0])
            reason = str(available[1]) if len(available) > 1 else ""
        else:
            ok = bool(available)
            reason = ""
        if not ok:
            raise RuntimeError(f"Foundation Models unavailable: {reason or 'unknown'}")

        session = fm.LanguageModelSession()
        response = await session.respond(prompt)
        return str(response).strip()


def build_prompt(text: str, cfg: SummaryConfig) -> str:
    base = PROMPT_TEMPLATES[cfg.style]
    length = LENGTH_HINTS[cfg.length]
    prompt_parts = [base, length]
    if cfg.system_prompt and cfg.system_prompt.strip():
        prompt_parts.append(f"Additional instruction: {cfg.system_prompt.strip()}")
    prompt_parts.append("Text:")
    prompt_parts.append(text.strip())
    return "\n\n".join(prompt_parts)


async def summarize_text(
    text: str,
    cfg: SummaryConfig,
    source_kind: str = "text",
    client: SummaryClient | None = None,
) -> SummaryResult:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Input is empty.")

    prompt = build_prompt(cleaned, cfg)
    summary_client = client or AppleFoundationModelClient()
    response = await summary_client.summarize(prompt)
    title = derive_title(cleaned, response, cfg.style)
    return SummaryResult(
        title=title,
        style=cfg.style,
        length=cfg.length,
        summary_text=response.strip(),
        source_kind=source_kind,
        created_at=_now_iso(),
    )


async def summarize_ingested(
    content: IngestedContent,
    cfg: SummaryConfig,
    client: SummaryClient | None = None,
) -> SummaryResult:
    text = content.text or content.evidence_summary
    return await summarize_text(
        text=text,
        cfg=cfg,
        source_kind=content.source_kind,
        client=client,
    )


async def generate_japanese_reason(
    evidence_summary: str,
    suggested_folder: str,
    client: SummaryClient | None = None,
) -> tuple[str, float]:
    prompt = "\n\n".join(
        [
            "You are helping organize files on macOS Finder.",
            "In Japanese, explain why the file should be grouped into the suggested folder.",
            "Reply with exactly two lines.",
            f"1行目: reason= ではじめる 50文字以内の説明。",
            "2行目: confidence=0.00-1.00 の数値。",
            f"suggested_folder={suggested_folder}",
            f"evidence={evidence_summary}",
        ]
    )
    summary_client = client or AppleFoundationModelClient()
    raw = await summary_client.summarize(prompt)
    reason = ""
    confidence = 0.6
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("reason="):
            reason = stripped.split("=", 1)[1].strip()
        elif stripped.startswith("confidence="):
            try:
                confidence = float(stripped.split("=", 1)[1].strip())
            except ValueError:
                confidence = 0.6
    if not reason:
        reason = f"{suggested_folder} にまとめる候補です。"
    return reason, max(0.0, min(confidence, 1.0))


def summarize_sync(
    text: str,
    cfg: SummaryConfig,
    source_kind: str = "text",
    client: SummaryClient | None = None,
) -> SummaryResult:
    return asyncio.run(summarize_text(text, cfg, source_kind=source_kind, client=client))


def derive_title(source_text: str, summary_text: str, style: str) -> str:
    if style == "title-and-summary":
        first = summary_text.splitlines()[0].strip()
        if first:
            return first[:60]
    source_first_line = next((line.strip() for line in source_text.splitlines() if line.strip()), "")
    if source_first_line:
        return source_first_line[:60]
    summary_first_line = next((line.strip() for line in summary_text.splitlines() if line.strip()), "")
    return summary_first_line[:60] or "Summary"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
