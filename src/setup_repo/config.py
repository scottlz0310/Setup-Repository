"""設定管理モジュール"""

import json
import os
import subprocess
from pathlib import Path


def get_github_token() -> str | None:
    """環境変数またはgh CLIからGitHubトークンを自動検出"""
    # 環境変数を最初に試す
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token

    # gh CLIをフォールバックとして試す
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def get_github_user() -> str | None:
    """GitHubユーザー名の自動検出"""
    user = os.getenv("GITHUB_USER")
    if user:
        return user

    try:
        result = subprocess.run(
            ["git", "config", "--global", "user.name"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def auto_detect_config() -> dict:
    """環境から設定を自動検出"""
    config = {
        "owner": get_github_user() or "",
        "dest": str(Path.home() / "workspace"),
        "github_token": get_github_token(),
        "use_https": False,
        "max_retries": 2,
        "skip_uv_install": False,
        "auto_stash": False,
        "sync_only": False,
        "log_file": str(Path.home() / "logs" / "repo-sync.log"),
    }

    return config


def load_config() -> dict:
    """自動検出フォールバック付きで設定を読み込み"""
    # 自動検出した設定から開始
    config = auto_detect_config()

    # CONFIG_PATH環境変数が設定されている場合はそのディレクトリを使用
    config_dir = Path(os.getenv("CONFIG_PATH", "."))

    # ファイル設定が存在する場合は上書き
    config_files = ["config.local.json", "config.json"]
    for config_file in config_files:
        if config_dir.is_dir():
            config_path = config_dir / config_file
        else:
            # CONFIG_PATHが直接ファイルを指している場合
            if config_dir.name == config_file:
                config_path = config_dir
            else:
                config_path = Path(config_file)

        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                file_config = json.load(f)
                config.update(file_config)
            break

    # 環境変数による上書き（最優先）
    env_overrides = {
        "github_token": os.getenv("GITHUB_TOKEN"),
        "github_username": os.getenv("GITHUB_USERNAME"),
        "clone_destination": os.getenv("CLONE_DESTINATION"),
    }

    for key, value in env_overrides.items():
        if value is not None:
            config[key] = value

    return config
