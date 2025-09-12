#!/usr/bin/env python3
"""GitHub API操作モジュール"""

import json
import urllib.error
import urllib.request
from typing import Optional


class GitHubAPIError(Exception):
    """GitHub API関連のエラー"""

    pass


class GitHubAPI:
    """GitHub API操作クラス"""

    def __init__(self, token: str, username: str):
        """GitHub APIクライアントを初期化"""
        if not token:
            raise GitHubAPIError("GitHubトークンが必要です")
        if not username:
            raise GitHubAPIError("GitHubユーザー名が必要です")

        self.token = token
        self.username = username
        self.headers = {
            "User-Agent": "setup-repo/1.0",
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_user_info(self) -> dict:
        """認証されたユーザーの情報を取得"""
        try:
            import ssl
            import urllib.request

            # HTTPSのみ許可し、SSL検証を強制
            url = "https://api.github.com/user"
            if not url.startswith("https://"):
                raise ValueError("HTTPS URLのみ許可されています")

            req = urllib.request.Request(url, headers=self.headers)
            # SSL検証を強制するコンテキストを作成
            context = ssl.create_default_context()
            with urllib.request.urlopen(req, context=context) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_msg = f"GitHub API エラー: {e.code} {e.reason}"
            if e.code == 401:
                error_msg += " - 認証に失敗しました。トークンを確認してください。"
            elif e.code == 403:
                error_msg += " - APIレート制限に達しました。"
            elif e.code == 404:
                error_msg += " - ユーザーが見つかりません。"
            raise GitHubAPIError(error_msg) from e
        except Exception as e:
            raise GitHubAPIError(f"ネットワークエラー: {e}") from e

    def get_user_repos(self) -> list[dict]:
        """ユーザーのリポジトリ一覧を取得"""
        repos = []
        page = 1

        while True:
            try:
                url = f"https://api.github.com/user/repos?per_page=100&page={page}&affiliation=owner,collaborator,organization_member"
                req = urllib.request.Request(url, headers=self.headers)

                with urllib.request.urlopen(req) as response:
                    page_repos = json.loads(response.read().decode())

                    if not page_repos:
                        break

                    repos.extend(page_repos)
                    page += 1

            except urllib.error.HTTPError as e:
                error_msg = f"GitHub API エラー: {e.code} {e.reason}"
                if e.code == 401:
                    error_msg += " - 認証に失敗しました。"
                elif e.code == 403:
                    error_msg += " - APIレート制限に達しました。"
                raise GitHubAPIError(error_msg) from e
            except Exception as e:
                raise GitHubAPIError(f"ネットワークエラー: {e}") from e

        return repos


def get_repositories(owner: str, token: Optional[str] = None) -> list[dict]:
    """GitHub APIからリポジトリ一覧を取得（プライベートリポジトリ対応）"""
    headers = {"User-Agent": "repo-sync/1.0"}

    if not token:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("GitHubトークンが設定されていません。プライベートリポジトリは取得できません。")
        url = f"https://api.github.com/users/{owner}/repos?per_page=100"
        logger.info(f"'{owner}' のパブリックリポジトリのみ取得中...")
    else:
        headers["Authorization"] = f"token {token}"

        # 認証ユーザーを確認
        auth_user = _get_authenticated_user(token)
        if auth_user and auth_user.lower() == owner.lower():
            # 自分のリポジトリの場合は /user/repos を使用
            url = "https://api.github.com/user/repos?per_page=100&affiliation=owner,collaborator,organization_member"
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"認証ユーザー '{auth_user}' としてプライベートリポジトリを取得中...")
        else:
            # 他のユーザーの場合は /users/{owner}/repos を使用
            url = f"https://api.github.com/users/{owner}/repos?per_page=100"
            if auth_user:
                import logging

                logger = logging.getLogger(__name__)
                logger.info(f"認証ユーザー '{auth_user}' で '{owner}' のパブリックリポジトリを取得中...")

    repos = []
    page = 1

    while True:
        try:
            page_url = f"{url}&page={page}"
            req = urllib.request.Request(page_url, headers=headers)

            # HTTPS URLのみ許可してセキュリティを確保
            if not page_url.startswith("https://"):
                raise ValueError("HTTPS URLのみ許可されています")

            import ssl

            context = ssl.create_default_context()
            with urllib.request.urlopen(req, context=context) as response:
                page_repos = json.loads(response.read().decode())

                if not page_repos:
                    break

                repos.extend(page_repos)
                page += 1

        except urllib.error.HTTPError as e:
            if page == 1:  # 最初のページでエラーの場合のみ表示
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"GitHub API エラー: {e.code} {e.reason}")
            break
        except Exception as e:
            if page == 1:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"リポジトリ取得エラー: {e}")
            break

    return repos


def _get_authenticated_user(token: str) -> Optional[str]:
    """認証されたユーザー名を取得"""
    try:
        headers = {"User-Agent": "repo-sync/1.0", "Authorization": f"token {token}"}
        req = urllib.request.Request("https://api.github.com/user", headers=headers)

        # HTTPS URLのみ許可してセキュリティを確保
        import ssl

        context = ssl.create_default_context()
        with urllib.request.urlopen(req, context=context) as response:
            user_data = json.loads(response.read().decode())
            return user_data.get("login")

    except (urllib.error.HTTPError, Exception):
        return None
