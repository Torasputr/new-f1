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
GCS_BLOB_PUSH = f"{GCS_MEDAL_PUSH}/season={SEASON}/driver.parquet"

DRIVER_NUMBER_TO_COUNTRY = {
    1: "United Kingdom",
    3: "Netherlands",
    5: "Brazil",
    6: "France",
    10: "France",
    11: "Mexico",
    12: "Italy",
    14: "Spain",
    16: "Monaco",
    18: "Canada",
    23: "Thailand",
    27: "Germany",
    30: "New Zealand",
    31: "France",
    41: "United Kingdom",
    43: "Argentina",
    44: "United Kingdom",
    55: "Spain",
    63: "United Kingdom",
    77: "Finland",
    81: "Australia",
    87: "United Kingdom",
}


def driver_number_to_country(n):
    key = int(n)
    return DRIVER_NUMBER_TO_COUNTRY.get(key, "Unknown")


def upload_parquet(dataframe, client):
    buf = BytesIO()
    dataframe.to_parquet(buf, index=False)
    buf.seek(0)
    blob = client.bucket(GCS_BUCKET).blob(GCS_BLOB_PUSH)
    blob.upload_from_file(
        buf, content_type="application/vnd.apache.parquet", size=len(buf.getvalue())
    )
    print(f"[INFO] Uploaded DataFrame to GCS on {GCS_BLOB_PUSH}")


def main():
    print(f"[INFO] Fetching drivers for season {SEASON}")
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_BLOB_FETCH)

    df = pd.read_parquet(BytesIO(blob.download_as_bytes()))
    print(f"[INFO] Found {len(df)} drivers")

    print(f"[INFO] Dropping unneeded columns")
    columns_to_drop = ["meeting_key", "session_key", "country_code"]
    df = df.drop(columns=columns_to_drop)

    print(f"[INFO] Mapping driver to their country representation")
    df["country"] = df["driver_number"].map(driver_number_to_country)

    columns_to_strip = [
        "broadcast_name",
        "full_name",
        "name_acronym",
        "team_name",
        "team_colour",
        "first_name",
        "last_name",
        "headshot_url",
        "country",
    ]
    print(f"[INFO] Stripping columns for the string columns")
    for col in columns_to_strip:
        df[col] = df[col].str.strip()

    upload_parquet(df, client)


if __name__ == "__main__":
    main()
