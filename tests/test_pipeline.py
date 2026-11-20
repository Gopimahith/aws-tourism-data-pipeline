import io
import json
import os
import sys

import boto3
import pandas as pd
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from generate_sample_data import generate  # noqa: E402
from lambda_handler import handler  # noqa: E402
from validate import validate_and_clean  # noqa: E402

BUCKET = "tourism-pipeline-test"


def _row(**over):
    base = {
        "visit_id": "V1", "user_id": "U1", "attraction_id": "A1",
        "attraction_type": "Beach", "country": "India", "visit_year": "2024",
        "visit_month": "5", "visit_mode": "Family", "rating": "4",
    }
    base.update(over)
    return base


def test_valid_row_passes():
    clean, report = validate_and_clean(pd.DataFrame([_row()]))
    assert len(clean) == 1
    assert report["rows_rejected"] == 0
    assert report["pass_rate"] == 1.0


@pytest.mark.parametrize(
    "bad,reason",
    [
        ({"rating": "6"}, "invalid_rating"),
        ({"rating": "0"}, "invalid_rating"),
        ({"rating": "3.5"}, "invalid_rating"),
        ({"visit_month": "13"}, "invalid_month"),
        ({"visit_mode": "Alone"}, "invalid_visit_mode"),
        ({"country": ""}, "missing_required_value"),
    ],
)
def test_each_rule_rejects_one_row(bad, reason):
    clean, report = validate_and_clean(pd.DataFrame([_row(**bad)]))
    assert len(clean) == 0
    assert report["rejected_by_reason"][reason] == 1


def test_duplicate_visit_id_keeps_first():
    df = pd.DataFrame([_row(), _row(rating="2")])
    clean, report = validate_and_clean(df)
    assert len(clean) == 1
    assert clean.loc[0, "rating"] == 4
    assert report["rejected_by_reason"]["duplicate_visit_id"] == 1


def test_missing_column_raises():
    with pytest.raises(ValueError):
        validate_and_clean(pd.DataFrame([{"visit_id": "V1"}]))


def test_reasons_add_up_to_rejected_total():
    clean, report = validate_and_clean(generate(2000))
    assert sum(report["rejected_by_reason"].values()) == report["rows_rejected"]
    assert report["rows_in"] == report["rows_out"] + report["rows_rejected"]
    assert report["rows_rejected"] > 0


@mock_aws
def test_lambda_end_to_end(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET)

    raw = generate(1000)
    s3.put_object(Bucket=BUCKET, Key="raw/visits.csv", Body=raw.to_csv(index=False).encode())

    event = {"Records": [{"s3": {"bucket": {"name": BUCKET}, "object": {"key": "raw/visits.csv"}}}]}
    result = handler(event)
    assert result["processed"] == 1

    clean = pd.read_csv(io.BytesIO(s3.get_object(Bucket=BUCKET, Key="clean/visits.csv")["Body"].read()))
    report = json.loads(s3.get_object(Bucket=BUCKET, Key="reports/visits.quality.json")["Body"].read())
    assert len(clean) == report["rows_out"]
    assert report["rows_in"] == 1000
    assert clean["rating"].between(1, 5).all()


@mock_aws
def test_lambda_ignores_non_raw_keys(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
    event = {"Records": [{"s3": {"bucket": {"name": BUCKET}, "object": {"key": "clean/visits.csv"}}}]}
    assert handler(event)["processed"] == 0
