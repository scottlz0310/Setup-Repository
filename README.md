# 🚀 リポジトリセットアップツール

[![Coverage](https://img.shields.io/badge/coverage-90.35%25-brightgreen)](htmlcov/index.html)
[![Tests](https://github.com/scottlz0310/Setup-Repository/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/scottlz0310/Setup-Repository/actions)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Quality](https://img.shields.io/badge/quality-CI%2FCD%20Ready-brightgreen)](https://github.com/scottlz0310/Setup-Repository)

クロスプラットフォーム対応のGitHubリポジトリセットアップ・同期ツールです。包括的なコード品質管理、CI/CDパイプライン、自動依存関係管理を統合しています。

## 📦 推奨: モダンパッケージマネージャーでuvをインストール

**Linux/WSL:**
```bash
sudo snap install --classic uv
```

**Windows:**
```powershell
# pipxを使用（推奨）
pipx install uv

# またはcurlでインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# またはwinget
winget install astral-sh.uv
```

## 🏃‍♂️ クイックスタート

### 方法1: グローバルツールとしてインストール（推奨）

```bash
# インストール
uv tool install git+https://github.com/scottlz0310/Setup-Repository.git

# 任意のリポジトリで使用可能
cd /path/to/any/repository
setup-repo cleanup list --merged
setup-repo cleanup clean --merged --dry-run
```

> ℹ️ v1.4.4以降、`uv tool install` で導入するCLIにも `.gitignore`/`.vscode` テンプレートが同梱されるため、グローバル環境からでもテンプレート同期が確実に適用されます。

### 方法2: ローカル開発

1. **初期セットアップ**
   ```bash
   uv run main.py setup
   ```

2. **設定の編集**
   ```bash
   # 必要に応じて個人設定を編集
   nano config.local.json
   ```

3. **リポジトリ同期実行**
   ```bash
   uv run main.py sync
   # 実行内容確認
   uv run main.py sync --dry-run
   ```

## ⚙️ 設定ファイル

- `config.json.template` - 設定テンプレート（リポジトリで管理）
- `config.local.json` - 個人設定（gitで除外）

## 🚀 リリース管理

このプロジェクトは自動化されたリリース管理システムを採用しています：

### 📋 リリース手順

```bash
# 1. 品質チェック実行
make quality-gate

# 2. バージョン更新
make version-bump TYPE=patch  # patch|minor|major|prerelease

# 3. リリースタグ作成・プッシュ
git push origin main
git push origin --tags
```

### 🏷️ 自動リリース機能

- **タグベースリリース**: `v*.*.*`形式のタグで自動リリース
- **CHANGELOG自動更新**: コミット履歴から変更内容を自動生成
- **GitHub Releases**: アセット添付とリリースノート自動作成
- **品質ゲート**: リリース前の自動品質チェック

詳細は [docs/release-management.md](docs/release-management.md) を参照してください。

## 🧪 テスト・品質管理

### 包括的品質管理システム

このプロジェクトは以下の品質管理機能を統合しています：

### ✨ テストリファクタリング完了（全Phase完了）

**2025-09-17更新**: プロジェクトルールに準拠した実環境重視のテストへのリファクタリングが全Phase完了しました。

#### Phase 1-3: テスト構造最適化
- ✅ **50+件の環境偽装モックを削除**
- ✅ **実環境でのプラットフォーム固有テストへ変更**
- ✅ **`@pytest.mark.skipif`で適切なスキップ条件実装**
- ✅ **外部依存モック（GitHub API等）は維持**
- ✅ **プラットフォーム別テスト分離完了**

#### Phase 4: CI/CD最適化
- ✅ **実環境重視テストへのCI/CD最適化**
- ✅ **プラットフォーム固有テストの実環境実行**
- ✅ **品質ゲートの実環境対応**

詳細は [.amazonq/rules/test-refactoring-plan.md](.amazonq/rules/test-refactoring-plan.md) を参照してください。

- **Ruff**: 高速リンティング・フォーマッティング
- **MyPy**: 厳格な型チェック
- **Pytest**: 包括的テストスイート（単体・統合・パフォーマンス）
- **Pre-commit**: コミット前自動品質チェック
- **GitHub Actions**: CI/CDパイプライン
- **Dependabot**: 自動依存関係更新
- **セキュリティスキャン**: Bandit、Safety統合

### カバレッジ測定
```bash
# カバレッジ付きテスト実行
uv run pytest --cov=src/setup_repo --cov-report=html

# 品質メトリクス収集
uv run python scripts/quality-metrics.py

# 品質トレンド分析
uv run python scripts/quality-trends.py
```

### 品質チェック
```bash
# 全品質チェック実行
uv run ruff check .          # リンティング
uv run ruff format .         # フォーマッティング
uv run mypy src/             # 型チェック
uv run pytest               # テスト実行
uv run bandit -r src/        # セキュリティスキャン
uv run ruff format .         # フォーマッティング
uv run mypy src/             # 型チェック
uv run pytest tests/         # テスト実行
```

### 開発環境セットアップ

#### 自動セットアップ（推奨）
```bash
# 包括的な開発環境セットアップ
uv run python scripts/setup-dev-environment.py
```

#### 手動セットアップ
```bash
# 開発依存関係インストール + pre-commit設定
make setup-dev

# または個別実行
uv sync --dev
uv run python scripts/setup-pre-commit.py
```

## 📚 ドキュメント

- [🚀 詳細セットアップガイド](docs/setup-guide.md)
- [🌍 グローバルツールインストール](docs/global-tool-installation.md)
- [🔧 トラブルシューティング](docs/setup-guide.md#🔍-トラブルシューティング)
- [📊 カバレッジレポート](htmlcov/index.html)

## ✨ メリット

- ✅ 全プラットフォーム対応の単一コードベース
- ✅ 個人設定をgitから除外
- ✅ 簡単な設定管理
- ✅ プラットフォーム間で一貫した動作
- 🔧 モダンなパッケージマネージャー対応
- 🌐 日本語インターフェース
- 🛡️ 自動品質チェック（Pre-commit、Ruff、MyPy、Pytest）
- ✨ **実環境重視のテストスイート（ルール準拠）**
- 🧹 **リモートブランチクリーンナップ機能**

## 🧪 開発・テスト

### 🔧 Pre-commit設定（推奨）

開発者向けの自動品質チェックを設定できます。コミット時に自動的にコード品質チェックが実行されます。

#### 自動セットアップ

```bash
# Pre-commitの自動セットアップ（推奨）
uv run python scripts/setup-pre-commit.py
```

#### 手動セットアップ

```bash
# 1. 開発依存関係をインストール
uv sync --dev

# 2. Pre-commitフックをインストール
uv run pre-commit install

# 3. 全ファイルに対してテスト実行
uv run pre-commit run --all-files
```

#### Pre-commit使用方法

```bash
# 手動でpre-commitを実行
uv run pre-commit run --all-files

# 特定のフックのみ実行
uv run pre-commit run ruff          # Ruffリンティング
uv run pre-commit run ruff-format   # Ruffフォーマッティング
uv run pre-commit run mypy          # MyPy型チェック
uv run pre-commit run pytest-check  # Pytestテスト

# Pre-commitフックを更新
uv run pre-commit autoupdate

# コミット時にpre-commitをスキップ（緊急時のみ）
git commit --no-verify
```

### テスト実行

#### 推奨環境別の実行方法

**Linux/macOS/WSL（並列実行 - 推奨）:**
```bash
# 高速並列テスト実行
make test-parallel
# または
uv run pytest -n auto

# カバレッジ付き並列実行
uv run pytest -n auto --cov=src/setup_repo --cov-report=html
```

**Windows（直列実行）:**
```bash
# Windowsネイティブでの実行
make test
# または
uv run pytest

# WSL経由での並列実行（推奨）
wsl make test-parallel
```

**全環境共通:**
```bash
# 単体テストのみ実行
uv run pytest tests/unit/ -v

# 統合テストのみ実行
uv run pytest tests/integration/ -v

# 特定のマーカーでテスト実行
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m "not slow"
```

> **注意**: Windows環境では並列実行（`pytest-xdist`）に既知の問題があります。WSL環境での実行を推奨します。

### コード品質チェック

```bash
# リンティング
uv run ruff check .

# フォーマッティング
uv run ruff format .

# 型チェック
uv run mypy src/

# 全品質チェック実行
uv run ruff check . && uv run ruff format . && uv run mypy src/ && uv run pytest
```

### セキュリティチェック

```bash
# セキュリティツールのインストール
uv sync --group security

# 統合セキュリティチェック実行
uv run python scripts/security-check.py

# 個別セキュリティチェック
uv run safety check                    # 既知の脆弱性チェック
uv run bandit -r src/                  # コードセキュリティ分析
uv run semgrep --config=auto src/      # セキュリティパターンマッチング
uv run pip-licenses                    # ライセンス監査

# 特定のチェックのみ実行
uv run python scripts/security-check.py --check safety
uv run python scripts/security-check.py --check bandit
uv run python scripts/security-check.py --check semgrep
uv run python scripts/security-check.py --check license
```

### 開発依存関係のインストール

```bash
# 開発依存関係を含む全依存関係をインストール
uv sync --dev

# セキュリティツールも含める場合
uv sync --dev --group security
```

### VS Code開発環境セットアップ

このプロジェクトはVS Codeでの開発を最適化するための設定を提供しています：

#### 推奨拡張機能の自動インストール

VS Codeでプロジェクトを開くと、以下の拡張機能のインストールが推奨されます：

- **ms-python.python**: Python開発の基本機能
- **charliermarsh.ruff**: Ruffリンター・フォーマッター統合
- **ms-python.mypy-type-checker**: MyPy型チェック統合
- **ms-vscode.test-adapter-converter**: テスト実行統合

#### プラットフォーム固有設定

プロジェクトには各プラットフォーム用の最適化されたVS Code設定が含まれています：

- `vscode-templates/linux/settings.json` - Linux用設定
- `vscode-templates/windows/settings.json` - Windows用設定
- `vscode-templates/wsl/settings.json` - WSL用設定

#### 自動設定機能

- **保存時自動フォーマット**: Ruffによる自動コード整形
- **インポート自動整理**: 保存時にインポート文を自動整理
- **リアルタイム型チェック**: MyPyによるリアルタイム型エラー表示
- **テスト統合**: VS Code内でのPytestテスト実行

## 🧹 ブランチクリーンナップ

リモートブランチを整理して、リポジトリをクリーンに保つことができます。

### ⚠️ 重要: 事前準備

ブランチクリーンナップを実行する前に、必ずリモートの状態を同期してください：

```bash
git fetch --prune
```

### ブランチ一覧表示

```bash
# グローバルツールとしてインストール済みの場合
setup-repo cleanup list
setup-repo cleanup list --merged
setup-repo cleanup list --stale --days 90

# ローカル開発の場合
uv run main.py cleanup list
make cleanup-branches-list

# マージ済みブランチ一覧
uv run main.py cleanup list --merged

# 90日以上更新されていないブランチ一覧
uv run main.py cleanup list --stale --days 90
```

### マージ済みブランチの削除

```bash
# グローバルツール（任意のリポジトリで使用可能）
cd /path/to/any/repository
git fetch --prune
setup-repo cleanup clean --merged --dry-run  # 確認
setup-repo cleanup clean --merged -y         # 実行

# ローカル開発
uv run main.py cleanup clean --merged --dry-run
make cleanup-branches-merged
```

### 古いブランチの削除

```bash
# グローバルツール
cd /path/to/any/repository
git fetch --prune
setup-repo cleanup clean --stale --days 90 --dry-run  # 確認
setup-repo cleanup clean --stale --days 90 -y         # 実行

# ローカル開発
uv run main.py cleanup clean --stale --days 90 --dry-run
make cleanup-branches-stale
```

詳細は [docs/setup-guide.md#ブランチクリーンナップ](docs/setup-guide.md#🧹-ブランチクリーンナップ) を参照してください。

## 🛡️ セキュリティ

このプロジェクトは包括的なセキュリティ対策を実装しています：

### 自動セキュリティチェック

- **CI/CD統合**: 全プルリクエストで自動セキュリティスキャン
- **定期スキャン**: 毎日のセキュリティ脆弱性チェック
- **Pre-commitフック**: コミット前のセキュリティチェック

### セキュリティツール

- **Safety**: 既知の脆弱性データベースとの照合
- **Bandit**: Pythonコードのセキュリティ脆弱性検出
- **Semgrep**: セキュリティパターンマッチング
- **CodeQL**: GitHub統合の静的コード分析
- **TruffleHog**: シークレット検出
- **Dependabot**: 自動依存関係更新

### セキュリティポリシー

詳細なセキュリティポリシーと脆弱性報告手順については [SECURITY.md](SECURITY.md) を参照してください。
