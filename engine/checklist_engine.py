"""
Checklist Engine
Loads and provides access to the official 49 review parameters for AY 2026–27.
"""

import json
import os
from typing import List, Dict, Any


def load_official_checklist(config_path: str = "config/checklist.json") -> Dict[str, Any]:
    if not os.path.exists(config_path):
        # try relative to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alt_path = os.path.join(base_dir, config_path)
        if os.path.exists(alt_path):
            config_path = alt_path
        else:
            raise FileNotFoundError(f"Checklist config not found at {config_path}")
            
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_parameters() -> List[Dict[str, Any]]:
    data = load_official_checklist()
    return data.get("parameters", [])


def get_parameter_by_id(param_id: int) -> Dict[str, Any]:
    for p in get_parameters():
        if p["parameter_id"] == param_id:
            return p
    raise ValueError(f"Parameter ID {param_id} not found in official checklist")
