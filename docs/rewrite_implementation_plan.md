# Setup-Repository v2.0 リライト実装計画

## 概要

既存実装をゼロベースでリライトし、モダンな技術スタックで再構築する。
サブブランチ `feature/v2-rewrite` で開発し、完成後にマージする。

**リライトの目的:**

- モダンな技術スタックへの移行
- 並列処理による大幅な高速化
- 構造化ログとCLI体験の向上
- 型安全性とバリデーションの強化

---

## 技術スタック

### 新規採用ライブラリ

| ライブラリ | 用途 | 選定理由 |
|-----------|------|----------|
| **Typer** | CLI フレームワーク | 型ヒントベース、Rich統合、自動補完生成 |
| **Rich** | コンソール出力 | テーブル、パネル、プログレスバー、トレースバック |
| **Structlog** | 構造化ログ | contextvars対応、並行処理に強い、プロセッサチェーン |
| **httpx** | HTTP クライアント | async対応、型安全、HTTP/2、requests後継 |
| **Pydantic v2** | データバリデーション | 高速（Rust製コア）、型安全、シリアライズ統合 |
| **pydantic-settings** | 設定管理 | 環境変数統合、.env対応、バリデーション |

### 継続利用

| ライブラリ | 用途 |
|-----------|------|
| **concurrent.futures** | 並列処理（標準ライブラリ） |
| **pathlib** | パス操作（標準ライブラリ） |
| **subprocess** | Git コマンド実行（標準ライブラリ） |

### 削除するライブラリ

| ライブラリ | 理由 |
|-----------|------|
| **requests** | httpx に置換 |
| **argparse** | Typer に置換 |
| **rg (ripgrep)** | 使用頻度低、標準ライブラリで代替可能 |

### 開発ツール（継続）

- **uv**: パッケージ管理
- **Ruff**: Lint/Format
- **BasedPyright**: 型チェック
- **Pytest**: テスト
- **pre-commit**: Git Hooks

---

## アーキテクチャ

### ディレクトリ構造

```
src/setup_repo/
├── __init__.py
├── cli/                      # CLI レイヤー
│   ├── __init__.py
│   ├── app.py                # Typer アプリケーション
│   ├── commands/             # サブコマンド
│   │   ├── __init__.py
│   │   ├── sync.py           # sync コマンド
│   │   ├── cleanup.py        # cleanup コマンド
│   │   └── config.py         # config コマンド
│   └── output.py             # Rich 出力ヘルパー
├── core/                     # ビジネスロジック
│   ├── __init__.py
│   ├── sync.py               # リポジトリ同期
│   ├── git.py                # Git 操作
│   ├── github.py             # GitHub API
│   └── parallel.py           # 並列処理
├── models/                   # Pydantic モデル
│   ├── __init__.py
│   ├── config.py             # 設定モデル
│   ├── repository.py         # リポジトリモデル
│   └── result.py             # 処理結果モデル
└── utils/                    # ユーティリティ
    ├── __init__.py
    ├── logging.py            # Structlog 設定
    └── console.py            # Rich Console 共有インスタンス
```

### レイヤー構成

```
CLI Layer (Typer + Rich)
    ↓
Core Layer (ビジネスロジック)
    ↓
Infrastructure Layer (Git, GitHub API, ファイルシステム)
```

---

## Phase 0: プロジェクト基盤

**目的:** リライト用のブランチとプロジェクト構造を準備

### 実装内容

1. **ブランチ作成**

   ```bash
   git checkout -b feature/v2-rewrite
   ```

2. **pyproject.toml の更新**

   ```toml
   [project]
   name = "setup-repository"
   version = "2.0.0-alpha.1"
   requires-python = ">=3.11"
   dependencies = [
       "typer[all]>=0.21.0",
       "rich>=14.2.0",
       "structlog>=25.5.0",
       "httpx>=0.28.1",
       "pydantic>=2.12.5",
       "pydantic-settings>=2.12.0",
   ]
   ```

3. **ディレクトリ構造の作成**

   - 上記アーキテクチャに従ってディレクトリを作成
   - 各 `__init__.py` の配置

4. **共有インスタンスの定義**

   ```python
   # src/setup_repo/utils/console.py
   from rich.console import Console

   console = Console()
   ```

### 完了条件

- ブランチ `feature/v2-rewrite` が作成されている
- 新しいディレクトリ構造が作成されている
- `uv sync` で依存関係がインストールできる

---

## Phase 1: ロギング基盤 (Structlog + Rich)

**目的:** 構造化ログの基盤を構築し、すべてのモジュールで使用可能にする

### 実装内容

