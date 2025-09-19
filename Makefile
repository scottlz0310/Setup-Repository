# Setup Repository Makefile
# プロジェクトルール準拠の統一コマンド群

.PHONY: bootstrap lint format typecheck test cov security build release clean
.PHONY: merge-coverage setup-dev quality-gate

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

# 🔄 統合カバレッジ（ローカル開発用）
merge-coverage:
	@echo "🔄 統合カバレッジ処理を実行しています..."
	@if [ -d "coverage-artifacts" ]; then \
		uv run python scripts/merge-coverage.py --coverage-dir coverage-artifacts --verbose; \
	else \
		echo "⚠️ coverage-artifactsディレクトリが見つかりません"; \
		echo "ℹ️ 各プラットフォームでテストを実行してからこのコマンドを使用してください"; \
	fi

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
	rm -rf coverage-artifacts merged-coverage coverage-reports
	rm -f coverage.xml coverage.json test-results.xml coverage-merge.log
	@echo "✅ クリーンアップが完了しました"

# 🎯 品質ゲート（統合）
quality-gate: lint typecheck test
	@echo "🎯 品質ゲートを実行しています..."
	@echo "✅ 全ての品質チェックが通過しました"

# ℹ️ ヘルプ
help:
	@echo "📋 利用可能なコマンド:"
	@echo "  bootstrap      - 開発環境の初期セットアップ"
	@echo "  setup-dev      - 開発依存関係のセットアップ"
	@echo "  lint          - コードリンティング"
	@echo "  format        - コードフォーマッティング"
	@echo "  typecheck     - 型チェック"
	@echo "  test          - テスト実行"
	@echo "  test-fast     - 高速テスト実行（Windows最適化）"
	@echo "  cov           - カバレッジ測定"
	@echo "  merge-coverage - 統合カバレッジ処理"
	@echo "  security      - セキュリティチェック"
	@echo "  build         - パッケージビルド"
	@echo "  release       - リリース"
	@echo "  clean         - クリーンアップ"
	@echo "  quality-gate  - 品質ゲート（統合）"
	@echo "  help          - このヘルプを表示"
