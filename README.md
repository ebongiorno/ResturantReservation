# Restaurant Reservation & Waitlist API

CPSC 449 — Web Back-End Engineering | Fall 2026

A Python/Flask REST API for a **single restaurant**. Customers can reserve a specific table for a fixed time slot, cancel reservations, and join a waitlist. Staff can manage tables, reservations, and waitlist entries. This repository contains the back end only; use curl or Postman to send requests.

> **Project status:** Database schema, seed script, and shared MySQL connection have been created and tested locally. The API routes, application factory, and automated test suite are being developed by the team. Commands for starting Flask and running pytest below require those components to be merged first. Update this README with verified instructions before submission.

## Requirements

- Python **3.12+**
- MySQL Server **8.0+** (running locally on port 3306 by default)
- Git
- Dependencies from `requirements.txt`: `Flask`, `Flask-JWT-Extended`, `mysql-connector-python`, `python-dotenv`, `pytest`

## 1. Clone and install dependencies

In **Windows Command Prompt**, from the directory where you want the project:

```cmd
git clone https://github.com/ebongiorno/ResturantReservation.git
cd ResturantReservation
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

In **PowerShell**, activate with `.\.venv\Scripts\Activate.ps1` instead.

If you already cloned the repository, use `git pull origin main` **after the shared changes are merged into `main`**. Save or commit your work first.

## 2. Configure environment variables

Copy the example file to a private local `.env`:

```cmd
copy .env.example .env
```

Fill in the settings using **your own** local MySQL credentials:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=replace_with_your_local_password
DB_NAME=restaurant_db
JWT_SECRET_KEY=replace_with_a_random_secret
```

Generate a secret with `python -c "import secrets; print(secrets.token_hex(32))"` and paste the result as `JWT_SECRET_KEY`. Do **not** commit `.env`, passwords, or JWT secrets. A non-root database account with appropriate permissions is preferable outside local development.

## 3. Create and seed the database

Start MySQL Server before running these commands. From the **repository root**, run:

```cmd
mysql -u root -p -e "SOURCE schema.sql"
mysql -u root -p -e "SOURCE seed.sql"
```

Enter your local MySQL password when prompted. The initial seed data contains **six restaurant tables** and **three fixed slots** (5:00 PM, 6:30 PM, 8:00 PM). Run `seed.sql` once on a fresh database; rerunning the inserts may cause duplicate-key errors.

Verify the tables and sample records:

```cmd
mysql -u root -p -e "USE restaurant_db; SHOW TABLES;"
mysql -u root -p -e "SELECT * FROM restaurant_db.restaurant_tables;"
mysql -u root -p -e "SELECT * FROM restaurant_db.time_slots;"
```

Expected database tables: `users`, `restaurant_tables`, `time_slots`, `reservations`, `waitlist_entries`.

> `schema.sql` creates and selects the `restaurant_db` database. The commands above assume the MySQL CLI is on your Windows PATH. If you use a non-root account, substitute its username for `root` and ensure it has the required permissions.

## 4. Verify the Python database connection

From the repository root with the virtual environment activated:

```cmd
python -c "from app.db import get_db; db = get_db(); print('Connected to:', db.database); db.close()"
```

Expected output:

```text
Connected to: restaurant_db
```

The Flask modules can import `get_db` from `app.db`. **Each caller must close the connection**; for write operations, commit on success or roll back on failure.

## 5. Run the Flask API

**Pending integration:** After `app/__init__.py` provides the Flask application factory `create_app()`, and all blueprints are registered, the intended command from the repository root is:

```cmd
python -m flask --app app:create_app run --debug
```

The default development address is `http://127.0.0.1:5000`. Do not use Flask's development server for production. **Confirm this command after the application factory is merged.**

## 6. API routes and permissions (planned contract)

All routes are prefixed with `/api/v1`. Requests and responses use JSON. Authenticated routes use a JWT access token: `Authorization: Bearer <TOKEN>`.

