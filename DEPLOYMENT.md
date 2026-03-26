# Deployment Instructions

Complete guide for deploying CryptoPulse to production.

## Table of Contents
1. [Local Deployment](#local-deployment)
2. [GitHub Repository Setup](#github-repository-setup)
3. [CI/CD Pipeline Setup](#cicd-pipeline-setup)
4. [Cloud Deployment Options](#cloud-deployment-options)
5. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Local Deployment

### Prerequisites

- **Docker Desktop** (Windows/Mac/Linux)
- **PostgreSQL 17+** (localhost:5432)
- **AWS Account** with S3 bucket
- **CoinGecko API** (free tier works)
- **Git**

### Installation Steps

**1. Clone Repository**
```bash
git clone https://github.com/YOUR-USERNAME/cryptopulse-datalake.git
cd cryptopulse-datalake
```

**2. Configure Environment**
```bash
cp .env.example .env
```

**Edit `.env`** with your actual credentials:
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalr...
AWS_REGION=ap-southeast-2
AWS_BUCKET_NAME=cryptopulse-data-lake-baltasar

# PostgreSQL (on host machine)
POSTGRES_HOST=host.docker.internal
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=%40Genome0602%2E%2A

# CoinGecko API
COINGECKO_API_KEY=YOUR_KEY (optional)
```

**3. Create PostgreSQL Database**
```bash
psql -U postgres -c "CREATE DATABASE airflow OWNER postgres;"
```

**4. Build & Start Containers**
```bash
# Clean Docker environment
docker system prune -a -f

# Build custom Airflow image
docker-compose build --no-cache

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

Expected output:
```
NAME                    STATUS
airflow-webserver       Up (healthy)
airflow-scheduler       Up (healthy)
spark-master            Up
spark-worker            Up
```

**5. Access Airflow UI**
- URL: http://localhost:8090
- Username: `admin`
- Password: `admin`

**6. Verify DAG**
1. Click **DAGs** in left menu
2. Look for `cryptopulse_lakehouse_pipeline`
3. Status should show **green checkmark** (DAG parsed successfully)

**7. Trigger DAG Manually**
1. Click `cryptopulse_lakehouse_pipeline`
2. Click **play icon** (top right)
3. Click **Trigger DAG**
4. Monitor **Graph View** for task progress

### Troubleshooting Local Deployment

**Containers won't start**
```bash
docker-compose logs -f
docker system prune -a -f
docker-compose build --no-cache
docker-compose up -d
```

**PostgreSQL connection failed**
```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT 1"

# Verify password is URL-encoded
# @ = %40, . = %2E, * = %2A
# Update .env: POSTGRES_PASSWORD=%40Genome0602%2E%2A
```

**Spark job fails with S3 error**
```bash
# Verify AWS credentials in .env
# Check bucket exists
aws s3 ls s3://cryptopulse-data-lake-baltasar/

# Check S3 connectivity from container
docker-compose exec airflow-webserver python -c \
  "import boto3; s3 = boto3.client('s3'); print(s3.list_buckets())"
```

---

## GitHub Repository Setup

### Create Repository

1. Go to https://github.com/new
2. **Repository name**: `cryptopulse-datalake`
3. **Description**: "End-to-end cryptocurrency data lakehouse pipeline"
4. Select **Private** (recommended)
5. ✅ Add `.gitignore`: Python
6. ✅ Add License: MIT
7. Click **Create repository**

### Clone & Push Code

```bash
git clone https://github.com/YOUR-USERNAME/cryptopulse-datalake.git
cd cryptopulse-datalake

# Add all files
git add .

# Verify .env is NOT included
git ls-files | grep -E "^\.env$"
# Should output nothing (good!)

# Commit
git commit -m "Initial commit: CryptoPulse data lakehouse"

# Push to GitHub
git push origin main
```

### Verify Files on GitHub

On GitHub.com, confirm:
- ✅ `README.md` (complete documentation)
- ✅ `.env.example` (template visible)
- ✅ `.env` (NOT visible - protected by `.gitignore`)
- ✅ `docker-compose.yaml`
- ✅ `Dockerfile.airflow`
- ✅ `src/` (all Python scripts)
- ✅ `.github/workflows/` (CI/CD pipelines)

---

## CI/CD Pipeline Setup

### GitHub Secrets Configuration

GitHub Actions workflows use secrets to access sensitive credentials without hardcoding them.

**1. Navigate to Secrets**
- Go to repository **Settings**
- Click **Secrets and variables** → **Actions**
- Click **New repository secret**

**2. Add 10 Secrets**

| Secret Name | Value from .env |
|---|---|
| AWS_ACCESS_KEY_ID | AWS_ACCESS_KEY_ID=... |
| AWS_SECRET_ACCESS_KEY | AWS_SECRET_ACCESS_KEY=... |
| AWS_REGION | ap-southeast-2 |
| AWS_BUCKET_NAME | cryptopulse-data-lake-baltasar |
| COINGECKO_API_KEY | (optional) |
| POSTGRES_HOST | localhost |
| POSTGRES_PORT | 5432 |
| POSTGRES_USER | postgres |
| POSTGRES_PASSWORD | %40Genome0602%2E%2A |
| POSTGRES_DB | postgres |

**3. Verify Secrets Created**
```bash
# You should see all 10 secrets in Settings → Secrets and variables
```

### Enable GitHub Actions

1. Go to repository **Actions** tab
2. Click **I understand my workflows, go ahead and enable them**

### Run Workflows

**Option A: Automatic (On Push)**
```bash
git push origin main
# Workflows automatically trigger
# Check Actions tab to monitor
```

**Option B: Manual Trigger**
1. Go to **Actions** tab
2. Click **Build & Test CryptoPulse**
3. Click **Run workflow** → **Run workflow**

### Monitor Workflow Execution

1. Go to **Actions** tab
2. Click the workflow run (top one is most recent)
3. Expand each step to see logs
4. **Green checkmark** = Step succeeded
5. **Red X** = Step failed (click to see error)

### Workflow Descriptions

**Build & Test** (`.github/workflows/build.yml`)
- Runs on: Every push + PR
- Purpose: Validate code syntax and security
- Time: ~5-10 minutes
- Status: ✅ OK = Code is clean

**Deploy** (`.github/workflows/deploy.yml`)
- Runs on: Push to `main` (manual trigger available)
- Purpose: Full deployment test
- Time: ~10-15 minutes
- Status: ✅ OK = Full pipeline works

---

## Cloud Deployment Options

### Option 1: AWS ECS (Elastic Container Service)

Deploy containers to AWS ECS with automatic scaling.

**Setup**:
1. Create AWS ECS cluster
2. Create task definition from `docker-compose.yaml`
3. Create service with ALB (load balancer)
4. Point GitHub Actions to deploy on push

**GitHub Workflow Addition**:
```yaml
- name: Deploy to ECS
  run: |
    aws ecs update-service \
      --cluster cryptopulse-cluster \
      --service cryptopulse-service \
      --force-new-deployment
```

### Option 2: Azure Container Instances (ACI)

Deploy containers to Azure without managing Kubernetes.

**Setup**:
1. Create Azure Container Registry
2. Build image and push to registry
3. Create container instance
4. Configure networking

**GitHub Workflow Addition**:
```yaml
- name: Push to Azure Container Registry
  run: |
    az login --service-principal -u ${{ secrets.AZURE_CLIENT_ID }} ...
    docker tag cryptopulse-airflow:latest myregistry.azurecr.io/cryptopulse:latest
    docker push myregistry.azurecr.io/cryptopulse:latest
```

### Option 3: Kubernetes (EKS/AKS/GKE)

Deploy to managed Kubernetes for production-grade scalability.

**Create Kubernetes manifests**:
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cryptopulse-airflow
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cryptopulse
  template:
    metadata:
      labels:
        app: cryptopulse
    spec:
      containers:
      - name: airflow
        image: cryptopulse-airflow:latest
        ports:
        - containerPort: 8080
        env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: cryptopulse-secret
              key: aws-access-key-id
        # ... more env vars
```

---

## Monitoring & Maintenance

### Health Checks

**Check Container Status**
```bash
docker-compose ps
```

**Check Airflow Webserver**
```bash
curl http://localhost:8090/health
```

**Check Postgres Connection**
```bash
docker-compose exec airflow-webserver airflow db check
```

### Logs

**Airflow Scheduler**
```bash
docker-compose logs -f airflow-scheduler
```

**Airflow Webserver**
```bash
docker-compose logs -f airflow-webserver
```

**Spark Master**
```bash
docker-compose logs -f spark-master
```

**View logs from specific time**
```bash
docker-compose logs --since 2026-03-27T08:00:00 airflow-scheduler
```

### Performance Tuning

**Increase Spark memory**:
Edit `docker-compose.yaml`:
```yaml
spark-master:
  environment:
    SPARK_DRIVER_MEMORY: 4G
    SPARK_EXECUTOR_MEMORY: 4G
```

**Increase Airflow parallelism**:
Edit `docker-compose.yaml`:
```yaml
airflow-scheduler:
  environment:
    AIRFLOW__CORE__PARALLELISM: 8
    AIRFLOW__CORE__DAG_CONCURRENCY: 4
```

### Backup & Recovery

**Backup PostgreSQL**
```bash
docker-compose exec postgres pg_dump -U postgres airflow > backup.sql
```

**Restore PostgreSQL**
```bash
docker-compose exec -T postgres psql -U postgres airflow < backup.sql
```

**S3 Data Validation**
```bash
# Check Bronze layer size
aws s3 du s3://cryptopulse-data-lake-baltasar/raw/ --human-readable

# Validate data integrity
aws s3api head-object \
  --bucket cryptopulse-data-lake-baltasar \
  --key raw/2026/03/27/top_100_crypto_*.json
```

### Update & Restart

**Update code**
```bash
git pull origin main
docker-compose build --no-cache
docker-compose down
docker-compose up -d
```

**Update Docker images**
```bash
docker-compose pull
docker-compose up -d
```

### Scheduled Maintenance

**Weekly**:
- [ ] Check Airflow logs for errors
- [ ] Verify S3 data is being written correctly
- [ ] Monitor disk space usage

**Monthly**:
- [ ] Review CPU/memory usage
- [ ] Update Python dependencies
- [ ] Test disaster recovery procedures

**Quarterly**:
- [ ] Review AWS costs
- [ ] Optimize Spark configurations
- [ ] Plan capacity increase if needed

---

## Production Checklist

Before deploying to production:

- [ ] All tests pass in GitHub Actions
- [ ] GitHub Secrets configured (10 secrets)
- [ ] `.env` is NOT committed to GitHub
- [ ] PostgreSQL backup strategy defined
- [ ] S3 bucket versioning enabled
- [ ] AWS IAM policy uses least privilege
- [ ] Monitoring/alerting configured
- [ ] Documentation updated
- [ ] Team has access to credentials (via vault/1Password/etc)
- [ ] Disaster recovery plan documented

---

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Review [README.md](README.md)
3. Check GitHub Issues
4. Search error message on Stack Overflow

---

**Status**: Ready for production deployment ✅
