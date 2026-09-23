from __future__ import annotations

import json
from pathlib import Path

import pytest

from bessible.api import npg

FIX = Path(__file__).parent / "fixtures"


def test_capacity_heatmap_leeds():
    r = npg.DATASETS["capacity_heatmap"].parse(json.loads((FIX / "npg_capacity_heatmap_leeds.json").read_text()))
    assert r.total_count == 37  # rows within 5 km of central Leeds
    site = r.results[0]
    assert (site.name, site.type, site.voltages, site.area) == ("Upper Basinghall Street", "Primary", 11.0, "NPgY")
    assert site.demandavailablecapacity == pytest.approx(9.16)
    assert site.generationavailablecapacity == pytest.approx(4.17)
    assert site.latlon is not None


def test_capacity_heatmap_radius_query():
    req = npg.DATASETS["capacity_heatmap"].near(53.8, -1.55, 5000)
    assert req.where.startswith("within_distance(latlon, ")
    assert req.url().startswith("https://northernpowergrid.opendatasoft.com/")
