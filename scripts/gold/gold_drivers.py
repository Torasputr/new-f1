from google.cloud import storage
import os
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO

load_dotenv()

GCS_BUCKET = os.getenv("GCS_BUCKET", "").strip()
GCS_MEDAL_FETCH = os.getenv("GCS_MEDAL_FETCH", "").strip()
GCS_MEDAL_PUSH = os.getenv("GCS_MEDAL_PUSH", "").strip()
SEASON = int(os.getenv("SEASON", ""))
GCS_BLOB_FETCH = f"{GCS_MEDAL_FETCH}/season={SEASON}/driver.parquet"
GCS_BUCKET_MART = os.getenv("GCS_BUCKET_MART", "").strip()
BLOB_PUSH_PARQUET = f"{GCS_MEDAL_PUSH}/season={SEASON}/driver.parquet"
BLOB_PUSH_JSON = f"season={SEASON}/driver.json"


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
    print(f"[INFO] Fetching drivers for season {SEASON} from {GCS_BLOB_FETCH}")
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_BLOB_FETCH)

    df = pd.read_parquet(BytesIO(blob.download_as_bytes()))

    upload_files(df, client)


if __name__ == "__main__":
    main()
