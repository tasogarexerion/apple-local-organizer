# Apple Local Organizer

Apple Intelligence の Foundation Models を使ったローカル要約と Finder 整理提案の実験プロジェクトです。

GitHub にはソースコードだけでも公開できます。Developer ID 署名や notarization が未完了でも、`ad-hoc` 署名または未署名の開発者向けプレビューとして DMG を公開できます。

公開時の実務手順は [PUBLISHING.md](/Users/taso/開発/オンデバイスAI/PUBLISHING.md) にまとめています。

## License

このリポジトリのソースコードは [MIT License](/Users/taso/開発/オンデバイスAI/LICENSE) です。
ただし、Apple の SDK・フレームワーク・同梱しない外部 runtime にはそれぞれの利用条件が適用されます。

## 構成

- `core/`: Python コア。要約、環境判定、取り込み、整理提案、履歴管理、JSON ブリッジを含みます。
- `shell/`: SwiftUI/AppKit のメニューバーシェル。Python コアを subprocess で呼びます。
- `fixtures/`: テスト用のサンプル生成スクリプトと生成先。
- `release/`: 直配布用ビルドと notarization の雛形スクリプト。

## 開発用の最短手順

```bash
python3 fixtures/generate_fixtures.py
PYTHONPATH=core/src python3 -m unittest discover -s core/tests -v
swift build --package-path shell
```

この環境では `swift test` が使えないことがあるため、最小確認は `swift build` を基準にしています。

## CLI 例

```bash
PYTHONPATH=core/src python3 -m ailocaltools.cli check-environment
PYTHONPATH=core/src python3 -m ailocaltools.cli summarize-clipboard
PYTHONPATH=core/src python3 -m ailocaltools.cli summarize-file fixtures/generated/sample_notes.md
PYTHONPATH=core/src python3 -m ailocaltools.cli scan-folder ~/Downloads
PYTHONPATH=core/src python3 -m ailocaltools.cli list-recent
PYTHONPATH=core/src python3 -m ailocaltools.cli validate-device --report validation/reports/device-report.json
```

`apple-fm-sdk` が使えない環境では、シェルは互換モードになり、AI 機能は無効として扱います。
Foundation Models / Vision の実機検証は、通常の Terminal か sandbox 外の実行環境で行ってください。

## 配布フロー

```bash
release/build_app.sh
DEVELOPER_ID_APP_HASH="<40 hex sha1>" release/sign_app.sh
release/package_dmg.sh
NOTARY_PROFILE="<profile>" TEAM_ID="<team>" release/notarize_app.sh --artifact release/build/AppleLocalOrganizer.dmg
release/staple_dmg.sh release/build/AppleLocalOrganizer.dmg
```

同梱 Python ランタイムは `vendor/python-runtime/macos-arm64/` に配置します。
この runtime は `apple_fm_sdk` と PyObjC 依存を含む relocatable な CPython を前提にします。
署名名を露出したくない場合は `DEVELOPER_ID_APP` ではなく `DEVELOPER_ID_APP_HASH` を使えます。

## GitHub 公開の進め方

### 1. ソースコードだけ先に公開する

- 署名や notarization は不要です。
- `vendor/python-runtime/`、`release/build/`、`validation/reports/` のような生成物やローカル依存物はコミットしません。
- GitHub Actions では `.github/workflows/ci.yml` が fixture 生成、Python テスト、Swift build を実行します。

### 2. 開発者向けプレビュー DMG を公開する

- Developer ID がなくても `DEVELOPER_ID_APP=- release/sign_app.sh` で ad-hoc 署名できます。
- その後 `release/package_dmg.sh` で DMG を作り、`release/prepare_github_release.sh` で GitHub Releases 用の説明文と SHA-256 を生成します。
- この配布物は Gatekeeper の警告が出る前提です。一般ユーザー向けの正式配布には向きません。

### 2.5. 公開前チェックを回す

- `scripts/public_release_check.sh` で秘密情報の簡易検査、サイズ検査、fixture 生成、Python テスト、Swift build、Release Notes 生成確認をまとめて実行できます。

### 3. 一般公開に切り替える

- Developer ID 署名と notarization が用意できたら、同じ release フローで差し替えできます。
- その場合は GitHub Releases 側の説明文だけ更新すれば足ります。
