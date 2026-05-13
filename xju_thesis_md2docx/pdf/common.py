from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DOCX2PDF_DIR = REPO_ROOT / "tools" / "docx2pdf"
WORD_BACKEND_DIR = TOOLS_DOCX2PDF_DIR / "backends" / "word"
LIBREOFFICE_BACKEND_DIR = TOOLS_DOCX2PDF_DIR / "backends" / "libreoffice"


class PdfError(RuntimeError):
    pass


def is_windows() -> bool:
    return os.name == "nt"


def is_wsl() -> bool:
    if is_windows():
        return False
    release = platform.uname().release.lower()
    return "microsoft" in release or "wsl" in release


def bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def run_command(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, object] = {
        "env": env,
        "cwd": str(cwd) if cwd is not None else None,
        "text": True,
    }
    if capture:
        kwargs.update({"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT})
    result = subprocess.run(args, **kwargs)
    if result.returncode != 0:
        output = result.stdout if capture else ""
        raise PdfError(
            f"command failed ({result.returncode}): {' '.join(args)}"
            + (f"\n{output}" if output else "")
        )
    return result


def which_any(names: list[str]) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def ensure_input_file(path: Path, label: str = "input DOCX") -> Path:
    if not path.is_file():
        raise PdfError(f"{label} not found: {path}")
    return path


def resolve_path(raw: str | Path) -> Path:
    return Path(raw).expanduser().resolve()


def resolve_output_path(input_path: Path, raw_output: str | Path | None) -> Path:
    if raw_output is None:
        return input_path.with_suffix(".pdf")
    return Path(raw_output).expanduser().resolve()


def print_check(ok: bool, message: str) -> bool:
    stream = sys.stdout if ok else sys.stderr
    prefix = "[ok]" if ok else "[fail]"
    print(f"{prefix} {message}", file=stream)
    return ok
