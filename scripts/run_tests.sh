#!/bin/bash
# Comprehensive test runner script for the bot security framework

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
COVERAGE_THRESHOLD=80
VERBOSE=false
SECURITY_ONLY=false
PERFORMANCE_ONLY=false
INTEGRATION_ONLY=false
QUICK=false
GENERATE_REPORT=true

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Run comprehensive test suite for the Telegram bot framework

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -c, --coverage PERCENT  Set coverage threshold (default: 80)
    -s, --security          Run only security tests
    -p, --performance       Run only performance tests
    -i, --integration       Run only integration tests
    -q, --quick             Run quick test suite (skip slow tests)
    --no-report             Skip HTML report generation
    --install-deps          Install test dependencies before running

Examples:
    $0                      # Run all tests
    $0 -v -c 90            # Run all tests with 90% coverage threshold
    $0 -s                  # Run only security tests
    $0 -q                  # Run quick test suite
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        -s|--security)
            SECURITY_ONLY=true
            shift
            ;;
        -p|--performance)
            PERFORMANCE_ONLY=true
            shift
            ;;
        -i|--integration)
            INTEGRATION_ONLY=true
            shift
            ;;
        -q|--quick)
            QUICK=true
            shift
            ;;
        --no-report)
            GENERATE_REPORT=false
            shift
            ;;
        --install-deps)
            INSTALL_DEPS=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Set up environment
export BOT_TOKEN="${BOT_TOKEN:-1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw}"
export WEBHOOK_URL="${WEBHOOK_URL:-https://example.com/webhook}"
export LOG_LEVEL="${LOG_LEVEL:-WARNING}"

print_status "Starting test execution..."

# Check if we're in the right directory
if [[ ! -f "pytest.ini" ]]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Install dependencies if requested
if [[ "$INSTALL_DEPS" == "true" ]]; then
    print_status "Installing test dependencies..."
    pip install -r requirements-test.txt
fi

# Build pytest command
PYTEST_CMD="pytest"

# Add verbosity
if [[ "$VERBOSE" == "true" ]]; then
    PYTEST_CMD="$PYTEST_CMD -v"
else
    PYTEST_CMD="$PYTEST_CMD -q"
fi

# Add coverage
PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=term-missing --cov-report=xml"

if [[ "$COVERAGE_THRESHOLD" -gt 0 ]]; then
    PYTEST_CMD="$PYTEST_CMD --cov-fail-under=$COVERAGE_THRESHOLD"
fi

# Add HTML report if requested
if [[ "$GENERATE_REPORT" == "true" ]]; then
    PYTEST_CMD="$PYTEST_CMD --html=test-report.html --self-contained-html"
fi

# Configure test selection
if [[ "$SECURITY_ONLY" == "true" ]]; then
    print_status "Running security tests only..."
    PYTEST_CMD="$PYTEST_CMD tests/security/ -m security"
elif [[ "$PERFORMANCE_ONLY" == "true" ]]; then
    print_status "Running performance tests only..."
    if [[ "$QUICK" == "true" ]]; then
        PYTEST_CMD="$PYTEST_CMD tests/performance/ -m 'performance and not slow'"
    else
        PYTEST_CMD="$PYTEST_CMD tests/performance/ -m performance"
    fi
elif [[ "$INTEGRATION_ONLY" == "true" ]]; then
    print_status "Running integration tests only..."
    PYTEST_CMD="$PYTEST_CMD tests/integration/ -m integration"
else
    print_status "Running complete test suite..."
    if [[ "$QUICK" == "true" ]]; then
        PYTEST_CMD="$PYTEST_CMD tests/ -m 'not slow'"
    else
        PYTEST_CMD="$PYTEST_CMD tests/"
    fi
fi

# Run pre-test checks
print_status "Running pre-test security checks..."

# Check for basic security issues
if command -v bandit >/dev/null 2>&1; then
    print_status "Running Bandit security analysis..."
    bandit -r src/ -ll -q || print_warning "Bandit found potential security issues"
else
    print_warning "Bandit not installed - skipping static security analysis"
fi

# Check dependencies for vulnerabilities
if command -v safety >/dev/null 2>&1; then
    print_status "Checking dependencies for vulnerabilities..."
    safety check --short-report || print_warning "Safety found potential vulnerabilities"
else
    print_warning "Safety not installed - skipping dependency vulnerability check"
fi

# Run the tests
print_status "Executing test suite..."
print_status "Command: $PYTEST_CMD"

if eval $PYTEST_CMD; then
    print_success "All tests passed!"
    TEST_EXIT_CODE=0
else
    print_error "Some tests failed!"
    TEST_EXIT_CODE=1
fi

# Post-test analysis
print_status "Performing post-test analysis..."

# Check test coverage
if [[ -f "coverage.xml" ]]; then
    COVERAGE_PERCENT=$(python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
root = tree.getroot()
coverage = root.get('line-rate')
print(f'{float(coverage)*100:.1f}')
" 2>/dev/null || echo "Unknown")
    
    print_status "Test coverage: $COVERAGE_PERCENT%"
fi

# Generate summary report
cat << EOF

=== TEST EXECUTION SUMMARY ===
Test Suite: $(if [[ "$SECURITY_ONLY" == "true" ]]; then echo "Security Only"; elif [[ "$PERFORMANCE_ONLY" == "true" ]]; then echo "Performance Only"; elif [[ "$INTEGRATION_ONLY" == "true" ]]; then echo "Integration Only"; else echo "Complete Suite"; fi)
Coverage Threshold: $COVERAGE_THRESHOLD%
$(if [[ "$COVERAGE_PERCENT" != "Unknown" ]]; then echo "Actual Coverage: $COVERAGE_PERCENT%"; fi)
Mode: $(if [[ "$QUICK" == "true" ]]; then echo "Quick"; else echo "Full"; fi)
Exit Code: $TEST_EXIT_CODE

Reports Generated:
$(if [[ -f "coverage.xml" ]]; then echo "- coverage.xml (XML coverage report)"; fi)
$(if [[ -f "test-report.html" ]] && [[ "$GENERATE_REPORT" == "true" ]]; then echo "- test-report.html (HTML test report)"; fi)

EOF

# Show report locations
if [[ "$GENERATE_REPORT" == "true" ]] && [[ -f "test-report.html" ]]; then
    print_success "HTML test report generated: test-report.html"
fi

if [[ -f "coverage.xml" ]]; then
    print_success "Coverage report generated: coverage.xml"
fi

# Cleanup
print_status "Cleaning up temporary files..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

if [[ $TEST_EXIT_CODE -eq 0 ]]; then
    print_success "Test execution completed successfully!"
else
    print_error "Test execution failed!"
fi

exit $TEST_EXIT_CODE