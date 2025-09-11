# .gitignore テンプレート

このディレクトリには、異なる開発環境・言語用の.gitignoreテンプレートが含まれています。

## 利用可能なテンプレート

- `common.gitignore` - OS固有ファイル、IDE、一時ファイルなど
- `python.gitignore` - Python開発用（__pycache__、.venv、テストカバレッジなど）
- `node.gitignore` - Node.js開発用（node_modules、npm-debug.logなど）
- `uv.gitignore` - uvパッケージマネージャー用
- `vscode.gitignore` - VS Code設定ファイル用

## 使用方法

GitignoreManagerクラスが自動的にこれらのテンプレートを読み込み、
プロジェクトの種類に応じて適切な.gitignoreエントリを追加します。

```python
from setup_repo.gitignore_manager import GitignoreManager

manager = GitignoreManager(repo_path)
manager.setup_gitignore_from_templates(['common', 'python', 'uv'])
```