| Method | Route | Action | Access |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Register customer | Public |
| POST | `/api/v1/auth/login` | Obtain token | Public |
| GET | `/api/v1/tables` | List tables (paginated) | Public |
| POST | `/api/v1/tables` | Create table | Staff |
| GET | `/api/v1/tables/<id>` | Read table | Public |
| PUT | `/api/v1/tables/<id>` | Update table | Staff |
| DELETE | `/api/v1/tables/<id>` | Delete/deactivate table | Staff |
| GET | `/api/v1/reservations` | Own reservations (all for staff) | Authenticated |
| POST | `/api/v1/reservations` | Create booking | Customer |
| GET | `/api/v1/reservations/<id>` | Read booking | Owner/staff |
| PUT | `/api/v1/reservations/<id>` | Change booking | Owner/staff |
| DELETE | `/api/v1/reservations/<id>` | Cancel booking | Owner/staff |
| GET | `/api/v1/waitlist` | List waitlist | Staff |
| POST | `/api/v1/waitlist` | Join waitlist | Customer |
| DELETE | `/api/v1/waitlist/<id>` | Leave waitlist | Owner/staff |

**Conventions:** At least tables and reservations provide full CRUD. Pagination: `GET /api/v1/tables?page=1&per_page=10`. Expected errors include `400` (bad input), `401` (authentication required), `403` (forbidden), `404` (not found), and `409` (booking conflict). The team plans a uniform error object, e.g. `{"error":{"code":"conflict","message":"Table already reserved"}}`.

**Example requests (templates; verify and complete once routes are implemented):**

```cmd
curl http://127.0.0.1:5000/api/v1/tables?page=1^&per_page=10
curl http://127.0.0.1:5000/api/v1/tables/1
curl -X POST http://127.0.0.1:5000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"email\":\"customer@example.com\",\"password\":\"example-password\"}"
```

**Before submission:** Add a verified curl/Postman example for **every endpoint** above, including authenticated `POST`, `PUT`, and `DELETE` calls. Confirm actual request fields and responses with each module owner; do not assume the examples above represent working endpoints yet.

## 7. Test the application

**Pending integration:** Automated tests must use a **separate test database/configuration**, never the development database. After `tests/conftest.py` and the test suite are merged, the intended command is:

```cmd
python -m pytest -v
```

Test coverage should include successful CRUD, input validation, authentication (`401`), ownership/roles (`403`), pagination, waitlist ordering, and concurrent booking attempts where only one succeeds. Do **not** run destructive tests against `restaurant_db`.

## Design and consistency rules

- **One restaurant**, with fixed, non-overlapping slots; customers choose an available specific table.
- **Customer/staff authorization**; customers may manage only their own bookings and waitlist entries, while staff manage restaurant resources. Staff registration must not be publicly self-selectable.
- **Confirmed bookings** for a given table/date/slot cannot overlap. The database schema includes a generated active-booking key and a unique constraint; canceled reservations remain in history and release their slot.
- **Waitlist:** FIFO by `created_at`, then `id`, for a date/slot. Staff-managed promotion is the initial scope; automatic promotion is optional.
- No website, payments, notifications, multi-restaurant setup, Redis, Docker, or microservices are required.

## Repository layout

```text
app/
  __init__.py        # Flask app factory (team integration)
  auth.py            # Authentication and roles
  db.py              # Shared MySQL connection
  tables.py          # Restaurant table endpoints
  reservations.py    # Booking endpoints
  waitlist.py        # Waitlist endpoints
tests/               # pytest tests and test configuration
schema.sql           # MySQL schema
seed.sql             # Sample database rows
requirements.txt     # Python dependencies
.env.example         # Safe configuration template
README.md            # Setup and API documentation
```

The listed application modules and test files are the **planned final layout**; some may not exist yet.

## Team responsibilities

| Member | Workstream |
|---|---|
| 1 | Authentication, JWT login, role/ownership authorization and auth tests |
| 2 | MySQL schema/seed, connection helper, tables CRUD, pagination and tests |
| 3 | Reservations CRUD, availability, transactions and conflict tests |
| 4 | Waitlist, pytest/integration coordination, README integration |

All team members contribute to the report, scaling analysis, testing, Git history, and presentation.

## Submission and presentation

- **November 21, 2026:** Final repository link and tagged release/ZIP; 8–12 page report PDF; individual peer evaluations.
- **December 5, 2026:** Team presentation (10 minutes + 3 minutes of questions). All members speak.

## Final README verification checklist

Before submitting, confirm on a clean machine that: environment setup works; the database builds and seeds successfully; the app starts; each route has a working curl/Postman example; `pytest` uses isolated test data and passes; and the documented sample responses match the real API. Remove all **Pending integration** notes only after those steps are verified.
