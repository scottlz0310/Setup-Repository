# 🚀 Setup Repository v1.4.5

## 📋 変更内容

### 🐛 修正

- **テンプレート同梱問題の完全修正**
  - テンプレートディレクトリをパッケージソース内に移動 (`src/setup_repo/templates/`)
  - `importlib.resources`を使用してテンプレートにアクセスするように更新
  - VS Codeテンプレートが`.gitignore`で除外されていた問題を修正
  - すべてのプラットフォーム（Ubuntu, macOS, Windows）でテストが成功

### 🔧 その他

- 型アノテーション追加（`Path | Traversable`対応）
- `vscode_setup.py`を`importlib.resources`対応に更新
- テストを実際のパッケージテンプレートを使用するように更新

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
