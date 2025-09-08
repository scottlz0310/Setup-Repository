#!/usr/bin/env python3
"""GitHub API操作モジュール"""
import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional


def get_repositories(owner: str, token: Optional[str] = None) -> List[Dict]:
    """GitHub APIからリポジトリ一覧を取得（プライベートリポジトリ対応）"""
    headers = {'User-Agent': 'repo-sync/1.0'}
    
    if not token:
        print("⚠️  GitHubトークンが設定されていません。プライベートリポジトリは取得できません。")
        url = f"https://api.github.com/users/{owner}/repos?per_page=100"
        print(f"🌍 '{owner}' のパブリックリポジトリのみ取得中...")
    else:
        headers['Authorization'] = f'token {token}'
        
        # 認証ユーザーを確認
        auth_user = _get_authenticated_user(token)
        if auth_user and auth_user.lower() == owner.lower():
            # 自分のリポジトリの場合は /user/repos を使用
            url = "https://api.github.com/user/repos?per_page=100&affiliation=owner,collaborator,organization_member"
            print(f"🔑 認証ユーザー '{auth_user}' としてプライベートリポジトリを取得中...")
        else:
            # 他のユーザーの場合は /users/{owner}/repos を使用
            url = f"https://api.github.com/users/{owner}/repos?per_page=100"
            if auth_user:
                print(f"🔍 認証ユーザー '{auth_user}' で '{owner}' のパブリックリポジトリを取得中...")
    
    repos = []
    page = 1
    
    while True:
        try:
            page_url = f"{url}&page={page}"
            req = urllib.request.Request(page_url, headers=headers)
            
            with urllib.request.urlopen(req) as response:
                page_repos = json.loads(response.read().decode())
                
                if not page_repos:
                    break
                
                repos.extend(page_repos)
                page += 1
                
        except urllib.error.HTTPError as e:
            if page == 1:  # 最初のページでエラーの場合のみ表示
                print(f"❌ GitHub API エラー: {e.code} {e.reason}")
            break
        except Exception as e:
            if page == 1:
                print(f"❌ リポジトリ取得エラー: {e}")
            break
    
    return repos


def _get_authenticated_user(token: str) -> Optional[str]:
    """認証されたユーザー名を取得"""
    try:
        headers = {
            'User-Agent': 'repo-sync/1.0',
            'Authorization': f'token {token}'
        }
        req = urllib.request.Request("https://api.github.com/user", headers=headers)
        
        with urllib.request.urlopen(req) as response:
            user_data = json.loads(response.read().decode())
            return user_data.get('login')
            
    except (urllib.error.HTTPError, Exception):
        return None