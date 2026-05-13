# docx2pdf

统一的 DOCX 转 PDF 后端调度入口。

跨平台核心逻辑在 Python 模块 `xju_thesis_md2docx.pdf` 中；本目录下的 `.sh`、`.ps1`、`.cmd` 只是不同系统上的启动器。

Linux / WSL：

```bash
bash tools/docx2pdf/docx2pdf.sh --backend word thesis.docx thesis.pdf
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice thesis.docx thesis.pdf
bash tools/docx2pdf/docx2pdf.sh --backend auto thesis.docx thesis.pdf
```

Windows PowerShell：

```powershell
.\tools\docx2pdf\docx2pdf.ps1 --backend word thesis.docx thesis.pdf
.\tools\docx2pdf\docx2pdf.ps1 --backend libreoffice thesis.docx thesis.pdf
```

也可以直接调用 Python 模块：

```bash
python -m xju_thesis_md2docx.pdf --backend auto thesis.docx thesis.pdf
```

## 后端选择

| 后端 | 适用场景 | 主要依赖 | 版式保真度 |
| --- | --- | --- | --- |
| `word` | Windows / WSL + Windows Word，本机最终预览 | Windows Microsoft Word | 最高，最接近 Word 打开效果 |
| `libreoffice` | Windows/Linux/CI/无 Word 快速预览 | LibreOffice | 中等，可能与 Word 分页和字体不同 |
| `auto` | 自动选择可用后端 | Word 或 LibreOffice | 优先 Word，否则 LibreOffice |

默认后端是 `word`。也可以通过环境变量修改：

```bash
XJU_DOCX2PDF_BACKEND=libreoffice \
  bash tools/docx2pdf/docx2pdf.sh thesis.docx thesis.pdf
```

可配置项示例集中放在：

```text
tools/docx2pdf/env.example
```

这个示例文件不会被脚本自动加载；需要时可以复制为本地 `.env` 后手动 `source`。

后端特有参数会原样传给后端脚本：

```bash
bash tools/docx2pdf/docx2pdf.sh --backend word thesis.docx thesis.pdf --no-update-fields
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice thesis.docx thesis.pdf --keep-tmp
bash tools/docx2pdf/docx2pdf.sh --backend libreoffice thesis.docx thesis.pdf --no-update-fields
```

LibreOffice 后端默认会先打开文档并刷新目录/字段，再导出 PDF；`--no-update-fields` 会回退到 LibreOffice 纯 `--convert-to` 模式。

## 目录职责

```text
tools/docx2pdf/
├── docx2pdf.sh
├── docx2pdf.ps1
├── docx2pdf.cmd
└── backends/
    ├── word/
    │   ├── convert.sh
    │   ├── doctor.sh
    │   └── word_export.vbs
    └── libreoffice/
        ├── convert.sh
        ├── doctor.sh
        └── update_fields_and_export.xba
```

- `xju_thesis_md2docx/pdf/` 放置跨平台 Python 调度和后端控制逻辑。
- `docx2pdf.sh`、`docx2pdf.ps1`、`docx2pdf.cmd` 只负责启动 Python 模块。
- `backends/word/` 放置 Word 后端使用的 `word_export.vbs` 和兼容 wrapper。
- `backends/libreoffice/` 放置 LibreOffice 字段刷新宏模板和兼容 wrapper。
- `tools/word-docx2pdf/`、`tools/libreoffice-docx2pdf/` 仅作为旧路径兼容入口保留，实际会转发到 `tools/docx2pdf/backends/`。

Word 后端不需要 Microsoft Word 安装路径配置。它通过 Windows COM 注册名 `Word.Application` 启动 Word；如果 doctor 检查失败，通常要修复 Windows 侧 Word/Office 安装或首次启动状态，而不是填写 `WINWORD.EXE` 绝对路径。

## 后端诊断

```bash
bash tools/docx2pdf/backends/word/doctor.sh
bash tools/docx2pdf/backends/libreoffice/doctor.sh
```

Windows PowerShell：

```powershell
.\xju.ps1 doctor --backend word
.\xju.ps1 doctor --backend libreoffice
```

兼容旧入口仍然可用：

```bash
bash tools/word-docx2pdf/doctor.sh
bash tools/libreoffice-docx2pdf/doctor.sh
```
