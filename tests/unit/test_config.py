"""
設定管理機能のテスト

マルチプラットフォームテスト方針に準拠した設定管理機能のテスト
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.config import (
    Config,
    ConfigError,
    load_config,
    save_config,
    merge_configs,
    validate_config,
)
from tests.multiplatform.helpers import (
    verify_current_platform,
    get_platform_specific_config,
)


class TestConfig:
    """設定管理機能のテスト"""

    def test_load_config_success(self):
        """設定ファイル読み込み成功テスト"""
        platform_info = verify_current_platform()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "github": {
                    "username": "testuser",
                    "token": "test_token"
                },
                "repositories": ["repo1", "repo2"]
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            config = load_config(config_path)
            assert config["github"]["username"] == "testuser"
            assert len(config["repositories"]) == 2
        finally:
            Path(config_path).unlink()

    def test_load_config_file_not_found(self):
        """設定ファイルが見つからない場合のテスト"""
        with pytest.raises(ConfigError, match="設定ファイルが見つかりません"):
            load_config("nonexistent_config.json")

    def test_load_config_invalid_json(self):
        """無効なJSON設定ファイルのテスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json}')
            config_path = f.name
        
        try:
            with pytest.raises(ConfigError, match="無効なJSON"):
                load_config(config_path)
        finally:
            Path(config_path).unlink()

    def test_save_config_success(self):
        """設定ファイル保存成功テスト"""
        platform_info = verify_current_platform()
        
        config_data = {
            "github": {
                "username": "testuser",
                "token": "test_token"
            },
            "platform": platform_info.name
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            result = save_config(config_path, config_data)
            assert result["success"] is True
            
            # 保存された設定を確認
            with open(config_path, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
            
            assert saved_config["github"]["username"] == "testuser"
            assert saved_config["platform"] == platform_info.name
        finally:
            Path(config_path).unlink()

    def test_save_config_permission_error(self):
        """設定ファイル保存権限エラーテスト"""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(ConfigError, match="権限エラー"):
                save_config("/root/config.json", {})

    def test_merge_configs_success(self):
        """設定マージ成功テスト"""
        base_config = {
            "github": {
                "username": "baseuser",
                "token": "base_token"
            },
            "repositories": ["repo1"]
        }
        
        override_config = {
            "github": {
                "token": "new_token"
            },
            "repositories": ["repo2", "repo3"],
            "new_setting": "value"
        }
        
        merged = merge_configs(base_config, override_config)
        
        assert merged["github"]["username"] == "baseuser"  # 保持
        assert merged["github"]["token"] == "new_token"    # 上書き
        assert merged["repositories"] == ["repo2", "repo3"]  # 上書き
        assert merged["new_setting"] == "value"            # 追加

    def test_merge_configs_deep_merge(self):
        """深いネスト構造の設定マージテスト"""
        base_config = {
            "settings": {
                "editor": {
                    "tabSize": 4,
                    "insertSpaces": True
                },
                "python": {
                    "interpreter": "python3"
                }
            }
        }
        
        override_config = {
            "settings": {
                "editor": {
                    "tabSize": 2
                },
                "linter": {
                    "enabled": True
                }
            }
        }
        
        merged = merge_configs(base_config, override_config)
        
        assert merged["settings"]["editor"]["tabSize"] == 2
        assert merged["settings"]["editor"]["insertSpaces"] is True
        assert merged["settings"]["python"]["interpreter"] == "python3"
        assert merged["settings"]["linter"]["enabled"] is True

    def test_validate_config_success(self):
        """設定検証成功テスト"""
        valid_config = {
            "github": {
                "username": "testuser",
                "token": "ghp_1234567890abcdef"
            },
            "repositories": ["repo1", "repo2"],
            "sync_settings": {
                "auto_sync": True,
                "interval": 3600
            }
        }
        
        result = validate_config(valid_config)
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_config_missing_required(self):
        """必須設定項目不足のテスト"""
        invalid_config = {
            "repositories": ["repo1"]
            # github設定が不足
        }
        
        result = validate_config(invalid_config)
        assert result["valid"] is False
        assert any("github" in error for error in result["errors"])

    def test_validate_config_invalid_token_format(self):
        """無効なトークン形式のテスト"""
        invalid_config = {
            "github": {
                "username": "testuser",
                "token": "invalid_token"  # 正しい形式ではない
            },
            "repositories": ["repo1"]
        }
        
        result = validate_config(invalid_config)
        assert result["valid"] is False
        assert any("token" in error for error in result["errors"])

    def test_config_class_init(self):
        """Configクラスの初期化テスト"""
        platform_info = verify_current_platform()
        
        config = Config()
        assert config.platform == platform_info.name
        assert isinstance(config.data, dict)

    def test_config_class_load_from_file(self):
        """Configクラスのファイル読み込みテスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "github": {
                    "username": "testuser",
                    "token": "test_token"
                }
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            config = Config()
            config.load_from_file(config_path)
            
            assert config.get("github.username") == "testuser"
            assert config.get("github.token") == "test_token"
        finally:
            Path(config_path).unlink()

    def test_config_class_get_nested_value(self):
        """Configクラスのネストした値取得テスト"""
        config = Config()
        config.data = {
            "level1": {
                "level2": {
                    "value": "test"
                }
            }
        }
        
        assert config.get("level1.level2.value") == "test"
        assert config.get("level1.level2.nonexistent") is None
        assert config.get("level1.level2.nonexistent", "default") == "default"

    def test_config_class_set_nested_value(self):
        """Configクラスのネストした値設定テスト"""
        config = Config()
        
        config.set("github.username", "testuser")
        config.set("github.token", "test_token")
        
        assert config.data["github"]["username"] == "testuser"
        assert config.data["github"]["token"] == "test_token"

    def test_config_class_platform_specific_defaults(self):
        """プラットフォーム固有のデフォルト設定テスト"""
        platform_info = verify_current_platform()
        platform_config = get_platform_specific_config()
        
        config = Config()
        config.apply_platform_defaults()
        
        assert config.get("platform.name") == platform_info.name
        assert config.get("platform.shell") == platform_config["shell"]

    @pytest.mark.integration
    def test_config_full_workflow(self):
        """設定管理の完全ワークフローテスト"""
        platform_info = verify_current_platform()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            
            # 1. 新しい設定を作成
            config = Config()
            config.set("github.username", "testuser")
            config.set("github.token", "test_token")
            config.apply_platform_defaults()
            
            # 2. ファイルに保存
            config.save_to_file(str(config_path))
            assert config_path.exists()
            
            # 3. 新しいインスタンスで読み込み
            new_config = Config()
            new_config.load_from_file(str(config_path))
            
            # 4. 設定が正しく保存・読み込みされたことを確認
            assert new_config.get("github.username") == "testuser"
            assert new_config.get("platform.name") == platform_info.name

    def test_config_environment_variable_override(self):
        """環境変数による設定上書きテスト"""
        with patch.dict("os.environ", {
            "GITHUB_TOKEN": "env_token",
            "GITHUB_USERNAME": "env_user"
        }):
            config = Config()
            config.load_from_environment()
            
            assert config.get("github.token") == "env_token"
            assert config.get("github.username") == "env_user"

    def test_config_backup_and_restore(self):
        """設定のバックアップと復元テスト"""
        config = Config()
        config.set("test.value", "original")
        
        # バックアップ作成
        backup = config.create_backup()
        
        # 設定を変更
        config.set("test.value", "modified")
        assert config.get("test.value") == "modified"
        
        # バックアップから復元
        config.restore_from_backup(backup)
        assert config.get("test.value") == "original"