# 基于本体论的 IRM 模块核心设计方案

## 1. 设计哲学：从“线性统计”到“拓扑传导”

传统风控侧重于历史波动率（Volatility）和资产间的统计相关性（Correlation matrix）。但当黑天鹅事件发生时，历史相关性往往会失效。
**本体论风控 (Ontological Risk Management)** 的核心假设是：**市场是一个由因果和逻辑链条构成的复杂网络（语义图谱）**。风险并非随机爆发，而是沿着特定的“实体-关系”拓扑结构进行传导的。

---

## 2. 核心架构：三层架构模型

### 2.1 知识图谱层 (本体定义)
本体层定义了市场运行的“物理法则”与基本盘。
*   **节点 (Nodes - 实体与业务角色定义)**
    *   `InterestRate` (利率基准)：市场的“资本成本”锚点。决定了全球折现率的基础，是导致科技股和长久期资产杀估值的核心源头。
    *   `Currency` (货币与流动性)：市场的“购买力与风向标”。美元指数（DXY）反映全球美元流动性紧缩程度，日元等避险/套息货币则反映资本流向。
    *   `Volatility` (风险脉搏)：市场的“恐惧体温计”。VIX（股市）和 MOVE（债市）不直接产生价值，但决定了风险传递的放大倍数（Gamma效应）。
    *   `Commodity` (大宗商品)：实体经济的“成本项与避险端”。原油代表通胀压力，黄金代表对法币信用的对冲。
    *   `Sector` / `Theme` (行业与主题)：市场的“聚合层”。用于识别系统性行业风险或由特定叙事（如AI）引发的共振。
    *   `EquityETF` / `Stock` / `Crypto` (资产终端)：风险传导的“叶子节点”。这是所有计算最终落地的地方，也是计算损益和调整仓位的基本单位。
    *   `Hub` (基本面定价枢纽)：充当“宏微观翻译器” (Macro-to-Micro Translators)。
        *   `PE` (市盈率/估值倍数枢纽)：流动性与风险的天然接收器。负责吸收美国10年期国债收益率（贴现率）和 VIX（风险溢价）的变动。引入 **ERP (股权风险溢价)** 作为核心感知维度，衡量资产相对于无风险利率的安全边际。
        *   `EPS` (每股收益/盈利预期枢纽)：实体经济与商业周期的传导接收器。吸收美元指数（汇兑利润）、大宗商品（成本）以及产业主题（海量订单）带来的冲击，转化为资产实际盈利基准的上调或下调。
    *   `Portfolio` (个人账户)：系统的“终局终端”。代表用户的资金分部、平均成本和当前持仓权重，是所有风控建议的目标。
*   **虚拟代理 (Virtual Proxy)**
    *   `Event` (扰动源)：传导链条的“第一推动力”。它不是图中的持久化物理节点，而是由微观或宏观新闻触发，通过 LLM 解析为虚拟节点后，对图谱内的目标物理节点发起一阶冲击的计算入口点。
*   **边 (Edges - 关系与业务传导含义)**
    *   `DRIVES` (宏观驱动)：描绘金融市场的“第一推动力”（如：油价驱动通胀预期，推高美债收益率信号）。
    *   `SPILLS_TO` (风险溢出)：描述由于市场脆弱性或恐慌导致的跨界传染（如：债市剧震引爆股市 VIX 飙升）。
    *   `PRICES` (定价压制)：宏观或风险因子对定价枢纽（PE/EPS）或具体标的的直接冲击测试路径（携带核心 `base_beta` 与修饰器 `state_trigger`）。
    *   `DETERMINES` (价值决定)：枢纽（Hubs）到底层资产的决定路径。基于基础定价公式 $P=EPS \times PE$，将枢纽的变动翻译为最终资产层面的价格浮动预期。
    *   `BELONGS_TO` / `HEAVILY_EXPOSED_TO` / `TRACKS` (结构归属)：定义资产在物理结构上（行业、指数成分）的静态暴露量。
    *   `DRIVES_THEME` / `PARTICIPATES_IN` (主题叙事)：超越传统行业划分的逻辑共振点（如：AI 主题叙事对相关软硬件的同步推升）。
    *   `CORRELATES_WITH` / `COMPOSES` (相关性补充)：统计学意义上的强联动补丁，用于捕捉无法用因果律直接解释但高度一致的市场行为。
    *   `HOLDS` (持仓触达)：系统决策的终端，将所有传导分值最终映射到用户账户持仓上，驱动凯利公式建议。

> [!tip] 图谱更新机制：静态结构与动态权重的分离
> 图的结构（Topology）不需要高频实时更新，但图的权重（Weights）和节点状态（State）需要阶段性或实时更新。
> - **结构层 (低频/静态)**：描述实体的物理属性与归属（如 Airlines 依赖 Oil），这是市场的“常识”层，结构非常稳定。
> - **状态与参数层 (中高频/动态)**：描述传导的敏感度和放大倍数。例如，“油价上涨打击航司利润”是静态结构，但当前油价是 40美元 还是 120美元（节点实时状态），决定了传导杀伤力的指数级差异。分析引擎在进行遍历推演前，只需拉取一遍最新的宏观水位数据即可完成“动态赋权（Dynamic Modifier）”，无需每秒重构整个高维网络。

### 2.2 推理计算层 (影响分析引擎)

当一个 **事件 (Event)** 发生时，引擎在图谱上进行穿透式的风险计算。

> [!important]
> 传导分析不只是看单个资产，而是看事件的涟漪效应如何渗透到整个投资组合。

#### 一阶影响 (First-Order Impact) - 直接/显性冲击
*   **机制**：事件直接作用于关联的首层节点。
*   **示例**：**中东冲突** $\xrightarrow{+ Impact}$ `Oil` (原油产出受限，价格上涨)。
*   **计算**：基于资产对该事件类型的历史贝塔 (Beta) 或专家规则进行 Delta 调整。

