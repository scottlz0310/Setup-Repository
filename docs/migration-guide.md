# Setup Repository リファクタリング移行ガイド

## 概要

Setup-Repositoryプロジェクトは、責任分離の徹底とテストカバレッジ向上を目的として大規模なリファクタリングを実施しました。このガイドでは、新しいモジュール構造への移行方法と、後方互換性の維持について説明します。

## 主要な変更点

### 1. モジュール分割

以下の大きなモジュールが責任に基づいて分割されました：

#### Quality Logger分割 (19関数 → 3モジュール)

**変更前:**

```python
from setup_repo.quality_logger import QualityError, ColoredFormatter, setup_quality_logging
```

**変更後:**

```python
# エラー処理関連
from setup_repo.quality_errors import QualityError, QualityWarning, handle_quality_error

# フォーマッター関連  
from setup_repo.quality_formatters import ColoredFormatter, JSONFormatter, format_log_message

# 基本ログ機能
from setup_repo.quality_logger import setup_quality_logging, get_quality_logger
```

#### CI Error Handler分割 (11関数 → 2モジュール)

**変更前:**

```python
from setup_repo.ci_error_handler import detect_ci_environment, handle_ci_error
```

**変更後:**

```python
# CI環境検出
from setup_repo.ci_environment import detect_ci_environment, get_system_info

# エラーハンドリング
from setup_repo.ci_error_handler import handle_ci_error, generate_error_report
```

#### Logging Config分割 (11関数 → 2モジュール)

**変更前:**

```python
from setup_repo.logging_config import setup_logging, TeeHandler
```

**変更後:**

```python
# 基本設定
from setup_repo.logging_config import setup_logging, get_log_config

# カスタムハンドラー
from setup_repo.logging_handlers import TeeHandler, ColoredConsoleHandler
```

#### Quality Metrics分割 (11関数 → 2モジュール)

**変更前:**

```python
from setup_repo.quality_metrics import calculate_quality_score, collect_ruff_metrics
```

**変更後:**

```python
# メトリクス計算
from setup_repo.quality_metrics import calculate_quality_score, get_quality_metrics

# データ収集
from setup_repo.quality_collectors import collect_ruff_metrics, collect_mypy_metrics
```

#### Interactive Setup分割 (10関数 → 2モジュール)

**変更前:**

```python
from setup_repo.interactive_setup import run_interactive_setup, validate_github_credentials
```

**変更後:**

```python
# メインウィザード
from setup_repo.interactive_setup import run_interactive_setup, setup_wizard

# 入力検証
from setup_repo.setup_validators import validate_github_credentials, validate_directory_path
```

### 2. 責任重複の解消

以下の重複関数が統一されました：

#### プラットフォーム検出統一

**変更前:**

```python
# utils.py と platform_detector.py に重複実装
from setup_repo.utils import detect_platform  # 削除済み
```

**変更後:**

```python
# platform_detector.py に統一
from setup_repo.platform_detector import detect_platform
```

#### UV環境管理統一

**変更前:**

```python
# python_env.py と uv_installer.py に重複実装
from setup_repo.python_env import ensure_uv  # 削除済み
```

**変更後:**

```python
# uv_installer.py に統一
from setup_repo.uv_installer import ensure_uv
```

#### エラーレポート統一

**変更前:**

```python
# ci_error_handler.py と quality_logger.py に重複実装
```

**変更後:**

```python
# quality_logger.py に統一
from setup_repo.quality_logger import save_error_report
```

## 移行手順

### ステップ1: 現在のインポート文を確認

プロジェクト内で以下のコマンドを実行して、変更が必要なインポート文を特定します：

```bash
# 分割されたモジュールのインポートを検索
grep -r "from setup_repo.quality_logger import" . --include="*.py"
grep -r "from setup_repo.ci_error_handler import" . --include="*.py"
grep -r "from setup_repo.logging_config import" . --include="*.py"
grep -r "from setup_repo.quality_metrics import" . --include="*.py"
grep -r "from setup_repo.interactive_setup import" . --include="*.py"

# 重複解消されたモジュールのインポートを検索
grep -r "from setup_repo.utils import detect_platform" . --include="*.py"
grep -r "from setup_repo.python_env import ensure_uv" . --include="*.py"
```

