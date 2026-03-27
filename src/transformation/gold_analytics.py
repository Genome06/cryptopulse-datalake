# Gold Analytics Transformation
# This script performs advanced analytics on the Silver Layer data to create Gold Layer tables.
import os
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, desc, round, avg, first, last, lit

def create_spark_session():
    """
    Initializes Spark Session with S3A and AWS configurations and required packages.
    Includes partitionOverwriteMode=dynamic to prevent data loss when overwriting partitions.
    """
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "ap-southeast-2")
    
    return SparkSession.builder \
        .master("spark://spark:7077") \
        .appName("CryptoPulse-Gold-Analytics") \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.access.key", access_key) \
        .config("spark.hadoop.fs.s3a.secret.key", secret_key) \
        .config("spark.hadoop.fs.s3a.endpoint", f"s3.{region}.amazonaws.com") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic") \
        .getOrCreate()

def run_gold_transformation():
    """
    Executes full Gold Layer analytics including Leaders, Liquidity, and Trends.
    Uses dynamic date handling to avoid hardcoding.
    """
    spark = create_spark_session()
    bucket_name = os.getenv("AWS_BUCKET_NAME")
    
    # --- DYNAMIC DATE HANDLING ---
    # Automatically detect current date for filtering and partitioning
    now = datetime.now()
    curr_year = now.strftime("%Y")
    curr_month = now.strftime("%m")
    curr_day = now.strftime("%d")
    report_date = now.strftime("%Y-%m-%d")

    # 1. EXTRACT: Read from Silver Layer
    silver_path = f"s3a://{bucket_name}/silver/prices/"
    df = spark.read.parquet(silver_path)

    # Filter for the latest data available for snapshots
    latest_df = df.filter(
        (col("year") == curr_year) & 
        (col("month") == curr_month) & 
        (col("day") == curr_day)
    )

    print(f"Processing Gold Layer for date: {report_date}")

    # 2. TRANSFORM: Top 10 Market Leaders
    market_leaders = latest_df.select("coin_id", "symbol", "price_usd", "market_cap_usd") \
        .orderBy(desc("market_cap_usd")) \
        .limit(10) \
        .withColumn("report_date", lit(report_date))

    # 3. TRANSFORM: Liquidity Analysis
    liquidity_analysis = latest_df.withColumn(
            "liquidity_ratio", 
            round(col("volume_24h") / col("market_cap_usd"), 4)
        ) \
        .select("coin_id", "symbol", "liquidity_ratio") \
        .orderBy(desc("liquidity_ratio")) \
        .limit(10) \
        .withColumn("report_date", lit(report_date))

    # 4. TRANSFORM: Performance Trends (Comparison over time)
    # Aggregating historical data from Silver Layer
    coin_trends = df.groupBy("coin_id", "symbol") \
        .agg(
            first("price_usd").alias("initial_price"),
            last("price_usd").alias("current_price"),
            avg("price_usd").alias("avg_price_period")
        ) \
        .withColumn("price_change_pct", 
            round(((col("current_price") - col("initial_price")) / col("initial_price")) * 100, 2)) \
        .withColumn("report_date", lit(report_date))

    # 5. LOAD: Save results to specific Gold tables
    base_gold_path = f"s3a://{bucket_name}/gold"
    
    print("Writing analytical tables to Gold Zone...")
    
    # Use Dynamic Partition Overwrite: only replaces the partition being written (today's date)
    # Preserves historical partitions while preventing duplicates if DAG runs multiple times on the same day
    # Note: partitionOverwriteMode configured at SparkSession level (create_spark_session())
    market_leaders.write.mode("overwrite").partitionBy("report_date").parquet(f"{base_gold_path}/market_leaders/")
    liquidity_analysis.write.mode("overwrite").partitionBy("report_date").parquet(f"{base_gold_path}/liquidity_analysis/")
    coin_trends.write.mode("overwrite").partitionBy("report_date").parquet(f"{base_gold_path}/coin_trends/")

    print(f"SUCCESS: All 3 Gold analytical tables created for {report_date}")
    spark.stop()

if __name__ == "__main__":
    run_gold_transformation()