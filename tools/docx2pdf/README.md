# docx2pdf

统一的 DOCX 转 PDF 后端调度入口。

```bash
bash tools/docx2pdf/docx2pdf.sh --backend word thesis.docx thesis.pdf
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice thesis.docx thesis.pdf
bash tools/docx2pdf/docx2pdf.sh --backend auto thesis.docx thesis.pdf
```

## 后端选择

| 后端 | 适用场景 | 主要依赖 | 版式保真度 |
| --- | --- | --- | --- |
| `word` | WSL + Windows Word，本机最终预览 | Windows Microsoft Word | 最高，最接近 Word 打开效果 |
| `libreoffice` | Linux/CI/无 Word 快速预览 | LibreOffice | 中等，可能与 Word 分页和字体不同 |
| `auto` | 自动选择可用后端 | Word 或 LibreOffice | 优先 Word，否则 LibreOffice |

默认后端是 `word`。也可以通过环境变量修改：

```bash
XJU_DOCX2PDF_BACKEND=libreoffice \
  bash tools/docx2pdf/docx2pdf.sh thesis.docx thesis.pdf
```

后端特有参数会原样传给后端脚本：

```bash
bash tools/docx2pdf/docx2pdf.sh --backend word thesis.docx thesis.pdf --no-update-fields
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice thesis.docx thesis.pdf --keep-tmp
```
