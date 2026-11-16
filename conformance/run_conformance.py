"""Implementation-independent conformance runner for SIPL."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> int:
    cases_path = Path(__file__).parent / "cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    passed = 0

    for case in cases:
        with tempfile.NamedTemporaryFile("w", suffix=".sipl", delete=False, encoding="utf-8") as tmp:
            tmp.write(case["source"])
            tmp_path = Path(tmp.name)

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "src.sipl.cli", "run", str(tmp_path), "--json"],
                capture_output=True,
                text=True,
            )
            if case["expect_valid"]:
                assert proc.returncode == 0, f"{case['id']} failed: {proc.stderr}"
                data = json.loads(proc.stdout)
                assert data["final_state"] == case["expected_state"], (
                    f"{case['id']} state mismatch: {data['final_state']} != {case['expected_state']}"
                )
            else:
                assert proc.returncode != 0, f"{case['id']} should have failed but succeeded"
            print(f"[PASS] {case['id']}: {case['description']}")
            passed += 1
        finally:
            tmp_path.unlink(missing_ok=True)

    print(f"\nConformance result: {passed}/{len(cases)} passed.")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())