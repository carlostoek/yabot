# Makefile

.PHONY: test-integration test-setup

test-setup:
	@echo "🔧 Instalando dependencias de pruebas..."
	pip install pytest pytest-asyncio pytest-cov

test-integration:
	@scripts/run_integration_tests.sh

test-integration-fast:
	@PYTHONPATH=. python -m pytest tests/integration/test_real_integration.py -v
