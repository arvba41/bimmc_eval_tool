"""Efficiency-map figures of the paper (Analysis I) with the same model settings as the cycle
evaluation: each converter has its own voltage limit and Rdson follows Tj.

    python/venv/bin/python doc/figures/make_paper_maps.py

The figures of python/create_maps_PCIM.py (dashboard settings) are not touched.
Output: doc/figures/maps/<application>/*.png
"""

import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("TQDM_DISABLE", "1")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

import create_maps_PCIM as cm  # noqa: E402
import applications as apps  # noqa: E402

OUT = Path(__file__).resolve().parent / "maps"


def job(key):
    cm.VOLTAGE_LIMIT = "own"
    cm.RDSON_TJ = True
    cm.create_maps(key, 0.5, OUT, xlsx=False)
    return key


if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=6) as pool:
        for k in pool.map(job, list(apps.APPLICATIONS)):
            print("done", k, flush=True)
