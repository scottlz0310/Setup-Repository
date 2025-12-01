# 🚀 Setup Repository v1.4.7

## 📋 変更内容

### 🎉 新機能

- **大きなリポジトリのShallow Cloneサポート**
  - PowerToysなど大きなリポジトリのクローン時のタイムアウト問題を解決
  - `large_repos`設定で特定リポジトリを自動的にshallow cloneに対応
  - `shallow_clone`、`clone_depth`、`clone_timeout`の設定オプション追加

### 🔧 改善

- **クローン処理の最適化**
  - デフォルトタイムアウトを600秒（10分）に延長
  - 設定可能なタイムアウト値により柔軟な調整が可能
  - Shallow cloneにより大きなリポジトリのクローン時間を大幅短縮

- **エラーハンドリングの強化**
  - タイムアウト時に適切なエラーメッセージとガイダンスを表示
  - 設定の調整方法を分かりやすく案内

### 📚 ドキュメント

- 大きなリポジトリの設定方法をsetup-guide.mdに追加
- config.json.templateに新しい設定オプションの説明を追加

### 🧪 テスト

- Shallow clone機能の包括的なテストケースを追加（7つの新規テスト）
- タイムアウト処理のテストを追加
- Large repos設定のテストを追加

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
