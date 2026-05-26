#!/usr/bin/env python3
"""
resolve_meta.py - Resolve %(keyword)s placeholders in a file using .meta.json
Usage: resolve_meta.py <file_to_resolve> [--meta /path/to/.meta.json]
       If --meta not specified, defaults to $INSTALLROOT/.meta.json
"""
import json
import re
import os
import sys

_PLACEHOLDER = re.compile(r"\%\(([a-zA-Z][a-zA-Z0-9_]*)\)s")
_DEFAULT_PLACEHOLDER = re.compile(r"\%\(([a-zA-Z][a-zA-Z0-9_]*):-([^)]*)\)s")


def _err(*msg):
    print("ERROR:", *msg, file=sys.stderr)
    sys.exit(1)


def _strip(v):
    return v.strip() if isinstance(v, str) else v


def collect_vars(meta_path):
    with open(meta_path) as f:
        meta = json.load(f)

    pkg_vars = {k.strip(): _strip(v) for k, v in meta["package"].get("variables", {}).items()}
    dep_vars = {}   # k -> (value, first_source)
    conflicts = {}  # k -> [sources]

    for dep_type in ("build", "runtime"):
        for dep in meta.get("dependencies", {}).get("direct", {}).get(dep_type, []):
            dep_name = dep["name"]
            for k, v in dep.get("variables", {}).items():
                k, v = k.strip(), _strip(v)
                if k in pkg_vars:
                    _err(f"variable '{k}' from dep '{dep_name}' conflicts with package variable")
                if k in dep_vars:
                    conflicts.setdefault(k, [dep_vars[k][1]]).append(dep_name)
                else:
                    dep_vars[k] = (v, dep_name)

    if conflicts:
        for k, srcs in conflicts.items():
            print(f"ERROR: variable '{k}' defined in multiple deps: {', '.join(srcs)}", file=sys.stderr)
        sys.exit(1)

    return {k: v for k, (v, _) in dep_vars.items()} | pkg_vars


def _apply_defaults(data, all_vars):
    """Rewrite %(key:-default)s → %(key)s and inject default when key is absent."""
    def rewrite(m):
        all_vars.setdefault(m.group(1), m.group(2))
        return f"%({m.group(1)})s"
    return _DEFAULT_PLACEHOLDER.sub(rewrite, data)


def resolve_from_meta(meta_path, data):
    all_vars = collect_vars(meta_path)
    data = _apply_defaults(data, all_vars)

    missing = set(_PLACEHOLDER.findall(data)) - set(all_vars)
    if missing:
        for k in sorted(missing):
            print(f"ERROR: placeholder %({k})s used in file but not defined in meta", file=sys.stderr)
        sys.exit(1)

    def _sub(m):
        key = m.group(1)
        if key not in all_vars:
            raise KeyError(key)
        return str(all_vars[key])

    for _ in range(10):
        if not _PLACEHOLDER.search(data):
            break
        try:
            data = _PLACEHOLDER.sub(_sub, data)
        except KeyError as e:
            _err(f"placeholder %({e.args[0]})s introduced by substitution is not defined")
    else:
        remaining = ", ".join(set(_PLACEHOLDER.findall(data)))
        _err(f"circular or unresolvable variable references: {remaining}")

    return data


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Resolve .meta.json placeholders in a file")
    parser.add_argument("file", nargs="?", help="File to resolve")
    parser.add_argument("--meta", help="Path to .meta.json (default: $INSTALLROOT/.meta.json)")
    parser.add_argument("--list-vars", action="store_true", help="List all available variables and exit")
    args = parser.parse_args()

    meta_path = args.meta
    if not meta_path:
        installroot = os.environ.get("INSTALLROOT")
        if not installroot:
            _err("--meta not specified and $INSTALLROOT is not set")
        meta_path = os.path.join(installroot, ".meta.json")

    if not os.path.exists(meta_path):
        _err(f".meta.json not found at {meta_path}")

    if args.list_vars:
        all_vars = collect_vars(meta_path)
        print("Available variables:")
        for k, v in sorted(all_vars.items()):
            print(f"  %({k})s  ->  {v}")
        return

    if not args.file:
        _err("file argument is required unless --list-vars is used")

    if not os.path.exists(args.file):
        _err(f"file not found: {args.file}")

    with open(args.file) as f:
        data = f.read()

    sys.stdout.write(resolve_from_meta(meta_path, data))


if __name__ == "__main__":
    main()
