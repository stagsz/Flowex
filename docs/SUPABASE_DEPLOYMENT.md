# Flowex Supabase Deployment Guide

Deploy Flowex using Supabase + modern PaaS providers. No AWS/Auth0 lock-in.

**Estimated Cost:** $0-25/month (free tiers available)
**Setup Time:** ~30 minutes

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │     │   Backend       │     │   Workers       │
│   (Vercel)      │────▶│   (Railway)     │────▶│   (Railway)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────────────────────────────┐
                        │           Supabase                   │
                        │  ┌─────────┬─────────┬─────────┐    │
                        │  │   Auth  │   DB    │ Storage │    │
                        │  └─────────┴─────────┴─────────┘    │
                        └─────────────────────────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   Upstash Redis │
                        │   (Serverless)  │
                        └─────────────────┘
```

### Services Used

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| **Supabase** | Auth + PostgreSQL + Storage | 500MB DB, 1GB storage |
| **Railway** | Backend + Celery workers | $5 credit/month |
| **Vercel** | Frontend hosting | 100GB bandwidth |
| **Upstash** | Serverless Redis | 10K commands/day |

---

## Phase 1: Supabase Project Setup

### 1.1 Create Project

1. Go to [supabase.com](https://supabase.com) and sign up
2. Click **New Project**
3. Configure:
   - **Name:** `flowex-production`
   - **Database Password:** Generate strong password (save it!)
   - **Region:** Choose closest to your users
4. Wait ~2 minutes for provisioning

### 1.2 Get Credentials

Go to **Settings** → **API** and note:

```
Project URL:        https://xxxxxxxxx.supabase.co
Anon Key:           eyJhbGciOiJIUzI1NiIs...  (public)
Service Role Key:   eyJhbGciOiJIUzI1NiIs...  (secret - backend only)
JWT Secret:         your-jwt-secret           (Settings → API → JWT Settings)
```

Go to **Settings** → **Database** and get connection string:
```
postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

### 1.3 Configure Authentication

1. Go to **Authentication** → **Providers**
2. Enable desired providers:

**Email/Password (Recommended for start):**
- Toggle **Email** provider ON
- Configure email templates if desired

