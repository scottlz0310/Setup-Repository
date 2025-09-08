"""CLI コマンドハンドラー"""
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional

from .config import load_config, auto_detect_config
from .setup import setup_dependencies, create_personal_config
from .sync import sync_repositories


def setup_cli(args) -> None:
    """初期セットアップコマンド"""
    print("🔧 初期セットアップを開始します...")
    
    # 依存関係チェック
    if not setup_dependencies():
        return
    
    # 個人設定作成
    create_personal_config()
    
    print("\\n✅ セットアップ完了! 次の手順:")
    print("   1. 必要に応じて config.local.json を確認/編集")
    print("   2. 実行: python main.py sync --dry-run")
    print("   3. 実行: python main.py sync")


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