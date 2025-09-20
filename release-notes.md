# 🚀 Setup Repository v1.3.0

## 📋 変更内容

### ✨ 追加
- 🏗️ **新機能実装完了**
  - Deploy管理ワークフロー実装
  - Migration管理ワークフロー実装
  - Template・Backup機能追加
  - システム監視・アラート機能追加
  - GitHub API認証確認スクリプト追加
- 🧪 **テスト強化**
  - validate_file_path関数のセキュリティテスト強化
  - パストラバーサル攻撃対策テスト追加
  - プラットフォーム固有テストの改善
  - Windows環境向け高速テスト実行スクリプト
- 📊 **品質向上**
  - Phase 4完了 - エンタープライズ品質達成（87.88%カバレッジ）
  - カバレッジ要件を80%に引き上げ
  - テスト設定のpyproject.toml統合

### 🔄 変更
- CI/CDパイプライン最適化
  - 不要なMerge Platform Coverageジョブを削除
  - coverage.jsonファイルをCI/CDから削除
  - 実行時間短縮とパイプライン簡素化
- ファイル出力先をoutputディレクトリに統一
- ドキュメント構造の整理・分類

### 🐛 修正
- macOSでのパス解決問題を修正
- プラットフォーム検出テストのWSL対応
- テストレポート・カバレッジファイルの出力先修正
- Windows環境でのpytest最適化

### 🗑️ 削除
- scripts/merge-coverage.py（統合カバレッジスクリプト）
- Makefileのmerge-coverageターゲット
- 関連ログファイル（coverage-merge.log）

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
