---
name: "irm"
description: "基于本体知识图谱的投资风险管理 (IRM) 模块。用于宏观到微观的影响传导分析、非线性风险评估、基于凯利公式的仓位优化、实时数据源查询，以及集成 Polymarket 预测市场搜索。"
---

# 本体论风控 (IRM) 技能

本技能采用 **神经符号 (Neuro-Symbolic)** 架构处理金融风险：利用知识图谱 (FalkorDB) 建模市场因果律，并结合 Python 算法引擎计算风险的非线性传导。

## 核心能力

- **本体路径追踪**: 追踪宏观冲击（利率、原油、波动率）如何穿透行业和基本面枢纽（PE/EPS），最终影响具体资产。
- **非线性状态修饰**: 利用 JSON 驱动的 `threshold_config` 配置，计算极值环境下的风险放大或吸收效应。
- **自描述知识管理**: 经验区间（PE/EPS Bands）直接作为属性存储在图节点中，使本体图能独立描述自身的风险边界。
- **自动一体化权重更新**: 将 Redis 账本（股数）与 FalkorDB（实时报价）解耦，动态计算并同步全量持仓权重。
- **混合数据持久化与知识沉淀**: 
    - **FalkorDB**: 存储拓扑结构、风险逻辑、经验区间。资产的**凯利先验假设**（胜率、预期回报、最大回撤）已下沉至 `:Investable` 节点属性，实现知识长效化。
    - **Redis**: 存储数据源配置及动态交易账本（持仓股数与成本）。
- **凯利公式决策引擎**: 实时从图谱中抓取资产权重及其内生的胜率/赔率参数，结合追踪的影响分值，自动给出精准的调仓、减持或清仓建议。

## 图谱标签手册 (Label Reference)

> [!IMPORTANT] **标签叠加原则 (Label Stacking)**
> 系统采用“基类+业务类”的复合标签方案。对于所有**作为行情追踪对象的市场标的（如各类股票、指数、宏观指标等）**，**必须保留 `:Asset` 标签**作为基类。它是数据同步管道和传导引擎识别目标的唯一物理抓手，严禁为此类资产建立孤立的业务标签。而结构整合/算力中枢类节点（如 `Sector`, `Hub`, `Portfolio`）则属于独立的非行情实体，**不使用** `:Asset` 标签。

在执行 `graph nodes --label <LABEL>` 时，可使用以下核心标签进行过滤：

| 标签 | 核心属性 (Properties) | 定义与用途 (及组合要求) |
| :--- | :--- | :--- |
| **`Investable`** | `base_win_rate`, `expected_upside`, `expected_max_dd` | **最常用**。所有承载凯利先验假设的可交易资产。必须组合 `:Asset` 使用。 |
| `Asset` | `ticker`, `name`, `name_cn`, `value`, `percentile` | **系统根标签**。所有涉及价格/水位同步的节点必须包含此标签。 |
| `Macro` | `ticker`, `value`, `percentile`, `metric_type` | **宏观锚点**。涵盖利率/汇率/波动率。必须组合 `:Asset` 使用。 |
| `Stock` | `ticker`, `name`, `sector`, `industry` | 具体上市公司股票。必须组合 `:Asset:Investable`。 |
| `EquityETF` | `ticker`, `name`, `index_tracked` | 权益类 ETF。必须组合 `:Asset:Investable`。 |
| `Crypto` | `ticker`, `name` | 数字加密货币。必须组合 `:Asset:Investable`。 |
| `Commodity` | `ticker`, `name` | 大宗商品实物或其价格代号。通常组合 `:Asset:Investable`。 |
| `Sector` / `Theme` | `name`, `name_cn` | 行业聚合节点与投资主题节点。用于归拢共振风险。 |
| `Hub:Valuation` | `target`, `pe_min`, `pe_max`, `percentile` | 估值中枢节点（推演 PE 逻辑）。负责跨层级翻译冲击。 |
| `Hub:Earnings` | `target`, `eps_min`, `eps_max`, `percentile` | 盈利预期节点（推演 EPS 逻辑）。负责跨层级翻译冲击。 |
| `Portfolio` | `owner`, `name`, `total_value`, `currency` | 账户终端。存储折算后的本位币总 NAV 与资产分布锚点。 |

## 图谱关系手册 (Edge Types)

| 关系类型 | 业务语义 | 计算特征 |
| :--- | :--- | :--- |
| **`DRIVES`** | **因果驱动** | 核心传导路径（例：油价 -> 通胀 -> 利率）。受距离衰减影响。 |
| **`PRICES`** | **定价压制** | 典型的估值挤压或业绩拖累。承载非线性 `threshold_config`。 |
| **`SPILLS_TO`**| **风险溢出** | 跨品种关联（例：垃圾债震荡 -> 恐慌指数 VIX）。 |
| **`DETERMINES`**| **价值决定** | 限定于 `Hub -> Asset`。遵循会计恒等式，$P = PE \times EPS$，**无距离衰减**。 |
| **`COMPOSES`** | **成分构成** | 定义指数/组合的物理构成。承载权重基准，**无距离衰减**。 |
| **`TRACKS`** | **模拟追踪** | ETF 对底层指数的追踪转换（Proxy）。**无距离衰减**。 |
| **`HOLDS`** | **账户持仓** | **系统保留边**。仅存在于 `Portfolio -> Asset`，映射 Redis 实时账本。 |
| `HEAVILY_EXPOSED_TO` | 重度暴露 | 标记对特定行业或叙事因子的敏感性。 |
| `CORRELATES_WITH` | 资产相关性 | 描述资产间的联动性，通常由 `calc_betas.py` 自动计算。 |