1. **Structlog 設定**

   ```python
   # src/setup_repo/utils/logging.py
   import logging
   import structlog
   from logging.handlers import RotatingFileHandler
   from pathlib import Path

   from setup_repo.utils.console import console

   def configure_logging(
       level: str = "INFO",
       log_file: Path | None = None,
   ) -> None:
       """ログ設定を初期化"""

       # 共通プロセッサ
       shared_processors: list[structlog.types.Processor] = [
           structlog.contextvars.merge_contextvars,
           structlog.processors.add_log_level,
           structlog.processors.TimeStamper(fmt="iso"),
           structlog.processors.StackInfoRenderer(),
           structlog.dev.set_exc_info,  # 例外情報を自動付与
       ]

       if log_file:
           # ファイル出力も有効化
           _setup_file_handler(log_file, shared_processors)

       # コンソール出力設定
       structlog.configure(
           processors=[
               *shared_processors,
               structlog.processors.ExceptionPrettyPrinter(),  # 例外を見やすく表示
               structlog.dev.ConsoleRenderer(colors=True),
           ],
           wrapper_class=structlog.make_filtering_bound_logger(
               getattr(logging, level.upper())
           ),
           context_class=dict,
           logger_factory=structlog.PrintLoggerFactory(),
           cache_logger_on_first_use=True,
       )

   def _setup_file_handler(
       log_file: Path,
       processors: list[structlog.types.Processor],
   ) -> None:
       """JSON Lines ファイルハンドラを設定"""
       log_file.parent.mkdir(parents=True, exist_ok=True)

       handler = RotatingFileHandler(
           log_file,
           maxBytes=10_000_000,  # 10MB
           backupCount=5,
           encoding="utf-8",
       )

       formatter = structlog.stdlib.ProcessorFormatter(
           processor=structlog.processors.JSONRenderer(),
           foreign_pre_chain=processors,
       )
       handler.setFormatter(formatter)

       root = logging.getLogger()
       root.addHandler(handler)
       root.setLevel(logging.DEBUG)

   def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
       """ロガーを取得"""
       return structlog.get_logger(name)
   ```

2. **コンテキスト管理ヘルパー**

   ```python
   # src/setup_repo/utils/logging.py (続き)
   from contextlib import contextmanager
   from structlog.contextvars import bind_contextvars, clear_contextvars

   @contextmanager
   def log_context(**kwargs):
       """一時的なログコンテキストを設定"""
       bind_contextvars(**kwargs)
       try:
           yield
       finally:
           clear_contextvars()
   ```

### 完了条件

- `configure_logging()` でコンソール出力が設定される
- `--log-file` 指定時に JSON Lines ファイルが出力される
- `log_context()` でスレッドセーフなコンテキスト管理ができる

---

## Phase 2: 設定管理 (Pydantic Settings)

**目的:** 型安全な設定管理を実装し、環境変数・設定ファイル・CLI引数を統合

### 実装内容

1. **設定モデル**

   ```python
   # src/setup_repo/models/config.py
   import os
   import subprocess
   from pathlib import Path
   from typing import Self

   from pydantic import Field, model_validator
   from pydantic_settings import BaseSettings, SettingsConfigDict

   class AppSettings(BaseSettings):
       """アプリケーション設定"""

       model_config = SettingsConfigDict(
           env_prefix="SETUP_REPO_",
           env_file=".env",
           env_file_encoding="utf-8",
           extra="ignore",
       )

       # GitHub 設定
       github_owner: str = Field(default="", description="GitHub オーナー名")
       github_token: str | None = Field(default=None, description="GitHub Token")
       use_https: bool = Field(default=False, description="HTTPS を使用")

       # ディレクトリ設定
       workspace_dir: Path = Field(
           default=Path.home() / "workspace",
           description="リポジトリのクローン先",
       )

       # 並列処理設定
       max_workers: int = Field(default=10, ge=1, le=32, description="並列数")

       # Git 設定
       auto_prune: bool = Field(default=True, description="自動 fetch --prune")
       auto_stash: bool = Field(default=False, description="自動 stash/pop")
       git_ssl_no_verify: bool = Field(default=False, description="SSL 検証をスキップ（社内 CA 対応）")

       # ログ設定
       log_level: str = Field(default="INFO", description="ログレベル")
       log_file: Path | None = Field(default=None, description="ログファイルパス")

       @model_validator(mode="after")
       def auto_detect_github_settings(self) -> Self:
           """GitHub 設定を自動検出"""
           # github_owner の自動検出
           if not self.github_owner:
               if owner := os.environ.get("GITHUB_USER"):
                   self.github_owner = owner
               else:
                   try:
                       result = subprocess.run(
                           ["git", "config", "user.name"],
                           capture_output=True,
                           text=True,
                       )
                       if result.returncode == 0:
                           self.github_owner = result.stdout.strip()
                   except Exception:
                       pass

           # github_token の自動検出
           if not self.github_token:
               try:
                   result = subprocess.run(
                       ["gh", "auth", "token"],
                       capture_output=True,
                       text=True,
                   )
                   if result.returncode == 0:
                       self.github_token = result.stdout.strip()
               except Exception:
                   pass

           return self
   ```

