"""秘密情報処理セキュリティテスト."""

import json
import platform
import shutil
import tempfile
from pathlib import Path

import pytest

from ..multiplatform.helpers import verify_current_platform


class TestSecretHandlingSecurity:
    """秘密情報処理セキュリティテストクラス."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.platform_info = verify_current_platform()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """テストメソッドの後処理."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.security
    def test_secret_detection_in_files(self):
        """ファイル内の秘密情報検出テスト."""

        # 秘密情報検出関数
        def detect_secrets_in_file(file_path):
            """ファイル内の秘密情報を検出."""
            if not Path(file_path).exists():
                return {"secrets_found": False, "reason": "File does not exist"}

            content = Path(file_path).read_text()

            # 秘密情報パターン
            secret_patterns = {
                "password": [
                    r'password\s*[=:]\s*["\'][^"\']{3,}["\']',
                    r'pwd\s*[=:]\s*["\'][^"\']{3,}["\']',
                    r'passwd\s*[=:]\s*["\'][^"\']{3,}["\']',
                ],
                "api_key": [r'api[_-]?key\s*[=:]\s*["\'][^"\']{10,}["\']', r'apikey\s*[=:]\s*["\'][^"\']{10,}["\']'],
                "token": [
                    r'token\s*[=:]\s*["\'][^"\']{10,}["\']',
                    r'access[_-]?token\s*[=:]\s*["\'][^"\']{10,}["\']',
                    r'auth[_-]?token\s*[=:]\s*["\'][^"\']{10,}["\']',
                ],
                "secret": [
                    r'secret\s*[=:]\s*["\'][^"\']{5,}["\']',
                    r'client[_-]?secret\s*[=:]\s*["\'][^"\']{10,}["\']',
                ],
                "private_key": [r"-----BEGIN\s+PRIVATE\s+KEY-----", r"-----BEGIN\s+RSA\s+PRIVATE\s+KEY-----"],
                "database_url": [
                    r'database[_-]?url\s*[=:]\s*["\'][^"\']*://[^"\']+["\']',
                    r'db[_-]?url\s*[=:]\s*["\'][^"\']*://[^"\']+["\']',
                ],
            }

            detected_secrets = []
            import re

            for secret_type, patterns in secret_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        detected_secrets.append(
                            {
                                "type": secret_type,
                                "pattern": pattern,
                                "match": match.group(),
                                "start": match.start(),
                                "end": match.end(),
                            }
                        )

            return {
                "secrets_found": len(detected_secrets) > 0,
                "detected_secrets": detected_secrets,
                "total_secrets": len(detected_secrets),
            }

        # テストファイル作成
        test_cases = [
            ("clean_config.py", "DEBUG = True\nTIMEOUT = 30", False),
            ("config_with_password.py", "PASSWORD = 'secret123'", True),
            ("api_config.py", "API_KEY = 'abcd1234efgh5678'", True),
            ("database_config.py", "DATABASE_URL = 'postgresql://user:pass@localhost/db'", True),
            (
                "private_key.pem",
                "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...",
                True,
            ),
        ]

        for filename, content, should_detect_secrets in test_cases:
            test_file = self.temp_dir / filename
            test_file.write_text(content)

            result = detect_secrets_in_file(test_file)
            assert result["secrets_found"] == should_detect_secrets

            if should_detect_secrets:
                assert result["total_secrets"] > 0

    @pytest.mark.security
    def test_environment_variable_secret_detection(self):
        """環境変数内の秘密情報検出テスト."""

        # 環境変数秘密情報検出関数
        def detect_secrets_in_env_vars(env_vars):
            """環境変数内の秘密情報を検出."""
            secret_env_patterns = [
                r".*password.*",
                r".*secret.*",
                r".*key.*",
                r".*token.*",
                r".*auth.*",
                r".*credential.*",
            ]

            detected_secrets = []
            import re

            for env_name, env_value in env_vars.items():
                # 環境変数名のチェック
                for pattern in secret_env_patterns:
                    if re.match(pattern, env_name.lower()):
                        detected_secrets.append(
                            {
                                "type": "environment_variable",
                                "name": env_name,
                                "value_length": len(env_value) if env_value else 0,
                                "pattern_matched": pattern,
                            }
                        )
                        break

            return {
                "secrets_found": len(detected_secrets) > 0,
                "detected_secrets": detected_secrets,
                "total_secrets": len(detected_secrets),
            }

        # テスト環境変数
        test_env_vars = {
            "DEBUG": "True",
            "TIMEOUT": "30",
            "DATABASE_PASSWORD": "secret123",
            "API_KEY": "abcd1234efgh5678",
            "SECRET_TOKEN": "xyz789abc123",
            "USER_NAME": "testuser",
        }

        result = detect_secrets_in_env_vars(test_env_vars)
        assert result["secrets_found"] is True
        assert result["total_secrets"] == 3  # PASSWORD, API_KEY, SECRET_TOKEN

    @pytest.mark.security
    def test_secret_masking(self):
        """秘密情報マスキングのテスト."""

        # 秘密情報マスキング関数
        def mask_secrets(text):
            """テキスト内の秘密情報をマスク."""
            import re

            # マスキングパターン
            masking_patterns = [
                (r'(password\s*[=:]\s*["\'])([^"\']+)(["\'])', r"\1***MASKED***\3"),
                (r'(api[_-]?key\s*[=:]\s*["\'])([^"\']+)(["\'])', r"\1***MASKED***\3"),
                (r'(token\s*[=:]\s*["\'])([^"\']+)(["\'])', r"\1***MASKED***\3"),
                (r'(secret\s*[=:]\s*["\'])([^"\']+)(["\'])', r"\1***MASKED***\3"),
                (r"(://[^:]+:)([^@]+)(@)", r"\1***MASKED***\3"),  # URL内のパスワード
            ]

            masked_text = text
            for pattern, replacement in masking_patterns:
                masked_text = re.sub(pattern, replacement, masked_text, flags=re.IGNORECASE)

            return masked_text

        # マスキングテスト
        test_cases = [
            ("password = 'secret123'", "password = '***MASKED***'"),
            ("API_KEY = 'abcd1234'", "API_KEY = '***MASKED***'"),
            ("token = 'xyz789'", "token = '***MASKED***'"),
            ("database://user:password@host/db", "database://user:***MASKED***@host/db"),
            ("normal text without secrets", "normal text without secrets"),
        ]

        for original_text, expected_pattern in test_cases:
            masked_text = mask_secrets(original_text)
            if "***MASKED***" in expected_pattern:
                assert "***MASKED***" in masked_text
            else:
                assert masked_text == expected_pattern

    @pytest.mark.security
    def test_secure_secret_storage(self):
        """セキュアな秘密情報保存のテスト."""

        # セキュア保存関数
        def store_secret_securely(secret_name, secret_value, storage_path):
            """秘密情報をセキュアに保存."""
            import base64
            import hashlib
            import json

            # 簡単な暗号化（実際の実装ではより強力な暗号化を使用）
            def simple_encrypt(data, key):
                """簡単なXOR暗号化."""
                key_bytes = key.encode()
                data_bytes = data.encode()
                encrypted = bytes(
                    a ^ b
                    for a, b in zip(
                        data_bytes,
                        (key_bytes * (len(data_bytes) // len(key_bytes) + 1))[: len(data_bytes)],
                        strict=False,
                    )
                )
                return base64.b64encode(encrypted).decode()

            # 暗号化キーの生成（実際の実装では安全なキー管理を使用）
            encryption_key = hashlib.sha256(f"key_{secret_name}".encode()).hexdigest()[:16]

            # 秘密情報の暗号化
            encrypted_value = simple_encrypt(secret_value, encryption_key)

            # セキュアファイルに保存
            secret_data = {
                "name": secret_name,
                "encrypted_value": encrypted_value,
                "created_at": "2024-12-01T10:00:00Z",
            }

            storage_file = Path(storage_path)
            storage_file.write_text(json.dumps(secret_data, indent=2))

            # Unix系では権限を制限
            if platform.system() != "Windows":
                import os

                os.chmod(storage_file, 0o600)

            return True

        def retrieve_secret_securely(secret_name, storage_path):
            """セキュアに保存された秘密情報を取得."""
            import base64
            import hashlib
            import json

            def simple_decrypt(encrypted_data, key):
                """簡単なXOR復号化."""
                key_bytes = key.encode()
                encrypted_bytes = base64.b64decode(encrypted_data.encode())
                decrypted = bytes(
                    a ^ b
                    for a, b in zip(
                        encrypted_bytes,
                        (key_bytes * (len(encrypted_bytes) // len(key_bytes) + 1))[: len(encrypted_bytes)],
                        strict=False,
                    )
                )
                return decrypted.decode()

            storage_file = Path(storage_path)
            if not storage_file.exists():
                return None

            secret_data = json.loads(storage_file.read_text())

            # 復号化キーの生成
            encryption_key = hashlib.sha256(f"key_{secret_name}".encode()).hexdigest()[:16]

            # 秘密情報の復号化
            decrypted_value = simple_decrypt(secret_data["encrypted_value"], encryption_key)

            return decrypted_value

        # セキュア保存テスト
        secret_file = self.temp_dir / "secure_secrets.json"

        # 秘密情報の保存
        store_result = store_secret_securely("api_key", "super_secret_key_123", secret_file)
        assert store_result is True
        assert secret_file.exists()

        # 保存されたファイルに平文の秘密情報が含まれていないことを確認
        file_content = secret_file.read_text()
        assert "super_secret_key_123" not in file_content
        assert "encrypted_value" in file_content

        # 秘密情報の取得
        retrieved_secret = retrieve_secret_securely("api_key", secret_file)
        assert retrieved_secret == "super_secret_key_123"

    @pytest.mark.security
    def test_secret_in_memory_handling(self):
        """メモリ内秘密情報処理のテスト."""

        # セキュアメモリ処理クラス
        class SecureString:
            """セキュアな文字列処理クラス."""

            def __init__(self, value):
                self._value = value
                self._accessed = False

            def get_value(self):
                """値を取得（一度のみ）."""
                if self._accessed:
                    raise ValueError("Secret has already been accessed")
                self._accessed = True
                return self._value

            def clear(self):
                """メモリから値をクリア."""
                self._value = None

            def __del__(self):
                """デストラクタで自動クリア."""
                self.clear()

            def __str__(self):
                return "***SECURE_STRING***"

            def __repr__(self):
                return "SecureString(***MASKED***)"

        # セキュア文字列テスト
        secure_secret = SecureString("my_secret_password")

        # 文字列表現のテスト
        assert str(secure_secret) == "***SECURE_STRING***"
        assert "***MASKED***" in repr(secure_secret)

        # 値の取得テスト
        retrieved_value = secure_secret.get_value()
        assert retrieved_value == "my_secret_password"

        # 二重アクセスの防止テスト
        with pytest.raises(ValueError, match="Secret has already been accessed"):
            secure_secret.get_value()

    @pytest.mark.security
    def test_secret_logging_prevention(self):
        """秘密情報のログ出力防止テスト."""

        # セキュアログ関数
        def secure_log(message, secrets_to_mask=None):
            """秘密情報をマスクしてログ出力."""
            if secrets_to_mask is None:
                secrets_to_mask = []

            masked_message = message
            for secret in secrets_to_mask:
                if secret in masked_message:
                    masked_message = masked_message.replace(secret, "***MASKED***")

            return f"LOG: {masked_message}"

        # ログマスキングテスト
        secret_password = "secret123"
        secret_api_key = "abcd1234efgh5678"

        test_message = f"Connecting with password {secret_password} and API key {secret_api_key}"

        # マスクなしログ（危険）
        unsafe_log = secure_log(test_message)
        assert secret_password in unsafe_log
        assert secret_api_key in unsafe_log

        # マスクありログ（安全）
        safe_log = secure_log(test_message, [secret_password, secret_api_key])
        assert secret_password not in safe_log
        assert secret_api_key not in safe_log
        assert "***MASKED***" in safe_log

    @pytest.mark.security
    def test_configuration_secret_handling(self):
        """設定ファイル内秘密情報処理のテスト."""

        # 設定ファイル秘密情報処理関数
        def process_config_with_secrets(config_file_path):
            """設定ファイルの秘密情報を安全に処理."""
            import json

            if not Path(config_file_path).exists():
                return {"processed": False, "reason": "Config file not found"}

            config_content = Path(config_file_path).read_text()

            try:
                config_data = json.loads(config_content)
            except json.JSONDecodeError:
                return {"processed": False, "reason": "Invalid JSON format"}

            # 秘密情報フィールドの識別
            secret_fields = ["password", "secret", "key", "token", "credential"]

            processed_config = {}
            secrets_found = []

            for key, value in config_data.items():
                if any(secret_field in key.lower() for secret_field in secret_fields):
                    # 秘密情報フィールドは処理済みマークを付ける
                    processed_config[key] = "***PROCESSED_SECRET***"
                    secrets_found.append(key)
                else:
                    processed_config[key] = value

            return {
                "processed": True,
                "config": processed_config,
                "secrets_found": secrets_found,
                "total_secrets": len(secrets_found),
            }

        # 設定ファイルテスト
        config_data = {
            "app_name": "test_app",
            "debug": True,
            "database_password": "secret123",
            "api_key": "abcd1234",
            "timeout": 30,
            "secret_token": "xyz789",
        }

        config_file = self.temp_dir / "test_config.json"
        config_file.write_text(json.dumps(config_data, indent=2))

        result = process_config_with_secrets(config_file)

        assert result["processed"] is True
        assert result["total_secrets"] == 3  # password, api_key, secret_token
        assert result["config"]["app_name"] == "test_app"  # 非秘密情報は保持
        assert result["config"]["database_password"] == "***PROCESSED_SECRET***"

    @pytest.mark.security
    def test_secret_transmission_security(self):
        """秘密情報送信セキュリティのテスト."""

        # セキュア送信関数
        def prepare_secure_transmission(data, secrets_to_exclude=None):
            """送信前に秘密情報を除外."""
            if secrets_to_exclude is None:
                secrets_to_exclude = []

            # データのコピーを作成
            secure_data = data.copy() if isinstance(data, dict) else data

            # 秘密情報フィールドを除外
            if isinstance(secure_data, dict):
                for secret_field in secrets_to_exclude:
                    if secret_field in secure_data:
                        secure_data[secret_field] = "***EXCLUDED***"

            return {"data": secure_data, "excluded_fields": secrets_to_exclude, "safe_for_transmission": True}

        # 送信データテスト
        transmission_data = {
            "user_id": "12345",
            "username": "testuser",
            "password": "secret123",
            "api_key": "abcd1234",
            "email": "test@example.com",
            "session_token": "xyz789",
        }

        # セキュア送信準備
        secure_transmission = prepare_secure_transmission(
            transmission_data, secrets_to_exclude=["password", "api_key", "session_token"]
        )

        assert secure_transmission["safe_for_transmission"] is True
        assert secure_transmission["data"]["username"] == "testuser"  # 非秘密情報は保持
        assert secure_transmission["data"]["password"] == "***EXCLUDED***"
        assert secure_transmission["data"]["api_key"] == "***EXCLUDED***"
        assert len(secure_transmission["excluded_fields"]) == 3

    @pytest.mark.security
    def test_secret_cleanup_on_exit(self):
        """終了時の秘密情報クリーンアップテスト."""

        # クリーンアップ管理クラス
        class SecretManager:
            """秘密情報管理クラス."""

            def __init__(self):
                self.secrets = {}
                self.cleanup_registered = False

            def store_secret(self, name, value):
                """秘密情報を保存."""
                self.secrets[name] = value
                if not self.cleanup_registered:
                    # 実際の実装では atexit.register を使用
                    self.cleanup_registered = True

            def get_secret(self, name):
                """秘密情報を取得."""
                return self.secrets.get(name)

            def cleanup_all_secrets(self):
                """全ての秘密情報をクリーンアップ."""
                for name in list(self.secrets.keys()):
                    self.secrets[name] = None
                    del self.secrets[name]
                return True

            def __del__(self):
                """デストラクタでクリーンアップ."""
                self.cleanup_all_secrets()

        # 秘密情報管理テスト
        secret_manager = SecretManager()

        # 秘密情報の保存
        secret_manager.store_secret("api_key", "secret_api_key_123")
        secret_manager.store_secret("password", "secret_password_456")

        # 秘密情報の取得確認
        assert secret_manager.get_secret("api_key") == "secret_api_key_123"
        assert secret_manager.get_secret("password") == "secret_password_456"

        # クリーンアップ実行
        cleanup_result = secret_manager.cleanup_all_secrets()
        assert cleanup_result is True

        # クリーンアップ後の確認
        assert secret_manager.get_secret("api_key") is None
        assert secret_manager.get_secret("password") is None
        assert len(secret_manager.secrets) == 0
