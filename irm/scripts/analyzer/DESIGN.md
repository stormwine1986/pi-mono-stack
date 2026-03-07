# 传导推演引擎与凯利公式决策器 (Analyzer Design)

## 1. 推理计算层 (影响分析引擎)

当一个 **事件 (Event)** 发生时，引擎在图谱上进行穿透式的风险计算。

### 1.1 传导机制说明

*   **一阶影响 (First-Order Impact)**: 事件直接作用于关联的首层节点。示例：**中东冲突** $\to$ `Oil` (+10%)。
*   **二阶影响 (Second-Order Impact)**: 首层节点的变动，沿着本体链条向次级节点传导（微分链条）。示例：`Oil` $\to$ `Airline_Sector` (成本) $\to$ `DAL` (估值)。
*   **计算模型**: 使用图遍历算法（BFS/DFS），结合路径衰减因子（Decay Factor）计算累积风险暴露。

### 1.2 解构资产价格与戴维斯双杀诊断 (Davis Double Play/Kill)

系统的定价公式基于 $P = EPS \times PE$ 构建。宏观与微观冲击被 PE 和 EPS 两个独立枢纽进行精准吸收与翻译。

*   **“杀估值”(纯流动性枯竭)**: 探测到伤害全由 PE 枢纽承接，若 `erp_percentile` 跌至历史低位，触发非线性崩塌报警。
*   **“杀业绩”(基本面恶化)**: 由于大宗飙升或汇率恶化引发的 EPS 枢纽下调，剥离情绪面干扰。
*   **“戴维斯双杀”(共振必杀)**: 算力引擎将在节点得出非线性极高的负面冲击值，向交易员强降风险准备金与警告。

---

## 2. 传导公式与参数设计 (Transmission Formula)

### 2.1 核心变量定义

$$Impact(B) = \Delta A \times \Big( \beta \times \mu(A_{state}) \times \gamma(Market_{vol}) \Big) \times D^{n}$$

| 变量 | 物理意义与计算来源 |
| :--- | :--- |
| **Base Beta ($\beta$)** | 历史线性敏感度，决定基础方向与大力度。来自 OLS 回归。 |
| **State Modifier ($\mu$)** | 基于**当前水位 (Percentile)** 的非线性放大器。实现“极位指数放大”、“安全边际钝化”或“阈值断路器”模式。 |
| **Volatility Accer ($\gamma$)** | 全局恐慌加速器。当 $VIX > 30$ 时，坏消息破坏力加倍。 |
| **Distance Decay ($D^n$)** | 距离衰减因子。由于信息耗散与确定性折价，$D$ 取 0.6-0.85，随跳数 $n$ 幂次递减。 |

### 2.2 防限流与阈值截断 (Threshold Truncation)

在代码层面，设定：**当 $Impact \times D^n$ 的绝对值小于 0.01 时，遍历终止 (Pruning)**。其业务含义是“市场已经彻底钝化，该末端影响可忽略不计”。

---

## 3. 仓位管理与决策输出 (Portfolio Decision)

将推演波动映射至用户当前的 **Portfolio（持仓组合）**。

### 3.1 动态凯利公式 (Dynamic Kelly Criterion)

传统的凯利公式 $f^* = \frac{bp - q}{b}$。在 IRM 中，**图谱推演的 Impact Score 会直接实时修正参数**:

*   **胜率 ($p$) 惩罚**: 某资产承受高负向冲击分值时，系统判定胜率显著下降，从而导致 $f^*$ 指数级向 0 线收拢。
*   **仓位建议**: 通过凯利计算得出极其精确的量化指令（如：建议将仓位从 15% 降至 0% 即清仓）。

### 3.2 长短期的凯利应用 (Time Horizon)

*   **贝叶斯概率 (Bayesian Probability)**: 长期投资侧重于资产在生态位中的复利能力确信度。
*   **部分凯利 (Fractional Kelly)**: 长期资金引入“半凯利 (Half-Kelly)”或更低比例，以提升夏普比率，保证账户生存。
*   **基础资产假设 (Base Assumptions)**: 为每个资产设定 `base_win_rate`, `upside`, `max_dd` 作为先验输入。
