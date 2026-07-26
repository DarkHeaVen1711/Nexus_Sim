import os
import json


def test_pipeline_modules_exist():
    src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
    for name in ["download.py", "clean.py", "lanes.py", "zones.py", "export.py"]:
        assert os.path.isfile(os.path.join(src_dir, name)), f"Missing pipeline module: {name}"


def test_cities_config_exists():
    cfg = os.path.join(os.path.dirname(__file__), "..", "cities.yaml")
    assert os.path.isfile(cfg), "pipeline/cities.yaml not found"
