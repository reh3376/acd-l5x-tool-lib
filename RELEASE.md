# Release Guide

This guide explains how to release a new version of the `plc-format-converter` package to PyPI.

## Prerequisites

1. **PyPI Account**: Ensure you have a PyPI account and are a maintainer of the `plc-format-converter` project
2. **GitHub Permissions**: Ensure you have write access to the repository
3. **Trusted Publishing**: The repository should be configured for PyPI trusted publishing (recommended)

## Release Process

### 1. Prepare the Release

1. **Update Version**: Update the version in `pyproject.toml`:
   ```toml
   [project]
   version = "1.2.3"  # Update to new version
   ```

2. **Update Changelog**: Add release notes to `CHANGELOG.md` (if it exists)

3. **Test Locally**: Run the full test suite:
   ```bash
   uv run pytest tests/ -v
   uv run ruff check .
   uv run mypy src/plc_format_converter
   ```

4. **Build and Test Package**:
   ```bash
   python -m build
   python -m twine check dist/*
   ```

### 2. Create and Push Release

1. **Commit Changes**:
   ```bash
   git add .
   git commit -m "Release v1.2.3"
   git push origin main
   ```

2. **Create Git Tag**:
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```

3. **Create GitHub Release**:
   - Go to the [GitHub Releases page](https://github.com/reh3376/acd-l5x-tool-lib/releases)
   - Click "Create a new release"
   - Select the tag you just created (`v1.2.3`)
   - Add release title: `v1.2.3`
   - Add release notes describing changes
   - Click "Publish release"

### 3. Automated Publishing

Once you publish the GitHub release, the automated workflow will:

1. **Trigger**: The `release-package.yml` workflow will automatically start
2. **Build**: Create distribution packages (wheel and source)
3. **Test**: Verify the packages are valid
4. **Publish**: Upload to PyPI using trusted publishing

### 4. Verify Release

1. **Check PyPI**: Verify the package appears on [PyPI](https://pypi.org/project/plc-format-converter/)
2. **Test Installation**: Test installing the new version:
   ```bash
   pip install plc-format-converter==1.2.3
   ```
3. **Test CLI Tools**: Verify command-line tools work:
   ```bash
   acd2l5x --help
   l5x2acd --help
   plc-convert --help
   ```

## Trusted Publishing Setup

### PyPI Configuration

1. Go to your [PyPI account settings](https://pypi.org/manage/account/publishing/)
2. Add a new trusted publisher with:
   - **PyPI Project Name**: `plc-format-converter`
   - **Owner**: `reh3376`
   - **Repository name**: `acd-l5x-tool-lib`
   - **Workflow filename**: `release-package.yml`
   - **Environment name**: (leave empty)

### Benefits of Trusted Publishing

- ✅ No need to manage API tokens
- ✅ More secure authentication
- ✅ Automatic credential rotation
- ✅ Audit trail of releases

## Manual Publishing (Fallback)

If trusted publishing is not available, you can publish manually:

1. **Install Publishing Tools**:
   ```bash
   pip install build twine
   ```

2. **Build Package**:
   ```bash
   python -m build
   ```

3. **Upload to PyPI**:
   ```bash
   python -m twine upload dist/*
   ```

## Troubleshooting

### Workflow Fails

1. Check the [Actions tab](https://github.com/reh3376/acd-l5x-tool-lib/actions) for error details
2. Common issues:
   - Version already exists on PyPI (use `skip-existing: true`)
   - Trusted publishing not configured
   - Package validation errors

### PyPI Upload Errors

1. **403 Forbidden**: Check trusted publishing configuration
2. **400 Bad Request**: Package validation failed - check with `twine check`
3. **409 Conflict**: Version already exists - increment version number

### Version Conflicts

If you need to fix a release:

1. **Patch Release**: Increment patch version (1.2.3 → 1.2.4)
2. **Yank Release**: Use PyPI web interface to yank problematic version
3. **Never Delete**: Don't delete releases, use yanking instead

## Release Checklist

- [ ] Version updated in `pyproject.toml`
- [ ] Changelog updated (if applicable)
- [ ] Tests passing locally
- [ ] Package builds without errors
- [ ] Changes committed and pushed
- [ ] Git tag created and pushed
- [ ] GitHub release created and published
- [ ] Workflow completed successfully
- [ ] Package available on PyPI
- [ ] Installation tested

## Support

For release-related issues:

1. Check [GitHub Actions logs](https://github.com/reh3376/acd-l5x-tool-lib/actions)
2. Review [PyPI project page](https://pypi.org/project/plc-format-converter/)
3. Contact repository maintainers 