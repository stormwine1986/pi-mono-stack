---
name: "irm"
description: "基于本体知识图谱的投资风险管理 (IRM) 模块。用于宏观到微观的影响传导分析、非线性风险评估以及基于凯利公式的仓位优化。"
---

# 本体论风控 (IRM) 技能

本技能采用 **神经符号 (Neuro-Symbolic)** 架构处理金融风险：利用知识图谱 (FalkorDB) 建模市场因果律，并结合 Python 算法引擎计算风险的非线性传导。

## 核心能力

- **本体路径追踪**: 追踪宏观冲击（利率、原油、波动率）如何穿透行业和基本面枢纽（PE/EPS），最终影响具体资产。
- **非线性状态修饰**: 利用 JSON 驱动的 `threshold_config` 配置，计算极值环境下的风险放大或吸收效应。
- **配置管理**: 管理存储在 Redis 中的经验区间（PE/EPS Bands）和数据源映射。
- **自动化数据管道**: 将实时价格、估值 (PE) 和盈利预期 (EPS Growth) 从外部供应商同步至知识图谱。
- **组合与节点探索**: 通过 CLI 直接探索图谱实体，并审计实时的资产配置状态。
- **凯利公式仓位优化**: 根据图谱追踪得出的影响分值，自动修正贝叶斯胜率并给出调仓建议。

## 使用方法

所有操作均通过 Docker 容器内的 `irm` CLI 执行。**禁止**使用 `docker exec irm irm init-db` 命令初始化数据库。**禁止**直接读取cyper文件。

### 1. 配置与区间 (Bands) 管理
管理用于分位数映射的经验区间和数据源：
```bash
# 查看或更新 PE 经验带
docker exec irm irm pe-bands ls
docker exec irm irm pe-bands update <ticker> <min> <max>

# 查看或更新 EPS 增长经验带
docker exec irm irm eps-bands ls
docker exec irm irm eps-bands update <ticker> <min> <max>

# 查看或更新数据源映射
docker exec irm irm sources ls
docker exec irm irm sources update <ticker> <symbol> <provider>
```

### 2. 追踪市场冲击
模拟宏观节点受到的冲击，并查看其对投资组合的涟漪效应：
```bash
# 示例：美债 10 年期收益率上升 0.5 (相对 Delta)
docker exec irm irm tracer --ticker "US10Y" --delta 0.5 --owner Admin
```

### 3. 图谱探索与审计
```bash
# 查看图谱节点状态 (实体、枢纽、分位点)
docker exec irm irm graph nodes

# 查看图谱边参数 (Beta、ID、非线性配置)
docker exec irm irm graph edges

# 查看持仓组合详情
docker exec irm irm portfolio --owner Admin
```

### 4. 数据备份与同步
```bash
# 执行全量数据与配置恢复 (从 .irm 目录下的 EXPORTED 文件载入)
docker exec irm irm restore

# 备份当前图谱数据与配置
docker exec irm irm backup
```

### 5. 获取调仓建议
```bash
# 基于传导影响获取调仓建议
docker exec irm irm advisor --impacts '{"QQQM": -61.38, "NVDA": -81.66}' --weights '{"QQQM": 0.35, "NVDA": 0.25}' --fraction 0.5
```