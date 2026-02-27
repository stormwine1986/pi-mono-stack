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
    init-db)
        python3 /app/scripts/ontology/sync_schema.py "$@"
        ;;
    help|*)
        echo "IRM (Investment Risk Management) CLI"
        echo "Usage: irm <command> [options]"
        echo ""
        echo "Available Commands:"
        echo "  tracer   - Trace macro-to-micro impact propagation"
        echo "  advisor  - Get Kelly-based portfolio allocation advice"
        echo "  init-db  - Sync/Initialize graph schema from SCHEMA.cypher"
        echo ""
        echo "Use 'irm <command> --help' for more information on a specific command."
        ;;
esac
