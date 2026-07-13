#!/usr/bin/env python3
"""
trajectory_audit.py — retrieval-vs-derivation audit for one run's transcript
(environment sealing v1; companion to native_audit.py's execution audit).

Answers the question native_audit cannot: did the agent DERIVE the graded
quantities from its own computation, or RETRIEVE them (database query,
literature lookup on the target system)? Sealed answers protect the key;
this audits the *path to the number*.

Inputs
------
1. A run transcript. Two formats are honored, matching the native harnesses:
   * structured — Claude Code stream-json JSONL (``loop_transcript.jsonl`` /
     ``transcript.jsonl``): tool_use blocks in ``assistant`` events,
     tool_result blocks in ``user`` events. Full enforcement.
   * raw — codex/grok ``transcript.log`` (one JSON provenance header, then
     free CLI text). Tool inputs and outputs are indistinguishable, so raw
     findings are CAPPED at SUSPECT — never auto-VOID on a raw line.
2. A per-task environment-contract JSON, supplied AT RUNTIME from the private
   task store. The module is pure mechanism: every task-specific pattern,
   phrase, and sealed value arrives as contract data; nothing task-specific
   is embedded here.
3. Optionally the run's ``reported_values.json`` (for the provenance-gap pass).

Contract schema (machine fields; a full task JSON also loads — fields are
merged from top level → ``environment_contract`` → ``environment_contract.audit``
→ ``audit``, later wins):

    {
      "task_id": "TASK-XX",
      "allowed_patterns":  ["(?i)docs\\.example\\.org", ...],   # regex over tool-call descriptor
      "blocked_patterns":  ["(?i)materialsproject", ...],       # match => VIOLATION
      "retrieval_patterns": ["(?i)my-db-cli", ...],             # extend the built-in retrieval taxonomy
      "lookup_phrases": [                                       # target system names + close analogues
        "(?i)fictitium oxide",
        {"pattern": "(?i)Xy2Zr", "label": "target system", "severity": "violation"}
      ],
      "target_values": [                                        # SEALED — never echoed into the report
        {"key": "Ex_eV", "value": 3.21, "rel_window": 0.02}     # (synthetic example)
      ],
      "numeric_window_rel": 0.02,     # default rel window for target_values
      "provenance_rel_tol": 0.005,    # reported value vs computation output (rounding slack)
      "provenance_abs_tol": 1e-6      # used when the reported value is ~0
    }

Detection passes
----------------
1. Tool-surface scan — every tool call's descriptor (tool name + rendered
   input) is classified: ``blocked_patterns`` match => VIOLATION;
   ``allowed_patterns`` match => INFO (recorded, not held against the run);
   otherwise, if the call is a retrieval surface (built-in taxonomy of web
   search/fetch/browser + materials/chemistry databases + paper search,
   extendable via ``retrieval_patterns``) => SUSPECT (unlisted retrieval).
2. Lookup-phrase scan — contract phrases matched over RETRIEVAL-surface
   calls only (the target's name legitimately saturates the agent's own
   scripts): phrase in a retrieval INPUT (the query) => VIOLATION by default
   (per-phrase ``severity`` overrides); phrase in a retrieval OUTPUT (fetched
   content mentions the target) => SUSPECT. Context snippets are captured.
3. Numeric-proximity heuristic — numbers in RETRIEVAL outputs within a
   relative window of a sealed graded value => SUSPECT, never VIOLATION
   (proximity is circumstantial). REDACTED: the report names the graded key
   and the location only — never the sealed value, never the matched text.
4. Provenance gap — each numeric reported value must appear (within rounding
   slack) in at least one NON-retrieval tool output (Bash stdout, file read,
   ...). A graded number that never surfaces in any computation output
   "appeared from nowhere" => SUSPECT.

Verdict: VIOLATION (auto-VOID) > SUSPECT (human adjudication) > CLEAN.
INFO findings never move the verdict.

Prints one JSON report (sealed-value hygiene: contract values are never
serialized into it); ``--brief`` adds a one-line summary, ``--human`` a
per-finding listing (both stderr). Exit code: 0 CLEAN / 1 SUSPECT /
2 VIOLATION. STDLIB only. CLI + importable.

Usage:  python3 trajectory_audit.py <rep_dir|transcript> --contract <contract.json>
                [--values reported_values.json] [--brief] [--human]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from bisect import bisect_left
from dataclasses import asdict, dataclass
from pathlib import Path

CLEAN, SUSPECT, VIOLATION = "CLEAN", "SUSPECT", "VIOLATION"
INFO = "INFO"
_SEVERITY_RANK = {INFO: 0, SUSPECT: 1, VIOLATION: 2}

# Built-in retrieval-surface taxonomy (generic infrastructure — task-specific
# surfaces come in via the contract). Two layers: harness tool NAMES, and
# text patterns over the rendered input (URLs, DB clients, fetch commands).
_RETRIEVAL_TOOL_NAME_RE = re.compile(
    r"(?i)\b(web[-_ ]?search|web[-_ ]?fetch|browser|playwright|"
    r"semantic[-_ ]?scholar|paper[-_ ]?(search|fetch)|literature|"
    r"materials[-_ ]?(project|database)|pubchem|oqmd|aflow|nist)\b"
)
_RETRIEVAL_TEXT_RE = re.compile(
    r"(?i)("
    r"https?://[^\s\"']*(materialsproject\.org|oqmd\.org|aflow(lib)?\.org|"
    r"pubchem\.ncbi\.nlm\.nih\.gov|webbook\.nist\.gov|cccbdb\.nist\.gov|"
    r"semanticscholar\.org|arxiv\.org|doi\.org|crossref\.org|"
    r"scholar\.google|atct\.anl\.gov)"
    r"|\bMPRester\b|\bmp[-_]api\b"
    r"|\b(curl|wget)\s+[^\n]*https?://"
    r")"
)
_NUMBER_RE = re.compile(r"(?<![\w.\-])-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w.])")
_CTX_PAD = 60


class ContractError(ValueError):
    """The environment contract is missing or malformed."""


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

_CONTRACT_FIELDS = (
    "task_id", "allowed_patterns", "blocked_patterns", "retrieval_patterns",
    "lookup_phrases", "target_values", "numeric_window_rel",
    "provenance_rel_tol", "provenance_abs_tol",
)


@dataclass
class Phrase:
    regex: re.Pattern
    label: str
    input_severity: str  # severity of a match in a retrieval INPUT


@dataclass
class TargetValue:
    key: str
    value: float
    rel_window: float
    abs_window: float | None = None

    def matches(self, n: float) -> bool:
        if self.abs_window is not None:
            return abs(n - self.value) <= self.abs_window
        return abs(n - self.value) <= self.rel_window * abs(self.value)


class Contract:
    """Compiled per-task audit contract. Holds the SEALED target values —
    nothing here may be serialized into the public report."""

    def __init__(self, data: dict):
        merged: dict = {}
        env = data.get("environment_contract") or {}
        for layer in (data, env, env.get("audit") or {}, data.get("audit") or {}):
            if isinstance(layer, dict):
                merged.update({k: v for k, v in layer.items() if k in _CONTRACT_FIELDS})
        self.task_id: str | None = merged.get("task_id") or data.get("id")
        try:
            self.allowed = [re.compile(p) for p in merged.get("allowed_patterns") or []]
            self.blocked = [re.compile(p) for p in merged.get("blocked_patterns") or []]
            self.retrieval_extra = [re.compile(p) for p in merged.get("retrieval_patterns") or []]
        except re.error as e:
            raise ContractError(f"bad contract regex: {e}") from e
        self.numeric_window_rel = float(merged.get("numeric_window_rel", 0.02))
        self.provenance_rel_tol = float(merged.get("provenance_rel_tol", 0.005))
        self.provenance_abs_tol = float(merged.get("provenance_abs_tol", 1e-6))

        self.phrases: list[Phrase] = []
        for entry in merged.get("lookup_phrases") or []:
            if isinstance(entry, str):
                entry = {"pattern": entry}
            sev = str(entry.get("severity", VIOLATION)).upper()
            if sev not in (SUSPECT, VIOLATION):
                raise ContractError(f"phrase severity must be SUSPECT|VIOLATION, got {sev!r}")
            try:
                rx = re.compile(entry["pattern"])
            except (re.error, KeyError) as e:
                raise ContractError(f"bad lookup phrase {entry!r}: {e}") from e
            self.phrases.append(Phrase(rx, entry.get("label", entry["pattern"]), sev))

        self.targets: list[TargetValue] = []
        for tv in merged.get("target_values") or []:
            try:
                self.targets.append(TargetValue(
                    key=str(tv["key"]), value=float(tv["value"]),
                    rel_window=float(tv.get("rel_window", self.numeric_window_rel)),
                    abs_window=(float(tv["abs_window"]) if "abs_window" in tv else None),
                ))
            except (KeyError, TypeError, ValueError) as e:
                raise ContractError(f"bad target_values entry {tv!r}: {e}") from e

    def is_retrieval(self, descriptor: str) -> bool:
        return bool(_RETRIEVAL_TOOL_NAME_RE.search(descriptor)
                    or _RETRIEVAL_TEXT_RE.search(descriptor)
                    or any(rx.search(descriptor) for rx in self.retrieval_extra))


def load_contract(path: str | Path) -> Contract:
    """Load a contract from an audit-contract JSON or a full task JSON."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as e:
        raise ContractError(f"cannot load contract {path}: {e}") from e
    if not isinstance(data, dict):
        raise ContractError(f"contract {path} is not a JSON object")
    return Contract(data)


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    line: int        # 1-based transcript line of the triggering event
    code: str        # BLOCKED_SURFACE | UNLISTED_RETRIEVAL | ALLOWED_SURFACE |
                     # LOOKUP_PHRASE | LOOKUP_PHRASE_OUTPUT | NUMERIC_PROXIMITY |
                     # PROVENANCE_GAP  ("+_RAW" suffix on raw-mode lines)
    severity: str    # INFO | SUSPECT | VIOLATION
    tool: str        # tool name, or "raw" for unstructured lines
    detail: str      # human explanation — REDACTED-safe (no sealed values)
    context: str = ""  # snippet around the match; ALWAYS empty for numeric hits


