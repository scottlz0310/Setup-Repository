# Setup Repository - Makefile
# カバレッジ測定と品質チェック用のタスク

.PHONY: help test coverage coverage-report coverage-html coverage-check quality-gate quality-metrics quality-trend quality-report security security-scan security-sbom clean install dev-install version-check version-bump release

# デフォルトターゲット
help:
	@echo "📊 Setup Repository - カバレッジ & 品質チェック"
	@echo ""
	@echo "利用可能なコマンド:"
	@echo "  make install        - 本番依存関係をインストール"
	@echo "  make dev-install    - 開発依存関係をインストール"
	@echo "  make test           - テスト実行（基本）"
	@echo "  make coverage       - カバレッジ付きテスト実行"
	@echo "  make coverage-html  - HTMLカバレッジレポート生成"
	@echo "  make coverage-report - カバレッジレポート表示"
	@echo "  make coverage-check - カバレッジ品質ゲート実行"
	@echo "  make quality-gate   - 全品質チェック実行"
	@echo "  make quality-metrics - 品質メトリクス収集"
	@echo "  make quality-trend  - 品質トレンド分析"
	@echo "  make quality-report - 品質HTMLレポート生成"
	@echo "  make security       - 包括的セキュリティチェック"
	@echo "  make security-scan  - Safety脆弱性スキャン"
	@echo "  make security-sbom  - SBOM生成"
	@echo "  make version-check  - バージョン一貫性チェック"
	@echo "  make version-bump   - バージョン自動インクリメント"
	@echo "  make release        - リリース準備（品質チェック + バージョン確認）"
	@echo "  make clean          - 生成ファイルをクリーンアップ"
	@echo ""

# 依存関係インストール
install:
	@echo "📦 本番依存関係をインストール中..."
	uv sync

dev-install:
	@echo "📦 開発依存関係をインストール中..."
	uv sync --dev

# テスト実行
test:
	@echo "🧪 基本テスト実行中..."
	uv run pytest tests/ -v

# カバレッジ測定
coverage:
	@echo "📊 カバレッジ付きテスト実行中..."
	uv run pytest tests/ \
		--cov=src/setup_repo \
		--cov-report=term-missing \
		--cov-report=xml \
		--cov-report=json \
		--cov-fail-under=80 \
		-v

# HTMLカバレッジレポート生成
coverage-html:
	@echo "📊 HTMLカバレッジレポート生成中..."
	uv run pytest tests/ \
		--cov=src/setup_repo \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-fail-under=25 \
		-v
	@echo "✅ HTMLレポート生成完了: htmlcov/index.html"

# カバレッジレポート表示
coverage-report:
	@echo "📊 カバレッジレポート表示中..."
	uv run python scripts/coverage-check.py --report-only --min-coverage 80

# カバレッジ品質ゲート
coverage-check:
	@echo "🚀 カバレッジ品質ゲート実行中..."
	uv run python scripts/coverage-check.py --min-coverage 80

# 全品質チェック
quality-gate:
	@echo "🔍 全品質チェック実行中..."
	@echo "1️⃣ Ruffリンティング..."
	uv run ruff check . --fix
	@echo "2️⃣ Ruffフォーマッティング..."
	uv run ruff format .
	@echo "3️⃣ MyPy型チェック..."
	uv run mypy src/
	@echo "4️⃣ カバレッジ品質ゲート..."
	$(MAKE) coverage-check
	@echo "5️⃣ セキュリティチェック..."
	$(MAKE) security
	@echo "✅ 全品質チェック完了！"

# セキュリティチェック（ルール6章準拠）
security:
	@echo "🛡️ 包括的セキュリティチェック実行中..."
	@echo "1️⃣ Banditセキュリティ分析..."
	uv run bandit -r src/ -c pyproject.toml
	@echo "2️⃣ Safety脆弱性スキャン..."
	uv run safety scan --output screen
	@echo "3️⃣ ライセンス監査..."
	uv run pip-licenses --format=table
	@echo "✅ セキュリティチェック完了！"