#### 二阶影响 (Second-Order Impact) - 延展/隐性联动
*   **机制**：首层节点的变动，沿着本体链条向次级节点传导。
*   **微观传导示例 (成本驱动)**：`Oil` 飙升 $\xrightarrow{- Impact}$ `Airline_Sector` (燃油成本骤增) $\xrightarrow{- Impact}$ `DAL` (达美航空估值受压)。
*   **宏观传导示例 (利率驱动)**：`Oil` 飙升 $\xrightarrow{+ Impact}$ `Inflation` (通胀反弹预期) $\xrightarrow{+ Impact}$ `US10Y_Yield` (美债收益率攀升) $\xrightarrow{- Impact}$ `Tech_Sector` (科技成长股杀估值)。
*   **计算**：使用图遍历算法（BFS/DFS），结合路径衰减因子（Decay Factor）计算二级、三级甚至四级网络节点的累积风险暴露。

#### 解构资产价格与戴维斯双杀诊断 (Davis Double Play/Kill)
*   **机制**：系统的定价公式基于 $P = EPS \times PE$ 构建，其中 $PE$ 深层受 $1 / (Rf + ERP)$ 驱动。宏观与微观冲击不再是模糊地砸向底层股票，而是被 PE 和 EPS 两个独立枢纽进行精准吸收与翻译。
*   **诊断分析溯源**：
    *   **“杀估值”(纯流动性枯竭)**：当 US10Y 飙升，图算法清晰追溯到伤害全由 PE 枢纽承接。如果探测到 `erp_percentile` 跌至历史低位，将触发非线性崩塌报警。此时定性为：资金性价比丧失，跨资产虹吸效应启动。
    *   **“杀业绩”(基本面恶化)**：由于大宗飙升或汇率恶化引发的 EPS 枢纽下调，剥离了情绪面的干扰。
    *   **“戴维斯双杀”(共振必杀)**：当宏观上的利率飙升（压低 PE & 挤压 ERP）与微观成本/业绩恶化（打压 EPS）同时发生定点共振，算力引擎将在节点得出非线性极高的负面冲击值，向交易员强降风险准备金与警告。

### 2.3 决策与执行层 (仓位管理输出)

分析引擎将图谱的波动映射至用户当前的 **Portfolio（持仓组合）**，并给出调仓反馈：

1.  **风险溯源聚类**：发现看似分散的仓位，实际上暴露在同一个底层节点上（例如组合持有 Tech 股和 Crypto，表面资产不同，但底层都极度依赖“充裕流动性/降息预期”节点）。
2.  **动态凯利公式仓位控制 (Dynamic Kelly Criterion Sizing)**：
    传统的凯利公式 $f^* = \frac{bp - q}{b}$ (其中 $p$ 为胜率, $q$ 为败率, $b$ 为盈亏比) 往往依赖历史静态假设。而在本体论 IRM 中，**图谱传导引擎输出的冲击分值 (Impact Score) 会被用来直接实时修正凯利公式的参数**：
    *   **胜率 ($p$) 惩罚**：如果一个资产（如 DAL）在事件传导中承受了极高的二阶负向冲击分值（如 -18），引擎会判定该资产的当前上涨概率大幅降低，强制下调其凯利公式中的预期胜率 $p$。
    *   **动态缩小仓位 ($f^*$)**：由于 $p$ 被下调，凯利公式计算出的建议仓位比例 $f^*$ 会呈指数级快速收缩。
    *   **结论输出**：系统不会简单地说“这票有风险”，而是通过凯利计算得出“由于油价传导恶化，该标的胜率降至40%以下，**建议将仓位从 15% 强制降至 0%（清仓）**”等极其精确的量化指令。
3.  **对冲路线推荐 (Hedging)**：在图谱中反向查询，寻找因该事件收益（正向二阶影响）且与当前持仓负相关的节点作为对冲资产。

### 2.4 长短期的凯利公式应用 (Time Horizon & Kelly Criterion)

长期投资者（如持仓以年为单位的价值投资者或大类资产配置者）是否适用凯利公式？答案是**适用，但参数输入和应用方式与短线交易有本质区别。** 

传统短线交易者的凯利公式输入源于“高频交易的历史统计（如过去100次突破策略的胜率）”。这是**经验概率（Frequentist Probability）**。
对于长期投资，这套 IRM 本体论系统将凯利公式的输入转化为了**贝叶斯概率（Bayesian Probability）**，其应用逻辑如下：

1.  **极值规避（防止毁灭性回撤）**
    长期投资最大的敌人不是日常波动，而是本金的永久性损失。本体论引擎计算出的二阶极值报警，正是为了在长期复利曲线上**剪除致命的左侧尾部风险**。当系统探测到结构性的宏观恶化（如行业颠覆、流动性枯竭），通过动态凯利公式强制减仓，可以避免长期资金深陷泥潭。

2.  **盈亏比 ($b$) 的重新定义**
    在长线投资中，$b$ 不再是“每次止盈止损设置的赔率”，而是**资产未来 3-5 年的预期收益率（CAGR）与最大回撤预期之比**。IRM 引擎通过评估企业在“本体图谱”中所处的生态位（例如：处于成长性赛道且对宏观加息敏感度低），赋予其更高的长期 $b$ 值，推高其基础配置比例。

3.  **部分凯利 (Fractional Kelly) 的必要性**
    满仓运行（Full Kelly）在数学上能在长期实现对数收益最大化，但在现实中会导致极其剧烈的波动。对于长期资金，IRM 系统在执行层应该引入“半凯利 (Half-Kelly)”或更低比例。**即：在本体论图谱给出确定性机会时，系统建议的仓位上限被限制在最优值的 50% 或更低。** 这保证了长期投资组合的夏普比率和账户的平稳生存。

