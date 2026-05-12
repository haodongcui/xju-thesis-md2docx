# 贡献指南

感谢关注 `xju-thesis-md2docx`。本项目的目标是把新疆大学本科毕业论文（设计）Markdown 主稿稳定导出为符合学校格式要求的 DOCX，并提供可检查的 PDF 预览流程。

## 基本原则

- Markdown 是源文件，DOCX/PDF 是生成物。
- 优先修导出器或 Markdown 示例，不建议把手工修改后的 DOCX 作为长期来源。
- 格式改动应尽量对齐学校规范和范例，避免只针对单篇论文做特殊处理。
- 新功能应保持可选和可回退，避免破坏已有论文导出。

## 本地检查

提交前建议至少运行：

```bash
python3 -m py_compile xju_thesis_md2docx/main.py
bash demo.sh
```

如果修改了公式转换或 PDF 预览相关代码，还建议运行：

```bash
bash tools/word-docx2pdf/doctor.sh
bash tools/docx2pdf/docx2pdf.sh --backend word example/thesis-demo.generated.docx example/thesis-demo.generated.pdf
```

如果修改了 LibreOffice 后端，还建议运行：

```bash
bash tools/libreoffice-docx2pdf/doctor.sh
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice example/thesis-demo.generated.docx example/thesis-demo.generated.pdf
```

## 提交内容

建议提交：

- `xju_thesis_md2docx/` 中的源码改动；
- `example/thesis-demo.md` 或 `example/README.md` 中的示例更新；
- `README.md`、`tools/word-docx2pdf/README.md` 等文档更新。

不建议提交：

- `example/*.generated.docx`；
- `example/*.generated.pdf`；
- `example/preview/`；
- `xju_thesis_md2docx/world-math/node_modules/`；
- 本地临时文件、缓存和手工备份文件。

## 格式类改动

如果改动标题、页边距、正文、图题、表题、参考文献、公式或目录相关逻辑，请在说明中写清楚：

- 修改前的问题；
- 对应的学校规范或范例位置；
- 导出后的检查方式；
- 是否会影响已有 Markdown 写法。
