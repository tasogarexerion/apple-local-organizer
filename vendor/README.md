# Vendor Assets

同梱する Python ランタイムは `vendor/python-runtime/macos-arm64/` に配置します。

- `bin/python3`
- `lib/`
- `Frameworks/` または relocatable に必要な共有ライブラリ
- `lib/python3.12/site-packages/` に `apple_fm_sdk` と PyObjC (`Foundation`, `Quartz`, `Vision` など)

このディレクトリ自体は配布時の入力であり、リポジトリには通常コミットしません。
Homebrew の単純コピーは開発確認には使えても、完全な standalone 配布用 runtime としては不十分な場合があります。直配布用には relocatable な CPython 一式を前提にしてください。
