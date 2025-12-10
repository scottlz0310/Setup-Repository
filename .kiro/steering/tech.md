# 技術スタック

## ビルドシステム・パッケージ管理

- **メイン**: `uv` - モダンなPythonパッケージマネージャー・環境管理ツール
- **ビルドバックエンド**: Hatchling（pyproject.tomlで指定）
- **パッケージ構造**: src/レイアウトを使用した標準Pythonパッケージ

## 技術スタック

- **言語**: Python 3.11+（3.11-3.13をサポート）
- **設定**: 自動検出フォールバック付きJSONベース設定ファイル
- **CLIフレームワーク**: Typer（型ヒント駆動CLI）+ Rich（リッチターミナル出力）
- **クロスプラットフォーム**: プラットフォーム固有検出機能付きネイティブPython
- **バージョン管理**: GitHub API統合Git

## 開発ツール

- **リンティング**: Ruff（flake8、black、isortを置き換え）
- **型チェック**: 厳格設定のBasedPyright
- **テスト**: pytest（開発依存関係）

## 共通コマンド

### セットアップ・インストール
```bash
# 初期セットアップ（推奨）
uv run main.py setup

# 手動依存関係インストール
uv sync --dev
```

### 開発
```bash
# ツール実行
uv run main.py sync
uv run main.py sync --dry-run

# コード品質チェック
uv run ruff check .
uv run ruff format .
uv run basedpyright src/

# テスト
uv run pytest
```

### 設定
```bash
# 個人設定編集
nano config.local.json

# 現在の設定表示（自動検出 + ファイル上書き）
python -c "from src.setup_repo.config import load_config; import json; print(json.dumps(load_config(), indent=2))"
```

## パッケージマネージャー統合

このツールはプラットフォームごとに複数のパッケージマネージャーをサポートします：
- **Windows**: Scoop（推奨）、Winget、Chocolatey
- **Linux/WSL**: Homebrew（推奨）、snap、APT、curl
- **macOS**: Homebrew（推奨）、curl
