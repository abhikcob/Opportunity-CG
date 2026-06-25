# Opportunity Tracker

Streamlit app to store opportunity details, control dropdown values through admin forms, and show KPI dashboards.

## Architecture

```text
Browser Users
    |
    v
Streamlit App
    |
    +-- Login and role-based access
    +-- Opportunity create/update forms
    +-- Admin forms for dropdowns and users
    +-- KPI dashboard and chart builder
    |
    v
Database
    |
    +-- Local development: SQLite
    +-- Cloud deployment: Neon/Supabase Postgres free tier
```

## Main Modules

- `app.py`: complete Streamlit application.
- `analysis.py`: dashboard, KPI tables, fixed charts, weekly update tracking, and interactive chart builder.
- `requirements.txt`: Python packages needed to run the app.
- `opportunities.db`: local SQLite database created automatically when running locally.

## User Roles

| Role | Access |
|---|---|
| Admin | Manage users, dropdowns, opportunities, dashboard, charts |
| Editor | Add/update opportunities, dashboard, charts |
| Viewer | Dashboard and charts only |

## Admin-Controlled Lists

Admin can manage these from the **Admin** page in the app:

- Status
- Owner
- Priority
- Sector
- Country
- Onshore HC Type
- Firm/Named/Unnamed
- Users and roles
- User password reset

No Python code change is needed for admin changes.

## Opportunity Fields

Users enter:

- Account
- Opportunity
- Country
- Owner
- Probability (%)
- TCV Ke Unweighted
- Status
- Partner(s)
- Priority
- Fixed Price
- Sector
- Firm/Named/Unnamed
- Onshore HC
- Onshore HC Type
- Remarks
- Onshore HC2
- Onshore HC2 Type
- Remarks2

The system generates:

- ID
- Weighted TCV
- Created By
- Created At
- Updated By
- Updated At

Weighted TCV formula:

```text
Weighted TCV = TCV Ke Unweighted * Probability / 100
```

## Dashboard

The dashboard includes:

- Total opportunities
- Total TCV Ke
- Weighted TCV
- Opportunities updated in the last 7 days
- Weighted TCV by status
- Weighted TCV by owner
- Owner-wise last update tracking
- Interactive chart builder

The app creates 100 sample opportunity rows automatically when the opportunity table is empty.

## Run Locally

Open PowerShell:

```powershell
cd "D:\generative AI\Opportunity-CG"
pip install -r requirements.txt
streamlit run app.py
```

Then open the local browser link shown by Streamlit.

## Login

The first run creates only one user:

```text
Email: admin@example.com
Password: admin123
```

Change this password before using the app with real users.

## Add Real Users

1. Login as admin.
2. Open **Admin** from the left menu.
3. Go to **Users**.
4. Add users with role `admin`, `editor`, or `viewer`.
5. Share the app link and temporary password with each user.

## Streamlit Cloud Deployment

1. Push this project to GitHub.
2. Create a free Postgres database in Neon or Supabase.
3. Deploy the GitHub repo to Streamlit Cloud.
4. Add this secret in Streamlit Cloud:

```toml
DATABASE_URL = "postgresql+psycopg2://user:password@host/dbname?sslmode=require"
```

5. Open the Streamlit app link in the browser.
6. Login as admin and create real users.

## Notes

- Local SQLite is good for development and testing.
- For multiple real users on Streamlit Cloud, use Postgres.
- Do not store real company passwords in code.
- Admin changes are made from the app UI, not from Python code.
