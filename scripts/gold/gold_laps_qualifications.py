from google.cloud import storage
import os
from dotenv import load_dotenv
from io import BytesIO
import pandas as pd

load_dotenv()

# ============================================================================================
# VARIABLES
# ============================================================================================

GCS_BUCKET = os.getenv("GCS_BUCKET").strip()
GCS_MEDAL_FETCH = os.getenv("GCS_MEDAL_FETCH").strip()
GCS_MEDAL_PUSH = os.getenv("GCS_MEDAL_PUSH").strip()
SEASON = int(os.getenv("SEASON"))
BLOB_FETCH = f"{GCS_MEDAL_FETCH}/season={SEASON}/all_session_laps.parquet"
GCS_BUCKET_MART = os.getenv("GCS_BUCKET_MART").strip()

BLOB_PUSH_PARQUET = f"{GCS_MEDAL_PUSH}/season={SEASON}/qualifying_laps.parquet"
BLOB_PUSH_JSON = f"{GCS_MEDAL_PUSH}/season={SEASON}/qualifying_laps.json"

# ============================================================================================
# FUNCTIONS
# ============================================================================================


def load_parquet_from_gcs(client, bucket, blob_path):
    if not bucket:
        raise ValueError("[ERROR] Bucket Name is Required")
    if not blob_path:
        raise ValueError("[ERROR] Blob Path is Required")

    client = storage.Client()
    bucket = client.bucket(bucket)
    blob = bucket.blob(blob_path)

    if not blob.exists():
        raise FileNotFoundError(f"[ERROR] Blob {blob_path} does not exist")

    print(f"[INFO] Blob exists: {blob.name}")
    df = pd.read_parquet(BytesIO(blob.download_as_bytes()))
    return df


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


# ============================================================================================
# MAIN
# ============================================================================================


def main():
    client = storage.Client()
    df = load_parquet_from_gcs(client, GCS_BUCKET, BLOB_FETCH)
    print(f"[INFO] Filtering Qualification Lap")
    df = df.loc[df["session_name"] == "Qualifying"]

    df["date"] = df["date_start"].dt.strftime("%Y-%m-%d")
    df["time"] = df["date_start"].dt.strftime("%H:%M:%S")

    print(f"[INFO] Sorting and dropping duplicates")
    df = df.sort_values(
        by=["session_key", "driver_number", "lap_duration"],
        ascending=[True, True, True],
    )
    df = df.drop_duplicates(subset=["session_key", "driver_number"], keep="first")
    df = df.sort_values(by=["session_key", "lap_duration"], ascending=[True, True])

    print(f"[INFO] Converting lap duration to formatted string")
    td = pd.to_timedelta(df["lap_duration"], unit="s")

    minutes = (td.dt.total_seconds() // 60).astype(int)
    seconds = (td.dt.total_seconds() % 60).astype(int)
    milliseconds = (td.dt.microseconds // 1000).astype(int)

    df["lap_duration_fmt"] = (
        minutes.astype(str).str.zfill(2)
        + ":"
        + seconds.astype(str).str.zfill(2)
        + "."
        + milliseconds.astype(str).str.zfill(3)
    )

    print(f"[INFO] Adding grid position")
    df["grid_position"] = df.groupby("session_key").cumcount() + 1

    order = [
        "meeting_key",
        "session_key",
        "session_name",
        "date",
        "time",
        "driver_number",
        "full_name",
        "team_name",
        "country",
        "lap_duration_fmt",
        "grid_position",
        "ingested_at",
    ]

    df = df[order]
    df = df.rename(columns={"lap_duration_fmt": "lap_duration"})

    upload_files(df, client)


if __name__ == "__main__":
    main()
