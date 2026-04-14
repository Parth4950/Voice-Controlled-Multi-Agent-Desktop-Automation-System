"""Filesystem helpers: create, copy, move, delete, rename, open in Explorer."""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from config import get_bruh_files_root, get_filesystem_scope
from tools.log import safe_log

_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def _system32_root() -> Path:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    return (Path(windir) / "System32").resolve()


def _delete_is_forbidden(path: Path) -> bool:
    """Block deletes that would brick the OS or wipe a drive root."""
    try:
        r = path.resolve()
    except OSError:
        return True
    if not r.parts:
        return True
    if r.parent == r or (r.drive and len(r.parts) == 1):
        return True
    try:
        r.relative_to(_system32_root())
        return True
    except ValueError:
        pass
    try:
        r.relative_to(Path(os.environ.get("WINDIR", r"C:\Windows")).resolve())
        if r.is_dir() and r.name.lower() == "windows":
            return True
    except ValueError:
        pass
    return False


def _path_in_scope(p: Path) -> bool:
    try:
        r = p.resolve()
    except OSError:
        return False
    if get_filesystem_scope() == "full":
        return True
    home = Path.home().resolve()
    if r == home or home in r.parents:
        return True
    br = get_bruh_files_root().resolve()
    return r == br or br in r.parents


def _scope_error() -> str:
    return (
        "That path is outside your profile. Set filesystem_scope to full in config.json "
        "if you really want that."
    )


def reveal_in_explorer(path: Path) -> None:
    try:
        path = path.resolve()
    except OSError:
        return
    try:
        if path.is_dir():
            subprocess.Popen(["explorer", str(path)], shell=False)
        elif path.is_file():
            subprocess.Popen(["explorer", "/select,", str(path)], shell=False)
        else:
            subprocess.Popen(["explorer", str(path.parent)], shell=False)
    except Exception as e:
        safe_log("DEBUG -> reveal_in_explorer:", e)


def sanitize_name(raw: str) -> Optional[str]:
    if not raw:
        return None
    name = raw.strip().strip('"').strip("'")
    name = re.sub(r"[\x00-\x1f]", "", name)
    if not name or name in (".", ".."):
        return None
    if ".." in name or "/" in name or "\\" in name:
        return None
    if re.match(r"^[a-zA-Z]:", name):
        return None
    base = Path(name).name
    if not base:
        return None
    stem = Path(base).stem.upper()
    part = Path(base).suffix.upper()
    if stem in _RESERVED or (not part and base.upper() in _RESERVED):
        return None
    return base


def _normalize_path_spec_text(spec: str) -> str:
    """Clean common speech filler words from filesystem path fragments."""
    s = (spec or "").strip().strip('"').strip("'")
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^(?:the\s+)?(?:folder|file|directory)\s+", "", s, flags=re.I)
    s = re.sub(r"^(?:the\s+)?(?:path|location)\s+", "", s, flags=re.I)
    return s.strip()


