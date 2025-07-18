# ml_pipeline/run_manager.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json, csv, subprocess, os, uuid

class RunManager:
    def __init__(self, run_id: str, root: str | Path = None):
        """
        Initialize RunManager with consistent path resolution.
        
        Parameters
        ----------
        run_id : str
            Unique identifier for this run
        root : str | Path, optional
            Root directory for runs. If None, automatically resolves to 
            <ml_pipeline_root>/runs for consistency across different script locations.
        """
        if root is None:
            # Automatically resolve to ml_pipeline root runs folder
            # Go up from src/ml_pipeline to ml_pipeline root
            ml_pipeline_root = Path(__file__).parent.parent.parent
            self.root = ml_pipeline_root / "runs"
        else:
            self.root = Path(root)
        
        self.root.mkdir(exist_ok=True)
        self.runs_csv = self.root.parent / "runs.csv"
        self.run_id = run_id
        self.run_path = self.root / run_id

        if self.run_exists():
            print(f"⚠️  Run directory already exists: {self.run_path}")
        else:
            print(f"✅ Creating new run directory: {self.run_path}")
        
        # Create run directory and subdirectories
        self.run_path.mkdir(exist_ok=True)
        (self.run_path / "feature_ids_testing").mkdir(exist_ok=True)
        (self.run_path / "saved_models").mkdir(exist_ok=True)
        (self.run_path / "data_cache").mkdir(exist_ok=True)
        (self.run_path / "model_diagnostics").mkdir(exist_ok=True)
        
        

    def new_run(self) -> Path:
        """Create a new run directory with a deterministic ID based on the tag."""
        return self.run_path

    def load_run(self) -> Path:
        """Load an existing run by its tag."""
        if not self.run_exists():
            raise ValueError(f"No existing run found with tag: {self.run_id}")
        return self.run_path

    def run_exists(self) -> bool:
        """Check if a run with the given tag exists."""
        return self.run_path.exists()

    def save_json(self, name: str, obj):
        if not self.run_path:
            raise ValueError("No active run. Call new_run() or load_run() first.")
        with open(self.run_path / name, "w") as f:
            json.dump(obj, f, indent=2)

    def record_summary(self, metrics: dict, note: str = ""):
        if not self.run_path:
            raise ValueError("No active run. Call new_run() or load_run() first.")
        row = {
            "run_id": self.run_id,
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

    def get_diagnostics_path(self, model_name: str) -> Path:
        """Get the diagnostics directory path for a specific model."""
        if not self.run_path:
            raise ValueError("No active run. Call new_run() or load_run() first.")
        diagnostics_path = self.run_path / "model_diagnostics" / model_name
        diagnostics_path.mkdir(parents=True, exist_ok=True)
        return diagnostics_path