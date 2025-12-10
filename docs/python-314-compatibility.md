# Python 3.14 Compatibility Guide

## Overview

Python 3.14 is currently in experimental/release candidate phase. While Setup-Repository supports Python 3.14 testing (marked as experimental in CI), some pre-commit hooks and development tools may not yet be fully compatible.

## Known Compatibility Issues

### pyupgrade Hook

**Issue**: The `pyupgrade` pre-commit hook is not compatible with Python 3.14 as of December 2025.

**Error Symptoms**:
```
TypeError: cannot use a bytes pattern on a string-like object
  File ".../pyupgrade/_main.py", line 297, in _fix_tokens
    tokenize.cookie_re.match(token.src)
```

**Solutions**:

1. **Option 1: Remove pyupgrade** (Recommended for Python 3.14)
   - Remove the `pyupgrade` hook from your `.pre-commit-config.yaml`
   - Ruff already provides similar functionality with its `UP` rules

2. **Option 2: Pin Python Version for Pre-commit**
   - Use Python 3.11-3.13 for pre-commit hooks
   - Example workflow configuration:
   ```yaml
   - name: Install Python for pre-commit
     run: |
       # Always use Python 3.13 for pre-commit, regardless of test matrix
       uv python install 3.13
       uv tool install pre-commit --python 3.13
   ```

3. **Option 3: Skip pyupgrade in Python 3.14 environments**
   - Add version-specific skip configuration
   ```yaml
   repos:
     - repo: https://github.com/asottile/pyupgrade
       rev: v3.15.0
       hooks:
         - id: pyupgrade
           language_version: python3.13  # Pin to specific version
   ```

## Recommended Pre-commit Configuration

For Python 3.14 compatibility, Setup-Repository's `.pre-commit-config.yaml` deliberately excludes `pyupgrade` and relies on Ruff's `UP` rules instead:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.7
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

Ruff's UP rules cover most of `pyupgrade`'s functionality and are Python 3.14 compatible.

**Template**: A complete Python 3.14 compatible pre-commit configuration template is available at [docs/templates/pre-commit-config-python314.yaml](templates/pre-commit-config-python314.yaml)

## CI/CD Workflow Considerations

### Python Version Detection

When detecting Python version from `pyproject.toml` for pre-commit, avoid defaulting to 3.14:

**⚠️ Problematic Pattern**:
```bash
# DON'T: Defaults to 3.14 on failure
PYTHON_VERSION=$(... || echo "3.14")
```

**✅ Better Pattern**:
```bash
# DO: Use stable Python version as fallback
PYTHON_VERSION=$(parse_python_version || echo "3.13")
```

### Experimental Python 3.14 Testing

If you want to test with Python 3.14:

1. Mark as experimental in your CI matrix:
```yaml
matrix:
  python-version: ["3.11", "3.12", "3.13"]
  include:
    - python-version: "3.14"
      experimental: true

continue-on-error: ${{ matrix.experimental || false }}
```

2. Use a stable Python version (3.11-3.13) for pre-commit hooks:
```yaml
- name: Setup Python for tests
  run: uv python install ${{ matrix.python-version }}

- name: Setup Python for pre-commit
  run: uv python install 3.13  # Fixed version for pre-commit
```

## Migration Guide

If you encounter Python 3.14 + pyupgrade issues in an existing repository:

1. **Immediate Fix**: Remove `pyupgrade` from `.pre-commit-config.yaml`
   ```bash
   # Remove pyupgrade hook section
   sed -i '/pyupgrade/,+3d' .pre-commit-config.yaml
   ```

2. **Enable Ruff's UP rules**: Ensure `pyproject.toml` includes:
   ```toml
   [tool.ruff.lint]
   select = ["E", "F", "W", "I", "N", "UP", ...]
   ```

3. **Update CI**: Pin pre-commit Python version to 3.13
4. **Test**: Run `pre-commit run --all-files` to verify

## Monitoring Tool Compatibility

Check tool compatibility before using Python 3.14 in production:

- ✅ **Compatible**: ruff, basedpyright (pyright), black, bandit
- ⚠️ **Incompatible**: pyupgrade (as of 2025-12)
- ❓ **Unknown**: Check individual tool repositories

## References

- [Python 3.14 Release Schedule](https://peps.python.org/pep-0745/)
- [Ruff UP rules documentation](https://docs.astral.sh/ruff/rules/#pyupgrade-up)
- Setup-Repository's [.pre-commit-config.yaml](.pre-commit-config.yaml) (reference implementation)

## Support

If you encounter other Python 3.14 compatibility issues:

1. Check the tool's GitHub repository for open issues
2. Consider pinning to Python 3.13 for stable operations
3. Report compatibility issues to tool maintainers
4. Use Setup-Repository's configuration as a reference

---

**Last Updated**: 2025-12-08
**Applies to**: Python 3.14.0 and later
