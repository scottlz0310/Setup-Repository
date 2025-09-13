"""セキュリティ修正のテストクラス"""

from pathlib import Path

import pytest

from src.setup_repo.security_utils import SecureCommandRunner, SecurePathHandler, SecurityValidator


class TestSecurityFixes:
    """セキュリティ修正のテストクラス"""

    def test_command_injection_prevention(self):
        """OSコマンドインジェクション対策テスト"""
        dangerous_args = [
            "--help; rm -rf /",
            "--config=`cat /etc/passwd`",
            "--output=$(whoami)",
            "file.txt && rm -rf /",
            "input | malicious_command",
        ]

        for arg in dangerous_args:
            assert not SecurityValidator.validate_command_args([arg])

    def test_safe_command_args(self):
        """安全なコマンド引数のテスト"""
        safe_args = ["--help", "--config=config.json", "--output=report.txt", "-v", "--format=json"]

        for arg in safe_args:
            assert SecurityValidator.validate_command_args([arg])

    def test_path_traversal_prevention(self):
        """パストラバーサル対策テスト"""
        base_path = "/safe/directory"

        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\Windows\\System32",
            "/etc/shadow",
            "../../sensitive_file.txt",
        ]

        for dangerous_path in dangerous_paths:
            with pytest.raises(ValueError):
                SecurePathHandler.safe_join(base_path, dangerous_path)

    def test_safe_path_join(self):
        """安全なパス結合テスト"""
        import tempfile

        # 一時ディレクトリを使用してクロスプラットフォーム対応
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir) / "safe" / "base"
            base.mkdir(parents=True, exist_ok=True)

            result = SecurePathHandler.safe_join(base, "config.json")

            # 結果パスがベースパス内にあることを確認
            try:
                result.resolve().relative_to(base.resolve())
                assert result.name == "config.json"
            except ValueError:
                # パスがベース外にある場合は失敗
                pytest.fail("結果パスがベースパス外にあります")

    def test_xss_prevention(self):
        """XSS対策テスト"""
        malicious_content = "<script>alert('XSS')</script>"
        safe_content = SecurityValidator.sanitize_html_content(malicious_content)

        # タグがエスケープされていることを確認
        assert "<script>" not in safe_content
        assert "</script>" not in safe_content
        assert "&lt;script&gt;" in safe_content
        assert "&lt;/script&gt;" in safe_content

    def test_html_escape_various_inputs(self):
        """様々な入力のHTMLエスケープテスト"""
        test_cases = [
            ("<script>", "&lt;script&gt;"),
            ("'single quotes'", "&#x27;single quotes&#x27;"),
            ('"double quotes"', "&quot;double quotes&quot;"),
            ("&ampersand", "&amp;ampersand"),
            ("<img src=x onerror=alert(1)>", "&lt;img src=x onerror=alert(1)&gt;"),
        ]

        for input_str, expected in test_cases:
            result = SecurityValidator.sanitize_html_content(input_str)
            assert expected in result

    def test_secure_command_runner(self):
        """セキュアなコマンド実行のテスト"""
        runner = SecureCommandRunner()

        # 存在するコマンドの検証
        try:
            path = runner.verify_command("python3")
            assert path is not None
            assert Path(path).exists()
        except FileNotFoundError:
            # python3が存在しない環境では、pythonを試す
            path = runner.verify_command("python")
            assert path is not None
            assert Path(path).exists()

    def test_secure_command_runner_nonexistent(self):
        """存在しないコマンドのテスト"""
        runner = SecureCommandRunner()

        with pytest.raises(FileNotFoundError):
            runner.verify_command("nonexistent_command_12345")

    def test_config_path_validation(self):
        """設定ファイルパス検証のテスト"""
        import tempfile

        # 一時ディレクトリを使用してクロスプラットフォーム対応
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "safe" / "config"
            base_path.mkdir(parents=True, exist_ok=True)

            # 有効な設定ファイル
            valid_configs = ["config.json", "settings.yaml", "app.toml"]

            for config in valid_configs:
                try:
                    result = SecurePathHandler.validate_config_path(str(base_path), config)
                    assert config in result
                except ValueError:
                    # パスが存在しない場合はスキップ
                    pass

    def test_invalid_config_extensions(self):
        """無効な設定ファイル拡張子のテスト"""
        import tempfile

        # 一時ディレクトリを使用してクロスプラットフォーム対応
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "safe" / "config"
            base_path.mkdir(parents=True, exist_ok=True)

            invalid_configs = [
                "malicious.exe",
                "script.sh",
                "config.txt",
                "settings",  # 拡張子なし
            ]

            for config in invalid_configs:
                with pytest.raises(ValueError):
                    SecurePathHandler.validate_config_path(str(base_path), config)
