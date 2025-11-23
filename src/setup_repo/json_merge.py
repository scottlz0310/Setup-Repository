#!/usr/bin/env python3
"""JSON設定マージユーティリティ"""

from typing import Any


def merge_json_settings(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """
    2つのJSON設定を再帰的にマージする

    マージルール：
    - プリミティブ値: overlayの値で上書き
    - リスト: 重複を除いて結合
    - オブジェクト: 再帰的にマージ

    Args:
        base: ベースとなる設定
        overlay: 上書きする設定

    Returns:
        マージ後の設定
    """
    result = base.copy()

    for key, value in overlay.items():
        if key not in result:
            # 新しいキーはそのまま追加
            result[key] = value
        elif isinstance(value, dict) and isinstance(result[key], dict):
            # 両方がオブジェクトの場合は再帰的にマージ
            result[key] = merge_json_settings(result[key], value)
        elif isinstance(value, list) and isinstance(result[key], list):
            # 両方がリストの場合は重複を除いて結合
            result[key] = _merge_lists(result[key], value)
        else:
            # プリミティブ値は上書き
            result[key] = value

    return result


def _merge_lists(base_list: list[Any], overlay_list: list[Any]) -> list[Any]:
    """
    リストをマージ（重複除去）

    Args:
        base_list: ベースリスト
        overlay_list: 追加するリスト

    Returns:
        マージ後のリスト
    """
    # 順序を保持しつつ重複を除去
    seen = set()
    result = []

    for item in base_list + overlay_list:
        # プリミティブ値とdictのみサポート
        if isinstance(item, dict):
            # dictは文字列化して比較（完全一致のみ重複扱い）
            item_str = str(sorted(item.items()))
            if item_str not in seen:
                seen.add(item_str)
                result.append(item)
        else:
            # プリミティブ値
            if item not in seen:
                seen.add(item)
                result.append(item)

    return result


def merge_multiple_settings(*settings_list: dict[str, Any]) -> dict[str, Any]:
    """
    複数のJSON設定を順番にマージ

    Args:
        *settings_list: マージする設定のリスト（左から順に適用）

    Returns:
        マージ後の設定
    """
    if not settings_list:
        return {}

    result = settings_list[0].copy()
    for settings in settings_list[1:]:
        result = merge_json_settings(result, settings)

    return result
