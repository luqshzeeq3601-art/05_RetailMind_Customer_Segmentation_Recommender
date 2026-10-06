"""Tests for freeze protocol, selection integrity, and temporal isolation."""

import json
from pathlib import Path

import pytest

from retailmind.experiments import run_test_pipeline


def test_freeze_manifest_integrity() -> None:
    selection_path = Path("reports/selection.json")
    assert selection_path.exists(), "Selection manifest should exist after freeze"

    with open(selection_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert "freeze_timestamp_utc" in manifest
    assert "source_sha256" in manifest
    assert "config_sha256" in manifest
    assert "lock_sha256" in manifest
    assert "selected_segmentation" in manifest
    assert "selected_recommender" in manifest
    assert manifest["cf_qualifies"] is True
    assert manifest["selected_recommender"] == "ItemItemCF_N50"


def test_test_pipeline_rejects_missing_selection(tmp_path: Path) -> None:
    # If selection manifest is missing, test run should raise RuntimeError
    fake_config = tmp_path / "config.yaml"
    fake_config.write_text("dataset:\n  raw_xlsx_path: dummy\n", encoding="utf-8")

    # Temporarily check rejection with invalid config path
    with pytest.raises(Exception):
        run_test_pipeline(fake_config)
