#!/bin/bash

# IRM CLI Entrypoint
# Usage: irm <command> [args]

COMMAND=$1
shift

case "$COMMAND" in
    tracer)
        python3 /app/scripts/ontology/tracer.py "$@"
        ;;

    portfolio)
        SUBCOMMAND=$1
        shift
        case "$SUBCOMMAND" in
            update)
                python3 /app/scripts/analyzer/portfolio_manager.py update "$@"
                ;;
            advisor)
                python3 /app/scripts/analyzer/portfolio_advisor.py "$@"
                ;;
            list|ls|*)
                python3 /app/scripts/analyzer/portfolio_manager.py list "$@"
                ;;
        esac
        ;;

    graph)
        SUBCOMMAND=$1
        shift
        case "$SUBCOMMAND" in
            nodes)
                python3 /app/scripts/analyzer/node_viewer.py "$@"
                ;;
            edges)
                python3 /app/scripts/analyzer/edge_viewer.py "$@"
                ;;
            *)
                echo "Unknown graph command: $SUBCOMMAND"
                echo "Usage: irm graph {nodes|edges}"
                ;;
        esac
        ;;

    sources)
        python3 /app/scripts/analyzer/config_manager.py sources "$@"
        ;;
    backup)
        python3 /app/scripts/ontology/export_cypher.py "$@"
        ;;
    store|restore)
        echo "[*] Restoring Ontology from EXPORTED_SCHEMA.cypher..."
        python3 /app/scripts/ontology/sync_schema.py --schema /home/pi-mono/.pi/agent/workspace/.irm/EXPORTED_SCHEMA.cypher
        echo "[*] Restoring Configurations from EXPORTED_CONFIG.sh..."
        
        bash /home/pi-mono/.pi/agent/workspace/.irm/EXPORTED_CONFIG.sh
        echo "[+] Restore complete."
        ;;
    help|*)
        echo "IRM (Investment Risk Management) CLI"
        echo "Usage: irm <command> [options]"
        echo ""
        echo "Available Commands:"
        echo "  tracer    - Trace macro-to-micro impact propagation"
        echo "  portfolio list   - List asset allocation status for a specified owner"
        echo "  portfolio update - Update a specific holding (e.g. irm portfolio update NVDA 300 850)"
        echo "  portfolio advisor - Get Kelly-based allocation advice (requires impacts/weights)"

        echo "  graph     - Graph operations (nodes, edges)"
 
        echo "  backup    - Export live Ontology data and Configs to .irm directory"
        echo "  store     - Restore data and configs from EXPORTED backups in .irm"
        echo "  sources   - Manage data sources configuration (ls, update)"
        echo ""
        echo "Use 'irm <command> --help' for more information on a specific command."
        ;;
esac
