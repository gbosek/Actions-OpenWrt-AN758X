#!/usr/bin/env python3
"""Validate unified-diff hunk line counts before an expensive firmware build."""

from __future__ import annotations

import re
import sys
from pathlib import Path

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def validate(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    errors: list[str] = []
    i = 0

    while i < len(lines):
        m = HUNK.match(lines[i])
        if not m:
            i += 1
            continue

        old_need = int(m.group(2) or "1")
        new_need = int(m.group(4) or "1")
        old_got = new_got = 0
        start = i + 1
        i += 1

        while i < len(lines) and (old_got < old_need or new_got < new_need):
            line = lines[i]
            if not line:
                errors.append(
                    f"{path}:{i + 1}: unprefixed empty line inside hunk "
                    f"starting at line {start}"
                )
                break

            prefix = line[0]
            if prefix == " ":
                old_got += 1
                new_got += 1
            elif prefix == "-":
                old_got += 1
            elif prefix == "+":
                new_got += 1
            elif prefix == "\\":
                # "\ No newline at end of file" does not consume a diff line.
                pass
            else:
                errors.append(
                    f"{path}:{i + 1}: invalid hunk line prefix {prefix!r} "
                    f"(hunk starts at line {start})"
                )
                break

            if old_got > old_need or new_got > new_need:
                errors.append(
                    f"{path}:{start}: hunk count exceeded: "
                    f"expected old/new {old_need}/{new_need}, "
                    f"got {old_got}/{new_got}"
                )
                break
            i += 1
        else:
            if old_got != old_need or new_got != new_need:
                errors.append(
                    f"{path}:{start}: hunk count mismatch: "
                    f"expected old/new {old_need}/{new_need}, "
                    f"got {old_got}/{new_got}"
                )

        # If the loop stopped on an error, advance so validation can continue.
        if i == start - 1:
            i += 1

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} PATCH...", file=sys.stderr)
        return 2

    failed = False
    for arg in sys.argv[1:]:
        path = Path(arg)
        errors = validate(path)
        if errors:
            failed = True
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
        else:
            print(f"OK: {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
