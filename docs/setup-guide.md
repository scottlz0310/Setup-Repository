# セットアップガイド

## 🚀 初回セットアップ

### 前提条件
- Python 最新版 (3.9以上)
- Git 最新版

### クイックスタート

1. **リポジトリをクローン**
   ```bash
   git clone <repository-url>
   cd Setup-Repository
   ```

2. **インタラクティブセットアップを実行**
   ```bash
   uv run main.py setup
   ```

セットアップウィザードが以下を自動で行います：
- プラットフォーム検出
- 必要ツールのインストール
- GitHub認証の設定
- ワークスペースの構成
- 設定ファイルの作成

## 📋 プラットフォーム別詳細

### Windows
**推奨パッケージマネージャー:**
- Scoop (推奨)
- Winget (標準)
- Chocolatey

**Scoopのインストール:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
```

### Linux/WSL
**推奨パッケージマネージャー:**
- Snap (推奨)
- APT
- curl (公式インストーラー)

**Snapのインストール:**
```bash
sudo apt update && sudo apt install snapd
```

### macOS
**推奨パッケージマネージャー:**
- Homebrew (推奨)
- curl (公式インストーラー)

**Homebrewのインストール:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## 🔧 手動セットアップ

自動セットアップが失敗した場合の手動手順：

### 1. 必要ツールのインストール

**uv (Python環境管理):**
```bash
# Windows (Scoop)
scoop install uv

# Linux/WSL (Snap)
sudo snap install --classic uv

# macOS (Homebrew)
brew install uv

# フォールバック (pip)
pip install uv
```

**GitHub CLI (オプション):**
```bash
# Windows (Scoop)
scoop install gh

# Linux/WSL (Snap)
sudo snap install gh

# macOS (Homebrew)
brew install gh
```

### 2. GitHub認証

**GitHub CLIを使用:**
```bash
gh auth login
```

**環境変数を使用:**
```bash
export GITHUB_TOKEN=your_personal_access_token
```

### 3. 設定ファイルの作成

`config.local.json` を作成：
```json
{
  "owner": "your_github_username",
  "dest": "/path/to/your/workspace",
  "github_token": "your_github_token",
  "use_https": false,
  "max_retries": 2,
  "skip_uv_install": false,
  "auto_stash": false,
  "sync_only": false,
  "log_file": "/path/to/logs/repo-sync.log"
}
```

## 🔍 トラブルシューティング

### よくある問題

**Q: Pythonが見つからない**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip

# Windows
winget install Python.Python

# macOS
brew install python
```

**Q: Gitが見つからない**
```bash
# Ubuntu/Debian
sudo apt install git

# Windows
winget install Git.Git

# macOS
brew install git
```

**Q: パッケージマネージャーが見つからない**
- Windows: Wingetは標準搭載、Scoopは手動インストール
- Linux: Snapは多くのディストリビューションで利用可能
- macOS: Homebrewの手動インストールが必要

**Q: GitHub認証に失敗する**
1. GitHub CLIでの認証: `gh auth login`
2. Personal Access Tokenの作成: https://github.com/settings/tokens
3. 環境変数での設定: `export GITHUB_TOKEN=token`

**Q: ワークスペースディレクトリが作成できない**
- 権限を確認: `ls -la /path/to/parent/directory`
- 手動作成: `mkdir -p /path/to/workspace`

### ログの確認

エラーが発生した場合、以下でログを確認：
```bash
# 設定ファイルで指定したログファイル
cat ~/logs/repo-sync.log

# 直接実行時のエラー
uv run main.py setup 2>&1 | tee setup.log
```

## 🧪 開発環境セットアップ（開発者向け）

開発に参加する場合は、以下の追加セットアップを実行してください。

### 1. 開発依存関係のインストール

```bash
# 開発依存関係を含む全依存関係をインストール
uv sync --dev

# セキュリティツールも含める場合
uv sync --dev --group security
```

### 2. Pre-commitフックのセットアップ（推奨）

Pre-commitフックを設定することで、コミット時に自動的にコード品質チェックが実行されます。

#### 自動セットアップ（推奨）

```bash
# Pre-commitの自動セットアップ
uv run python scripts/setup-pre-commit.py
```

#### 手動セットアップ

```bash
# Pre-commitフックをインストール
uv run pre-commit install

# 全ファイルに対してテスト実行
uv run pre-commit run --all-files
```

#### Pre-commitフック内容

- **Ruff**: リンティングと自動修正
- **Ruff Format**: コードフォーマッティング
- **MyPy**: 型チェック（src/ディレクトリのみ）
- **Bandit**: セキュリティ脆弱性チェック
- **基本チェック**: ファイル末尾、行末空白、YAML/JSON構文
- **Pytest**: 単体テスト実行
- **Safety**: 既知の脆弱性チェック

### 3. テスト実行方法

#### 基本的なテスト実行

