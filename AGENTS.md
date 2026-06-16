# AGENTS.md

This file provides guidance to the AI agent when working with code in this repository.

## Project Overview

WeChat Mini Program + Flask backend for hairstyle transfer (发型迁移). Uses Alibaba Cloud AI APIs (hair segmentation, face fusion, Bailian sketch) with virtual currency (scissor_hairs / comb_hairs dual-balance system).

## Commands

### Backend

```bash
cd backend
pip install -r requirements.txt   # install deps
python init_db.py                 # init database (must run after model changes)
python app.py                     # start dev server on port 5003
```

- Server runs on **port 5003** (not the default 5000)
- No migration framework (no Alembic) — schema changes use manual `migrate_*.py` scripts in `backend/`
- Tests are individual `test_*.py` scripts, run with `python test_<name>.py`

### Frontend

- Open `miniprogram/` directory in **WeChat DevTools** — no build step
- API base URL: `miniprogram/utils/constants.js`

## Key Gotchas

- **Module imports are fragile** — `app.py` uses try/except with fallbacks for optional modules (`api.py`, `auth.py`, `models.py`, etc.). If a module fails to import, the app still starts with reduced functionality. Always verify imports after changes.
- **Two balance types**: `scissor_hairs` (剪刀卡槽) and `comb_hairs` (梳子卡槽). Many operations consume from both. Guest users only get `comb_hairs`.
- **Pricing is duplicated** across `backend/config.py` and `miniprogram/utils/constants.js`. Changes to pricing must be made in both places.
- **Developer mode**: IDs in `DEVELOPER_ACCOUNTS` (from `.env` or `debug_config.py`) bypass normal payment/permission checks. `debug_config.py` is gitignored.
- **Image URLs must be public**: Alibaba Cloud AI APIs require publicly accessible URLs. Images are uploaded to Alibaba Cloud OSS before processing.
- **Celery** is listed in requirements but used only for scheduled tasks (`scheduler.py`). Worker: `celery -A scheduler:make_celery worker --loglevel=info`
- **Production deploy**: files are scp'd to `139.196.105.33:/opt/hairstyle-transfer-v5.3-release/`

## Domain Whitelist Rules (CRITICAL)

**Problem**: WeChat Mini Program APIs (`wx.getImageInfo`, `wx.downloadFile`, `wx.saveImageToPhotosAlbum`) require domains to be configured in the WeChat backend whitelist. OSS domains are often not configured, causing 401/403 errors.

**Solution**: Always use server domain proxy for external resources.

### Rules:
1. **Frontend must NOT directly access OSS URLs** — use `/api/proxy/resource?url=<encoded_url>` instead
2. **Backend provides proxy endpoints** — `/api/proxy/resource` for generic resources, `/api/referral/qrcode-image` for QR codes
3. **Deploy script checks domains** — `deploy.sh` runs `check_domain_whitelist()` to warn about unconfigured domains
4. **Allowed proxy domains** — defined in `api.py` `proxy_resource()` function, add new domains there when needed

### When adding new external resources:
1. Add domain to `allowed_domains` in `api.py` `proxy_resource()`
2. Use proxy URL in frontend: `${API_BASE_URL}/api/proxy/resource?url=${encodeURIComponent(ossUrl)}`
3. Run `deploy.sh` to verify domain configuration

### WeChat Mini Program backend configuration:
- **request 域名**: `https://xn--gmq63iba0780e.com`
- **downloadFile 域名**: `https://xn--gmq63iba0780e.com` (for proxy)
- **uploadFile 域名**: `https://xn--gmq63iba0780e.com` (for proxy)
- Do NOT add OSS domains directly — use proxy instead

## Database

- MySQL with PyMySQL, no ORM migrations — use `python init_db.py` or manual SQL
- `member_level` is an ENUM column with values: `'normal'`, `'vip'` (no `'premium'`)
- User type defaults to `'normal'` (enforced by `migrate_user_type_default.py`)

## Environment

Backend requires `.env` file. Copy from `backend/.env.example`. Critical env vars:

- `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
- `DASHSCOPE_API_KEY` (Bailian sketch API)
- `MYSQL_*` (host, user, password, database)
- `JWT_SECRET_KEY`
- `WECHAT_APP_ID` / `WECHAT_APP_SECRET` / `WECHAT_MCH_ID`
- `WECHAT_PAY_CERT_PATH` / `WECHAT_PAY_KEY_PATH` / `WECHAT_PAY_API_V3_KEY`

## Sensitive Files (NEVER commit)

- `backend/.env` — contains API keys
- `backend/certs/wechat/*.pem` — WeChat payment certificates
- `backend/private.key` — private key in miniprogram root
- `backend/static/uploads/`, `backend/static/results/` — user files
