# Setup-Repository: .gitignore自動Push機能 実装計画

## 📋 現状分析

### 課題
- `.gitignore`の自動提案機能は便利だが、提案を受け入れた後のpush忘れが発生
- 複数環境（WSL、Windows、複数PC）で同じ提案が繰り返し表示される
- 手動でpushする手間が発生し、本来の目的（複数環境での一括同期）を阻害

### 現在の実装箇所
- **`gitignore_manager.py`**: `.gitignore`管理ロジック
- **`sync.py`**: リポジトリ同期時に`gitignore_manager.setup_gitignore()`を呼び出し
- **`git_operations.py`**: Git操作の基本機能

## 🎯 実装目標

`.gitignore`提案を受け入れた際に、自動的にcommit & pushを実行する機能を追加する。

### ユーザー体験の改善
```
現在: 提案 → 受け入れ → [push忘れ] → 他環境で再度提案
改善後: 提案 → 受け入れ → 自動commit & push → 他環境で同期完了
```

## 🔧 実装詳細

### 1. `git_operations.py`に新機能を追加

#### 追加する関数
```python
def commit_and_push_file(
    repo_path: Path,
    file_path: str,
    commit_message: str,
    auto_confirm: bool = False,
    skip_hooks: bool = False
) -> bool:
    """
    特定のファイルをcommit & pushする

    Args:
        repo_path: リポジトリのパス
        file_path: commitするファイルの相対パス（例: ".gitignore"）
        commit_message: コミットメッセージ
        auto_confirm: Trueの場合は確認なしで実行
        skip_hooks: Trueの場合はpre-commitフックをスキップ（--no-verify）

    Returns:
        成功したらTrue、失敗またはユーザーがキャンセルしたらFalse
    """
    # 実装内容:
    # 1. リポジトリの状態確認（既にcommit済みでないか）
    # 2. ユーザーに確認（auto_confirmがFalseの場合）
    # 3. git add {file_path}
    # 4. git commit -m "{commit_message}" [--no-verify]
    # 5. pre-commitフック失敗時の処理
    #    a. 自動修正された場合 → 再度addしてcommit
    #    b. エラーの場合 → ユーザーに選択肢提示
    #       - フックをスキップしてcommit（--no-verify）
    #       - 手動で修正する
    #       - キャンセル
    # 6. git push
    # 7. エラーハンドリング（push失敗時の処理）
```

### 2. `gitignore_manager.py`の修正

#### `add_entries()`メソッドの修正
```python
def add_entries(
    self,
    new_entries: list[str],
    dry_run: bool = False,
    auto_push: bool = True  # 新規追加
) -> bool:
    """新しいエントリを.gitignoreに追加"""
    # 既存の処理...

    # 追加成功後
    if success and auto_push and not dry_run:
        from .git_operations import commit_and_push_file

        # ユーザーに確認
        print("\n   📤 .gitignoreをリモートリポジトリにpushしますか？")
        print("   これにより他の環境でも同じ設定が共有されます。")
        response = input("   pushしますか？ [Y/n]: ").strip().lower()

        if response != 'n':
            commit_msg = f"chore: update .gitignore (auto-generated entries)"
            if commit_and_push_file(
                self.repo_path,
                ".gitignore",
                commit_msg,
                auto_confirm=False
            ):
                print("   ✅ .gitignoreをpushしました")
            else:
                print("   ⚠️  pushに失敗しました。後で手動でpushしてください")

    return success
```

#### `setup_gitignore_from_templates()`メソッドの修正
同様に、テンプレートから`.gitignore`を作成した後にもpushオプションを追加。

### 3. `sync.py`の修正

```python
# .gitignore管理（169行目付近）
gitignore_manager = GitignoreManager(repo_path)
# auto_pushパラメータを追加
gitignore_manager.setup_gitignore(dry_run, auto_push=True)
```

### 4. 設定ファイルへのオプション追加

`config.json`に新しい設定項目を追加：
```json
{
  "gitignore_auto_push": true,  // デフォルトでpush確認を表示
  "gitignore_auto_push_no_confirm": false  // trueの場合は確認なしでpush
}
```

## 🔒 安全性の考慮

### エラーハンドリング
1. **Commitの失敗**
   - **pre-commitフックでの失敗** ← 最も頻繁に発生
     - フォーマッターが自動修正を実行
     - Linterがエラーを検出
     - テストが失敗
   - ファイルが既にstaged状態
   - コミットメッセージの問題

2. **Pushの失敗**
   - リモートリポジトリが存在しない
   - 認証エラー
   - ネットワークエラー
   - マージコンフリクト

3. **対策**
   - **pre-commit失敗時の特別処理**
     - 自動修正が行われた場合は再度addしてcommit
     - エラーの場合は詳細を表示して手動対応を促す
     - フックをスキップするオプション提供（`--no-verify`）
   - Push失敗時は警告を表示し、手動pushを促す
   - バックアップは作成しない（.gitignoreの変更のみ）
   - dry_runモードでは実行しない