```bash
# 全テスト実行
uv run pytest

# 単体テストのみ実行
uv run pytest tests/unit/ -v

# 統合テストのみ実行
uv run pytest tests/integration/ -v

# 高速テストのみ（CIで使用）
uv run pytest -m "not slow"
```

#### カバレッジ付きテスト実行

```bash
# カバレッジ付きテスト実行
uv run pytest --cov=src/setup_repo --cov-report=html

# カバレッジレポートをブラウザで表示
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

#### 特定のマーカーでテスト実行

```bash
# 単体テストのみ
uv run pytest -m unit

# 統合テストのみ
uv run pytest -m integration

# 遅いテストを除外
uv run pytest -m "not slow"
```

### 4. コード品質チェック

#### 個別品質チェック

```bash
# リンティング
uv run ruff check .

# フォーマッティング
uv run ruff format .

# 型チェック
uv run mypy src/

# セキュリティチェック
uv run bandit -r src/
```

#### 統合品質チェック

```bash
# 全品質チェック実行
uv run ruff check . && uv run ruff format . && uv run mypy src/ && uv run pytest

# Makefileを使用した品質チェック（利用可能な場合）
make quality-gate
```

### 5. Pre-commit使用方法

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

### 6. 品質基準

このプロジェクトでは段階的厳格化ポリシーを採用しています：

#### 現在の段階（初期段階）
- **MyPy**: 基本的な型チェック（一部緩和設定）
- **テストカバレッジ**: 80%以上
- **Ruff**: 基本的なエラーチェック
- **セキュリティ**: Bandit、Safetyによる基本チェック

#### 将来の段階（予定）
- **MyPy**: より厳格な型チェック
- **テストカバレッジ**: 90%以上
- **Ruff**: 包括的なチェック
- **セキュリティ**: より厳格なセキュリティ基準

## 🧹 ブランチクリーンナップ

リモートブランチを整理して、リポジトリをクリーンに保つことができます。

### ブランチ一覧表示

```bash
# 全リモートブランチ一覧
uv run main.py cleanup list

# マージ済みブランチ一覧
uv run main.py cleanup list --merged

# 90日以上更新されていないブランチ一覧
uv run main.py cleanup list --stale --days 90

# Makefileを使用
make cleanup-branches-list
```

### マージ済みブランチの削除

```bash
# 削除対象を確認（dry-run）
uv run main.py cleanup clean --merged --dry-run

# 確認ありで削除
uv run main.py cleanup clean --merged

# 確認なしで削除
uv run main.py cleanup clean --merged -y

# カスタムベースブランチ指定
uv run main.py cleanup clean --merged --base-branch origin/develop

# Makefileを使用
make cleanup-branches-merged              # dry-run
make cleanup-branches-merged-confirm      # 実行
```

### 古いブランチの削除

```bash
# 90日以上更新されていないブランチを確認（dry-run）
uv run main.py cleanup clean --stale --days 90 --dry-run

# 確認ありで削除
uv run main.py cleanup clean --stale --days 90

# 確認なしで削除
uv run main.py cleanup clean --stale --days 90 -y

# カスタム日数指定（180日）
uv run main.py cleanup clean --stale --days 180 -y

# Makefileを使用
make cleanup-branches-stale               # dry-run (90日)
make cleanup-branches-stale-confirm       # 実行 (90日)
```

### 安全機能

- **main/developブランチは自動除外**: ベースブランチは削除されません
- **HEADブランチは自動除外**: 現在チェックアウトされているブランチは保護されます
- **削除前確認**: デフォルトで確認プロンプトが表示されます
- **dry-runモード**: 実際に削除せず、対象を確認できます

### 使用例

```bash
# ワークフロー例: 安全なクリーンナップ

# 1. マージ済みブランチを確認
make cleanup-branches-merged

# 2. 問題なければ削除実行
make cleanup-branches-merged-confirm

# 3. 古いブランチを確認
make cleanup-branches-stale

# 4. 問題なければ削除実行
make cleanup-branches-stale-confirm
```

## 📚 次のステップ

セットアップ完了後：

1. **設定確認**
   ```bash
   cat config.local.json
   ```

2. **テスト実行**
   ```bash
   uv run main.py sync --dry-run
   ```

3. **実際の同期**
   ```bash
   uv run main.py sync
   ```

### 開発者向け次のステップ

1. **品質チェック実行**
   ```bash
   uv run pre-commit run --all-files
   ```

2. **テストカバレッジ確認**
   ```bash
   uv run pytest --cov=src/setup_repo --cov-report=html
   ```

3. **コントリビューションガイド確認**
   ```bash
   cat CONTRIBUTING.md
   ```

## 🆘 サポート

問題が解決しない場合：
1. [Issues](../../issues) で既知の問題を確認
2. 新しいIssueを作成して詳細を報告
3. ログファイルとエラーメッセージを含める
