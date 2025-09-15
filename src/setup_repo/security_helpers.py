"""セキュリティヘルパー関数

Path Traversal、Command Injection、XSS攻撃を防ぐための共通ユーティリティ関数を提供します。
"""

import html
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, List

logger = logging.getLogger(__name__)

# 認証関連の定数
SESSION_TIMEOUT = 3600  # 1時間
MAX_LOGIN_ATTEMPTS = 3


def safe_path_join(base: Path, user_path: str) -> Path:
    """パストラバーサル攻撃を防ぐ安全なパス結合
    
    Args:
        base: ベースディレクトリパス
        user_path: ユーザー入力パス
        
    Returns:
        安全に結合されたパス
        
    Raises:
        ValueError: パストラバーサル攻撃が検出された場合
    """
    if not user_path:
        return base
        
    resolved = (base / user_path).resolve()
    base_resolved = base.resolve()
    
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError(f"Path traversal detected: {user_path}")
    
    return resolved


def safe_subprocess(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """コマンドインジェクション攻撃を防ぐ安全なsubprocess実行
    
    Args:
        cmd: 実行するコマンドリスト
        **kwargs: subprocess.runに渡す追加引数
        
    Returns:
        subprocess.CompletedProcess結果
        
    Raises:
        ValueError: 空のコマンドが渡された場合
        FileNotFoundError: 実行可能ファイルが見つからない場合
    """
    if not cmd:
        raise ValueError("Empty command")
    
    # 実行可能ファイルの絶対パス解決
    if not os.path.isabs(cmd[0]):
        executable = shutil.which(cmd[0])
        if not executable:
            raise FileNotFoundError(f"Executable not found: {cmd[0]}")
        cmd[0] = executable
    
    # デフォルトタイムアウト設定
    kwargs.setdefault('timeout', 30)
    
    return subprocess.run(cmd, **kwargs)


def safe_html_escape(data: Any) -> str:
    """XSS攻撃を防ぐHTMLエスケープ
    
    Args:
        data: エスケープするデータ
        
    Returns:
        HTMLエスケープされた文字列
    """
    return html.escape(str(data), quote=True)


def validate_file_path(file_path: Path, allowed_extensions: List[str] = None) -> bool:
    """ファイルパスの安全性を検証
    
    Args:
        file_path: 検証するファイルパス
        allowed_extensions: 許可する拡張子のリスト
        
    Returns:
        パスが安全な場合True
    """
    try:
        # パスの正規化
        normalized = file_path.resolve()
        
        # 拡張子チェック
        if allowed_extensions:
            if not any(str(normalized).endswith(ext) for ext in allowed_extensions):
                return False
        
        # 危険なパターンチェック
        dangerous_patterns = ['..', '~', '$']
        path_str = str(normalized)
        
        return not any(pattern in path_str for pattern in dangerous_patterns)
        
    except (OSError, ValueError):
        return False


def validate_session_data(session_data: dict[str, Any]) -> bool:
    """セッションデータの有効性を検証
    
    Args:
        session_data: 検証するセッションデータ
        
    Returns:
        セッションが有効な場合True
    """
    if not isinstance(session_data, dict):
        return False
    
    required_fields = ['user_id', 'session_id', 'created_at']
    return all(field in session_data for field in required_fields)


def check_admin_role(session_data: dict[str, Any]) -> bool:
    """サーバーサイドセッションベースの管理者権限チェック
    
    Args:
        session_data: セッションデータ
        
    Returns:
        管理者権限がある場合True
    """
    if not validate_session_data(session_data):
        logger.warning("無効なセッションデータで管理者権限チェックが試行されました")
        return False
    
    # サーバーサイドで検証された認証済みロールのみを信頼
    authenticated_role = session_data.get('authenticated_role')
    return authenticated_role == 'admin'


def sanitize_user_input(user_input: str, max_length: int = 1000) -> str:
    """ユーザー入力の安全な無害化
    
    Args:
        user_input: ユーザー入力文字列
        max_length: 最大許可文字数
        
    Returns:
        無害化された文字列
    """
    if not isinstance(user_input, str):
        return ""
    
    # 長さ制限
    sanitized = user_input[:max_length]
    
    # 危険な文字を除去
    dangerous_chars = ['<', '>', '&', '"', "'", '\x00']
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    return sanitized.strip()