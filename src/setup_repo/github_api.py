#!/usr/bin/env python3
"""GitHub API操作モジュール"""

from typing import Optional

import requests


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
            response = requests.get("https://api.github.com/user", headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"GitHub API エラー: {e.response.status_code}"
            if e.response.status_code == 401:
                error_msg += " - 認証に失敗しました。トークンを確認してください。"
            elif e.response.status_code == 403:
                error_msg += " - APIレート制限に達しました。"
            elif e.response.status_code == 404:
                error_msg += " - ユーザーが見つかりません。"
            raise GitHubAPIError(error_msg) from e
        except ValueError as e:
            raise GitHubAPIError(f"レスポンスの解析に失敗しました: {e}") from e
        except requests.exceptions.RequestException as e:
            raise GitHubAPIError(f"ネットワークエラー: {e}") from e

    def get_user_repos(self) -> list[dict]:
        """ユーザーのリポジトリ一覧を取得"""
        repos = []
        page = 1

        while True:
            try:
                response = requests.get(
                    "https://api.github.com/user/repos",
                    headers=self.headers,
                    params={
                        "per_page": "100",
                        "page": str(page),
                        "affiliation": "owner,collaborator,organization_member",
                    },
                    timeout=30,
                )
                response.raise_for_status()
                page_repos = response.json()

                if not page_repos:
                    break

                repos.extend(page_repos)
                page += 1

            except requests.exceptions.HTTPError as e:
                error_msg = f"GitHub API エラー: {e.response.status_code}"
                if e.response.status_code == 401:
                    error_msg += " - 認証に失敗しました。"
                elif e.response.status_code == 403:
                    error_msg += " - APIレート制限に達しました。"
                raise GitHubAPIError(error_msg) from e
            except ValueError as e:
                raise GitHubAPIError(f"レスポンスの解析に失敗しました: {e}") from e
            except requests.exceptions.RequestException as e:
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
            response = requests.get(url, headers=headers, params={"page": str(page)}, timeout=30)
            response.raise_for_status()
            page_repos = response.json()

            if not page_repos:
                break

            repos.extend(page_repos)
            page += 1

        except requests.exceptions.HTTPError as e:
            if page == 1:  # 最初のページでエラーの場合のみ表示
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"GitHub API エラー: {e.response.status_code}")
            break
        except ValueError as e:
            if page == 1:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"JSON解析エラー: {e}")
            break
        except requests.exceptions.RequestException as e:
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
        response = requests.get("https://api.github.com/user", headers=headers, timeout=30)
        response.raise_for_status()
        user_data = response.json()
        return user_data.get("login")

    except (requests.exceptions.RequestException, ValueError):
        return None
