"""Compatibility entry point for the simplified checklist."""
from pathlib import Path
import json
from checklist_data import build_data
Path(__file__).with_name('content.json').write_text(json.dumps(build_data(),ensure_ascii=False,indent=2))
