from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ailocaltools.organizer import build_reason, scan_folder, suggest_folder_name


class OrganizerTests(unittest.TestCase):
    def test_suggest_folder_name(self) -> None:
        folder = suggest_folder_name(
            Path("/tmp/receipt.pdf"),
            "ファイル名: receipt.pdf / 本文抜粋: Invoice from Apple Store",
        )
        self.assertEqual(folder, "Receipts")

    def test_build_reason(self) -> None:
        reason, confidence = build_reason(Path("/tmp/archive.zip"), "Installers", "zip")
        self.assertIn("Installers", reason)
        self.assertGreater(confidence, 0.5)

    def test_scan_folder_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "スクリーンショット.png"
            target.write_text("fake image", encoding="utf-8")
            before = set(path.name for path in root.iterdir())
            run = scan_folder(root)
            after = set(path.name for path in root.iterdir())
            self.assertEqual(before, after)
            self.assertEqual(run.suggestions[0].target_folder_name, "Screenshots")
