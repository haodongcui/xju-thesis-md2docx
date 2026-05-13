from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ...common import (
    PdfError,
    bool_env,
    ensure_input_file,
    is_windows,
    is_wsl,
    print_check,
    resolve_output_path,
    resolve_path,
    run_command,
    which_any,
)


BACKEND_DIR = Path(__file__).resolve().parent
WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


def _powershell_exe() -> str | None:
    return which_any(["powershell.exe", "powershell"])


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _powershell_output(command: str) -> str:
    ps = _powershell_exe()
    if not ps:
        raise PdfError("PowerShell not found")
    result = run_command([ps, "-NoProfile", "-Command", command], capture=True)
    return (result.stdout or "").replace("\r", "").strip()


def _word_com_check() -> tuple[bool, str]:
    ps = _powershell_exe()
    if not ps:
        return False, "PowerShell not found"
    command = (
        "try { "
        "$w = New-Object -ComObject Word.Application; "
        "$w.Quit(); "
        "[Console]::Out.Write('OK') "
        "} catch { "
        "[Console]::Out.Write('FAIL:' + $_.Exception.Message) "
        "}"
    )
    try:
        result = subprocess.run(
            [ps, "-NoProfile", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as exc:
        return False, str(exc)
    output = (result.stdout or "").replace("\r", "").strip()
    if result.returncode == 0 and output == "OK":
        return True, "Microsoft Word COM automation is available"
    return False, output or f"PowerShell exited with {result.returncode}"


def _wslpath(*args: str) -> str:
    result = run_command(["wslpath", *args], capture=True)
    return (result.stdout or "").replace("\r", "").strip()


def _wsl_path_to_unix(raw: str | Path) -> Path:
    value = str(raw)
    if WINDOWS_PATH_RE.match(value) or value.startswith("\\\\"):
        return Path(_wslpath("-u", value)).resolve()
    return Path(value).expanduser().resolve()


def _path_to_windows(raw: Path) -> str:
    if is_wsl():
        return _wslpath("-w", str(raw))
    return str(raw)


def _resolve_backend_path(raw: str | Path | None, default: Path) -> Path:
    if raw is None:
        return default.resolve()
    if is_wsl():
        return _wsl_path_to_unix(raw)
    return resolve_path(raw)


def _resolve_input_path(raw: str | Path) -> Path:
    if is_wsl():
        return _wsl_path_to_unix(raw)
    return resolve_path(raw)


def _resolve_output(raw_input: Path, raw_output: str | Path | None) -> Path:
    if raw_output is None:
        return raw_input.with_suffix(".pdf")
    if is_wsl():
        return _wsl_path_to_unix(raw_output)
    return Path(raw_output).expanduser().resolve()


def _default_tmp_root() -> Path:
    if is_wsl():
        raw = _powershell_output("[Console]::Out.Write([IO.Path]::GetTempPath())")
        return (_wsl_path_to_unix(raw) / "thesis_word_docx2pdf").resolve()
    return (Path(tempfile.gettempdir()) / "thesis_word_docx2pdf").resolve()


def _resolve_tmp_root(raw: str | Path | None) -> Path:
    if raw:
        if is_wsl():
            return _wsl_path_to_unix(raw)
        return resolve_path(raw)
    return _default_tmp_root()


def _call_cscript_native(vbs: Path, input_docx: Path, output_pdf: Path, update_fields: bool) -> None:
    cscript = which_any(["cscript.exe", "cscript"])
    if not cscript:
        raise PdfError("cscript not found in PATH")
    run_command(
        [
            cscript,
            "//nologo",
            str(vbs),
            str(input_docx),
            str(output_pdf),
            "1" if update_fields else "0",
        ],
        capture=True,
    )


def _call_cscript_wsl(job_dir: Path, vbs: Path, input_docx: Path, output_pdf: Path, update_fields: bool) -> None:
    ps = _powershell_exe()
    if not ps:
        raise PdfError("powershell.exe not found in PATH")
    win_job_dir = _path_to_windows(job_dir)
    command = (
        f"Set-Location -LiteralPath {_ps_quote(win_job_dir)}; "
        f"& cscript //nologo {_ps_quote(_path_to_windows(vbs))} "
        f"{_ps_quote(_path_to_windows(input_docx))} "
        f"{_ps_quote(_path_to_windows(output_pdf))} "
        f"{_ps_quote('1' if update_fields else '0')}"
    )
    result = subprocess.run(
        [ps, "-NoProfile", "-Command", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise PdfError((result.stdout or "").replace("\r", "") or f"PowerShell exited with {result.returncode}")


def convert(
    input_docx: str | Path,
    output_pdf: str | Path | None = None,
    *,
    tmp_root: str | Path | None = None,
    vbs_template: str | Path | None = None,
    keep_tmp: bool | None = None,
    skip_word_check: bool | None = None,
    update_fields: bool | None = None,
) -> Path:
    if not (is_windows() or is_wsl()):
        raise PdfError("Word backend requires native Windows, or WSL with Windows interop enabled")

    if is_wsl() and not which_any(["wslpath"]):
        raise PdfError("wslpath not found in PATH")

    keep_tmp = bool_env("THESIS_WORD_DOCX2PDF_KEEP_TMP", False) if keep_tmp is None else keep_tmp
    skip_word_check = (
        bool_env("THESIS_WORD_DOCX2PDF_SKIP_WORD_CHECK", False)
        if skip_word_check is None
        else skip_word_check
    )
    update_fields = bool_env("THESIS_WORD_DOCX2PDF_UPDATE_FIELDS", True) if update_fields is None else update_fields

    input_path = ensure_input_file(_resolve_input_path(input_docx))
    output_path = _resolve_output(input_path, output_pdf)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    default_vbs = BACKEND_DIR / "word_export.vbs"
    vbs_path = _resolve_backend_path(
        vbs_template or os.environ.get("THESIS_WORD_DOCX2PDF_VBS_TEMPLATE"),
        default_vbs,
    )
    ensure_input_file(vbs_path, "VBS template")

    if not skip_word_check:
        ok, message = _word_com_check()
        if not ok:
            raise PdfError(f"Microsoft Word COM automation is unavailable: {message}")

    tmp_root_path = _resolve_tmp_root(tmp_root or os.environ.get("THESIS_WORD_DOCX2PDF_TMP_ROOT"))
    tmp_root_path.mkdir(parents=True, exist_ok=True)
    if is_wsl():
        tmp_root_win = _path_to_windows(tmp_root_path)
        if tmp_root_win.startswith("\\\\"):
            raise PdfError(f"--tmp-root must resolve to a Windows-local path, not a WSL UNC path: {tmp_root_win}")

    job_dir = Path(tempfile.mkdtemp(prefix="job-", dir=str(tmp_root_path)))
    try:
        job_input = job_dir / "input.docx"
        job_vbs = job_dir / "word_export.vbs"
        job_output = job_dir / "output.pdf"
        shutil.copy2(input_path, job_input)
        shutil.copy2(vbs_path, job_vbs)

        if is_wsl():
            _call_cscript_wsl(job_dir, job_vbs, job_input, job_output, update_fields)
        else:
            _call_cscript_native(job_vbs, job_input, job_output, update_fields)

        if not job_output.is_file():
            raise PdfError("Word did not produce output.pdf in the temporary working directory")
        shutil.copy2(job_output, output_path)
    finally:
        if keep_tmp:
            print(f"Temporary files kept at: {job_dir}")
        else:
            shutil.rmtree(job_dir, ignore_errors=True)

    print(f"PDF written to: {output_path}")
    if is_wsl():
        print(f"Windows-side PDF path: {_path_to_windows(output_path)}")
    print("Backend: word")
    return output_path


def doctor() -> int:
    print("Word PDF backend environment check")
    print()
    status = 0

    if is_windows():
        print_check(True, "native Windows detected")
    elif is_wsl():
        print_check(True, f"WSL kernel detected: {os.uname().release}")
    else:
        print_check(False, f"this does not look like Windows or WSL: {os.name}")
        status = 1

    ps = _powershell_exe()
    if ps:
        print_check(True, f"PowerShell: {ps}")
    else:
        print_check(False, "PowerShell not found")
        status = 1

    if is_wsl():
        wslpath = which_any(["wslpath"])
        if wslpath:
            print_check(True, f"wslpath: {wslpath}")
        else:
            print_check(False, "wslpath not found")
            status = 1

    cscript = which_any(["cscript.exe", "cscript"])
    if cscript:
        print_check(True, f"cscript: {cscript}")
    else:
        print_check(False, "cscript not found")
        status = 1

    try:
        temp_path = _powershell_output("[Console]::Out.Write([IO.Path]::GetTempPath())")
        print_check(True, f"Windows temp path: {temp_path}")
    except PdfError as exc:
        print_check(False, f"could not read Windows temp path: {exc}")
        status = 1

    ok, message = _word_com_check()
    if ok:
        print_check(True, message)
    else:
        print_check(False, f"Microsoft Word COM automation is unavailable: {message}")
        status = 1

    return status
