from __future__ import annotations

import platform
from typing import Callable

from .models import EnvironmentStatus

MIN_SHELL_MACOS_MAJOR = 15
MIN_AI_MACOS_MAJOR = 26


def parse_macos_major(version: str) -> int:
    if not version:
        return 0
    try:
        return int(version.split(".")[0])
    except (TypeError, ValueError):
        return 0


def current_macos_version() -> str:
    return platform.mac_ver()[0] or platform.platform()


def shell_supported(version: str | None = None) -> bool:
    return parse_macos_major(version or current_macos_version()) >= MIN_SHELL_MACOS_MAJOR


def ai_os_supported(version: str | None = None) -> bool:
    return parse_macos_major(version or current_macos_version()) >= MIN_AI_MACOS_MAJOR


def check_environment(
    version_provider: Callable[[], str] = current_macos_version,
) -> EnvironmentStatus:
    version = version_provider()
    if not shell_supported(version):
        return EnvironmentStatus(
            shell_supported=False,
            ai_supported=False,
            reason="macOS 15 以上が必要です。",
            os_version=version,
        )

    if not ai_os_supported(version):
        return EnvironmentStatus(
            shell_supported=True,
            ai_supported=False,
            reason="互換シェルのみ利用できます。AI 機能は macOS 26 以上で有効です。",
            os_version=version,
        )

    try:
        import apple_fm_sdk as fm  # type: ignore
    except ImportError:
        return EnvironmentStatus(
            shell_supported=True,
            ai_supported=False,
            reason="apple-fm-sdk が見つからないため AI 機能を有効化できません。",
            os_version=version,
        )

    try:
        model = fm.SystemLanguageModel()
        available = model.is_available()
    except Exception as exc:
        return EnvironmentStatus(
            shell_supported=True,
            ai_supported=False,
            reason=f"Foundation Models の確認に失敗しました: {exc}",
            os_version=version,
        )

    if isinstance(available, tuple):
        is_available = bool(available[0])
        reason = str(available[1]) if len(available) > 1 else ""
    else:
        is_available = bool(available)
        reason = ""

    if not is_available:
        return EnvironmentStatus(
            shell_supported=True,
            ai_supported=False,
            reason=f"Apple Intelligence を利用できません: {reason or '利用不可'}",
            os_version=version,
        )

    return EnvironmentStatus(
        shell_supported=True,
        ai_supported=True,
        reason="AI 機能を利用できます。",
        os_version=version,
    )
