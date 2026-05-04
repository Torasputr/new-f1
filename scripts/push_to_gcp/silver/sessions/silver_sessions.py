import os
from dotenv import load_dotenv
from google.cloud import storage
import pandas as pd
from io import BytesIO

load_dotenv()

SEASON = int(os.getenv("SEASON"))
GCS_BUCKET = os.getenv("GCS_BUCKET", "").strip()
GCS_MEDAL_FETCH = os.getenv("GCS_MEDAL_FETCH", "").strip()
GCS_MEDAL_PUSH = os.getenv("GCS_MEDAL_PUSH", "").strip()
BLOB_FETCH = f"{GCS_MEDAL_FETCH}/season={SEASON}/session.parquet"
BLOB_PUSH = f"silver/season={SEASON}/session.parquet"

def upload_parquet(df, bucket, blob_path, client):
    buf= BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)

    blobpush = client.bucket(bucket).blob(blob_path)
    blobpush.upload_from_file(buf, content_type="application/vnd.apache.parquet", size=len(buf.getvalue()))
    print(f"[INFO] Uploaded DataFrame to GCS on {blob_path}")

def main():
    print(f"[INFO] Fetching sessions for season {SEASON}")
    client = storage.Client()
    blob = client.bucket(GCS_BUCKET).blob(BLOB_FETCH)
    df = pd.read_parquet(BytesIO(blob.download_as_bytes()))

    print(f"[INFO] Found {len(df)} sessions")
    
    unneeded_columns = ["session_type"]
    print(f"[INFO] Dropping {unneeded_columns}")
    df = df.drop(columns=unneeded_columns, errors="coerce")

    print(f"[INFO] Changing session name and stripping")
    for i in range(1, 4):
        df.loc[df["session_name"] == f"Day {i}", "session_name"] = f"Testing Day {i}"
    df["session_name"] = df["session_name"].str.strip()
    
    print(f"[INFO] Converting date start and end to datetime")
    df["date_start"] = pd.to_datetime(df["date_start"])
    df["date_end"] = pd.to_datetime(df["date_end"])

    print(f"[INFO] Stripping circuit short name")
    df["circuit_short_name"] = df["circuit_short_name"].str.strip()

    print(f"[INFO] Stripping country name")
    df["country_name"] = df["country_name"].str.strip()

    print(f"[INFO] Stripping location")
    df["location"] = df["location"].str.strip()

    print(f"[INFO] Converting gmt offset to timedelta")
    df["gmt_offset"] = pd.to_timedelta(df["gmt_offset"])

    ingested_at = pd.Timestamp.now(tz="UTC")
    df["ingested_at"] = ingested_at
    print(f"[INFO] Ingested at {ingested_at}")

    upload_parquet(df, GCS_BUCKET, BLOB_PUSH, client)

if __name__ == "__main__":
    main()
