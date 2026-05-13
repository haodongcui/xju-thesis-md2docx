# LibreOffice PDF backend

使用 LibreOffice headless 模式把 `docx` 导出为 `pdf`。

LibreOffice 后端的跨平台控制逻辑在 `xju_thesis_md2docx/pdf/libreoffice.py`。本目录保留字段刷新宏模板和 Linux/WSL 兼容 wrapper。

这个后端不依赖 Windows Microsoft Word，适合 Windows、Linux、WSL、本机无 Word 或 CI 环境中的基础 PDF 预览。但它使用的是 LibreOffice 的 DOCX 排版引擎，导出效果不保证与 Microsoft Word 完全一致。

默认情况下，脚本会先用临时 LibreOffice profile 打开文档，主动刷新目录/索引/文本域，然后再导出 PDF。这样可以避免纯 `--convert-to` 模式下目录为空或页码未刷新的问题。字段刷新和导出宏模板放在本目录的 `update_fields_and_export.xba`。

## 依赖

- LibreOffice / `soffice`
- 中文字体和 Times New Roman 兼容字体

Ubuntu / Debian 可安装：

```bash
sudo apt-get update
sudo apt-get install -y libreoffice
```

可先运行诊断：

```bash
bash tools/docx2pdf/backends/libreoffice/doctor.sh
```

## 用法

推荐通过统一入口调用：

```bash
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice thesis.docx
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice thesis.docx thesis.pdf
```

Windows PowerShell：

```powershell
.\xju.ps1 pdf thesis.docx thesis.pdf --backend libreoffice
.\tools\docx2pdf\docx2pdf.ps1 --backend libreoffice thesis.docx thesis.pdf
```

也可以直接调用本后端：

```bash
bash tools/docx2pdf/backends/libreoffice/convert.sh thesis.docx
bash tools/docx2pdf/backends/libreoffice/convert.sh thesis.docx thesis.pdf
```

旧兼容入口仍然可用，但不建议新文档继续使用：

```bash
bash tools/libreoffice-docx2pdf/docx2pdf.sh thesis.docx thesis.pdf
```

可配置项示例见：

```text
tools/docx2pdf/env.example
```

## 参数

```text
Usage:
  xju pdf <input.docx> [output.pdf] --backend libreoffice [options]

Options:
  --soffice PATH        LibreOffice executable path. Defaults to libreoffice/soffice in PATH.
  --tmp-root PATH       Temporary root directory. Defaults to $TMPDIR/xju_libreoffice_docx2pdf.
  --keep-tmp            Keep temporary files for debugging.
  --no-update-fields    Use direct --convert-to without opening the document and updating fields/indexes.
  -h, --help            Show help.
```

对应环境变量：

```text
XJU_LIBREOFFICE_BIN
XJU_LIBREOFFICE_DOCX2PDF_TMP_ROOT
XJU_LIBREOFFICE_DOCX2PDF_KEEP_TMP=1
XJU_LIBREOFFICE_DOCX2PDF_UPDATE_FIELDS=0
```

## 与 Word 后端的差异

LibreOffice 后端更通用，但对 DOCX 的解释和 Microsoft Word 不完全相同。毕业论文场景中常见差异包括：

- 分页位置变化，导致目录页码和章节起止页不同；
- 中文字体、英文/数字字体和行距的替换差异；
- 页眉页脚、题注、表格边距和图片缩放细节不同；
- Word 原生公式 OMML 的显示效果可能变化；
- Word 域、目录域和引用跳转的刷新能力不同。脚本会尽量刷新目录/字段，但刷新后的分页仍以 LibreOffice 自己的排版结果为准。

因此，LibreOffice 更适合作为“无 Word 时的快速预览后端”，当前默认的高保真后端仍建议使用 Microsoft Word。
