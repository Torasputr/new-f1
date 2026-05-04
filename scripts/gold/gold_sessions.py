import os
from dotenv import load_dotenv
from google.cloud import storage
import pandas as pd
from io import BytesIO

load_dotenv()

SEASON = int(os.getenv("SEASON", ""))
GCS_BUCKET = os.getenv("GCS_BUCKET", "").strip()
GCS_MEDAL_FETCH = os.getenv("GCS_MEDAL_FETCH", "").strip()
GCS_MEDAL_PUSH = os.getenv("GCS_MEDAL_PUSH", "").strip()
BLOB_FETCH = f"{GCS_MEDAL_FETCH}/season={SEASON}/session.parquet"
BLOB_PUSH_PARQUET = f"{GCS_MEDAL_PUSH}/season={SEASON}/session.parquet"
BLOB_PUSH_JSON = f"season={SEASON}/session.json"
GCS_BUCKET_MART = os.getenv("GCS_BUCKET_MART", "").strip()


def upload_files(df, client):
    buf_parq = BytesIO()
    df.to_parquet(buf_parq, index=False)
    buf_parq.seek(0)
    bparq = client.bucket(GCS_BUCKET).blob(BLOB_PUSH_PARQUET)
    bparq.upload_from_file(
        buf_parq,
        content_type="application/vnd.apache.parquet",
        size=len(buf_parq.getvalue()),
    )
    print(f"[INFO] Uploaded Parquet to gs://{GCS_BUCKET}/{BLOB_PUSH_PARQUET}")

    buf_json = BytesIO()
    df.to_json(buf_json, orient="records", date_format="iso", date_unit="ms")
    buf_json.seek(0)
    bjson = client.bucket(GCS_BUCKET_MART).blob(BLOB_PUSH_JSON)
    bjson.upload_from_file(
        buf_json,
        content_type="application/json; charset=utf-8",
        size=len(buf_json.getvalue()),
    )
    print(f"[INFO] Uploaded JSON to gs://{GCS_BUCKET_MART}/{BLOB_PUSH_JSON}")


def main():
    print(f"[INFO] Fetching silver sessions for season {SEASON}")
    client = storage.Client()
    blob = client.bucket(GCS_BUCKET).blob(BLOB_FETCH)
    df = pd.read_parquet(BytesIO(blob.download_as_bytes()))

    print(f"[INFO] Found {len(df)} sessions")

    columns_to_drop = ["date_end"]
    print(f"[INFO] Dropping {columns_to_drop}")
    df = df.drop(columns=columns_to_drop, errors="coerce")

    print(f"[INFO] Converting ingested_at to datetime")
    ingested_at = pd.Timestamp.now(tz="UTC")
    df["ingested_at"] = ingested_at
    print(f"[INFO] Ingested at {ingested_at}")

    print(f"[INFO] Uploading DataFrame to GCS")
    upload_files(df, client)
    print(
        f"[INFO] Uploaded DataFrame to GCS on {BLOB_PUSH_PARQUET} and {BLOB_PUSH_JSON}"
    )


if __name__ == "__main__":
    main()
