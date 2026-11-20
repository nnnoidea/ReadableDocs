# 绘图模板与统一风格

先按[读者问题选图](choosing-figures.md)，再在目录中选择模板。以下依次说明可选模板、生成方法、内容口径和视觉样式；只读取当前图型需要的字段。

## 模板目录

| 读者问题 | 模板名 | 主要填写内容 |
| --- | --- | --- |
| 整体包含哪些部分 | `containment` | `root`：`label` 与嵌套 `children` |
| 两组对象有哪些交集 | `set-overlap` | 两个 `sets`，各含 `label` 和成员 `items` |
| 哪些对象对应 | `mapping` | `left/right` 的 `id/label`；`links` 的 `from/to/label` |
| 谁负责哪些任务 | `responsibility-matrix` | `rows`、`columns`、二维 `values` |
| 步骤怎样进行 | `flow` | `nodes` 的 `id/label`；`edges` 的 `from/to/label` |
| 条件怎样决定分支 | `decision` | 同上；条件节点用 `kind:"decision"`，分支标签写条件 |
| 对象怎样分层 | `hierarchy` | 节点和归属边；需要时填语义层次 `rank` |
| 什么事件改变状态 | `state` | 状态节点、转换边及触发条件 |
| 谁执行并交接工作 | `swimlane` | `lanes`；顺序 `steps` 中的 `lane/text/edge_label` |
| 各方怎样交换消息 | `sequence` | `participants`；`messages` 的 `from/to/label` |
| 事件怎样依次发生 | `timeline` | `events` 的 `date/label/detail`，按阅读顺序填写 |
| 时间区间怎样重叠 | `gantt` | `rows` 的 `label/start/end`，可填短 `note` |
| 分组内部怎样组织、分组之间怎样连接 | `grouped-flow` | `groups` 的 `label/nodes`；全图 `edges`，可标 `feedback` |
| 多对象怎样分别完成共同步骤 | `aligned-process` | `columns`；各行 `label/cells`，按列连接步骤 |
| 非数值的结构或机制有何差异 | `structure-comparison` | 同上，按共同方面对齐比较 |
| 总览中的部分具体怎样工作 | `overview-detail` | `overview`；`details` 的 `target/figure` |
| 哪些组合更高、更低 | `heatmap` | `rows`、`columns`、二维数值 `values`、`unit` |
| 各部分占整体多少 | `composition` | `series` 名称；每行 `label/values`，按占比归一 |
| 总量与组成怎样变化 | `stacked-amount` | 同上；各条用相同数量刻度 |
| 相对基线有何收益与代价 | `delta-comparison` | `series`；各行基线说明与差值 `values`；`unit` |
| 趋势距离参考线多远 | `trend-reference` | 真实 `x`；`series` 的 `name/values`；参考 `label/value` |
| 多项指标分别距离目标多远 | `metric-reference` | `panels` 中各指标的数据、参考值、单位 |
| 同一问题需要多个观察角度 | `multi-panel` | `panels` 中各子图的完整内容；`columns` 为 1 或 2 |
| 单个整体的占比 | `pie` | `labels`、非负 `values`，总和为正 |
| 一个关键结果是多少 | `stat-card` | `label/value/unit`；可选必要短注 `detail` |
| 当前距离目标多少 | `target-meter` | `label/value/target/unit`；可选 `minimum`（默认 0）、`target_label/detail` |
| 同一对象前后变化多少 | `before-after` | `rows` 的 `label/before/after`；`before_label/after_label/unit`；可选变化量 `display_scale/delta_unit` |
| 比较类别数值 | `bar` | `labels`、`values`；多组可用 `series` 的 `name/y` |
| 长名称类别怎样比较 | `horizontal-bar` | 与 `bar` 相同；横向排列，数值在条形末端 |
| 普通数值趋势 | `line` | 数值 `x`、`values`、`x_label/y_label` |
| 两个数值变量的关联 | `scatter` | 数值 `x`、`values`，每对值属于同一对象 |
| 数据集中在哪里 | `histogram` | 原始 `values`、分箱数 `bins`（默认 8，1–50） |
| 比较分布与离群值 | `boxplot` | `groups` 中的 `label/values` |

选择组合布局或需要对象图形、连接字段时，读取[组合布局与视觉组件](composing-figures.md)。

## 选模板、填内容、渲染

`SKILL_DIR` 表示本 Skill 所在目录，执行时替换为实际路径。只需 Python 3 标准库即可生成 SVG。需要跨图复用颜色时，先准备名称到颜色的映射文件 `colors.json`，具体取值见下文统一风格。

