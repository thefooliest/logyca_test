import pytest
import pandas as pd
from worker.processor import _validate, CSV_COLUMNS


def make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=CSV_COLUMNS)


def test_validate_all_valid():
    df = make_df([
        {"date": "2026-01-01", "product_id": 1001, "quantity": 2, "price": 10.50},
        {"date": "2026-01-01", "product_id": 1002, "quantity": 1, "price": 5.20},
    ])
    valid, invalid = _validate(df)
    assert len(valid) == 2
    assert len(invalid) == 0


def test_validate_missing_quantity():
    df = make_df([
        {"date": "2026-01-01", "product_id": 1001, "quantity": None, "price": 10.50},
    ])
    valid, invalid = _validate(df)
    assert len(valid) == 0
    assert len(invalid) == 1


def test_validate_negative_quantity():
    df = make_df([
        {"date": "2026-01-01", "product_id": 1001, "quantity": -1, "price": 10.50},
    ])
    valid, invalid = _validate(df)
    assert len(valid) == 0
    assert len(invalid) == 1


def test_validate_missing_price():
    df = make_df([
        {"date": "2026-01-01", "product_id": 1001, "quantity": 2, "price": None},
    ])
    valid, invalid = _validate(df)
    assert len(valid) == 0
    assert len(invalid) == 1


def test_validate_non_numeric_price():
    df = make_df([
        {"date": "2026-01-01", "product_id": 1001, "quantity": 2, "price": "abc"},
    ])
    valid, invalid = _validate(df)
    assert len(valid) == 0
    assert len(invalid) == 1


def test_validate_missing_product_id():
    df = make_df([
        {"date": "2026-01-01", "product_id": None, "quantity": 2, "price": 10.50},
    ])
    valid, invalid = _validate(df)
    assert len(valid) == 0
    assert len(invalid) == 1


def test_validate_mixed_valid_and_invalid():
    df = make_df([
        {"date": "2026-01-01", "product_id": 1001, "quantity": 2, "price": 10.50},
        {"date": "2026-01-01", "product_id": None, "quantity": 2, "price": 10.50},
        {"date": "2026-01-01", "product_id": 1002, "quantity": 1, "price": 5.20},
        {"date": "2026-01-01", "product_id": 1003, "quantity": -1, "price": 2.99},
    ])
    valid, invalid = _validate(df)
    assert len(valid) == 2
    assert len(invalid) == 2


def test_validate_zero_quantity():
    df = make_df([
        {"date": "2026-01-01", "product_id": 1001, "quantity": 0, "price": 10.50},
    ])
    valid, invalid = _validate(df)
    assert len(valid) == 0
    assert len(invalid) == 1


def test_validate_zero_price():
    df = make_df([
        {"date": "2026-01-01", "product_id": 1001, "quantity": 2, "price": 0},
    ])
    valid, invalid = _validate(df)
    assert len(valid) == 0
    assert len(invalid) == 1


def test_validate_empty_dataframe():
    df = make_df([])
    valid, invalid = _validate(df)
    assert len(valid) == 0
    assert len(invalid) == 0