# 設定ファイル整合性管理

本ドキュメントは、ルール6章「セキュリティ・品質保証」に従って、各設定ファイル間の整合性を管理します。

## セキュリティツール設定の整合性

### Safety設定

**pyproject.toml**:
```toml
[dependency-groups]
security = [
    "safety>=3.6.0",  # 新しいscanコマンド対応バージョン
    "bandit>=1.8.6",
    "pip-licenses>=5.0.0",
]
```

**pre-commit設定**:
```yaml
- id: safety-scan
  entry: uv run safety scan --output screen
```

**Makefile**:
```makefile
security-scan:
    uv run safety scan --output screen --detailed-output
```

### Bandit設定

**pyproject.toml**:
```toml
[tool.bandit]
exclude_dirs = ["tests", "venv", ".venv", "build", "dist"]
```

**pre-commit設定**:
```yaml
- id: bandit
  args: ["-c", "pyproject.toml"]
  files: ^src/
```

## 整合性チェックリスト

- [x] Safety: pyproject.toml ↔ pre-commit ↔ Makefile
- [x] Bandit: pyproject.toml ↔ pre-commit ↔ Makefile
- [x] バージョン要件の統一
- [x] 実行オプションの統一
- [x] 除外設定の統一

## 更新手順

1. **pyproject.toml**を基準として設定を更新
2. **pre-commit設定**を同期
3. **Makefile**のターゲットを同期
4. `uv sync --group security`で依存関係を更新
5. `make security`で動作確認

## 関連ファイル

- `pyproject.toml`: 依存関係とツール設定
- `.pre-commit-config.yaml`: pre-commitフック設定
- `Makefile`: 開発者向けコマンド
- `.safety-project.ini`: Safety Platform設定
- `docs/security-exceptions.md`: セキュリティ例外記録
