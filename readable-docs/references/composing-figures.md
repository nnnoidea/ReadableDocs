# 组合布局与视觉组件

组合布局安排多组信息的位置和对应关系；视觉组件用图形表示对象或动作。先按阅读问题选择布局，再填写对象、连接和该布局需要的内容，最后生成图示。

## 1. 选择布局

| 阅读问题 | 模板 | 内容组织方式 |
| --- | --- | --- |
| 哪些对象属于同一部分，各部分怎样连接 | `grouped-flow` | 区域内放对象，连线可以在组内或跨组 |
| 不同对象怎样分别完成相同步骤 | `aligned-process` | 每列一个对象，每行同一步骤，同列步骤相连 |
| 两种结构、机制或操作有什么不同 | `structure-comparison` | 每列一个对象，同一行比较同一方面 |
| 总览中的某部分具体怎样工作 | `overview-detail` | 总览保留主线，虚线连接对象与其局部解释 |

## 2. 填写对象

对象可以是实体、材料或动作。以下字段用于分组内的节点、对齐布局的列标题和单元格，以及总览对象：

| 字段 | 用途 |
| --- | --- |
| `label` | 对象或动作的名称 |
| `id` | 供连线或局部图引用的唯一标识；分组节点和总览对象必填 |
| `detail` | 必要短注，如有 |
| `symbol` | 表示含义的图形，见下表；省略时直接呈现文字对象 |
| `presentation` | `card`（默认）：小图标与文字放在一起；`symbol`：较大图形在上、标签在下 |
| `emphasis` | `true` 突出当前阅读重点 |
| `color` | 使用[统一调色板](drawing.md)中的颜色 |

`symbol` 按对象或动作的含义选择：

| 取值 | 含义 |
| --- | --- |
| `object` | 一个对象或实体 |
| `collection` | 一组对象、样本或材料 |
| `document` | 文档、记录或输入输出文件 |
| `store` | 存储、资料库、已有数据 |
| `search` | 查找、检索或核对 |
| `process` | 处理、转换或执行 |
| `filter` | 筛选满足条件的部分 |
| `decision` | 判断或条件检查 |
| `result` | 结果；用 `status:"neutral"`（默认）、`"pass"`、`"fail"` 明确普通结果、通过或未通过 |

例如，一个需要突出的核对动作可以写为：

```json
{"id":"review", "label":"核对材料", "detail":"只核对本轮新增内容",
 "symbol":"search", "presentation":"symbol", "emphasis":true}
```

文字自动换行，单元格和同行高度随内容增长。组件也可用于已有 `flow/hierarchy/state` 的节点。

需要区分对象身份时，`symbol:"object"` 可配 `shape:"circle"`、`"square"`、`"diamond"` 或 `"hexagon"`。同一对象跨图沿用相同的名称、形状和颜色。顶层 `color_map` 按对象 ID 或名称提供共享配色，单个对象的 `color` 优先。

图形表示含义，标签说明具体对象。集合图标中的叠片表示“集合”，真实数量由数据图或数值标注表达；分组底色表示范围，强调色表示重点。对象身份、判断条件等符号用途在必要时用图例或邻近短注解释。

## 3. 填写连接

连接填写在 `edges` 中：`from` 和 `to` 引用对象 ID，`label` 说明关系或条件。默认使用箭头；无方向的关联填 `directed:false`。

可用 `emphasis`、`color` 和 `dash` 设置重点、颜色和虚线。反馈边填写 `feedback:true`，供布局识别回路。虚实线与颜色的含义在同一图中保持一致。

```json
{"from":"review", "to":"edit", "label":"需补充材料",
 "feedback":true, "dash":true}
```

布局自动选择连接点，绕开节点，并在边界外留出转折距离；标签避开节点和已有连线。需要调整连接方向时，`from_side/to_side` 可指定 `left/right/top/bottom`。图过密时，按说明点拆分或明确业务阶段。

已有流程图也使用这套连接能力，`direction:"horizontal"` 支持横向分支和汇合。

## 4. 按布局组织内容

### 分组连接：`grouped-flow`

`groups` 列出分组，每组包含 `label` 和 `nodes`。节点 ID 在全图唯一，顶层 `edges` 可连接任意两个节点。`columns` 指定每行排几个分组，支持 1–3。

默认按组内前置关系排列：前置节点在上，平行节点并列，汇合节点在下；反馈边单独作为回路。需要明确业务阶段时，在分组中填写 `rows:[["a"],["b","c"],["d"]]`，每个节点恰好出现一次。

### 共同步骤与结构对照

`columns` 填 2–4 个对象。`rows` 中每行包含方面或步骤名称 `label`，以及与列数一致的 `cells`。单元格可以是字符串或上述对象组件；缺项用 `null`，显示为“—”。

- `aligned-process` 默认 `connect_rows:true`，连接同列相邻且存在的单元格，缺项处中断路径。
- `structure-comparison` 默认 `connect_rows:false`，通过共同位置对应比较方面。

行的名称和顺序由说明目的决定，同一行处理同一步骤或比较同一方面。

### 总览与局部：`overview-detail`

`overview` 列出总览对象，顶层 `edges` 表示这些对象之间的实际关系。`details` 每项用 `target` 指向一个总览对象的 ID，用 `figure` 填写其局部图：

```json
{"target":"review", "figure":{
  "template":"flow", "title":"核对哪些材料",
  "nodes":[{"id":"a","label":"核对来源"},{"id":"b","label":"核对内容"}],
  "edges":[{"from":"a","to":"b"}]
}}
```

同一对象可以对应多个局部图。局部复用已有流程、关系、数据图或上述组合布局，并标明对应对象名称。虚线表示“该对象的展开”；执行关系由图内箭头表达。布局保留一层总览与局部，更多层次用独立图展开。

## 5. 生成并查看

`SKILL_DIR` 替换为本 Skill 的实际路径。读取选中模板，替换示例内容后生成 SVG：

```sh
python3 SKILL_DIR/scripts/draw.py --template grouped-flow > figure.json
# 填写实际对象、关系、条件和重点。
python3 SKILL_DIR/scripts/draw.py figure.json figure.svg
```

自行编写 JSON 时，`template` 选择布局，业务内容由实际字段提供。生成和预览命令、共用样式见[绘图模板与统一风格](drawing.md)。

按文档阅读宽度查看连接起止对象、分组边界、共同对齐行、总览与局部的对应，以及字号和间距。完整图文检查沿用主 Skill；修改后重新生成、查看，再填写复查结论。
