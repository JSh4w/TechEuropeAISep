from __future__ import annotations

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
