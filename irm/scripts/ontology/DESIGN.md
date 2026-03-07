# 知识图谱与本体数据结构设计 (Ontology Design)

## 1. 核心架构：知识图谱层 (本体定义与技术规范)

本体层定义了市场运行的“物理法则”与基本盘。设计上遵循**“逻辑与物理分离 (Logic-Physical Decoupling)”**的原则：节点仅存储客观事实（价格、水位、元数据），而复杂的传导规律、非线性阶跃阈值则通过“边”上的配置属性承载。

### 1.1 核心实体节点 (Node Types)

| 分类 | 标签 (Labels) | 业务角色与定义 | 核心技术属性 (Properties) |
| :--- | :--- | :--- | :--- |
| **宏观基准** | `Asset:Macro` | **宏观锚点与定价源头**。包含 `InterestRate` (利率)、`Currency` (货币/汇率)、`Volatility` (波动率) 等。此类节点不可直接投资，不适用凯利公式参数。 | `ticker` (唯一标识), `value`, `percentile` (水位), `metric_type` |
| **可交易标的** | `Asset:Investable` | **终端投资资产**。如 `Stock`, `EquityETF`, `Commodity`, `Crypto`。这是组合持仓的实体，承载凯利理论的基本面先验假设。 | 继承 `Asset` 属性，新增 `base_win_rate`, `expected_upside`, `expected_max_dd` (用于凯利计算)。 |
| **结构聚合** | `Sector` / `Theme` | **行业与主题概念**。用于归拢同质化风险或捕捉特定叙事（如 AI 基础设施）产生的共振。 | `name` (英文标识), `name_cn` (中文定性) |
| **定价枢纽** | `Hub:Valuation` / `Earnings` | **宏微观翻译器 (Translators)** ★。负责吸收宏观冲击并翻译为资产估值或盈利预期的变动。 | `target` (关联Ticker), `pe_min`/`pe_max` (PE经验带), `eps_min`/`eps_max` (盈利增速带), `percentile` (水位) |
| **账户终端** | `Portfolio` | **系统决策终点**。代表用户的资金分布与持股逻辑，是所有风控建议下发的锚点。 | `owner` (所属权), `name` (组合名), `total_value` (总净值/NAV, 以本位币计价), `currency` (本位币/Base Currency, 换算基准) |
| **虚拟代理** | `Event` | **传导第一推动力**。由 LLM 解析新闻后生成的非持久化实时节点，作为冲击计算的入口。 | `delta_pct` (初始Delta), `event_logic` (事件成因) |

### 1.2 核心传导边 (Edge Types)

图谱中所有的边均包含 `id` (nanoID 唯一标识) 和 `logic` (业务逻辑描述，供 LLM 提取并生成诊断报告)。

| 关系类型 | 业务语义 | 核心属性与计算逻辑 |
| :--- | :--- | :--- |
| `[:DRIVES]` | **宏观驱动** | 描绘因果链条（如：油价推高通胀预期）。 |
| `[:SPILLS_TO]` | **风险溢出** | 描述跨市场恐慌传染（如：债市震荡引发股市 VIX 飙升）。 |
| `[:PRICES]` | **定价压制** ★ | **核心算力通道**。承载 `base_beta` (基准敏感度) 与 `threshold_config` (非线性阶跃 JSON)。 |
| `[:CORRELATES_WITH]` | **资产相关性** | 描述具有强正/负相关的资产联动关系，用于计算避险或溢出。 |
| `[:HEAVILY_EXPOSED_TO]` | **重度暴露** | 描述资产对特定行业或风险因素（如 AI 基础设施）的非对称暴露。 |
| `[:DETERMINES]` | **价值决定** | 限定于 `Hub` → `Asset` 方向。承载 $P = PE \times EPS$ 的决定逻辑。 |
| `[:BELONGS_TO]` / `[:COMPOSES]` / `[:TRACKS]` | **结构归属** | 定义行业归属、成分占比或指数追踪关系。携带 `composition_weight` 属性。 |
| `[:HOLDS]` | **仓位触达** ★ | **实时联动边**。承载 `weight_pct` (全局权重), `denomination` (计价币种)。与之关联的物理账本(股数/成本/币种)存储在 Redis 中。 |

---

## 2. 工程实现说明

> [!tip] 图谱更新机制：静态结构与动态权重的分离
> - **结构层 (低频/静态)**：本体拓扑描述的是金融市场的“逻辑物理法则”（如航司依赖燃油），结构极其稳定，无需高频更新。
> - **参数层 (中高频/动态)**：节点状态（分位数）和边的权重（Beta）由自动化管道从数据源同步。分析引擎推理前，只需基于“当前水位”完成**动态赋权 (Dynamic Modifier)** 即可得出非线性结论。

> [!tip] 多币种计价槽位 (Denomination Slot) 设计
> - **计价分离原则**：`[:HOLDS]` 边的 `denomination` 属性标注每个持仓的计价货币(如 USD/CNY/JPY)，权重在各自币域内独立计算后换算为总 `weight_pct`。
> - **Redis 物理账本**：`irm:portfolio:{owner}:holdings:{ticker}` 的 Hash 中包含 `shares`/`avg_cost`/`denomination` 三个字段。

---

## 3. 核心边引擎机制 (JSON Payload Schema)

可以通过编写一个 JSON Schema 来优雅地结构化这种多维度边：

```json
{
  "source": "US10Y",
  "target": "PE_NVDA",
  "edge_attributes": {
    "id": "Vy_777P_YmE9V7VG76u5f",
    "base_beta": -1.8,
    "modifier_metric": "target_percentile",  // 引擎指令：读取目标节点的水位分位
    "state_trigger": "percentile_amplifier", // 语义化标签
    "threshold_config": [                    // 引擎实际执行的“纯数字化规则”
      {"min": 0.95, "max": 1.0, "mu": 4.0},  // 极值崩塌区：4倍放大
      {"min": 0.85, "max": 0.95, "mu": 2.0}, // 风险预警区：2倍放大
      {"min": 0.0,  "max": 0.85, "mu": 1.0}  // 常规区间：常态传导
    ],
    "gamma_sensitive": true,                 // 是否受全局恐慌情绪(VIX)加持
    "logic": "极高贴现率重创超高估值AI远期现金流"
  }
}
```
