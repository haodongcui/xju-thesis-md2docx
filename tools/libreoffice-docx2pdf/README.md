# libreoffice-docx2pdf

使用 LibreOffice headless 模式把 `docx` 导出为 `pdf`。

这个后端不依赖 Windows Microsoft Word，适合 Linux、本机无 Word 或 CI 环境中的基础 PDF 预览。但它使用的是 LibreOffice 的 DOCX 排版引擎，导出效果不保证与 Microsoft Word 完全一致。

## 依赖

- LibreOffice / `soffice`
- Linux 字体环境，尤其是中文字体和 Times New Roman 兼容字体

Ubuntu / Debian 可安装：

```bash
sudo apt-get update
sudo apt-get install -y libreoffice
```

可先运行诊断：

```bash
bash tools/libreoffice-docx2pdf/doctor.sh
```

## 用法

```bash
bash tools/libreoffice-docx2pdf/docx2pdf.sh thesis.docx
bash tools/libreoffice-docx2pdf/docx2pdf.sh thesis.docx thesis.pdf
```

也可以通过统一入口选择后端：

```bash
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice thesis.docx thesis.pdf
```

## 参数

```text
Usage:
  bash docx2pdf.sh [options] <input.docx> [output.pdf]

Options:
  --soffice PATH        LibreOffice executable path. Defaults to libreoffice/soffice in PATH.
  --tmp-root PATH       Temporary root directory. Defaults to $TMPDIR/xju_libreoffice_docx2pdf.
  --keep-tmp            Keep temporary files for debugging.
  -h, --help            Show help.
```

对应环境变量：

```text
XJU_LIBREOFFICE_BIN
XJU_LIBREOFFICE_DOCX2PDF_TMP_ROOT
XJU_LIBREOFFICE_DOCX2PDF_KEEP_TMP=1
```

## 与 Word 后端的差异

LibreOffice 后端更通用，但对 DOCX 的解释和 Microsoft Word 不完全相同。毕业论文场景中常见差异包括：

- 分页位置变化，导致目录页码和章节起止页不同；
- 中文字体、英文/数字字体和行距的替换差异；
- 页眉页脚、题注、表格边距和图片缩放细节不同；
- Word 原生公式 OMML 的显示效果可能变化；
- Word 域、目录域和引用跳转的刷新能力不同。

因此，LibreOffice 更适合作为“无 Word 时的快速预览后端”，当前默认的高保真后端仍建议使用 Microsoft Word。
