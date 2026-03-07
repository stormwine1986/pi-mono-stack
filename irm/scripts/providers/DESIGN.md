# 常态数据源与自动化管道设计 (Providers Design)

## 1. 三位一体周期性自动化管道 (The Trinity Update Pipelines)

为了维持本体图谱的“实时生命力”，系统设计了三个独立运行的 Python 数据管道（Cron Jobs），负责将外部物理世界的变动同步到图谱的属性中。

### 1.1 管道功能矩阵 (Pipeline Matrix)

| 管道脚本 | 核心职责 | 更新目标 (Nodes) | 具体更新属性 (Properties) |
| :--- | :--- | :--- | :--- |
| **`update_price_signals.py`** | **市场现状同步** | 所有 `Asset` 及其子类 | `value` (最新价/利率), `percentile` (基于3年历史数据的价格位置分位) |
| **`update_percentiles.py`** | **估值压力更新** | `Hub:Valuation` | `value` (当前 PE 数值), `pe_percentile` (PE 线性映射), `percentile` (综合复合水位) |
| **`update_earnings.py`** | **增长预期同步** | `Hub:Earnings` | `value` (远期 EPS 增长率数值), `percentile` (增长率线性映射) |

### 1.2 核心算法增强：复合风险水位 (Composite Percentile Logic)

在 `Hub:Valuation` 节点中，引入了**复合估值压力逻辑**。确保当估值回落但利率飙升导致性价比丧失时，风险水位依然保持在高位。

*   **计算公式**: $percentile = \max(pe\_percentile, \quad 1.0 - erp\_percentile)$
*   **业务含义**: `percentile` 成为风险开关，无论是因为“价格太贵” (PE) 还是“性价比太低” (1-ERP)，只要有一个满足，资产在推演路径上就处于“极度脆弱”状态，触发非线性 Beta 放大。

---

## 2. 自动化 Beta 提取与回归演进 (Knowledge Discovery)

该管道是系统“自适应能力”的核心，负责定期通过真实交易数据提取资产间的线性敏感度（$\beta$）。

*   **业务逻辑**: 脚本 `calc_betas.py` 通过过去 3 年的历史数据，自动降采样为 **周线 (Weekly)**，通过 OLS 回归捕捉价值真实联动。
*   **数学范式对称**: 根据节点 `metric_type` 自动切换，`Rate` 类型计算基点变动 (diff)，`Price` 类型计算收益率 (pct_change)。
*   **统计显著性防御**: 仅 $P < 0.1$ 的显著路径会被自动更新，否则保留专家先验。

---

## 3. 分布式 Provider 架构

在 `scripts/providers/` 目录下，通过 `BaseProvider` 定义了统一的接口。
*   **`yfinance`**: 主要的资产价格来源。
*   **`fred`**: 宏观利率与经济指标。
*   **`akshare_fund/bond`**: 针对国内公募基金与国债的水位抓取。

所有的物理数据抓取均与图谱同步脚本（`update_*.py`）解耦。
