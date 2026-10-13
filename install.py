#!/usr/bin/env python3
"""Back up and install the committed dotCodex template, preserving personal TOML settings."""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

try:
    import tomlkit
except ImportError:
    sys.exit("tomlkit is required: python3 -m pip install -r requirements.txt")

REPO = Path(__file__).resolve().parent
BACKUPS = REPO / "backups"
STATE = "codex/.dotcodex-state.json"


class InstallError(Exception):
    pass

class _Missing:
    def __repr__(self):
        return "MISSING"


MISSING = _Missing()


def canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def dump_json(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


class SettingsMerge:
    """Three-way merge of config.toml.

    base: the template applied last time (MISSING if unknown), user: the current file,
    tpl: the template being applied now. Template changes are applied; user changes win.
    """

    def __init__(self):
        self.warnings = []
        self.notes = []

    def merge(self, base, user, tpl, path=()):
        where = ".".join(path) or "(root)"
        if tpl is MISSING:
            if base is MISSING or user is MISSING:
                return user
            if canon(user) == canon(base):
                return MISSING  # dropped from the template, untouched by the user
            if isinstance(user, dict) and isinstance(base, dict):
                merged = self.merge(base, user, {}, path)
                return merged if merged else MISSING
            if isinstance(user, list) and isinstance(base, list):
                merged = self.merge(base, user, [], path)
                return merged if merged else MISSING
            self.warnings.append(f"{where}: dropped from the template, but you changed it; keeping {canon(user)}")
            return user
        if user is MISSING:
            if base is not MISSING:
                self.notes.append(f"{where}: you removed it; not adding it back")
                return MISSING
            return tpl
        if isinstance(user, dict) and isinstance(tpl, dict):
            base_dict = base if isinstance(base, dict) else {}
            merged = {}
            for key in list(user) + [k for k in tpl if k not in user]:
                value = self.merge(base_dict.get(key, MISSING), user.get(key, MISSING), tpl.get(key, MISSING), path + (key,))
                if value is not MISSING:
                    merged[key] = value
            return merged
        if isinstance(user, list) and isinstance(tpl, list) and path == ("sandbox_workspace_write", "writable_roots"):
            base_list = base if isinstance(base, list) else []
            return self.merge_items(base_list, user, tpl, where)
        if canon(user) == canon(tpl):
            return tpl
        if base is not MISSING and canon(user) == canon(base):
            return tpl  # template changed a value the user never touched
        if base is MISSING or canon(base) != canon(tpl):
            self.warnings.append(f"{where}: keeping your value {canon(user)} (template: {canon(tpl)})")
        return user

    def merge_items(self, base, user, tpl, where):
        """Union as a set, keeping the user's order first, then new template items."""
        base_keys = {canon(x) for x in base}
        user_keys = {canon(x) for x in user}
        tpl_keys = {canon(x) for x in tpl}
        merged, seen = [], set()
        for item in user:
            key = canon(item)
            if key in seen or (key in base_keys and key not in tpl_keys):
                continue  # duplicate, or dropped from the template
            seen.add(key)
            merged.append(item)
        for item in tpl:
            key = canon(item)
            if key in seen:
                continue
            seen.add(key)
            if key in base_keys and key not in user_keys:
                self.notes.append(f"{where}: you removed {key}; not adding it back")
                continue
            merged.append(item)
        return merged

def git(*args):
    result = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)
    if result.returncode:
        raise InstallError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise InstallError(f"cannot read {path}: {exc}") from exc


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reject_symlinks(path):
    for item in [path, *path.parents]:
        if item.is_symlink():
            raise InstallError(f"refusing symlink: {item}")


def target(roots, key):
    parts = key.split("/")
    if parts[0] not in roots or len(parts) < 2 or any(p in ("", ".", "..") for p in parts):
        raise InstallError(f"invalid managed path: {key}")
    path = roots[parts[0]].joinpath(*parts[1:])
    # Never follow symlinks, including symlinked roots or ancestors.
    reject_symlinks(path)
    return path


def read_optional(path):
    if path.exists() and not path.is_file():
        raise InstallError(f"expected a file: {path}")
    return path.read_bytes() if path.exists() else None