### 2.5 资产先验假设 (Base Assumptions) 的业务定义

在长线投资（3-5 年）的语境下，系统为每个资产设定了一套“先天性格特征”，作为凯利公式的基础输入。

1.  **基础胜率 (base_win_rate / $p$)**：
    *   **业务含义**：代表对资产在投资周期内，基于其竞争壁垒和生态位持续复利能力的“初始确信度”。
    *   **分层策略**：指数类资产（如 QQQM）通常拥有最高的确信度（如 0.70）；高增长单股（如 NVDA, PLTR）因面临竞争和技术迭代，确信度居中；高波动投机资产（如 BTC）确信度最低。
2.  **预期盈亏比 (Upside vs Max Drawdown / $b$)**：
    *   **Upside**：资产在投资周期内预期的总回报潜能。
    *   **Max Drawdown (Max_DD)**：为获得上述回报必须承受的“人性门票”或极端风险底线。
    *   **$b$ 映射**：$b = Upside / Max\_DD$。它是系统判定该资产“值得承担多少回撤风险”的衡星标准。
3.  **动态惩罚逻辑**：
    *   分析引擎输出的 **Impact Score** 会直接扣减 **base_win_rate**。当本体传导显示某资产遭受严重冲击时，系统会判定其“复利确定性”下降，从而强制凯利公式输出更保守的仓位建议，甚至触发清仓（Liquidate）。

---

## 3. 传导公式与参数设计 (Transmission Formula & Engine)


在基于本体论的 IRM 系统中，一条边从 A 指向 B （$A \rightarrow B$），代表 A 的变动会冲击 B。
如何科学地定义这种冲击的**方向**、**强度**和**非线性放大机制**，是分析引擎的核心。

---

### 3.1 核心属性定义层 (Edge Parameters)

我们可以在图谱的每一条边上，定义三个核心属性：

#### 3.1.1 Base Beta (基准敏感度 $\beta$) (基准敏感度 $\beta$)
*   **物理意义**：历史常态下的线性传导系数。代表 A 每变动 1%，B 预期会如何变动。
*   **计算来源**：长期（如 1 年至 3 年）的 Pearson 相关系数或回归斜率。
*   **示例**：
    *   US10Y $\rightarrow$ Tech_Sector: $\beta = -1.5$ （美债收益率上升 1%，科技板块大概率下跌 1.5%）。
    *   Oil $\rightarrow$ Airlines: $\beta = -0.8$。
*   **作用**：决定传导的**基础方向（正相关/负相关）**和**基准力度**。

#### 3.1.2 State Modifier (状态修饰因子 $\mu$) 与机制转换 (Regime-Switching Engine)
*   **架构解耦原则（Node vs Edge）**：在系统设计中，**节点（Node）**仅包含客观的物理属性和当前状态值（如 PE 枢纽自带的 `percentile` 属性）；而**边（Edge）**承载传导计算规律。因此，所有的非线性修饰器（`state_trigger`）和引擎抓取准星（`modifier_metric`）均挂载在边上，由图遍历引擎主动感知并触发计算。
*   **物理意义**：基于目标节点 **当前水位（如历史分位 - percentile）** 的非线性放大器。它是对当前市场环境“极值状态”与“机制转换”的刻画。这在 PE（估值倍数）等本身具有分布特征的基本面指标上体现得尤为明显。
*   **设计原理**：当一个指标处于极低位置和处于极高位置时，它对边际利空的防御力是完全不对称的。“常态线性传导”与“泡沫黑天鹅传导”的差别就体现在这个阈值开关上。
*   **计算方式 (配置驱动引擎侧)**：
    1.  图遍历引擎沿着边（如 `PRICES`）传递冲击时，不再执行任何业务硬编码。它直接读取边上的 `threshold_config` (一段定义了区间的 JSON)。
    2.  引擎提取目标节点（如 PE 枢纽）当前的客观水位值（如 `percentile=0.99`）。
    3.  通过简单的数值区间匹配（如落入 `[0.95, 1.0]` 区间），引擎得出当前的非线性修饰乘数 $\mu$。
*   **作用**：让线性拓扑网络获得捕捉 **Regime-Switching（状态切换）** 和感知**“安全边际”**的能力，同时完美保证了“数据层（客观状态）”与“逻辑层（计算规则）”在代码上的绝对解耦。

##### 三大典型阈值设计模式 (Threshold Design Patterns)
为了使风控逻辑清晰可读，通过配置上述的 JSON 阈值，我们在业务上定义了以下 3 种典型的数据分布模式（它们亦被记录在边上的 `state_trigger` 字段中，供人类或 LLM 快速理解）：

1.  **`percentile_amplifier` (极位指数放大器模式)**
    *   **配置特征**：当目标水位越高时，`mu` 呈现陡峭的台阶式上升（如 >=85% 设为 2.0，>=95% 设为 4.0）。
    *   **应用场景**：主要用于防范**“拥挤踩踏杀估值”**。例如应对 US10Y 冲击高估值的 NVDA/PLTR 时，或高油价引发通胀恐慌时。在极值区，即便是微小的边际利空，也会被视为压倒骆驼的最后一根稻草，引爆极高的非线性破坏力。
2.  **`margin_dampener` (安全边际与低位钝化器模式)**
    *   **配置特征**：当目标水位越低时，`mu` 急剧收缩（如 <=15% 设为 0.25）。
    *   **应用场景**：代表价值投资中的**“跌无可跌 (Price in)”**。只要大盘蓝筹资产（如 AAPL/GOOGL 的估值）跌到了历史极寒水位，它就会像海绵一样吸收并过滤上游传来的冲击，不再将恐慌等比传导至资产组合端，模拟“避险资金最后堡垒”的抗跌性。