```sh
python3 SKILL_DIR/scripts/draw.py --list
python3 SKILL_DIR/scripts/draw.py --template composition > figure.json
# 编辑 figure.json，填入实际内容后生成图
python3 SKILL_DIR/scripts/draw.py figure.json figure.svg
# 可选：整篇文档复用同一份对象—颜色配置
python3 SKILL_DIR/scripts/draw.py figure.json figure.svg --colors colors.json
# macOS PNG 预览，需 Quick Look 与 Pillow
python3 SKILL_DIR/scripts/preview.py figure.svg figure.png
```

每个模板都是 `assets/templates/` 下的独立 JSON，只读取选中的模板。对象、数值、日期均是示例；替换标题、说明、数据和来源，按需增加或删除内容项，保留图型所需字段。生成器计算位置、连线、坐标和换行；输出后检查实际渲染及图文。

所有图型共用 `title`（标题）、`subtitle`（补充说明）和 `caption`（来源、单位或必要限定）。也可在自行编写的 JSON 中填写 `"template":"composition"` 选择布局，并提供该图型的必要内容；模板名本身只提供布局参数。

## 数据与关系口径

- **包含图**：按 `children` 画嵌套框，框大小用于容纳内容，不编码数量。层次过深时拆成局部图。
- **交集图**：根据两个成员列表计算独有和交集。面积只表示集合关系；更多集合用对应矩阵表达。
- **映射图**：`links` 默认有箭头，`directed:false` 使用无向连线。连接密集或标签过多时用矩阵。
- **矩阵与热力图**：行、列和值维度相同。热力值为有限数或 `null`；`null` 显示缺失，0 是真实数值。跨零时颜色区分正负，深浅表示绝对值；其余情况颜色越深数值越大，图注给出口径。
- **时间线**：依次呈现输入事件，间距不表示持续时间。**甘特图**按实际时间定位，日期用 `YYYY-MM-DD`，或全部用同一单位的数字；结束等于开始表示里程碑。
- **堆叠图**：每行 `values` 与 `series` 同序；系列可用名称字符串，或 `{"name":"名称","emphasis":true}` 对象。`normalize:true` 归一到 100%，总和须大于 0；`false` 使用共同数量刻度。均标原始值与总量，需填单位。
- **差值图**：输入按明确基线计算的差值，各行标签说明基线。系列同样支持名称字符串或带 `name/emphasis/color` 的对象。默认模板 `display_scale:100` 将 0–1 分差转成百分点；普通差值用 1，并填写相应单位。
- **参考线趋势图**：`x` 严格递增，按真实间距绘制。参考值参与坐标范围计算；可填 `y_min/y_max`，范围必须覆盖所有点和参考线。默认就近标出系列名与末点值，参考线保留名称和值；`label_indices` 指定需强调的点值位置（从 0 开始），`show_values:true` 展开全部点值，`false` 仅保留系列名称。各面板轴范围分别标注。
- **多面板**：默认纵向排列，适合文档阅读；`columns:2` 可并排。子图各自有标题、单位和范围；相同尺度比较时显式填写一致的轴范围。每个子图采用本表内已有布局，层级为一层。
- **数值卡与目标尺**：数值为有限数；单位与必要限定就近填写。目标尺要求 `target > minimum` 且 `value >= minimum`，超过目标时扩展刻度并标明超出量。前后对照点图保留两个值的共同尺度，变化量默认按“后 − 前”计算。
- **普通数据图**：`bar/line/scatter` 多组数据可用 `series:[{"name":"组名","x":[1,2],"y":[3,5]}]`。柱状图使用共同 `labels`；`orientation:"auto"` 会为长名称或超过六个类别选择横向布局，亦可指定 `horizontal/vertical`；折线按输入顺序连接。直方图为等宽分箱，最后一组包含最大值；箱线图采用线性插值四分位数、1.5 IQR 须和单独离群点。

## ReadableDocs 风格

统一样式在 `scripts/canvas.py`：标题 27、分组标题 19、主体 17、标签 15、紧凑注释 13、关键数值 44；网格、参考线、普通线、重点线分为四级。文字按最终画布宽度测量，普通与参考线趋势图共用末端标注和引线避让。白底，深蓝灰正文，蓝与青绿为主要类别色，赭色用于参考或提醒；低对比网格、圆角浅底框、左侧细色条标题。字号、留白、换行和图注由共同画布处理。颜色用于区分信息，正负方向及条件同时用文字、位置或符号表达。

