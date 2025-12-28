# Processing Flow Documentation

このドキュメントでは、`setup-repo` の内部処理フローを詳しく説明します。

## sync コマンドの処理フロー

```
setup-repo sync --owner <user> [--dest <dir>] [--jobs N] [--no-prune] [--dry-run]
```

### 1. 設定の読み込み

```
┌─────────────────────────────────────────────────────────────────┐
│ AppSettings の読み込み                                           │
├─────────────────────────────────────────────────────────────────┤
│ 1. 環境変数から設定を読み込み (SETUP_REPO_* プレフィックス)        │
│ 2. .env ファイルがあれば読み込み                                  │
│ 3. GitHub owner が未設定の場合:                                   │
│    - gh api user から取得を試みる                                 │
│    - 失敗したら git config user.name から取得                     │
│ 4. GitHub token が未設定の場合:                                   │
│    - gh auth token から取得を試みる                               │
└─────────────────────────────────────────────────────────────────┘
```

**設定項目:**

| 環境変数 | CLI オプション | デフォルト | 説明 |
|----------|---------------|-----------|------|
| `SETUP_REPO_GITHUB_OWNER` | `--owner` | 自動検出 | GitHub オーナー名 |
| `SETUP_REPO_GITHUB_TOKEN` | - | 自動検出 | GitHub トークン |
| `SETUP_REPO_WORKSPACE_DIR` | `--dest` | `~/workspace` | クローン先 |
| `SETUP_REPO_MAX_WORKERS` | `--jobs` | `10` | 並列数 |
| `SETUP_REPO_USE_HTTPS` | - | `false` | HTTPS 使用 |
| `SETUP_REPO_GIT_SSL_NO_VERIFY` | - | `false` | SSL 検証スキップ |
| `SETUP_REPO_LOG_FILE` | `--log-file` | `None` | ログファイル |

### 2. リポジトリ一覧の取得

```
┌─────────────────────────────────────────────────────────────────┐
│ GitHub API からリポジトリ一覧を取得                              │
├─────────────────────────────────────────────────────────────────┤
│ GET /users/{owner}/repos?page=N&per_page=100                    │
│                                                                 │
│ - ページネーション対応 (100件ずつ取得)                            │
│ - トークンがあれば認証ヘッダを付与                                │
│ - SSL 検証オプション対応                                         │
└─────────────────────────────────────────────────────────────────┘
```

**取得される情報:**

- `name`: リポジトリ名
- `full_name`: フルパス (owner/repo)
- `clone_url`: HTTPS クローン URL
- `ssh_url`: SSH クローン URL
- `default_branch`: デフォルトブランチ
- `private`: プライベートリポジトリかどうか
- `archived`: アーカイブ済みかどうか
- `fork`: フォークかどうか

### 3. 並列処理

```
┌─────────────────────────────────────────────────────────────────┐
│ ParallelProcessor による並列処理                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ThreadPoolExecutor (max_workers=10)                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ... ┌─────────┐           │
│  │ Worker1 │ │ Worker2 │ │ Worker3 │     │ WorkerN │           │
│  │  repo1  │ │  repo2  │ │  repo3  │     │  repoN  │           │
│  └────┬────┘ └────┬────┘ └────┬────┘     └────┬────┘           │
│       │           │           │               │                 │
│       ▼           ▼           ▼               ▼                 │
│  ┌─────────────────────────────────────────────────┐           │
│  │              結果を収集                          │           │
│  │  - 成功/失敗/スキップをカウント                   │           │
│  │  - 各リポジトリの処理時間を記録                   │           │
│  └─────────────────────────────────────────────────┘           │
│                                                                 │
│  Rich Progress: [████████████████████] 100% 10/10 ETA 00:00     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4. 各リポジトリの処理

```
┌─────────────────────────────────────────────────────────────────┐
│ リポジトリごとの処理フロー                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  リポジトリパスが存在する？                                       │
│         │                                                       │
│    ┌────┴────┐                                                  │
│    ▼         ▼                                                  │
│  [Yes]     [No]                                                 │
│    │         │                                                  │
│    ▼         ▼                                                  │
│  ┌─────┐  ┌─────────────────────────────────────┐              │
│  │Pull │  │Clone                                │              │
│  └──┬──┘  │  git clone --depth 1 [--branch X]  │              │
│     │     │  <url> <dest>                       │              │
│     │     └─────────────────────────────────────┘              │
│     │                                                          │
│     ▼                                                          │
│  ┌─────────────────────────────────────────────┐               │
│  │ 1. git fetch --prune (auto_prune=true時)    │               │
│  │ 2. git pull --ff-only                        │               │
│  └─────────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Pull 処理の詳細

### 未コミット変更がある場合の動作

```
┌─────────────────────────────────────────────────────────────────┐
│ git pull --ff-only の動作                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ケース1: 変更がリモートとコンフリクトしない                        │
│   → pull 成功、ローカル変更は保持される                           │
│   → ステータス: SUCCESS                                          │
│                                                                 │
│ ケース2: 変更がリモートとコンフリクトする                          │
│   → pull 失敗 (fast-forward できない)                            │
│   → ステータス: FAILED                                           │
│   → エラー: "merge conflict" など                                │
│                                                                 │
│ ケース3: auto_stash=true の場合 (デフォルト: false)               │
│   → 変更を stash してから pull                                   │
│   → pull 後に stash pop                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### fetch --prune の動作

```
┌─────────────────────────────────────────────────────────────────┐
│ git fetch --prune (auto_prune=true時、デフォルト)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ - リモートで削除されたブランチを自動的にローカルから削除           │
│ - リモート追跡ブランチを最新の状態に更新                          │
│ - pull の前に実行される                                          │
│                                                                 │
│ 例:                                                             │
│   リモートで feature/old が削除された場合                         │
│   → ローカルの origin/feature/old も削除される                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## ログ出力

