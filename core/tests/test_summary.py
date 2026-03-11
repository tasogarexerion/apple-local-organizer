from __future__ import annotations

import unittest

from ailocaltools.summary import SummaryConfig, build_prompt, derive_title, summarize_text


class FakeClient:
    async def summarize(self, prompt: str) -> str:
        return "タイトル\n- 要点1\n- 要点2"


class SummaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_prompt(self) -> None:
        cfg = SummaryConfig(style="bullets", length="short", system_prompt="Focus on actions")
        prompt = build_prompt("hello", cfg)
        self.assertIn("Focus on actions", prompt)
        self.assertIn("Target length", prompt)

    async def test_summarize_text(self) -> None:
        result = await summarize_text(
            "会議メモです",
            SummaryConfig(style="title-and-summary", length="short"),
            client=FakeClient(),
        )
        self.assertEqual(result.title, "タイトル")
        self.assertEqual(result.style, "title-and-summary")

    async def test_derive_title(self) -> None:
        title = derive_title("first line\nsecond", "- summary", "bullets")
        self.assertEqual(title, "first line")
