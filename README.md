# xju-thesis-md2docx

新疆大学本科毕业论文（设计）`Markdown -> DOCX` 格式转换工具。

本项目面向希望用 Markdown 维护论文主稿、再导出为学校格式 Word 文档的写作流程。当前实现不依赖 Word 模板包替换，而是直接生成原生 OOXML `docx` 文件，并提供可选的 DOCX 转 PDF 后端，方便检查分页、目录、公式、图表和整体版式。

## 功能

- 从 Markdown 主稿生成新疆大学本科毕业论文（设计）DOCX。
- 自动生成封面、原创性声明、任务书、中英文摘要、目录域、正文、参考文献、致谢和附录。
- 写入学校论文格式所需的页面边距、页眉页脚、页码、标题、正文、题注、表格、公式和参考文献样式。
- 正文章节使用 Word 原生编号，不把章节号硬编码进标题文本。
- 支持一级到三级标题、行内公式、块公式、Markdown 管道表格、长表拆分、单图、并排图、引用块和代码块。
- 支持 LaTeX 公式转换为 Word 原生 OMML；依赖缺失时保留 LaTeX 文本并给出 warning。
- 可选调用 Windows Microsoft Word 或 LibreOffice 将 DOCX 导出为 PDF，用于人工或 AI 预览排版效果。

## 适用范围

适合：

- 新疆大学本科毕业论文（设计）正文写作和反复导出。
- 希望把论文源文件纳入 Git 版本管理的场景。
- 希望由 AI 修改 Markdown，并通过生成 PDF 图片检查 Word 版式效果的流程。
- 需要一个无需学校 DOCX 模板包替换的开源实现。

不适合：

- 完全跳过 Word / WPS 最终检查后直接提交。
- 复杂浮动对象、脚注尾注、修订痕迹、自动交叉题注等深度 Word 排版场景。
- 评议书、答辩委员会意见等过程性材料的整包合并。

## 安装

### Python 依赖

```bash
git clone https://github.com/<your-name>/xju-thesis-md2docx.git
cd xju-thesis-md2docx
python3 -m pip install -r requirements.txt
```

最小依赖只需要 Python 和 Pillow，可以完成正文、封面、图片、表格、目录域和基础公式文本导出。

### 公式转换依赖

如果希望 LaTeX 公式尽量转换为 Word 原生公式，需要安装 Node.js 依赖：

```bash
cd xju_thesis_md2docx/world-math
npm install
```

公式依赖是可选项。没有安装时，导出不会失败，公式会以 LaTeX 文本形式写入 Word，并在命令行提示 warning。

### PDF 预览依赖

PDF 预览不是生成 DOCX 的必要条件。当前支持两个后端：

| 后端 | 适用环境 | 特点 |
| --- | --- | --- |
| `word` | WSL + Windows Microsoft Word | 默认高保真后端，最接近 Word 打开效果 |
| `libreoffice` | Linux / WSL / CI | 不依赖 Word，更通用，但版式可能与 Word 有差异 |

Word 后端诊断：

```bash
bash tools/word-docx2pdf/doctor.sh
```

LibreOffice 后端诊断：

```bash
bash tools/libreoffice-docx2pdf/doctor.sh
```

Ubuntu / Debian 可安装 LibreOffice：

```bash
sudo apt-get update
sudo apt-get install -y libreoffice
```

两个后端都不需要 Docker，也不需要 `docker pull`。

## 快速开始

运行内置示例：

```bash
bash demo.sh
```

生成文件：

```text
example/thesis-demo.generated.docx
```

导出自己的论文：

```bash
python3 xju_thesis_md2docx.py thesis.md thesis.docx
```

如果不传输出路径，默认生成同名 `.docx`：

```bash
python3 xju_thesis_md2docx.py thesis.md
```

常用参数：

```bash
python3 xju_thesis_md2docx.py thesis.md thesis.docx --assets-dir path/to/cover-assets
python3 xju_thesis_md2docx.py thesis.md thesis.docx --no-cover-assets
python3 xju_thesis_md2docx.py thesis.md thesis.docx --no-formula-conversion
```

封面默认使用仓库内置资源：

```text
xju_thesis_md2docx/resources/xju-emblem.jpeg
xju_thesis_md2docx/resources/xju-wordmark.png
```

也可以在论文 Markdown 同级目录下放置本地资源，优先覆盖默认封面图：

```text
img/cover-assets/xju-emblem.jpeg
img/cover-assets/xju-wordmark.png
```

## PDF 预览

生成 DOCX 后，可以继续导出 PDF：

```bash
python3 xju_thesis_md2docx.py example/thesis-demo.md example/thesis-demo.generated.docx
bash tools/docx2pdf/docx2pdf.sh --backend word example/thesis-demo.generated.docx example/thesis-demo.generated.pdf
```

使用 LibreOffice 后端：

```bash
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice example/thesis-demo.generated.docx example/thesis-demo.generated.pdf
```

