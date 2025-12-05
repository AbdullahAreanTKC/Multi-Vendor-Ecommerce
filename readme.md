# Multi Vendor Ecommerce (Django)

Production-ready multi-vendor ecommerce site with customer, vendor, and staff dashboards, Stripe payments, rate limiting, health checks, and Dockerized deployment.

## Requirements
- Python 3.11+
- Node is not required (pure Django + static assets)
- Docker (optional) for containerized deploy

## Quick Start (local)
```bash
git clone <this-repo>
cd Multi-Vendor-Ecommerce
cp .env.example .env   # adjust secrets, Stripe keys, DB url
chmod +x setup.sh dev.sh migrate.sh start.sh
./setup.sh             # creates .venv, installs deps, migrates, collectstatic
source .venv/bin/activate
./dev.sh               # starts Django at http://127.0.0.1:8001
```

## Running with Docker
```bash
cp .env.example .env        # set STRIPE keys + SECRET_KEY
docker-compose up --build
```
- App: http://localhost:8001
- Postgres, Redis included; healthcheck at `/health/`.

## Environment Variables (.env)
- `SECRET_KEY` (required)
- `DEBUG` (`True`/`False`)
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL` (use `sqlite:///db.sqlite3` for local; set Postgres URL if deploying with an external DB)
- `REDIS_URL` (rate limiting + cache; falls back to locmem)
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`
- `RATE_LIMIT_REQUESTS_PER_MINUTE` (default 200)
- `DJANGO_SUPERUSER_*` (email, password, first/last name, mobile) for auto superuser in scripts

## Operational Scripts
- `./setup.sh` – bootstrap venv, install deps, migrate, collectstatic, optional superuser
- `./dev.sh` – runserver for local dev
- `./start.sh` – production entrypoint (gunicorn, migrations, collectstatic)
- `./migrate.sh` – apply migrations only

## Key Features
- Custom user model with roles (customer/editor/vendor)
- Vendor store + products, cart, checkout, coupon support with discount caps
- Stripe card payments (PaymentIntent)
- Order placement is atomic & stock-safe to prevent overselling
- Admin/staff dashboards secured for staff users
- Rate limiting middleware & cached sessions (Redis-ready)
- Health check endpoint: `/health/`

## Notes
- Set valid Stripe test keys before using payments.
- Default database is SQLite for convenience; Docker/production use Postgres via `DATABASE_URL`.
- Static files served by WhiteNoise; `collectstatic` runs in setup/start scripts.

## Testing
- No automated tests are shipped; after changes run:
```bash
source .venv/bin/activate
python manage.py check
python manage.py test
```