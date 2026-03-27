# GitHub Setup Guide for CryptoPulse

This guide walks you through preparing your GitHub repository for CI/CD deployment of CryptoPulse.

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Enter repository name: `cryptopulse-datalake`
3. Select **Private** (recommended) or **Public**
4. ✅ Add `.gitignore` for Python
5. ✅ Add MIT License
6. Click **Create repository**

## Step 2: Clone & Push Code

```bash
git clone https://github.com/YOUR-USERNAME/cryptopulse-datalake.git
cd cryptopulse-datalake
git checkout main
git add .
git commit -m "Initial commit: CryptoPulse data lakehouse pipeline"
git push origin main
```

**Verify**:
- ✅ `.env` is NOT in the repository (protected by `.gitignore`)
- ✅ `.env.example` IS committed
- ✅ All source files are present

## Step 3: Configure GitHub Secrets

GitHub Secrets allow you to store sensitive credentials that workflows can use without hardcoding them.

### Access GitHub Secrets

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. Click **Secrets and variables** → **Actions** (left sidebar)
4. Click **New repository secret**

### Add Each Secret

Create the following secrets with values from your `.env` file:

#### 1. AWS_ACCESS_KEY_ID
- **Name**: `AWS_ACCESS_KEY_ID`
- **Value**: Copy from `.env` → `AWS_ACCESS_KEY_ID=AKIA...`

#### 2. AWS_SECRET_ACCESS_KEY
- **Name**: `AWS_SECRET_ACCESS_KEY`
- **Value**: Copy from `.env` → `AWS_SECRET_ACCESS_KEY=wJalr...`

#### 3. AWS_REGION
- **Name**: `AWS_REGION`
- **Value**: `ap-southeast-2` (or your region)

#### 4. AWS_BUCKET_NAME
- **Name**: `AWS_BUCKET_NAME`
- **Value**: `cryptopulse-data-lake-baltasar` (your bucket name)

#### 5. COINGECKO_API_KEY
- **Name**: `COINGECKO_API_KEY`
- **Value**: Your CoinGecko API key (optional, free tier works)

#### 6. POSTGRES_HOST ⚠️ IMPORTANT
- **Name**: `POSTGRES_HOST`
- **Value**: **CHOOSE ONE**:

| Strategy | Value | When to Use |
|----------|-------|------------|
| **Development (Local)** | `localhost` | Testing on local machine only |
| **Production (AWS RDS)** | `cryptopulse-postgres.xxxxx.ap-southeast-2.rds.amazonaws.com` | GitHub Actions CI/CD + Production |

**Recommended**: Use **AWS RDS** for GitHub Actions workflows to work properly.
See [AWS_RDS_SETUP.md](../AWS_RDS_SETUP.md) for complete RDS configuration guide.

#### 7. POSTGRES_PORT
- **Name**: `POSTGRES_PORT`
- **Value**: `5432`

#### 8. POSTGRES_USER
- **Name**: `POSTGRES_USER`
- **Value**: `postgres`

#### 9. POSTGRES_PASSWORD
- **Name**: `POSTGRES_PASSWORD`
- **Value**: Your PostgreSQL password (URL-encoded if contains special chars)

#### 10. POSTGRES_DB
- **Name**: `POSTGRES_DB`
- **Value**: `postgres`

### Verify Secrets Are Configured

```bash
# In GitHub UI, you should see 10 secrets:
✅ AWS_ACCESS_KEY_ID
✅ AWS_SECRET_ACCESS_KEY
✅ AWS_REGION
✅ AWS_BUCKET_NAME
✅ COINGECKO_API_KEY
✅ POSTGRES_HOST
✅ POSTGRES_PORT
✅ POSTGRES_USER
✅ POSTGRES_PASSWORD
✅ POSTGRES_DB
```

## Step 4: Enable GitHub Actions

1. Go to your repository **Actions** tab
2. Select **I understand my workflows, go ahead and enable them**
3. This activates the CI/CD workflows

## Step 5: Choose Your Deployment Strategy

### Option A: Local Development Only (✅ Simple, ❌ No CI/CD)

- Keep `POSTGRES_HOST=localhost`
- Deploy manually via `docker-compose up -d` on your machine
- CI/CD will validate code only (syntax, security)
- **Guide**: See [.github/workflows/local-deploy.md](workflows/local-deploy.md)

### Option B: Production with GitHub Actions (⚠️ Requires AWS RDS)

- Create AWS RDS PostgreSQL instance (see [AWS_RDS_SETUP.md](../AWS_RDS_SETUP.md))
- Update `POSTGRES_HOST` to RDS endpoint
- CI/CD will fully validate + test on GitHub servers
- **Recommended for team projects**

