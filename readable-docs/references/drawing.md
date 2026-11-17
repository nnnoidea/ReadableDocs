# 绘图模板与统一风格

先按[读者问题选图](choosing-figures.md)，再选下表的模板。优先填内容，由源码生成布局；模板无法准确表达时，再在任务目录定制绘制，并沿用本节风格。

## 选模板、填内容、渲染

`SKILL_DIR` 表示本 Skill 所在目录，执行时替换为实际路径。只需 Python 3 标准库即可生成 SVG。

```sh
python3 SKILL_DIR/scripts/draw.py --list
python3 SKILL_DIR/scripts/draw.py --template composition > figure.json
# 编辑 figure.json，填入实际内容后生成图
python3 SKILL_DIR/scripts/draw.py figure.json figure.svg
# macOS PNG 预览，需 Quick Look 与 Pillow
python3 SKILL_DIR/scripts/preview.py figure.svg figure.png
```

每个模板都是 `assets/templates/` 下的独立 JSON，只读取选中的模板。对象、数值、日期均是示例；替换标题、说明、数据和来源，按需增加或删除内容项，保留图型所需字段。生成器计算位置、连线、坐标和换行；输出后检查实际渲染及图文。

也可以写 `"template":"composition"` 并提供该图型的必要字段。这只选择布局，缺少内容时会报错，不会用示例数据补齐。`title`、`subtitle`、`caption` 通用于所有图型；`caption` 可写来源、单位或必要限定。

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
| 哪些组合更高、更低 | `heatmap` | `rows`、`columns`、二维数值 `values`、`unit` |
| 各部分占整体多少 | `composition` | `series` 名称；每行 `label/values`，按占比归一 |
| 总量与组成怎样变化 | `stacked-amount` | 同上；各条用相同数量刻度 |
| 相对基线有何收益与代价 | `delta-comparison` | `series`；各行基线说明与差值 `values`；`unit` |
| 趋势距离参考线多远 | `trend-reference` | 真实 `x`；`series` 的 `name/values`；参考 `label/value` |
| 多项指标分别距离目标多远 | `metric-reference` | `panels` 中各指标的数据、参考值、单位 |
| 同一问题需要多个观察角度 | `multi-panel` | `panels` 中各子图的完整内容；`columns` 为 1 或 2 |
| 单个整体的占比 | `pie` | `labels`、非负 `values`，总和为正 |
| 比较类别数值 | `bar` | `labels`、`values`；多组可用 `series` 的 `name/y` |
| 普通数值趋势 | `line` | 数值 `x`、`values`、`x_label/y_label` |
| 两个数值变量的关联 | `scatter` | 数值 `x`、`values`，每对值属于同一对象 |
| 数据集中在哪里 | `histogram` | 原始 `values`、分箱数 `bins`（默认 8，1–50） |
| 比较分布与离群值 | `boxplot` | `groups` 中的 `label/values` |

模板名是入口，JSON 的 `type` 是底层布局。`set-overlap` 对应 `sets`；`responsibility-matrix` 对应 `matrix`；两种堆叠模板对应 `stacked`；`delta-comparison` 对应 `delta`；`trend-reference` 对应 `trend`；两种多面板模板对应 `panels`。

## 数据与关系口径

- **包含图**：按 `children` 画嵌套框，框大小用于容纳内容，不编码数量。层次过深时拆成局部图。
- **交集图**：根据两个成员列表计算独有和交集。面积只表示集合关系；更多集合用对应矩阵表达。
- **映射图**：`links` 默认有箭头，`directed:false` 使用无向连线。连接密集或标签过多时用矩阵。
- **矩阵与热力图**：行、列和值维度相同。热力值为有限数或 `null`；`null` 显示缺失，0 是真实数值。跨零时颜色区分正负，深浅表示绝对值；其余情况颜色越深数值越大，图注给出口径。
- **时间线**：依次呈现输入事件，间距不表示持续时间。**甘特图**按实际时间定位，日期用 `YYYY-MM-DD`，或全部用同一单位的数字；结束等于开始表示里程碑。
- **堆叠图**：每行 `values` 与 `series` 同序。`normalize:true` 归一到 100%，总和须大于 0；`false` 使用共同数量刻度。均标原始值与总量，需填单位。
- **差值图**：输入按明确基线计算的差值，各行标签说明基线。默认模板 `display_scale:100` 将 0–1 分差转成百分点；普通差值用 1，并填写相应单位。
- **参考线趋势图**：`x` 严格递增，按真实间距绘制。参考值参与坐标范围计算；可填 `y_min/y_max`，范围必须覆盖所有点和参考线。`show_values` 控制点值标签；多点时默认简化。各面板轴范围分别标注。
- **多面板**：默认纵向排列，适合文档阅读；`columns:2` 可并排。子图各自有标题、单位和范围；相同尺度比较时显式填写一致的轴范围。每个子图采用本表内已有布局，层级为一层。
- **普通数据图**：`bar/line/scatter` 多组数据可用 `series:[{"name":"组名","x":[1,2],"y":[3,5]}]`。柱状图使用共同 `labels`；折线按输入顺序连接。直方图为等宽分箱，最后一组包含最大值；箱线图采用线性插值四分位数、1.5 IQR 须和单独离群点。

## ReadableDocs 风格

统一样式在 `scripts/canvas.py`：白底，深蓝灰正文，蓝与青绿为主要类别色，赭色用于参考或提醒；低对比网格、圆角浅底框、左侧细色条标题。字号、留白、换行和图注由共同画布处理。颜色用于区分信息，正负方向及条件同时用文字、位置或符号表达。

借鉴 Answer Me with HTML 按信息关系选择组件的组织方式；这些模板和布局由本项目实现，共用自己的画布与样式。选择模板、拆分说明点、调整图型或模板参数仍无法表达时，才在任务目录定制布局；优先复用 `canvas.py`，在自查记录中注明缺少的表达能力。

## 样例与自检

```sh
python3 SKILL_DIR/scripts/draw.py --gallery ./figure-gallery
python3 -B SKILL_DIR/scripts/test_draw.py
```

生成器保留旧版 `type` 输入方式。SVG 可用于支持矢量图的输出位置；PNG 预览使用 macOS Quick Look 和 Pillow，其他系统使用已有 SVG 渲染工具。最终还需检查目标文档中的显示宽度、标签和图文衔接。
