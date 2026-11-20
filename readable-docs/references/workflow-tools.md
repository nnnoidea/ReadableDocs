# 过程文件工具

`workspace.py` 负责切章、汇总、保存快照、生成差异和交付索引。Agent 按主 Skill 完成四阶段判断，修改后重新读取、查看实际图示，再写复查结论。

## 1. 准备任务目录

在任务目录的 `source/draft.md` 中保存完整初稿：目的、读者、限制在前，用 `# 文档草稿` 分隔正文，正文以 `##` 划分章节，章内使用更低级标题。

后续文件各自承担以下用途：

```text
task/
  source/
    draft.md             # 初稿，完成后保留
    brief.md             # 当前写作依据
    intro.md             # 仅标题或空文件
    01.md, 02.md, …       # 当前章节正文，实际修改位置
    chapters.json        # 章节顺序、标题和文件；可填写 sources 来源
    document.md          # 从当前章节汇总的正文
    figures/             # 图源和生成图
    data/                # 共享绘图数据，如有
  review.md              # 按阶段、章节记录检查与输出回查
  stages/                # 全稿快照：当时的稿件与资源副本
  pairs/                 # 章节改写前后快照及后续修订
  index.md               # 自动生成的交付索引
```

所需图源、截图、附件和数据保存在 `source/` 内。图和附件在使用处写完整的相对链接，例如 `![概览](figures/overview.svg)`，让各章可以独立解析。正文来源在写作时确认，可填入 `chapters.json` 各章的 `sources` 数组。

以下命令从任务目录执行，`SKILL_DIR` 替换为本 Skill 的实际路径。

## 2. 切章并保存初稿

完整初稿保存后执行：

```sh
python3 SKILL_DIR/scripts/workspace.py split source/draft.md
python3 SKILL_DIR/scripts/workspace.py snapshot source stages/01-text-initial
```

`split` 生成写作依据、章节文件和章节清单；有实质正文的开篇独立成为 `00.md`，同样纳入检查。代码块内的标题保留在原章。

`snapshot` 先将当前章节汇总成 `document.md`，再保存整个源稿包及文件哈希。快照使用新目录名，后续修改保留原版本。

从此，正文直接局部修改章节文件，依据更新到 `brief.md`。只需汇总全文时执行：

```sh
python3 SKILL_DIR/scripts/workspace.py assemble source
```

## 3. 检查文字并保存定稿

按主 Skill 逐章检查、修改和复读，在 `review.md` 中使用文字自查表。全部章节完成后汇总正文，进行整体文字复查；相关修改仍落实到章节文件。通过后保存文字定稿：

```sh
python3 SKILL_DIR/scripts/workspace.py snapshot source stages/02-text-final
```

## 4. 逐章画图并保存配对

每章改写前保存 `before`，图示和配文完成后保存 `after`：

```sh
python3 SKILL_DIR/scripts/workspace.py pair source 01 pairs --stage before
# 在 source/ 中画图、改写第 01 章并保存。
python3 SKILL_DIR/scripts/workspace.py pair source 01 pairs --stage after
```

配对快照保存该章、写作依据、引用资源、图片同名的 JSON/Python/SVG/PNG，以及共享 `data/`、`colors.json`、`document.css`。定制绘图的额外依赖放在 `data/`，或显式保存在对应快照中。工具同时生成 `pairs/01/after.diff`。

全部章节改写完成后保存完整图文初稿，再进入图文逐章检查：

```sh
python3 SKILL_DIR/scripts/workspace.py snapshot source stages/03-illustrated-initial
```

## 5. 检查图文并保留修订

逐章读取原配对稿、查看实际图示，将发现写入 `review.md` 的图文自查表。需要修改时，在当前章节和图源中修改、重新生成图，再保存新的修订快照：

```sh
python3 SKILL_DIR/scripts/workspace.py pair source 01 pairs --stage rev01
```

重新读取修订结果、查看更新后的图，再填写结论。再次修改使用 `rev02` 等新名称。保留文字的理由写在“配文作用”项，定制图原因写在“图示表达”项；后续检查引用已有依据，补充新发现、实际变化及本轮复查结果。

修订差异默认对照初始 `after`。需要比较相邻两轮时执行：

```sh
python3 SKILL_DIR/scripts/workspace.py diff pairs/01/rev01 pairs/01/rev02 --output pairs/01/rev02-vs-rev01.diff
```

各章通过后汇总，进行整体图文复查，重点核对跨章衔接、重复、遗漏、事实一致性与整体视觉效果。新修改继续保存修订、复读和看图；整体通过后保存最终快照：

```sh
python3 SKILL_DIR/scripts/workspace.py snapshot source stages/04-illustrated-final
```

## 6. 输出与交付索引

按[源稿包与交付](delivery.md)生成文档并完成对应检查，将结果记入 `review.md`。

完成后生成交付索引，直接链接正文、写作依据和检查记录：

```sh
python3 SKILL_DIR/scripts/workspace.py index source index.md --review review.md
```

索引读取章节清单及已有 `sources`，按原值列出来源。文件对应关系与差异由工具生成；内容判断保留在实际检查发生的位置。
