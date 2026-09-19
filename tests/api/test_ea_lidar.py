from __future__ import annotations

from pathlib import Path

import pytest

from bessible.api.ea_lidar import DtmGrid, WcsError, dtm_for_bbox

FIX = Path(__file__).parent / "fixtures"


def test_geotiff():
    g = DtmGrid.from_geotiff((FIX / "ea_lidar_dtm_dorking.tif").read_bytes())
    assert (g.width, g.height) == (28, 34)
    assert g.pixel_m == pytest.approx((1.03, 1.01), abs=0.02)  # native 1 m cells
    assert g.rows[0][0] is None  # no-data corner
    assert g.rows[0][1] == pytest.approx(58.36)
    lat, lon = g.centre(10, 10)
    assert g.at(lat, lon) == g.rows[10][10]
    assert g.at(0, 0) is None
    assert g.slope_percent(10, 10) >= 0
    assert g.slope_percent(0, 0) is None


def test_not_a_tiff():
    with pytest.raises(ValueError, match="not a TIFF"):
        DtmGrid.from_geotiff(b'{"message":"Internal server error"}')


def test_request():
    p = dtm_for_bbox(51.2325, -0.3308, 51.2328, -0.3304).params()
    assert p["subset"] == ["Lat(51.2325,51.2328)", "Long(-0.3308,-0.3304)"]
    assert p["subsettingCrs"].endswith("/4326")
    assert "scaleFactor" not in p  # small box: native resolution
    big = dtm_for_bbox(51.228, -0.34, 51.237, -0.325, max_pixels=250).params()
    assert big["scaleFactor"] == pytest.approx(0.239, abs=0.001)


def test_error():
    e = WcsError.model_validate({"message": "Internal server error", "statusCode": 500, "code": "internal_error"})
    assert e.status_code == 500
