# リファクタリング移行ガイド

## 🚀 開始前の準備

### 環境確認
```bash
# 現在のブランチ確認
git branch

# 作業ブランチ作成
git checkout -b refactor/responsibility-separation

# 依存関係確認
uv sync --dev
```

### ベースライン確立
```bash
# 現在の品質メトリクス記録
uv run python main.py quality --save-trend

# テスト実行
uv run pytest tests/ --cov=src/setup_repo

# 品質チェック
make quality-gate
```

## 📝 Phase 1: 重複解消の実装例

### Task 1.1: detect_platform()統一

**Before (utils.py)**:
```python
def detect_platform() -> str:
    import platform
    system = platform.system().lower()
    # 簡易実装
```

**After**: 削除して以下に統一
```python
from .platform_detector import detect_platform
```

**変更箇所**:
- `src/setup_repo/sync.py`: インポート変更
- `tests/unit/test_utils.py`: テスト削除

### Task 1.2: ensure_uv()統一

**変更前**:
```python
# python_env.py
def ensure_uv():
    # 重複実装

# uv_installer.py  
def ensure_uv():
    # メイン実装
```

**変更後**:
```python
# python_env.py
from .uv_installer import ensure_uv

# uv_installer.py (変更なし)
def ensure_uv():
    # 統一実装
```

## 🔧 Phase 2: モジュール分割の実装例

### Task 2.1: quality_logger.py分割

**新ファイル構造**:
```
src/setup_repo/
├── quality_logger.py      # 基本ログ機能
├── quality_errors.py      # エラークラス
└── quality_formatters.py  # フォーマッター
```

**移行手順**:
1. 新ファイル作成
2. 関数・クラスの移動
3. インポート文の更新
4. テストの分割

**例: quality_errors.py作成**:
```python
"""品質チェック専用エラークラス"""

class QualityCheckError(Exception):
    """品質チェック関連のベースエラークラス"""
    pass

class RuffError(QualityCheckError):
    """Ruffリンティングエラー"""
    pass
```

## 🧪 テスト移行パターン

### 既存テストの分割
```python
# Before: test_quality_logger.py (大きなファイル)
class TestQualityLogger:
    def test_logging_functions(self):
        pass
    
    def test_error_classes(self):
        pass
    
    def test_formatters(self):
        pass

# After: 分割
# test_quality_logger.py
class TestQualityLogger:
    def test_logging_functions(self):
        pass

# test_quality_errors.py  
class TestQualityErrors:
    def test_error_classes(self):
        pass

# test_quality_formatters.py
class TestQualityFormatters:
    def test_formatters(self):
        pass
```

## 🔍 検証コマンド

### 各Phase完了後の確認
```bash
# テスト実行
uv run pytest tests/ -v

# 品質チェック
uv run ruff check .
uv run mypy src/

# カバレッジ確認
uv run pytest --cov=src/setup_repo --cov-report=html

# 統合テスト
uv run python main.py setup --help
uv run python main.py sync --dry-run
```

### 品質メトリクス比較
```bash
# リファクタリング後のメトリクス
uv run python main.py quality

# トレンド比較
uv run python main.py trend analyze --days 7
```

## ⚠️ 注意事項

### 破壊的変更の回避
- 既存のpublic APIは維持
- deprecation警告の追加
- 段階的な移行

### テストの継続実行
- 各変更後にテスト実行
- カバレッジの低下を防ぐ
- CI/CDパイプラインの確認

### コミット戦略
```bash
# 小さな単位でコミット
git add src/setup_repo/utils.py
git commit -m "refactor: remove duplicate detect_platform() from utils"

git add src/setup_repo/sync.py  
git commit -m "refactor: update import for detect_platform()"
```

## 🎯 完了確認

### 最終チェックリスト
- [ ] 全テスト通過
- [ ] カバレッジ維持
- [ ] 品質ゲート通過
- [ ] 既存機能の動作確認
- [ ] ドキュメント更新

### マージ準備
```bash
# 最終テスト
make quality-gate

# プルリクエスト作成
git push origin refactor/responsibility-separation

# レビュー依頼
# - 変更内容の説明
# - テスト結果の添付
# - 品質メトリクスの比較
```