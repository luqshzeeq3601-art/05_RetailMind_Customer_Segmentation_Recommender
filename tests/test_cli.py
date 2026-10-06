"""Tests for CLI parsing and subcommand dispatch."""

from retailmind.cli import build_parser


def test_cli_parser_commands() -> None:
    parser = build_parser()

    # Test download args
    args_dl = parser.parse_args(["download", "--config", "configs/default.yaml"])
    assert args_dl.command == "download"
    assert args_dl.config == "configs/default.yaml"

    # Test train args
    args_tr = parser.parse_args(["train", "--stage", "validation"])
    assert args_tr.command == "train"
    assert args_tr.stage == "validation"

    # Test recommend args
    args_rec = parser.parse_args(["recommend", "--customer-id", "17850", "--top-k", "10", "--mode", "repeat_allowed", "--bundle", "artifacts/release"])
    assert args_rec.command == "recommend"
    assert args_rec.customer_id == "17850"
    assert args_rec.top_k == 10
    assert args_rec.mode == "repeat_allowed"

    # Test benchmark args
    args_bm = parser.parse_args(["benchmark", "--bundle", "artifacts/release", "--calls", "50"])
    assert args_bm.command == "benchmark"
    assert args_bm.calls == 50