2. **設定のロード**

   ```python
   # src/setup_repo/models/config.py (続き)
   from functools import lru_cache

   @lru_cache
   def get_settings() -> AppSettings:
       """設定をロード（キャッシュ付き）"""
       return AppSettings()

   def reset_settings() -> None:
       """設定キャッシュをクリア（テスト用）"""
       get_settings.cache_clear()
   ```

### 完了条件

- 環境変数 `SETUP_REPO_*` から設定が読み込まれる
- `.env` ファイルから設定が読み込まれる
- `github_owner` と `github_token` が自動検出される
- バリデーションエラーが適切に報告される

---

## Phase 3: データモデル (Pydantic)

**目的:** リポジトリ情報と処理結果のモデルを定義

### 実装内容

1. **リポジトリモデル**

   ```python
   # src/setup_repo/models/repository.py
   from datetime import datetime
   from pydantic import BaseModel, Field, HttpUrl

   class Repository(BaseModel):
       """GitHub リポジトリ情報"""

       name: str
       full_name: str
       clone_url: str
       ssh_url: str
       default_branch: str = "main"
       private: bool = False
       archived: bool = False
       fork: bool = False
       pushed_at: datetime | None = None

       def get_clone_url(self, use_https: bool = False) -> str:
           """クローン用 URL を取得"""
           return self.clone_url if use_https else self.ssh_url
   ```

2. **処理結果モデル**

   ```python
   # src/setup_repo/models/result.py
   from datetime import datetime
   from enum import Enum
   from pydantic import BaseModel, Field

   class ResultStatus(str, Enum):
       SUCCESS = "success"
       FAILED = "failed"
       SKIPPED = "skipped"

   class ProcessResult(BaseModel):
       """リポジトリ処理結果"""

       repo_name: str
       status: ResultStatus
       duration: float = 0.0
       message: str = ""
       error: str | None = None
       timestamp: datetime = Field(default_factory=datetime.now)

       @property
       def is_success(self) -> bool:
           return self.status == ResultStatus.SUCCESS

   class SyncSummary(BaseModel):
       """同期処理のサマリー"""

       total: int
       success: int
       failed: int
       skipped: int
       duration: float
       results: list[ProcessResult]

       @classmethod
       def from_results(
           cls,
           results: list[ProcessResult],
           duration: float,
       ) -> "SyncSummary":
           return cls(
               total=len(results),
               success=sum(1 for r in results if r.status == ResultStatus.SUCCESS),
               failed=sum(1 for r in results if r.status == ResultStatus.FAILED),
               skipped=sum(1 for r in results if r.status == ResultStatus.SKIPPED),
               duration=duration,
               results=results,
           )
   ```

### 完了条件

- `Repository` モデルで GitHub API レスポンスをパースできる
- `ProcessResult` で処理結果を表現できる
- `SyncSummary` でサマリーを生成できる

---

## Phase 4: GitHub API クライアント (httpx)

**目的:** 型安全な GitHub API クライアントを実装

### 実装内容

1. **GitHub クライアント（同期版）**

   ```python
   # src/setup_repo/core/github.py
   import httpx
   from pydantic import ValidationError

   from setup_repo.models.repository import Repository
   from setup_repo.utils.logging import get_logger

   log = get_logger(__name__)

   class GitHubClient:
       """GitHub API クライアント（同期版）"""

       BASE_URL = "https://api.github.com"

       def __init__(
           self,
           token: str | None = None,
           verify_ssl: bool = True,
       ):
           self.token = token
           self.verify_ssl = verify_ssl
           self._client: httpx.Client | None = None

       def _get_headers(self) -> dict[str, str]:
           """共通ヘッダーを取得"""
           headers = {
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28",
           }
           if self.token:
               headers["Authorization"] = f"Bearer {self.token}"
           return headers

       @property
       def client(self) -> httpx.Client:
           if self._client is None:
               self._client = httpx.Client(
                   base_url=self.BASE_URL,
                   headers=self._get_headers(),
                   timeout=30.0,
                   verify=self.verify_ssl,
               )
           return self._client

       def get_repositories(self, owner: str) -> list[Repository]:
           """ユーザーのリポジトリ一覧を取得"""
           repos: list[Repository] = []
           page = 1

           while True:
               response = self.client.get(
                   f"/users/{owner}/repos",
                   params={"page": page, "per_page": 100},
               )
               response.raise_for_status()

               data = response.json()
               if not data:
                   break

               repos.extend(self._parse_repositories(data))
               page += 1

           log.info("fetched_repositories", owner=owner, count=len(repos))
           return repos

       def _parse_repositories(self, data: list[dict]) -> list[Repository]:
           """API レスポンスをパース"""
           repos: list[Repository] = []
           for item in data:
               try:
                   repo = Repository(
                       name=item["name"],
                       full_name=item["full_name"],
                       clone_url=item["clone_url"],
                       ssh_url=item["ssh_url"],
                       default_branch=item.get("default_branch", "main"),
                       private=item.get("private", False),
                       archived=item.get("archived", False),
                       fork=item.get("fork", False),
                       pushed_at=item.get("pushed_at"),
                   )
                   repos.append(repo)
               except ValidationError as e:
                   log.warning("invalid_repo_data", repo=item.get("name"), error=str(e))
           return repos

       def close(self) -> None:
           if self._client:
               self._client.close()
               self._client = None

       def __enter__(self) -> "GitHubClient":
           return self

       def __exit__(self, *args) -> None:
           self.close()
   ```

