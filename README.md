# xju-thesis-md2docx-native

新疆大学本科毕业论文（设计）`Markdown -> DOCX` 原生版导出工具。

这个项目从 `xju-thesis-md2docx` 迁移而来，但导出方式已经改变：它不再读取、复制、替换学校 Word 模板包，而是直接生成一个新的 OOXML `docx` 文件。这样更适合后续封装成独立开源项目，也方便继续扩展 Word、LibreOffice、PDF 预览等多后端流程。

## 功能概览

- [x] 从 Markdown 主稿生成原生 OOXML DOCX
- [x] 自动生成封面、声明、中英文摘要、目录域和正文
- [x] 生成自有 Word 样式：正文、标题、题注、参考文献、代码块、公式块、表格文字
- [x] 写入基础节属性、正文页眉和页脚页码
- [x] 支持一级到三级标题、参考文献、致谢和附录
- [x] 支持单图、并排图、Markdown 管道表格和长表拆分标记
- [x] 支持 LaTeX 公式转 Word 原生 OMML；依赖缺失时保底写入 LaTeX 文本
- [x] 支持 WSL + Windows Microsoft Word 导出 PDF 预览

## 与模板版的区别

模板版的核心思路是“拿学校 DOCX 模板作为底座，再替换其中的文档内容”。原生版的核心思路是“从零写入标准 DOCX 包结构”。

原生版会直接生成这些主要部件：

- `[Content_Types].xml`
- `_rels/.rels`
- `docProps/core.xml`
- `docProps/app.xml`
- `word/document.xml`
- `word/styles.xml`
- `word/settings.xml`
- `word/fontTable.xml`
- `word/header1.xml`
- `word/footer1.xml`
- `word/_rels/document.xml.rels`
- `word/media/*`

因此它不依赖 `xju-template.docx`，也不会携带模板中的隐藏样式、历史关系、修订痕迹或复杂 Word 私有状态。代价是：学校模板中非常细的人工版式细节，需要逐步在原生样式和节属性里补齐。

## 安装

### 最小依赖

```bash
cd xju-thesis-md2docx-native
python3 -m pip install -r requirements.txt
```

最小依赖可以完成正文、封面、图片、表格和目录域导出。公式会在依赖缺失时保留为 LaTeX 文本，并打印 warning。

### 公式依赖

如果希望公式尽量转成 Word 原生公式：

```bash
cd xju-thesis-md2docx-native/xju_thesis_md2docx_native/world-math
npm install
```

公式转换 helper 使用 Node.js。这里不自动联网安装依赖，避免导出过程被网络或代理问题卡住。

## 快速开始

运行示例：

```bash
cd xju-thesis-md2docx-native
bash demo.sh
```

生成文件：

```text
example/thesis-demo.generated.docx
```

导出自己的论文：

```bash
python3 xju_thesis_md2docx_native.py thesis.md thesis.docx
```

如果不写输出路径，默认生成同名 `.docx`：

```bash
python3 xju_thesis_md2docx_native.py thesis.md
```

常用参数：

```bash
python3 xju_thesis_md2docx_native.py thesis.md thesis.docx --assets-dir path/to/cover-assets
python3 xju_thesis_md2docx_native.py thesis.md thesis.docx --no-cover-assets
python3 xju_thesis_md2docx_native.py thesis.md thesis.docx --no-formula-conversion
```

默认封面资源在：

```text
xju_thesis_md2docx_native/resources/
```

也可以在 Markdown 同级目录下放：

```text
img/cover-assets/xju-emblem.jpeg
img/cover-assets/xju-wordmark.png
```

## 生成 PDF 预览

如果在 WSL 中运行，且 Windows 主机安装了 Microsoft Word，可以使用内置的 Word 后端导出 PDF：

```bash
bash tools/word-docx2pdf/doctor.sh
python3 xju_thesis_md2docx_native.py example/thesis-demo.md example/thesis-demo.generated.docx
bash tools/word-docx2pdf/docx2pdf.sh example/thesis-demo.generated.docx example/thesis-demo.generated.pdf
```

这个后端默认使用运行时临时目录，不依赖本仓库的绝对路径。确实需要指定 Windows 临时目录时，可以给 `docx2pdf.sh` 传 `--tmp-root`。

PDF 渲染成图片后，AI 或人工可以直接检查 Word 样式效果：

```bash
mkdir -p example/preview/thesis-demo
pdftoppm -png -f 1 -l 6 -r 120 \
  example/thesis-demo.generated.pdf \
  example/preview/thesis-demo/page
```

`example/preview/` 是生成物，默认被 `.gitignore` 忽略。

## Markdown 结构

推荐结构：

```markdown
# 论文题目

## 封面信息
论文题目：你的论文题目
学生姓名：张三
学号：2022xxxxxx
所属院系：某某学院
专业：某某专业
班级：某某班
指导教师：某某老师
日期：2026 年 4 月

---

## 声明
声明正文。

作者签名：__________
签字日期：__________

---

## 摘要
中文摘要正文。

关键词：关键词1；关键词2；关键词3

---

## ABSTRACT
English abstract.

KEY WORDS: Keyword one; Keyword two; Keyword three

---

## 目录
这里可以放占位文字；导出器会写入 Word 目录域。

---

# 1 绪论
## 1.1 研究背景
正文。

# 参考文献
[1] 作者. 文献题名[文献类型]. 出版信息.

# 致谢
致谢正文。

# 附录
## 附录 A 附加材料
附录正文。
```

正文必须从第一个编号一级标题开始，例如 `# 1 绪论`。前置部分用二级标题组织。

## 当前边界

- 目录是 Word 域，最终提交前仍建议在 Word / WPS 中刷新目录和页码。
- 页眉、页脚、标题、正文、题注、表格和参考文献已有原生样式，但还不是学校模板的逐像素复刻。
- 不处理任务书、评议书、答辩委员会意见等过程性材料合并。
- 不校验参考文献真实性，也不自动改写 GB/T 7714 条目。
- 不支持复杂 Word 手工排版对象，例如脚注、尾注、自动交叉题注、复杂浮动图文混排。

## 项目结构

```text
xju-thesis-md2docx-native/
├── xju_thesis_md2docx_native.py
├── xju_thesis_md2docx_native/
│   ├── main.py
│   ├── resources/
│   └── world-math/
├── example/
├── tools/
│   └── word-docx2pdf/
├── demo.sh
└── README.md
```