### ステップ2: インポート文を更新

#### 自動更新スクリプト

以下のPythonスクリプトを使用して、インポート文を自動更新できます：

```python
#!/usr/bin/env python3
"""
インポート文自動更新スクリプト
"""

import re
from pathlib import Path

# インポート変更マッピング
IMPORT_MAPPINGS = {
    # Quality Logger分割
    r'from setup_repo\.quality_logger import (QualityError|QualityWarning|handle_quality_error|format_error_message|log_exception|create_error_report)':
        r'from setup_repo.quality_errors import \1',
    r'from setup_repo\.quality_logger import (ColoredFormatter|JSONFormatter|format_log_message|add_color_codes|strip_color_codes)':
        r'from setup_repo.quality_formatters import \1',
    
    # CI Error Handler分割
    r'from setup_repo\.ci_error_handler import (detect_ci_environment|get_system_info|collect_environment_vars|get_ci_metadata|is_ci_environment)':
        r'from setup_repo.ci_environment import \1',
    
    # Logging Config分割
    r'from setup_repo\.logging_config import (TeeHandler|RotatingFileHandler|ColoredConsoleHandler|create_file_handler|create_console_handler)':
        r'from setup_repo.logging_handlers import \1',
    
    # Quality Metrics分割
    r'from setup_repo\.quality_metrics import (collect_ruff_metrics|collect_mypy_metrics|collect_pytest_metrics|collect_coverage_metrics|parse_tool_output)':
        r'from setup_repo.quality_collectors import \1',
    
    # Interactive Setup分割
    r'from setup_repo\.interactive_setup import (validate_github_credentials|validate_directory_path|validate_setup_prerequisites|check_system_requirements)':
        r'from setup_repo.setup_validators import \1',
    
    # 重複解消
    r'from setup_repo\.utils import detect_platform':
        r'from setup_repo.platform_detector import detect_platform',
    r'from setup_repo\.python_env import ensure_uv':
        r'from setup_repo.uv_installer import ensure_uv',
}

def update_imports_in_file(file_path: Path) -> bool:
    """ファイル内のインポート文を更新"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        for pattern, replacement in IMPORT_MAPPINGS.items():
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"更新: {file_path}")
            return True
        
        return False
    
    except Exception as e:
        print(f"エラー: {file_path} - {e}")
        return False

def main():
    """メイン処理"""
    updated_files = []
    
    # Pythonファイルを検索して更新
    for py_file in Path('.').rglob('*.py'):
        if py_file.name.startswith('.') or 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
        
        if update_imports_in_file(py_file):
            updated_files.append(py_file)
    
    print(f"\n更新完了: {len(updated_files)}個のファイルを更新しました")
    for file_path in updated_files:
        print(f"  - {file_path}")

if __name__ == '__main__':
    main()
```

### ステップ3: 後方互換性の活用

移行期間中は、後方互換性機能により古いインポート文も動作します：

```python
# 古いインポート（非推奨警告が表示されますが動作します）
from setup_repo.quality_logger import QualityError  # DeprecationWarning

# 新しいインポート（推奨）
from setup_repo.quality_errors import QualityError
```

### ステップ4: テストの実行

インポート更新後、必ずテストを実行して動作確認を行います：

```bash
# 全テストの実行
uv run pytest

# 特定のモジュールのテスト
uv run pytest tests/unit/test_quality_logger.py
uv run pytest tests/unit/test_quality_errors.py
uv run pytest tests/unit/test_quality_formatters.py

# カバレッジ付きテスト
uv run pytest --cov=src/setup_repo --cov-report=html
```

## 新機能

### 移行チェックポイント機能

リファクタリング過程でのロールバック機能が追加されました：

```python
from setup_repo.migration_checkpoint import MigrationCheckpoint

# チェックポイント管理
checkpoint_manager = MigrationCheckpoint()

# チェックポイント作成
checkpoint_id = checkpoint_manager.create_checkpoint(
    "phase1_complete", 
    "Phase 1完了時点"
)

# ロールバック
checkpoint_manager.rollback_to_checkpoint(checkpoint_id)

# チェックポイント一覧
checkpoints = checkpoint_manager.list_checkpoints()
```

