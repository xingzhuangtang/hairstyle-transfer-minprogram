# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **WeChat Mini Program + Flask backend** application for hairstyle transfer (发型迁移). The app allows users to upload photos, apply hairstyle changes using AI (Alibaba Cloud APIs), and manage virtual currency (hair credits) for service consumption.

## Commands

### Backend (Python/Flask)

```bash
# Install dependencies
cd backend && pip install -r requirements.txt

# Initialize database
python init_db.py

# Run development server
python app.py

# Run tests
python test_payment_gateways.py
python test_virtual_currency.py
python test_performance.py
python test_ai_services.py
```

### Frontend (WeChat Mini Program)

- Open `miniprogram/` in **WeChat DevTools**
- No build step required - uses native mini program format
- API base URL: `miniprogram/utils/constants.js`

## Architecture

### Backend Structure (`backend/`)

| Category | Files |
|----------|-------|
| **Entry Points** | `app.py` (main), `api.py` (API blueprints) |
| **Services** | `auth.py`, `payment_service.py`, `hair_service.py`, `member_service.py`, `sms_service.py`, `account_service.py` |
| **AI/ML** | `aliyun_hair_transfer_fixed.py`, `hair_segmentation.py`, `sketch_converter.py`, `bailian_sketch_converter.py` |
| **Payment** | `wechat_pay.py`, `alipay_client.py`, `unionpay.py` |
| **Models** | `models.py` (SQLAlchemy ORM) |
| **Config** | `config.py`, `.env` |
| **Utilities** | `logging_config.py`, `scheduler.py`, `system_monitor.py` |
| **Database** | `init_db.py`, `db_backup.py`, `db_restore.py` |

**Key Services:**
- `HairService` - Manages hair credit consumption for operations
- `AuthService` - WeChat login, phone SMS login, JWT tokens
- `PaymentService` - Handles recharge orders (WeChat/Alipay/UnionPay)
- `MemberService` - VIP membership management

### Frontend Structure (`miniprogram/`)

**Pages:**
- `index` - Home page (hairstyle transfer main UI)
- `login` - WeChat/phone login
- `profile` - User profile/settings
- `balance` - Virtual currency balance
- `member` - VIP membership purchase
- `history` - Operation history
- `consumption` - Consumption records

**Utilities (`utils/`):**
- `request.js` - HTTP client with auto token handling
- `storage.js` - Local storage wrapper
- `constants.js` - API base URL
- `auth.js` - Auth helpers

**API Integration:**
- All requests go through `utils/request.js` which auto-attaches JWT tokens
- 401 responses trigger automatic logout and redirect to login page

## Database Schema

**Core Tables:**
- `users` - User accounts (openid, phone, balance, membership)
- `recharge_records` - Virtual currency recharge orders
- `member_orders` - VIP membership purchases
- `consumption_records` - Hair credit consumption logs
- `history_records` - Hairstyle transfer operation history
- `member_reminders` - Membership expiration notifications

## Environment Configuration

Backend requires `.env` file with:

```bash
# Alibaba Cloud
ALIBABA_CLOUD_ACCESS_KEY_ID=
ALIBABA_CLOUD_ACCESS_KEY_SECRET=
DASHSCOPE_API_KEY=

# Database
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=hairstyle_transfer

# JWT
JWT_SECRET_KEY=

# WeChat
WECHAT_APP_ID=
WECHAT_APP_SECRET=
WECHAT_MCH_ID=
WECHAT_API_KEY=

# Alipay
ALIPAY_APP_ID=
ALIPAY_PRIVATE_KEY=
ALIPAY_PUBLIC_KEY=
```

## Pricing Rules (from `config.py`)

**Virtual Currency:** 10 hair credits ≈ 1 CNY

**Operation Costs (normal/premium):**
- Hair segmentation: 4 / 2 credits
- Face merge: 4 / 2 credits
- Sketch conversion: 84 / 42 credits
- Combined (transfer + sketch): 88 / 46 credits