## Step 6: Test Workflows Manually

### Test Build & Validate Workflow

1. Go to **Actions** tab
2. Click **Build & Validate CryptoPulse** workflow
3. Click **Run workflow** → **Run workflow**
4. Wait for it to complete ✅
   - Validates DAG syntax
   - Checks Python code
   - Security scan
   - Docker build test

**Expected Result**: All checks pass (green checkmarks)

## Step 6: Branch Protection Rules (Optional)

To prevent direct pushes to `main` and require workflow success:

1. Go to **Settings** → **Branches**
2. Click **Add rule** under Branch protection rules
3. Branch name pattern: `main`
4. ✅ Enable:
   - Require a pull request before merging
   - Require status checks to pass
   - Require branches to be up to date
   - Restrict who can push to matching branches

## Understanding the Workflows

### `.github/workflows/build.yml`
**Triggers**: On every push to `main` or `develop`, and on PRs

**Steps**:
1. Checkout code
2. Build Airflow Docker image
3. Validate DAG Python syntax
4. Check transformation scripts
5. Security scan with Bandit
6. Verify docker-compose configuration

**Status**: ✅ OK = Code is syntactically correct and secure

### `.github/workflows/deploy.yml`
**Triggers**: On push to `main` only (workflow_dispatch for manual trigger)

**Steps**:
1. Checkout code
2. Build Docker image
3. Create `.env` from GitHub Secrets
4. Start all containers (`docker-compose up -d`)
5. Wait for Airflow to be healthy
6. Verify DAG is loaded
7. Test PostgreSQL connection
8. Test S3 connection
9. Run DAG manual test
10. Cleanup

**Status**: ✅ OK = Full deployment successful

## Monitoring Workflow Runs

### In GitHub UI

1. Go to **Actions** tab
2. Click any workflow run to see details
3. Expand steps to see logs
4. Click **Artifacts** to download logs

### Common Issues & Fixes

| Error | Fix |
|-------|-----|
| `Secret not found` | Verify secret name exactly matches workflow `${{ secrets.NAME }}` |
| `Airflow won't start` | Check PostgreSQL is running and password is URL-encoded |
| `S3 connection failed` | Verify AWS credentials and bucket exists |
| `Docker image build fails` | Check Dockerfile syntax in local build first |

## CI/CD Flow Summary

```
┌─────────────────────────────────────────┐
│ Push to GitHub (main branch)            │
└────────────────┬────────────────────────┘
                 ↓
        ┌────────────────────┐
        │ Build workflow runs│
        └────────┬───────────┘
                 ↓ (if successful)
        ┌────────────────────┐
        │Deploy workflow runs│
        └────────┬───────────┘
                 ↓ (if successful)
        ✅ Pipeline deployed
           (Airflow running,
            ready for data)
```

## Next Steps

1. ✅ Push code to GitHub
2. ✅ Configure 10 GitHub Secrets
3. ✅ Enable GitHub Actions
4. ✅ Run workflows manually to verify
5. ✅ Monitor workflow execution logs
6. 🔄 From now on: Push code → Workflows auto-run → Pipeline auto-deploys

## Security Best Practices

- ✅ Never commit `.env` (protected by `.gitignore`)
- ✅ Store all credentials as GitHub Secrets (not in code)
- ✅ Use role-based AWS IAM policy (least privilege)
- ✅ Rotate credentials regularly
- ✅ Enable branch protection on `main`
- ✅ Require PR reviews before merge
- ✅ Keep dependencies updated (run `docker-compose pull` periodically)

## Troubleshooting

### Secrets Not Available in Workflow

**Problem**: `${{ secrets.AWS_ACCESS_KEY_ID }}` appears as environment variable

**Solution**: 
- Verify secret name matches exactly
- Secret names are case-sensitive
- Wait 30 seconds after creating secret for it to be available

### Workflow Fails But Local Test Works

**Problem**: `docker-compose build` works locally but fails in GitHub Actions

**Solution**:
- GitHub Actions runs in a clean Ubuntu environment
- Ensure all dependencies are in `requirements.txt` or `Dockerfile`
- Test with `docker system prune -a` locally to simulate clean environment

### Permission Denied Error

**Problem**: `Permission denied` when GitHub Actions tries to access AWS/PostgreSQL

**Solution**:
- Verify AWS IAM user has S3 permissions
- Verify PostgreSQL user has database permissions
- Check credentials are correct in GitHub Secrets

## Documentation

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Compose in CI/CD](https://docs.docker.com/build/ci/)

---

**Status**: Ready for GitHub CI/CD deployment ✅
