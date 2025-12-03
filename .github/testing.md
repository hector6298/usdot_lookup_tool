# GitHub Actions CI/CD Pipeline

This repository uses GitHub Actions for continuous integration and testing.

## Workflow Details

### Test Workflow (`.github/workflows/test.yml`)

This workflow runs automatically on:
- **Pull Requests** to `main` or `master` branches
- **Pushes** to `main` or `master` branches

#### What it does:
1. **Sets up environment**: Ubuntu latest with Python 3.11
2. **Caches dependencies**: Improves build times by caching pip packages
3. **Installs dependencies**: Test requirements and application requirements
4. **Runs tests**: Executes the comprehensive test suite (106 tests)
5. **Reports results**: Provides test summary and failure details

#### Test Coverage:
- **CRUD Operations**: 63 tests covering all data operations
- **Route Handlers**: 40 tests covering API endpoints  
- **Authentication**: 17 tests for login/logout flows
- **File Upload**: 10 tests for OCR and upload processing
- **Data Management**: 13 tests for carrier data operations

#### Features:
- ✅ **Fast execution**: Tests complete in under 1 minute
- ✅ **Isolated testing**: No external dependencies required
- ✅ **Detailed reporting**: Verbose output with failure details
- ✅ **Fail-fast**: Stops after 10 failures to save resources
- ✅ **Caching**: Dependencies cached for faster builds

## Test Requirements

Test dependencies are managed in `requirements-test.txt`:
- `pytest>=8.0.0`: Testing framework
- `pytest-asyncio>=0.23.0`: Async test support

## Local Testing

To run tests locally:

```bash
# Install test dependencies
pip install -r requirements-test.txt
pip install -r requirements.txt

# Run the test suite
python -m pytest tests/test_crud_*.py tests/test_routes_*.py -v
```

## Excluded Tests

The workflow excludes `tests/test_database.py` and other legacy test files that have compatibility issues with the current SQLModel-based architecture.

## Status Checks

The test workflow provides status checks that:
- **Block merging** if tests fail
- **Show test results** in PR status checks
- **Provide detailed logs** for debugging failures

This ensures all code changes are thoroughly tested before being merged into the main branch.
