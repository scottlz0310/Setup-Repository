# Setup Repository

[![Coverage](https://img.shields.io/badge/coverage-89.58%25-brightgreen)](output/htmlcov/index.html)
[![Tests](https://github.com/scottlz0310/Setup-Repository/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/scottlz0310/Setup-Repository/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

GitHub リポジトリのセットアップ・同期ツール。モダンなCLIインターフェースで複数リポジトリを効率的に管理できます。

## Features

- **リポジトリ同期**: GitHub オーナーの全リポジトリをクローン/プル
- **並列処理**: 複数リポジトリを同時に処理（デフォルト10並列）
- **ブランチクリーンアップ**: マージ済みブランチの自動削除
- **リッチな出力**: プログレスバー、カラー出力、サマリー表示
- **構造化ログ**: JSON形式のログファイル出力対応

## What's New in v2.1.2

- リリース自動化のスマートバージョンチェックを修正

## Installation

### uv を使用（推奨）

```bash
# グローバルツールとしてインストール
uv tool install git+https://github.com/scottlz0310/Setup-Repository.git

# 任意のディレクトリで使用可能
setup-repo --help
```

### pip を使用

```bash
pip install git+https://github.com/scottlz0310/Setup-Repository.git
```

### 開発用インストール

```bash
git clone https://github.com/scottlz0310/Setup-Repository.git
cd Setup-Repository
uv sync --dev
```

## Quick Start

### 初期設定（推奨）

```bash
# 対話式ウィザードで設定
setup-repo init
```

ウィザードでは以下を設定できます:

- GitHub 認証（オーナー名・トークン）
- ワークスペースディレクトリ
- クローン方式（HTTPS/SSH）
- 詳細オプション（ログ設定、auto-prune、auto-stash、auto-cleanup）

### リポジトリを同期

```bash
# GitHub オーナーのリポジトリを同期
setup-repo sync --owner <github-username>

# 特定のディレクトリにクローン
setup-repo sync --owner <github-username> --dest ~/projects

# ドライランモード（実行せずにプレビュー）
setup-repo sync --owner <github-username> --dry-run

# 並列数を指定
setup-repo sync --owner <github-username> --jobs 5
```

### マージ済みブランチを削除

```bash
# カレントディレクトリのリポジトリ
setup-repo cleanup

# 特定のリポジトリ
setup-repo cleanup /path/to/repo

# ドライランモード
setup-repo cleanup --dry-run

# 確認なしで削除
setup-repo cleanup --force

# ベースブランチを指定
setup-repo cleanup --base develop

# スクワッシュマージされたブランチも検出（GitHub API使用）
setup-repo cleanup --include-squash
```

## Configuration

設定は以下の優先順位で読み込まれます（上が優先）:

1. 環境変数
2. TOML 設定ファイル (`~/.config/setup-repo/config.toml`)
3. 自動検出
4. デフォルト値

### TOML 設定ファイル（推奨）

`setup-repo init` コマンドで対話式に設定ファイルを作成できます:

```bash
setup-repo init
```

設定ファイルは `~/.config/setup-repo/config.toml` に保存されます:

```toml
[github]
owner = "your-username"
token = "ghp_xxxxxxxxxxxx"

[workspace]
dir = "~/workspace"
max_workers = 10

[git]
use_https = true
ssl_no_verify = false
auto_prune = true
auto_stash = false
auto_cleanup = false
auto_cleanup_include_squash = false

[logging]
file = "~/.local/share/setup-repo/logs/setup-repo.jsonl"
```

### 環境変数

環境変数は TOML 設定より優先されます:

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `SETUP_REPO_GITHUB_OWNER` | GitHub オーナー名 | 自動検出 |
| `SETUP_REPO_GITHUB_TOKEN` | GitHub トークン | 自動検出 (`gh auth token`) |
| `SETUP_REPO_WORKSPACE_DIR` | ワークスペースディレクトリ | `~/workspace` |
| `SETUP_REPO_MAX_WORKERS` | 並列処理数 | `10` |
| `SETUP_REPO_USE_HTTPS` | HTTPS でクローン | `false` |
| `SETUP_REPO_GIT_SSL_NO_VERIFY` | SSL 検証をスキップ | `false` |
| `SETUP_REPO_AUTO_PRUNE` | pull 時に --prune | `true` |
| `SETUP_REPO_AUTO_STASH` | pull 時に自動 stash | `false` |
| `SETUP_REPO_AUTO_CLEANUP` | sync 後に自動 cleanup | `false` |
| `SETUP_REPO_AUTO_CLEANUP_INCLUDE_SQUASH` | sync 後の squash マージ検出を含める | `false` |
| `SETUP_REPO_LOG_FILE` | ログファイルパス | なし |

### 自動検出

以下の設定は自動的に検出されます:

- **GitHub オーナー**: `gh api user` または `git config user.name` から取得
- **GitHub トークン**: `gh auth token` から取得

## CLI Options

### グローバルオプション

```bash
setup-repo [OPTIONS] COMMAND [ARGS]

Options:
  -v, --verbose   詳細な出力を表示
  -q, --quiet     サマリーのみ表示
  --log-file PATH JSON ログファイルパス
  --help          ヘルプを表示
```

### init コマンド

```bash
setup-repo init
```

対話式ウィザードで設定ファイルを作成します。設定は `~/.config/setup-repo/config.toml` に保存されます。

### sync コマンド

```bash
setup-repo sync [OPTIONS]

Options:
  -o, --owner TEXT      GitHub オーナー名
  -d, --dest PATH       クローン先ディレクトリ
  -j, --jobs INTEGER    並列数 [default: 10]
  --no-prune            fetch --prune をスキップ
  -n, --dry-run         実行せずにプレビュー
```

### cleanup コマンド

```bash
setup-repo cleanup [OPTIONS] [PATH]

Arguments:
  [PATH]  対象リポジトリパス [default: カレントディレクトリ]

Options:
  -b, --base TEXT       ベースブランチ [default: main]
  -n, --dry-run         削除せずにプレビュー
  -f, --force           確認なしで削除
  -s, --include-squash  スクワッシュマージされたブランチも検出（GitHub API使用）
```

**注意事項:**
- `--include-squash` オプションを使用する場合、GitHub トークンが必要です
- トークンは `SETUP_REPO_GITHUB_TOKEN` 環境変数または設定ファイルから取得されます
- スクワッシュマージの検出には GitHub API を使用するため、リモートが GitHub である必要があります

## Development

### 開発環境セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/scottlz0310/Setup-Repository.git
cd Setup-Repository

# 依存関係をインストール
uv sync --dev

# pre-commit フックをインストール
uv run pre-commit install
```

### テスト実行

```bash
# 全テスト実行
uv run pytest

# カバレッジ付き
uv run pytest --cov=src/setup_repo --cov-report=html

# 並列実行
uv run pytest -n auto
```

### コード品質チェック

```bash
# リンティング
uv run ruff check .

# フォーマッティング
uv run ruff format .

# 型チェック
uv run basedpyright src/

# セキュリティチェック
uv run bandit -r src/

# 全チェック（pre-commit）
uv run pre-commit run --all-files
```

### プロジェクト構造

```
src/setup_repo/
├── __init__.py
├── cli/                    # CLI レイヤー
│   ├── app.py              # Typer アプリケーション
│   ├── output.py           # Rich 出力ヘルパー
│   └── commands/
│       ├── init.py         # init コマンド（設定ウィザード）
│       ├── sync.py         # sync コマンド
│       └── cleanup.py      # cleanup コマンド
├── core/                   # コアロジック
│   ├── git.py              # Git 操作
│   ├── github.py           # GitHub API クライアント
│   └── parallel.py         # 並列処理
├── models/                 # データモデル
│   ├── config.py           # 設定モデル
│   ├── repository.py       # リポジトリモデル
│   └── result.py           # 処理結果モデル
└── utils/                  # ユーティリティ
    ├── console.py          # Rich コンソール
    └── logging.py          # Structlog 設定
```

## Technology Stack

- **CLI Framework**: [Typer](https://typer.tiangolo.com/) - モダンな CLI フレームワーク
- **Console Output**: [Rich](https://rich.readthedocs.io/) - リッチなターミナル出力
- **HTTP Client**: [httpx](https://www.python-httpx.org/) - 非同期対応 HTTP クライアント
- **Data Validation**: [Pydantic](https://docs.pydantic.dev/) - データバリデーション
- **Configuration**: [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - 設定管理
- **Logging**: [structlog](https://www.structlog.org/) - 構造化ログ

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

コントリビューションを歓迎します。詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。
