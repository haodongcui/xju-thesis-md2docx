# word-docx2pdf

WSL 下调用 Windows 侧 Microsoft Word，把 `docx` 导出为 `pdf`。

这个子目录刻意保持独立：复制出去后也可以作为单独项目使用。它不依赖主项目的源码路径，只要求运行时能找到本目录里的 `docx2pdf.sh` 和 `word_export.vbs`。

## 适用场景

- 需要用 Word 自己的排版引擎查看 DOCX 的分页和样式效果
- 需要给 AI 生成可进一步渲染成图片的 PDF 预览
- 当前运行环境是 WSL，Windows 主机已安装 Microsoft Word

不适合作为纯 Linux 或无 Office 环境的通用转换器。后续如果要支持 LibreOffice、OnlyOffice 等后端，应在外层做多后端调度，而不是把不同后端混在这个目录里。

## 依赖

- WSL
- Windows Microsoft Word
- WSL 可调用 `powershell.exe`、`wslpath`

可先运行诊断：

```bash
bash tools/word-docx2pdf/doctor.sh
```

## 用法

```bash
bash tools/word-docx2pdf/docx2pdf.sh thesis.docx
bash tools/word-docx2pdf/docx2pdf.sh thesis.docx thesis.pdf
```

默认输出为输入文件同名 `.pdf`。
输入、输出和 `--tmp-root` 支持相对路径、WSL 绝对路径，也支持 Windows 路径。

结合本项目示例：

```bash
python3 xju_thesis_md2docx_native.py example/thesis-demo.md example/thesis-demo.generated.docx
bash tools/word-docx2pdf/docx2pdf.sh example/thesis-demo.generated.docx example/thesis-demo.generated.pdf
```

如果要让 AI 查看页面效果，可以继续把 PDF 渲染为图片：

```bash
mkdir -p example/preview/thesis-demo
pdftoppm -png -r 160 example/thesis-demo.generated.pdf example/preview/thesis-demo/page
```

## 路径策略

默认不写死任何电脑用户路径。脚本会通过 Windows PowerShell 动态读取 Windows 临时目录：

```powershell
[IO.Path]::GetTempPath()
```

随后把 DOCX 复制到 Windows 本地临时目录，再调用 Word 导出 PDF。这样做是为了避免 Word COM 直接打开 WSL UNC 路径时出现兼容性问题。

如果你的机器需要指定临时目录，可以通过参数配置：

```bash
bash tools/word-docx2pdf/docx2pdf.sh thesis.docx thesis.pdf --tmp-root /mnt/c/Temp/xju-word-docx2pdf
```

也可以用环境变量：

```bash
XJU_WORD_DOCX2PDF_TMP_ROOT=/mnt/c/Temp/xju-word-docx2pdf \
  bash tools/word-docx2pdf/docx2pdf.sh thesis.docx thesis.pdf
```

`--tmp-root` 可以是 WSL 路径，也可以是 Windows 路径，例如 `C:\Temp\xju-word-docx2pdf`。但它必须指向 Windows 本地磁盘；不要指向 `/home/...` 这类 WSL 文件系统路径，否则 Word 看到的是 UNC 路径。

## 参数

```text
Usage:
  bash docx2pdf.sh [options] <input.docx> [output.pdf]

Options:
  --tmp-root PATH        Windows-local temporary root. Accepts WSL or Windows path.
  --vbs-template PATH    Override the VBS converter template.
  --keep-tmp            Keep temporary files for debugging.
  --skip-word-check      Skip the upfront Word COM availability check.
  --no-update-fields     Do not update Word fields before exporting.
  -h, --help             Show help.
```

对应环境变量：

```text
XJU_WORD_DOCX2PDF_TMP_ROOT
XJU_WORD_DOCX2PDF_VBS_TEMPLATE
XJU_WORD_DOCX2PDF_KEEP_TMP=1
XJU_WORD_DOCX2PDF_SKIP_WORD_CHECK=1
XJU_WORD_DOCX2PDF_UPDATE_FIELDS=0
```

## 调试

保留临时目录：

```bash
bash tools/word-docx2pdf/docx2pdf.sh thesis.docx --keep-tmp
```

脚本会打印临时目录位置。临时目录里通常包含：

- `input.docx`
- `word_export.vbs`
- `output.pdf`

## 已知限制

- 只能在可调用 Windows interop 的 WSL 环境工作
- 需要 Windows 侧 Word 授权、首次启动弹窗等状态正常
- Word COM 自动化不适合高并发调用
- PDF 预览接近 Word 效果，但最终提交前仍建议人工打开 Word / WPS 检查
