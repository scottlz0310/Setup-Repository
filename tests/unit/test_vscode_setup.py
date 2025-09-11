"""VS Code設定のテスト"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.setup_repo.vscode_setup import apply_vscode_template


class TestApplyVscodeTemplate:
    """apply_vscode_template関数のテストクラス"""

    def test_dry_run_mode(self, capsys):
        """ドライランモードのテスト"""
        repo_path = Path("/test/repo")
        platform = "windows"

        # テンプレートパスが存在する場合をシミュレート
        def mock_exists(self):
            path_str = str(self)
            return bool("vscode-templates" in path_str and "windows" in path_str)

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform, dry_run=True)

        assert result is True
        captured = capsys.readouterr()
        assert "VS Code設定適用中..." in captured.out
        assert "VS Code設定適用予定" in captured.out

    def test_dry_run_mode_with_different_repo_names(self, capsys):
        """異なるリポジトリ名でのドライランテスト"""
        test_cases = [
            Path("/test/my-awesome-repo"),
            Path("/test/simple-repo"),
            Path("/test/repo_with_underscores"),
        ]

        # テンプレートパスが存在する場合をシミュレート
        def mock_exists(self):
            path_str = str(self)
            return bool("vscode-templates" in path_str and "linux" in path_str)

        with patch.object(Path, "exists", mock_exists):
            for repo_path in test_cases:
                result = apply_vscode_template(repo_path, "linux", dry_run=True)
                assert result is True
                captured = capsys.readouterr()
                assert repo_path.name in captured.out

    def test_no_template_exists(self):
        """テンプレートが存在しない場合のテスト"""
        repo_path = Path("/test/repo")
        platform = "nonexistent"

        with patch("pathlib.Path.exists", return_value=False):
            result = apply_vscode_template(repo_path, platform)

        assert result is True

    def test_fallback_to_linux_template(self):
        """存在しないプラットフォームでLinuxテンプレートにフォールバックするテスト"""
        repo_path = Path("/test/repo")
        platform = "unknown_platform"

        with patch("pathlib.Path.exists") as mock_exists:
            # 最初の呼び出し（unknown_platform）はFalse、2回目（linux）もFalse
            mock_exists.return_value = False
            result = apply_vscode_template(repo_path, platform)

        assert result is True
        # unknown_platform と linux の両方のパスがチェックされることを確認
        assert mock_exists.call_count >= 2

    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    def test_successful_template_application(self, mock_copytree, capsys):
        """VS Code設定適用成功のテスト"""
        repo_path = Path("/test/repo")
        platform = "linux"
        mock_copytree.return_value = None

        # テンプレートパスは存在、.vscodeディレクトリは存在しない
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "linux" in path_str:
                return True
            if path_str.endswith(".vscode"):
                return False
            return False

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform)

        assert result is True
        mock_copytree.assert_called_once()
        captured = capsys.readouterr()
        assert "VS Code設定適用完了" in captured.out

    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    def test_copytree_failure(self, mock_copytree, capsys):
        """copytree失敗のテスト"""
        repo_path = Path("/test/repo")
        platform = "linux"
        mock_copytree.side_effect = OSError("Permission denied")

        # テンプレートパスは存在、.vscodeディレクトリは存在しない
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "linux" in path_str:
                return True
            if path_str.endswith(".vscode"):
                return False
            return False

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform)

        assert result is False
        captured = capsys.readouterr()
        assert "VS Code設定適用失敗" in captured.out
        assert "Permission denied" in captured.out

    @patch("src.setup_repo.vscode_setup.shutil.move")
    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    @patch("src.setup_repo.vscode_setup.time.time")
    def test_existing_vscode_directory_backup(
        self, mock_time, mock_copytree, mock_move, capsys
    ):
        """既存の.vscodeディレクトリがある場合のバックアップテスト"""
        repo_path = Path("/test/repo")
        platform = "linux"
        mock_time.return_value = 1234567890
        mock_move.return_value = None
        mock_copytree.return_value = None

        # テンプレートパスと.vscodeディレクトリの両方が存在
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "linux" in path_str:
                return True
            return bool(path_str.endswith(".vscode"))

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform)

        assert result is True
        expected_backup_path = str(repo_path / ".vscode.bak.1234567890")
        mock_move.assert_called_once_with(
            str(repo_path / ".vscode"), expected_backup_path
        )
        mock_copytree.assert_called_once()
        captured = capsys.readouterr()
        assert "既存設定をバックアップ" in captured.out
        assert ".vscode.bak.1234567890" in captured.out

    @patch("src.setup_repo.vscode_setup.shutil.move")
    def test_backup_move_failure(self, mock_move, capsys):
        """既存ディレクトリのmove失敗のテスト"""
        repo_path = Path("/test/repo")
        platform = "linux"
        mock_move.side_effect = OSError("Cannot move directory")

        # テンプレートパスと.vscodeディレクトリの両方が存在
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "linux" in path_str:
                return True
            return bool(path_str.endswith(".vscode"))

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform)

        assert result is False
        captured = capsys.readouterr()
        assert "VS Code設定適用失敗" in captured.out
        assert "Cannot move directory" in captured.out

    @pytest.mark.parametrize("platform", ["windows", "linux", "wsl"])
    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    def test_different_platforms(self, mock_copytree, platform):
        """異なるプラットフォームでのテスト"""
        repo_path = Path("/test/repo")
        mock_copytree.return_value = None

        # テンプレートパスは存在、.vscodeディレクトリは存在しない
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and platform in path_str:
                return True
            if path_str.endswith(".vscode"):
                return False
            return False

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform)

        assert result is True
        mock_copytree.assert_called()

    @pytest.mark.parametrize(
        "exception",
        [
            OSError("OS error"),
            OSError("IO error"),
            PermissionError("Permission denied"),
            FileNotFoundError("File not found"),
            Exception("Generic exception"),
        ],
    )
    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    def test_various_exception_types(self, mock_copytree, exception, capsys):
        """異なる例外タイプのテスト"""
        repo_path = Path("/test/repo")
        platform = "linux"
        mock_copytree.side_effect = exception

        # テンプレートパスは存在、.vscodeディレクトリは存在しない
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "linux" in path_str:
                return True
            if path_str.endswith(".vscode"):
                return False
            return False

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform)

        assert result is False
        captured = capsys.readouterr()
        assert "VS Code設定適用失敗" in captured.out

    def test_path_construction_and_repo_name_extraction(self):
        """パス構築とリポジトリ名抽出のテスト"""
        test_cases = [
            Path("/test/my-awesome-repo"),
            Path("/home/user/projects/simple-repo"),
            Path("C:\\Users\\user\\repos\\windows-repo"),
            Path("/tmp/repo_with_underscores"),
        ]

        for repo_path in test_cases:
            with patch("pathlib.Path.exists", return_value=False):
                result = apply_vscode_template(repo_path, "linux")
            assert result is True

    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    def test_template_path_resolution(self, mock_copytree):
        """テンプレートパス解決のテスト"""
        repo_path = Path("/test/repo")
        platform = "windows"
        mock_copytree.return_value = None

        # テンプレートパスは存在、.vscodeディレクトリは存在しない
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "windows" in path_str:
                return True
            if path_str.endswith(".vscode"):
                return False
            return False

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform)

        assert result is True
        # copytreeが正しいパスで呼び出されることを確認
        args, kwargs = mock_copytree.call_args
        template_path, vscode_path = args
        assert "windows" in str(template_path)
        assert ".vscode" in str(vscode_path)

    @patch("src.setup_repo.vscode_setup.shutil.move")
    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    @patch("src.setup_repo.vscode_setup.time.time")
    def test_multiple_backup_scenarios(
        self, mock_time, mock_copytree, mock_move, capsys
    ):
        """複数のバックアップシナリオのテスト"""
        repo_path = Path("/test/repo")
        platform = "linux"
        mock_copytree.return_value = None
        mock_move.return_value = None

        # テンプレートパスと.vscodeディレクトリの両方が存在
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "linux" in path_str:
                return True
            return bool(path_str.endswith(".vscode"))

        # 異なるタイムスタンプでテスト
        timestamps = [1234567890, 1234567891, 1234567892]

        with patch.object(Path, "exists", mock_exists):
            for timestamp in timestamps:
                mock_time.return_value = timestamp
                result = apply_vscode_template(repo_path, platform)
                assert result is True

                expected_backup_path = str(repo_path / f".vscode.bak.{timestamp}")
                mock_move.assert_called_with(
                    str(repo_path / ".vscode"), expected_backup_path
                )

    def test_edge_case_empty_repo_name(self):
        """エッジケース: 空のリポジトリ名"""
        repo_path = Path("/")
        platform = "linux"

        with patch("pathlib.Path.exists", return_value=False):
            result = apply_vscode_template(repo_path, platform)

        assert result is True

    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    def test_script_directory_resolution(self, mock_copytree):
        """スクリプトディレクトリ解決のテスト"""
        repo_path = Path("/test/repo")
        platform = "linux"
        mock_copytree.return_value = None

        # テンプレートパスは存在、.vscodeディレクトリは存在しない
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "linux" in path_str:
                return True
            if path_str.endswith(".vscode"):
                return False
            return False

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform)

        assert result is True
        mock_copytree.assert_called_once()

    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    def test_console_output_formatting(self, mock_copytree, capsys):
        """コンソール出力フォーマットのテスト"""
        repo_path = Path("/test/my-test-repo")
        platform = "linux"
        mock_copytree.return_value = None

        # テンプレートパスは存在、.vscodeディレクトリは存在しない
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "linux" in path_str:
                return True
            if path_str.endswith(".vscode"):
                return False
            return False

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform)

        assert result is True
        captured = capsys.readouterr()

        # 出力に適切な絵文字とフォーマットが含まれることを確認
        assert "📁" in captured.out
        assert "✅" in captured.out
        assert "my-test-repo" in captured.out
        assert "VS Code設定適用中..." in captured.out
        assert "VS Code設定適用完了" in captured.out

    @patch("src.setup_repo.vscode_setup.shutil.move")
    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    def test_backup_console_output(self, mock_copytree, mock_move, capsys):
        """バックアップ時のコンソール出力テスト"""
        repo_path = Path("/test/repo")
        platform = "linux"
        mock_move.return_value = None
        mock_copytree.return_value = None

        # テンプレートパスと.vscodeディレクトリの両方が存在
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "linux" in path_str:
                return True
            return bool(path_str.endswith(".vscode"))

        with (
            patch("src.setup_repo.vscode_setup.time.time", return_value=1234567890),
            patch.object(Path, "exists", mock_exists),
        ):
            result = apply_vscode_template(repo_path, platform)

        assert result is True
        captured = capsys.readouterr()
        assert "📦" in captured.out
        assert "既存設定をバックアップ" in captured.out

    def test_template_fallback_logic(self):
        """テンプレートフォールバックロジックのテスト"""
        repo_path = Path("/test/repo")
        platform = "unknown_platform"

        call_count = 0

        def mock_exists(self):
            nonlocal call_count
            call_count += 1
            path_str = str(self)

            # 最初の呼び出し（unknown_platform）はFalse
            if (
                call_count == 1
                and "unknown_platform" in path_str
                or call_count == 2
                and "linux" in path_str
            ):
                return False
            return False

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform)

        assert result is True
        assert call_count >= 2

    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    def test_real_world_scenario_success(self, mock_copytree, capsys):
        """実際のシナリオに近い成功テスト"""
        repo_path = Path("/home/user/projects/my-project")
        platform = "linux"
        mock_copytree.return_value = None

        # テンプレートパスは存在、.vscodeディレクトリは存在しない
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "linux" in path_str:
                return True
            if path_str.endswith(".vscode"):
                return False
            return False

        with patch.object(Path, "exists", mock_exists):
            result = apply_vscode_template(repo_path, platform)

        assert result is True
        captured = capsys.readouterr()
        assert "my-project" in captured.out
        assert "VS Code設定適用完了" in captured.out

    @patch("src.setup_repo.vscode_setup.shutil.move")
    @patch("src.setup_repo.vscode_setup.shutil.copytree")
    def test_real_world_scenario_with_backup(self, mock_copytree, mock_move, capsys):
        """実際のシナリオに近いバックアップありテスト"""
        repo_path = Path("/home/user/projects/existing-project")
        platform = "windows"
        mock_copytree.return_value = None
        mock_move.return_value = None

        # テンプレートパスと.vscodeディレクトリの両方が存在
        def mock_exists(self):
            path_str = str(self)
            if "vscode-templates" in path_str and "windows" in path_str:
                return True
            return bool(path_str.endswith(".vscode"))

        with (
            patch("src.setup_repo.vscode_setup.time.time", return_value=1640995200),
            patch.object(Path, "exists", mock_exists),
        ):
            result = apply_vscode_template(repo_path, platform)

        assert result is True
        captured = capsys.readouterr()
        assert "existing-project" in captured.out
        assert "既存設定をバックアップ" in captured.out
        assert ".vscode.bak.1640995200" in captured.out