2. **GitHub クライアント（非同期版）**

   ```python
   # src/setup_repo/core/github.py (続き)

   class AsyncGitHubClient:
       """GitHub API クライアント（非同期版）

       大量のリポジトリ取得や複数の API 呼び出しが必要な場合に使用。
       """

       BASE_URL = "https://api.github.com"

       def __init__(
           self,
           token: str | None = None,
           verify_ssl: bool = True,
       ):
           self.token = token
           self.verify_ssl = verify_ssl
           self._client: httpx.AsyncClient | None = None

       def _get_headers(self) -> dict[str, str]:
           """共通ヘッダーを取得"""
           headers = {
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28",
           }
           if self.token:
               headers["Authorization"] = f"Bearer {self.token}"
           return headers

       @property
       def client(self) -> httpx.AsyncClient:
           if self._client is None:
               self._client = httpx.AsyncClient(
                   base_url=self.BASE_URL,
                   headers=self._get_headers(),
                   timeout=30.0,
                   verify=self.verify_ssl,
               )
           return self._client

       async def get_repositories(self, owner: str) -> list[Repository]:
           """ユーザーのリポジトリ一覧を取得（非同期）"""
           repos: list[Repository] = []
           page = 1

           while True:
               response = await self.client.get(
                   f"/users/{owner}/repos",
                   params={"page": page, "per_page": 100},
               )
               response.raise_for_status()

               data = response.json()
               if not data:
                   break

               repos.extend(self._parse_repositories(data))
               page += 1

           log.info("fetched_repositories", owner=owner, count=len(repos))
           return repos

       def _parse_repositories(self, data: list[dict]) -> list[Repository]:
           """API レスポンスをパース（GitHubClient と共通）"""
           repos: list[Repository] = []
           for item in data:
               try:
                   repo = Repository(
                       name=item["name"],
                       full_name=item["full_name"],
                       clone_url=item["clone_url"],
                       ssh_url=item["ssh_url"],
                       default_branch=item.get("default_branch", "main"),
                       private=item.get("private", False),
                       archived=item.get("archived", False),
                       fork=item.get("fork", False),
                       pushed_at=item.get("pushed_at"),
                   )
                   repos.append(repo)
               except ValidationError as e:
                   log.warning("invalid_repo_data", repo=item.get("name"), error=str(e))
           return repos

       async def close(self) -> None:
           if self._client:
               await self._client.aclose()
               self._client = None

       async def __aenter__(self) -> "AsyncGitHubClient":
           return self

       async def __aexit__(self, *args) -> None:
           await self.close()
   ```

### 完了条件

- 同期版: リポジトリ一覧が取得できる
- 非同期版: `async with` と `await` で動作する
- SSL 検証のスキップが可能（社内 CA 対応）
- ページネーションが正しく動作する
- エラーハンドリングが適切

---

## Phase 5: Git 操作

**目的:** Git コマンドのラッパーを実装

### 実装内容