3.  **`threshold_breaker` (阈值断路器 / 阶跃跃迁器模式)**
    *   **配置特征**：不再关注平滑过渡。某特定点位之下 `mu` 为极小的常态值，一旦跨越临界值，直接跳跃至 `mu >= 1.0`。
    *   **应用场景**：代表**宏观范式的突破或是心理红线**。例如，当实际利率（名义利率 - 通胀预期）跨越某个临界点时，资金将成群结队地无情抛弃黄金回流生息资产，此时直接触发价值重估机制。

#### 3.1.3 Volatility Accelerator (波动率加速器 / Gamma 因子 $\gamma$)
*   **物理意义**：市场恐慌情绪导致的流动性溢价与抛售踩踏效应。
*   **设计原理**：当整体市场处于高位震荡或“VIX（恐慌指数）”飙升时，坏消息的破坏力会被无情放大，好消息则会被无视。
*   **作用位置**：这是一个**全局参数（Global Setting）**或**宏观条件参数**。
*   **计算方式**：$\text{if } VIX > 30 \text{, then } \gamma = 2.0 \text{ else } \gamma = 1.0$。所有涉及避险或高风险资产下挫的边，乘以该系数。

---

### 3.2 距离衰减因子 (Distance Decay Factor, \(D^n\)) 的业务定义

在图谱遍历由于传递节点众多时，“蝴蝶效应”会被无限放大从而得出错误结论。为了让风险计算拟合现实（物理定律中的能量守恒），系统引入了距离衰减因子 $D^n$。

#### 物理与市场意义
*   **信息耗散**：随着传导链条的拉长，原始事件的影响力在金融市场中会被其它中间变量（如市场情绪的消化、公司的逆周期套期保值、套利者的抹平操作）所稀释。衰减因子代表了这种**影响力的沿途损耗**。
*   **确定性折价 (Uncertainty Discount)**：一阶影响往往是最确定的（比如突发加息 $\rightarrow$ 短期美债收益率飙升，这几乎是 100% 发生）。但传导到二阶、三阶时，逻辑链条变长，被证伪的概率增加。$D^n$ 本质上是对传导路径不确定性的一种“概率打折”。

#### 公式定义与赋值逻辑
*   **基础衰减常量 (D)**：通常取值为 `0.6` 到 `0.85` 之间。代表每经过一个节点跳转，原始冲击力保留的百分比。
*   **幂次递减 (n)**：$n$ 表示从源头事件节点（$n=0$）出发，经过的边的数量。
    *   源头事件 (Event) $\rightarrow$ 一级受影响资产 ($n=0$)，衰减为 $D^0 = 1$ (满额承受)。
    *   一级资产 $\rightarrow$ 二级资产 ($n=1$)，衰减为 $D^1$。
    *   二级资产 $\rightarrow$ 三级资产 ($n=2$)，衰减为 $D^2$。

**示例**：
假设基础衰减系数设定为 $D=0.75$（每次传递损耗25%）：
> 原油供应中断（震惊值100分）
> $\rightarrow$ 原油价格暴涨（承受100分冲击）
> $\rightarrow$ 航空业燃油成本激增（承受 $100 \times 0.75 = 75$分冲击）
> $\rightarrow$ 某航空公司利润下滑（连降多级：只分配到 $75 \times 0.75 = 56.25$分）

> [!important] 防限流与阈值截断 (Threshold Truncation)
> 在工程实现上，如果不控制衰减，系统会陷入无限深度的子图遍历（例如计算出 10 阶微弱影响）。因此在代码层面，通常需要设定：**当 $Impact \times D^n$ 的绝对值小于某个微小阈值（如0.01）时，遍历终止（Pruning）。** 其业务含义是“市场已经彻底钝化，该末端影响可忽略不计”。

---

### 3.3 传导公式合成 (Transmission Formula)

结合上述三个变量，我们可以得到一个“非线性动态传导”公式：

$$Impact(B) = \Delta A \times \Big( \beta \times \mu(A_{current\_state}) \times \gamma(Market_{volatility}) \Big) \times D^{n}$$

**变量解释**：
*   $Impact(B)$：资产/节点 B 承受的绝对冲击分值（最终用来指导减仓）。
*   $\Delta A$：源头事件释放的原始 Delta（如降息超预期，算作 +2.0）。
*   $\beta$：边上的基准敏感度常量。
*   $\mu(A_{state})$：根据节点 A 当前水位实时查表得出的修饰倍数。
*   $\gamma$：全局恐慌情绪加速器。
*   $D^{n}$：距离衰减因子 (Distance Decay，属于图遍历属性。一阶 $D^0=1$，二阶 $D^1=0.8$，代表链条越长，影响越弱)。

---

## 4. 技术落地方案

### 4.1 模块交互工作流 (Workflow)

```mermaid
sequenceDiagram
    participant LLM as Event Parser (LLM)
    participant Graph as Ontology Graph (FalkorDB)
    participant Engine as Transmission Engine (Tracer)
    participant Portfolio as Portfolio State
    participant UI as Output / Suggestion

    LLM->>Graph: 解析自然语言新闻，Grounding 到起始物理节点 (e.g. Oil: +10%)
    Engine->>Graph: 沿着网络扩散，查询目标节点状态与边配置
    Graph-->>Engine: 返回包含目标水位 (percentile) 与边规则 (threshold_config) 的子图
    Engine->>Engine: 线性传导: 结合 Base Beta 一阶推进
    Engine->>Engine: 非线性修正: 纯数据驱动，解析边 JSON 区间得出乘数 mu
    Engine->>Engine: 累加并衰减高阶网络影响 (e.g. 枢纽 EPS -4.8)
    Engine->>Portfolio: 将所有末级资产的衰减幅面映射到真实账户持仓
    Portfolio-->>Engine: 计算整体资产回撤敞口
    Engine->>UI: 触发预警并输出凯利公式调仓建议
```

