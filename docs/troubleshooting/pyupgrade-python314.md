# Troubleshooting: pyupgrade + Python 3.14 Error

## Error Symptoms

If you see this error when running pre-commit with Python 3.14:

```
TypeError: cannot use a bytes pattern on a string-like object
  File ".../pyupgrade/_main.py", line 297, in _fix_tokens
    tokenize.cookie_re.match(token.src)
```

## Root Cause

The `pyupgrade` pre-commit hook is not compatible with Python 3.14 due to changes in Python's internal tokenize module.

## Quick Fix

### Option 1: Remove pyupgrade (Recommended)

1. Remove the `pyupgrade` hook from `.pre-commit-config.yaml`:

```bash
# Find and remove the pyupgrade section
sed -i '/pyupgrade/,+4d' .pre-commit-config.yaml
```

2. Ensure Ruff's UP rules are enabled in `pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4"]
```

3. Run pre-commit:

```bash
pre-commit run --all-files
```

### Option 2: Pin Pre-commit to Python 3.13

Modify your CI workflow to use Python 3.13 for pre-commit:

```yaml
- name: Install Python for pre-commit
  run: |
    uv python install 3.13
    uv tool install pre-commit --python 3.13

- name: Run pre-commit
  run: pre-commit run --all-files
```

### Option 3: Use the Template

Copy Setup-Repository's Python 3.14 compatible pre-commit configuration:

```bash
curl -o .pre-commit-config.yaml \
  https://raw.githubusercontent.com/scottlz0310/Setup-Repository/main/docs/templates/pre-commit-config-python314.yaml
```

## Complete Solution

For detailed information and best practices, see:
- [Python 3.14 Compatibility Guide](../python-314-compatibility.md)
- [Pre-commit Configuration Template](../templates/pre-commit-config-python314.yaml)
- Setup-Repository's [.pre-commit-config.yaml](../../.pre-commit-config.yaml) (reference)

## Testing the Fix

After applying the fix:

```bash
# Clear pre-commit cache
pre-commit clean

# Run all hooks
pre-commit run --all-files

# If successful, commit the changes
git add .pre-commit-config.yaml pyproject.toml
git commit -m "fix: remove pyupgrade for Python 3.14 compatibility"
```

## Prevention

When setting up a new Python project that may use Python 3.14:

1. **Don't include pyupgrade** in `.pre-commit-config.yaml`
2. **Use Ruff** with UP rules instead
3. **Pin pre-commit** to Python 3.13 in CI if testing with 3.14
4. **Mark Python 3.14 as experimental** in CI matrix

Example CI matrix:

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
    include:
      - python-version: "3.14"
        experimental: true

continue-on-error: ${{ matrix.experimental || false }}
```

## Related Issues

- PDF-PageTool: [Actions run #20015230935](https://github.com/scottlz0310/PDF-PageTool/actions/runs/20015230935)
- pyupgrade compatibility: Track at [asottile/pyupgrade](https://github.com/asottile/pyupgrade)

---

**Last Updated**: 2025-12-08
**Status**: pyupgrade does not support Python 3.14 as of 2025-12-08