# Safety脆弱性スキャン
security-scan:
	@echo "🔍 Safety脆弱性スキャン実行中..."
	uv run safety scan --output screen --detailed-output

# SBOM生成（ルール6.2準拠）
security-sbom:
	@echo "📋 SBOM生成中..."
	uv run python scripts/generate-sbom.py
	@echo "✅ SBOM生成完了: output/sbom_latest.json"

# 品質メトリクス収集
quality-metrics:
	@echo "📊 品質メトリクス収集中..."
	uv run python main.py quality --save-trend
	@echo "✅ 品質メトリクス収集完了"

# 品質トレンド分析
quality-trend:
	@echo "📈 品質トレンド分析中..."
	uv run python main.py trend analyze --days 30
	@echo "✅ 品質トレンド分析完了"

# 品質HTMLレポート生成
quality-report:
	@echo "📊 品質HTMLレポート生成中..."
	uv run python main.py trend report
	@echo "✅ 品質HTMLレポート生成完了: quality-trends/trend-report.html"

# クリーンアップ
clean:
	@echo "🧹 生成ファイルをクリーンアップ中..."
	rm -rf htmlcov/
	rm -f coverage.xml coverage.json .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf __pycache__/
	rm -rf quality-trends/
	rm -f quality-report.json
	rm -f test-report.json
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ クリーンアップ完了"

# 開発環境セットアップ
setup-dev: dev-install
	@echo "🔧 開発環境セットアップ中..."
	uv run pre-commit install
	@echo "✅ 開発環境セットアップ完了"

# CI/CD用タスク
ci-test:
	@echo "🤖 CI/CDテスト実行中..."
	uv run pytest tests/ \
		--cov=src/setup_repo \
		--cov-report=xml \
		--cov-report=term \
		--cov-fail-under=80 \
		--junit-xml=test-results.xml \
		-v

# カバレッジバッジ生成用
coverage-badge:
	@echo "🏷️ カバレッジバッジ情報生成中..."
	@COVERAGE=$$(uv run python -c "import json; print(f\"{json.load(open('coverage.json'))['totals']['percent_covered']:.0f}\")"); \
	if [ "$$COVERAGE" -ge 90 ]; then \
		COLOR="brightgreen"; \
	elif [ "$$COVERAGE" -ge 80 ]; then \
		COLOR="green"; \
	elif [ "$$COVERAGE" -ge 70 ]; then \
		COLOR="yellow"; \
	elif [ "$$COVERAGE" -ge 60 ]; then \
		COLOR="orange"; \
	else \
		COLOR="red"; \
	fi; \
	echo "カバレッジ: $$COVERAGE%"; \
	echo "バッジURL: https://img.shields.io/badge/coverage-$$COVERAGE%25-$$COLOR"# バージョン管理

version-check:
	@echo "🔍 バージョン一貫性チェック中..."
	uv run python scripts/version-manager.py --check

version-bump:
	@echo "📈 バージョン自動インクリメント"
	@echo "使用法: make version-bump TYPE=patch|minor|major|prerelease"
	@if [ -z "$(TYPE)" ]; then \
		echo "❌ TYPEパラメータが必要です"; \
		echo "例: make version-bump TYPE=patch"; \
		exit 1; \
	fi
	uv run python scripts/version-manager.py --bump $(TYPE)

# リリース準備
release:
	@echo "🚀 リリース準備中..."
	@echo "1️⃣ 品質チェック実行..."
	$(MAKE) quality-gate
	@echo "2️⃣ バージョン一貫性チェック..."
	$(MAKE) version-check
	@echo "3️⃣ SBOM生成..."
	$(MAKE) security-sbom
	@echo "4️⃣ ビルドテスト..."
	uv build
	@echo "✅ リリース準備完了！"
	@echo ""
	@echo "🏷️ リリースタグを作成するには:"
	@echo "  make version-bump TYPE=patch  # パッチバージョンアップ"
	@echo "  git push origin main"
	@echo "  git push origin --tags"
