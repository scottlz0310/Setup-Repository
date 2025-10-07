# Setup Repository Makefile
# プロジェクトルール準拠の統一コマンド群

.PHONY: bootstrap lint format typecheck test cov security build release clean
.PHONY: setup-dev quality-gate

# 🚀 開発環境セットアップ
bootstrap:
	@echo "🚀 開発環境をセットアップしています..."
	uv venv --python 3.13
	uv sync --dev
	uv run python scripts/setup-pre-commit.py
	@echo "✅ 開発環境のセットアップが完了しました"

# 🔧 開発依存関係セットアップ
setup-dev:
	@echo "🔧 開発依存関係をセットアップしています..."
	uv sync --dev
	uv run python scripts/setup-pre-commit.py
	@echo "✅ 開発依存関係のセットアップが完了しました"

# 🔍 リンティング
lint:
	@echo "🔍 コードリンティングを実行しています..."
	uv run ruff check .

# 🎨 フォーマッティング
format:
	@echo "🎨 コードフォーマッティングを実行しています..."
	uv run ruff format .

# 🔬 型チェック
typecheck:
	@echo "🔬 型チェックを実行しています..."
	uv run mypy src/

# 🧪 テスト実行
test:
	@echo "🧪 テストを実行しています..."
	uv run pytest -q

# ⚡ 高速テスト実行（Windows最適化）
test-fast:
	@echo "⚡ 高速テストを実行しています..."
	uv run python scripts/windows-fast-test.py

# 📊 カバレッジ測定
cov:
	@echo "📊 カバレッジ測定を実行しています..."
	uv run pytest --cov=src/setup_repo --cov-report=term-missing --cov-report=html --cov-report=xml



# 🛡️ セキュリティチェック
security:
	@echo "🛡️ セキュリティチェックを実行しています..."
	uv run python scripts/security-check.py

# 🏗️ ビルド
build:
	@echo "🏗️ パッケージをビルドしています..."
	uv build

# 🚀 リリース
release:
	@echo "🚀 リリースプロセスを開始しています..."
	@echo "タグ生成やリリースノート自動化をフック"

# 🧹 クリーンアップ
clean:
	@echo "🧹 クリーンアップを実行しています..."
	rm -rf .venv .cache .pytest_cache .ruff_cache .mypy_cache dist build htmlcov .coverage
	rm -rf coverage-artifacts coverage-reports
	rm -f coverage.xml coverage.json test-results.xml
	@echo "✅ クリーンアップが完了しました"

# 🎯 品質ゲート（統合）
quality-gate: lint typecheck test
	@echo "🎯 品質ゲートを実行しています..."
	@echo "✅ 全ての品質チェックが通過しました"

# 🧹 ブランチクリーンナップ
cleanup-branches-list:
	@echo "📋 リモートブランチ一覧を表示しています..."
	uv run main.py cleanup list

cleanup-branches-merged:
	@echo "🧹 マージ済みブランチをクリーンナップしています..."
	uv run main.py cleanup clean --merged --dry-run
	@echo "⚠️  実際に削除する場合は: make cleanup-branches-merged-confirm"

cleanup-branches-merged-confirm:
	@echo "🧹 マージ済みブランチを削除しています..."
	uv run main.py cleanup clean --merged -y

cleanup-branches-stale:
	@echo "🧹 古いブランチをクリーンナップしています（90日以上）..."
	uv run main.py cleanup clean --stale --days 90 --dry-run
	@echo "⚠️  実際に削除する場合は: make cleanup-branches-stale-confirm"

cleanup-branches-stale-confirm:
	@echo "🧹 古いブランチを削除しています（90日以上）..."
	uv run main.py cleanup clean --stale --days 90 -y

# ℹ️ ヘルプ
help:
	@echo "📋 利用可能なコマンド:"
	@echo ""
	@echo "🚀 開発環境:"
	@echo "  bootstrap      - 開発環境の初期セットアップ"
	@echo "  setup-dev      - 開発依存関係のセットアップ"
	@echo ""
	@echo "🔍 品質チェック:"
	@echo "  lint          - コードリンティング"
	@echo "  format        - コードフォーマッティング"
	@echo "  typecheck     - 型チェック"
	@echo "  test          - テスト実行"
	@echo "  test-fast     - 高速テスト実行（Windows最適化）"
	@echo "  cov           - カバレッジ測定"
	@echo "  security      - セキュリティチェック"
	@echo "  quality-gate  - 品質ゲート（統合）"
	@echo ""
	@echo "🧹 ブランチクリーンナップ:"
	@echo "  cleanup-branches-list           - リモートブランチ一覧表示"
	@echo "  cleanup-branches-merged         - マージ済みブランチ確認（dry-run）"
	@echo "  cleanup-branches-merged-confirm - マージ済みブランチ削除（実行）"
	@echo "  cleanup-branches-stale          - 古いブランチ確認（90日以上、dry-run）"
	@echo "  cleanup-branches-stale-confirm  - 古いブランチ削除（90日以上、実行）"
	@echo ""
	@echo "🏗️ ビルド・リリース:"
	@echo "  build         - パッケージビルド"
	@echo "  release       - リリース"
	@echo "  clean         - クリーンアップ"
	@echo ""
	@echo "ℹ️  ヘルプ:"
	@echo "  help          - このヘルプを表示"
