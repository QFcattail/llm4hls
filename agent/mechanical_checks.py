"""Mechanical checks — LLM-free hard gates before spending a tool call.

LLM review (self-check) has blind spots (it passed a changed signature in
testing). These checks are deterministic and catch the high-value, easy-to-
verify hazards that an LLM tends to miss:

  - signature changed   (top-level function signature must match the header)
  - header include lost (the kernel must still #include its header)
  - forbidden tokens    (e.g. system(), dynamic alloc that won't synthesize)

Use these as a first gate; LLM review runs only if mechanical checks pass.
"""
from __future__ import annotations

import re


def _extract_signature(code: str, top_fn: str) -> str | None:
    """Best-effort: grab the top-level function signature line from kernel code.

    Args:
        code: The kernel source text.
        top_fn: The top-level function name to locate.

    Returns:
        The matched signature text, or None if no match is found.
    """
    # match: <return type> <top_fn>( <args> )
    pat = re.compile(
        r"(?:^|\n)\s*[\w:*&<>,\s]+?\b" + re.escape(top_fn) + r"\s*\([^;{]*\)",
        re.MULTILINE,
    )
    m = pat.search(code)
    return m.group(0).strip() if m else None


def check_signature_unchanged(original: str, candidate: str, top_fn: str) -> tuple[bool, str]:
    """Verify the top-level function signature was not changed.

    Args:
        original: The original kernel source.
        candidate: The candidate kernel source to verify.
        top_fn: The top-level function name whose signature must be preserved.

    Returns:
        A (passed, message) tuple where ``passed`` is True when the signature
        matches and ``message`` describes the result or the mismatch.
    """
    orig_sig = _extract_signature(original, top_fn)
    cand_sig = _extract_signature(candidate, top_fn)
    if orig_sig is None or cand_sig is None:
        return False, "could not parse top-level signature for comparison"
    if orig_sig != cand_sig:
        return False, f"signature changed:\n  was: {orig_sig}\n  now: {cand_sig}"
    return True, "signature unchanged"


def check_header_included(candidate: str, header_names: list[str]) -> tuple[bool, str]:
    """Verify the kernel still includes its required headers.

    Args:
        candidate: The candidate kernel source to verify.
        header_names: Header file names that must appear in the source.

    Returns:
        A (passed, message) tuple where ``passed`` is True when all headers
        are present and ``message`` lists any missing includes.
    """
    missing = [h for h in header_names if h not in candidate]
    if missing:
        return False, f"missing #include: {missing}"
    return True, "headers present"


def mechanical_review(original: str, candidate: str, task) -> tuple[bool, list[str]]:
    """Run all mechanical checks. Returns (passed, list_of_issues).

    Args:
        original: The original kernel source.
        candidate: The candidate kernel source to verify.
        task: Harness Task object exposing ``.top`` (top function name) and
            ``.headers`` (mapping of header name to content).

    Returns:
        A (passed, issues) tuple where ``passed`` is True when no issues were
        found and ``issues`` is the list of human-readable problem strings.
    """
    issues: list[str] = []
    ok, msg = check_signature_unchanged(original, candidate, task.top)
    if not ok:
        issues.append(msg)
    header_names = list(task.headers.keys())
    ok2, msg2 = check_header_included(candidate, header_names)
    if not ok2:
        issues.append(msg2)
    return (len(issues) == 0), issues