def resolve_path_spec(spec: str, must_exist: bool = False) -> Optional[Path]:
    """Turn a voice fragment into a Path (aliases, absolute paths, Bruh home fallbacks)."""
    if not spec:
        return None
    s = _normalize_path_spec_text(spec)
    if not s:
        return None
    s_norm = os.path.expandvars(s)
    s_norm = s_norm.replace("/", "\\")

    if re.match(r"^[a-zA-Z]:\\", s_norm) or s_norm.startswith("\\\\"):
        try:
            p = Path(s_norm).expanduser().resolve()
            if must_exist and not p.exists():
                return None
            return p
        except OSError:
            return None

    s_low = s_norm.lower()
    alias_bases: Tuple[Tuple[str, Path], ...] = (
        ("my documents\\", Path.home() / "Documents"),
        ("my documents", Path.home() / "Documents"),
        ("documents\\", Path.home() / "Documents"),
        ("documents", Path.home() / "Documents"),
        ("my desktop\\", Path.home() / "Desktop"),
        ("my desktop", Path.home() / "Desktop"),
        ("desktop\\", Path.home() / "Desktop"),
        ("desktop", Path.home() / "Desktop"),
        ("downloads\\", Path.home() / "Downloads"),
        ("downloads", Path.home() / "Downloads"),
        ("pictures\\", Path.home() / "Pictures"),
        ("pictures", Path.home() / "Pictures"),
        ("videos\\", Path.home() / "Videos"),
        ("videos", Path.home() / "Videos"),
        ("music\\", Path.home() / "Music"),
        ("music", Path.home() / "Music"),
        ("bruh files\\", get_bruh_files_root()),
        ("bruh files", get_bruh_files_root()),
        ("bruh folder\\", get_bruh_files_root()),
        ("bruh folder", get_bruh_files_root()),
    )
    for prefix, base in alias_bases:
        pl = prefix.lower()
        if s_low == pl.rstrip("\\"):
            p = base.resolve()
            if must_exist and not p.exists():
                return None
            return p
        if s_low.startswith(pl):
            rest = s_norm[len(prefix) :].lstrip("\\/")
            if not rest:
                p = base.resolve()
                if must_exist and not p.exists():
                    return None
                return p
            try:
                p = (base / rest).resolve()
            except OSError:
                return None
            if must_exist and not p.exists():
                return None
            return p

    if "\\" not in s_norm and "/" not in s_norm and ":" not in s_norm:
        segment = Path(s_norm).name
        candidates = [
            get_bruh_files_root() / segment,
            Path.home() / "Documents" / segment,
            Path.home() / "Desktop" / segment,
            Path.home() / "Downloads" / segment,
        ]
        for cand in candidates:
            try:
                cr = cand.resolve()
            except OSError:
                continue
            if cr.exists():
                return cr
        if must_exist:
            return None
        try:
            return (get_bruh_files_root() / segment).resolve()
        except OSError:
            return None

    try:
        p = Path(s_norm).expanduser().resolve()
    except OSError:
        return None
    if must_exist and not p.exists():
        return None
    return p


def _resolve_parent_for_create(spec: str) -> Optional[Path]:
    p = resolve_path_spec(spec, must_exist=False)
    if p is None:
        return None
    if not _path_in_scope(p):
        return None
    return p


def _folder_name_segment(name: str) -> Optional[str]:
    s = sanitize_name(name)
    if s:
        return s
    raw = name.strip().strip('"').strip("'")
    if not raw or ".." in raw or "/" in raw or "\\" in raw or ":" in raw:
        return None
    return Path(raw).name or None


def create_folder(name: str, parent_spec: Optional[str] = None) -> str:
    seg = _folder_name_segment(name)
    if parent_spec:
        parent = _resolve_parent_for_create(parent_spec)
        if parent is None:
            return "Couldn't figure out that folder location."
        if not _path_in_scope(parent):
            return _scope_error()
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return f"Couldn't use that location: {e}"
        if not seg:
            return "Invalid folder name."
        try:
            target = (parent / seg).resolve()
        except OSError:
            return "Invalid folder name."
    else:
        if not seg:
            return "Invalid folder name."
        root = get_bruh_files_root()
        try:
            root.mkdir(parents=True, exist_ok=True)
            target = (root / seg).resolve()
        except OSError as e:
            return f"Couldn't create folder: {e}"
        if root not in target.parents and target != root:
            return "Invalid folder path."

    if not _path_in_scope(target):
        return _scope_error()
    try:
        target.mkdir(parents=True, exist_ok=True)
        safe_log("DEBUG -> Created folder:", target)
        reveal_in_explorer(target)
        return f"Folder created at {target}"
    except OSError as e:
        safe_log("DEBUG -> create_folder error:", e)
        return f"Couldn't create folder: {e}"


def _file_name_segment(name: str) -> Optional[str]:
    s = sanitize_name(name)
    if s:
        return s if "." in s else f"{s}.txt"
    raw = name.strip().strip('"').strip("'")
    if not raw or ".." in raw or "/" in raw or "\\" in raw or ":" in raw:
        return None
    base = Path(raw).name
    if not base:
        return None
    if "." not in base:
        base = f"{base}.txt"
    return base