### 4.2 大语言模型 (LLM) 的核心角色定义

在这个系统中，LLM **不负责直接计算数学风险**，而是作为连接非结构化现实碎片与高度结构化本体图谱之间的**翻译官和映射器 (Semantic Router & Parser)**。

它的主要职责锚定在以下两个关键环节：

1.  **输入端：事件的结构化解析 (Event Extraction & Grounding)**
    现实世界的新闻是混乱的（如：“沙特设施遇袭，产量下降”或“美联储暗示年内由于就业不佳将提前降息”）。引擎无法直接读取这些文本。
    LLM 的任务是阅读这些新闻/研报，并强制输出符合 `tracer.py` 入参的指令：
    ```json
    {
      "target_ticker": "UKOIL",
      "initial_delta_pct": "+8",
      "current_vix_estimate": 25,
      "event_logic": "沙特减产引发的供给侧断崖冲击"
    }
    ```
    它负责把含糊的人类语言，翻译成图分析引擎能接收的“初始扰动参数 ($\Delta A$)”与全局宏观系数定调（VIX）。

2.  **输出端：投顾视角的逻辑凝练 (Explainability & Advising)**
    传导引擎计算完后，输出的只有一堆冰冷的数字（如 `DAL Impact Score: -1.2, Position -25%`）。
    LLM 的第二个任务是接收这些计算结果和图谱中边上带有的 `logic` 解释，并结合当前的宏观语境，为交易员生成一段逻辑连贯的“诊断报告”。
    *示例输出*：“由于本次原油减产发生在油价历史高位（激活了 `percentile_amplifier`），且当前市场风险偏好脆弱（VIX=28）。风险模型侦测到您的持仓中【达美航空】暴露在严重的二阶传导链路上风险评分为-4.8。但其自身估值防御强劲触发了 `margin_dampener`，最终建议将其仓位缩减四分之一进行锁损防御。”

> **深度思考：为什么不让 LLM 纯天然地全干？**
> LLM 存在极高的幻觉率，且在复杂图谱的多跳高阶浮点数连乘计算上表现灾难。如果在提示词里让 LLM 直接想“油价对各行业有啥影响并给个减仓比例”，它很可能是基于陈旧记忆瞎编的。**让大语言模型负责理解语义、提取参数与解说翻译；让 FalkorDB 图数据库和 Python 算法负责严格定量的数学传导**，这是目前金融 AI 工程化最为精准的落地解法（Neuro-Symbolic AI 神经符号学架构）。

### 4.3 目录结构规划建议

在现有的 `pi-mono-stack/irm/scripts/` 目录下，已经形成并落地了以下核心结构：

```text
irm/scripts/
├── entrypoint.sh             # 容器启动引导与后台生命周期维持
├── irm.sh                    # 统一操作 CLI 入口路由 (irm tracer, irm advisor, irm portfolio, irm init-db)
├── ontology/
│   ├── sync_schema.py        # Schema 同步器：解析 .cypher 实体规则库并全量注入图谱
│   ├── tracer.py             # 纯血图算法核心：基于 Cypher 读图与 JSON 阈值配置驱动的非线性传导引擎
│   ├── calc_betas.py         # 自动化 Beta 提取：基于历史数据回归分析资产间的线性敏感度
│   ├── update_price_signals.py # 全局价格信号同步：拉取资产/指标价格并更新其在图中的分位数水位
│   ├── update_percentiles.py  # 估值分位更新：自动化拉取 PE 数据并计算拥挤度分位
│   └── update_earnings.py    # 盈利预期更新：同步底层标的的盈利预测与增速分位
└── analyzer/
    ├── portfolio_viewer.py   # 持仓观测舱：聚合组合持仓并实时展成金融仓位表
    ├── portfolio_advisor.py  # 凯利公式专家组：结合推演损幅与 Bayesian 胜率修正，给出仓位建议
    ├── config_manager.py     # 分布式配置管理：统一维护 Redis 中的经验区间(Bands)与数据源映射
    └── node_viewer.py        # 节点探针：快速查询特定 Ticker 在图中的物理属性与分位点
```

---

### 4.4 核心边引擎机制 (JSON Payload Schema)

可以通过编写一个 Python 字典（或 JSON Schema）来优雅地结构化这种多维度边：

```json
// edges_config 示例 (映射为 Cypher 定义)
{
  "source": "US10Y",
  "target": "PE_NVDA",
  "edge_attributes": {
    "base_beta": -1.8,
    "modifier_metric": "target_percentile",  // 引擎指令：主动去读取 target(PE_NVDA) 节点的 percentile 属性 (或填 source_percentile 读起源节点水位)
    "state_trigger": "percentile_amplifier", // 保留作为语义化标签，用于 LLM 投顾解说与前端可视化染色
    "threshold_config": [                    // 引擎实际执行的“纯数字化规则”
      {"min": 0.95, "max": 1.0, "mu": 4.0},  // 极值崩塌区 (>=95%)：触发 4倍 放大
      {"min": 0.85, "max": 0.95, "mu": 2.0}, // 风险预警区 (85%~95%)：触发 2倍 放大
      {"min": 0.0,  "max": 0.85, "mu": 1.0}  // 常规区间 (<85%)：常态线性传导
    ],
    "gamma_sensitive": true,                 // 是否受全局恐慌情绪(VIX)加持
    "logic": "极高贴现率重创超高估值AI远期现金流"
  }
}
```

这种设计的精妙之处在于：**日常盘整期（$\mu=1, \gamma=1$）它退化为普通的线性相关性模型；而一遇极值环境，非线性乘数被激活，它就摇身一变成了一套“黑天鹅防御雷达”。**

---

### 4.5 P/E 百分位自动化更新管道 (PE Percentile Pipeline)

