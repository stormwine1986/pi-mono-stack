#!/bin/bash

# IRM CLI Entrypoint
# Usage: irm <command> [args]

COMMAND=$1
shift

case "$COMMAND" in
    tracer)
        python3 /app/scripts/ontology/tracer.py "$@"
        ;;
    advisor)
        python3 /app/scripts/analyzer/portfolio_advisor.py "$@"
        ;;
    portfolio)
        python3 /app/scripts/analyzer/portfolio_viewer.py "$@"
        ;;
    nodes)
        python3 /app/scripts/analyzer/node_viewer.py "$@"
        ;;
    init-db)
        python3 /app/scripts/ontology/sync_schema.py "$@"
        ;;
    pe-bands)
        python3 /app/scripts/analyzer/config_manager.py pe-bands "$@"
        ;;
    help|*)
        echo "IRM (Investment Risk Management) CLI"
        echo "Usage: irm <command> [options]"
        echo ""
        echo "Available Commands:"
        echo "  tracer    - Trace macro-to-micro impact propagation"
        echo "  advisor   - Get Kelly-based portfolio allocation advice"
        echo "  portfolio - List asset allocation status for a specified owner"
        echo "  nodes     - List all entities in the graph (excluding portfolios)"
        echo "  init-db   - Sync/Initialize graph schema from SCHEMA.cypher"
        echo "  pe-bands  - Manage PE bands configuration (ls)"
        echo ""
        echo "Use 'irm <command> --help' for more information on a specific command."
        ;;
esac
