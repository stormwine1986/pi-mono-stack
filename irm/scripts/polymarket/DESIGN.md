# 事件预言机与预测市场模块 (Polymarket Design)

## 1. 模块定位

PMK (Polymarket) 模块的作用是**将外部事件的真实确信度数字化**。
传统的 IRM 模型依赖于分析师的主观 Delta 输入，而 PMK 模块直接从预测市场（Prediction Markets）提取数据。

*   **真金白银的胜率 (Real-money Odds)**：通过 Polymarket 的订单簿数据，获取某个事件（如：2024 美国大选、美联储下次加息概率、中东各冲突结局）的可操作概率。
*   **作为图谱“第一推动力”**：PMK 的价格变动被转化为图谱中 `Event` 节点的 `delta_pct`（初始扰动值），从而启动整个 IRM 分析链条。

---

## 2. 工程实现：Gamma API 接入

目前的 `cli.py` 脚本负责对接 Polymarket 的公有 API。

### 2.1 搜索与过滤逻辑

*   **`search` 命令**：解析自然语言关键词（如："Bitcoin", "Election"），返回活跃的且未关闭的预测市场。
*   **字段过滤 (DEFAULT_FIELDS)**：仅提取 `question`, `outcomePrices`, `volume`, `liquidity` 等核心特征。

### 2.2 概率转换方法 (Odds-to-Delta)

系统将 Polymarket 的结果（如：某个 Outcome 的 Price 为 0.65，即 65% 的概率）映射为 `Event` 节点的属性：
*   **基准对比 (Base Comparison)**：将当前价格与过去 24 小时均值对比，计算出对应的“震惊值 ($\Delta A$)”。
*   **流动性校验 (Liquidity Check)**：若市场的 Liquidity 低于 10,000 USD，则忽略该事件信号，防止由于散户对赌导致模型失效。

---

## 3. 角色演进

未来，该模块将不仅是一个查询工具，而是一个**自动化事件感知器 (Automated Event Recognizer)**。

1.  **定期巡检 (Scanning)**：定期扫描与系统核心资产（如：BTC, QQQM）强相关的预测市场。
2.  **自动预警 (Auto-Warning)**：当某个事件概率在 1 小时内波动超过 15%，系统自动将其 Grounding 到图谱的物理节点，并触发 `tracer.py` 进行全局风险扫描。