该管道旨在自动执行从外部金融市场（OpenBB）拉取实时市盈率（P/E），并根据配置的经验带（Bands）计算资产估位（Percentile），最后将计算结果持久化到 FalkorDB 本体图谱中，以驱动风控引擎的动态传导。

#### 1. 架构概览

系统采用 **“配置与逻辑分离”** 的设计模式，主要由三部分组成：分布式配置中心（Redis）、数据采集执行器（Python/OpenBB）和本体知识图谱（FalkorDB）。

```mermaid
graph TD
    subgraph "External"
        OpenBB[OpenBB SDK / yfinance]
    end

    subgraph "IRM Container"
        CLI[IRM CLI / irm.sh]
        ConfigMgr[config_manager.py]
        ValUpdate[update_percentiles.py]
        EarnUpdate[update_earnings.py]
    end

    subgraph "Infrastructures"
        Redis[(Redis - Config Store)]
        FalkorDB[(FalkorDB - Ontology Chart)]
    end

    CLI -->|pe/eps-bands update| ConfigMgr
    ConfigMgr -->|HSET/HGETALL| Redis
    ValUpdate -->|PE Bands| Redis
    ValUpdate -->|Fetch PE| OpenBB
    ValUpdate -->|Update Hub:Valuation| FalkorDB
    EarnUpdate -->|EPS Bands| Redis
    EarnUpdate -->|Fetch EPS Growth| OpenBB
    EarnUpdate -->|Update Hub:Earnings| FalkorDB
```

#### 2. 核心组件说明

*   **配置层 (Redis)**：
    *   `irm:config:pe_bands`: 存储 Ticker 对应的 PE 经验区间（用于杀估值判定）。
    *   `irm:config:eps_bands`: 存储 Ticker 对应的盈利增速预期区间（用于杀业绩判定）。
*   **执行层 (update_percentiles.py / update_earnings.py)**：
    1.  **扫描图谱**：查询所有 `(h:Hub:Valuation)` 或 `(h:Hub:Earnings)` 节点。
    2.  **拉取数据**：调用 `openbb` 获取 `pe_ratio` 或 `earnings_growth` (Forward EPS Growth)。
    3.  **水位映射**：依据 Redis 中的 `[min, max]` 区间，将绝对指标映射为 **0.0 - 1.0** 的拥挤度分位（Percentile）。
    4.  **写回图谱**：更新 `Hub` 节点的 `percentile` 属性。
*   **管理层 (IRM CLI)**：
    *   `irm pe-bands update <ticker> <min> <max>`
    *   `irm eps-bands update <ticker> <min> <max>`

---

### 4.6 全局价格信号自动化配置与同步管道 (Price Signals Pipeline)

该管道旨在提取“客观的市场状态（例如美元处于历史极高位、标普100的实时价格等）”，并将其作为 `percentile` 属性或其他动态指标更新至本体图谱。

#### 1. 架构概览

数据源同步管道遵循“配置（由终端设定）与执行（由算力完成）彻底代码级分离”的理念。它承载了全系统所有逻辑资产（Ticker）到物理交易所代码（Symbol）的映射关系。

```mermaid
graph TD
    subgraph "External Providers"
        YFinance[Yahoo Finance]
        FRED[Federal Reserve Economic Data]
    end

    subgraph "IRM Container"
        CLI[IRM CLI / irm.sh]
        ConfigMgr[config_manager.py]
        MacroUpdater[update_price_signals.py]
    end

    subgraph "Infrastructures"
        Redis[(Redis - Config Store)]
        FalkorDB[(FalkorDB - Ontology Chart)]
    end

    CLI -->|sources ls/update| ConfigMgr
    ConfigMgr -->|HSET/HGETALL| Redis
    MacroUpdater -->|Read Config| Redis
    MacroUpdater -->|Fetch 3Y TimeSeries| YFinance
    MacroUpdater -->|Fetch 3Y TimeSeries| FRED
    MacroUpdater -->|Calculate rank(pct=True)| MacroUpdater
    MacroUpdater -->|Update Value & Percentile| FalkorDB
```

#### 2. 核心组件说明

*   **配置层 (Redis `irm:config:sources`)**：
    存储所有纳管资产的拉取凭证信息（如 `{"US10Y": {"symbol": "^TNX", "provider": "yfinance"}}`）。
*   **执行层 (update_price_signals.py)**：
    1.  **拉取历史序列**：通过 OpenBB 向供应商拉取 3 年历史数据。
    2.  **计算水位 (Percentile)**：应用 `rank(pct=True)` 提取分位数。
    3.  **提取物理值 (Value)**：保留资产的最新报价数据（如 VIX 报价 15.3 或 BTC 价格）。
    4.  **更新图谱**：同步设置 `Asset` 节点的 `percentile` 和 `value` 属性。
*   **管理层 (IRM CLI)**：
    *   `irm sources ls`：查看当前纳管的所有标的与代码映射。
    *   `irm sources update <ticker> <symbol> <provider>`：动态修改或新增标的映射。

---

### 4.7 自动化 Beta 提取与回归演进管道 (Beta Calculation Pipeline)

该管道是系统“自适应能力”的核心，负责定期通过真实市场交易数据提取资产间的线性敏感度（$\beta$）。

#### 1. 业务逻辑
系统拒绝使用静态硬编码的 Beta，而是通过历史回归得出结论。
*   **回归区间**：拉取过去 3 年 (156 周) 的数据。
*   **采样频率**：自动降采样为 **周线 (Weekly)**，以过滤日内噪音，捕捉价值中枢的真实联动。

#### 2. 数学范式对齐 (`metric_type`)
根据本体图节点上定义的 `metric_type` 自动切换回归算法：
*   **Rate 类回归**：源节点为 `rate` 时，计算 `diff()` (基点变动) 进行 OLS。
*   **Price 类回归**：源节点为 `price` 时，计算 `pct_change()` (收益率) 进行 OLS。

