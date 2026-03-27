# DAG file for orchestrating the crypto data pipeline using Apache Airflow
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import sys
from pyathena import connect

# Add src path for imports
sys.path.insert(0, '/opt/airflow/src')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Define paths for ingestion and transformation scripts
SRC_HOME = "/opt/airflow/src"

# Default arguments for robust execution
default_args = {
    'owner': 'baltasar_djata',
    'depends_on_past': False,
    'start_date': datetime(2026, 3, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=30),
}

def run_ingestion():
    """
    Python function to run the ingest_crypto.py script.
    Fetches data from CoinGecko API and stores to S3 Bronze layer.
    """
    print("Starting crypto data ingestion...")
    from ingestion.ingest_crypto import fetch_top_market_data, upload_to_s3
    
    bucket_name = os.getenv("AWS_BUCKET_NAME")
    data = fetch_top_market_data(per_page=100)
    if data:
        upload_to_s3(data, bucket_name, folder_name="raw")
        print("Ingestion completed successfully!")
    else:
        raise Exception("Failed to fetch data from CoinGecko")

def repair_athena_partitions():
    """
    Executes MSCK REPAIR TABLE on all Gold Layer tables in Athena.
    This updates partition metadata so Athena discovers new data automatically.
    Essential for keeping Streamlit dashboard up-to-date without manual intervention.
    """
    print("Starting Athena partition repair...")
    
    # Get Athena configuration from environment
    athena_database = os.getenv("ATHENA_DATABASE", "gold_layer")
    athena_s3_staging_dir = os.getenv("ATHENA_S3_STAGING_DIR")
    aws_region = os.getenv("AWS_REGION", "ap-southeast-2")
    
    if not athena_s3_staging_dir:
        raise Exception("ATHENA_S3_STAGING_DIR environment variable not set")
    
    # Tables to repair
    tables = ["market_leaders", "liquidity_analysis", "coin_trends"]
    
    # Connect to Athena
    conn = connect(
        region_name=aws_region,
        s3_staging_dir=athena_s3_staging_dir,
    )
    
    cursor = conn.cursor()
    
    try:
        for table in tables:
            repair_query = f"MSCK REPAIR TABLE {athena_database}.{table}"
            print(f"Executing: {repair_query}")
            cursor.execute(repair_query)
            result = cursor.fetchall()
            print(f"✓ {table} partition repair completed: {result}")
        
        print(f"SUCCESS: All {len(tables)} Gold tables are now up-to-date in Athena!")
        print("→ Streamlit dashboard can now query latest data")
    
    except Exception as e:
        print(f"ERROR: Athena partition repair failed: {str(e)}")
        raise
    
    finally:
        cursor.close()
        conn.close()

with DAG(
    'cryptopulse_lakehouse_pipeline',
    default_args=default_args,
    description='End-to-end automated crypto data pipeline: Bronze → Silver → Gold',
    schedule_interval='0 8 * * *',  # Runs daily at 08:00 UTC
    catchup=False,
    tags=['cryptopulse', 'data_engineering', 'aws'],
    doc_md="""
    ## CryptoPulse Pipeline
    Fetches crypto data from CoinGecko API, processes via PySpark,
    and loads to AWS S3 in Bronze → Silver → Gold architecture.
    """
) as dag:

    # Task 1: Ingestion (API to Bronze S3)
    ingest_data = PythonOperator(
        task_id='ingest_crypto_to_bronze',
        python_callable=run_ingestion,
        doc_md="Fetch from CoinGecko API → store raw JSON to S3 Bronze layer",
    )

    # Task 2: Silver Transformation (Bronze to Silver Parquet)
    spark_silver = BashOperator(
        task_id='spark_process_silver',
        bash_command=(
            'cd /opt/airflow/src && '
            'python transformation/spark_process.py'
        ),
        env={
            'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
            'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'AWS_REGION': os.getenv('AWS_REGION'),
            'AWS_BUCKET_NAME': os.getenv('AWS_BUCKET_NAME'),
        },
        doc_md="PySpark: clean Bronze → Silver (Parquet with missing values handled)",
    )

    # Task 3: Gold Analytics (Silver to Gold Aggregation)
    spark_gold = BashOperator(
        task_id='spark_process_gold',
        bash_command=(
            'cd /opt/airflow/src && '
            'python transformation/gold_analytics.py'
        ),
        env={
            'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
            'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'AWS_REGION': os.getenv('AWS_REGION'),
            'AWS_BUCKET_NAME': os.getenv('AWS_BUCKET_NAME'),
        },
        doc_md="PySpark: aggregate Silver → Gold (Data ready for Athena/Streamlit)",
    )

    # Task 4: Repair Athena Partitions (Update metadata for Streamlit)
    repair_athena = PythonOperator(
        task_id='repair_athena_partitions',
        python_callable=repair_athena_partitions,
        doc_md="MSCK REPAIR TABLE: auto-update Athena partition metadata so Streamlit queries latest data",
    )

    # Define the execution pipeline order
    ingest_data >> spark_silver >> spark_gold >> repair_athena