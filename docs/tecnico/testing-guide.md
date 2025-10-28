# Testing Guide for Telegram Bot Security Framework

## Overview

This document provides comprehensive guidelines for testing the Telegram bot framework with a focus on security, performance, and reliability.

## Table of Contents

1. [Test Architecture](#test-architecture)
2. [Running Tests](#running-tests)
3. [Test Categories](#test-categories)
4. [Security Testing](#security-testing)
5. [Performance Testing](#performance-testing)
6. [Integration Testing](#integration-testing)
7. [CI/CD Integration](#cicd-integration)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Test Architecture

Our testing framework is built on pytest with the following structure:

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── security/                   # Security-focused tests
│   ├── test_auth_security.py   # Authentication & authorization tests
│   ├── test_data_security.py   # Data protection tests
│   └── test_vulnerability_scanning.py # Vulnerability scans
├── integration/                # Integration tests
│   └── test_app_integration.py # End-to-end integration tests
├── performance/                # Performance and load tests
│   └── test_load_performance.py # Load testing suite
└── utils/                      # Test utilities
    └── test_factories.py       # Test data factories
```

### Key Features

- **Security-First Approach**: Comprehensive security testing at all levels
- **Scalable Architecture**: Tests can grow with the project
- **Performance Monitoring**: Built-in performance benchmarking
- **CI/CD Integration**: Automated testing in GitHub Actions
- **Comprehensive Coverage**: Unit, integration, and security tests

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with our custom script (recommended)
./scripts/run_tests.sh
```

### Test Runner Options

```bash
# Security tests only
./scripts/run_tests.sh --security

# Performance tests only
./scripts/run_tests.sh --performance

# Quick test suite (skip slow tests)
./scripts/run_tests.sh --quick

# With custom coverage threshold
./scripts/run_tests.sh --coverage 90

# Verbose output
./scripts/run_tests.sh --verbose
```

### Environment Setup

Set these environment variables for testing:

```bash
export BOT_TOKEN="your_test_bot_token"
export WEBHOOK_URL="https://your-test-domain.com/webhook"
export LOG_LEVEL="WARNING"  # Reduce noise during testing
```

## Test Categories

### Test Markers

We use pytest markers to categorize tests:

- `@pytest.mark.security` - Security-focused tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.benchmark` - Benchmark tests

### Running Specific Categories

```bash
# Run only security tests
pytest -m security

# Run everything except slow tests
pytest -m "not slow"

# Run integration and security tests
pytest -m "integration or security"
```

## Security Testing

### Authentication & Authorization Tests

Location: `tests/security/test_auth_security.py`

**Key Tests:**
- Bot token validation and protection
- Webhook URL security validation
- Request authentication
- Rate limiting protection
- Input sanitization

```python
@pytest.mark.security
def test_bot_token_not_exposed_in_logs(self, config_manager):
    """Ensure bot tokens are never logged."""
    # Test implementation
```

### Data Security Tests

Location: `tests/security/test_data_security.py`

**Key Tests:**
- Sensitive data encryption
- Memory cleanup after processing
- SQL injection prevention
- File path traversal protection
- User data isolation

### Vulnerability Scanning

Location: `tests/security/test_vulnerability_scanning.py`

**Automated Scans:**
- Dependency vulnerability scanning (Safety)
- Static code analysis (Bandit)
- Secret detection
- SQL injection pattern detection
- Hardcoded credential detection

## Performance Testing

### Load Testing

Location: `tests/performance/test_load_performance.py`

**Key Metrics:**
- Message processing throughput
- Concurrent request handling
- Memory usage under load
- Rate limiting overhead
- Long-running stability

### Benchmarking

```bash
# Run benchmarks
pytest -m benchmark

# Generate benchmark reports
pytest -m benchmark --benchmark-json=results.json
```

## Integration Testing

### Full Application Testing

Location: `tests/integration/test_app_integration.py`

**Test Scenarios:**
- Complete application lifecycle
- Webhook vs. polling mode
- Command routing pipeline
- Error handling integration
- Security pipeline integration

### Example Integration Test

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_application_lifecycle(self, bot_app, mock_env_vars):
    """Test complete application startup, processing, and shutdown."""
    with patch.dict('os.environ', mock_env_vars):
        # Test startup
        success = await bot_app.start()
        assert success
        
        # Test processing
        test_update = SecureTestDataFactory.create_test_webhook_payload()
        response = await bot_app.process_update(test_update)
        
        # Test shutdown
        success = await bot_app.stop()
        assert success
```

## CI/CD Integration

### GitHub Actions Workflows

1. **Main CI Pipeline** (`.github/workflows/ci.yml`)
   - Unit tests across Python versions
   - Integration tests
   - Quality gates
   - Coverage reporting

2. **Security Pipeline** (`.github/workflows/test-security.yml`)
   - Security-focused tests
   - Vulnerability scanning
   - Weekly security audits
   - Automatic issue creation for failures

### Workflow Triggers

- **Push to main/develop**: Full test suite
- **Pull requests**: Tests + security checks
- **Weekly schedule**: Comprehensive security audit
- **Manual dispatch**: On-demand testing

## Best Practices

### Writing Secure Tests

1. **Never use real credentials in tests**
   ```python
   # Good
   BOT_TOKEN = "1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
   
   # Bad - real token
   BOT_TOKEN = os.getenv("REAL_BOT_TOKEN")
   ```

2. **Test security assumptions explicitly**
   ```python
   def test_user_data_isolation(self):
       session1 = UserSession("user1")
       session2 = UserSession("user2")
       
       session1.store_data("secret", "user1_data")
       assert session2.get_data("secret") is None  # Must not access other user's data
   ```

3. **Use factory patterns for test data**
   ```python
   # Use factories for consistent, safe test data
   test_update = SecureTestDataFactory.create_test_webhook_payload()
   ```

### Performance Testing Guidelines

1. **Set realistic thresholds**
   ```python
   # Should process at least 100 messages per second
   assert throughput >= 100
   ```

2. **Monitor resource usage**
   ```python
   # Memory growth should be reasonable
   assert memory_growth < 50 * 1024 * 1024  # 50MB limit
   ```

3. **Test under realistic load**
   ```python
   # Test with concurrent users
   tasks = [process_user_request(user_id) for user_id in user_ids]
   await asyncio.gather(*tasks)
   ```

### Test Organization

1. **Group related tests in classes**
   ```python
   class TestAuthSecurity:
       def test_token_validation(self):
           pass
       
       def test_rate_limiting(self):
           pass
   ```

2. **Use descriptive test names**
   ```python
   def test_webhook_url_validation_rejects_http_urls(self):
       # Clear what is being tested
   ```

3. **Document complex test scenarios**
   ```python
   def test_concurrent_message_processing(self):
       """Test that the application can handle multiple concurrent messages
       without race conditions or data corruption."""
   ```

## Coverage Requirements

- **Minimum Coverage**: 80%
- **Security Modules**: 95%
- **Critical Paths**: 100%

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View detailed coverage
open htmlcov/index.html
```

## Troubleshooting

### Common Issues

1. **Tests timing out**
   - Increase timeout in pytest.ini
   - Use `@pytest.mark.timeout(30)` for specific tests

2. **Coverage failures**
   - Check if new code is properly covered
   - Review excluded files in pytest.ini

3. **Security test failures**
   - Review bandit configuration in .bandit
   - Update security patterns as needed

4. **Performance test instability**
   - Run on dedicated CI runners
   - Allow for reasonable variance in thresholds

### Debug Mode

```bash
# Run with debug output
pytest -v -s --tb=long

# Run specific failing test
pytest tests/security/test_auth_security.py::TestAuthSecurity::test_bot_token_not_exposed_in_logs -v
```

### Test Environment Issues

```bash
# Check environment variables
env | grep BOT_TOKEN

# Verify dependencies
pip list | grep pytest

# Check test discovery
pytest --collect-only
```

## Continuous Improvement

### Adding New Tests

1. **Identify the test category** (unit/integration/security)
2. **Choose appropriate location** in test directory structure
3. **Add relevant markers** (`@pytest.mark.security`, etc.)
4. **Update this documentation** if introducing new patterns

### Security Test Expansion

When adding new security features:

1. **Add corresponding security tests**
2. **Update vulnerability scanning patterns**
3. **Ensure CI pipeline covers new tests**
4. **Document security assumptions**

### Performance Baseline Updates

- Review performance thresholds quarterly
- Update based on infrastructure changes
- Consider feature complexity growth

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Bandit Security Scanner](https://bandit.readthedocs.io/)
- [Safety Vulnerability Scanner](https://pyup.io/safety/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Remember**: Security is not a one-time implementation but an ongoing process. Keep tests updated as the application evolves!