def create_file(name: str, parent_spec: Optional[str] = None) -> str:
    if parent_spec:
        parent = _resolve_parent_for_create(parent_spec)
        if parent is None:
            return "Couldn't figure out that location."
        if not _path_in_scope(parent):
            return _scope_error()
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return f"Couldn't use that location: {e}"
        base = _file_name_segment(name)
        if not base:
            return "Invalid file name."
        try:
            target = (parent / base).resolve()
        except OSError:
            return "Invalid file name."
    else:
        base = _file_name_segment(name)
        if not base:
            return "Invalid file name."
        root = get_bruh_files_root()
        try:
            root.mkdir(parents=True, exist_ok=True)
            target = (root / base).resolve()
        except OSError as e:
            return f"Couldn't create file: {e}"
        if root not in target.parents and target != root:
            return "Invalid file path."

    if not _path_in_scope(target):
        return _scope_error()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)
        safe_log("DEBUG -> Created file:", target)
        reveal_in_explorer(target)
        return f"File created at {target}"
    except OSError as e:
        safe_log("DEBUG -> create_file error:", e)
        return f"Couldn't create file: {e}"


def fs_open(path_spec: str) -> str:
    p = resolve_path_spec(path_spec, must_exist=True)
    if p is None or not p.exists():
        return "Couldn't find that path."
    if not _path_in_scope(p):
        return _scope_error()
    reveal_in_explorer(p)
    return f"Opened {p}"


def fs_copy(src_spec: str, dst_spec: str) -> str:
    src = resolve_path_spec(src_spec, must_exist=True)
    dst = resolve_path_spec(dst_spec, must_exist=False)
    if src is None or not src.exists():
        return "Couldn't find the source."
    if dst is None:
        return "Couldn't figure out the destination."
    if not _path_in_scope(src) or not _path_in_scope(dst):
        return _scope_error()
    try:
        if dst.exists() and dst.is_dir():
            dst = dst / src.name
        if src.is_dir():
            if dst.exists():
                return "Destination already exists. Pick a new name or folder."
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        safe_log("DEBUG -> fs_copy:", src, "->", dst)
        reveal_in_explorer(dst if dst.exists() else dst.parent)
        return f"Copied to {dst}"
    except OSError as e:
        safe_log("DEBUG -> fs_copy error:", e)
        return f"Copy failed: {e}"


def fs_move(src_spec: str, dst_spec: str) -> str:
    src = resolve_path_spec(src_spec, must_exist=True)
    dst = resolve_path_spec(dst_spec, must_exist=False)
    if src is None or not src.exists():
        return "Couldn't find the source."
    if dst is None:
        return "Couldn't figure out the destination."
    if not _path_in_scope(src) or not _path_in_scope(dst):
        return _scope_error()
    if _delete_is_forbidden(src):
        return "Won't move that system path."
    try:
        dest = shutil.move(str(src), str(dst))
        dest_path = Path(dest).resolve()
        safe_log("DEBUG -> fs_move:", dest_path)
        reveal_in_explorer(dest_path)
        return f"Moved to {dest_path}"
    except OSError as e:
        safe_log("DEBUG -> fs_move error:", e)
        return f"Move failed: {e}"


def fs_delete(path_spec: str) -> str:
    p = resolve_path_spec(path_spec, must_exist=True)
    if p is None or not p.exists():
        return "Nothing there to delete."
    if not _path_in_scope(p):
        return _scope_error()
    if _delete_is_forbidden(p):
        return "Won't delete that path."
    try:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        safe_log("DEBUG -> fs_delete:", p)
        reveal_in_explorer(p.parent)
        return f"Deleted {p}"
    except OSError as e:
        safe_log("DEBUG -> fs_delete error:", e)
        return f"Delete failed: {e}"


def fs_rename(old_spec: str, new_spec: str) -> str:
    old = resolve_path_spec(old_spec, must_exist=True)
    if old is None or not old.exists():
        return "Couldn't find that to rename."
    if not _path_in_scope(old):
        return _scope_error()
    if _delete_is_forbidden(old):
        return "Won't rename that system path."
    new_s = new_spec.strip().strip('"').strip("'")
    if not new_s:
        return "Need a new name."
    if "\\" in new_s or "/" in new_s or ".." in new_s:
        new_path = resolve_path_spec(new_s, must_exist=False)
        if new_path is None:
            return "Bad new path."
        if not _path_in_scope(new_path):
            return _scope_error()
        target = new_path
    else:
        target = (old.parent / new_s).resolve()
        if not _path_in_scope(target):
            return _scope_error()
    if target.exists():
        return "Something already exists with that name."
    try:
        old.rename(target)
        safe_log("DEBUG -> fs_rename:", old, "->", target)
        reveal_in_explorer(target)
        return f"Renamed to {target}"
    except OSError as e:
        safe_log("DEBUG -> fs_rename error:", e)
        return f"Rename failed: {e}"
