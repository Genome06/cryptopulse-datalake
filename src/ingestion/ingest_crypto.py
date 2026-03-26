# Python Script - Ingest Top 100 Crypto Data from CoinGecko and Store in AWS S3
import os
import json
import requests
import boto3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fetch_top_market_data(per_page=100):
    """
    Fetches market data for the top N coins by market cap.
    Uses the /coins/markets endpoint for bulk data.
    """
    base_url = os.getenv("COINGECKO_BASE_URL")
    api_key = os.getenv("COINGECKO_API_KEY")
    
    # Endpoint for bulk market data
    url = f"{base_url}/coins/markets"
    
    # Parameters for the request
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": 1,
        "sparkline": "false"
    }
    
    headers = {
        "accept": "application/json",
        "x-cg-demo-api-key": api_key
    }

    try:
        print(f"Fetching top {per_page} coins from CoinGecko...")
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status() 
        data = response.json()
        print(f"Successfully retrieved {len(data)} coins.")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CoinGecko: {e}")
        return None

def upload_to_s3(data, bucket_name, folder_name="raw"):
    """
    Uploads the raw JSON list to AWS S3 bucket with date partitioning.
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )

    now = datetime.now()
    timestamp = now.strftime("%H%M%S")
    date_path = now.strftime("%Y/%m/%d")
    file_name = f"top_100_crypto_{timestamp}.json"
    
    s3_key = f"{folder_name}/{date_path}/{file_name}"

    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(data) # Data is now a list of 100 dictionaries
        )
        print(f"Successfully uploaded bulk data to: s3://{bucket_name}/{s3_key}")
        return s3_key
    except Exception as e:
        print(f"Failed to upload data to S3: {e}")
        return None

if __name__ == "__main__":
    print("--- CryptoPulse Ingestion: Bronze Layer (Bulk Mode) ---")
    
    # 1. Fetch Top 100 Coins
    raw_data = fetch_top_market_data(per_page=100)
    
    if raw_data:
        # 2. Upload to S3
        target_bucket = os.getenv("AWS_BUCKET_NAME")
        upload_to_s3(raw_data, target_bucket)
    else:
        print("Ingestion failed: No data retrieved.")