如果要让 AI 或人工逐页检查版式，可以把 PDF 渲染成图片：

```bash
mkdir -p example/preview/thesis-demo
pdftoppm -png -f 1 -l 6 -r 120 \
  example/thesis-demo.generated.pdf \
  example/preview/thesis-demo/page
```

`tools/docx2pdf/` 是统一调度入口；`tools/word-docx2pdf/` 和 `tools/libreoffice-docx2pdf/` 是独立后端。Word 后端默认使用 Windows 临时目录，不依赖本仓库或个人电脑的绝对路径。确实需要指定临时目录时，可以使用：

```bash
bash tools/docx2pdf/docx2pdf.sh --backend word thesis.docx thesis.pdf --tmp-root /mnt/c/Temp/xju-word-docx2pdf
```

格式验收建议以 `word` 后端为准；`libreoffice` 后端更适合无 Word 环境下快速预览。

## Markdown 结构

推荐从 `example/thesis-demo.md` 复制结构，再替换为自己的论文内容。核心结构如下：

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

## 任务书
届：2026
工作开始日期：2026 年 3 月 1 日
工作结束日期：2026 年 5 月 20 日
目的及意义：任务书中的目的及意义。
主要工作任务：任务书中的主要工作任务。
教研室主任：
接受任务日期：

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
### 1.1.1 三级标题示例
正文。

# 参考文献
[1] 作者. 文献题名[文献类型]. 出版信息.

# 致谢
致谢正文。

# 附录
## 附录 A 附加材料
附录正文。
```

约定：

- 正文从第一个编号一级标题开始，例如 `# 1 绪论`。
- 前置部分使用二级标题组织，例如 `## 封面信息`、`## 摘要`。
- 图题、表题建议单独成行，例如 `图 2-1 xxx`、`表 2-1 xxx`。
- 正文引用写作 `[1]`、`[1-3]`、`[1，3-4]`，导出器会尽量生成上标和文末跳转。
- 长表可以在表题和表格之间写 `<!-- xju-table-split: 8, 10 -->`，按数据行拆分续表。
- 并排图使用 `:::figure-row` 容器，见示例文件。

更多写法见：

- `example/README.md`
- `example/thesis-demo.md`
- `tools/word-docx2pdf/README.md`

## 格式对齐状态

当前实现已经按新疆大学本科毕业论文（设计）规范和范例重点对齐以下内容：

- A4 页面、页边距、页眉页脚、正文页码；
- 封面、声明、任务书、中英文摘要、目录、正文、参考文献、致谢、附录的文档顺序；
- 一级、二级、三级标题的字体、字号、缩进、段前段后和目录级别；
- 正文段落小四宋体、首行缩进两字符、1.5 倍行距；
- 图题、表题、表格文字、参考文献悬挂缩进；
- 公式块编号、常见 `\hat{}`、`\bar{}` 重音公式后处理；
- 正文参考文献引用上标和链接。

仍建议最终提交前人工检查：

- 在 Word / WPS 中刷新目录域和页码；
- 检查分页、孤行、图片位置、表格跨页和公式显示；
- 按学院或指导教师的额外要求调整非统一部分；
- 核对参考文献真实性和 GB/T 7714 细节。

## 项目结构

```text
xju-thesis-md2docx/
├── xju_thesis_md2docx.py              # 公开入口
├── xju_thesis_md2docx/
│   ├── main.py                        # 原生 OOXML 导出器
│   ├── resources/                     # 默认封面资源
│   └── world-math/                    # LaTeX -> OMML helper
├── example/
│   ├── README.md
│   ├── thesis-demo.md
│   └── img/
├── tools/
│   ├── docx2pdf/                      # PDF 后端统一入口
│   ├── word-docx2pdf/                 # WSL + Windows Word PDF 后端
│   └── libreoffice-docx2pdf/          # LibreOffice PDF 后端
├── demo.sh
├── requirements.txt
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## 开发与贡献

本项目以 Markdown 为源文件，DOCX/PDF 是生成物。提交改动时建议：

```bash
python3 -m py_compile xju_thesis_md2docx/main.py
bash demo.sh
```

如果修改了 PDF 后端，在 WSL + Word 环境下再运行：

```bash
bash tools/word-docx2pdf/doctor.sh
bash tools/docx2pdf/docx2pdf.sh --backend word example/thesis-demo.generated.docx example/thesis-demo.generated.pdf
```

如果修改了 LibreOffice 后端，再运行：

```bash
bash tools/libreoffice-docx2pdf/doctor.sh
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice example/thesis-demo.generated.docx example/thesis-demo.generated.pdf
```

欢迎围绕以下方向贡献：

- 更完整的学校格式细节对齐；
- LibreOffice / OnlyOffice 等可选 PDF 后端；
- 更稳健的公式、图表、引用和附录处理；
- 更小、更清晰的示例和测试文档。

更详细的提交约定见 `CONTRIBUTING.md`。

## License

MIT
