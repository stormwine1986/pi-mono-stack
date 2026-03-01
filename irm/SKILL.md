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
- **三位一体自动化管道**: 对接外部供应商（OpenBB/FRED），同步资产价格、物理估值 (P/E) 与盈利预期，并自动执行复合风险水位推演。
- **混合配置驱动**: 核心图谱定义逻辑，Redis 负责实时维护外部数据源 (`sources`) 的映射关系。
- **凯利公式仓位优化**: 根据图谱追踪得出的影响分值，自动修正贝叶斯胜率并给出量化调仓建议。

## 使用方法

所有操作均通过 Docker 容器内的 `irm` CLI 执行。**禁止**使用 `docker exec irm irm init-db` 命令初始化数据库。**禁止**直接读取 cypher 文件。

### 1. 数据来源管理
管理用于实时数据采集的 Ticker 与供应商 Symbol 映射关系：
```bash
# 查看当前纳管的所有数据源映射
docker exec irm irm sources ls

# 更新或新增一个数据源（支持 yfinance 和 fred）
docker exec irm irm sources update <ticker> <symbol> <provider>
```
*注：PE/EPS 的经验带 (Bands) 现在直接通过图维护命令或 Cypher 语句更新。*

### 2. 追踪市场冲击
模拟宏观节点受到的冲击，并查看其对投资组合的涟漪效应。系统会自动激活边上的复合风险水位逻辑。
```bash
# 示例：美债 10 年期收益率上升 0.5 (相对 Delta)
docker exec irm irm tracer --ticker "US10Y" --delta 0.5 --owner Admin
```

### 3. 图谱探索与审计
```bash
# 查看图谱节点状态 (已优化对齐：包含物理值 VAL、分位点 PCT、经验带 BANDS)
docker exec irm irm graph nodes

# 查看图谱边参数 (Beta、ID、非线性配置 JSON)
docker exec irm irm graph edges

# 查看持仓组合详情 (权益占比、市值分布)
docker exec irm irm portfolio --owner Admin
```

### 4. 数据维护与同步
```bash
# 执行全量数据与配置恢复 (从 .irm 目录下的备份加载)
docker exec irm irm restore

# 备份当前活跃图谱及配置至容器外持久化目录
docker exec irm irm backup
```

### 5. 获取调仓建议
```bash
# 基于传导影响分值与当前仓位，获取经过凯利公式优化后的配置建议
docker exec irm irm advisor --impacts '{"QQQM": -61.38, "NVDA": -81.66}' --weights '{"QQQM": 0.35, "NVDA": 0.25}' --fraction 0.5
```