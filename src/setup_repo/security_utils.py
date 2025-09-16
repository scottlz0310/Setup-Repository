"""セキュリティ関連のユーティリティ関数"""

import html
import logging
import re
import shutil
import subprocess
from pathlib import Path

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
    def safe_join(base: str | Path, *parts: str) -> Path:
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
        self, command: str, args: list[str], timeout: int = 60, cwd: Path | None = None
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


def scan_for_secrets(content: str) -> dict[str, list[dict[str, str]]]:
    """コンテンツ内のシークレットをスキャン"""
    secrets_found: dict[str, list[dict[str, str]]] = {
        "api_keys": [],
        "tokens": [],
        "passwords": [],
        "private_keys": [],
    }

    # APIキーのパターン
    api_key_patterns = [
        (r"(?i)api[_-]?key[\s]*[=:][\s]*['\"]?([a-zA-Z0-9_-]{20,})['\"]?", "API Key"),
        (r"(?i)github[_-]?token[\s]*[=:][\s]*['\"]?([a-zA-Z0-9_-]{20,})['\"]?", "GitHub Token"),
        (r"(?i)secret[_-]?key[\s]*[=:][\s]*['\"]?([a-zA-Z0-9_-]{20,})['\"]?", "Secret Key"),
    ]

    for pattern, secret_type in api_key_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            secrets_found["api_keys"].append(
                {
                    "type": secret_type,
                    "value": match.group(1)[:10] + "...",  # 部分的に表示
                    "line": str(content[: match.start()].count("\n") + 1),
                    "position": str(match.start()),
                }
            )

    # パスワードのパターン
    password_patterns = [
        (r"(?i)password[\s]*[=:][\s]*['\"]?([^\s'\"]{8,})['\"]?", "Password"),
        (r"(?i)passwd[\s]*[=:][\s]*['\"]?([^\s'\"]{8,})['\"]?", "Password"),
    ]

    for pattern, secret_type in password_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            # 明らかにプレースホルダーやテスト値は除外
            value = match.group(1)
            if value.lower() in ["password", "your_password", "test", "example", "placeholder"]:
                continue  # type: ignore[unreachable]

            secrets_found["passwords"].append(
                {
                    "type": secret_type,
                    "value": "***",  # パスワードは非表示
                    "line": str(content[: match.start()].count("\n") + 1),
                    "position": str(match.start()),
                }
            )

    # 秘密鍵のパターン
    private_key_patterns = [
        (r"-----BEGIN [A-Z ]+PRIVATE KEY-----", "Private Key"),
        (r"-----BEGIN RSA PRIVATE KEY-----", "RSA Private Key"),
        (r"-----BEGIN OPENSSH PRIVATE KEY-----", "OpenSSH Private Key"),
    ]

    for pattern, secret_type in private_key_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            secrets_found["private_keys"].append(
                {
                    "type": secret_type,
                    "value": "[PRIVATE KEY DETECTED]",
                    "line": str(content[: match.start()].count("\n") + 1),
                    "position": str(match.start()),
                }
            )

    return secrets_found


def validate_input(input_data: str, input_type: str = "general") -> dict[str, bool | str | list[str]]:
    """入力データのセキュリティ検証"""
    errors = []
    warnings = []

    # 基本的なサニタイゼーション
    if not isinstance(input_data, str):
        errors.append("入力データは文字列である必要があります")
        return {"valid": False, "errors": errors, "warnings": warnings}  # type: ignore[unreachable]

    # 長さチェック
    if len(input_data) > 10000:  # 10KB制限
        errors.append("入力データが長すぎます")  # type: ignore[unreachable]

    # コマンドインジェクションチェック
    dangerous_patterns = [
        r"[;&|`$(){}\[\]]",  # コマンドインジェクション
        r"<script",  # XSS
        r"javascript:",  # JavaScript URL
        r"data:.*base64",  # Data URL
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, input_data, re.IGNORECASE):
            errors.append(f"危険なパターンが検出されました: {pattern}")

    # タイプ別検証
    if input_type == "path":
        if not SecurityValidator.validate_path(input_data):
            errors.append("危険なパスが検出されました")  # type: ignore[unreachable]

    elif input_type == "url":
        url_pattern = r"^https?://[a-zA-Z0-9.-]+(/.*)?$"
        if not re.match(url_pattern, input_data):
            errors.append("URLの形式が無効です")

        # 危険なURLチェック
        dangerous_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]  # nosec B104
        for host in dangerous_hosts:
            if host in input_data.lower():
                warnings.append(f"ローカルホストへのアクセスが検出されました: {host}")

    elif input_type == "email":
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, input_data):
            errors.append("メールアドレスの形式が無効です")

    # シークレットスキャン
    secrets = scan_for_secrets(input_data)
    total_secrets = sum(len(secrets[key]) for key in secrets)
    if total_secrets > 0:
        warnings.append(f"シークレットが検出されました: {total_secrets}件")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "secrets_detected": str(total_secrets),
    }
