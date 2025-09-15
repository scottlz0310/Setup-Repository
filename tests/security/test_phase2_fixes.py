"""
Phase 2セキュリティ修正のテスト

認証強化とエラーハンドリング改善のテストを実行します。
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.setup_repo.security_helpers import (
    check_admin_role,
    sanitize_user_input,
    validate_session_data,
)
from src.setup_repo.logging_config import check_logging_permissions
from src.setup_repo.quality_errors import ErrorReporter
from src.setup_repo.ci_error_handler import CIErrorHandler


class TestAuthenticationSecurity:
    """認証セキュリティのテスト"""

    def test_validate_session_data_valid(self):
        """有効なセッションデータの検証"""
        valid_session = {
            'user_id': 'user123',
            'session_id': 'session456',
            'created_at': '2024-01-01T00:00:00Z'
        }
        assert validate_session_data(valid_session) is True

    def test_validate_session_data_invalid(self):
        """無効なセッションデータの検証"""
        # 必須フィールドが不足
        invalid_session = {
            'user_id': 'user123',
            'session_id': 'session456'
            # created_at が不足
        }
        assert validate_session_data(invalid_session) is False

        # 辞書でない場合
        assert validate_session_data("invalid") is False
        assert validate_session_data(None) is False

    def test_check_admin_role_valid_admin(self):
        """有効な管理者セッションのテスト"""
        admin_session = {
            'user_id': 'admin123',
            'session_id': 'session456',
            'created_at': '2024-01-01T00:00:00Z',
            'authenticated_role': 'admin'
        }
        assert check_admin_role(admin_session) is True

    def test_check_admin_role_non_admin(self):
        """非管理者セッションのテスト"""
        user_session = {
            'user_id': 'user123',
            'session_id': 'session456',
            'created_at': '2024-01-01T00:00:00Z',
            'authenticated_role': 'user'
        }
        assert check_admin_role(user_session) is False

    def test_check_admin_role_invalid_session(self):
        """無効なセッションでの管理者チェック"""
        invalid_session = {'invalid': 'data'}
        assert check_admin_role(invalid_session) is False

    def test_sanitize_user_input(self):
        """ユーザー入力の無害化テスト"""
        # 危険な文字の除去
        dangerous_input = "<script>alert('xss')</script>"
        sanitized = sanitize_user_input(dangerous_input)
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert "script" in sanitized  # 文字自体は残る

        # 長さ制限
        long_input = "a" * 2000
        sanitized = sanitize_user_input(long_input, max_length=100)
        assert len(sanitized) == 100

        # 非文字列入力
        assert sanitize_user_input(123) == ""
        assert sanitize_user_input(None) == ""


class TestLoggingPermissions:
    """ログ権限チェックのテスト"""

    @patch('src.setup_repo.logging_config.LoggingConfig.is_ci_environment')
    def test_check_logging_permissions_ci(self, mock_is_ci):
        """CI環境での権限チェック"""
        mock_is_ci.return_value = True
        assert check_logging_permissions() is True

    @patch('src.setup_repo.logging_config.LoggingConfig.is_ci_environment')
    def test_check_logging_permissions_local(self, mock_is_ci):
        """ローカル環境での権限チェック"""
        mock_is_ci.return_value = False
        # セッションデータなしの場合は許可
        assert check_logging_permissions() is True

    @patch('src.setup_repo.logging_config.LoggingConfig.is_ci_environment')
    def test_check_logging_permissions_with_admin_session(self, mock_is_ci):
        """管理者セッションでの権限チェック"""
        mock_is_ci.return_value = False
        admin_session = {
            'user_id': 'admin123',
            'session_id': 'session456',
            'created_at': '2024-01-01T00:00:00Z',
            'authenticated_role': 'admin'
        }
        assert check_logging_permissions(admin_session) is True


class TestErrorHandlingImprovements:
    """エラーハンドリング改善のテスト"""

    def test_error_reporter_save_report_success(self):
        """エラーレポート保存の成功ケース"""
        with tempfile.TemporaryDirectory() as temp_dir:
            reporter = ErrorReporter(Path(temp_dir))
            error_data = {
                'timestamp': '2024-01-01T00:00:00Z',
                'errors': [{'type': 'TestError', 'message': 'Test error'}]
            }
            
            result_path = reporter.save_report(error_data, 'test')
            assert result_path.exists()
            
            # ファイル内容の確認
            with open(result_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            assert saved_data == error_data

    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_error_reporter_save_report_permission_error(self, mock_open):
        """権限エラー時のフォールバック"""
        reporter = ErrorReporter()
        error_data = {'test': 'data'}
        
        # 権限エラーが発生してもフォールバック先に保存される
        result_path = reporter.save_report(error_data, 'test')
        assert result_path is not None

    def test_ci_error_handler_stage_error(self):
        """CI エラーハンドラーのステージエラー処理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = CIErrorHandler(
                enable_github_annotations=False,
                error_report_dir=Path(temp_dir)
            )
            
            test_error = ValueError("Test stage error")
            handler.handle_stage_error("test_stage", test_error, duration=1.5)
            
            assert len(handler.errors) == 1
            assert handler.errors[0] == test_error

    def test_ci_error_handler_quality_check_error(self):
        """品質チェックエラーの処理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = CIErrorHandler(
                enable_github_annotations=False,
                error_report_dir=Path(temp_dir)
            )
            
            test_error = RuntimeError("Quality check failed")
            metrics = {'coverage': 75.0, 'issues': 5}
            
            handler.handle_quality_check_error("ruff", test_error, metrics)
            
            assert len(handler.errors) == 1
            assert handler.errors[0] == test_error

    def test_ci_error_handler_comprehensive_report(self):
        """包括的エラーレポートの作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = CIErrorHandler(
                enable_github_annotations=False,
                error_report_dir=Path(temp_dir)
            )
            
            # エラーを追加
            handler.handle_stage_error("test", ValueError("Test error"))
            
            # レポート作成
            report = handler.create_comprehensive_error_report()
            
            assert 'timestamp' in report
            assert 'total_errors' in report
            assert report['total_errors'] == 1
            assert len(report['errors']) == 1
            assert report['errors'][0]['type'] == 'ValueError'


