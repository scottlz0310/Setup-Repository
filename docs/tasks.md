# Setup-Repository v2.0 Rewrite Tasks

## 進捗状況

- **ブランチ**: `feature/v2-rewrite`
- **開始日**: 2025-12-29
- **現在のフェーズ**: Phase 7 完了 ✅
- **テストカバレッジ**: 87.29%
- **テスト数**: 86 passed

---

## Phase 0: プロジェクト基盤 ✅

- [x] ブランチ `feature/v2-rewrite` を作成
- [x] 不要ファイル/ディレクトリを削除
- [x] 新しいディレクトリ構造を作成
- [x] pyproject.toml を更新
- [x] 共有インスタンス (`console.py`) を作成

## Phase 1: ロギング基盤 (Structlog + Rich) ✅

- [x] `src/setup_repo/utils/logging.py` を作成
- [x] `configure_logging()` を実装
- [x] `log_context()` コンテキストマネージャを実装
- [x] ファイルハンドラ（JSONL）を実装
- [x] テストを作成 (10 tests)

## Phase 2: 設定管理 (Pydantic Settings) ✅

- [x] `src/setup_repo/models/config.py` を作成
- [x] `AppSettings` クラスを実装
- [x] 自動検出機能（GitHub owner/token）を実装
- [x] テストを作成 (12 tests)

## Phase 3: データモデル (Pydantic) ✅

- [x] `src/setup_repo/models/repository.py` を作成
- [x] `src/setup_repo/models/result.py` を作成
- [x] テストを作成 (10 tests)

## Phase 4: GitHub API クライアント (httpx) ✅

- [x] `src/setup_repo/core/github.py` を作成
- [x] `GitHubClient` (同期版) を実装
- [x] `AsyncGitHubClient` (非同期版) を実装
- [x] テストを作成 (13 tests)

## Phase 5: Git 操作 ✅

- [x] `src/setup_repo/core/git.py` を作成
- [x] `GitOperations` クラスを実装
- [x] テストを作成 (17 tests)

## Phase 6: 並列処理 (ThreadPoolExecutor + Rich Progress) ✅

- [x] `src/setup_repo/core/parallel.py` を作成
- [x] `ParallelProcessor` クラスを実装
- [x] テストを作成 (8 tests)

## Phase 7: CLI 実装 (Typer + Rich) ✅

- [x] `src/setup_repo/cli/app.py` を作成
- [x] `src/setup_repo/cli/output.py` を作成
- [x] `src/setup_repo/cli/commands/sync.py` を作成
- [x] `src/setup_repo/cli/commands/cleanup.py` を作成
- [x] テストを作成 (16 tests)

## Phase 8: テスト ✅

- [x] ユニットテストを作成 (86 tests)
- [x] カバレッジ 80% 以上を達成 (87.29%)
- [ ] 統合テストを作成 (オプション)

## Phase 9: マイグレーションと統合 🔲

- [ ] 既存機能の移行確認
- [ ] ドキュメント更新
- [ ] ブランチマージ

---

## 実装済みファイル構造

```
src/setup_repo/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── app.py           # Typer application
│   ├── output.py        # Rich output helpers
│   └── commands/
│       ├── __init__.py
│       ├── sync.py      # sync command
│       └── cleanup.py   # cleanup command
├── core/
│   ├── __init__.py
│   ├── git.py           # Git operations
│   ├── github.py        # GitHub API client
│   └── parallel.py      # Parallel processing
├── models/
│   ├── __init__.py
│   ├── config.py        # AppSettings
│   ├── repository.py    # Repository model
│   └── result.py        # ProcessResult, SyncSummary
└── utils/
    ├── __init__.py
    ├── console.py       # Rich console
    └── logging.py       # Structlog configuration

tests/
├── conftest.py
└── unit/
    ├── test_cli.py      # 16 tests
    ├── test_config.py   # 12 tests
    ├── test_git.py      # 17 tests
    ├── test_github.py   # 13 tests
    ├── test_logging.py  # 10 tests
    ├── test_models.py   # 10 tests
    └── test_parallel.py # 8 tests
```

## CLI コマンド

```bash
# ヘルプを表示
setup-repo --help

# リポジトリを同期
setup-repo sync --owner <github-owner> --dest <directory>

# マージ済みブランチを削除
setup-repo cleanup [path] --base main --dry-run
```

---

## 削除対象ファイル/ディレクトリ

### ソースコード（すべて置換済み）
- `src/setup_repo/*.py` (既存の全ファイル) ✅ 削除済み
- `main.py` ✅ 削除済み

### テスト（すべて置換済み）
- `tests/` (既存のテストファイル) ✅ 削除済み

### 不要な生成物/キャッシュ
- `__pycache__/` ✅ 削除済み
- その他の生成ファイル ✅ 削除済み

---

## 保持するファイル

- `.git/`
- `.github/`
- `.vscode/`
- `.gitignore`
- `.pre-commit-config.yaml`
- `.yamllint`
- `.bandit`
- `pyproject.toml` (更新済み)
- `uv.lock` (更新済み)
- `pyrightconfig.json`
- `renovate.json`
- `config.json.template`
- `config.local.json`
- `LICENSE`
- `README.md` (後で更新)
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `GOVERNANCE.md`
- `SECURITY.md`
- `SUPPORT.md`
- `Makefile` (後で更新)
- `docs/rewrite_implementation_plan.md`
- `docs/tasks.md`
- `custom/` (テンプレート)
