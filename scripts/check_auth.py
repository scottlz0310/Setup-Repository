#!/usr/bin/env python3
"""GitHub API認証確認スクリプト"""

import json
import os
from pathlib import Path

import requests


def check_github_auth():
    """GitHub認証状況を確認"""
    print("🔍 GitHub認証状況を確認中...")

    # 1. 環境変数からトークンを確認
    env_token = os.getenv("GITHUB_TOKEN")
    print(f"環境変数 GITHUB_TOKEN: {'✅ 設定済み' if env_token else '❌ 未設定'}")

    # 2. config.local.jsonからトークンを確認
    config_path = Path("config.local.json")
    config_token = None
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                config_token = config.get("github_token")
                print(f"config.local.json トークン: {'✅ 設定済み' if config_token else '❌ 未設定'}")
                if config_token:
                    print(f"  値: {config_token[:10]}..." if len(config_token) > 10 else f"  値: {config_token}")
        except Exception as e:
            print(f"❌ config.local.json読み込みエラー: {e}")
    else:
        print("❌ config.local.json が見つかりません")

    # 3. 有効なトークンを特定
    token = env_token or config_token
    if not token:
        print("\n❌ GitHubトークンが見つかりません")
        print("以下のいずれかの方法でトークンを設定してください：")
        print("1. 環境変数: export GITHUB_TOKEN=your_token")
        print("2. config.local.json: github_token フィールドを設定")
        return False

    # 4. トークンの有効性を確認
    print("\n🔍 トークンの有効性を確認中...")
    try:
        headers = {"Authorization": f"token {token}", "User-Agent": "setup-repo-auth-check/1.0"}

        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)

        if response.status_code == 200:
            user_data = response.json()
            print("✅ 認証成功!")
            print(f"  ユーザー: {user_data.get('login')}")
            print(f"  名前: {user_data.get('name', 'N/A')}")
            print(f"  プライベートリポジトリ数: {user_data.get('total_private_repos', 'N/A')}")
            print(f"  パブリックリポジトリ数: {user_data.get('public_repos', 'N/A')}")

            # レート制限情報も表示
            remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
            limit = response.headers.get("X-RateLimit-Limit", "N/A")
            print(f"  APIレート制限: {remaining}/{limit}")
            return True

        elif response.status_code == 401:
            print("❌ 認証失敗: トークンが無効です")
            print("  新しいPersonal Access Tokenを生成してください:")
            print("  https://github.com/settings/tokens")
            return False

        elif response.status_code == 403:
            print("❌ APIレート制限に達しています")
            print(f"  リセット時刻: {response.headers.get('X-RateLimit-Reset', 'N/A')}")
            return False

        else:
            print(f"❌ 予期しないエラー: {response.status_code}")
            print(f"  レスポンス: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ ネットワークエラー: {e}")
        return False


if __name__ == "__main__":
    success = check_github_auth()
    exit(0 if success else 1)
