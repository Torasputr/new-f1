from google.cloud import storage
import os
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO

load_dotenv()

# ============================================================================================
# VARIABLES
# ============================================================================================

GCS_BUCKET = os.getenv("GCS_BUCKET").strip()
GCS_MEDAL_FETCH = os.getenv("GCS_MEDAL_FETCH").strip()
GCS_MEDAL_PUSH = os.getenv("GCS_MEDAL_PUSH").strip()
SEASON = int(os.getenv("SEASON"))
BLOB_FETCH = f"{GCS_MEDAL_FETCH}/season={SEASON}/laps/all_session_laps.parquet"
BLOB_PUSH = f"{GCS_MEDAL_PUSH}/season={SEASON}/all_session_laps.parquet"

REFERENCE_BLOB_BASE = f"gold/season={SEASON}"
BLOB_FETCH_SESSIONS = f"{REFERENCE_BLOB_BASE}/session.parquet"
BLOB_FETCH_DRIVERS = f"{REFERENCE_BLOB_BASE}/driver.parquet"

# ============================================================================================
# FUNCTIONS
# ============================================================================================


def load_client_bucket(bucket):
    if not bucket:
        raise ValueError("[ERROR] Bucket Name is Required")
    client = storage.Client()
    bucket = client.bucket(bucket)
    return client, bucket


def load_parquet(blob):
    print(f"[INFO] Loading Parquet from GCS: {blob.name}")
    df = pd.read_parquet(BytesIO(blob.download_as_bytes()))
    print(f"[INFO] Loaded Parquet from GCS: {blob.name}")
    return df


def load_parquet_from_gcs(bucket, blob_path):
    if not blob_path:
        raise ValueError("[ERROR] Blob Path is Required")
    blob = bucket.blob(blob_path)
    if not blob.exists():
        raise FileNotFoundError(f"[ERROR] Blob does not exist: {blob_path}")
    df = load_parquet(blob)
    return df


def drop_columns(df, columns):
    missing = [c for c in columns if c not in df.columns]
    if missing:
        print(f"[WARN] Columns not found in df: {missing}")

    print(f"[INFO] Dropping columns: {columns}")
    df = df.drop(columns=columns, errors="ignore")
    print(f"[INFO] Columns Dropped")
    return df


def strip_string(column):
    if column is None:
        raise ValueError("[ERROR] Column not found")

    column = column.str.strip()
    print(f"[INFO] Stripping String")
    return column

def upload_to_gcs(df, bucket, blob_path, client):
    if blob_path is None:
        raise ValueError("[ERROR] Blob Path is Required")

    buf = BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    blob = client.bucket(bucket).blob(blob_path)
    blob.upload_from_file(buf, content_type="application/vnd.apache.parquet", size=len(buf.getvalue()))
    print(f"[INFO] Uploaded DataFrame to GCS on {blob_path}")

# ============================================================================================
# MAIN
# ============================================================================================

def main():
    client, bucket = load_client_bucket(GCS_BUCKET)
    df = load_parquet_from_gcs(bucket, BLOB_FETCH)
    df_sessions = load_parquet_from_gcs(bucket, BLOB_FETCH_SESSIONS)
    df_drivers = load_parquet_from_gcs(bucket, BLOB_FETCH_DRIVERS)

    cols_to_drop1 = [
        "date_start",
        "meeting_key",
        "circuit_key",
        "circuit_short_name",
        "location",
        "gmt_offset",
        "year",
        "ingested_at",
        "country_key",
        "country_code",
        "country_name",
    ]

    columns_to_drop2 = [
        "broadcast_name",
        "name_acronym",
        "team_colour",
        "first_name",
        "last_name",
        "headshot_url",
    ]

    df_sessions_right = drop_columns(df_sessions, cols_to_drop1)
    df_drivers_right = drop_columns(df_drivers, columns_to_drop2)

    print(f"[INFO] Merging laps and sessions on session_key")
    new_df = pd.merge(df, df_sessions_right, on="session_key", how="left")

    print(f"[INFO] Merging laps and drivers on driver_number")
    new_df = pd.merge(new_df, df_drivers_right, on="driver_number", how="left")
    print(f"[INFO] Merging success")

    column_order = [
        "meeting_key",
        "session_key",
        "session_name",
        "driver_number",
        "full_name",
        "team_name",
        "country",
        "lap_number",
        "date_start",
        "duration_sector_1",
        "duration_sector_2",
        "duration_sector_3",
        "i1_speed",
        "i2_speed",
        "lap_duration",
        "segments_sector_1",
        "segments_sector_2",
        "segments_sector_3",
        "st_speed",
        "ingested_at",
    ]

    new_df = new_df[column_order]

    string_strip_cols = ["session_name", "full_name", "team_name", "country"]
    for c in string_strip_cols:
        print(f"[INFO] Stripping {c}")
        new_df[c] = strip_string(new_df[c])

    print(f"[INFO] Filling date start")
    session_date_map = (
        df_sessions.drop_duplicates(subset=["session_key"]).set_index("session_key")["date_start"]
    )

    new_df["date_start"] = new_df["date_start"].fillna(
        new_df["session_key"].map(session_date_map)
    )
    new_df["date_start"] = pd.to_datetime(new_df["date_start"])
    print(f"[INFO] Date start filled and converted to datetime")

    upload_to_gcs(new_df, GCS_BUCKET, BLOB_PUSH, client)
if __name__ == "__main__":
    main()
