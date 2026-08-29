"""
Smoke test for the template, runnable without an API key.

The template's selling point is that a chain produced by the agent verifies
offline, and that a tampered chain does not. Both halves are asserted here.

src.agent is deliberately not imported. It constructs a ChatAnthropic client
at module scope, so importing it would require a live key and would turn a
missing secret into a failing build. Everything below the model, which is all
of the Context Passport wiring, runs with no network and no credentials: the
recorder is driven through the LangChain callback lifecycle directly, exactly
as LangGraph would drive it during a real run.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


def _run_agent_steps(workdir: Path, steps: int = 3) -> int:
    """Drive the recorder through a chain of steps and return the passport count."""
    from src.recorder import make_recorder

    handler = make_recorder(trace_id="trace_smoke")
    for i in range(steps):
        run_id = uuid.uuid4()
        handler.on_chain_start({"name": f"node_{i}"}, {"question": f"q{i}"}, run_id=run_id)
        handler.on_chain_end({"answer": f"a{i}"}, run_id=run_id)

    return len(list((workdir / "passports").glob("*.json")))


def _verify(passports: Path, repo_root: Path) -> int:
    """Run the verifier the way the README tells an auditor to run it."""
    result = subprocess.run(
        [sys.executable, "-m", "src.verify", str(passports)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        # The recorder writes to ./passports and ./.keys relative to the cwd,
        # so run from a scratch directory rather than dirtying the checkout.
        import os

        os.chdir(workdir)
        sys.path.insert(0, str(repo_root))

        count = _run_agent_steps(workdir)
        if count != 3:
            print(f"FAIL: expected 3 passports, got {count}", file=sys.stderr)
            return 1
        print(f"ok: recorder produced {count} signed passports")

        passports = workdir / "passports"

        if _verify(passports, repo_root) != 0:
            print("FAIL: a chain the template just produced did not verify", file=sys.stderr)
            return 1
        print("ok: the produced chain verifies")

        # A verifier that passes everything is not a verifier. Edit one
        # record's payload and require the run to fail.
        victim = sorted(passports.glob("*.json"))[0]
        record = json.loads(victim.read_text(encoding="utf-8"))
        record["payload"]["output"] = "tampered"
        victim.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")

        if _verify(passports, repo_root) == 0:
            print("FAIL: verifier accepted a chain with an edited payload", file=sys.stderr)
            return 1
        print("ok: the verifier rejects an edited payload")

    print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
