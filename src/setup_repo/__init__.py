"""セットアップリポジトリパッケージ"""

__version__ = "1.4.7"

# 後方互換性のためのエイリアス設定
try:
    from .compatibility import create_compatibility_aliases

    create_compatibility_aliases()
except ImportError:
    # 互換性モジュールが利用できない場合は警告を出力
    import warnings

    warnings.warn(
        "後方互換性モジュールが利用できません。一部の古いインポートが動作しない可能性があります。",
        ImportWarning,
        stacklevel=2,
    )
