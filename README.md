# Dextere Haulers Limited

A React + Vite frontend and Django REST API for Dextere Haulers Limited.

## Run locally

Frontend:

```powershell
npm install
npm run dev
```

Backend, from `backend/`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Set `VITE_API_URL` when building the frontend to the backend origin without `/api` (for example, `https://your-api.onrender.com`). The app appends `/api` automatically.

## Deploy to Render

The root `render.yaml` Blueprint defines a free PostgreSQL database, the Django backend, and the React static site. To deploy:

1. Commit and push the changes to the repository's `main` branch.
2. In Render, choose **New > Blueprint**, connect `kevincoder3860/DEXTER-LOGISTICS`, and select `main`.
3. Review the resources from `render.yaml`, then click **Deploy Blueprint**.

The backend uses root directory `backend`, runs `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`, and starts with `gunicorn dextere_backend.wsgi:application --bind 0.0.0.0:$PORT`. The frontend builds with `npm install && npm run build` and publishes `dist`.

The Blueprint generates `SECRET_KEY`, connects `DATABASE_URL` to the database's internal URL, and passes the Render hostnames between the services. The frontend converts `VITE_API_URL` to HTTPS and appends `/api`. The backend adds its `RENDER_EXTERNAL_HOSTNAME` to `ALLOWED_HOSTS` and the frontend hostname to its CORS allowlist.

No secret values need to be committed. To use a custom domain, add its hostname to the backend's `ALLOWED_HOSTS` and its HTTPS origin to `CORS_ALLOWED_ORIGINS` in the Blueprint or Render Environment settings.

After deployment, create a Django superuser from the backend service's Shell:

```sh
python manage.py createsuperuser
```

The database migration runs on each deploy as part of the build command. Back up important data before deploying schema changes.

Render's Free web services can spin down after inactivity, and Free PostgreSQL databases expire after 30 days. Use paid resources and a backup plan for production data.

## Important before going live

The API currently supports transport enquiries and dispatcher management. Verify operational details before launch:

- Official company phone, email, office address and social links.
- Actual passenger routes, timetables, seat inventory and fares.
- Actual cargo services, vehicle fleet and operating areas.
- Shipment data and tracking updates if live shipment tracking is advertised.
- Secure production secrets and dispatcher account credentials.
- M-PESA Daraja integration and payment reconciliation.
- GPS hardware/mobile-driver location integration if live tracking is required.
- Privacy notice, terms, cancellation/refund policy and cookie notice.
- Applicable operator, vehicle, driver, insurance, customs and cross-border authorisations.

Do not advertise live tracking, instant ticketing, payment acceptance or confirmed routes until those services have been implemented and tested.
