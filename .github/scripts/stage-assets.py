#!/usr/bin/env python3
"""Validate successful outputs; never publish invented data or an API error card."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

EXPECTED = {
    "snake-light.svg": "SNAKE_OUTCOME",
    "snake-dark.svg": "SNAKE_OUTCOME",
    "stats-light.svg": "STATS_LIGHT_OUTCOME",
    "stats-dark.svg": "STATS_DARK_OUTCOME",
    "languages-light.svg": "LANGUAGES_LIGHT_OUTCOME",
    "languages-dark.svg": "LANGUAGES_DARK_OUTCOME",
    "streak-light.svg": "STREAK_LIGHT_OUTCOME",
    "streak-dark.svg": "STREAK_DARK_OUTCOME",
}
ERROR_PHRASES = (
    "something went wrong", "could not fetch", "api rate limit",
    "rate limit exceeded", "unable to fetch", "failed to fetch",
    "could not resolve to a user", "user not found",
)


def main() -> int:
    source = Path(".generated")
    ready = Path(os.environ["RUNNER_TEMP"]) / "profile-ready"
    ready.mkdir(parents=True, exist_ok=True)
    # Only expected names are touched; unrelated files are not removed.
    for name in EXPECTED:
        (ready / name).unlink(missing_ok=True)
    valid: list[str] = []
    failed: list[str] = []
    for name, outcome_key in EXPECTED.items():
        path = source / name
        try:
            if os.environ.get(outcome_key) != "success":
                raise ValueError("generator did not finish successfully")
            if path.is_symlink() or not path.is_file():
                raise ValueError("generator did not produce a regular file")
            if not 50 <= path.stat().st_size <= 5_000_000:
                raise ValueError("invalid output size")
            root = ET.parse(path).getroot()
            if root.tag != "{http://www.w3.org/2000/svg}svg":
                raise ValueError("output is not an SVG image")
            visible_text = " ".join(root.itertext()).lower()
            if any(phrase in visible_text for phrase in ERROR_PHRASES):
                raise ValueError("output appears to be an API error card")
            shutil.copy2(path, ready / name)
            valid.append(name)
        except (OSError, ValueError, ET.ParseError) as exc:
            failed.append(name)
            print(f"::warning::{name}: {exc}")
    summary = ["## Profile visuals", "", f"Validated: {len(valid)}/{len(EXPECTED)} images.", ""]
    summary += [f"- Generated: `{name}`" for name in valid]
    summary += [f"- Not refreshed: `{name}` (previous version is preserved, if present)" for name in failed]
    summary += ["", "Only generator results are published. No replacement statistics are invented."]
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write("\n".join(summary) + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            handle.write(f"partial={'true' if failed else 'false'}\n")
    if not valid:
        print("::error::No valid images were produced. Nothing will be published.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
