"""セキュリティヘルパー関数

セキュリティ脆弱性を防ぐための共通ユーティリティ関数群
"""

import os
import shutil
import subprocess
import html
import logging
from pathlib import Path
from typing import List, Any, Optional

logger = logging.getLogger(__name__)


def safe_path_join(base: Path, user_path: str) -> Path:
    """パストラバーサル攻撃を防ぐ安全なパス結合
    
    Args:
        base: ベースディレクトリ
        user_path: ユーザー入力パス
        
    Returns:
        安全に結合されたパス
        
    Raises:
        ValueError: パストラバーサル攻撃を検出した場合
    """
    if not user_path:
        raise ValueError("Empty path not allowed")
        
    resolved = (base / user_path).resolve()
    base_resolved = base.resolve()
    
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError(f"Path traversal detected: {user_path}")
        
    return resolved


def safe_subprocess(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """コマンドインジェクション攻撃を防ぐ安全なsubprocess実行
    
    Args:
        cmd: 実行するコマンドのリスト
        **kwargs: subprocess.runに渡す追加引数
        
    Returns:
        subprocess.CompletedProcess
        
    Raises:
        ValueError: 空のコマンドの場合
        FileNotFoundError: 実行可能ファイルが見つからない場合
    """
    if not cmd:
        raise ValueError("Empty command not allowed")
        
    # 実行可能ファイルの絶対パス解決
    if not os.path.isabs(cmd[0]):
        executable = shutil.which(cmd[0])
        if not executable:
            raise FileNotFoundError(f"Executable not found: {cmd[0]}")
        cmd = [executable] + cmd[1:]
    
    # デフォルトタイムアウト設定
    kwargs.setdefault('timeout', 30)
    kwargs.setdefault('check', True)
    
    return subprocess.run(cmd, **kwargs)


def safe_html_escape(data: Any) -> str:
    """XSS攻撃を防ぐHTMLエスケープ
    
    Args:
        data: エスケープするデータ
        
    Returns:
        エスケープされた文字列
    """
    return html.escape(str(data), quote=True)


def validate_file_path(file_path: Path, allowed_extensions: Optional[List[str]] = None) -> bool:
    """ファイルパスの安全性を検証
    
    Args:
        file_path: 検証するファイルパス
        allowed_extensions: 許可する拡張子のリスト
        
    Returns:
        安全な場合True
    """
    try:
        # パスの正規化
        normalized = file_path.resolve()
        
        # 危険な文字列のチェック
        dangerous_patterns = ['..', '~', '$']
        path_str = str(normalized)
        
        for pattern in dangerous_patterns:
            if pattern in path_str:
                logger.warning(f"Dangerous pattern '{pattern}' found in path: {path_str}")
                return False
                
        # 拡張子チェック
        if allowed_extensions:
            if file_path.suffix.lower() not in allowed_extensions:
                logger.warning(f"File extension '{file_path.suffix}' not allowed")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Path validation failed: {e}")
        return False


class SecurityError(Exception):
    """セキュリティ関連のエラー"""
    pass


class PathTraversalError(SecurityError):
    """パストラバーサル攻撃エラー"""
    pass


class CommandInjectionError(SecurityError):
    """コマンドインジェクション攻撃エラー"""
    pass


def validate_session_data(session_data: Any) -> bool:
    """セッションデータの妥当性を検証
    
    Args:
        session_data: 検証するセッションデータ
        
    Returns:
        有効な場合True
    """
    if not isinstance(session_data, dict):
        return False
        
    required_fields = ['user_id', 'session_id', 'created_at']
    return all(field in session_data for field in required_fields)


def check_admin_role(session_data: dict) -> bool:
    """サーバーサイドセッションベースの認証チェック
    
    Args:
        session_data: セッションデータ
        
    Returns:
        管理者権限がある場合True
    """
    if not validate_session_data(session_data):
        return False
        
    return session_data.get('authenticated_role') == 'admin'


def sanitize_user_input(user_input: Any, max_length: int = 1000) -> str:
    """ユーザー入力の無害化
    
    Args:
        user_input: ユーザー入力
        max_length: 最大長
        
    Returns:
        無害化された文字列
    """
    if not isinstance(user_input, str):
        return ""
        
    # 危険な文字を除去
    dangerous_chars = ['<', '>', '"', "'", '&']
    sanitized = user_input
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
        
    # 長さ制限
    return sanitized[:max_length]


# 後方互換性のためのエイリアス
safe_subprocess_run = safe_subprocess