#### 3. 统计学显著性防御
脚本 (`calc_betas.py`) 在回写前强制检查 **P-Value**。只有 $P < 0.1$ 的联动路径才会被更新至图谱，否则判定为“伪相关”，保留专家定义的常识先验值。

---

## 附录：核心实体节点 (Node Types) 与物理属性定义库

在 IRM 本体论中，节点(Node) 严格遵守“只保留客观事实”的解耦原则。所有的业务敏感度、传导方向和放大乘数一律挂载在边(Edge)上。

### 1. 金融与宏观资产类 (`Asset` 及其子标签)
可交易或可监测的具体标的，用于唯一标识物种其在宏观结构中的角色。
*   `ticker` *(String, 必填)*: 唯一标识代码（如 'US10Y', 'AAPL', 'VIX'）。
*   `name` *(String, 必填)*: 资产的中英文全称或简称。
*   `value` *(Float, 动态脚本维护)*: **当前物理报价/指标值**。引擎（`tracer.py`）利用该值判定是否触发边上的阶跃阈值，或以此计算扰动后的新环境水位。
*   `percentile` *(Float, 动态脚本维护)*: 该资产在 3 年历史区间内的分位水位。
*   `metric_type` *(String, 必填)*: **核心计算属性**。`rate` 代表利率/波动率（取差分回归）；`price` 代表价格资产（取收益率回归）。
*   `region` *(String, 可选)*: 所属地域（如 'US', 'JP'），主要用于宏观利率。
*   `role` *(String, 可选)*: 宏观角色定义（如 'Global Pricing Anchor'）。
*   `type` *(String, 可选)*: 资产具体形态（特用于汇率，如 'Fiat Index', 'FX Pair'）。
*   `market` *(String, 可选)*: 所属金融市场板块（特用于波动率，如 'Equity', 'Fixed Income'）。
*   `sector` *(String, 可选)*: 资源/物理行业分类（特用于大宗商品，如 'Energy', 'Precious Metals'）。
*   `style` *(String, 可选)*: 投资组合风格归类（特用于 ETF，如 'Growth', 'Defensive'）。
*   `supply_type` *(String, 可选)*: 供给模型属性（特用于 Crypto，如 BTC 的 'Fixed'）。

### 2. 微观公司实体 (`Asset:Stock`)
代表具体的上市公司标的，携带有用于评估实体冲击的财务拆解数据。
*   继承上述 `Asset` 的核心属性 (`ticker`, `name` 等)。
*   `foreign_revenue_pct` *(Float, 可选)*: 财报披露的海外营收占比（如 `0.58`）。作为客观物理指标，它将在引擎推演强势美元 (DXY) 冲击时，决定该公司承受汇兑损益折损的底座基数。

### 3. 主题与行业概念聚合网 (`Sector`, `Theme`)
用于抽象的网状层级，归拢同质化风险或市场共振叙事。
*   `name` *(String, 必填)*: 标准英文界定名（如 'Information Technology', 'AI Infrastructure'）。
*   `name_cn` *(String, 可选)*: 辅助中文命名定性。

### 4. 账户维度的终端节点 (`Portfolio`)
IRM 系统的投顾和凯利公式重分配目标。
*   `owner` *(String, 必填)*: 账户持有人识别（如 'Admin'）。
*   `name` *(String, 必填)*: 组合定位名。
*   `strategy` *(String, 可选)*: 交易主旨大纲（如 'Macro-Thematic Allocation'）。
*   `currency` *(String, 必填)*: 计价与结算基础币种（如 'USD'）。
*   `total_value` *(Float, 必填)*: 组合当前整体资产净值规模（如 `1000000`）。

### 5. 定价引擎极值监控节点 (`Hub` - `Valuation` / `Earnings`) ★ 核心
作为金融泡沫与业绩恐慌的吸收防波堤。
*   `target` *(String, 必填)*: 指向其映射的底层标的 ticker（如 'NVDA'）。
*   `name` *(String, 必填)*: 指标特征维度定义（如 'NVDA 估值倍数 (PE)'）。
*   `pe_percentile` *(Float, 可选)*: **当前 PE 历史分位点（如 `0.95`）**。衡量估值拥挤度。
*   `erp_percentile` *(Float, 可选)*: **当前 ERP 历史分位点（如 `0.05`）**。衡量个股相对于美债的性价比，是触发利率敏感性崩塌的关键。
*   `percentile` *(Float, 可选)*: [兼容性保留] 默认为 `pe_percentile`，引擎将优先寻找特定指标。
*   `value` *(Float, 动态)*: 实时指标原值。

---

## 附录：核心传导边 (Edge Types) 与引擎属性库

边 (Edge) 承载了系统所有的“业务逻辑”、“数学敏感度”以及“状态转换阈值”。节点间的互相关联共同织成了风险传导演算网络。

### 1. 边的语义类型 (Edge Relationships)
*   `[:DRIVES]` **(宏观驱动)**: 描绘金融市场第一推动力（如油价推高通胀预期）或主题叙事爆发（如 AI 概念拉爆龙头股价）。
*   `[:SPILLS_TO]` **(风险溢出)**: 描绘因资金链脆弱导致跨市场恐慌蔓延（如债市利率剧震引爆股市恐慌）。
*   `[:PRICES]` **(定价压制)**: 核心算力通道。用于宏观因子或风险因子对资产或定价枢纽进行定点打击（常带有复杂的极值阈值设定）。
*   `[:COMPOSES]` / `[:TRACKS]` / `[:BELONGS_TO]` / `[:HEAVILY_EXPOSED_TO]` **(结构归属)**: 定义资产间的物理从属特征（如个股占行业圈定的权重，指数占成分股的权重）。
*   `[:CORRELATES_WITH]` **(相关性补充)**: 捕捉无法用因单项归因解释，但具有统计学同步特征的市场行为。
*   `[:DETERMINES]` **(价值决定)**: 限定于 Hub (PE/EPS 枢纽) 到底层资产方向。承载 P = PE * EPS 的转化公式。
*   `[:HOLDS]` **(组合触达)**: 承载终端私人账户 (Portfolio) 对资产的真实持仓明细。

