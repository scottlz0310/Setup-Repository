"""CLI コマンドハンドラー"""
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional

from .config import load_config, auto_detect_config
from .setup import run_interactive_setup
from .sync import sync_repositories


def setup_cli(args) -> None:
    """初期セットアップコマンド"""
    run_interactive_setup()


def sync_cli(args) -> None:
    """リポジトリ同期コマンド"""
    config = load_config()
    
    # コマンドライン引数で設定を上書き
    if args.owner:
        config["owner"] = args.owner
    if args.dest:
        config["dest"] = args.dest
    
    config.update({
        'dry_run': args.dry_run,
        'force': args.force,
        'use_https': args.use_https or config.get('use_https', False),
        'sync_only': args.sync_only or config.get('sync_only', False),
        'auto_stash': args.auto_stash or config.get('auto_stash', False),
        'skip_uv_install': args.skip_uv_install or config.get('skip_uv_install', False)
    })
    
    # リポジトリ同期実行
    sync_repositories(config)