1. **Git 操作クラス**

   ```python
   # src/setup_repo/core/git.py
   import subprocess
   from pathlib import Path

   from setup_repo.utils.logging import get_logger, log_context
   from setup_repo.models.result import ProcessResult, ResultStatus

   log = get_logger(__name__)

   class GitOperations:
       """Git 操作"""

       def __init__(self, auto_prune: bool = True, auto_stash: bool = False):
           self.auto_prune = auto_prune
           self.auto_stash = auto_stash

       def _run(
           self,
           args: list[str],
           cwd: Path | None = None,
           check: bool = True,
       ) -> subprocess.CompletedProcess[str]:
           """Git コマンドを実行"""
           cmd = ["git", *args]
           log.debug("git_command", cmd=" ".join(cmd), cwd=str(cwd))

           return subprocess.run(
               cmd,
               cwd=cwd,
               capture_output=True,
               text=True,
               check=check,
           )

       def clone(
           self,
           url: str,
           dest: Path,
           branch: str | None = None,
       ) -> ProcessResult:
           """リポジトリをクローン"""
           args = ["clone", "--depth", "1"]
           if branch:
               args.extend(["--branch", branch])
           args.extend([url, str(dest)])

           try:
               self._run(args)
               log.info("cloned", url=url, dest=str(dest))
               return ProcessResult(
                   repo_name=dest.name,
                   status=ResultStatus.SUCCESS,
                   message="Cloned successfully",
               )
           except subprocess.CalledProcessError as e:
               log.error("clone_failed", url=url, error=e.stderr)
               return ProcessResult(
                   repo_name=dest.name,
                   status=ResultStatus.FAILED,
                   error=e.stderr,
               )

       def fetch_and_prune(self, repo_path: Path) -> bool:
           """fetch --prune を実行"""
           if not self.auto_prune:
               return True

           try:
               self._run(["fetch", "--prune"], cwd=repo_path)
               log.debug("fetched_and_pruned", repo=repo_path.name)
               return True
           except subprocess.CalledProcessError as e:
               log.warning("fetch_prune_failed", repo=repo_path.name, error=e.stderr)
               return False

       def pull(self, repo_path: Path) -> ProcessResult:
           """リポジトリを pull"""
           with log_context(repo=repo_path.name):
               # まず fetch --prune
               self.fetch_and_prune(repo_path)

               # stash が必要な場合
               stashed = False
               if self.auto_stash and self._has_changes(repo_path):
                   self._run(["stash"], cwd=repo_path)
                   stashed = True
                   log.debug("stashed")

               try:
                   self._run(["pull", "--ff-only"], cwd=repo_path)
                   log.info("pulled")

                   if stashed:
                       self._run(["stash", "pop"], cwd=repo_path, check=False)
                       log.debug("stash_popped")

                   return ProcessResult(
                       repo_name=repo_path.name,
                       status=ResultStatus.SUCCESS,
                       message="Pulled successfully",
                   )
               except subprocess.CalledProcessError as e:
                   log.error("pull_failed", error=e.stderr)
                   return ProcessResult(
                       repo_name=repo_path.name,
                       status=ResultStatus.FAILED,
                       error=e.stderr,
                   )

       def _has_changes(self, repo_path: Path) -> bool:
           """未コミットの変更があるか"""
           result = self._run(["status", "--porcelain"], cwd=repo_path, check=False)
           return bool(result.stdout.strip())

       def get_merged_branches(self, repo_path: Path, base_branch: str = "main") -> list[str]:
           """マージ済みブランチを取得"""
           try:
               result = self._run(
                   ["branch", "--merged", base_branch],
                   cwd=repo_path,
               )
               branches = []
               for line in result.stdout.strip().split("\n"):
                   branch = line.strip().lstrip("* ")
                   if branch and branch != base_branch:
                       branches.append(branch)
               return branches
           except subprocess.CalledProcessError:
               return []

       def delete_branch(self, repo_path: Path, branch: str) -> bool:
           """ブランチを削除"""
           try:
               self._run(["branch", "-d", branch], cwd=repo_path)
               log.info("branch_deleted", branch=branch)
               return True
           except subprocess.CalledProcessError as e:
               log.warning("branch_delete_failed", branch=branch, error=e.stderr)
               return False
   ```

### 完了条件

- clone/pull/fetch が動作する
- `auto_prune` で fetch --prune が制御できる
- `auto_stash` で stash/pop が動作する
- マージ済みブランチの取得・削除ができる

---

## Phase 6: 並列処理 (ThreadPoolExecutor + Rich Progress)

**目的:** 複数リポジトリの並列処理を実装

### 実装内容

1. **並列処理クラス**

   ```python
   # src/setup_repo/core/parallel.py
   import time
   from concurrent.futures import ThreadPoolExecutor, as_completed
   from pathlib import Path
   from typing import Callable

   from rich.progress import (
       Progress,
       SpinnerColumn,
       TextColumn,
       BarColumn,
       TaskProgressColumn,
       TimeElapsedColumn,
       TimeRemainingColumn,
   )

   from setup_repo.utils.console import console
   from setup_repo.utils.logging import get_logger, log_context
   from setup_repo.models.result import ProcessResult, ResultStatus, SyncSummary

   log = get_logger(__name__)

   class ParallelProcessor:
       """並列処理"""

       def __init__(self, max_workers: int = 10):
           self.max_workers = max_workers

       def process(
           self,
           items: list[Path],
           process_func: Callable[[Path], ProcessResult],
           desc: str = "Processing",
       ) -> SyncSummary:
           """複数アイテムを並列処理"""
           results: list[ProcessResult] = []
           start_time = time.time()

           with Progress(
               SpinnerColumn(),
               TextColumn("[progress.description]{task.description}"),
               BarColumn(),
               TaskProgressColumn(),
               TimeElapsedColumn(),
               TimeRemainingColumn(),  # 残り時間を表示
               console=console,
               transient=True,
           ) as progress:
               task = progress.add_task(desc, total=len(items))

               with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                   futures = {
                       executor.submit(self._safe_process, item, process_func): item
                       for item in items
                   }

                   for future in as_completed(futures):
                       item = futures[future]
                       try:
                           result = future.result()
                           results.append(result)
                           progress.update(
                               task,
                               advance=1,
                               description=f"{desc}: {result.repo_name}",
                           )
                       except Exception as e:
                           log.exception("unexpected_error", item=str(item))
                           results.append(ProcessResult(
                               repo_name=item.name,
                               status=ResultStatus.FAILED,
                               error=str(e),
                           ))
                           progress.update(task, advance=1)

           duration = time.time() - start_time
           return SyncSummary.from_results(results, duration)

       def _safe_process(
           self,
           item: Path,
           func: Callable[[Path], ProcessResult],
       ) -> ProcessResult:
           """例外をキャッチして処理"""
           with log_context(repo=item.name):
               start = time.time()
               try:
                   result = func(item)
                   result.duration = time.time() - start
                   return result
               except Exception as e:
                   log.exception("process_failed")
                   return ProcessResult(
                       repo_name=item.name,
                       status=ResultStatus.FAILED,
                       duration=time.time() - start,
                       error=str(e),
                   )
   ```

