# 🚀 Setup Repository v1.3.6

## 📋 変更内容

### ✨ 新機能
- 完全自動化リリースフロー実装

### 🐛 修正
- pre-commitによる品質修正
- リリースワークフローのYAML構文エラー修正

### 🔧 その他
- docs: スマートバージョンチェック機能をドキュメントに反映
- docs: リリースワークフロー完全ガイド追加

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