class TestSecurityIntegration:
    """セキュリティ統合テスト"""

    def test_authentication_flow(self):
        """認証フローの統合テスト"""
        # 1. セッション作成
        session_data = {
            'user_id': 'test_user',
            'session_id': 'test_session',
            'created_at': '2024-01-01T00:00:00Z',
            'authenticated_role': 'admin'
        }
        
        # 2. セッション検証
        assert validate_session_data(session_data) is True
        
        # 3. 管理者権限チェック
        assert check_admin_role(session_data) is True
        
        # 4. ログ権限チェック
        with patch('src.setup_repo.logging_config.LoggingConfig.is_ci_environment', return_value=False):
            assert check_logging_permissions(session_data) is True

    def test_error_handling_with_security(self):
        """セキュリティを考慮したエラーハンドリング"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # セキュリティエラーレポーター
            reporter = ErrorReporter(Path(temp_dir))
            
            # 危険な入力を含むエラーデータ
            dangerous_error_data = {
                'user_input': '<script>alert("xss")</script>',
                'file_path': '../../../etc/passwd',
                'command': 'rm -rf /'
            }
            
            # 安全な処理
            sanitized_data = {
                'user_input': sanitize_user_input(dangerous_error_data['user_input']),
                'timestamp': '2024-01-01T00:00:00Z'
            }
            
            # レポート保存
            result_path = reporter.save_report(sanitized_data, 'security_test')
            assert result_path.exists()
            
            # 危険な文字が除去されていることを確認
            with open(result_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            assert '<' not in saved_data['user_input']
            assert '>' not in saved_data['user_input']