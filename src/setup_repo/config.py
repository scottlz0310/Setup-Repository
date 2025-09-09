"""設定管理モジュール"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional


def get_github_token() -> Optional[str]:
    """環境変数またはgh CLIからGitHubトークンを自動検出"""
    # 環境変数を最初に試す
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token

    # gh CLIをフォールバックとして試す
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_github_user() -> Optional[str]:
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
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def auto_detect_config() -> Dict:
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


def load_config() -> Dict:
    """自動検出フォールバック付きで設定を読み込み"""
    # 自動検出した設定から開始
    config = auto_detect_config()

    # ファイル設定が存在する場合は上書き
    config_files = ["config.local.json", "config.json"]
    for config_file in config_files:
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path) as f:
                file_config = json.load(f)
                config.update(file_config)
            break

    return config
