# libreoffice-docx2pdf

兼容入口。实际 LibreOffice 后端实现已经移动到：

```text
tools/docx2pdf/backends/libreoffice/
```

建议使用统一入口：

```bash
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice thesis.docx thesis.pdf
```
