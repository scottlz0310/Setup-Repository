# プロジェクト構造

## ルートディレクトリレイアウト

```
├── main.py                 # メインエントリーポイント - CLIディスパッチャー
├── pyproject.toml         # プロジェクトメタデータ、依存関係、ツール設定
├── uv.lock               # 依存関係ロックファイル（uv）
├── config.json.template  # 設定テンプレート（追跡対象）
├── config.local.json     # 個人設定（gitignore対象）
├── src/setup_repo/       # メインパッケージソース
├── docs/                 # ドキュメント
├── vscode-templates/     # プラットフォーム固有VS Code設定
└── .vscode/             # VS Codeワークスペース設定（gitignore対象）
```

## ソースコード構成（`src/setup_repo/`）

- **`__init__.py`** - パッケージ初期化
- **`cli.py`** - CLIコマンドハンドラー（setup_cli、sync_cli）
- **`config.py`** - 自動検出付き設定管理
- **`setup.py`** - 初期セットアップオーケストレーション
- **`interactive_setup.py`** - セットアップウィザード実装
- **`sync.py`** - リポジトリ同期ロジック
- **`git_operations.py`** - Gitコマンドラッパー
- **`github_api.py`** - GitHub API相互作用
- **`platform_detector.py`** - クロスプラットフォーム検出
- **`python_env.py`** - Python環境管理
- **`uv_installer.py`** - UVパッケージマネージャー統合
- **`vscode_setup.py`** - VS Code設定
- **`safety_check.py`** - 安全性検証
- **`gitignore_manager.py`** - .gitignoreファイル管理
- **`utils.py`** - 共通ユーティリティ

## 設定ファイル

- **`config.json.template`** - 利用可能な全オプション付きテンプレート
- **`config.local.json`** - ユーザー固有上書き（gitignore対象）
- 設定読み込み優先度：自動検出 → config.local.json → config.json

## プラットフォームテンプレート（`vscode-templates/`）

```
vscode-templates/
├── windows/settings.json
├── linux/settings.json
└── wsl/settings.json
```

## ドキュメント（`docs/`）

- **`setup-guide.md`** - 包括的セットアップ手順
- **`refactoring-guidelines.md`** - コードメンテナンスガイドライン

## コード規約

- **モジュール命名**: 説明的な名前でsnake_case
- **関数構成**: 各モジュールは集中した責務を持つ
- **CLIパターン**: 専用ハンドラー関数付きサブコマンド
- **設定**: フォールバック自動検出付きJSONベース
- **エラーハンドリング**: 情報的メッセージ付き優雅な劣化
- **国際化**: 英語コードコメント付き日本語インターフェース
