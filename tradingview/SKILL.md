---
name: tradingview
description: Fetch real-time financial market data (stocks, bonds, currencies, commodities) using TradingView data via tvDatafeed. Use when the user asks for real-time data for global markets, key economic indicators (VIX, DXY, yields), or commodities.
---

# TradingView Financial Data Skill

This skill allows you to query financial market data using TradingView's data feed. It supports global stocks, bond yields, currencies, and major commodities.

## Capabilities

- **Global Stocks**: Real-time prices for US and China markets.
- **Economic Indicators**: VIX, DXY, Bond Yields (CN10Y, US10Y, JP10Y).
- **Currencies & Commodities**: Real-time Forex pairs, GOLD, and UKOIL.

## Usage

**IMPORTANT**: This skill executes via a dedicated Docker container named `tradingview`.

### 1. Check Environment

Ensure the `tradingview` container is running:
```bash
docker ps | grep tradingview
```

### 2. Run Query

**General Format:**
```bash
docker exec tradingview python3 /app/scripts/query_market_data.py <EXCHANGE>:<SYMBOL>
```
Example: `CBOE:BBJP`, `SSE:600519`, `NASDAQ:AAPL`, `FX_IDC:USDJPY`.

**Specific Indicators (Simplified):**
The script supports shorthand for common indicators:
```bash
docker exec tradingview python3 /app/scripts/query_market_data.py CN10Y
docker exec tradingview python3 /app/scripts/query_market_data.py US10Y
docker exec tradingview python3 /app/scripts/query_market_data.py VIX
```

**Supported Shortcuts:**
- Bond Yields: `CN10Y`, `US10Y`, `JP10Y`
- Indices: `VIX`, `DXY`
- Commodities: `GOLD`, `UKOIL`
- Forex: `USDJPY`, `EURUSD`, `USDCNY`

### Major Exchanges Codes

| Code | Exchange |
|------|----------|
| **NYSE** | New York Stock Exchange |
| **NASDAQ** | NASDAQ |
| **AMEX** | American Stock Exchange |
| **CBOE** | Chicago Board Options Exchange |
| **SSE** | Shanghai Stock Exchange |

### 3. Interpret Results

The output will be a JSON string. Parse it to answer the user's question.
If the JSON contains an "error" field, report it to the user.