### 完了条件

- 複数リポジトリが並列処理される
- Rich Progress でプログレスバーが表示される
- エラーが発生しても他の処理は継続する
- `SyncSummary` でサマリーが生成される

---

## Phase 7: CLI 実装 (Typer + Rich)

**目的:** ユーザーフレンドリーな CLI を実装

### 実装内容

1. **Typer アプリケーション**

   ```python
   # src/setup_repo/cli/app.py
   from pathlib import Path
   from typing import Annotated, Optional

   import typer
   from rich.panel import Panel
   from rich.table import Table

   from setup_repo.utils.console import console
   from setup_repo.utils.logging import configure_logging, get_logger
   from setup_repo.models.config import get_settings

   app = typer.Typer(
       name="setup-repo",
       help="GitHub リポジトリセットアップ・同期ツール",
       rich_markup_mode="rich",
       no_args_is_help=True,
   )

   log = get_logger(__name__)

   # グローバルオプション
   @app.callback()
   def main(
       verbose: Annotated[
           bool,
           typer.Option("--verbose", "-v", help="詳細な出力を表示"),
       ] = False,
       quiet: Annotated[
           bool,
           typer.Option("--quiet", "-q", help="サマリーのみ表示"),
       ] = False,
       log_file: Annotated[
           Optional[Path],
           typer.Option("--log-file", help="JSON ログファイルパス"),
       ] = None,
   ) -> None:
       """Setup Repository CLI"""
       level = "DEBUG" if verbose else "WARNING" if quiet else "INFO"
       settings = get_settings()
       configure_logging(
           level=level,
           log_file=log_file or settings.log_file,
       )
   ```

2. **sync コマンド**

   ```python
   # src/setup_repo/cli/commands/sync.py
   from pathlib import Path
   from typing import Annotated, Optional

   import typer

   from setup_repo.cli.app import app
   from setup_repo.cli.output import show_summary
   from setup_repo.utils.console import console
   from setup_repo.core.github import GitHubClient
   from setup_repo.core.git import GitOperations
   from setup_repo.core.parallel import ParallelProcessor
   from setup_repo.utils.logging import get_logger
   from setup_repo.models.config import get_settings
   from setup_repo.models.result import ProcessResult, ResultStatus

   log = get_logger(__name__)

   @app.command()
   def sync(
       owner: Annotated[
           Optional[str],
           typer.Option("--owner", "-o", help="GitHub オーナー名"),
       ] = None,
       dest: Annotated[
           Optional[Path],
           typer.Option("--dest", "-d", help="クローン先ディレクトリ"),
       ] = None,
       jobs: Annotated[
           int,
           typer.Option("--jobs", "-j", help="並列数"),
       ] = 10,
       no_prune: Annotated[
           bool,
           typer.Option("--no-prune", help="fetch --prune をスキップ"),
       ] = False,
       dry_run: Annotated[
           bool,
           typer.Option("--dry-run", "-n", help="実行せずにプレビュー"),
       ] = False,
   ) -> None:
       """リポジトリを同期"""
       settings = get_settings()

       owner = owner or settings.github_owner
       if not owner:
           console.print("[red]Error:[/] GitHub オーナーが指定されていません")
           raise typer.Exit(1)

       dest_dir = dest or settings.workspace_dir
       dest_dir.mkdir(parents=True, exist_ok=True)

       # リポジトリ一覧を取得
       with GitHubClient(settings.github_token) as client:
           repos = client.get_repositories(owner)

       if not repos:
           console.print("[yellow]Warning:[/] リポジトリが見つかりません")
           raise typer.Exit(0)

       # dry-run モード
       if dry_run:
           _show_dry_run(repos, dest_dir)
           raise typer.Exit(0)

       # 同期処理
       git = GitOperations(auto_prune=not no_prune)
       processor = ParallelProcessor(max_workers=jobs)

       def process_repo(repo_path: Path) -> ProcessResult:
           if repo_path.exists():
               return git.pull(repo_path)
           else:
               # 対応するリポジトリを探す
               repo = next((r for r in repos if r.name == repo_path.name), None)
               if repo:
                   return git.clone(
                       repo.get_clone_url(settings.use_https),
                       repo_path,
                       repo.default_branch,
                   )
               return ProcessResult(
                   repo_name=repo_path.name,
                   status=ResultStatus.SKIPPED,
                   message="Repository not found",
               )

       paths = [dest_dir / repo.name for repo in repos]
       summary = processor.process(paths, process_repo, desc="Syncing")

       show_summary(summary)

       if summary.failed > 0:
           raise typer.Exit(1)
   ```

