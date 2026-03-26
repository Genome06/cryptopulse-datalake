# DAG file for orchestrating the crypto data pipeline using Apache Airflow
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import sys

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

    # Define the execution pipeline order
    ingest_data >> spark_silver >> spark_gold