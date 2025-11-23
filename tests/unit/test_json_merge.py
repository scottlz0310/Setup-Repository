"""
JSON設定マージユーティリティのテスト
"""

from setup_repo.json_merge import merge_json_settings, merge_multiple_settings


class TestJsonMerge:
    """JSON設定マージのテスト"""

    def test_merge_primitives(self):
        """プリミティブ値のマージテスト"""
        base = {"key1": "value1", "key2": 2}
        overlay = {"key2": 3, "key3": "value3"}

        result = merge_json_settings(base, overlay)

        assert result["key1"] == "value1"  # baseの値を保持
        assert result["key2"] == 3  # overlayで上書き
        assert result["key3"] == "value3"  # overlayから追加

    def test_merge_nested_objects(self):
        """ネストされたオブジェクトのマージテスト"""
        base = {"editor": {"fontSize": 12, "tabSize": 4}}
        overlay = {"editor": {"fontSize": 14, "lineHeight": 20}}

        result = merge_json_settings(base, overlay)

        assert result["editor"]["fontSize"] == 14  # overlayで上書き
        assert result["editor"]["tabSize"] == 4  # baseを保持
        assert result["editor"]["lineHeight"] == 20  # overlayから追加

    def test_merge_lists(self):
        """リストのマージテスト（重複除去）"""
        base = {"extensions": ["ext1", "ext2"]}
        overlay = {"extensions": ["ext2", "ext3"]}

        result = merge_json_settings(base, overlay)

        # 重複を除いて結合
        assert result["extensions"] == ["ext1", "ext2", "ext3"]

    def test_merge_lists_with_dicts(self):
        """辞書を含むリストのマージテスト"""
        base = {"items": [{"name": "item1"}, {"name": "item2"}]}
        overlay = {"items": [{"name": "item2"}, {"name": "item3"}]}

        result = merge_json_settings(base, overlay)

        # 辞書の重複も除去される
        assert len(result["items"]) == 3
        assert {"name": "item1"} in result["items"]
        assert {"name": "item2"} in result["items"]
        assert {"name": "item3"} in result["items"]

    def test_merge_empty_base(self):
        """空のベースとのマージテスト"""
        base = {}
        overlay = {"key": "value"}

        result = merge_json_settings(base, overlay)

        assert result == {"key": "value"}

    def test_merge_empty_overlay(self):
        """空のオーバーレイとのマージテスト"""
        base = {"key": "value"}
        overlay = {}

        result = merge_json_settings(base, overlay)

        assert result == {"key": "value"}

    def test_merge_type_change(self):
        """型が変わる場合のマージテスト"""
        base = {"key": "string"}
        overlay = {"key": 123}

        result = merge_json_settings(base, overlay)

        # overlayの型で上書き
        assert result["key"] == 123

        # リストからオブジェクトへ
        base2 = {"key": ["item1", "item2"]}
        overlay2 = {"key": {"nested": "value"}}

        result2 = merge_json_settings(base2, overlay2)
        assert result2["key"] == {"nested": "value"}

    def test_merge_multiple_settings(self):
        """複数設定のマージテスト"""
        settings1 = {"a": 1, "b": 2}
        settings2 = {"b": 3, "c": 4}
        settings3 = {"c": 5, "d": 6}

        result = merge_multiple_settings(settings1, settings2, settings3)

        assert result["a"] == 1
        assert result["b"] == 3  # settings2で上書き
        assert result["c"] == 5  # settings3で上書き
        assert result["d"] == 6

    def test_merge_multiple_empty(self):
        """空のリストでのマージテスト"""
        result = merge_multiple_settings()

        assert result == {}

    def test_merge_multiple_single(self):
        """単一設定のマージテスト"""
        settings = {"key": "value"}

        result = merge_multiple_settings(settings)

        assert result == {"key": "value"}

    def test_deep_nested_merge(self):
        """深くネストされたマージテスト"""
        base = {"level1": {"level2": {"level3": {"value": 1}}}}
        overlay = {"level1": {"level2": {"level3": {"value": 2, "extra": 3}}}}

        result = merge_json_settings(base, overlay)

        assert result["level1"]["level2"]["level3"]["value"] == 2
        assert result["level1"]["level2"]["level3"]["extra"] == 3

    def test_vscode_settings_realistic_merge(self):
        """実際のVS Code設定に近いマージテスト"""
        common = {
            "editor.formatOnSave": True,
            "editor.tabSize": 4,
            "files.watcherExclude": {
                "**/.git/objects/**": True,
                "**/node_modules/**": True,
            },
        }

        python_settings = {
            "python.linting.enabled": True,
            "[python]": {
                "editor.formatOnSave": True,
                "editor.defaultFormatter": "charliermarsh.ruff",
            },
            "files.watcherExclude": {
                "**/__pycache__/**": True,
                "**/.venv/**": True,
            },
        }

        platform_settings = {
            "files.eol": "\n",
            "python.defaultInterpreterPath": "./.venv/bin/python",
        }

        existing_settings = {
            "editor.fontSize": 14,
            "workbench.colorTheme": "Dark+",
        }

        result = merge_multiple_settings(common, python_settings, platform_settings, existing_settings)

        # 共通設定
        assert result["editor.formatOnSave"] is True
        assert result["editor.tabSize"] == 4

        # Python設定
        assert result["python.linting.enabled"] is True
        assert result["[python]"]["editor.defaultFormatter"] == "charliermarsh.ruff"

        # プラットフォーム設定
        assert result["files.eol"] == "\n"
        assert result["python.defaultInterpreterPath"] == "./.venv/bin/python"

        # 既存設定（保持される）
        assert result["editor.fontSize"] == 14
        assert result["workbench.colorTheme"] == "Dark+"

        # files.watcherExcludeはマージされる
        assert result["files.watcherExclude"]["**/.git/objects/**"] is True
        assert result["files.watcherExclude"]["**/node_modules/**"] is True
        assert result["files.watcherExclude"]["**/__pycache__/**"] is True
        assert result["files.watcherExclude"]["**/.venv/**"] is True
