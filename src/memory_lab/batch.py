"""Run a balanced series of independent policy-memory experiments."""

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

from .experiment import Config, REPORT_ROOT, run


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_mode: dict[str, dict[str, Any]] = {}
    for mode in ("explicit", "implicit"):
        group = [row for row in rows if row["mode"] == mode]
        count = len(group)
        completed = [row for row in group if "first" in row]
        by_mode[mode] = {
            "runs": count,
            "completed": len(completed),
            "model_or_runtime_errors": count - len(completed),
            "policy_persisted": sum(row["first"]["poison_persisted"] is not None for row in completed),
            "policy_retrieved": sum(row["first"]["poison_retrieved"] is not None for row in completed),
            "virtual_impacts": sum(row["attack_success"] for row in completed),
            "impact_rate": round(sum(row["attack_success"] for row in completed) / len(completed), 3) if completed else None,
        }
    return {"total_runs": len(rows), "by_mode": by_mode, "runs": rows}


def chart(summary: dict[str, Any]) -> str:
    width, height, left = 660, 280, 150
    rows = [("persisted", "policy_persisted"), ("retrieved", "policy_retrieved"), ("impact", "virtual_impacts")]
    maximum = max(1, max(value[key] for value in summary["by_mode"].values() for _, key in rows))
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-label="comparison of ten poisoning experiments"><style>text{{font:13px sans-serif;fill:#1d2939}}.e{{fill:#175cd3}}.i{{fill:#7a5af8}}.grid{{stroke:#eaecf0}}</style><text x="22" y="28" style="font-size:18px;font-weight:bold">Independent-run outcomes</text>']
    for index, (label, key) in enumerate(rows):
        y = 62 + index * 66
        pieces.append(f'<text x="22" y="{y+22}">{label}</text><line class="grid" x1="{left}" y1="{y+30}" x2="620" y2="{y+30}"/>')
        for offset, (mode, css) in enumerate((("explicit", "e"), ("implicit", "i"))):
            value = summary["by_mode"][mode][key]
            bar = value / maximum * 380
            bar_y = y + offset * 24
            pieces.append(f'<rect class="{css}" x="{left}" y="{bar_y}" width="{bar:.1f}" height="18" rx="3"/><text x="{left+bar+8:.1f}" y="{bar_y+14}">{mode}: {value}/{summary["by_mode"][mode]["runs"]}</text>')
    return "".join(pieces) + "</svg>"


def main() -> None:
    parser = argparse.ArgumentParser(description="run balanced independent policy-memory experiments")
    parser.add_argument("--per-mode", type=int, default=5)
    parser.add_argument("--attack-at", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--prefix", default="series-10")
    args = parser.parse_args()
    if args.per_mode < 1:
        raise SystemExit("--per-mode must be positive")
    metrics: list[dict[str, Any]] = []
    for mode in ("explicit", "implicit"):
        for index in range(1, args.per_mode + 1):
            run_id = f"{args.prefix}-{mode}-{index:02d}"
            existing = REPORT_ROOT / run_id / "metrics.json"
            if existing.exists():
                metrics.append(json.loads(existing.read_text(encoding="utf-8")))
                continue
            try:
                metrics.append(run(Config(run_id, mode, args.attack_at, args.max_steps)))
            except Exception as exc:
                failure = {"run_id": run_id, "mode": mode, "error": str(exc)}
                output = REPORT_ROOT / run_id
                output.mkdir(parents=True, exist_ok=True)
                (output / "error.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8")
                metrics.append(failure)
    summary = aggregate(metrics)
    output = REPORT_ROOT / args.prefix
    output.mkdir(parents=True, exist_ok=True)
    (output / "aggregate.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["run_id", "mode", "attack_success", "persisted_step", "retrieved_step", "impact_step", "memory_count", "retrieval_backend", "error"]
    with (output / "aggregate.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in metrics:
            first = item.get("first", {})
            writer.writerow({"run_id": item["run_id"], "mode": item["mode"], "attack_success": item.get("attack_success"), "persisted_step": first.get("poison_persisted"), "retrieved_step": first.get("poison_retrieved"), "impact_step": first.get("virtual_impact"), "memory_count": item.get("memory_count"), "retrieval_backend": item.get("retrieval_backend"), "error": item.get("error")})
    (output / "aggregate.svg").write_text(chart(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