### 後方互換性機能

段階的移行をサポートする互換性機能：

```python
from setup_repo.compatibility import show_migration_guide, check_deprecated_imports

# 移行ガイドの表示
show_migration_guide()

# 非推奨インポートのチェック
check_deprecated_imports()
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. インポートエラー

**問題:**

```
ImportError: cannot import name 'QualityError' from 'setup_repo.quality_logger'
```

**解決方法:**

```python
# 変更前
from setup_repo.quality_logger import QualityError

# 変更後
from setup_repo.quality_errors import QualityError
```

#### 2. 非推奨警告

**問題:**

```
DeprecationWarning: quality_logger.QualityError is deprecated. Use quality_errors.QualityError instead.
```

**解決方法:**
警告に従って新しいインポートパスに更新してください。

#### 3. テスト失敗

**問題:**
モジュール分割後にテストが失敗する

**解決方法:**

1. テストファイル内のインポート文を更新
2. モックの対象パスを新しいモジュールに変更
3. テストデータの構造を確認

```python
# 変更前
@patch('setup_repo.quality_logger.QualityError')

# 変更後  
@patch('setup_repo.quality_errors.QualityError')
```

### デバッグ方法

#### 1. インポート問題の診断

```python
# インポート可能性の確認
try:
    from setup_repo.quality_errors import QualityError
    print("インポート成功")
except ImportError as e:
    print(f"インポートエラー: {e}")
```

#### 2. モジュール構造の確認

```python
import setup_repo
import pkgutil

# パッケージ内のモジュール一覧
for importer, modname, ispkg in pkgutil.iter_modules(setup_repo.__path__):
    print(f"モジュール: {modname}, パッケージ: {ispkg}")
```

#### 3. 後方互換性の確認

```python
import sys

# 互換性モジュールの確認
compatibility_modules = [
    'setup_repo.quality_logger_legacy',
    'setup_repo.ci_error_handler_legacy',
    'setup_repo.logging_config_legacy',
    'setup_repo.quality_metrics_legacy',
    'setup_repo.interactive_setup_legacy'
]

for module_name in compatibility_modules:
    if module_name in sys.modules:
        print(f"互換性モジュール利用可能: {module_name}")
    else:
        print(f"互換性モジュール未登録: {module_name}")
```

## 移行スケジュール

### Phase 1: 準備期間 (1-2週間)

- [ ] 現在のインポート文の調査
- [ ] 移行計画の策定
- [ ] テスト環境での動作確認

### Phase 2: 段階的移行 (2-4週間)

- [ ] 新しいインポート文への更新
- [ ] テストの実行と修正
- [ ] 非推奨警告の解消

### Phase 3: 完了確認 (1週間)

- [ ] 全テストの通過確認
- [ ] 後方互換性機能の無効化検討
- [ ] ドキュメントの最終更新

## サポート

### 質問・問題報告

移行に関する質問や問題がある場合は、以下の方法でサポートを受けられます：

1. **GitHub Issues**: プロジェクトのIssuesページで報告
2. **移行ログ**: `docs/api-changes.md` で詳細な変更履歴を確認
3. **テストケース**: `tests/unit/test_compatibility.py` で互換性テストを参照

### 追加リソース

- [API変更ログ](api-changes.md)
- [アーキテクチャドキュメント](architecture.md)
- [テスト戦略ドキュメント](testing-strategy.md)
- [継続的改善プロセス](continuous-improvement.md)

## まとめ

このリファクタリングにより、以下の改善が実現されました：

- **責任分離の徹底**: 各モジュールが単一の責任を持つ
- **保守性の向上**: コードの理解と修正が容易
- **テストカバレッジ向上**: 80%以上のカバレッジを達成
- **品質ゲート強化**: 継続的な品質監視体制

段階的移行により、既存のコードを破壊することなく改善を実現できます。移行期間中は後方互換性機能を活用し、計画的に新しい構造に移行してください。