两个目标同时落实到成图：**重点更突出、更易懂；画面更好看。** 先确定主次，再安排视觉分量；按内容收紧画布，相关对象靠近、不同信息组留出间隔。数据标记清楚，网格与辅助边线较轻；关键标注就近放置，文字保持深色。并列比较保持同一尺度，数据的长度、位置与比例保持真实。

### 填内容时指定重点

| 模板 | 可填写的字段 | 效果 |
| --- | --- | --- |
| `flow/decision/hierarchy/state` | 节点或边 `emphasis:true`；顶层 `focus_path:["a","b","c"]` | 节点浅青底、强调边线和粗体；路径加重并用青色；路径须沿材料中已有的有向连接 |
| `flow` | `direction:"auto"`（默认）、`"vertical"` 或 `"horizontal"` | 最多四节点的简单链自动横排；其余默认纵排。显式横排支持分支与汇合，复杂连接自动绕开节点 |
| `containment` | 任意层对象 `emphasis:true` | 突出需要首先看见的组成部分 |
| `mapping` | 左右对象或连接 `emphasis:true` | 突出当前对应关系 |
| `swimlane/sequence` | 步骤或消息 `emphasis:true` | 突出关键动作或交接 |
| `composition/stacked-amount/delta-comparison` | 行或系列 `emphasis:true`；系列可指定 `color` | 突出当前比较对象或组成，其余保留为背景 |
| `gantt/before-after` | 行 `emphasis:true`，可选 `color` | 突出关键区间或前后变化 |
| `trend-reference` | `gap:{"series":"方案名","reference":"目标名","index":3,"unit":"F1"}` | 在指定点与参考值之间画括号，自动计算“当前 − 参考”；`index` 默认末点，支持 `display_scale` |
| `timeline` | 事件 `emphasis:true` | 用强调色和较大的节点标记关键事件 |
| `bar` | 顶层 `focus:["类别名称"]` | 突出这些类别，其余柱作为灰色背景；默认收紧柱宽，小数据集就近标值 |
| `bar/line/scatter/trend-reference` | 数据系列 `emphasis:true`；可选 `color` | 有重点系列时其余系列用灰色；选中系列保留自己的颜色。跨图可指定同一颜色 |
| `line/trend-reference` | 顶层 `label_indices:[0,3]`；或 `show_values:true/false` | 选择当前问题需要的点值；默认标末点。该字段只控制标注，全部数据仍参与绘制 |

`colors.json` 是名称到颜色的对象，例如 `{"当前方案":"#28679b","基线":"#187e75"}`，也可直接在图源中填 `color_map`。同一份配置供各图复用；多面板会传入子图，单个系列的 `color` 优先。配置作用于普通数据系列、堆叠与差值系列、甘特和前后对照的行标签。

`color` 使用本项目六种类别色之一：`#28679b`、`#187e75`、`#96703a`、`#8668a4`、`#b75654`、`#667b90`。重点依据写作目的与材料确定；需要平等比较时，保持默认的同等突出。组成图的分隔保留原始比例；趋势图将名称和值放在末端附近，密集末端用引线对应，更多系列使用图例或拆成多面板。

例如，在已有流程的关键节点与对应边加 `"emphasis":true`；比较方案乙时在柱状图顶层填 `"focus":["方案乙"]`。图的标题写出材料支持的发现，单位、必要条件与来源保留在相应位置。

模板、拆分或参数调整仍无法表达时，在任务目录定制绘制，优先复用 `canvas.py`，并在图文自查记录中说明缺少的表达能力。

## 样例与自检

```sh
python3 SKILL_DIR/scripts/draw.py --gallery ./figure-gallery
python3 -B SKILL_DIR/scripts/test_draw.py
```

SVG 可用于支持矢量图的输出位置；PNG 预览使用 macOS Quick Look 和 Pillow，其他系统使用已有 SVG 渲染工具。最终按目标文档的阅读宽度查看：首先看到的是否是重点，关系是否直接可见，标签是否容易对应；画面比例、间距、对齐、字号和配色是否协调。调整后重新渲染、查看，再写检查结论。

## 兼容已有图源

使用 `template` 名称可直接选择布局；维护已有 `type` 图源时，使用以下对应关系：

`set-overlap` 对应 `sets`；`responsibility-matrix` 对应 `matrix`；两种堆叠模板对应 `stacked`；`delta-comparison` 对应 `delta`；`trend-reference` 对应 `trend`；两种多面板模板对应 `panels`；`stat-card` 对应 `stat`，`target-meter` 对应 `meter`，`horizontal-bar` 对应 `bar`。

`grouped-flow` 对应 `grouped`，两种对齐模板对应 `aligned`，`overview-detail` 对应 `detail`。
