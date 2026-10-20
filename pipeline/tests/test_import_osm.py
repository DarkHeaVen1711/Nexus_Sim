"""Tests for pipeline/src/import_osm.py"""

import os
import sys

import pytest

# Ensure pipeline/src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from import_osm import _slugify, import_osm  # noqa: E402


def test_slugify():
    assert _slugify("Mumbai, India") == "mumbai-india"
    assert _slugify("New York City") == "new-york-city"
    assert _slugify("   ") == "city"


def test_import_minimal_osm(tmp_path):
    """Import a minimal hand-written .osm file."""
    osm_content = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
  <node id="1" lat="19.0760" lon="72.8777"/>
  <node id="2" lat="19.0770" lon="72.8787"/>
  <node id="3" lat="19.0765" lon="72.8795"/>
  <way id="10">
    <nd ref="1"/>
    <nd ref="2"/>
    <tag k="highway" v="residential"/>
  </way>
  <way id="11">
    <nd ref="2"/>
    <nd ref="3"/>
    <tag k="highway" v="residential"/>
  </way>
</osm>
"""
    source = tmp_path / "mumbai.osm"
    source.write_text(osm_content, encoding="utf-8")

    out_dir = tmp_path / "data"
    result = import_osm(str(source), city_id="mumbai", city_name="Mumbai", out_dir=str(out_dir))

    assert result["city_id"] == "mumbai"
    assert result["city_name"] == "Mumbai"
    assert result["status"] == "ready"
    assert result["node_count"] >= 1
    assert result["edge_count"] >= 1
    assert len(result["bbox"]) == 4
    assert len(result["center"]) == 2
    assert os.path.exists(result["graph_json_path"])
    assert os.path.exists(result["cleaned_path"])

    # graph.json should be valid JSON with nodes and edges
    import json
    with open(result["graph_json_path"]) as f:
        graph = json.load(f)
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) >= 1
    assert len(graph["edges"]) >= 1
