"""Unit and integration tests for data acquisition and provenance."""

from pathlib import Path

import pandas as pd
import pytest

from retailmind.data import (
    compute_file_sha256,
    download_official_dataset,
)


def test_compute_file_sha256(tmp_path: Path) -> None:
    test_file = tmp_path / "sample.txt"
    test_file.write_text("hello retailmind", encoding="utf-8")
    h = compute_file_sha256(test_file)
    assert isinstance(h, str)
    assert len(h) == 64
    # Re-computing should give the exact same hash
    assert compute_file_sha256(test_file) == h


def test_download_failure_handling(tmp_path: Path) -> None:
    bad_url = "https://archive.ics.uci.edu/non_existent_dataset_url_12345.zip"
    zip_path = tmp_path / "bad.zip"
    xlsx_path = tmp_path / "bad.xlsx"
    prov_path = tmp_path / "prov.json"

    with pytest.raises(RuntimeError):
        download_official_dataset(
            source_url=bad_url,
            raw_zip_path=zip_path,
            raw_xlsx_path=xlsx_path,
            provenance_path=prov_path,
        )


def test_download_missing_columns_handling(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "invalid_cols.xlsx"
    df = pd.DataFrame({"WrongCol": [1, 2, 3]})
    df.to_excel(xlsx_path, index=False)
    prov_path = tmp_path / "prov.json"

    with pytest.raises(ValueError, match="missing required columns"):
        download_official_dataset(
            source_url="dummy",
            raw_zip_path=tmp_path / "dummy.zip",
            raw_xlsx_path=xlsx_path,
            provenance_path=prov_path,
        )
