# Vision Guard: AI-Powered Smart Surveillance System

Vision Guard is an AI-driven surveillance platform for residential estates. It uses YOLOv8 for real-time person and vehicle detection, automated incident reporting, and a management dashboard for security personnel.

## Key Features

- Real-time person and vehicle detection (YOLOv8)
- Security incident timeline with automatic grouping
- Live monitoring dashboard with dynamic detection counts
- Camera management (RTSP, HTTP, USB webcam)
- Threat scoring and estate map view

## Tech Stack

- **Backend:** Django 6, Django REST Framework
- **AI/CV:** Python 3.10+, YOLOv8 (Ultralytics), OpenCV
- **Database:** SQLite (dev) / MySQL (production via env vars)
- **Frontend:** Django Templates, Bootstrap 5

## Setup

### 1. Prerequisites

- Python 3.10+
- Webcam or RTSP stream URL

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy the example env file and set your secrets:

```bash
cp .env.example .env
```

Edit `.env` and generate strong random values for `DJANGO_SECRET_KEY` and `VISION_GUARD_ENGINE_TOKEN`. **Never commit `.env` to git.**

### 4. YOLO model weights

Create the models directory. Weights are auto-downloaded on first engine run, or place `yolov8n.pt` manually:

```bash
mkdir models
```

### 5. Initialize database

```bash
python manage.py migrate
```

### 6. Create admin account

```bash
python manage.py createsuperuser
```

When prompted, set role to ADMIN via the Django admin after creation, or use the shell:

```bash
python manage.py shell -c "from accounts.models import CustomUser; u=CustomUser.objects.get(username='admin'); u.role='ADMIN'; u.save()"
```

## Running the system

Two processes are required for full functionality:

**Terminal 1 — Web dashboard:**

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000

**Terminal 2 — AI detection engine:**

Add at least one active camera (Stream URL `0` for webcam), then:

```bash
python manage.py run_vanguard
```

## Production notes

- Set `DJANGO_DEBUG=False` in `.env`
- `DJANGO_SECRET_KEY` and `VISION_GUARD_ENGINE_TOKEN` are required when `DEBUG=False`
- Use MySQL by setting `DB_ENGINE=mysql` and related `DB_*` env vars
- Set `USE_REDIS=true` if using Django Channels with Redis

## Pushing to GitHub

```bash
git init
git add .
git status   # verify .env, db.sqlite3, and models/*.pt are NOT staged
git commit -m "Initial commit: Vision Guard surveillance platform"
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```