3. **出力ヘルパー**

   ```python
   # src/setup_repo/cli/output.py
   from rich.panel import Panel
   from rich.table import Table

   from setup_repo.utils.console import console
   from setup_repo.models.result import SyncSummary, ResultStatus

   def show_summary(summary: SyncSummary) -> None:
       """サマリーを表示"""
       # サマリーパネル
       console.print(Panel(
           f"[green]✓ Success: {summary.success}[/]  "
           f"[red]✗ Failed: {summary.failed}[/]  "
           f"[yellow]⊘ Skipped: {summary.skipped}[/]  "
           f"[dim]Duration: {summary.duration:.1f}s[/]",
           title="Summary",
           border_style="blue",
       ))

       # 失敗詳細
       if summary.failed > 0:
           table = Table(title="Failed Repositories", show_header=True)
           table.add_column("Repository", style="cyan")
           table.add_column("Error", style="red")
           table.add_column("Duration", style="dim", justify="right")

           for r in summary.results:
               if r.status == ResultStatus.FAILED:
                   table.add_row(
                       r.repo_name,
                       r.error or r.message,
                       f"{r.duration:.1f}s",
                   )

           console.print(table)
   ```

4. **cleanup コマンド**

   ```python
   # src/setup_repo/cli/commands/cleanup.py
   from pathlib import Path
   from typing import Annotated, Optional

   import typer
   from rich.table import Table

   from setup_repo.cli.app import app
   from setup_repo.utils.console import console
   from setup_repo.core.git import GitOperations
   from setup_repo.utils.logging import get_logger
   from setup_repo.models.config import get_settings

   log = get_logger(__name__)

   @app.command()
   def cleanup(
       path: Annotated[
           Optional[Path],
           typer.Argument(help="対象リポジトリパス"),
       ] = None,
       base_branch: Annotated[
           str,
           typer.Option("--base", "-b", help="ベースブランチ"),
       ] = "main",
       dry_run: Annotated[
           bool,
           typer.Option("--dry-run", "-n", help="削除せずにプレビュー"),
       ] = False,
       force: Annotated[
           bool,
           typer.Option("--force", "-f", help="確認なしで削除"),
       ] = False,
   ) -> None:
       """マージ済みブランチを削除"""
       repo_path = path or Path.cwd()

       if not (repo_path / ".git").exists():
           console.print("[red]Error:[/] Git リポジトリではありません")
           raise typer.Exit(1)

       git = GitOperations()

       # まず fetch --prune
       git.fetch_and_prune(repo_path)

       # マージ済みブランチを取得
       branches = git.get_merged_branches(repo_path, base_branch)

       if not branches:
           console.print("[green]✓[/] 削除対象のブランチはありません")
           raise typer.Exit(0)

       # テーブル表示
       table = Table(title="Merged Branches")
       table.add_column("Branch", style="cyan")

       for branch in branches:
           table.add_row(branch)

       console.print(table)

       if dry_run:
           console.print(f"\n[dim]{len(branches)} branch(es) would be deleted[/]")
           raise typer.Exit(0)

       # 確認
       if not force:
           confirm = typer.confirm(f"{len(branches)} branch(es) を削除しますか?")
           if not confirm:
               raise typer.Abort()

       # 削除
       deleted = 0
       for branch in branches:
           if git.delete_branch(repo_path, branch):
               deleted += 1

       console.print(f"[green]✓[/] {deleted}/{len(branches)} branch(es) deleted")
   ```

### 完了条件

- `setup-repo sync` でリポジトリ同期ができる
- `setup-repo cleanup` でブランチ削除ができる
- `--help` で各コマンドのヘルプが表示される
- Tab 補完が動作する

---

## Phase 8: テスト

**目的:** 新しい実装のテストを作成

### 実装内容

1. **テスト構造**

   ```
   tests/
   ├── conftest.py           # 共通フィクスチャ
   ├── unit/
   │   ├── test_config.py    # 設定テスト
   │   ├── test_github.py    # GitHub API テスト
   │   ├── test_git.py       # Git 操作テスト
   │   ├── test_parallel.py  # 並列処理テスト
   │   └── test_models.py    # モデルテスト
   └── integration/
       └── test_cli.py       # CLI 統合テスト
   ```

