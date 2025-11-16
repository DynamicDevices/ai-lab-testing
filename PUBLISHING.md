# Publishing Guide

This guide explains how to package and publish `lab-testing` to PyPI.

## Prerequisites

1. **PyPI Account**: Create accounts on:
   - [Test PyPI](https://test.pypi.org/) (for testing)
   - [PyPI](https://pypi.org/) (for production)

2. **API Tokens**: Generate API tokens from both sites:
   - Test PyPI: https://test.pypi.org/manage/account/token/
   - PyPI: https://pypi.org/manage/account/token/

3. **Build Tools**: Install required tools:
   ```bash
   python3.10 -m pip install --upgrade build twine
   ```

## Configuration

### PyPI Credentials

Create `~/.pypirc` file:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-<your-production-token>

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-<your-test-token>
```

**Security Note**: Never commit `.pypirc` to git. Add it to `.gitignore`.

## Building the Package

### 1. Clean Previous Builds

```bash
make clean
```

### 2. Build Distribution Files

```bash
make build
```

This creates:
- `dist/lab_testing-<version>-py3-none-any.whl` (wheel)
- `dist/lab_testing-<version>.tar.gz` (source distribution)

### 3. Check Distribution

```bash
make check-dist
```

This validates the package files.

## Publishing

### Test on Test PyPI First

```bash
make publish-test
```

Then test installation:
```bash
python3.10 -m pip install --index-url https://test.pypi.org/simple/ lab-testing
```

### Publish to Production PyPI

Once tested, publish to production:

```bash
make publish
```

## Version Management

### Update Version

1. Update version in `lab_testing/version.py`:
   ```python
   __version__ = "0.1.1"
   ```

2. Update version in `pyproject.toml`:
   ```toml
   version = "0.1.1"
   ```

3. Update `CHANGELOG.md` with release notes

4. Commit and tag:
   ```bash
   git add lab_testing/version.py pyproject.toml CHANGELOG.md
   git commit -m "Release version 0.1.1"
   git tag -a v0.1.1 -m "Release version 0.1.1"
   git push origin main --tags
   ```

5. Build and publish:
   ```bash
   make clean build publish
   ```

## Installation for Users

After publishing, users can install:

```bash
# From PyPI
python3.10 -m pip install lab-testing

# With dev dependencies
python3.10 -m pip install "lab-testing[dev]"
```

## Troubleshooting

### "Package already exists" Error

- Check if version already exists on PyPI
- Increment version number

### Authentication Errors

- Verify `.pypirc` file exists and has correct tokens
- Check token permissions on PyPI

### Build Errors

- Ensure all dependencies are listed in `pyproject.toml`
- Check `MANIFEST.in` includes all necessary files
- Run `make clean` before rebuilding

## Automated Publishing (Optional)

For CI/CD, you can use GitHub Actions:

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: python3.10 -m pip install build twine
      - run: python3.10 -m build
      - run: python3.10 -m twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
```