### ユーザー確認
- デフォルトは「確認あり」で安全性を重視
- `gitignore_auto_push_no_confirm`でスキップ可能（上級者向け）

## 📝 実装順序

### Phase 1: 基本機能（優先度：高）
1. `git_operations.py`に`commit_and_push_file()`を実装
2. `gitignore_manager.py`の`add_entries()`を修正
3. 基本的なエラーハンドリング

### Phase 2: 統合（優先度：高）
4. `sync.py`との統合
5. 動作確認とテスト

### Phase 3: 拡張機能（優先度：中）
6. `setup_gitignore_from_templates()`への適用
7. 設定ファイルのオプション追加
8. ユニットテスト追加

### Phase 4: 改善（優先度：低）
9. ドキュメント更新
10. エラーメッセージの改善
11. パフォーマンス最適化

## 🧪 テストケース

### 必須テスト
1. 正常系：提案受け入れ → commit & push成功
2. ユーザーがpushを拒否した場合
3. **pre-commitフックでの失敗**
   - 自動修正が実行された場合（例：Black, Ruff --fix）
   - エラーで停止する場合（例：Lintエラー）
   - フックをスキップした場合（--no-verify）
4. Pushが失敗した場合（認証エラー等）
5. dry_runモードでの動作
6. 既にcommit済みの場合
7. リモートリポジトリが存在しない場合

### 環境別テスト
- Windows
- WSL
- Linux
- macOS（可能であれば）

## 📊 期待される効果

### Before
```
1. リポジトリ同期実行
2. .gitignore提案 → 受け入れ
3. [push忘れ]
4. 別環境で同期実行
5. 同じ.gitignore提案 → 受け入れ
6. [push忘れ] → 無限ループ
```

### After
```
1. リポジトリ同期実行
2. .gitignore提案 → 受け入れ → 自動push
3. 別環境で同期実行
4. .gitignoreは最新 → 提案なし
5. 完了！
```

## ⚠️ 注意事項

### 実装時の考慮点
- 複数のリポジトリを同期する際、pushが連続で発生する可能性
- GitHub APIのレート制限は影響しない（通常のgit push）
- 大量のリポジトリで同時にpushする場合の処理時間
- **pre-commitフックの処理時間**（特にLinterやFormatter実行時）
- **pre-commitで`.gitignore`が変更される可能性**
  - 例：end-of-file-fixer、trailing-whitespace
  - 自動修正された場合の再commit処理

### 今後の拡張可能性
- 他の自動生成ファイルにも適用可能（例: `.vscode/settings.json`）
- バッチ処理オプション（全リポジトリの変更を一度にpush）
- pushのタイミングを同期完了後にまとめる

## 🚀 実装完了

### ✅ Phase 1 & 2: 完了（2025-09-30）

#### 実装内容

1. **`git_operations.py`**: `commit_and_push_file()`関数を実装
   - 自動commit & push機能
   - pre-commitフック失敗時の自動リトライ
   - upstream未設定時の自動設定
   - 詳細なエラーハンドリング

2. **`gitignore_manager.py`**: auto_push機能の統合
   - `add_entries()`、`setup_gitignore_from_templates()`、`setup_gitignore()`にauto_push対応
   - **自動環境検知機能**の実装
     - pytest/unittest実行時は自動的に無効化
     - CI環境（GitHub Actions, GitLab CI, Jenkins等）で自動的に無効化
     - 環境変数`SETUP_REPO_AUTO_PUSH`で明示的に制御可能
   - コンストラクタで`auto_push`パラメータを受け取り可能

3. **`sync.py`**: auto_push有効化

4. **テスト**: 全27テスト通過
   - 既存テストはすべてパス
   - 新規テスト3件追加（自動検知の動作確認）

#### 環境検知の優先順位

1. **最優先**: `GitignoreManager(auto_push=True/False)` - 明示的な指定
2. **次点**: 環境変数 `SETUP_REPO_AUTO_PUSH=1/0/true/false/yes/no`
3. **自動検知**:
   - pytest実行中 → 無効
   - unittest実行中 → 無効
   - CI環境 → 無効
4. **デフォルト**: 有効

#### 使い方

##### 通常の使用（自動push有効）
```python
manager = GitignoreManager(repo_path)
manager.add_entries([".DS_Store", "*.log"])
# → ユーザーに確認後、自動的にcommit & push
```

##### テスト時（自動的に無効化）
```bash
# pytest実行中は自動的に無効化される
pytest tests/
```

##### 環境変数での制御
```bash
# 明示的に有効化（CI環境でも有効にしたい場合）
SETUP_REPO_AUTO_PUSH=1 python -m setup_repo sync

# 明示的に無効化
SETUP_REPO_AUTO_PUSH=0 python -m setup_repo sync
```

##### プログラムでの制御
```python
# 常に無効化
manager = GitignoreManager(repo_path, auto_push=False)

# 常に有効化
manager = GitignoreManager(repo_path, auto_push=True)
```

---

**Phase 1 & 2の実装が完了しました！本番環境でテストしてフィードバックをお待ちしています。**