### 2. 传导计算核心属性 (Engine Execution Properties)
这些属性直接决定引擎 `tracer.py` 如何利用距离衰减公式计算最终冲击。

*   `base_beta` *(Float)*: **基准线性敏感度**。表示常态盘整期下，源头节点每变动 1%，目标节点理论上的变动幅面（如 `-1.8`，代表反向放大）。
*   `gamma_sensitive` *(Boolean)*: **恐慌共振开关**。如果为 `true`，代表此路径在 VIX 飙升等全局恐慌时期极容易发生踩踏出逃，引擎将叠加全局 Gamma 加速器。
*   `threshold_config` *(String/JSON Array)*: **非线性阶跃/阻断配置**。引擎计算的核心数据驱动层。形如 `[{"min": 0.95, "max": 1.0, "mu": 4.0}, ...]`，引擎会扫描目标节点的当前客观水位并赋予暴风乘数 (mu) 或过滤乘数。
*   `logic` / `description` *(String)*: **系统推演解说词**。计算引擎不读该字段，它的作用是作为 Prompt 提供给末端投顾 LLM 提取以生成通顺的人类研报（如：*"强势美元抽血加密市场流动性"*）。
*   `modifier_metric` *(String)*: **[已剥离至架构注释]** (如 'target_percentile')。用以说明上述 `threshold_config` 所对准的目标节点探测字段。
*   `state_trigger` *(String)*: **[已剥离至架构注释]** (如 'percentile_amplifier', 'margin_dampener')。用作可视化系统的渲染标签指令。

### 3. 静态权重与持仓属性 (Static & Holding Properties)
主要出现在归属、包含或账户边缘。

*   `composition_weight` / `sector_weight` *(Float)*: 客观成分占比（如科技股占纳斯达克100权重的 `0.58`）。
*   `weight_pct` *(Float)*: 当前该资产占 Portfolio 的持仓配额百分比（如 `0.25` 代表 25% 仓位）。
*   `shares` *(Float)*: 持有的具体份额数。
*   `avg_cost` *(Float)*: 用户交易建仓的基础成本。
*   `formula` *(String)*: 转化公式口径释义（如 `P=EPS*PE`）。

---

## 5. 系统部署与容器拓扑 (System Deployment & Topology)

IRM 模块采用高度解耦的微服务/容器化设计，以确保计算引擎与数据存储的独立扩展性。

### 5.1 容器集群架构

系统由两个核心容器组成，通过 Docker 内部网络进行高速通信：

*   **网络模式 (Network Mode)**：采用 **Host Mode** (`--network host`)。容器直连宿主机网络协议栈，消除 NAT 损耗，确保大规模图数据查询与回归运算的毫秒级响应。在此模式下，容器内部通过 `localhost:6379` 互联。

1.  **`irm` 算力容器 (Python Compute Engine)**
    *   **角色**：承载所有的业务逻辑与数据管道（Pipelines）。
    *   **组件**：包含 OpenBB SDK、图计算引擎 (`tracer.py`)、凯利公式决策器、以及各项属性同步脚本。
    *   **交互**：从外界（OpenBB/FRED）拉取金融数据，并向 `redis` 容器发起 Cypher 查询和配置读写。

2.  **`redis` 存储容器 (FalkorDB + Config Store)**
    *   **角色**：混合型数据中枢。
    *   **FalkorDB**：作为图数据库（默认 6379 端口），存储整个本体图谱（Nodes/Edges）。
    *   **Redis Key-Value**：作为配置中心（`irm:config:*`），存储 PE/EPS 的经验带（Bands）和数据源映射。

### 5.2 网络拓扑与数据流向

```mermaid
graph LR
    subgraph "Host Network (Standardized on localhost)"
        IRM[irm 容器] -- "Cypher/Redis (127.0.0.1:6379)" --> DB["redis 容器 (FalkorDB)"]
    end

    Internet((Internet)) -- "API (OpenBB/FRED)" --> IRM
    User((User)) -- "CLI (irm.sh)" --> IRM
```

### 5.3 生产环境部署建议

*   **持久化**：`redis` 容器必须挂载外部卷，以防 FalkorDB 中的本体图谱数据在容器重启时丢失。
*   **凭证管理**：所有的 API Key（如 `FRED_API_KEY`）应通过 Docker Environment 或 `.env` 文件注入 `irm` 容器，严禁硬编码在脚本中。
*   **连接配置**：`irm` 算力引擎与 `redis` 存储层的连接串统一由环境变量 **`REDIS_URL`** 定义（例如：`redis://localhost:6379`）。系统内部所有脚本（如 `tracer.py`, `update_earnings.py`）均通过该变量初始化数据库客户端连接。
*   **资源配额**：由于 `calc_betas.py` 等脚本涉及大规模回归运算，且 `falkordb` 在进行深度路径遍历时具有一定的内存开销，建议为 `irm` 和 `redis` 容器设置合理的内存上限。

### 5.4 部署与构建指令 (Commands)

系统推荐使用顶层控制工具 `stack-ctl` 进行标准化的构建与部署：

*   **全量构建与启动**：
    ```bash
    # 在项目根目录下执行，自动完成镜像构建与容器编排
    stack-ctl build irm
    stack-ctl up irm
    ```
*   **状态同步与热重载**：
    如果仅修改了脚本内容而无需重构镜像，可利用 `docker cp` 将代码推送到正在运行的容器中，或通过 `stack-ctl` 触发配置滚动更新。
