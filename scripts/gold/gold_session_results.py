from google.cloud import storage
import os
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO
import numpy as np

load_dotenv()

GCS_BUCKET = os.getenv("GCS_BUCKET", "").strip()
GCS_BUCKET_MART = os.getenv("GCS_BUCKET_MART", "").strip()
GCS_MEDAL_FETCH = os.getenv("GCS_MEDAL_FETCH", "").strip()
BLOB_FETCH_PATH = f"{GCS_MEDAL_FETCH}/season=2026/session_result.parquet"

BLOB_FETCH_SESSIONS = f"gold/season=2026/session.parquet"
BLOB_FETCH_DRIVERS = f"gold/season=2026/driver.parquet"

BLOB_PUSH = f"gold/season=2026/session_result.parquet"
BLOB_PUSH_DRIVERS = f"gold/season=2026/wdc.parquet"
BLOB_PUSH_TEAM_POINTS = f"gold/season=2026/team_points.parquet"

BLOB_PUSH_JSON = f"season=2026/session_result.json"
BLOB_PUSH_DRIVERS_JSON = f"season=2026/wdc.json"
BLOB_PUSH_TEAM_POINTS_JSON = f"season=2026/team_points.json"


def fill_position_by_laps(group):
    g = group.copy()
    pos = g["position"]
    known = pos.notna()
    if known.all():
        return g

    last = int(pos[known].max()) if known.any() else 0
    miss = g.loc[~known].copy()
    miss = miss.sort_values(
        by=["number_of_laps", "driver_sort"],
        ascending=[False, True],
        kind="mergesort",
    )

    miss["position"] = np.arange(1, len(miss) + 1, dtype="int64") + last
    g.loc[miss.index, "position"] = miss["position"].astype("Int64")
    return g


def upload_parquet_and_json(df, client, blob_parquet_path, blob_json_path) -> None:
    bucket_parquet = client.bucket(GCS_BUCKET)
    bucket_json = client.bucket(GCS_BUCKET_MART)

    buf_p = BytesIO()
    df.to_parquet(buf_p, index=False)
    buf_p.seek(0)
    b_p = bucket_parquet.blob(blob_parquet_path)
    b_p.upload_from_file(
        buf_p,
        content_type="application/vnd.apache.parquet",
        size=len(buf_p.getvalue()),
    )

    json_path = blob_json_path
    buf_j = BytesIO()
    df.to_json(
        buf_j,
        orient="records",
        date_format="iso",
        date_unit="ms",
        default_handler=str,
    )
    buf_j.seek(0)
    b_j = bucket_json.blob(json_path)
    b_j.upload_from_file(
        buf_j,
        content_type="application/json; charset=utf-8",
        size=len(buf_j.getvalue()),
    )
    print(
        f"[INFO] Parquet gs://{GCS_BUCKET}/{blob_parquet_path} | "
        f"JSON gs://{GCS_BUCKET_MART}/{json_path}"
    )


def main():
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(BLOB_FETCH_PATH)
    df = pd.read_parquet(BytesIO(blob.download_as_bytes()))

    blob_sessions = bucket.blob(BLOB_FETCH_SESSIONS)
    df_sessions = pd.read_parquet(BytesIO(blob_sessions.download_as_bytes()))

    blob_drivers = bucket.blob(BLOB_FETCH_DRIVERS)
    df_drivers = pd.read_parquet(BytesIO(blob_drivers.download_as_bytes()))

    good_keys = df_sessions.loc[
        df_sessions["session_name"].isin(["Sprint", "Race"])
        & (~df_sessions["is_cancelled"]),
        "session_key",
    ]

    df = df.loc[df["session_key"].isin(good_keys)]

    df = df.sort_values(by=["session_key", "points"], ascending=[True, False])

    df = df.drop_duplicates(subset=["session_key", "driver_number"])
    df["driver_sort"] = df["full_name"].astype(str)

    column_convert = ["number_of_laps", "points", "position"]
    df["number_of_laps"] = df["number_of_laps"].fillna(0).astype(int)
    df["points"] = df["points"].astype(int)
    df = df.groupby("session_key", group_keys=False).apply(
        fill_position_by_laps, include_groups=False
    )

    totals = (
        df.groupby("driver_number", as_index=False)["points"]
        .sum()
        .rename(columns={"points": "TotalPoints"})
    )

    df_drivers = df_drivers.drop(columns=["TotalPoints"], errors="ignore")
    df_drivers = df_drivers.merge(totals, on="driver_number", how="left")
    df_drivers["TotalPoints"] = df_drivers["TotalPoints"].fillna(0).astype(int)

    df_drivers = df_drivers.sort_values(by="TotalPoints", ascending=False)

    team_points = df_drivers.groupby("team_name", as_index=False)["TotalPoints"].sum()
    team_points = team_points.sort_values(by="TotalPoints", ascending=False)

    upload_parquet_and_json(df, client, BLOB_PUSH, BLOB_PUSH_JSON)
    upload_parquet_and_json(
        df_drivers, client, BLOB_PUSH_DRIVERS, BLOB_PUSH_DRIVERS_JSON
    )
    upload_parquet_and_json(
        team_points, client, BLOB_PUSH_TEAM_POINTS, BLOB_PUSH_TEAM_POINTS_JSON
    )


if __name__ == "__main__":
    main()
