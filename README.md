# SwasthyaSync

SwasthyaSync is a Flask-based web application for **timing-aware nutrition guidance**.  
It combines user lifestyle timings (wake, meals, sleep), profile inputs, and AI analysis (Gemini) to generate:

- personalized diet plans
- meal-photo nutrition analysis
- daily macro tracking with next-meal suggestions

---

## Tech Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Migrate (Alembic)
- Google Gemini API (`google-generativeai`)
- Jinja2 templates + static CSS/JS
- SQLite (default, configurable via environment variable)

---

## Project Structure

```text
SwasthyaSync/
  app.py
  config.py
  extensions.py
  requirements.txt
  blueprints/
    auth/routes.py
    profile/routes.py
    diet/routes.py
    nutrition/routes.py
  models/
    __init__.py
    user_model.py
    lifestyle_model.py
    nutrition_model.py
    diet_model.py
  services/
    gemini_service.py
    prompt_builder.py
    sleep_service.py
    timing_analysis_service.py
    nutrition_service.py
  templates/
  static/
  migrations/
```

---

## Core Modules and Responsibilities

- `app.py`
  - application factory (`create_app`)
  - extension init (`db`, `migrate`)
  - blueprint registration
  - root route (`/`) and health route (`/health`)

- `config.py`
  - environment-based configuration
  - keys for secret, database URL, and Gemini API key

- `blueprints/auth/routes.py`
  - registration, login, logout
  - password hashing and session creation

- `blueprints/profile/routes.py`
  - saves lifestyle timing inputs (`wake`, `breakfast`, `lunch`, `snack`, `dinner`, `sleep`)

- `blueprints/diet/routes.py`
  - collects health/preferences form
  - merges timing from form + stored lifestyle
  - builds prompt payload and calls diet generation
  - persists diet request + response

- `blueprints/nutrition/routes.py`
  - receives meal photo upload
  - calls AI meal analysis
  - stores nutrition log
  - computes day totals and next-meal guidance

- `services/gemini_service.py`
  - Gemini integration for diet generation and meal image analysis
  - **offline fallback mode** when API key is not configured

- `services/nutrition_service.py`
  - daily macro aggregation
  - meal log creation
  - timing feedback + next meal recommendations

---

## Data Model Overview

- `users`
  - account identity + auth data
- `user_lifestyle`
  - one-to-one with user for timing fields
- `nutrition_logs`
  - meal-level macro and AI insights per user
- `diet_requests`
  - prompt/response payload storage for generated plans

Managed with Alembic migrations in `migrations/versions/`.

---

## End-to-End Flow (How the App Works)

1. User lands on `/` and signs up/logs in.
2. User updates lifestyle timings in `/profile/`.
3. For diet planning:
   - user submits form on `/diet/plan`
   - app builds a unified JSON payload (body + medical + preferences + timing + sleep analysis)
   - Gemini service generates a structured diet plan (or local fallback plan)
   - plan is stored and shown on `/diet/plan/detail/<request_id>`
4. For nutrition tracking:
   - user uploads meal image at `/nutrition/tracker`
   - Gemini estimates dish/macros (or fallback estimate)
   - app logs meal, updates daily totals, and shows next-meal guidance

---

## Environment Variables

Set these before running:

- `FLASK_ENV` = `development` or `production`
- `SWASTHYASYNC_SECRET_KEY` = strong random string
- `SWASTHYASYNC_DATABASE_URI` = SQLAlchemy DB URI  
  Example: `sqlite:///swasthyasync.db`
- `SWASTHYASYNC_GEMINI_API_KEY` = your Gemini API key (optional, but needed for live AI responses)

> If `SWASTHYASYNC_GEMINI_API_KEY` is missing, the app still works using deterministic fallback outputs.

---

## Local Setup (Windows PowerShell)

### 1) Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Set environment variables

```powershell
$env:FLASK_ENV="development"
$env:SWASTHYASYNC_SECRET_KEY="replace-with-strong-secret"
$env:SWASTHYASYNC_DATABASE_URI="sqlite:///swasthyasync.db"
$env:SWASTHYASYNC_GEMINI_API_KEY="replace-with-your-gemini-key"
```

### 4) Run migrations

```powershell
flask --app app:create_app db upgrade
```

If migrations are not initialized in a fresh clone, run:

```powershell
flask --app app:create_app db init
flask --app app:create_app db migrate -m "Initial schema"
flask --app app:create_app db upgrade
```

### 5) Start the app

```powershell
python app.py
```

Open: `http://127.0.0.1:5000`

---

## Useful Developer Commands

```powershell
# run app with flask
flask --app app:create_app run --debug

# apply latest migration
flask --app app:create_app db upgrade

# create a new migration after model changes
flask --app app:create_app db migrate -m "describe-change"
```

---

## Notes for New Contributors

- Authentication currently uses server-side session cookies.
- `User.last_login_at` is referenced in auth route but not present in current model/migration schema.
- Some static image references are expected under `static/img/`.
- App is modular by blueprint and service layer, which makes feature extensions straightforward (e.g., premium analytics, wearable integrations, coach dashboard).

---

## GitHub Upload Checklist

Before pushing:

1. Ensure no secrets are committed (especially API keys).
2. Keep `.venv/`, `__pycache__/`, local DB files, and temporary files in `.gitignore`.
3. Confirm migrations are included if schema changed.
4. Verify app boots with:
   - `pip install -r requirements.txt`
   - `flask --app app:create_app db upgrade`
   - `python app.py`

Recommended first commit example:

```text
Initial SwasthyaSync app scaffold with auth, profile, diet intelligence, nutrition tracker, and migrations
```

