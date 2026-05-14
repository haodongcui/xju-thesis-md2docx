# Profile Development

Profile 是学校、学位和文档格式规则的边界。通用层负责 Markdown 扫描、图片、公式、表格和 DOCX 打包；profile 负责解释这些元素在某个论文格式中的含义。

## Profile 需要定义什么

新增一个学校或学位格式时，建议新建：

```text
thesis_md2docx/profiles/<school_degree_thesis>/
├── __init__.py
├── profile.py
├── body.py
├── document.py
├── frontmatter.py
├── styles.py
├── header_footer.py
└── format_requirements/
```

最少需要实现：

- `profile.py`：定义 `ThesisProfile` 子类，并在 `profiles/registry.py` 注册。
- `document.py`：定义封面、声明、摘要、目录、正文、致谢、附录等文档结构。
- `frontmatter.py`：定义封面、声明、任务书、摘要、关键词等前置页渲染。
- `body.py`：定义正文标题、参考文献、附录、图表题、公式编号等规则。
- `styles.py`：定义 Word 样式目录、样式角色映射、编号、字体表等。
- `header_footer.py`：定义该 profile 的页眉页脚。
- `format_requirements/`：保存学校格式文件或说明，作为 profile 维护依据。

Profile 还应显式提供：

- `front_matter_spec()`：前置页 key、标题文字、摘要关键词前缀。
- `document_layout()`：封面、前置页、正文起始、正文延续等分节规则。
- `style_catalog()`：结构化声明 Word 样式，包括正文、标题、目录、图表题、参考文献、页眉页脚等。
- `style_roles()`：把通用语义角色映射到具体 Word 样式 ID，例如 `body.normal -> XjuBody`。
- `style_bundle()`：styles、numbering、settings、font table、页眉页脚。
- `package_parts()`：DOCX 包内各 XML 部件路径；默认使用标准 Word 路径。

## 通用层和 profile 的边界

通用层可以处理：

- Markdown 段落、标题、代码块、公式块、图片、表格。
- 将 Markdown 正文解析为 `HeadingBlock`、`ParagraphBlock`、`TableBlock`、`ImageBlock` 等 IR block。
- 行内公式、行内代码、加粗、斜体、参考文献跳转。
- DOCX zip 包结构、媒体文件关系、PDF 后端调用。

Profile 应该处理：

- 哪些前置部分存在，例如封面、声明、任务书、摘要、目录。
- Markdown 前置部分 key 与最终显示标题的映射。
- 正文从哪个标题开始。
- 哪些标题不编号，例如参考文献、致谢、附录。
- 章节、附录、公式、图、表的编号规则。
- 正文、标题、图表题、参考文献、页眉页脚、目录样式。
- 页面尺寸、页边距、分节、页码格式。
- 学校或学位专用封面字段和固定文本。

当前 XJU profile 已经把封面、前置页、页眉页脚、样式 ID、编号和字体表都放回 profile 内。通用层不应该直接出现 `XjuBody`、`XjuHeading1` 这类学校专用样式名。

## 转换链路

整体链路如下：

```text
Markdown 文件
  -> parse_markdown_document()
  -> front sections + body text
  -> parse_body_blocks()
  -> IR blocks
  -> build_document_blocks()
  -> profile document/frontmatter/body/styles/layout
  -> OOXML parts
  -> DOCX zip
  -> PDF backend（可选）
```

职责划分：

- `markdown.py`：切分标题、前置部分和正文。
- `parser.py`：把正文 Markdown 扫描成 `HeadingBlock`、`ParagraphBlock`、`TableBlock` 等 IR。
- `ir.py`：定义中间结构，尽量不包含学校样式细节。
- `builders/document.py`：通用正文 IR 到 OOXML 的调度器，通过 profile hook 渲染特殊格式。
- `ooxml/`：提供段落、表格、图片、字段、包部件等基础 OOXML 构造。
- `profiles/<name>/`：决定某个学校/学位格式到底怎样排版。
- `pdf/`：负责 DOCX 到 PDF，不影响 DOCX 生成逻辑。

## 样式体系

样式要按“语义角色”组织，不要让通用正文渲染器直接依赖某个学校的样式 ID。推荐分成三层：

- `StyleCatalog`：声明 Word 样式本身，例如 `XjuBody`、`XjuHeading1`、`XjuReference`。
- `StyleRoleMap`：声明语义角色到样式 ID 的映射，例如 `body.heading.level1 -> XjuHeading1`。
- `StyleBundle`：把 catalog 和其他 DOCX 部件输出成最终 `styles.xml`、`numbering.xml`、`fontTable.xml` 等。

新增 profile 时至少要覆盖这些语义角色：

- `body.normal`
- `body.heading.level1`
- `body.heading.level2`
- `body.heading.level3`
- `front.heading`
- `toc.field`
- `caption.default`
- `reference.item`
- `table.cell`
- `math.block`
- `header.default`
- `footer.default`

样式、布局和渲染规则要分清楚：字体字号、缩进、行距属于样式；页边距、分节、页码属于布局；图片缩放、表格列宽、公式编号属于渲染规则。

`md2docx doctor` 会校验默认 profile 的样式目录和角色映射，能提前发现：

- 重复的 style id；
- `basedOn` 或 `next` 指向不存在的样式；
- 语义角色指向未声明的样式。

## 正文解析规则

正文语义规则由 `BodyParseRules` 描述。不同学校通常需要调整：

- `reference_heading`
- `acknowledgement_heading`
- `appendix_heading`
- `unnumbered_headings`
- `reference_entry_pattern`
- `caption_pattern`
- `table_caption_prefixes`
- `chapter_number_pattern`

例如 XJU 本科论文的规则放在：

```text
thesis_md2docx/profiles/xju_undergraduate_thesis/body.py
```

## 渲染 Hook

`body_style_profile()` 返回的字典可以提供渲染 hook：

- `heading_builder`
- `acknowledgement_heading_builder`
- `caption_builder`
- `reference_builder`
- `table_builder`
- `appendix_heading_normalizer`
- `appendix_reference_normalizer`
- `section_pr_builder`

这些 hook 让通用正文构建器不需要知道具体学校规则。

## 当前限制

当前 profile 机制优先服务“毕业论文”扩展。它适合新增其他学校、本科、硕士、博士论文格式。项目已经引入轻量 IR 和结构化样式层；如果要扩展到简历、合同、标书、报告等任意 Word 文档，后续还需要继续抽象 front matter、封面页、特殊页面和动态对象布局。

## AST / IR 是什么

AST 是 Abstract Syntax Tree，抽象语法树；IR 是 Intermediate Representation，中间表示。这里的作用是让转换链路分成两步：

```text
Markdown 文本 -> IR blocks -> profile/layout 渲染 -> DOCX OOXML
```

IR block 不关心最终 Word 样式，只表达文档结构。例如：

- `HeadingBlock`
- `ParagraphBlock`
- `ImageBlock`
- `FigureRowBlock`
- `TableBlock`
- `MathBlock`
- `PageBreakBlock`

这样新增格式时，可以复用 Markdown 解析结果，只重写 profile/layout 规则。
