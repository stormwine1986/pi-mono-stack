---
name: "irm"
description: "基于本体知识图谱的投资风险管理 (IRM) 模块。用于宏观到微观的影响传导分析、非线性风险评估以及基于凯利公式的仓位优化。"
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

在执行 `graph nodes --label <LABEL>` 时，可使用以下核心标签进行过滤：

| 标签 | 定义与用途 |
| :--- | :--- |
| **`Investable`** | **最常用**。所有可交易并承载凯利先验假设的资产 (Stock, ETF, Crypto 等)。 |
| `Asset` | 所有图谱实体的根标签（包含宏观指标与微观资产）。 |
| `Macro` | 宏观锚点标签（涵盖 InterestRate, Currency, Volatility）。 |
| `Stock` | 具体上市公司股票。 |
| `EquityETF` | 权益类 ETF。 |
| `Crypto` | 数字加密货币。 |
| `Commodity` | 大宗商品实物或其价格代号。 |
| `Sector` / `Theme` | 行业聚合节点与投资主题节点。 |
| `Hub:Valuation` | 估值中枢节点（承载 PE 逻辑）。 |
| `Hub:Earnings` | 盈利预期节点（承载 EPS 逻辑）。 |


## 使用方法

所有操作均通过 Docker 容器内的 `irm` CLI 执行。

### 1. 资产与数据源管理
管理数据源映射关系，确保价格同步正常。
```bash
# 查看当前纳管的所有数据源映射 (yfinance/fred)
docker exec irm irm sources ls

# 更新或新增一个数据源
docker exec irm irm sources update <ticker> <symbol> <provider>
```

### 2. 持仓账本维护 (Portfolio Management)
管理真实的交易持仓。系统会自动维护 Redis 账本并同步更新图谱中的边拓扑。
```bash
# 查看持仓状态 (已优化中英文字符对齐，实时计算市值与权重)
docker exec irm irm portfolio list

# 更新持仓（全自动触发权重重算与拓扑维护）
# 示例：更新 NVDA 为 400 股，单价 900
docker exec irm irm portfolio update NVDA 400 900

# 清仓：将股数设为 0 即可自动删除 Redis 账本及图谱对应的持仓边
docker exec irm irm portfolio update GOLD 0 0
```

### 3. 风险追踪与决策
```bash
# 追踪冲击：模拟源头波动对组合的连锁反应
# --delta 数值含义：
# 1. 价格类资产 (Asset:Stock/Crypto): 传统的百分比变动 (e.g. 5 代表上涨 5%)
# 2. 利率/指标类 (Macro:InterestRate/Volatility): 对当前绝对值的百分比缩放 (e.g. 当前利率 4.0, delta 10 代表变动 4.0 * 10% = +0.4)
docker exec irm irm tracer --ticker "US10Y" --delta 0.5

# 获取调仓建议：通过凯利公式自动结合“当前图谱权重”评估冲击后的最优配置
docker exec irm irm portfolio advisor --impacts '{"QQQM": -5, "NVDA": 10}'
```

### 4. 图谱审计与可视化 (Graph Auditing)
查看当前本体图谱的节点属性、风险参数及传导逻辑配置。

```bash
# 查看全局节点及其关键属性（估值带、凯利参数等）
docker exec irm irm graph nodes

# 仅查看可投资标的资产 (Investable) 及其凯利先验假设
docker exec irm irm graph nodes --label Investable

# 仅查看定价枢纽节点 (Hub)
docker exec irm irm graph nodes --label Hub

# 查看边配置与传导逻辑 (Beta, 非线性阶跃阈值, 逻辑说明)
docker exec irm irm graph edges
```

### 5. 系统备份与恢复 (Maintenance)
涵盖图谱拓扑、边逻辑及 Redis 中的动态持仓账本。
```bash
docker exec irm irm backup
docker exec irm irm restore
```

**禁止使用 `irm restore` 命令重置数据库**