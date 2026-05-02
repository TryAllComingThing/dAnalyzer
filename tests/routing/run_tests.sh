#!/usr/bin/env bash
# 路由测试运行脚本
# 用法: ./run_tests.sh [p0|p1|p2|p3|all]

set -euo pipefail

cd "$(dirname "$0")/../.."

LEVEL="${1:-p0}"

case "$LEVEL" in
    p0)
        echo "=== Running P0 core routing tests ==="
        pytest tests/routing/test_routing_comprehensive.py -m p0 -v --tb=short
        ;;
    p0p1|p1)
        echo "=== Running P0+P1 routing tests ==="
        pytest tests/routing/test_routing_comprehensive.py -m "p0 or p1" -v --tb=short
        ;;
    p2)
        echo "=== Running P0+P1+P2 routing tests ==="
        pytest tests/routing/test_routing_comprehensive.py -m "p0 or p1 or p2" -v --tb=short
        ;;
    all)
        echo "=== Running ALL routing tests ==="
        pytest tests/routing/ -v --tb=short
        ;;
    *)
        echo "Usage: $0 [p0|p1|p2|all]"
        echo "  p0  - Core tests (every commit)"
        echo "  p1  - P0+P1 (daily)"
        echo "  p2  - P0+P1+P2 (pre-release)"
        echo "  all - All tests"
        exit 1
        ;;
esac
