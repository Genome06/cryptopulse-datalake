# AWS RDS PostgreSQL Setup for Production

Untuk production deployment dan GitHub Actions CI/CD yang benar-benar bisa run, gunakan AWS RDS (Relational Database Service) instead of localhost PostgreSQL.

## Step 1: Create AWS RDS PostgreSQL Instance

### Via AWS Console

1. Go to https://console.aws.amazon.com/rds/
2. Click **Create database**
3. Select **PostgreSQL**
4. Configuration:
   - **DB instance identifier**: `cryptopulse-postgres`
   - **Master username**: `postgres`
   - **Master password**: Use strong password (e.g., `MySecure!Pass123`)
   - **DB instance class**: `db.t3.micro` (free tier eligible)
   - **Storage**: `20 GB` (free tier eligible)
   - **Public accessibility**: `Yes` (so GitHub Actions can connect)
   - **VPC security group**: Create new or select existing
5. Click **Create database**

In security group, add inbound rule:
- **Protocol**: TCP
- **Port**: 5432
- **Source**: `0.0.0.0/0` (open to internet) or specific IP

### Via AWS CLI

```bash
aws rds create-db-instance \
  --db-instance-identifier cryptopulse-postgres \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password MySecure!Pass123 \
  --allocated-storage 20 \
  --publicly-accessible \
  --region ap-southeast-2
```

## Step 2: Get RDS Endpoint

After instance created (~5 minutes):

1. Go to **RDS Dashboard** → **Databases**
2. Click `cryptopulse-postgres`
3. Copy **Endpoint** (looks like: `cryptopulse-postgres.xxxxx.ap-southeast-2.rds.amazonaws.com`)

## Step 3: Update GitHub Secrets

Now update your GitHub repository secrets with RDS endpoint:

1. Go to GitHub → Repository **Settings** → **Secrets and variables** → **Actions**
2. Update these secrets:

| Secret | Old Value | New Value |
|--------|-----------|-----------|
| POSTGRES_HOST | `localhost` | `cryptopulse-postgres.xxxxx.ap-southeast-2.rds.amazonaws.com` |
| POSTGRES_PASSWORD | `%40Genome0602%2E%2A` | `MySecure!Pass123` (URL-encoded if needed) |

## Step 4: Update Local .env (Optional)

If you want to use RDS locally too:

```bash
cp .env .env.backup  # Backup
```

Edit `.env`:
```
POSTGRES_HOST=cryptopulse-postgres.xxxxx.ap-southeast-2.rds.amazonaws.com
POSTGRES_PASSWORD=MySecure!Pass123
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_DB=postgres
```

Then test:
```bash
psql -h cryptopulse-postgres.xxxxx.ap-southeast-2.rds.amazonaws.com -U postgres -d postgres -c "SELECT 1"
# Enter password when prompted
```

## Step 5: Initialize Database

Create `airflow` database in RDS:

```bash
# Using psql locally
psql -h cryptopulse-postgres.xxxxx.ap-southeast-2.rds.amazonaws.com -U postgres -c "CREATE DATABASE airflow OWNER postgres;"

# Or via AWS RDS Query Editor (in AWS Console)
CREATE DATABASE airflow OWNER postgres;
```

## Step 6: Test GitHub Actions

1. Push a change to GitHub:
```bash
git add .
git commit -m "Update for AWS RDS"
git push origin main
```

2. Go to **Actions** tab on GitHub
3. Watch workflow run
4. Should now complete successfully! ✅

## Cost Considerations

| Item | Cost |
|------|------|
| db.t3.micro | ~$9/month |
| 20GB storage | Included in free tier (first 12 months) |
| Data transfer | Charged if accessing from outside AWS |

**Recommendation**: Use AWS RDS free tier for first 12 months, then optimize.

## Backup & Recovery

### Enable automated backups:
```bash
aws rds modify-db-instance \
  --db-instance-identifier cryptopulse-postgres \
  --backup-retention-period 7 \
  --apply-immediately
```

### Manual snapshot:
```bash
aws rds create-db-snapshot \
  --db-snapshot-identifier cryptopulse-backup-$(date +%Y%m%d) \
  --db-instance-identifier cryptopulse-postgres
```

## Production Checklist

- [ ] RDS instance created and running
- [ ] Security group allows inbound on port 5432 from GitHub Actions
- [ ] Database `airflow` created
- [ ] GitHub Secrets updated with RDS endpoint
- [ ] Tested local connection: `psql -h <endpoint> -U postgres`
- [ ] GitHub Actions workflow passed with RDS
- [ ] Backups enabled (7-day retention minimum)
- [ ] Monitoring enabled (CloudWatch alarms optional)

---

**Next Steps**:
1. Create RDS instance (5 min)
2. Update GitHub Secrets (2 min)
3. Push code to trigger CI/CD (5 min)
4. Monitor workflow execution

That's it! Your GitHub Actions CI/CD will now work end-to-end. 🚀
