# Python Script - Ingest Crypto Data from CoinGecko API and Store in AWS S3
import os
import json
import requests
import boto3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file for security
load_dotenv()

def fetch_crypto_data(coin_id="bitcoin"):
    """
    Fetches raw market data from CoinGecko API.
    The Base URL is retrieved from environment variables for flexibility.
    """
    # Retrieve configuration from environment
    base_url = os.getenv("COINGECKO_BASE_URL")
    api_key = os.getenv("COINGECKO_API_KEY")
    
    # Construct the full endpoint URL
    url = f"{base_url}/coins/{coin_id}"
    
    headers = {
        "accept": "application/json",
        "x-cg-demo-api-key": api_key
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CoinGecko: {e}")
        return None

def upload_to_s3(data, bucket_name, folder_name="raw"):
    """
    Uploads the raw JSON data to AWS S3 bucket.
    Implements partitioning by Date (YYYY/MM/DD).
    """
    # Initialize S3 client using credentials from .env
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )

    # Generate unique filename and partitioned path 
    now = datetime.now()
    timestamp = now.strftime("%H%M%S")
    date_path = now.strftime("%Y/%m/%d")
    file_name = f"crypto_data_{timestamp}.json"
    
    # Final S3 Key (path in the bucket)
    s3_key = f"{folder_name}/{date_path}/{file_name}"

    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(data)
        )
        print(f"Successfully uploaded raw data to: s3://{bucket_name}/{s3_key}")
        return s3_key
    except Exception as e:
        print(f"Failed to upload data to S3: {e}")
        return None

if __name__ == "__main__":
    print("Starting CryptoPulse Ingestion Process...")
    
    # 1. Fetch data [cite: 11]
    raw_data = fetch_crypto_data("bitcoin")
    
    if raw_data:
        # 2. Load bucket name from environment variable
        target_bucket = os.getenv("AWS_BUCKET_NAME")
        
        # 3. Upload to Bronze Layer (Raw Zone) 
        upload_to_s3(raw_data, target_bucket)
    else:
        print("Ingestion failed: No data retrieved.")