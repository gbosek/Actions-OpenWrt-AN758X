#!/usr/bin/env python3
"""Package existing static analysis; never reads or modifies target binaries."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.analysis_dir / "evidence"
    tools = args.analysis_dir / "tools"
    args.out.mkdir(parents=True, exist_ok=True)
    specs = (
        ("54", "ghidra-54-opaque-inventory.json", "0x3e901258",
         "5140747f2ce176ac6622522184651403594d4f5624bf2238543136a0f3bfe7b8",
         "d59db24e7d97453a689144a94d3b10cfb873197dfcbea0cb1d279d38cced87b1"),
        ("66", "ghidra-66-inventory.json", "0x3e901328",
         "d74aa2f81214fda24725529a6000bb05c22c2da6f40dfd63f0c20ef067db08af",
         "11013d492120f406586413bad2689305f2713da2f0ebdde21feaf03fc93b0e3a"),
        ("1456", "ghidra-1456-opaque-inventory.json", "0x3e9013a0",
         "6e7b9cb9769398d5c0a603d758626719ee83610e0dd2a5bc0b66258e2ad1057f",
         "0e742e7bef0d8f4c1537d7c17de9b601274e42b18660dfde6deba81ac395c761"),
    )
    exports = []
    for label, filename, gp, code_sha, data_sha in specs:
        source = evidence / filename
        value = json.loads(source.read_text())
        export = {
            "provider": value["provider"],
            "program": value["program"],
            "language": value["language"],
            "coverage_note": value["coverage_note"],
            "input_code_sha256": code_sha,
            "input_data_sha256": data_sha,
            "code_base": "0x84000000", "data_base": "0x3e900000", "gp": gp,
            "source_inventory": filename,
            "source_inventory_sha256": sha256(source),
            "source_decoded_instruction_count": len(value["decoded_instructions"]),
            "requested_entries": value["requested_entries"],
            "export_note": "All current function candidates unchanged, including errors/false positives. Decoded instructions remain in the full source inventory; not a REA evidence envelope.",
            "functions": value["functions"],
        }
        out_name = f"rv32-{label}-candidate-functions.json"
        write_json(args.out / out_name, export)
        exports.append({"file": out_name, "sha256": sha256(args.out / out_name)})

    source = evidence / "mailbox-api-ledger.json"
    ledger = json.loads(source.read_text())
    wired = {
        "provider": ledger["provider"], "scope": ledger["scope"],
        "source_ledger_sha256": sha256(source),
        "selection": "Static tunnel, ppe, and ppe_sram_api table records only; XG2010G has no WiFi.",
        "samples": [],
    }
    for sample in ledger["samples"]:
        selected = {key: value for key, value in sample.items() if key != "tables"}
        selected["tables"] = [table for table in sample["tables"]
                              if table["kind"] in ("tunnel", "ppe", "ppe_sram_api")]
        wired["samples"].append(selected)
    write_json(args.out / "wired-mailbox-api-ledger.json", wired)

    for filename in ("old-firmware-audit.md", "clanker-source-audit.md",
                     "npu-core-module-audit.md", "wired-control-audit.md", "ghidra-npu66-inventory.json",
                     "npu66-objdump.txt"):
        shutil.copyfile(evidence / filename, args.out / filename)
    target_tools = args.out / "tools"
    target_tools.mkdir(exist_ok=True)
    for filename in ("NpuInventory.java", "NpuModuleRepair.java", "NpuOldAudit.java",
                     "npu-rv32-opaque.ilp32d.slaspec", "npu-rv32-opaque.ldefs",
                     "prepare-comparison.py"):
        shutil.copyfile(tools / filename, target_tools / filename)

    full_names = ["ghidra-54-inventory.json", "ghidra-66-inventory.json",
                  "ghidra-1456-inventory.json", "ghidra-54-opaque-inventory.json",
                  "ghidra-1456-opaque-inventory.json", "ghidra-npu66-inventory.json",
                  "mailbox-api-ledger.json"]
    manifest = {
        "scope": "Static analysis exports, original target binaries excluded; no npu_wifi.ko analysis delivery.",
        "original_sample_hashes": [{"label": label, "code_sha256": c, "data_sha256": d}
                                   for label, _, _, c, d in specs],
        "exports": exports,
        "full_inventories": [{"file": name, "bytes": (evidence / name).stat().st_size,
                              "sha256": sha256(evidence / name)} for name in full_names],
    }
    write_json(args.out / "analysis-manifest.json", manifest)
    print(json.dumps({"out": str(args.out), "candidate_exports": len(exports),
                      "wired_table_records": sum(t["record_count"] for s in wired["samples"] for t in s["tables"])}))


if __name__ == "__main__":
    main()
