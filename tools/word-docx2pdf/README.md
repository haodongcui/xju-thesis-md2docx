# word-docx2pdf

兼容入口。实际 Word 后端实现已经移动到：

```text
tools/docx2pdf/backends/word/
```

建议使用统一入口：

```bash
bash tools/docx2pdf/docx2pdf.sh --backend word thesis.docx thesis.pdf
```
