from falkordb import FalkorDB
import os
from urllib.parse import urlparse

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
parsed = urlparse(redis_url)
host = parsed.hostname or "localhost"
port = parsed.port or 6379

db = FalkorDB(host=host, port=port)
graph = db.select_graph('Graph-001')

print("1. Injecting :Investable label to tradeable asset categories...")
# Stock, EquityETF, Crypto, Commodity are investable.
graph.query("""
MATCH (a:Asset)
WHERE 'Stock' in labels(a) OR 'EquityETF' in labels(a) OR 'Crypto' in labels(a) OR 'Commodity' in labels(a)
SET a:Investable
""")

print("2. Providing default safety Kelly Assumptions to all :Investable nodes...")
graph.query("""
MATCH (a:Investable)
SET a.base_win_rate = 0.55, 
    a.expected_upside = 0.30, 
    a.expected_max_dd = 0.20
""")

print("3. Overriding specific high-conviction assets with custom assumptions...")
assumptions = {
    # 纳指/宽基 ETF: 胜率降至更可持续的水平，1:1 的赔率比符合宽基特征。
    "QQQM": {"base_win_rate": 0.58, "upside": 0.25, "max_dd": 0.25}, 
    "VGK":  {"base_win_rate": 0.58, "upside": 0.25, "max_dd": 0.25},
    "BBJP": {"base_win_rate": 0.58, "upside": 0.25, "max_dd": 0.25},

    # 权重科技股: 相比 ETF，个股需增加回撤预期至 30% 以应对中期调整。
    "AAPL": {"base_win_rate": 0.56, "upside": 0.30, "max_dd": 0.30},
    "GOOGL":{"base_win_rate": 0.56, "upside": 0.30, "max_dd": 0.30},

    # 高弹性增长股: 调低胜率，利用高赔率取胜。DD 设为 0.5 是防范戴维斯双杀。
    "NVDA": {"base_win_rate": 0.54, "upside": 0.80, "max_dd": 0.50},
    "PLTR": {"base_win_rate": 0.54, "upside": 0.80, "max_dd": 0.50},

    # 加密货币: 极高的非对称性。DD 设为 0.75 是为了模拟减半周期中的极限回撤。
    "BTC":  {"base_win_rate": 0.52, "upside": 1.50, "max_dd": 0.75},

    # 大宗商品/避险: 保持低波动特征，DD 设为 0.15 比较符合黄金的历史表现。
    "GOLD": {"base_win_rate": 0.55, "upside": 0.20, "max_dd": 0.15},

    # 周期性商品: 原油波动极不稳定，建议降低胜率并调高回撤容忍度。
    "UKOIL":{"base_win_rate": 0.52, "upside": 0.40, "max_dd": 0.35},

    # 防御性公用事业: 胜率最高，但 Up 设低。适合作为底仓，赔率比控制在 1:1。
    "UTES": {"base_win_rate": 0.60, "upside": 0.15, "max_dd": 0.15},
}

for ticker, data in assumptions.items():
    cypher = f"""MATCH (a:Investable {{ticker: '{ticker}'}}) 
                 SET a.base_win_rate = {data['base_win_rate']}, 
                     a.expected_upside = {data['upside']}, 
                     a.expected_max_dd = {data['max_dd']}"""
    graph.query(cypher)

print("4. Verifying Investable nodes...")
res = graph.query("MATCH (a:Investable) RETURN a.ticker, a.base_win_rate, a.expected_upside, a.expected_max_dd")
for row in res.result_set:
    print(f"{row[0]:<6} | WinRate: {row[1]:.2f} | Upside: {row[2]:.2f} | MaxDD: {row[3]:.2f}")

print("\n[+] Migration completed successfully.")