## 使用方法

所有操作均通过 Docker 容器内的 `irm` CLI 执行。

### 1. 资产与数据源管理
管理数据源映射关系，确保价格同步正常。
```bash
# 查看当前纳管的所有数据源映射 (yfinance/fred)
docker exec irm irm sources ls

# 更新或新增一个数据源
docker exec irm irm sources update <ticker> <symbol> <provider> [--name "中文显示名称"]

# 获取最新数值 (例如查询 QQQM)
docker exec irm irm sources query QQQM
```

### 2. 持仓账本维护 (Portfolio Management)
管理真实的交易持仓。系统会自动维护 Redis 账本并同步更新图谱中的边拓扑。
```bash
# 查看持仓状态 (已优化中英文字符对齐，实时计算市值与权重)
docker exec irm irm portfolio list

# 更新持仓（全自动触发权重重算与拓扑维护）
# 示例：更新 NVDA 为 400 股，单价 900（支持 --denom 切换计价币种）
docker exec irm irm portfolio update NVDA 400 900 --denom USD

# 清仓：将股数设为 0 即可自动删除 Redis 账本及图谱对应的持仓边
docker exec irm irm portfolio update GOLD 0 0
```

### 3. 风险追踪与决策
```bash
# 追踪冲击：模拟源头波动对组合的连锁反应
# --delta 数值含义：系统会自动识别指标类型 (rate/volatility) 并进行单位转换。
# 示例：原油上涨 50% 并在图中推演对 VIX 的溢出影响 (VIX 自动更新 Gamma 系数)
docker exec irm irm tracer --ticker UKOIL --delta 50

# 手动指定恐慌情绪：使用 --vix 参数覆盖图谱预测，强制以特定 VIX 水位计算 Gamma 加速
docker exec irm irm tracer --ticker "US10Y" --delta 10 --vix 45

# 精确穿透：查看特定源头对单一目标的传导路径与贡献分值
docker exec irm irm tracer --ticker "US10Y" --delta 5 --target NVDA

# 获取调仓建议：通过凯利公式自动结合“当前图谱权重”评估冲击后的最优配置
docker exec irm irm portfolio advisor --impacts '{"QQQM": -5, "NVDA": 10}'
```

### 4. 预测市场集成 (Polymarket Integration)
访问 Polymarket 预测市场数据，用于辅助判断宏观事件概率或市场情绪。
```bash
# 搜索预测市场 (例如搜索 Bitcoin 相关市场)
docker exec irm irm pmk search "Bitcoin"
```

### 5. 图谱审计与可视化 (Graph Auditing)
查看当前本体图谱的节点属性、风险参数及传导逻辑配置。

```bash
# 查看全局节点及其关键属性（估值带、凯利参数等）
docker exec irm irm graph nodes

# 仅查看可投资标的资产 (Investable) 及其凯利先验假设
docker exec irm irm graph nodes --label Investable

# 查看特定标的的物理属性与分位点
docker exec irm irm graph nodes --ticker QQQM

# 以 JSON 格式打印节点详情 (便于程序解析或深度审计)
docker exec irm irm graph nodes --ticker QQQM --json

# 查看边配置与传导逻辑 (Beta, 非线性阶跃阈值, 逻辑说明)
docker exec irm irm graph edges

# 综合查询：列出与特定节点相关的所有边（不限方向）
docker exec irm irm graph edges --nodeID NVDA

# 追踪因果：列出从特定节点出发的所有传导边
docker exec irm irm graph edges --from UKOIL

# 风险溯源：列出所有指向特定节点的边（查看受哪些因素推升）
docker exec irm irm graph edges --to VIX

# 执行自定义 Cypher 语句查询/修改图谱
docker exec irm irm graph exec "MATCH (n) RETURN COUNT(n)"
```

## 6. 后台自动化任务 (Background Tasks)

系统利用 **Dkron** 管理以下周期性任务，确保图谱数据的时效性与计算精度：

| 任务名称 (Dkron ID) | 执行频率 | 核心作用 |
| :--- | :--- | :--- |
| `irm-update-earnings` | 每日 12:00 | 自动从数据源拉取标的分析师预期收益增长 (Forward Growth)，映射至 `Hub:Earnings` 节点的期望分位点。 |
| `irm-update-percentiles` | 每日 12:00 | 拉取实时 P/E 估值，并结合 ERP (权益风险溢价) 压力计算 `Hub:Valuation` 中枢的复合风险水位。 |
| `irm-update-price-signals` | 每日 12:00 | 同步所有 `:Asset` 价格及 3 年历史分位点，完成后自动触发全量持仓账本的权重重算 (`Portfolio` 维护)。 |
| `irm-calc-betas` | 手动/按需 | 基于 3 年周线历史数据，利用 OLS 线性回归自动更新资产间传导路径的 `base_beta` 系数 (仅更新显著性 p < 0.1 的边)。 |

> [!TIP]
> 任务状态可通过 Dkron 控制面板 (通常在端口 `8080`) 或 IRM 容器日志进行监控。

## 7. 系统备份与恢复 (Maintenance)
涵盖图谱拓扑、边逻辑及 Redis 中的动态持仓账本。
```bash
docker exec irm irm backup
docker exec irm irm restore
```

**禁止使用 `irm restore` 命令重置数据库**