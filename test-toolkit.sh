#!/bin/bash
# Test Script for ads-grafana-toolkit
# Builds and runs the complete test environment

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Parse arguments
MODE="${1:-full}"

if [ "$MODE" = "help" ] || [ "$MODE" = "-h" ] || [ "$MODE" = "--help" ]; then
    echo "Test Script for ads-grafana-toolkit"
    echo ""
    echo "Usage: ./test-toolkit.sh [MODE]"
    echo ""
    echo "Modes:"
    echo "  full       - Build and run complete test environment (default)"
    echo "  build      - Build test container only"
    echo "  up         - Start existing test environment"
    echo "  down       - Stop test environment"
    echo "  clean      - Remove all test containers and volumes"
    echo "  logs       - Show logs from test container"
    echo "  shell      - Open shell in test container"
    echo "  audit      - Run audit script in test container"
    echo "  test       - Run automated tests"
    echo ""
    exit 0
fi

case "$MODE" in
    build)
        print_header "Building Test Container"
        docker-compose -f docker-compose.test.yml build
        print_success "Build complete"
        ;;

    up)
        print_header "Starting Test Environment"
        docker-compose -f docker-compose.test.yml up -d

        print_info "Waiting for services to start..."
        sleep 5

        echo ""
        print_success "Test environment is running!"
        echo ""
        echo "Access points:"
        echo "  Grafana (test):  http://localhost:3000 (admin/admin)"
        echo "  Grafana (docker): http://localhost:3001 (admin/admin)"
        echo "  Prometheus:      http://localhost:9090"
        echo "  Prometheus (standalone): http://localhost:9091"
        echo "  Node Exporter:   http://localhost:9100/metrics"
        echo "  Graphite:        http://localhost:8080"
        echo "  MySQL:           localhost:3306 (root/testpassword)"
        echo ""
        echo "Commands:"
        echo "  ./test-toolkit.sh shell   - Open shell in test container"
        echo "  ./test-toolkit.sh audit   - Run audit script"
        echo "  ./test-toolkit.sh logs    - View logs"
        echo "  ./test-toolkit.sh down    - Stop environment"
        ;;

    down)
        print_header "Stopping Test Environment"
        docker-compose -f docker-compose.test.yml down
        print_success "Test environment stopped"
        ;;

    clean)
        print_header "Cleaning Test Environment"
        print_info "This will remove all test containers and volumes"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f docker-compose.test.yml down -v
            docker rmi grafana-toolkit-test 2>/dev/null || true
            print_success "Cleaned test environment"
        else
            print_info "Cancelled"
        fi
        ;;

    logs)
        print_header "Test Container Logs"
        docker-compose -f docker-compose.test.yml logs -f grafana-toolkit-test
        ;;

    shell)
        print_header "Opening Shell in Test Container"
        print_info "Type 'exit' to leave the container"
        echo ""
        docker exec -it grafana-toolkit-test bash
        ;;

    audit)
        print_header "Running Audit Script"
        docker exec grafana-toolkit-test /opt/ads-grafana-toolkit/setup/scripts/audit_monitoring_stack.py
        ;;

    test)
        print_header "Running Automated Tests"

        # Start environment if not running
        if ! docker ps | grep -q grafana-toolkit-test; then
            print_info "Starting test environment..."
            docker-compose -f docker-compose.test.yml up -d
            sleep 10
        fi

        print_info "Running detection tests..."
        docker exec grafana-toolkit-test bash -c "cd /opt/ads-grafana-toolkit/setup && python3 scripts/detect_grafana.py"

        print_info "Running audit tests..."
        docker exec grafana-toolkit-test bash -c "cd /opt/ads-grafana-toolkit/setup && python3 scripts/audit_monitoring_stack.py"

        print_info "Testing toolkit commands..."
        docker exec grafana-toolkit-test bash -c "cd /opt/ads-grafana-toolkit && python3 -m ads_grafana_toolkit.cli.main --help"

        print_success "All tests passed!"
        ;;

    full|*)
        print_header "Building and Starting Complete Test Environment"

        print_info "Building test container..."
        docker-compose -f docker-compose.test.yml build

        print_info "Starting services..."
        docker-compose -f docker-compose.test.yml up -d

        print_info "Waiting for services to start..."
        sleep 10

        print_info "Running audit to verify services..."
        docker exec grafana-toolkit-test /opt/ads-grafana-toolkit/setup/scripts/audit_monitoring_stack.py

        echo ""
        print_success "Test environment ready!"
        echo ""
        echo "Access points:"
        echo "  Grafana (test):  http://localhost:3000 (admin/admin)"
        echo "  Grafana (docker): http://localhost:3001 (admin/admin)"
        echo "  Prometheus:      http://localhost:9090"
        echo "  Prometheus (standalone): http://localhost:9091"
        echo "  Node Exporter:   http://localhost:9100/metrics"
        echo "  Graphite:        http://localhost:8080"
        echo "  MySQL:           localhost:3306 (root/testpassword)"
        echo ""
        echo "Try these commands:"
        echo "  ./test-toolkit.sh shell   - Open shell in test container"
        echo "  ./test-toolkit.sh audit   - Run audit script"
        echo "  ./test-toolkit.sh test    - Run automated tests"
        echo "  ./test-toolkit.sh down    - Stop environment"
        ;;
esac
