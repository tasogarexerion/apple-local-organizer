from __future__ import annotations

import unittest
from unittest import mock

from ailocaltools.environment import ai_os_supported, check_environment, parse_macos_major, shell_supported


class EnvironmentTests(unittest.TestCase):
    def test_parse_macos_major(self) -> None:
        self.assertEqual(parse_macos_major("26.0"), 26)
        self.assertEqual(parse_macos_major(""), 0)

    def test_shell_supported(self) -> None:
        self.assertTrue(shell_supported("15.0"))
        self.assertFalse(shell_supported("14.9"))

    def test_ai_os_supported(self) -> None:
        self.assertTrue(ai_os_supported("26.1"))
        self.assertFalse(ai_os_supported("25.9"))

    def test_check_environment_reports_shell_only(self) -> None:
        status = check_environment(version_provider=lambda: "15.0")
        self.assertTrue(status.shell_supported)
        self.assertFalse(status.ai_supported)
        self.assertIn("macOS 26", status.reason)

    def test_check_environment_missing_sdk(self) -> None:
        with mock.patch("builtins.__import__", side_effect=ImportError):
            status = check_environment(version_provider=lambda: "26.0")
        self.assertTrue(status.shell_supported)
        self.assertFalse(status.ai_supported)
