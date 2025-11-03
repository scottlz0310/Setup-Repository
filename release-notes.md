# 🚀 Setup Repository v1.4.3

## 📋 変更内容

### ✨ 新機能
- Renovate自動依存関係更新の設定を追加

### 🐛 修正
- Windows環境でのgh/gitコマンドタイムアウトを追加
- pyproject.tomlのaddopts設定を正しい配列形式に修正
- CodeQL指摘事項の修正

### 🔧 その他
- chore: Renovate導入によりDependabot自動マージワークフローを削除
- 🚀 リリース v1.4.2 準備完了

## 📦 インストール方法

### 🐍 Pythonパッケージとして
```bash
pip install setup-repository
```

### 📥 ソースからインストール
```bash
git clone https://github.com/scottlz0310/Setup-Repository.git
cd Setup-Repository
uv sync --dev
uv run main.py setup
```

## 🔧 使用方法

```bash
# 初期セットアップ
setup-repo setup

# リポジトリ同期
setup-repo sync

# ドライランモード
setup-repo sync --dry-run
```

## 🌐 サポートプラットフォーム

- ✅ Windows (Scoop, Winget, Chocolatey)
- ✅ Linux (Snap, APT)
- ✅ WSL (Linux互換)
- ✅ macOS (Homebrew)

## 🐍 Python要件

- Python 3.11以上
- 対応バージョン: 3.11, 3.12, 3.13

---

**完全な変更履歴**: [CHANGELOG.md](https://github.com/scottlz0310/Setup-Repository/blob/main/CHANGELOG.md)
