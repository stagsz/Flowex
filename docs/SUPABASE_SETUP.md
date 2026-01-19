# Supabase Setup Guide

This guide explains how to set up Supabase as the backend infrastructure for Flowex development.

## Overview

Flowex supports two infrastructure configurations:
- **Development**: Supabase (PostgreSQL + Storage)
- **Production**: AWS (RDS PostgreSQL + S3)

Supabase provides a free tier that's perfect for development and testing.

## 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up/sign in
2. Click "New Project"
3. Fill in:
   - **Name**: `flowex-dev` (or your preferred name)
   - **Database Password**: Generate a strong password (save this!)
   - **Region**: Choose the closest to you
4. Click "Create new project" and wait for provisioning (~2 minutes)

## 2. Get Your API Keys

Once your project is ready:

1. Go to **Settings** (gear icon) → **API**
2. Note down these values:
   - **Project URL**: `https://[project-ref].supabase.co`
   - **anon public key**: For frontend (public)
   - **service_role key**: For backend (keep secret!)

## 3. Get Database Connection String

1. Go to **Settings** → **Database**
2. Under "Connection string", select **URI**
3. Copy the connection string
4. Replace `[YOUR-PASSWORD]` with your database password

The format is:
```
postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

**Important**: Use port `6543` (pooler) for better connection handling.

## 4. Create Storage Bucket

1. Go to **Storage** in the left sidebar
2. Click "New bucket"
3. Create a bucket named `drawings`:
   - **Name**: `drawings`
   - **Public bucket**: OFF (unchecked)
   - **File size limit**: 50 MB
   - **Allowed MIME types**: `application/pdf, image/png, image/jpeg`
4. Click "Create bucket"

## 5. Configure Storage Policies

1. Click on the `drawings` bucket
2. Go to **Policies** tab
3. Click "New policy" → "Create a policy from scratch"

### Policy for authenticated uploads:
```sql
-- Allow authenticated users to upload to their org folder
CREATE POLICY "Allow org uploads" ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'drawings' AND
  (storage.foldername(name))[1] = 'organizations'
);
```

### Policy for backend service role (all operations):
```sql
-- Service role has full access (used by backend)
CREATE POLICY "Service role full access" ON storage.objects
FOR ALL TO service_role
USING (bucket_id = 'drawings')
WITH CHECK (bucket_id = 'drawings');
```

## 6. Set Up Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# Copy from .env.example
cp .env.example .env
```

Fill in your Supabase values:

```env
# Storage Provider
STORAGE_PROVIDER=supabase

# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_STORAGE_BUCKET=drawings

# Database (use pooler connection string)
DATABASE_URL=postgresql://postgres.abc123:[password]@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
```

## 7. Run Database Migrations

With your environment configured, run the migrations:

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

## 8. Verify Setup

Start the backend server:

```bash
uvicorn app.main:app --reload
```

Check the health endpoint:
```bash
curl http://localhost:8000/health
```

You should see:
```json
{"status": "healthy", "version": "0.1.0"}
```

## Troubleshooting

### Connection Issues

**Error**: `connection refused` or `timeout`
- Verify your DATABASE_URL uses port 6543 (pooler)
- Check if your IP is allowed (Settings → Database → Connection Pooling)

**Error**: `password authentication failed`
- Double-check your database password
- Make sure there are no special characters that need URL encoding

### Storage Issues

**Error**: `Bucket not found`
- Create the `drawings` bucket in Supabase Storage
- Verify SUPABASE_STORAGE_BUCKET matches the bucket name

**Error**: `Permission denied`
- Check storage policies are correctly set up
- Verify you're using the service_role key (not anon key) for backend

### SSL Issues

If you see SSL certificate errors:
```env
# Add to DATABASE_URL
DATABASE_URL=postgresql://...?sslmode=require
```

## Switching to Production (AWS)

When ready for production, update your `.env`:

```env
# Change storage provider
STORAGE_PROVIDER=aws

# Configure AWS
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Use AWS RDS or other PostgreSQL
DATABASE_URL=postgresql://user:pass@your-rds-endpoint:5432/flowex
```

No code changes required - the storage service automatically uses the correct provider.

## Supabase Free Tier Limits

- **Database**: 500 MB
- **Storage**: 1 GB
- **Bandwidth**: 2 GB/month
- **API requests**: 500K/month

These limits are sufficient for development and small-scale testing.

## Next Steps

1. Set up Auth0 for authentication (see Auth0 setup guide)
2. Configure Redis for Celery background tasks
3. Start developing!