def sync_toml(document, values):
    """Change only changed values; keep personal comments, tables, and formatting."""
    for key in list(document):
        if key not in values:
            del document[key]
    for key, value in values.items():
        if key in document and document[key] == value:
            continue
        if key in document and isinstance(value, dict) and isinstance(document[key], dict):
            sync_toml(document[key], value)
        elif key in document and isinstance(value, list) and isinstance(document[key], tomlkit.items.Array):
            array = document[key]
            # Keep existing items (and their comments) while applying ordered set changes.
            retained = [item for item in array if item in value]
            if retained == value[:len(retained)] and len({canon(item) for item in value}) == len(value):
                for index in range(len(array) - 1, -1, -1):
                    if array[index] not in value:
                        del array[index]
                for item in value[len(retained):]:
                    array.append(item)
            else:
                document[key] = value
        else:
            document[key] = value


def make_plan(roots, args):
    ref = args.ref or "origin/HEAD"
    try:
        commit = git("rev-parse", "--verify", ref + "^{commit}").decode().strip()
    except InstallError as exc:
        raise InstallError(f"unknown ref {ref}; set origin/HEAD with git remote set-head origin --auto") from exc
    print(f"source: {ref} ({commit[:7]}); working-copy changes are not used")
    state_path = target(roots, STATE)
    state = load_json(state_path) if state_path.exists() else {}
    locations = {key: str(value) for key, value in roots.items()}
    if state.get("roots", locations) != locations:
        raise InstallError("installation targets changed; restore or use the previous --skills-dir")
    raw = args.worktree_dir or os.environ.get("WORKTREE_BASE_DIR") or state.get("worktree_dir") or "~/git/wt"
    worktree = os.path.abspath(os.path.expanduser(raw))
    if Path(worktree) in (Path.home(), Path("/")):
        raise InstallError("worktree directory must not be the home directory or filesystem root")
    files = {}
    for entry in git("ls-tree", "-rz", commit, "--", "AGENTS.md", "subagent-working-principles.md", "rules", "skills").split(b"\0"):
        if not entry:
            continue
        meta, name = entry.decode().split("\t", 1)
        mode, kind, _ = meta.split()
        if kind != "blob" or mode not in ("100644", "100755"):
            raise InstallError(f"unsupported template entry: {name}")
        key = "agents/" + name if name.startswith("skills/") else "codex/" + name
        content = git("show", f"{commit}:{name}")
        try:
            content = content.decode().replace("~/git/wt", worktree).encode()
        except UnicodeDecodeError:
            pass
        files[key] = (content, int(mode[-3:], 8))
    for required in ("codex/AGENTS.md", "codex/subagent-working-principles.md", "agents/skills/self-review/SKILL.md"):
        if required not in files:
            raise InstallError(f"template is incomplete: missing {required}")
    try:
        template_doc = tomlkit.parse(git("show", f"{commit}:config.toml").decode())
        template_doc["sandbox_workspace_write"]["writable_roots"] = [worktree]
        tpl = template_doc.unwrap()
        settings_path = target(roots, "codex/config.toml")
        old = read_optional(settings_path)
        doc = tomlkit.parse(old.decode()) if old is not None else copy.deepcopy(template_doc)
    except (ValueError, KeyError) as exc:
        raise InstallError(f"invalid config.toml: {exc}") from exc
    merger = SettingsMerge()
    merged = merger.merge(state.get("settings_template", MISSING), doc.unwrap() if old is not None else MISSING, tpl)
    sync_toml(doc, merged)
    new = tomlkit.dumps(doc).encode()
    # Avoid rewriting TOML if its values have not changed.
    if old is not None and merged == tomlkit.parse(old.decode()).unwrap():
        new = old
    files["codex/config.toml"] = (new, settings_path.stat().st_mode & 0o777 if old is not None else 0o600)
    for note in merger.notes:
        print(f"note: {note}")
    # Never print values from personal config: they may contain credentials.
    if merger.warnings:
        print(f"warning: kept {len(merger.warnings)} personal configuration overrides")
    if old != new:
        print("config.toml: values will change; personal values are omitted from output")
    writes, deletes = {}, []
    tracked = {}
    for key, (data, mode) in files.items():
        path = target(roots, key)
        current = read_optional(path)
        if key != "codex/config.toml":
            tracked[key] = digest(data)
        if current != data or (current is not None and path.stat().st_mode & 0o777 != mode):
            writes[key] = (data, mode)
            if current is not None and key != "codex/config.toml" and digest(current) != state.get("files", {}).get(key):
                print(f"warning: {key} will be overwritten after backup")
    for key, previous in state.get("files", {}).items():
        if key in tracked:
            continue
        current = read_optional(target(roots, key))
        if current is not None:
            if digest(current) == previous:
                deletes.append(key)
            else:
                print(f"warning: removed template file {key} has personal edits; keeping it")
    next_state = {"roots": locations, "worktree_dir": worktree, "settings_template": tpl, "files": tracked}
    if state != next_state:
        writes[STATE] = (dump_json(next_state).encode(), 0o600)
    return writes, deletes


