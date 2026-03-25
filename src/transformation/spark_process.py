# PySpark Script - Process Crypto Data from AWS S3 and Store Processed Data Back to S3
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp

def create_spark_session():
    """
    Initializes Spark Session with specialized S3A settings.
    Explicitly uses SimpleAWSCredentialsProvider.
    """
    bucket_name = os.getenv("AWS_BUCKET_NAME")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "ap-southeast-2")
    
    print(f"DEBUG: Connecting to S3 Bucket -> {bucket_name}")
    
    return SparkSession.builder \
        .master("spark://spark:7077") \
        .appName("CryptoPulse-Silver-Transformation") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.access.key", access_key) \
        .config("spark.hadoop.fs.s3a.secret.key", secret_key) \
        .config("spark.hadoop.fs.s3a.endpoint", f"s3.{region}.amazonaws.com") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .config("spark.hadoop.fs.s3a.socket.send.buffer", "65536") \
        .config("spark.hadoop.fs.s3a.socket.recv.buffer", "65536") \
        .config("spark.sql.shuffle.partitions", "4") \
        .getOrCreate()

def run_transformation():
    """
    Core ETL logic to clean JSON data and save as Parquet.
    """
    spark = create_spark_session()
    bucket_name = os.getenv("AWS_BUCKET_NAME")
    
    if not bucket_name:
        raise ValueError("ERROR: AWS_BUCKET_NAME is not set in environment!")

    input_path = f"s3a://{bucket_name}/raw/2026/03/25/*.json"
    output_path = f"s3a://{bucket_name}/processed/prices_parquet/"

    print(f"Reading raw JSON from: {input_path}")
    raw_df = spark.read.json(input_path)

    # Transform - Flattening the nested market_data structure
    silver_df = raw_df.select(
        col("id").alias("coin_id"),
        col("symbol"),
        col("name"),
        col("market_data.current_price.usd").cast("double").alias("price_usd"),
        col("market_data.market_cap.usd").cast("double").alias("market_cap_usd"),
        current_timestamp().alias("processed_at")
    )

    print(f"Saving Silver Layer (Parquet) to: {output_path}")
    silver_df.write.mode("overwrite").parquet(output_path)
    
    print("SUCCESS: Data transformed and saved to Silver Zone.")
    spark.stop()

if __name__ == "__main__":
    run_transformation()