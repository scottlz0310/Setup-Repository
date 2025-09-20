# 🚀 Setup Repository v1.3.1

## 📋 変更内容

### ✨ 追加
- 🔧 **統合バージョン管理システム**
  - version-manager.pyにリリース機能を統合
  - CHANGELOG自動更新機能
  - リリースノート自動生成機能
  - 完全なリリースプロセス自動化

### 🔄 変更
- CI/CDワークフローの簡素化
  - release.ymlをversion-manager.py依存に変更
  - インラインスクリプトを削除
  - 外部依存による保守性向上
- バージョン管理の統一化
  - 手動とCI両方で同じツールを使用
  - コード重複の削除

### 🐛 修正
- release.ymlファイルの破損を修復
- バージョン管理ロジックの一元化

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
