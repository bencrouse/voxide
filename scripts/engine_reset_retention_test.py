#!/usr/bin/env python3
"""Native negative control: a reset failure must preserve its report and raw evidence."""
import json
from pathlib import Path
import subprocess
import sys
import uuid


def main():
    binary = Path(sys.argv[1])
    directory = Path(sys.argv[2]) / uuid.uuid4().hex
    directory.mkdir(parents=True, exist_ok=False)
    result = subprocess.run([str(binary), "--self-test-reset-failure-control", str(directory)], capture_output=True, text=True)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Native reset-silence gate failed" in result.stderr, result.stderr
    reports = set(directory.glob("*/report.json"))
    assert len(reports) == 1, reports
    path = reports.pop()
    report = json.loads(path.read_text())
    assert report["diagnostic_reset_failure_control"] is True
    assert report["adapter_contract"] == "pass"
    assert report["native_reset_silence_gate"] == "fail"
    assert report["native_repeat_observations"], "Earlier observations were lost"
    for observation in report["native_reset_silence_observations"]:
        assert observation["within_tolerance"] is False and observation["peak"] >= .25
        prefix = path.parent / ("reset-silence-failure-" + str(observation["window"]))
        for suffix in ("-voice1.f32", "-voice2.f32", "-voice3.f32", "-native.json", "-availability.csv", "-controls.csv", "-callbacks.csv"):
            assert Path(str(prefix) + suffix).stat().st_size > 0, suffix
    print("Reset failure correctly failed its native gate after retaining complete evidence:", path)


if __name__ == "__main__":
    main()
