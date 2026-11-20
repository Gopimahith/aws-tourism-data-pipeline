"""AWS Lambda entry point: raw CSV in S3 -> validated CSV + quality report.

Trigger: S3 ObjectCreated event on the `raw/` prefix.
Outputs (same bucket):
  clean/<name>.csv              cleaned records, queried by Athena
  reports/<name>.quality.json   row counts and rejection reasons
"""
from __future__ import annotations

import io
import json
import urllib.parse

import boto3
import pandas as pd

from validate import validate_and_clean

RAW_PREFIX = "raw/"
CLEAN_PREFIX = "clean/"
REPORT_PREFIX = "reports/"


def process_object(s3, bucket: str, key: str) -> dict:
    """Clean one raw object and write the clean file and quality report."""
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    df = pd.read_csv(io.BytesIO(body), dtype=str)
    clean, report = validate_and_clean(df)

    name = key[len(RAW_PREFIX):].rsplit(".", 1)[0]
    s3.put_object(
        Bucket=bucket,
        Key=f"{CLEAN_PREFIX}{name}.csv",
        Body=clean.to_csv(index=False).encode("utf-8"),
    )
    report["source_key"] = key
    s3.put_object(
        Bucket=bucket,
        Key=f"{REPORT_PREFIX}{name}.quality.json",
        Body=json.dumps(report, indent=2).encode("utf-8"),
    )
    return report


def handler(event, context=None):
    s3 = boto3.client("s3")
    reports = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        if not key.startswith(RAW_PREFIX) or not key.endswith(".csv"):
            continue  # ignore our own outputs and non-CSV files
        reports.append(process_object(s3, bucket, key))
    return {"processed": len(reports), "reports": reports}