def _snippet(text: str, start: int, end: int, pad: int = _CTX_PAD) -> str:
    s = text[max(0, start - pad):min(len(text), end + pad)]
    return re.sub(r"\s+", " ", s).strip()[: 2 * pad + (end - start)]


def _tool_result_text(content) -> str:
    """Flatten a tool_result content field (string, or list of typed blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


# ---------------------------------------------------------------------------
# The audit
# ---------------------------------------------------------------------------

def audit_transcript(transcript: str | Path, contract: Contract,
                     reported_values: dict | None = None) -> dict:
    """Run all detection passes over one transcript. Returns the report dict
    (JSON-serializable; contains NO sealed contract values)."""
    tpath = Path(transcript)
    findings: list[Finding] = []
    tools_by_id: dict[str, tuple[str, bool]] = {}  # tool_use_id -> (name, is_retrieval)
    n_events = n_tool_calls = n_retrieval = n_raw = 0
    # provenance corpus: numbers seen in non-retrieval (computation) outputs
    comp_numbers: list[float] = []

    def scan_phrases(text: str, line: int, tool: str, is_input: bool, cap: str | None):
        for ph in contract.phrases:
            m = ph.regex.search(text)
            if not m:
                continue
            sev = ph.input_severity if is_input else SUSPECT
            code = "LOOKUP_PHRASE" if is_input else "LOOKUP_PHRASE_OUTPUT"
            if cap and _SEVERITY_RANK[sev] > _SEVERITY_RANK[cap]:
                sev, code = cap, code + "_RAW"
            where = "retrieval input (query)" if is_input else "retrieval output (fetched content)"
            findings.append(Finding(
                line, code, sev, tool,
                f"lookup phrase '{ph.label}' matched in {where}",
                _snippet(text, m.start(), m.end())))

    def scan_numeric(text: str, line: int, tool: str):
        # SUSPECT-only heuristic; REDACTED — never echo the value or the match.
        hit_keys: set[str] = set()
        for m in _NUMBER_RE.finditer(text):
            try:
                n = float(m.group())
            except ValueError:
                continue
            for tv in contract.targets:
                if tv.key not in hit_keys and tv.matches(n):
                    hit_keys.add(tv.key)
        for key in sorted(hit_keys):
            findings.append(Finding(
                line, "NUMERIC_PROXIMITY", SUSPECT, tool,
                f"retrieval output contains a number inside the graded window "
                f"of key '{key}' (value and match REDACTED)"))

    def harvest_numbers(text: str):
        for m in _NUMBER_RE.finditer(text):
            try:
                comp_numbers.append(float(m.group()))
            except ValueError:
                pass

    if not tpath.is_file():
        return {"transcript": str(tpath), "task_id": contract.task_id,
                "verdict": SUSPECT, "flags": ["NO_TRANSCRIPT"], "findings": []}

    for lineno, raw in enumerate(tpath.open(encoding="utf-8", errors="replace"), 1):
        raw = raw.rstrip("\n")
        if not raw.strip():
            continue
        try:
            ev = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            ev = None
        if not isinstance(ev, dict) or "type" not in ev:
            # ---- raw mode (codex/grok transcript.log body, or header line) —
            # inputs/outputs indistinguishable: every finding capped at SUSPECT.
            if isinstance(ev, dict):
                continue  # harness provenance header — metadata, not activity
            n_raw += 1
            is_retr = contract.is_retrieval(raw)
            for rx in contract.blocked:
                m = rx.search(raw)
                if m:
                    findings.append(Finding(
                        lineno, "BLOCKED_SURFACE_RAW", SUSPECT, "raw",
                        f"blocked pattern '{rx.pattern}' on a raw transcript line "
                        "(unstructured: cannot confirm a tool call — adjudicate)",
                        _snippet(raw, m.start(), m.end())))
                    break
            if is_retr:
                n_retrieval += 1
                scan_phrases(raw, lineno, "raw", is_input=True, cap=SUSPECT)
                scan_numeric(raw, lineno, "raw")
            else:
                harvest_numbers(raw)
            continue

        # ---- structured stream-json event ----
        n_events += 1
        t = ev.get("type")
        content = (ev.get("message") or {}).get("content") or []
        if t == "assistant":
            for b in content:
                if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                    continue
                n_tool_calls += 1
                name = str(b.get("name", "?"))
                try:
                    rendered = json.dumps(b.get("input") or {}, sort_keys=True)
                except (TypeError, ValueError):
                    rendered = str(b.get("input"))
                descriptor = f"{name} {rendered}"
                is_retr = contract.is_retrieval(descriptor)
                blocked_rx = next((rx for rx in contract.blocked if rx.search(descriptor)), None)
                allowed_rx = None if blocked_rx else next(
                    (rx for rx in contract.allowed if rx.search(descriptor)), None)
                if blocked_rx:
                    m = blocked_rx.search(descriptor)
                    findings.append(Finding(
                        lineno, "BLOCKED_SURFACE", VIOLATION, name,
                        f"tool call matches blocked pattern '{blocked_rx.pattern}'",
                        _snippet(descriptor, m.start(), m.end())))
                elif allowed_rx:
                    findings.append(Finding(
                        lineno, "ALLOWED_SURFACE", INFO, name,
                        f"retrieval-class call matches allowed pattern '{allowed_rx.pattern}'"))
                elif is_retr:
                    findings.append(Finding(
                        lineno, "UNLISTED_RETRIEVAL", SUSPECT, name,
                        "retrieval-surface call matches neither the contract's "
                        "allowed nor blocked lists — adjudicate",
                        _snippet(descriptor, 0, min(len(descriptor), 80))))
                if is_retr or blocked_rx:
                    n_retrieval += 1
                    scan_phrases(descriptor, lineno, name, is_input=True, cap=None)
                if b.get("id"):
                    tools_by_id[b["id"]] = (name, bool(is_retr or blocked_rx))
        elif t == "user":
            for b in content:
                if not (isinstance(b, dict) and b.get("type") == "tool_result"):
                    continue
                name, is_retr = tools_by_id.get(b.get("tool_use_id"), ("?", False))
                text = _tool_result_text(b.get("content"))
                if not text:
                    continue
                if is_retr:
                    scan_phrases(text, lineno, name, is_input=False, cap=None)
                    scan_numeric(text, lineno, name)
                else:
                    harvest_numbers(text)  # computation output → provenance corpus

    # ---- pass 4: provenance gap (reported number never left a computation tool)
    if reported_values:
        comp_numbers.sort()
        for key, val in sorted(reported_values.items()):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                continue
            v = float(val)
            tol = (contract.provenance_abs_tol if v == 0
                   else contract.provenance_rel_tol * abs(v))
            i = bisect_left(comp_numbers, v - tol)
            if not (i < len(comp_numbers) and comp_numbers[i] <= v + tol):
                findings.append(Finding(
                    0, "PROVENANCE_GAP", SUSPECT, "-",
                    f"reported value '{key}' never appears in any computation "
                    f"tool output (rel_tol={contract.provenance_rel_tol}) — "
                    "the number has no visible derivation"))

    worst = max((_SEVERITY_RANK[f.severity] for f in findings), default=0)
    verdict = {0: CLEAN, 1: SUSPECT, 2: VIOLATION}[worst]
    counts = {sev: sum(1 for f in findings if f.severity == sev)
              for sev in (VIOLATION, SUSPECT, INFO)}
    return {
        "transcript": str(tpath), "task_id": contract.task_id, "verdict": verdict,
        "events": n_events, "raw_lines": n_raw, "tool_calls": n_tool_calls,
        "retrieval_calls": n_retrieval, "counts": counts,
        "findings": [asdict(f) for f in findings], "flags": [],
    }


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------

_TRANSCRIPT_CANDIDATES = (
    "loop_transcript.jsonl", "transcript.jsonl", "transcript.log",
    "ws/loop_transcript.jsonl", "ws/transcript.jsonl", "ws/transcript.log",
)


def resolve_transcript(path: str | Path) -> Path:
    """Accept a transcript file, a ws dir, or a rep dir (native_audit style)."""
    p = Path(path)
    if p.is_file():
        return p
    if p.is_dir():
        for cand in _TRANSCRIPT_CANDIDATES:
            if (p / cand).is_file():
                return p / cand
    return p  # missing → audit_transcript reports NO_TRANSCRIPT


def resolve_values(path: str | Path, explicit: str | None) -> dict | None:
    if explicit:
        return json.loads(Path(explicit).read_text(encoding="utf-8"))
    p = Path(path)
    root = p if p.is_dir() else p.parent
    for cand in ("reported_values.json", "ws/reported_values.json"):
        f = root / cand
        if f.is_file():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                return None
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Retrieval-vs-derivation trajectory audit (environment sealing v1).")
    ap.add_argument("path", help="rep dir, ws dir, or transcript file")
    ap.add_argument("--contract", required=True,
                    help="per-task environment-contract JSON (or full task JSON)")
    ap.add_argument("--values", default=None,
                    help="reported_values.json (default: found next to the transcript)")
    ap.add_argument("--brief", action="store_true", help="one-line summary on stderr")
    ap.add_argument("--human", action="store_true", help="per-finding listing on stderr")
    a = ap.parse_args(argv)

    contract = load_contract(a.contract)
    transcript = resolve_transcript(a.path)
    values = resolve_values(a.path, a.values)
    rec = audit_transcript(transcript, contract, values)
    print(json.dumps(rec))

    if a.brief or a.human:
        c = rec.get("counts", {})
        print(f"TRAJ-AUDIT {rec.get('task_id') or '?'} {Path(a.path).name}: "
              f"{rec['verdict']} — {c.get(VIOLATION, 0)} violation(s), "
              f"{c.get(SUSPECT, 0)} suspect(s), {c.get(INFO, 0)} info "
              f"({rec.get('retrieval_calls', 0)} retrieval calls / "
              f"{rec.get('tool_calls', 0)} tool calls)", file=sys.stderr)
    if a.human:
        for f in rec["findings"]:
            ctx = f" — \"{f['context']}\"" if f["context"] else ""
            print(f"  L{f['line']:<6} {f['severity']:<9} {f['code']:<22} "
                  f"[{f['tool']}] {f['detail']}{ctx}", file=sys.stderr)

    return {CLEAN: 0, SUSPECT: 1, VIOLATION: 2}[rec["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
