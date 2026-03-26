# PySpark Script - Process Crypto Data from AWS S3 and Store Processed Data Back to S3
import os
import sys
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, lit

def create_spark_session():
    """
    Initializes Spark Session with S3A settings and required packages.
    """
    bucket_name = os.getenv("AWS_BUCKET_NAME")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "ap-southeast-2")
    
    print(f"DEBUG: Connecting to S3 Bucket -> {bucket_name}")
    
    return SparkSession.builder \
        .master("spark://spark:7077") \
        .appName("CryptoPulse-Silver-Transformation") \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.access.key", access_key) \
        .config("spark.hadoop.fs.s3a.secret.key", secret_key) \
        .config("spark.hadoop.fs.s3a.endpoint", f"s3.{region}.amazonaws.com") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .config("spark.sql.shuffle.partitions", "4") \
        .getOrCreate()

def run_transformation():
    """
    Dynamic ETL logic for processing Top 100 coins.
    """
    spark = create_spark_session()
    bucket_name = os.getenv("AWS_BUCKET_NAME")
    
    # --- DYNAMIC PATH LOGIC ---
    # If later using Airflow, we take the date from the argument.
    # For now, we take today's date (2026/03/26).
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    
    # Dynamic input path based on the newly filled folder
    input_path = f"s3a://{bucket_name}/raw/{year}/{month}/{day}/*.json"
    
    # Partitioned output path (Standard Data Lakehouse)
    output_path = f"s3a://{bucket_name}/silver/prices/"

    print(f"Reading raw JSON from: {input_path}")
    
    # USE multiLine=true because the data is now in the form of a LIST [ ... ]
    raw_df = spark.read.option("multiLine", "true").json(input_path)

    # Transform - Schema API /markets more FLAT
    silver_df = raw_df.select(
        col("id").alias("coin_id"),
        col("symbol"),
        col("name"),
        col("current_price").cast("double").alias("price_usd"),
        col("market_cap").cast("double").alias("market_cap_usd"),
        col("total_volume").cast("double").alias("volume_24h"),
        current_timestamp().alias("processed_at"),
        lit(year).alias("year"),   # Additional column for partitioning
        lit(month).alias("month"), # Additional column for partitioning
        lit(day).alias("day")      # Additional column for partitioning
    )

    print(f"Saving Cleaned Data to Silver Layer: {output_path}")
    
    # Write the transformed DataFrame back to S3 in Parquet format, partitioned by year/month/day
    silver_df.write \
        .mode("append") \
        .partitionBy("year", "month", "day") \
        .parquet(output_path)
    
    print(f"SUCCESS: {silver_df.count()} rows processed and partitioned.")
    spark.stop()

if __name__ == "__main__":
    run_transformation()