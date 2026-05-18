"""
Offline chain verifier for Context Passports produced by this template.

Usage:
    python -m src.verify ./passports/

This is the verifier a regulator or auditor would run. It needs only:
  - the passport JSON files
  - access to the embedded public_key field in each passport

It does NOT need:
  - network access
  - the agent runtime
  - any vendor service

Exits with code 0 if all checks pass, 1 if any check fails.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from context_passport import verify_chain
from context_passport.signing import verify_signature


def load_passports(directory: Path) -> list[dict]:
    """Load all passport JSON files, sorted by id (which is timestamp-prefixed)."""
    files = sorted(directory.glob("*.json"))
    out = []
    for f in files:
        with f.open(encoding="utf-8") as fp:
            out.append(json.load(fp))
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m src.verify <passports-directory>", file=sys.stderr)
        return 2

    directory = Path(sys.argv[1])
    if not directory.is_dir():
        print(f"Not a directory: {directory}", file=sys.stderr)
        return 2

    passports = load_passports(directory)
    if not passports:
        print(f"No passports found in {directory}.", file=sys.stderr)
        return 1

    print(f"Loaded {len(passports)} passports from {directory}")

    # Group by trace_id for chain-by-chain verification.
    chains: dict[str | None, list[dict]] = {}
    for p in passports:
        tid = p.get("trace_id")
        chains.setdefault(tid, []).append(p)

    all_ok = True
    for trace_id, chain in chains.items():
        # Ensure chain order: parent_id chain walk.
        ordered = _order_by_chain(chain)
        chain_ok = verify_chain(ordered)
        sig_results = [verify_signature(p) for p in ordered]
        sigs_ok = all(sig_results)

        label = trace_id or "(no trace_id)"
        print(f"\nTrace {label}:")
        print(f"  {len(ordered)} passports")
        print(f"  Integrity chain: {'OK' if chain_ok else 'BROKEN'}")
        print(f"  Signatures:      {sum(sig_results)}/{len(sig_results)} valid")

        if not chain_ok or not sigs_ok:
            all_ok = False

    print()
    if all_ok:
        print("All checks passed.")
        return 0
    else:
        print("Verification FAILED. Some checks did not pass.", file=sys.stderr)
        return 1


def _order_by_chain(chain: list[dict]) -> list[dict]:
    """Sort by parent_id linkage: root (parent_id=None) first, then each child."""
    by_id = {p["id"]: p for p in chain}
    roots = [p for p in chain if p.get("parent_id") is None]
    if not roots:
        # No root found — return as-is and let chain verifier fail
        return chain
    ordered = []
    current = roots[0]
    seen: set[str] = set()
    while current and current["id"] not in seen:
        ordered.append(current)
        seen.add(current["id"])
        # Find child whose parent_id is current.id
        children = [p for p in chain if p.get("parent_id") == current["id"]]
        current = children[0] if children else None
    # Append anything orphaned at the end (chain-verifier will catch breaks)
    for p in chain:
        if p["id"] not in seen:
            ordered.append(p)
    return ordered


if __name__ == "__main__":
    sys.exit(main())