def write_atomic(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".dotcodex-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def backup(roots, keys):
    reject_symlinks(BACKUPS)
    BACKUPS.mkdir(exist_ok=True, mode=0o700)
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    for n in range(1000):
        name = stamp if n == 0 else f"{stamp}-{n}"
        folder = BACKUPS / name
        try:
            folder.mkdir(mode=0o700)
            break
        except FileExistsError:
            continue
    else:
        raise InstallError("cannot allocate backup directory")
    entries = {}
    for key in keys:
        path = target(roots, key)
        data = read_optional(path)
        entries[key] = None if data is None else path.stat().st_mode & 0o777
        if data is not None:
            write_atomic(folder / key, data, 0o600)
    manifest = {"roots": {key: str(value) for key, value in roots.items()}, "entries": entries}
    write_atomic(folder / "manifest.json", dump_json(manifest).encode(), 0o600)
    return name


def restore_plan(roots, name):
    reject_symlinks(BACKUPS)
    names = sorted((p.name for p in BACKUPS.glob("*") if re.fullmatch(r"\d{14}(-\d+)?", p.name) and (p / "manifest.json").is_file()), key=lambda n: (n[:14], int(n[15:] or 0)))
    if name == "latest":
        if not names:
            raise InstallError("no backups")
        name = names[-1]
    if name not in names:
        raise InstallError(f"unknown backup: {name}")
    folder = BACKUPS / name
    reject_symlinks(folder / "manifest.json")
    manifest = load_json(folder / "manifest.json")
    if manifest["roots"] != {key: str(value) for key, value in roots.items()}:
        raise InstallError("backup targets do not match current installation targets")
    writes, deletes = {}, []
    for key, mode in manifest["entries"].items():
        path = target(roots, key)
        read_optional(path)
        if mode is None:
            deletes.append(key)
        else:
            saved = target({"codex": folder / "codex", "agents": folder / "agents"}, key)
            if not saved.is_file():
                raise InstallError(f"missing backup file: {key}")
            writes[key] = (saved.read_bytes(), mode)
    return writes, deletes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ref", help="committed template ref (default: origin/HEAD)")
    parser.add_argument("--worktree-dir")
    parser.add_argument("--codex-dir", default=os.environ.get("CODEX_HOME") or "~/.codex")
    parser.add_argument("--skills-dir", default="~/.agents/skills")
    parser.add_argument("--restore", nargs="?", const="latest", metavar="TIMESTAMP")
    args = parser.parse_args()
    if args.restore and (args.ref or args.worktree_dir):
        parser.error("--restore cannot be combined with --ref or --worktree-dir")
    roots = {"codex": Path(os.path.abspath(os.path.expanduser(args.codex_dir))), "agents": Path(os.path.abspath(os.path.expanduser(args.skills_dir))).parent}
    if Path(os.path.abspath(os.path.expanduser(args.skills_dir))).name != "skills":
        parser.error("--skills-dir must end in /skills")
    try:
        if roots["codex"] == roots["agents"] or roots["codex"] in roots["agents"].parents or roots["agents"] in roots["codex"].parents:
            raise InstallError("Codex and skills roots must not overlap")
        writes, deletes = restore_plan(roots, args.restore) if args.restore else make_plan(roots, args)
        if not writes and not deletes:
            print("Already up to date; nothing changed.")
            return
        for key in writes:
            print(f"write {target(roots, key)}")
        for key in deletes:
            print(f"delete {target(roots, key)}")
        if args.dry_run:
            print("dry-run: nothing changed")
            return
        name = backup(roots, [*writes, *deletes])
        print(f"backup: {BACKUPS / name}", flush=True)
        for key, (data, mode) in writes.items():
            write_atomic(target(roots, key), data, mode)
        for key in deletes:
            target(roots, key).unlink(missing_ok=True)
        print(f"Done. Undo with --restore {name} and the same target options.")
    except (InstallError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