### ログレベル

| レベル | CLI オプション | 出力内容 |
|--------|---------------|---------|
| DEBUG | `-v`, `--verbose` | 全ての詳細情報 (git コマンド、API 呼び出し等) |
| INFO | (デフォルト) | 主要な処理ステップ |
| WARNING | `-q`, `--quiet` | 警告とエラーのみ |

### verbose モードの出力例

```bash
$ setup-repo sync --owner myuser -v

2025-12-29T12:00:00 [debug] sync_started owner=myuser dest=/home/user/workspace jobs=10
ℹ Syncing repositories for myuser to /home/user/workspace
2025-12-29T12:00:01 [debug] fetching_repositories owner=myuser
2025-12-29T12:00:02 [info] repositories_fetched owner=myuser count=15
ℹ Found 15 repositories
2025-12-29T12:00:02 [debug] sync_config auto_prune=True ssl_no_verify=False
2025-12-29T12:00:02 [debug] pulling repo=repo1
2025-12-29T12:00:02 [debug] git_command cmd="git fetch --prune" cwd=/home/user/workspace/repo1
2025-12-29T12:00:03 [debug] fetched_and_pruned repo=repo1
2025-12-29T12:00:03 [debug] git_command cmd="git pull --ff-only" cwd=/home/user/workspace/repo1
2025-12-29T12:00:04 [info] pulled repo=repo1
...
2025-12-29T12:00:30 [info] sync_completed total=15 success=14 failed=1 skipped=0 duration=28.5s

╭─────────────────────────────── Summary ───────────────────────────────╮
│ ✓ Success: 14  ✗ Failed: 1  ⊘ Skipped: 0  Duration: 28.5s            │
╰───────────────────────────────────────────────────────────────────────╯
```

### ログファイル出力 (JSON Lines)

```bash
$ setup-repo sync --owner myuser --log-file sync.log
```

`sync.log` の内容:

```json
{"event": "sync_started", "owner": "myuser", "dest": "/home/user/workspace", "jobs": 10, "timestamp": "2025-12-29T12:00:00"}
{"event": "repositories_fetched", "owner": "myuser", "count": 15, "timestamp": "2025-12-29T12:00:02"}
{"event": "pulled", "repo": "repo1", "timestamp": "2025-12-29T12:00:04"}
{"event": "pulled", "repo": "repo2", "timestamp": "2025-12-29T12:00:05"}
{"event": "sync_completed", "total": 15, "success": 14, "failed": 1, "skipped": 0, "duration": "28.5s", "timestamp": "2025-12-29T12:00:30"}
```

## cleanup コマンドの処理フロー

```
setup-repo cleanup [path] [--base main] [--dry-run] [--force]
```

```
┌─────────────────────────────────────────────────────────────────┐
│ cleanup コマンドの処理                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. リポジトリパスの確認                                          │
│    - パス指定がなければカレントディレクトリ                        │
│    - .git ディレクトリの存在確認                                  │
│                                                                 │
│ 2. git fetch --prune                                            │
│    - リモート追跡ブランチを最新化                                 │
│                                                                 │
│ 3. マージ済みブランチの取得                                       │
│    git branch --merged <base_branch>                            │
│    - ベースブランチ自体は除外                                     │
│    - * (現在のブランチ) も除外                                    │
│                                                                 │
│ 4. ブランチ一覧をテーブル表示                                     │
│                                                                 │
│ 5. --dry-run の場合                                             │
│    → 削除対象の数を表示して終了                                   │
│                                                                 │
│ 6. --force がない場合                                            │
│    → 確認プロンプトを表示                                         │
│                                                                 │
│ 7. ブランチを削除                                                │
│    git branch -d <branch>                                       │
│    - 各ブランチの削除結果をカウント                               │
│                                                                 │
│ 8. 結果を表示                                                    │
│    "✓ X/Y branch(es) deleted"                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## エラーハンドリング

### リポジトリ処理のエラー

```
┌─────────────────────────────────────────────────────────────────┐
│ エラーが発生した場合                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. そのリポジトリは FAILED ステータスで記録                       │
│ 2. エラーメッセージを保存                                         │
│ 3. 他のリポジトリの処理は継続                                     │
│ 4. 最終サマリーで失敗したリポジトリを一覧表示                      │
│ 5. 1つでも失敗があれば exit code 1 で終了                        │
│                                                                 │
│ 例外の種類:                                                      │
│ - CalledProcessError: git コマンドの失敗                         │
│ - TimeoutExpired: 5分以上のタイムアウト                          │
│ - その他の例外: 予期せぬエラー                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## トラブルシューティング

### 未コミット変更があるリポジトリ

```bash
# 問題: pull 時にコンフリクトエラー
# 解決策1: 手動でコミットまたはスタッシュしてから再実行
cd /path/to/repo
git stash
setup-repo sync ...
git stash pop

# 解決策2: auto_stash を有効化 (環境変数)
export SETUP_REPO_AUTO_STASH=true
setup-repo sync ...
```

### SSL 証明書エラー (企業内 CA)

```bash
# 解決策: SSL 検証をスキップ
export SETUP_REPO_GIT_SSL_NO_VERIFY=true
setup-repo sync ...
```

### 詳細なデバッグ

```bash
# verbose モードでログファイルも出力
setup-repo sync --owner myuser -v --log-file debug.log

# ログファイルを確認
cat debug.log | jq .
```
