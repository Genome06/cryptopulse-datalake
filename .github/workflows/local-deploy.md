# Local Deployment Guide (Manual)

GitHub Actions CI/CD is designed for **validation only** (syntax check, security scan, build validation).

For **actual deployment** on your local machine, follow these steps:

## Prerequisites

- Docker Desktop running
- PostgreSQL 17 running on localhost:5432
- `.env` file configured with your credentials
- GitHub repository pulled/updated

## Local Deployment Steps

### 1. Pull Latest Code
```bash
cd cryptopulse-datalake
git pull origin main
```

### 2. Verify .env Configuration
```bash
# Check that these are configured in .env
cat .env | grep -E "AWS_|POSTGRES_|ATHENA_"
```

### 3. Clean Docker Environment
```bash
docker system prune -a -f
docker volume prune -f
```

### 4. Build & Start Containers
```bash
docker-compose build --no-cache
docker-compose up -d
```

### 5. Verify All Services
```bash
docker-compose ps
# Should show all containers RUNNING/healthy
```

### 6. Access Airflow
- URL: http://localhost:8090
- Username: `admin`
- Password: `admin`

### 7. Trigger DAG Manually (Optional)
```bash
# In Airflow UI:
# 1. Click cryptopulse_lakehouse_pipeline
# 2. Click play icon → Trigger DAG
# 3. Monitor in Graph View
```

### 8. View Logs
```bash
# Airflow Scheduler
docker-compose logs -f airflow-scheduler

# Airflow Webserver
docker-compose logs -f airflow-webserver

# Spark Master
docker-compose logs -f spark-master
```

## Troubleshooting

### All containers hang or slow
```bash
docker-compose down
docker system prune -a -f
docker-compose up -d
```

### PostgreSQL connection error
```bash
# Verify PostgreSQL is running
psql -U postgres -c "SELECT 1"

# Check password is URL-encoded in .env
# @ = %40, . = %2E, * = %2A
grep POSTGRES_PASSWORD .env
```

### Spark S3 upload fails
```bash
# Verify AWS credentials
cat .env | grep AWS_

# Check S3 bucket exists
aws s3 ls s3://cryptopulse-data-lake-baltasar/
```

---

**Note**: This is the recommended deployment method for development/testing. For production, see AWS RDS setup guide below.
