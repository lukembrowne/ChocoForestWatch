# ml_pipeline/run_manager.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json, csv, subprocess, os, uuid

class RunManager:
    def __init__(self, root: str | Path = "runs"):
        self.root = Path(root)
        self.root.mkdir(exist_ok=True)
        self.runs_csv = self.root.parent / "runs.csv"

    def new_run(self, tag: str = "") -> Path:
        ts = datetime.now().strftime("%Y%m%dT%H%M")   #timestamp       # e.g. 20250520T1832
        gid = tag or uuid.uuid4().hex[:6]                      # optional human tag
        run_id = f"{ts}_{gid}".strip("_")
        path = self.root / run_id
        path.mkdir()
        (path / "preds").mkdir()
        self.run_path = path
        return path

    def save_json(self, name: str, obj):
        with open(self.run_path / name, "w") as f:
            json.dump(obj, f, indent=2)

    def record_summary(self, metrics: dict, note: str = ""):
        row = {
            "run_id": self.run_path.name,
            "local": datetime.now().isoformat(timespec="seconds"),
            "accuracy": metrics.get("accuracy"),
            "note": note,
            **{f"f1_{i}": v for i, v in enumerate(metrics.get("f1", []))}
        }
        hdr = row.keys()
        write_header = not self.runs_csv.exists()
        with open(self.runs_csv, "a", newline="") as f:
            writer = csv.DictWriter(f, hdr)
            if write_header: writer.writeheader()
            writer.writerow(row)