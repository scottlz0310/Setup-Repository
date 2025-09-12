"""セキュリティ関連のユーティリティ関数"""

import html
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


class SecurityValidator:
    """セキュリティ検証クラス"""

    # 危険なパターンの定義
    DANGEROUS_PATH_PATTERNS = [
        r"\.\./",  # パストラバーサル
        r"\.\.\\",  # Windows パストラバーサル
        r"/etc/",  # システムファイル
        r"C:\\Windows",  # Windows システム
    ]

    DANGEROUS_COMMAND_PATTERNS = [
        r"[;&|`$]",  # コマンドインジェクション
        r"rm\s+-rf",  # 危険なコマンド
        r"sudo\s+",  # 権限昇格
    ]

    @classmethod
    def validate_path(cls, path: str) -> bool:
        """パスの安全性検証"""
        for pattern in cls.DANGEROUS_PATH_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                logger.warning(f"Dangerous path pattern detected: {path}")
                return False
        return True

    @classmethod
    def validate_command_args(cls, args: list[str]) -> bool:
        """コマンド引数の安全性検証"""
        for arg in args:
            for pattern in cls.DANGEROUS_COMMAND_PATTERNS:
                if re.search(pattern, arg):
                    logger.warning(f"Dangerous command pattern detected: {arg}")
                    return False
        return True

    @classmethod
    def sanitize_html_content(cls, content: str) -> str:
        """HTMLコンテンツのサニタイズ"""
        # HTMLエスケープ
        escaped = html.escape(content, quote=True)

        # 追加のサニタイズ（必要に応じて）
        # script タグの完全除去
        escaped = re.sub(r"<script.*?</script>", "", escaped, flags=re.IGNORECASE | re.DOTALL)

        return escaped


class SecurePathHandler:
    """セキュアなパス操作クラス"""

    @staticmethod
    def safe_join(base: Union[str, Path], *parts: str) -> Path:
        """セキュアなパス結合"""
        base_path = Path(base).resolve()

        # 各パート要素の検証
        for part in parts:
            if not part or part in (".", ".."):
                raise ValueError(f"Invalid path component: {part}")
            if any(char in part for char in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]):
                raise ValueError(f"Invalid characters in path: {part}")

        target_path = base_path.joinpath(*parts).resolve()

        # パストラバーサル検証
        try:
            target_path.relative_to(base_path)
        except ValueError:
            raise ValueError("Path traversal attempt detected") from None

        return target_path

    @staticmethod
    def validate_config_path(base_path: str, user_input: str) -> str:
        """設定ファイルパスの安全な検証"""
        if not user_input:
            raise ValueError("Empty path not allowed")

        # 許可された拡張子のチェック
        allowed_extensions = {".json", ".yaml", ".yml", ".toml", ".ini"}
        if not any(user_input.endswith(ext) for ext in allowed_extensions):
            raise ValueError("Invalid file extension")

        safe_path = SecurePathHandler.safe_join(base_path, user_input)
        return str(safe_path)


class SecureCommandRunner:
    """セキュアなコマンド実行クラス"""

    def __init__(self):
        self.verified_commands = {}

    def verify_command(self, command: str) -> str:
        """コマンドの存在確認とパス取得"""
        if command not in self.verified_commands:
            cmd_path = shutil.which(command)
            if not cmd_path:
                raise FileNotFoundError(f"Command '{command}' not found")
            self.verified_commands[command] = cmd_path
        return self.verified_commands[command]

    def run_secure_command(
        self, command: str, args: list[str], timeout: int = 60, cwd: Optional[Path] = None
    ) -> subprocess.CompletedProcess:
        """セキュアなコマンド実行"""
        cmd_path = self.verify_command(command)

        # 引数の検証
        if not SecurityValidator.validate_command_args(args):
            raise ValueError("Dangerous command arguments detected")

        return subprocess.run(
            [cmd_path] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            shell=False,  # 明示的にshell=Falseを指定
        )


def secure_html_render(template: str, **kwargs) -> str:
    """セキュアなHTML生成"""
    escaped_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, str):
            escaped_kwargs[key] = html.escape(value)
        elif isinstance(value, list):
            escaped_kwargs[key] = [html.escape(str(item)) if isinstance(item, str) else item for item in value]  # type: ignore[assignment]
        else:
            escaped_kwargs[key] = value

    return template.format(**escaped_kwargs)
