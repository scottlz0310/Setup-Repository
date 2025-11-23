# 🚀 Setup Repository v1.4.6

## 📋 変更内容

### 🎉 新機能

- **VS Codeテンプレート構造の刷新**
  - common/language/platformの3層構造に再設計
  - プロジェクトタイプを自動検出して適切なテンプレートを適用
  - 複数プロジェクトタイプの同時検出に対応（フロントエンドNode + バックエンドPython等）

- **JSON設定のインテリジェントマージ機能**
  - 既存のVS Code設定を保持しつつ新しい設定を統合
  - リスト、オブジェクト、プリミティブ値の適切なマージロジック
  - 不正なJSONの場合はバックアップを作成して安全に適用

- **Rust開発環境テンプレート追加**
  - rust-analyzer、cargo-nextest、cargo-watchなど包括的なツールチェーン対応
  - tasks.json（13種類のビルド/テスト/リントタスク）
  - launch.json（デバッグ設定、Tauri対応）
  - extensions.json（推奨拡張機能）
  - Tauri/axum/tower/tracingなどモダンなフレームワークに対応

### 🔧 改善

- **プロジェクトタイプ検出の大幅強化**
  - スコアリングシステムによる精確な検出（閾値10点）
  - ファイル数カウントによるボーナス加算
  - 単一ファイルによる誤検出を防止
  - ファイル数キャッシュによるパフォーマンス最適化

- **厳格な型チェック設定**
  - すべてのテンプレートでstrict mode有効化
  - Python: basedpyright + strict mypy対応
  - Node.js: Biomeリンター/フォーマッター対応
  - TypeScript: strict設定 + inlay hints有効化
  - Rust: clippy pedanticモード + inlay hints有効化

- **開発者体験の向上**
  - VS Code設定のマージにより既存設定が保持される
  - プロジェクトタイプに応じたextensions.jsonの自動配置
  - tasks.json/launch.jsonの自動セットアップ

### 🐛 修正

- Ruff lintエラーの修正（Traversableインポート位置）
- mypy型チェックエラーの修正（型注釈追加）
- テンプレート管理の後方互換性維持

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
