# セットアップガイド

## 🚀 初回セットアップ

### 前提条件
- Python 3.9以上
- Git

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

**Q: Python 3.9が見つからない**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3.9 python3.9-pip

# Windows
winget install Python.Python.3.12

# macOS
brew install python@3.9
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

## 🆘 サポート

問題が解決しない場合：
1. [Issues](../../issues) で既知の問題を確認
2. 新しいIssueを作成して詳細を報告
3. ログファイルとエラーメッセージを含める