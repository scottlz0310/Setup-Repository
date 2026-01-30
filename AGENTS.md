# リポジトリガイドライン

## プロジェクト構成とモジュール配置
- `src/setup_repo/`: アプリ本体。`cli/`（Typerコマンド）、`core/`（Git/GitHubロジック）、`models/`、`utils/`で構成。
- `tests/`: `unit/`、`integration/`、`fixtures/`（テストデータ）。
- `scripts/`: 開発用自動化（セットアップ、セキュリティチェックなど）。
- `docs/`: ドキュメント関連。
- `output/`: 生成物（カバレッジHTML/XML）。

## ビルド・テスト・開発コマンド
- `uv sync --dev`: 開発依存関係のインストール。
- `uv run python scripts/setup-dev-environment.py`: まとめて開発環境をセットアップ（推奨）。
- `uv run ruff check .` / `uv run ruff format .`: リントとフォーマット。
- `uv run basedpyright src/`: strict型チェック。
- `uv run pytest` / `uv run pytest -n auto`: テスト実行（並列はxdist）。
- `uv run pytest --cov=src/setup_repo`: カバレッジ測定（HTMLは`output/htmlcov`）。
- `make quality-gate` / `make build` / `make security`: 統合チェック、ビルド、セキュリティ検査。

## コーディングスタイルと命名規約
- Python 3.11+、インデントは4スペース、最大行長は120文字。
- 命名: ファイル/関数/変数は`snake_case`、クラスは`PascalCase`、定数は`UPPER_SNAKE_CASE`、非公開は`_leading_underscore`。
- 関数の引数・戻り値に型ヒント必須。BasedPyrightはstrictで実行。
- `ruff format`（ダブルクオート）を使用し、`print`は避けて構造化ログを使う。

## テスト指針
- 使用: `pytest`、`pytest-cov`、`pytest-xdist`。
- カバレッジ最低基準: `src/setup_repo/`で80%。
- 命名: `test_*.py`、関数は`test_*`。マーカーは`unit`、`integration`、`slow`。
- ロジックはunit、ファイル/Git操作はintegration中心で追加。

## コミットとプルリクエスト
- 形式はConventional Commit系: `type: summary`（例: `chore(deps-python): update dependency rich`）。
- 主なtype: `feat`、`fix`、`docs`、`style`、`refactor`、`test`、`chore`。
- PRは概要とテスト結果を明記し、重要変更は`CHANGELOG.md`を更新。関連Issueは`Fixes #123`でリンク。

## セキュリティと設定
- `config.json.template`を`config.local.json`にコピーしてローカル設定を作成（秘密情報はコミットしない）。
- セキュリティチェックは`make security`または`uv run python scripts/security-check.py`。

## エージェント向け指示
- 応答は日本語のみで行うこと。
- 作業完了時は必ず`uv run pre-commit run --all-files`を実行し、品質を担保すること。
