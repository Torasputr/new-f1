from google.cloud import storage
import os
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO

load_dotenv()

GCS_BUCKET = os.getenv("GCS_BUCKET", "").strip()
GCS_MEDAL_FETCH = os.getenv("GCS_MEDAL_FETCH", "").strip()
GCS_MEDAL_PUSH = os.getenv("GCS_MEDAL_PUSH", "").strip()
SEASON = int(os.getenv("SEASON"))
BLOB_PATH = f"{GCS_MEDAL_FETCH}/season={SEASON}/session_result/all_session_results.parquet"

BLOB_PATH_SESSIONS = f"gold/season={SEASON}/session.parquet"
BLOB_PATH_DRIVERS = f"gold/season={SEASON}/driver.parquet"

BLOB_PATH_PUSH = f"{GCS_MEDAL_PUSH}/season={SEASON}/session_result.parquet"

def main():
    print(f"[INFO] Fetching session results for season {SEASON}")
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(BLOB_PATH)
    df = pd.read_parquet(BytesIO(blob.download_as_bytes()))

    print(f"[INFO] Fetching sessions for season {SEASON}")
    blob_sessions = bucket.blob(BLOB_PATH_SESSIONS)
    df_sessions = pd.read_parquet(BytesIO(blob_sessions.download_as_bytes()))

    print(f"[INFO] Fetching drivers for season {SEASON}")
    blob_drivers = bucket.blob(BLOB_PATH_DRIVERS)
    df_drivers = pd.read_parquet(BytesIO(blob_drivers.download_as_bytes()))

    print(f"[INFO] Merging session results with sessions and drivers")
    df_drivers = df_drivers[["driver_number", "full_name", "team_name", "country"]]
    df_sessions = df_sessions[["session_key", "session_name", "location"]]
    df = pd.merge(df, df_drivers, on="driver_number", how="left")
    df = pd.merge(df, df_sessions, on="session_key", how="left")

    df = df[[
        "meeting_key",
        "session_key",
        "session_name",
        "location",
        "driver_number", 
        "full_name", 
        "country",
        "team_name",
        "number_of_laps",
        "dnf",
        "dns",
        "dsq",
        "gap_to_leader",
        "duration",
        "points",
        "position", 
        "ingested_at"
    ]]

    df = df.sort_values(
        by=["points", "session_key"],
        ascending=[False, True]
    )

    buf = BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)

    blob_push = bucket.blob(BLOB_PATH_PUSH)
    blob_push.upload_from_file(buf, content_type="application/vnd.apache.parquet", size=len(buf.getvalue()))
    print(f"[INFO] Uploaded DataFrame to GCS on {BLOB_PATH_PUSH}")

if __name__ == "__main__":
    main()