**Google OAuth (Optional):**
1. Create OAuth app at [console.cloud.google.com](https://console.cloud.google.com)
2. Set redirect URL: `https://xxxxxxxxx.supabase.co/auth/v1/callback`
3. Copy Client ID and Secret to Supabase

**Microsoft OAuth (Optional):**
1. Create app at [portal.azure.com](https://portal.azure.com) → Azure Active Directory
2. Set redirect URL: `https://xxxxxxxxx.supabase.co/auth/v1/callback`
3. Copy Client ID and Secret to Supabase

### 1.4 Create Storage Bucket

1. Go to **Storage** → **New Bucket**
2. Create bucket:
   - **Name:** `drawings`
   - **Public:** OFF
   - **File size limit:** 50 MB
   - **Allowed MIME types:** `application/pdf, image/png, image/jpeg`

3. Add storage policies (SQL Editor):

```sql
-- Backend service role full access
CREATE POLICY "Service role full access" ON storage.objects
FOR ALL TO service_role
USING (bucket_id = 'drawings')
WITH CHECK (bucket_id = 'drawings');

-- Authenticated users can read their org files
CREATE POLICY "Users read own org files" ON storage.objects
FOR SELECT TO authenticated
USING (
  bucket_id = 'drawings' AND
  (storage.foldername(name))[1] = 'organizations'
);
```

### 1.5 Run Database Migrations

You'll run this after setting up the backend, but prepare the command:

```bash
# Will run from Railway console or locally
alembic upgrade head
```

---

## Phase 2: Redis Setup (Upstash)

### 2.1 Create Upstash Database

1. Go to [upstash.com](https://upstash.com) and sign up
2. Click **Create Database**
3. Configure:
   - **Name:** `flowex-redis`
   - **Region:** Same as Supabase (e.g., eu-west-1)
   - **TLS:** Enabled
4. Copy the **Redis URL** (starts with `rediss://`)

```
REDIS_URL=rediss://default:xxxxx@eu1-xxxxx.upstash.io:6379
```

---

## Phase 3: Backend Deployment (Railway)

### 3.1 Create Railway Project

1. Go to [railway.app](https://railway.app) and sign up with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your Flowex repository
4. Railway will detect the project structure

### 3.2 Configure Backend Service

1. Click **Add Service** → **GitHub Repo** → Select `backend` folder
2. Or configure the existing service:

**Settings → General:**
- **Root Directory:** `/backend`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Settings → Build:**
- **Builder:** Nixpacks (auto-detected)
- **Build Command:** `pip install -r requirements.txt`

### 3.3 Add Environment Variables

Go to **Variables** and add:

```bash
# Application
DEBUG=false
LOG_JSON_FORMAT=true

# Auth Provider
AUTH_PROVIDER=supabase

# Supabase
SUPABASE_URL=https://xxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase
SUPABASE_STORAGE_BUCKET=drawings
STORAGE_PROVIDER=supabase

# Database
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

# Redis
REDIS_URL=rediss://default:xxxxx@eu1-xxxxx.upstash.io:6379

# JWT (generate secure key)
JWT_SECRET_KEY=generate-a-secure-random-string-here

# CORS (will update after frontend deploy)
CORS_ORIGINS=["http://localhost:5173"]
```

Generate JWT secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3.4 Deploy Celery Worker

1. Click **Add Service** → **GitHub Repo**
2. Configure:
   - **Root Directory:** `/backend`
   - **Start Command:** `celery -A app.core.celery_app worker --loglevel=info`
3. Copy the same environment variables from the backend service

### 3.5 Run Database Migrations

1. Go to Backend service → **Settings** → **Railway Shell**
2. Run:
```bash
alembic upgrade head
```

Or use Railway CLI locally:
```bash
railway run alembic upgrade head
```

### 3.6 Get Backend URL

After deployment, Railway provides a URL like:
```
https://flowex-backend-production.up.railway.app
```

Note this for frontend configuration.

---

## Phase 4: Frontend Deployment (Vercel)

### 4.1 Connect Repository

1. Go to [vercel.com](https://vercel.com) and sign up with GitHub
2. Click **Add New** → **Project**
3. Import your Flowex repository

### 4.2 Configure Build Settings

- **Framework Preset:** Vite
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm ci --legacy-peer-deps`

### 4.3 Add Environment Variables

```bash
# Backend API URL (from Railway)
VITE_API_URL=https://flowex-backend-production.up.railway.app

# Supabase (for frontend auth)
VITE_SUPABASE_URL=https://xxxxxxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...

# Disable dev bypass
VITE_DEV_AUTH_BYPASS=false

# Optional: Sentry
VITE_SENTRY_DSN=
VITE_SENTRY_ENVIRONMENT=production
```

### 4.4 Deploy

Click **Deploy**. Vercel will build and deploy your frontend.

Your frontend URL will be:
```
https://flowex.vercel.app
```

Or configure a custom domain in Vercel settings.

---

## Phase 5: Final Configuration

### 5.1 Update CORS Origins

Go back to Railway backend and update:

```bash
CORS_ORIGINS=["https://flowex.vercel.app","https://your-custom-domain.com"]
```

### 5.2 Update Supabase Auth URLs

Go to Supabase → **Authentication** → **URL Configuration**:

- **Site URL:** `https://flowex.vercel.app`
- **Redirect URLs:**
  - `https://flowex.vercel.app/auth/callback`
  - `https://flowex.vercel.app`

### 5.3 Verify Deployment

1. **Health Check:**
```bash
curl https://flowex-backend-production.up.railway.app/health
```

2. **Frontend:** Open `https://flowex.vercel.app`

3. **Test Auth Flow:** Sign up with email or OAuth

4. **Test Upload:** Upload a test PDF

---

## Alternative Providers

### Backend Alternatives

**Render.com:**
```yaml
# render.yaml
services:
  - type: web
    name: flowex-backend
    env: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
      # ... other vars
```

**Fly.io:**
```bash
cd backend
fly launch --name flowex-backend
fly secrets set DATABASE_URL="..." SUPABASE_URL="..." # etc
fly deploy
```

### Frontend Alternatives

**Netlify:**
```toml
# netlify.toml
[build]
  base = "frontend"
  command = "npm run build"
  publish = "dist"

[build.environment]
  VITE_API_URL = "https://your-backend.railway.app"
```

**Cloudflare Pages:**
- Build command: `npm run build`
- Build output directory: `frontend/dist`
- Root directory: `frontend`

---

## Cost Breakdown

### Free Tier (Hobby/Development)

| Service | Free Tier | Limits |
|---------|-----------|--------|
| Supabase | Free | 500MB DB, 1GB storage, 2GB bandwidth |
| Railway | $5/month credit | Usually covers light usage |
| Vercel | Free | 100GB bandwidth, 100 deployments/day |
| Upstash | Free | 10K commands/day |
| **Total** | **$0-5/month** | |

### Production Tier

| Service | Pro Tier | Limits |
|---------|----------|--------|
| Supabase Pro | $25/month | 8GB DB, 100GB storage |
| Railway Team | $20/month + usage | No limits |
| Vercel Pro | $20/month | 1TB bandwidth |
| Upstash Pay-as-you-go | ~$1-5/month | Per command |
| **Total** | **~$70/month** | |

---

## Troubleshooting

### Backend won't start

```bash
# Check Railway logs
railway logs

# Common issues:
# - Missing environment variables
# - Database connection string wrong (use port 6543 for pooler)
# - Redis URL missing 'rediss://' (with TLS)
```

### Authentication not working

1. Check `AUTH_PROVIDER=supabase` is set
2. Verify `SUPABASE_JWT_SECRET` matches Supabase dashboard
3. Check Supabase redirect URLs include your frontend domain

### Storage upload fails

1. Verify `drawings` bucket exists in Supabase
2. Check storage policies are created
3. Verify `SUPABASE_SERVICE_ROLE_KEY` is set (not anon key)

### CORS errors

1. Update `CORS_ORIGINS` to include your frontend URL
2. Include both `https://` and trailing slash variations
3. Restart backend service after changing

### Celery tasks not running

1. Check Celery worker is running (separate Railway service)
2. Verify `REDIS_URL` is same in both backend and worker
3. Check Upstash connection (TLS required: `rediss://`)

---

## Monitoring

### Supabase Dashboard
- **Database:** Monitor connections, queries, storage
- **Auth:** User signups, active sessions
- **Storage:** Bandwidth, file counts

### Railway Dashboard
- **Metrics:** CPU, memory, network
- **Logs:** Real-time application logs

### Optional: Sentry
Add `SENTRY_DSN` to both backend and frontend for error tracking.

---

## Migration to Production Scale

When you outgrow free tiers:

1. **Supabase Pro** ($25/month) - More DB/storage
2. **Railway Team** ($20/month) - Better support, no sleep
3. **Dedicated Redis** - If Upstash limits hit

Or migrate to AWS using the existing Terraform configuration in `terraform/`.

---

*Last updated: 2026-01-20*
