from __future__ import annotations

import pytest

from bessible.cli import build_parser


def test_cli_parser_start():
    parser = build_parser()
    args = parser.parse_args(["start", "https://example.com/site", "--battery-mw", "15", "--flexible", "--yes"])
    assert args.command == "start"
    assert args.url == "https://example.com/site"
    assert args.battery_mw == 15.0
    assert args.flexible is True
    assert args.yes is True


def test_cli_parser_start_postcode_detach():
    parser = build_parser()
    args = parser.parse_args(["start", "--postcode", "RH4 1AD", "--detach"])
    assert args.command == "start"
    assert args.postcode == "RH4 1AD"
    assert args.detach is True


def test_cli_parser_confirm():
    parser = build_parser()
    args = parser.parse_args(["confirm", "bessible-123456", "--capacity-mw", "10"])
    assert args.command == "confirm"
    assert args.run_id == "bessible-123456"
    assert args.capacity_mw == 10.0
    assert args.reject is False


def test_cli_parser_confirm_reject():
    parser = build_parser()
    args = parser.parse_args(["confirm", "bessible-123456", "--reject"])
    assert args.command == "confirm"
    assert args.reject is True


def test_cli_parser_result():
    parser = build_parser()
    args = parser.parse_args(["result", "bessible-123456"])
    assert args.command == "result"
    assert args.run_id == "bessible-123456"


def test_format_footprint():
    from bessible.cli import _format_footprint

    txt = _format_footprint(10.0)
    assert "2.0-3.0 acres" in txt
    assert "2 h: 1.0-1.5" in txt
    assert "8 h: 4.0-6.0" in txt


def test_build_footprint_polygon():
    from bessible.cli import _build_footprint_polygon
    from bessible.models import Position

    poly = _build_footprint_polygon(Position(lat=51.5, lon=-0.1), 10.0)
    assert poly is not None
    assert poly["type"] == "Polygon"


@pytest.mark.anyio
async def test_handle_confirmation_prompt_auto_yes():
    from unittest.mock import AsyncMock

    from bessible.cli import _handle_confirmation_prompt
    from bessible.models import CapacityOutput, Position, RunStatus, TitleOutput

    handle = AsyncMock()
    status = RunStatus(
        status="awaiting_confirmation",
        capacity=CapacityOutput(viable=True, firm_mw=10.0, ceiling_mw=15.0, recommended_mw=10.0),
        boundary=TitleOutput(title_number="BK123", area_m2=5000.0),
        position=Position(lat=51.5, lon=-0.1),
    )
    await _handle_confirmation_prompt(handle, status, auto_yes=True)
    handle.execute_update.assert_called_once()
    decision = handle.execute_update.call_args[0][1]
    assert decision.confirmed is True
    assert decision.capacity_mw == 10.0
    assert decision.footprint_geojson is not None
    assert decision.footprint_geojson["type"] == "Polygon"


@pytest.mark.anyio
async def test_cli_prompt_confirmation_132kv(capsys):
    from unittest.mock import AsyncMock

    from bessible.cli import _handle_confirmation_prompt
    from bessible.models import CapacityOutput, RunStatus

    cap = CapacityOutput(
        viable=True,
        substation="Leatherhead 132kV",
        connection_voltage_kv=132.0,
        firm_mw=85.0,
        ceiling_mw=100.0,
        recommended_mw=85.0,
    )
    st = RunStatus(status="awaiting_confirmation", capacity=cap)
    mock_handle = AsyncMock()

    await _handle_confirmation_prompt(mock_handle, st, auto_yes=True)
    captured = capsys.readouterr()
    assert "Substation:         Leatherhead 132kV" in captured.out
    assert "Connection Voltage: 132 kV" in captured.out
    mock_handle.execute_update.assert_awaited_once()
