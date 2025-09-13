"""
CLI機能のテスト

マルチプラットフォームテスト方針に準拠したCLI機能のテスト
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.cli import (
    CLI,
    parse_arguments,
    setup_command,
    sync_command,
    config_command,
    validate_command,
)
from tests.multiplatform.helpers import (
    verify_current_platform,
    get_platform_specific_config,
)


class TestCLI:
    """CLI機能のテスト"""

    def test_parse_arguments_setup(self):
        """setupコマンドの引数解析テスト"""
        platform_info = verify_current_platform()
        
        args = parse_arguments(["setup", "--config", "config.json"])
        assert args.command == "setup"
        assert args.config == "config.json"

    def test_parse_arguments_sync(self):
        """syncコマンドの引数解析テスト"""
        args = parse_arguments(["sync", "--dry-run", "--verbose"])
        assert args.command == "sync"
        assert args.dry_run is True
        assert args.verbose is True

    def test_parse_arguments_config(self):
        """configコマンドの引数解析テスト"""
        args = parse_arguments(["config", "--set", "github.token=test_token"])
        assert args.command == "config"
        assert args.set == "github.token=test_token"

    def test_parse_arguments_validate(self):
        """validateコマンドの引数解析テスト"""
        args = parse_arguments(["validate", "--check-all"])
        assert args.command == "validate"
        assert args.check_all is True

    def test_parse_arguments_help(self):
        """ヘルプオプションのテスト"""
        with pytest.raises(SystemExit):
            parse_arguments(["--help"])

    def test_parse_arguments_version(self):
        """バージョンオプションのテスト"""
        with pytest.raises(SystemExit):
            parse_arguments(["--version"])

    def test_parse_arguments_invalid_command(self):
        """無効なコマンドのテスト"""
        with pytest.raises(SystemExit):
            parse_arguments(["invalid_command"])

    def test_setup_command_success(self):
        """setupコマンド実行成功テスト"""
        platform_info = verify_current_platform()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            with patch("setup_repo.setup.Setup") as mock_setup:
                mock_instance = Mock()
                mock_instance.run.return_value = {"success": True}
                mock_setup.return_value = mock_instance
                
                result = setup_command(str(config_path))
                assert result["success"] is True

    def test_setup_command_config_not_found(self):
        """設定ファイルが見つからない場合のsetupコマンドテスト"""
        with pytest.raises(FileNotFoundError):
            setup_command("nonexistent_config.json")

    def test_sync_command_success(self):
        """syncコマンド実行成功テスト"""
        platform_info = verify_current_platform()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            with patch("setup_repo.sync.Sync") as mock_sync:
                mock_instance = Mock()
                mock_instance.run.return_value = {"success": True, "synced": 3}
                mock_sync.return_value = mock_instance
                
                result = sync_command(str(config_path), dry_run=False)
                assert result["success"] is True
                assert result["synced"] == 3

    def test_sync_command_dry_run(self):
        """syncコマンドのドライランテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            with patch("setup_repo.sync.Sync") as mock_sync:
                mock_instance = Mock()
                mock_instance.dry_run.return_value = {
                    "would_sync": 3,
                    "changes": ["repo1", "repo2", "repo3"]
                }
                mock_sync.return_value = mock_instance
                
                result = sync_command(str(config_path), dry_run=True)
                assert result["would_sync"] == 3
                assert len(result["changes"]) == 3

    def test_config_command_set(self):
        """config setコマンドのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            result = config_command(
                str(config_path),
                action="set",
                key_value="github.token=test_token"
            )
            
            assert result["success"] is True
            assert config_path.exists()

    def test_config_command_get(self):
        """config getコマンドのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            # 設定ファイルを作成
            config_data = {"github": {"token": "test_token"}}
            with open(config_path, "w") as f:
                import json
                json.dump(config_data, f)
            
            result = config_command(
                str(config_path),
                action="get",
                key="github.token"
            )
            
            assert result["value"] == "test_token"

    def test_config_command_list(self):
        """config listコマンドのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            # 設定ファイルを作成
            config_data = {
                "github": {"token": "test_token", "username": "testuser"},
                "repositories": ["repo1", "repo2"]
            }
            with open(config_path, "w") as f:
                import json
                json.dump(config_data, f)
            
            result = config_command(str(config_path), action="list")
            
            assert "github.token" in result["config"]
            assert "github.username" in result["config"]
            assert "repositories" in result["config"]

    def test_validate_command_success(self):
        """validateコマンド実行成功テスト"""
        platform_info = verify_current_platform()
        
        with patch("setup_repo.setup_validators.validate_git_config") as mock_git, \
             patch("setup_repo.setup_validators.validate_python_environment") as mock_python, \
             patch("setup_repo.setup_validators.validate_uv_installation") as mock_uv:
            
            mock_git.return_value = {"valid": True}
            mock_python.return_value = {"valid": True}
            mock_uv.return_value = {"valid": True}
            
            result = validate_command(check_all=True)
            
            assert result["git"]["valid"] is True
            assert result["python"]["valid"] is True
            assert result["uv"]["valid"] is True

    def test_validate_command_partial_failure(self):
        """validateコマンドの部分的失敗テスト"""
        with patch("setup_repo.setup_validators.validate_git_config") as mock_git, \
             patch("setup_repo.setup_validators.validate_python_environment") as mock_python:
            
            mock_git.return_value = {"valid": True}
            mock_python.side_effect = Exception("Python not found")
            
            result = validate_command(check_all=False)
            
            assert result["git"]["valid"] is True
            assert "error" in result["python"]

    def test_cli_class_init(self):
        """CLIクラスの初期化テスト"""
        platform_info = verify_current_platform()
        
        cli = CLI()
        assert cli.platform == platform_info.name

    def test_cli_class_run_setup(self):
        """CLIクラスのsetup実行テスト"""
        cli = CLI()
        
        with patch("setup_repo.cli.setup_command") as mock_setup:
            mock_setup.return_value = {"success": True}
            
            args = Mock()
            args.command = "setup"
            args.config = "config.json"
            
            result = cli.run(args)
            assert result["success"] is True

    def test_cli_class_run_sync(self):
        """CLIクラスのsync実行テスト"""
        cli = CLI()
        
        with patch("setup_repo.cli.sync_command") as mock_sync:
            mock_sync.return_value = {"success": True, "synced": 2}
            
            args = Mock()
            args.command = "sync"
            args.config = "config.json"
            args.dry_run = False
            args.verbose = False
            
            result = cli.run(args)
            assert result["success"] is True
            assert result["synced"] == 2

    def test_cli_class_run_config(self):
        """CLIクラスのconfig実行テスト"""
        cli = CLI()
        
        with patch("setup_repo.cli.config_command") as mock_config:
            mock_config.return_value = {"success": True}
            
            args = Mock()
            args.command = "config"
            args.config = "config.json"
            args.action = "set"
            args.set = "github.token=test"
            
            result = cli.run(args)
            assert result["success"] is True

    def test_cli_class_run_validate(self):
        """CLIクラスのvalidate実行テスト"""
        cli = CLI()
        
        with patch("setup_repo.cli.validate_command") as mock_validate:
            mock_validate.return_value = {"git": {"valid": True}}
            
            args = Mock()
            args.command = "validate"
            args.check_all = True
            
            result = cli.run(args)
            assert result["git"]["valid"] is True

    def test_cli_error_handling(self):
        """CLIエラーハンドリングのテスト"""
        cli = CLI()
        
        with patch("setup_repo.cli.setup_command") as mock_setup:
            mock_setup.side_effect = Exception("Setup failed")
            
            args = Mock()
            args.command = "setup"
            args.config = "config.json"
            
            with pytest.raises(Exception, match="Setup failed"):
                cli.run(args)

    @pytest.mark.integration
    def test_cli_full_workflow(self):
        """CLI完全ワークフローのテスト"""
        platform_info = verify_current_platform()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            cli = CLI()
            
            # 1. 設定の作成
            config_args = Mock()
            config_args.command = "config"
            config_args.config = str(config_path)
            config_args.action = "set"
            config_args.set = "github.token=test_token"
            
            with patch("setup_repo.cli.config_command") as mock_config:
                mock_config.return_value = {"success": True}
                config_result = cli.run(config_args)
            
            # 2. 検証の実行
            validate_args = Mock()
            validate_args.command = "validate"
            validate_args.check_all = True
            
            with patch("setup_repo.cli.validate_command") as mock_validate:
                mock_validate.return_value = {"git": {"valid": True}}
                validate_result = cli.run(validate_args)
            
            # 3. セットアップの実行
            setup_args = Mock()
            setup_args.command = "setup"
            setup_args.config = str(config_path)
            
            with patch("setup_repo.cli.setup_command") as mock_setup:
                mock_setup.return_value = {"success": True}
                setup_result = cli.run(setup_args)
            
            assert config_result["success"] is True
            assert validate_result["git"]["valid"] is True
            assert setup_result["success"] is True

    @pytest.mark.slow
    def test_cli_performance(self):
        """CLI操作のパフォーマンステスト"""
        import time
        
        platform_info = verify_current_platform()
        config = get_platform_specific_config()
        
        cli = CLI()
        
        start_time = time.time()
        
        # 複数のCLI操作を実行
        for _ in range(5):
            args = Mock()
            args.command = "validate"
            args.check_all = False
            
            with patch("setup_repo.cli.validate_command") as mock_validate:
                mock_validate.return_value = {"git": {"valid": True}}
                cli.run(args)
        
        elapsed = time.time() - start_time
        assert elapsed < 3.0, f"CLI操作が遅すぎます: {elapsed}秒"

    def test_cli_platform_specific_behavior(self):
        """プラットフォーム固有のCLI動作テスト"""
        platform_info = verify_current_platform()
        config = get_platform_specific_config()
        
        cli = CLI()
        
        # プラットフォーム固有の設定が適用されることを確認
        assert cli.platform == platform_info.name
        
        # プラットフォーム固有のコマンド実行
        if platform_info.name == "windows":
            # Windows固有のテスト
            assert config["shell"] == "powershell"
        else:
            # Unix系固有のテスト
            assert config["shell"] in ["bash", "zsh"]

    def test_cli_verbose_output(self):
        """CLI詳細出力のテスト"""
        cli = CLI()
        
        with patch("builtins.print") as mock_print:
            args = Mock()
            args.command = "sync"
            args.config = "config.json"
            args.dry_run = False
            args.verbose = True
            
            with patch("setup_repo.cli.sync_command") as mock_sync:
                mock_sync.return_value = {"success": True, "synced": 2}
                cli.run(args)
            
            # 詳細出力が行われたことを確認
            mock_print.assert_called()

    def test_cli_quiet_mode(self):
        """CLI静寂モードのテスト"""
        cli = CLI()
        
        with patch("builtins.print") as mock_print:
            args = Mock()
            args.command = "sync"
            args.config = "config.json"
            args.dry_run = False
            args.verbose = False
            args.quiet = True
            
            with patch("setup_repo.cli.sync_command") as mock_sync:
                mock_sync.return_value = {"success": True, "synced": 2}
                cli.run(args)
            
            # 出力が抑制されたことを確認
            mock_print.assert_not_called()