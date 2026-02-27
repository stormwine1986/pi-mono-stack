---
name: "irm"
description: "Investment Risk Management (IRM) based on Ontological Knowledge Graphs. Use this for macro-to-micro impact propagation, non-linear risk assessment, and Kelly-based portfolio optimization."
---

# Ontological Risk Management (IRM) Skill

This skill leverages a **Neuro-Symbolic** approach to financial risk: using Knowledge Graphs (FalkorDB) to model market causality and Python-based engines to calculate non-linear risk propagation.

## Core Capabilities

- **Ontological Path Tracing**: Trace how macro shocks (Interest Rates, Oil, Volatility) ripple through sectors and fundamental hubs (PE/EPS) to impact specific assets.
- **Non-Linear Amplification**: Calculate extreme scenario impacts using mathematical operators like `percentile_amplifier` and `margin_dampener`.
- **Kelly Portfolio Optimization**: Get position sizing advice based on Bayesian win-rate adjustments derived from real-time graph impacts.
- **Schema Management**: Initialize or evolve the financial ontology directly from the project workspace.

## Usage

All operations are executed via the `irm` CLI within the dedicated Docker container.

### 1. Initialize/Sync Database
Sync the ontology schema from the workspace (`.pi/agent/workspace/.irm/SCHEMA.cypher`) to FalkorDB:
```bash
docker exec irm irm init-db
```

### 2. Trace Market Impacts
Simulate a shock to a macro node and see the ripple effect on your portfolio:
```bash
# Example: US 10-Year Yield rises by 5% (relative) with VIX at 35
docker exec irm irm tracer --ticker US10Y --delta 5 --vix 35
```

### 3. Get Portfolio Advice
Input impact scores and current weights to get Kelly-based trade suggestions:
```bash
# Example: 0.5-Kelly advice for a portfolio
docker exec irm irm advisor --impacts '{"QQQM": -61.38, "NVDA": -81.66}' --weights '{"QQQM": 0.35, "NVDA": 0.25}' --fraction 0.5
```

## Directory Structure (Inside Container)

- `/app/scripts/ontology/tracer.py`: The graph traversal and impact engine.
- `/app/scripts/analyzer/portfolio_advisor.py`: The Kelly-criterion decision module.
- `/home/pi-mono/.pi/agent/workspace/.irm/`: Persistent workspace for schemas and logs.

## Risk Management Principles

1. **Correlation is Not Causality**: Use the Knowledge Graph to identify "hidden" common dependencies that simple correlation matrices miss.
2. **Survival First**: Use fractional Kelly (0.5 or lower) to balance growth with the ability to survive black swan events.
3. **Non-Linearity Matters**: Pay attention to "amplifiers" when assets are at 90th+ percentile valuations; risk is not a straight line.