2. **フィクスチャ**

   ```python
   # tests/conftest.py
   import pytest
   from pathlib import Path
   from unittest.mock import MagicMock

   from setup_repo.models.config import AppSettings, reset_settings

   @pytest.fixture
   def temp_dir(tmp_path: Path) -> Path:
       return tmp_path

   @pytest.fixture
   def mock_settings(monkeypatch) -> AppSettings:
       settings = AppSettings(
           github_owner="test-user",
           github_token="test-token",
           workspace_dir=Path("/tmp/test-workspace"),
       )
       monkeypatch.setattr("setup_repo.models.config.get_settings", lambda: settings)
       return settings

   @pytest.fixture(autouse=True)
   def reset_settings_cache():
       yield
       reset_settings()
   ```

### 完了条件

- 各モジュールのユニットテストがパスする
- CLI 統合テストがパスする
- カバレッジ 80% 以上

---

## Phase 9: マイグレーションと統合

**目的:** 既存コードからの移行と最終統合

### 実装内容

1. **既存機能の移行確認**

   - [ ] setup コマンド
   - [ ] sync コマンド
   - [ ] cleanup コマンド
   - [ ] quality コマンド（必要に応じて）
   - [ ] template コマンド（必要に応じて）
   - [ ] backup コマンド（必要に応じて）

2. **ドキュメント更新**

   - README.md の更新
   - CHANGELOG.md への記載
   - マイグレーションガイドの作成

3. **ブランチマージ**

   ```bash
   git checkout main
   git merge feature/v2-rewrite
   git tag v2.0.0
   git push origin main --tags
   ```

### 完了条件

- 既存の主要機能が動作する
- ドキュメントが更新されている
- v2.0.0 としてリリースされている

---

## 技術スタック詳細

### 依存関係一覧

```toml
[project]
dependencies = [
    # CLI
    "typer[all]>=0.21.0",       # CLI フレームワーク（Click + Rich 統合）

    # 出力
    "rich>=14.2.0",             # コンソール出力

    # ログ
    "structlog>=25.5.0",        # 構造化ログ

    # HTTP
    "httpx>=0.28.1",            # HTTP クライアント

    # データ
    "pydantic>=2.12.5",         # バリデーション
    "pydantic-settings>=2.12.0", # 設定管理
]

[dependency-groups]
dev = [
    "pytest>=9.0.0",
    "pytest-cov>=7.0.0",
    "pytest-xdist>=3.8.0",
    "ruff>=0.14.0",
    "basedpyright[all]",
    "pre-commit>=4.0.0",
]
```

### アーキテクチャ図

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │  sync   │  │ cleanup │  │ config  │  │  ...    │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       │            │            │            │              │
│  ┌────┴────────────┴────────────┴────────────┴────┐        │
│  │              Typer Application                  │        │
│  └────────────────────────────────────────────────┘        │
│       │                                                     │
│  ┌────┴────────────────────────────────────────────┐       │
│  │              Rich Output Helper                  │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                         Core Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  GitOperations│  │ GitHubClient │  │ParallelProcessor│   │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│       │                  │                  │               │
│  ┌────┴──────────────────┴──────────────────┴────┐         │
│  │              Structlog + Pydantic              │         │
│  └────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                    Infrastructure Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   subprocess │  │    httpx     │  │  filesystem  │      │
│  │    (git)     │  │  (GitHub)    │  │   (pathlib)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 実装順序

```
Phase 0: プロジェクト基盤
    ↓
Phase 1: ロギング (Structlog)
    ↓
Phase 2: 設定管理 (Pydantic Settings)
    ↓
Phase 3: データモデル (Pydantic)
    ↓
Phase 4: GitHub API (httpx)
    ↓
Phase 5: Git 操作
    ↓
Phase 6: 並列処理 (ThreadPoolExecutor + Rich)
    ↓
Phase 7: CLI (Typer + Rich)
    ↓
Phase 8: テスト
    ↓
Phase 9: マイグレーションと統合
```

---

## リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| 既存機能の欠落 | 高 | Phase 9 で移行チェックリストを使用 |
| テストカバレッジ低下 | 中 | 各 Phase でテストを同時作成 |
| 依存関係の競合 | 低 | uv による厳格な依存管理 |
| パフォーマンス劣化 | 低 | Phase 6 で並列処理を確実に実装 |

---

## 成功指標

1. **機能**
   - 既存の主要コマンド（sync, cleanup）が動作する
   - 並列処理で 10 リポジトリ以上の処理が 80% 高速化

2. **品質**
   - テストカバレッジ 80% 以上
   - Ruff/Pyright エラー 0

3. **DX (Developer Experience)**
   - `--help` で分かりやすいヘルプが表示される
   - Tab 補完が動作する
   - カラフルで見やすい出力
