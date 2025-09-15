# セキュリティ修正計画書

## Amazon Q Developer セキュリティスキャン結果

### 検出された問題概要
- **High Severity**: 19件（Path Traversal 8件、Command Injection 7件、XSS 1件、認証 1件、エラーハンドリング 2件）
- **Medium Severity**: 20件（パフォーマンス 8件、可読性 6件、エラーハンドリング 4件、ログ 2件）
- **Low/Info Severity**: 1件

## 🚨 High Severity 修正計画（優先度：最高）

### 1. CWE-22 Path Traversal（8件）
#### 対象ファイル
- `quality_collectors.py` (2件)
- `cli.py` (2件)
- `gitignore_manager.py` (1件)
- `platform_detector.py` (1件)
- `utils.py` (1件)
- `ci_error_handler.py` (1件)

#### 修正方針
```python
# 修正前（危険）
file_path = Path(user_input) / "config.json"

# 修正後（安全）
from pathlib import Path
import os.path

def safe_join(base_path: Path, user_path: str) -> Path:
    """パストラバーサル攻撃を防ぐ安全なパス結合"""
    resolved = (base_path / user_path).resolve()
    if not str(resolved).startswith(str(base_path.resolve())):
        raise ValueError("Path traversal detected")
    return resolved
```

### 2. CWE-77/78/88 OS Command Injection（7件）
#### 対象ファイル
- `quality_metrics.py` (1件)
- `interactive_setup.py` (1件)
- `setup_validators.py` (2件)
- `git_operations.py` (1件)
- `python_env.py` (1件)

#### 修正方針
```python
# 修正前（危険）
subprocess.run(["git", user_input])

# 修正後（安全）
import shutil
import subprocess

def safe_subprocess_run(cmd: list, **kwargs):
    """安全なsubprocess実行"""
    # 実行可能ファイルの絶対パスを取得
    if cmd and not os.path.isabs(cmd[0]):
        executable = shutil.which(cmd[0])
        if not executable:
            raise FileNotFoundError(f"Executable not found: {cmd[0]}")
        cmd[0] = executable

    # タイムアウト設定
    kwargs.setdefault('timeout', 30)
    return subprocess.run(cmd, **kwargs)
```

### 3. CWE-20/79/80 Cross-site Scripting（1件）
#### 対象ファイル
- `quality_formatters.py` (1件)

#### 修正方針
```python
# 修正前（危険）
html_content = f"<div>{user_data}</div>"

# 修正後（安全）
import html

def safe_html_format(data: str) -> str:
    """XSS攻撃を防ぐHTMLエスケープ"""
    return html.escape(data, quote=True)

html_content = f"<div>{safe_html_format(user_data)}</div>"
```

### 4. Authorization Issues（1件）
#### 対象ファイル
- `logging_config.py` (1件)

#### 修正方針
```python
# 修正前（危険）
if request.cookies.get('role') == 'admin':
    # 管理者機能

# 修正後（安全）
def check_admin_role(session_data: dict) -> bool:
    """サーバーサイドセッションベースの認証チェック"""
    return session_data.get('authenticated_role') == 'admin'

if check_admin_role(session):
    # 管理者機能
```

## ⚠️ Medium Severity 修正計画（優先度：高）

### 1. Performance Issues（8件）
#### 主要問題
- 文字列連結の非効率性
- 重複処理
- タイムアウト未設定

#### 修正方針
```python
# 文字列連結最適化
# 修正前
result = ""
for item in items:
    result += str(item)

# 修正後
result = "".join(str(item) for item in items)

# タイムアウト設定
subprocess.run(cmd, timeout=30)
```

### 2. Error Handling Issues（6件）
#### 修正方針
```python
# 修正前
try:
    risky_operation()
except Exception:
    pass  # 不適切

# 修正後
try:
    risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    # 適切な回復処理
```

### 3. Logging Issues（2件）
#### 修正方針
```python
# 修正前（ルール違反）
print("Debug message")

# 修正後（ルール準拠）
import logging
logger = logging.getLogger(__name__)
logger.debug("Debug message")
```

## 📋 実装計画

### Phase 1: Critical Security Fixes（即座実行）
1. **Path Traversal対策**
   - `safe_join()` ヘルパー関数実装
   - 全パス操作箇所の修正

2. **Command Injection対策**
   - `safe_subprocess_run()` ヘルパー関数実装
   - 全subprocess呼び出しの修正

3. **XSS対策**
   - HTML出力のエスケープ処理追加

### Phase 2: Authentication & Error Handling
1. **認証強化**
   - サーバーサイド認証実装

2. **エラーハンドリング改善**
   - 適切な例外処理追加

### Phase 3: Performance & Code Quality
1. **パフォーマンス最適化**
   - 文字列連結改善
   - 重複処理削除

2. **ログ出力修正**
   - print文をlogging呼び出しに変更

## 🛡️ セキュリティ強化ヘルパー関数

### 共通セキュリティユーティリティ
```python
# src/setup_repo/security_helpers.py
from pathlib import Path
import subprocess
import shutil
import html
import logging
from typing import List, Any

logger = logging.getLogger(__name__)

def safe_path_join(base: Path, user_path: str) -> Path:
    """パストラバーサル攻撃防止"""
    resolved = (base / user_path).resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise ValueError(f"Path traversal detected: {user_path}")
    return resolved

def safe_subprocess(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """コマンドインジェクション攻撃防止"""
    if not cmd:
        raise ValueError("Empty command")

    # 絶対パス解決
    if not os.path.isabs(cmd[0]):
        executable = shutil.which(cmd[0])
        if not executable:
            raise FileNotFoundError(f"Executable not found: {cmd[0]}")
        cmd[0] = executable

    kwargs.setdefault('timeout', 30)
    return subprocess.run(cmd, **kwargs)

def safe_html_escape(data: Any) -> str:
    """XSS攻撃防止"""
    return html.escape(str(data), quote=True)
```

## 🎯 成功指標

### Phase 1完了時
- **High Severity**: 0件
- **Path Traversal**: 完全解決
- **Command Injection**: 完全解決
- **XSS**: 完全解決

### Phase 2完了時
- **認証問題**: 解決
- **Critical Error Handling**: 解決

### Phase 3完了時
- **Medium Severity**: 50%以下に削減
- **パフォーマンス問題**: 主要問題解決
- **ログ出力**: ルール準拠100%

## 📝 注意事項

### 修正時の絶対ルール
- **機能破壊禁止**: 既存機能を壊さない
- **テスト実行**: 修正後は必ずテスト実行
- **段階的修正**: 一度に大量修正しない
- **バックアップ**: 修正前にコミット

### 品質保証
- 各修正後にセキュリティスキャン再実行
- テストカバレッジ維持（84.68%以上）
- Phase 2の安定性維持

## 🔄 継続的セキュリティ

### 自動化
- pre-commitフックにセキュリティチェック追加
- CI/CDパイプラインでセキュリティスキャン実行
- 定期的な脆弱性スキャン

### 開発プロセス
- セキュアコーディング標準の策定
- コードレビューでセキュリティチェック必須
- セキュリティ教育の実施
