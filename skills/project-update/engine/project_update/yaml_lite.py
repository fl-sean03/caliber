"""Minimal YAML reader — stdlib only.

The project-update engine's runtime must not depend on PyYAML (HPC + no-conda
portability). The per-project manifest uses a small, predictable YAML subset, so
we parse it ourselves.

Supported subset (enough for .sync/manifest.yaml):
  - nested mappings via 2-space indentation
  - lists of scalars (`- value`) and lists of mappings (`- key: value`)
  - inline flow lists on one line: `key: [a, b, c]`
  - scalars: str, int, float, bool (true/false), null (~, null, empty)
  - `#` comments and blank lines
  - single/double quoted strings (quotes stripped)

NOT supported (rejected or ignored): anchors/aliases, multi-doc `---`,
block scalars (`|`, `>`), complex keys. If a manifest ever needs those,
swap this for PyYAML behind the same `load()` signature.
"""
from __future__ import annotations

from typing import Any


def _scalar(token: str) -> Any:
    t = token.strip()
    if t == "" or t in ("~", "null", "None"):
        return None
    if (t[0] == '"' and t[-1] == '"') or (t[0] == "'" and t[-1] == "'"):
        return t[1:-1]
    low = t.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    return t


def _flow_list(token: str) -> list:
    inner = token.strip()[1:-1].strip()
    if not inner:
        return []
    return [_scalar(p) for p in inner.split(",")]


def _strip_comment(line: str) -> str:
    """Remove trailing `#` comment unless inside quotes."""
    out = []
    in_s = in_d = False
    for ch in line:
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d:
            break
        out.append(ch)
    return "".join(out).rstrip()


class _Line:
    __slots__ = ("indent", "text", "raw")

    def __init__(self, indent: int, text: str, raw: str):
        self.indent = indent
        self.text = text
        self.raw = raw


def _tokenize(src: str) -> list[_Line]:
    lines: list[_Line] = []
    for raw in src.splitlines():
        stripped_comment = _strip_comment(raw)
        if not stripped_comment.strip():
            continue
        indent = len(stripped_comment) - len(stripped_comment.lstrip(" "))
        lines.append(_Line(indent, stripped_comment.strip(), raw))
    return lines


def _parse_block(lines: list[_Line], i: int, indent: int) -> tuple[Any, int]:
    """Parse a block at the given indent; return (value, next_index)."""
    if i >= len(lines):
        return None, i
    first = lines[i]
    is_list = first.text.startswith("- ")

    if is_list:
        result: list = []
        while i < len(lines) and lines[i].indent == indent and lines[i].text.startswith("- "):
            item_text = lines[i].text[2:].strip()
            if ":" in item_text and not item_text.startswith("["):
                mapping: dict = {}
                key, _, rest = item_text.partition(":")
                rest = rest.strip()
                child_indent = indent + 2
                if rest.startswith("[") and rest.endswith("]"):
                    mapping[key.strip()] = _flow_list(rest)
                    i += 1
                elif rest == "":
                    val, i = _parse_block(lines, i + 1, _next_indent(lines, i + 1, child_indent))
                    mapping[key.strip()] = val
                else:
                    mapping[key.strip()] = _scalar(rest)
                    i += 1
                while i < len(lines) and lines[i].indent >= child_indent and not lines[i].text.startswith("- "):
                    if lines[i].indent == child_indent:
                        k, v, i = _parse_kv(lines, i, child_indent)
                        mapping[k] = v
                    else:
                        break
                result.append(mapping)
            else:
                result.append(_scalar(item_text))
                i += 1
        return result, i

    mapping = {}
    while i < len(lines) and lines[i].indent == indent and not lines[i].text.startswith("- "):
        k, v, i = _parse_kv(lines, i, indent)
        mapping[k] = v
    return mapping, i


def _next_indent(lines: list[_Line], i: int, default: int) -> int:
    if i < len(lines):
        return lines[i].indent
    return default


def _parse_kv(lines: list[_Line], i: int, indent: int) -> tuple[str, Any, int]:
    text = lines[i].text
    key, _, rest = text.partition(":")
    key = key.strip()
    rest = rest.strip()
    if rest.startswith("[") and rest.endswith("]"):
        return key, _flow_list(rest), i + 1
    if rest != "":
        return key, _scalar(rest), i + 1
    if i + 1 < len(lines) and lines[i + 1].indent > indent:
        val, i = _parse_block(lines, i + 1, lines[i + 1].indent)
        return key, val, i
    return key, None, i + 1


def loads(src: str) -> Any:
    lines = _tokenize(src)
    if not lines:
        return {}
    val, _ = _parse_block(lines, 0, lines[0].indent)
    return val


def load_file(path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return loads(fh.read())
