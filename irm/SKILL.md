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
- **混合数据持久化**: 
    - **FalkorDB**: 存储拓扑结构、风险逻辑、经验区间。
    - **Redis**: 存储数据源配置及动态交易账本（持仓股数与成本）。
- **凯利公式仓位优化**: 实时抓取图谱权重，结合追踪的影响分值，自动给出调仓、减持或清仓建议。

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
# 追踪冲击：模拟 US10Y 变动 0.5 后的涟漪效应
docker exec irm irm tracer --ticker "US10Y" --delta 0.5

# 获取调仓建议：通过凯利公式自动结合“当前图谱权重”评估冲击后的最优配置
# 仅需输入影响得分，无需手动输入权重
docker exec irm irm portfolio advisor --impacts '{"QQQM": -5, "NVDA": 10}'
```

### 4. 数据同步与备份
```bash
# 自动同步管道（执行价格更新、百分位重算、并联动刷新持仓权重）
docker exec irm irm update-price-signals

# 图谱审计
docker exec irm irm graph nodes  # 查看节点属性
docker exec irm irm graph edges  # 查看边配置

# 系统备份与恢复 (涵盖图谱拓扑与 Redis 动态账本)
docker exec irm irm backup
docker exec irm irm restore
```

## 注意事项
- **权重联动**：所有的权重 (`weight_pct`) 均由系统在价格更新或账本修改时自动重算。
- **数据一致性**：`irm backup` 会将动态持仓序列化为 Bash 指令，恢复时可确保 Redis 与图谱状态同步。