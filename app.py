from __future__ import annotations

import hashlib
import hmac
import random
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

import analysis


APP_TITLE = "Opportunity Tracker"
DEFAULT_DB = "sqlite:///opportunities.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def show_save_error(action: str, exc: Exception) -> None:
    st.error(f"Could not {action}. Please check the values and try again.")
    with st.expander("Technical details"):
        st.code(str(exc))


def get_database_url() -> str:
    try:
        database_url = st.secrets.get("DATABASE_URL", DEFAULT_DB)
        return database_url or DEFAULT_DB
    except Exception:
        return DEFAULT_DB


@st.cache_resource
def get_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, future=True)


def is_sqlite() -> bool:
    return get_database_url().startswith("sqlite")


def run_sql(sql: str, params: dict[str, Any] | None = None) -> None:
    with get_engine(get_database_url()).begin() as conn:
        conn.execute(text(sql), params or {})


def read_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    with get_engine(get_database_url()).connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def scalar(sql: str, params: dict[str, Any] | None = None) -> Any:
    with get_engine(get_database_url()).connect() as conn:
        return conn.execute(text(sql), params or {}).scalar()


def create_tables() -> None:
    id_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite() else "SERIAL PRIMARY KEY"

    run_sql(
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id {id_type},
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE
        )
        """
    )
    run_sql(
        f"""
        CREATE TABLE IF NOT EXISTS master_values (
            id {id_type},
            category TEXT NOT NULL,
            value TEXT NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            UNIQUE(category, value)
        )
        """
    )
    run_sql(
        f"""
        CREATE TABLE IF NOT EXISTS opportunities (
            id {id_type},
            account TEXT NOT NULL,
            opportunity TEXT NOT NULL,
            country TEXT,
            owner TEXT NOT NULL,
            probability REAL NOT NULL DEFAULT 0,
            tcv_unweighted REAL NOT NULL DEFAULT 0,
            weighted_tcv REAL NOT NULL DEFAULT 0,
            status TEXT,
            partners TEXT,
            priority TEXT,
            fixed_price BOOLEAN NOT NULL DEFAULT FALSE,
            sector TEXT,
            firm_named_unnamed TEXT,
            onshore_hc REAL,
            onshore_hc_type TEXT,
            remarks TEXT,
            onshore_hc2 REAL,
            onshore_hc2_type TEXT,
            remarks2 TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    run_sql(
        f"""
        CREATE TABLE IF NOT EXISTS saved_charts (
            id {id_type},
            name TEXT NOT NULL,
            owner_email TEXT NOT NULL,
            config TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


def seed_defaults() -> None:
    if not scalar("SELECT COUNT(*) FROM users"):
        run_sql(
            "INSERT INTO users (name, email, password_hash, role, active) VALUES (:name, :email, :password_hash, :role, :active)",
            {
                "name": "Admin",
                "email": "admin@example.com",
                "password_hash": hash_password("admin123"),
                "role": "admin",
                "active": True,
            },
        )

    defaults = {
        "status": ["On hold", "Approved", "Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026", "Q1 2027", "Q2 2027", "Q3 2027", "Q4 2027"],
        "owner": ["Owner 1", "Owner 2", "Owner 3", "Owner 4", "Owner 5", "Owner 6"],
        "priority": ["High", "Medium", "Low"],
        "sector": ["Oil & Gas", "PS", "MT"],
        "country": ["UAE", "KSA", "Qatar", "Oman", "Kuwait", "Bahrain"],
        "hc_type": ["", "Named", "Unnamed"],
        "firm_named_unnamed": ["", "Named", "Unnamed"],
    }
    for category, values in defaults.items():
        for value in values:
            exists = scalar(
                "SELECT COUNT(*) FROM master_values WHERE category = :category AND value = :value",
                {"category": category, "value": value},
            )
            if not exists:
                run_sql(
                    "INSERT INTO master_values (category, value, active) VALUES (:category, :value, :active)",
                    {"category": category, "value": value, "active": True},
                )

    seed_sample_opportunities()


def seed_sample_opportunities() -> None:
    if scalar("SELECT COUNT(*) FROM opportunities"):
        return

    random.seed(42)
    accounts = [
        "ADMO",
        "Al Noor Energy",
        "Gulf Ports",
        "Metro Transit",
        "National Health",
        "Blue Falcon",
        "Royal Services",
        "Emirates Works",
        "Atlas Logistics",
        "Desert Digital",
    ]
    opportunity_names = [
        "Phase 2 Expansion",
        "Next Steps - Phase 3",
        "Cloud Migration",
        "Managed Services Renewal",
        "Data Platform",
        "Cybersecurity Review",
        "ERP Enhancement",
        "AI Automation Pilot",
        "Support Extension",
        "Integration Program",
    ]
    countries = ["UAE", "KSA", "Qatar", "Oman", "Kuwait", "Bahrain"]
    owners = ["Owner 1", "Owner 2", "Owner 3", "Owner 4", "Owner 5", "Owner 6"]
    statuses = ["On hold", "Approved", "Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026", "Q1 2027", "Q2 2027", "Q3 2027", "Q4 2027"]
    priorities = ["High", "Medium", "Low"]
    sectors = ["Oil & Gas", "PS", "MT"]
    named_options = ["", "Named", "Unnamed"]
    base_date = datetime.now(timezone.utc).replace(microsecond=0)

    for item in range(1, 101):
        probability = random.choice([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        tcv_unweighted = random.randint(100, 5000)
        updated_at = (base_date - timedelta(days=random.randint(0, 45))).isoformat()
        created_at = (base_date - timedelta(days=random.randint(46, 180))).isoformat()
        run_sql(
            """
            INSERT INTO opportunities (
                account, opportunity, country, owner, probability, tcv_unweighted, weighted_tcv,
                status, partners, priority, fixed_price, sector, firm_named_unnamed,
                onshore_hc, onshore_hc_type, remarks, onshore_hc2, onshore_hc2_type, remarks2,
                created_by, created_at, updated_by, updated_at
            ) VALUES (
                :account, :opportunity, :country, :owner, :probability, :tcv_unweighted, :weighted_tcv,
                :status, :partners, :priority, :fixed_price, :sector, :firm_named_unnamed,
                :onshore_hc, :onshore_hc_type, :remarks, :onshore_hc2, :onshore_hc2_type, :remarks2,
                :created_by, :created_at, :updated_by, :updated_at
            )
            """,
            {
                "account": random.choice(accounts),
                "opportunity": f"{random.choice(opportunity_names)} {item:03d}",
                "country": random.choice(countries),
                "owner": random.choice(owners),
                "probability": probability,
                "tcv_unweighted": tcv_unweighted,
                "weighted_tcv": tcv_unweighted * probability / 100,
                "status": random.choice(statuses),
                "partners": random.choice(["", "Partner A", "Partner B", "Partner C"]),
                "priority": random.choice(priorities),
                "fixed_price": random.choice([True, False]),
                "sector": random.choice(sectors),
                "firm_named_unnamed": random.choice(named_options),
                "onshore_hc": random.randint(0, 12),
                "onshore_hc_type": random.choice(named_options),
                "remarks": random.choice(["", "Customer discussion ongoing", "Waiting for scope confirmation", "Commercial review in progress"]),
                "onshore_hc2": random.randint(0, 8),
                "onshore_hc2_type": random.choice(named_options),
                "remarks2": random.choice(["", "Follow up next week", "Partner input required", "Pending internal approval"]),
                "created_by": "admin@example.com",
                "created_at": created_at,
                "updated_by": "admin@example.com",
                "updated_at": updated_at,
            },
        )


def init_app() -> None:
    create_tables()
    seed_defaults()


def master_values(category: str, include_blank: bool = False) -> list[str]:
    df = read_df(
        "SELECT value FROM master_values WHERE category = :category AND active = TRUE ORDER BY value",
        {"category": category},
    )
    values = df["value"].tolist()
    return [""] + values if include_blank and "" not in values else values


def current_user() -> dict[str, Any] | None:
    return st.session_state.get("user")


def require_login() -> dict[str, Any]:
    user = current_user()
    if user:
        return user

    st.title(APP_TITLE)
    st.subheader("Sign in")
    with st.form("login"):
        email = st.text_input("Email").strip().lower()
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        df = read_df(
            "SELECT id, name, email, password_hash, role FROM users WHERE lower(email) = :email AND active = TRUE",
            {"email": email},
        )
        if not df.empty and verify_password(password, df.iloc[0]["password_hash"]):
            st.session_state.user = df.iloc[0].drop(labels=["password_hash"]).to_dict()
            st.rerun()
        st.error("Invalid email or password.")

    st.stop()


def can_edit(user: dict[str, Any]) -> bool:
    return user["role"] in {"admin", "editor"}


def can_admin(user: dict[str, Any]) -> bool:
    return user["role"] == "admin"


def opportunity_form(user: dict[str, Any], existing: dict[str, Any] | None = None) -> None:
    is_edit = existing is not None
    title = "Edit Opportunity" if is_edit else "Add Opportunity"
    st.subheader(title)

    with st.form("opportunity_form"):
        c1, c2, c3 = st.columns(3)
        account = c1.text_input("Account", value=existing.get("account", "") if existing else "")
        opportunity = c2.text_input("Opportunity", value=existing.get("opportunity", "") if existing else "")
        country = c3.selectbox("Country", master_values("country"), index=safe_index(master_values("country"), existing.get("country", "") if existing else "UAE"))

        c4, c5, c6 = st.columns(3)
        owners = master_values("owner")
        owner = c4.selectbox("Owner", owners, index=safe_index(owners, existing.get("owner", "") if existing else owners[0]))
        probability = c5.number_input("Probability (%)", min_value=0.0, max_value=100.0, value=float(existing.get("probability", 0) if existing else 0), step=5.0)
        tcv_unweighted = c6.number_input("TCV Ke Unweighted", min_value=0.0, value=float(existing.get("tcv_unweighted", 0) if existing else 0), step=10.0)

        weighted_tcv = tcv_unweighted * probability / 100
        st.metric("Weighted TCV", f"{weighted_tcv:,.2f}")

        c7, c8, c9, c10 = st.columns(4)
        statuses = master_values("status")
        priorities = master_values("priority")
        sectors = master_values("sector")
        firm_options = master_values("firm_named_unnamed", include_blank=True)
        status = c7.selectbox("Status", statuses, index=safe_index(statuses, existing.get("status", "") if existing else statuses[0]))
        priority = c8.selectbox("Priority", priorities, index=safe_index(priorities, existing.get("priority", "") if existing else priorities[0]))
        sector = c9.selectbox("Sector", sectors, index=safe_index(sectors, existing.get("sector", "") if existing else sectors[0]))
        firm_named_unnamed = c10.selectbox("Firm/Named/Unnamed", firm_options, index=safe_index(firm_options, existing.get("firm_named_unnamed", "") if existing else ""))

        c11, c12 = st.columns(2)
        partners = c11.text_input("Partner(s)", value=existing.get("partners", "") if existing else "")
        fixed_price = c12.checkbox("Fixed Price", value=bool(existing.get("fixed_price", False)) if existing else False)

        hc_options = master_values("hc_type", include_blank=True)
        c13, c14, c15 = st.columns(3)
        onshore_hc = c13.number_input("Onshore HC", min_value=0.0, value=float(existing.get("onshore_hc", 0) or 0 if existing else 0), step=1.0)
        onshore_hc_type = c14.selectbox("Onshore HC Type", hc_options, index=safe_index(hc_options, existing.get("onshore_hc_type", "") if existing else ""))
        onshore_hc2 = c15.number_input("Onshore HC2", min_value=0.0, value=float(existing.get("onshore_hc2", 0) or 0 if existing else 0), step=1.0)

        onshore_hc2_type = st.selectbox("Onshore HC2 Type", hc_options, index=safe_index(hc_options, existing.get("onshore_hc2_type", "") if existing else ""))
        remarks = st.text_area("Remarks", value=existing.get("remarks", "") if existing else "")
        remarks2 = st.text_area("Remarks2", value=existing.get("remarks2", "") if existing else "")

        submitted = st.form_submit_button("Save")

    if submitted:
        if not account or not opportunity:
            st.error("Account and Opportunity are required.")
            return
        params = {
            "account": account,
            "opportunity": opportunity,
            "country": country,
            "owner": owner,
            "probability": probability,
            "tcv_unweighted": tcv_unweighted,
            "weighted_tcv": weighted_tcv,
            "status": status,
            "partners": partners,
            "priority": priority,
            "fixed_price": fixed_price,
            "sector": sector,
            "firm_named_unnamed": firm_named_unnamed,
            "onshore_hc": onshore_hc,
            "onshore_hc_type": onshore_hc_type,
            "remarks": remarks,
            "onshore_hc2": onshore_hc2,
            "onshore_hc2_type": onshore_hc2_type,
            "remarks2": remarks2,
            "updated_by": user["email"],
            "updated_at": now_iso(),
        }
        try:
            if is_edit:
                params["id"] = existing["id"]
                run_sql(
                    """
                    UPDATE opportunities
                    SET account=:account, opportunity=:opportunity, country=:country, owner=:owner,
                        probability=:probability, tcv_unweighted=:tcv_unweighted, weighted_tcv=:weighted_tcv,
                        status=:status, partners=:partners, priority=:priority, fixed_price=:fixed_price,
                        sector=:sector, firm_named_unnamed=:firm_named_unnamed, onshore_hc=:onshore_hc,
                        onshore_hc_type=:onshore_hc_type, remarks=:remarks, onshore_hc2=:onshore_hc2,
                        onshore_hc2_type=:onshore_hc2_type, remarks2=:remarks2,
                        updated_by=:updated_by, updated_at=:updated_at
                    WHERE id=:id
                    """,
                    params,
                )
                st.success("Opportunity updated.")
            else:
                params.update({"created_by": user["email"], "created_at": now_iso()})
                run_sql(
                    """
                    INSERT INTO opportunities (
                        account, opportunity, country, owner, probability, tcv_unweighted, weighted_tcv,
                        status, partners, priority, fixed_price, sector, firm_named_unnamed,
                        onshore_hc, onshore_hc_type, remarks, onshore_hc2, onshore_hc2_type, remarks2,
                        created_by, created_at, updated_by, updated_at
                    ) VALUES (
                        :account, :opportunity, :country, :owner, :probability, :tcv_unweighted, :weighted_tcv,
                        :status, :partners, :priority, :fixed_price, :sector, :firm_named_unnamed,
                        :onshore_hc, :onshore_hc_type, :remarks, :onshore_hc2, :onshore_hc2_type, :remarks2,
                        :created_by, :created_at, :updated_by, :updated_at
                    )
                    """,
                    params,
                )
                st.success("Opportunity created.")
            st.cache_data.clear()
        except Exception as exc:
            show_save_error("save opportunity", exc)


def safe_index(values: list[str], value: Any) -> int:
    try:
        return values.index(value)
    except ValueError:
        return 0


def clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def clean_float(value: Any) -> float:
    if value is None or pd.isna(value) or value == "":
        return 0.0
    return float(value)


def clean_bool(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    return bool(value)


def opportunity_row_changed(original: dict[str, Any], edited: dict[str, Any], columns: list[str]) -> bool:
    for column in columns:
        original_value = original.get(column)
        edited_value = edited.get(column)
        if column in {"probability", "tcv_unweighted", "onshore_hc", "onshore_hc2"}:
            if clean_float(original_value) != clean_float(edited_value):
                return True
        elif column == "fixed_price":
            if clean_bool(original_value) != clean_bool(edited_value):
                return True
        elif clean_text(original_value) != clean_text(edited_value):
            return True
    return False


def save_opportunities_from_table(original_df: pd.DataFrame, edited_df: pd.DataFrame, user: dict[str, Any]) -> None:
    editable_columns = [
        "account",
        "opportunity",
        "country",
        "owner",
        "probability",
        "tcv_unweighted",
        "status",
        "partners",
        "priority",
        "fixed_price",
        "sector",
        "firm_named_unnamed",
        "onshore_hc",
        "onshore_hc_type",
        "remarks",
        "onshore_hc2",
        "onshore_hc2_type",
        "remarks2",
    ]
    original_by_id = {}
    if not original_df.empty:
        original_by_id = {int(row["id"]): row for row in original_df.to_dict("records") if not pd.isna(row["id"])}

    inserted = 0
    updated = 0
    for row in edited_df.to_dict("records"):
        account = clean_text(row.get("account"))
        opportunity = clean_text(row.get("opportunity"))
        owner = clean_text(row.get("owner"))

        is_blank_new_row = not account and not opportunity and not owner and pd.isna(row.get("id"))
        if is_blank_new_row:
            continue

        if not account or not opportunity or not owner:
            st.error("Account, Opportunity, and Owner are required for every saved row.")
            return

        probability = max(0.0, min(100.0, clean_float(row.get("probability"))))
        tcv_unweighted = clean_float(row.get("tcv_unweighted"))
        params = {
            "account": account,
            "opportunity": opportunity,
            "country": clean_text(row.get("country")),
            "owner": owner,
            "probability": probability,
            "tcv_unweighted": tcv_unweighted,
            "weighted_tcv": tcv_unweighted * probability / 100,
            "status": clean_text(row.get("status")),
            "partners": clean_text(row.get("partners")),
            "priority": clean_text(row.get("priority")),
            "fixed_price": clean_bool(row.get("fixed_price")),
            "sector": clean_text(row.get("sector")),
            "firm_named_unnamed": clean_text(row.get("firm_named_unnamed")),
            "onshore_hc": clean_float(row.get("onshore_hc")),
            "onshore_hc_type": clean_text(row.get("onshore_hc_type")),
            "remarks": clean_text(row.get("remarks")),
            "onshore_hc2": clean_float(row.get("onshore_hc2")),
            "onshore_hc2_type": clean_text(row.get("onshore_hc2_type")),
            "remarks2": clean_text(row.get("remarks2")),
            "updated_by": user["email"],
            "updated_at": now_iso(),
        }

        row_id = row.get("id")
        if row_id is None or pd.isna(row_id):
            params.update({"created_by": user["email"], "created_at": now_iso()})
            run_sql(
                """
                INSERT INTO opportunities (
                    account, opportunity, country, owner, probability, tcv_unweighted, weighted_tcv,
                    status, partners, priority, fixed_price, sector, firm_named_unnamed,
                    onshore_hc, onshore_hc_type, remarks, onshore_hc2, onshore_hc2_type, remarks2,
                    created_by, created_at, updated_by, updated_at
                ) VALUES (
                    :account, :opportunity, :country, :owner, :probability, :tcv_unweighted, :weighted_tcv,
                    :status, :partners, :priority, :fixed_price, :sector, :firm_named_unnamed,
                    :onshore_hc, :onshore_hc_type, :remarks, :onshore_hc2, :onshore_hc2_type, :remarks2,
                    :created_by, :created_at, :updated_by, :updated_at
                )
                """,
                params,
            )
            inserted += 1
            continue

        existing_id = int(row_id)
        if existing_id not in original_by_id:
            continue
        if not opportunity_row_changed(original_by_id[existing_id], row, editable_columns):
            continue

        params["id"] = existing_id
        run_sql(
            """
            UPDATE opportunities
            SET account=:account, opportunity=:opportunity, country=:country, owner=:owner,
                probability=:probability, tcv_unweighted=:tcv_unweighted, weighted_tcv=:weighted_tcv,
                status=:status, partners=:partners, priority=:priority, fixed_price=:fixed_price,
                sector=:sector, firm_named_unnamed=:firm_named_unnamed, onshore_hc=:onshore_hc,
                onshore_hc_type=:onshore_hc_type, remarks=:remarks, onshore_hc2=:onshore_hc2,
                onshore_hc2_type=:onshore_hc2_type, remarks2=:remarks2,
                updated_by=:updated_by, updated_at=:updated_at
            WHERE id=:id
            """,
            params,
        )
        updated += 1

    st.cache_data.clear()
    st.success(f"Saved table changes. Inserted: {inserted}. Updated: {updated}.")


def opportunities_page(user: dict[str, Any]) -> None:
    st.subheader("Opportunities")
    df = analysis.filtered_opportunities(read_df)
    table_columns = [
        "id",
        "account",
        "opportunity",
        "country",
        "owner",
        "probability",
        "tcv_unweighted",
        "weighted_tcv",
        "status",
        "partners",
        "priority",
        "fixed_price",
        "sector",
        "firm_named_unnamed",
        "onshore_hc",
        "onshore_hc_type",
        "remarks",
        "onshore_hc2",
        "onshore_hc2_type",
        "remarks2",
        "created_by",
        "created_at",
        "updated_by",
        "updated_at",
    ]
    if df.empty:
        df = pd.DataFrame(columns=table_columns)
    else:
        df = df.reindex(columns=table_columns)

    if not can_edit(user):
        st.dataframe(df, use_container_width=True, hide_index=True)
        return

    st.caption("Edit existing records directly in the table. Use the blank row at the bottom to insert new records.")
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        disabled=["id", "weighted_tcv", "created_by", "created_at", "updated_by", "updated_at"],
        column_order=table_columns,
        column_config={
            "id": st.column_config.NumberColumn("ID"),
            "account": st.column_config.TextColumn("Account", required=True),
            "opportunity": st.column_config.TextColumn("Opportunity", required=True),
            "country": st.column_config.SelectboxColumn("Country", options=master_values("country")),
            "owner": st.column_config.SelectboxColumn("Owner", options=master_values("owner"), required=True),
            "probability": st.column_config.NumberColumn("Probability (%)", min_value=0, max_value=100, step=5),
            "tcv_unweighted": st.column_config.NumberColumn("TCV Ke Unweighted", min_value=0, step=10),
            "weighted_tcv": st.column_config.NumberColumn("Weighted TCV"),
            "status": st.column_config.SelectboxColumn("Status", options=master_values("status")),
            "partners": st.column_config.TextColumn("Partner(s)"),
            "priority": st.column_config.SelectboxColumn("Priority", options=master_values("priority")),
            "fixed_price": st.column_config.CheckboxColumn("Fixed Price"),
            "sector": st.column_config.SelectboxColumn("Sector", options=master_values("sector")),
            "firm_named_unnamed": st.column_config.SelectboxColumn("Firm/Named/Unnamed", options=master_values("firm_named_unnamed", include_blank=True)),
            "onshore_hc": st.column_config.NumberColumn("Onshore HC", min_value=0, step=1),
            "onshore_hc_type": st.column_config.SelectboxColumn("Onshore HC Type", options=master_values("hc_type", include_blank=True)),
            "remarks": st.column_config.TextColumn("Remarks"),
            "onshore_hc2": st.column_config.NumberColumn("Onshore HC2", min_value=0, step=1),
            "onshore_hc2_type": st.column_config.SelectboxColumn("Onshore HC2 Type", options=master_values("hc_type", include_blank=True)),
            "remarks2": st.column_config.TextColumn("Remarks2"),
        },
    )

    if st.button("Save Table Changes", type="primary"):
        try:
            save_opportunities_from_table(df, edited_df, user)
            st.rerun()
        except Exception as exc:
            show_save_error("save table changes", exc)


def admin_page() -> None:
    st.subheader("Admin")
    tab1, tab2 = st.tabs(["Master Lists", "Users"])

    with tab1:
        list_labels = {
            "status": "Status",
            "owner": "Owner",
            "priority": "Priority",
            "sector": "Sector",
            "country": "Country",
            "hc_type": "Onshore HC Type",
            "firm_named_unnamed": "Firm/Named/Unnamed",
        }
        label_to_category = {label: category for category, label in list_labels.items()}
        selected_label = st.selectbox("Choose list to manage", list(label_to_category))
        category = label_to_category[selected_label]

        df = read_df(
            "SELECT id, value, active FROM master_values WHERE category = :category ORDER BY active DESC, value",
            {"category": category},
        )
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=["id"],
            column_config={
                "id": st.column_config.NumberColumn("ID"),
                "value": st.column_config.TextColumn("Dropdown Value", required=True),
                "active": st.column_config.CheckboxColumn("Available for Users"),
            },
        )

        c1, c2 = st.columns([1, 2])
        if c1.button("Save Changes", type="primary"):
            try:
                for row in edited_df.to_dict("records"):
                    if not str(row["value"]).strip():
                        st.error("Dropdown values cannot be blank.")
                        return
                    run_sql(
                        "UPDATE master_values SET value = :value, active = :active WHERE id = :id",
                        {"id": int(row["id"]), "value": str(row["value"]).strip(), "active": bool(row["active"])},
                    )
                st.cache_data.clear()
                st.success("List updated.")
                st.rerun()
            except Exception as exc:
                show_save_error("save list changes", exc)

        with st.form("add_master", clear_on_submit=True):
            value = st.text_input(f"Add new {selected_label}")
            submitted = st.form_submit_button("Add")
        if submitted and value:
            try:
                run_sql(
                    "INSERT INTO master_values (category, value, active) VALUES (:category, :value, :active)",
                    {"category": category, "value": value.strip(), "active": True},
                )
                st.cache_data.clear()
                st.success("Value added.")
                st.rerun()
            except Exception as exc:
                st.error("This value may already exist, or it could not be saved.")
                with st.expander("Technical details"):
                    st.code(str(exc))

    with tab2:
        st.markdown("### Existing Users")
        users = read_df("SELECT id, name, email, role, active FROM users ORDER BY name")
        edited_users = st.data_editor(
            users,
            use_container_width=True,
            hide_index=True,
            disabled=["id", "email"],
            column_config={
                "id": st.column_config.NumberColumn("ID"),
                "name": st.column_config.TextColumn("Name", required=True),
                "email": st.column_config.TextColumn("Email"),
                "role": st.column_config.SelectboxColumn("Role", options=["viewer", "editor", "admin"], required=True),
                "active": st.column_config.CheckboxColumn("Can Log In"),
            },
        )

        if st.button("Save User Changes", type="primary"):
            try:
                for row in edited_users.to_dict("records"):
                    if not str(row["name"]).strip():
                        st.error("User name cannot be blank.")
                        return
                    run_sql(
                        "UPDATE users SET name = :name, role = :role, active = :active WHERE id = :id",
                        {"id": int(row["id"]), "name": str(row["name"]).strip(), "role": row["role"], "active": bool(row["active"])},
                    )
                st.success("Users updated.")
                st.rerun()
            except Exception as exc:
                show_save_error("save user changes", exc)

        st.markdown("### Add New User")
        with st.form("add_user", clear_on_submit=True):
            name = st.text_input("Name")
            email = st.text_input("Email")
            role = st.selectbox("Role", ["viewer", "editor", "admin"])
            password = st.text_input("Temporary Password", type="password")
            submitted = st.form_submit_button("Add User")
        if submitted and name and email and password:
            try:
                existing_user_count = scalar(
                    "SELECT COUNT(*) FROM users WHERE lower(email) = :email",
                    {"email": email.strip().lower()},
                )
                if existing_user_count:
                    st.error("This email already exists. Use Reset User Password below instead of adding the same user again.")
                else:
                    run_sql(
                        "INSERT INTO users (name, email, password_hash, role, active) VALUES (:name, :email, :password_hash, :role, :active)",
                        {
                            "name": name.strip(),
                            "email": email.strip().lower(),
                            "password_hash": hash_password(password),
                            "role": role,
                            "active": True,
                        },
                    )
                    st.success("User added.")
                    st.rerun()
            except Exception as exc:
                show_save_error("add user", exc)
        elif submitted:
            st.error("Name, email, and temporary password are required.")

        st.markdown("### Reset User Password")
        with st.form("reset_password", clear_on_submit=True):
            active_users = read_df("SELECT email FROM users ORDER BY email")
            reset_email = st.selectbox("User", active_users["email"].tolist())
            new_password = st.text_input("New Temporary Password", type="password")
            reset_submitted = st.form_submit_button("Reset Password")
        if reset_submitted:
            if not reset_email or not new_password:
                st.error("Select a user and enter a new temporary password.")
            else:
                try:
                    run_sql(
                        "UPDATE users SET password_hash = :password_hash WHERE email = :email",
                        {"email": reset_email, "password_hash": hash_password(new_password)},
                    )
                    st.success("Password updated. Share the new temporary password with the user.")
                except Exception as exc:
                    show_save_error("reset password", exc)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    try:
        init_app()
    except Exception as exc:
        st.error("The app could not connect to or initialize the database.")
        st.info("If this is on Streamlit Cloud, check the DATABASE_URL secret or remove it to use temporary SQLite testing.")
        with st.expander("Technical details"):
            st.code(str(exc))
        st.stop()

    user = require_login()

    with st.sidebar:
        st.title(APP_TITLE)
        st.caption(f"{user['name']} | {user['role']}")
        pages = ["Dashboard", "Opportunities", "Chart Builder"]
        if can_admin(user):
            pages.append("Admin")
        page = st.radio("Navigation", pages)
        if st.button("Sign out"):
            st.session_state.clear()
            st.rerun()

    if page == "Dashboard":
        analysis.dashboard_page(read_df)
    elif page == "Opportunities":
        opportunities_page(user)
    elif page == "Chart Builder":
        analysis.chart_builder_page(user, read_df, run_sql)
    elif page == "Admin":
        admin_page()


if __name__ == "__main__":
    main()
