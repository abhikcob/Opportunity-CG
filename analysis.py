from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

import pandas as pd
import plotly.express as px
import streamlit as st


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@st.cache_data(ttl=30)
def load_opportunities(_read_df: Callable[[str, dict[str, Any] | None], pd.DataFrame]) -> pd.DataFrame:
    return _read_df("SELECT * FROM opportunities ORDER BY updated_at DESC", None)


def filtered_opportunities(read_df: Callable[[str, dict[str, Any] | None], pd.DataFrame]) -> pd.DataFrame:
    df = load_opportunities(read_df)
    if df.empty:
        return df

    with st.expander("Filters", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        owner = c1.multiselect("Owner", sorted(df["owner"].dropna().unique()))
        status = c2.multiselect("Status", sorted(df["status"].dropna().unique()))
        sector = c3.multiselect("Sector", sorted(df["sector"].dropna().unique()))
        priority = c4.multiselect("Priority", sorted(df["priority"].dropna().unique()))

    if owner:
        df = df[df["owner"].isin(owner)]
    if status:
        df = df[df["status"].isin(status)]
    if sector:
        df = df[df["sector"].isin(sector)]
    if priority:
        df = df[df["priority"].isin(priority)]
    return df


def render_kpi_section(df: pd.DataFrame) -> None:
    st.markdown("### KPI Summary")
    updated_last_7_days = int(
        pd.to_datetime(df["updated_at"], utc=True).ge(pd.Timestamp.utcnow() - pd.Timedelta(days=7)).sum()
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Opportunities", len(df))
    c2.metric("TCV Ke", f"{df['tcv_unweighted'].sum():,.0f}")
    c3.metric("Weighted TCV", f"{df['weighted_tcv'].sum():,.0f}")
    c4.metric("Updated Last 7 Days", updated_last_7_days)


def render_data_tables_section(df: pd.DataFrame) -> None:
    st.markdown("### Data Tables")

    st.markdown("#### Opportunity Details")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("#### Pipeline by Status")
    status_table = (
        df.groupby("status", dropna=False, as_index=False)
        .agg(opportunities=("id", "count"), tcv_ke=("tcv_unweighted", "sum"), weighted_tcv=("weighted_tcv", "sum"))
        .sort_values("weighted_tcv", ascending=False)
    )
    st.dataframe(status_table, use_container_width=True, hide_index=True)

    st.markdown("#### Pipeline by Owner")
    owner_table = (
        df.groupby("owner", dropna=False, as_index=False)
        .agg(opportunities=("id", "count"), tcv_ke=("tcv_unweighted", "sum"), weighted_tcv=("weighted_tcv", "sum"))
        .sort_values("weighted_tcv", ascending=False)
    )
    st.dataframe(owner_table, use_container_width=True, hide_index=True)


def render_fixed_charts_section(df: pd.DataFrame) -> None:
    st.markdown("### Fixed Charts")

    status_df = df.groupby("status", dropna=False, as_index=False)["weighted_tcv"].sum()
    owner_df = df.groupby("owner", dropna=False, as_index=False)["weighted_tcv"].sum()
    sector_df = df.groupby("sector", dropna=False, as_index=False)["weighted_tcv"].sum()
    priority_df = df.groupby("priority", dropna=False, as_index=False)["id"].count().rename(columns={"id": "opportunities"})

    st.markdown("#### Weighted TCV by Status")
    st.plotly_chart(px.bar(status_df, x="status", y="weighted_tcv"), use_container_width=True)

    st.markdown("#### Weighted TCV by Owner")
    st.plotly_chart(px.bar(owner_df, x="owner", y="weighted_tcv"), use_container_width=True)

    st.markdown("#### Weighted TCV by Sector")
    st.plotly_chart(px.pie(sector_df, names="sector", values="weighted_tcv"), use_container_width=True)

    st.markdown("#### Opportunity Count by Priority")
    st.plotly_chart(px.bar(priority_df, x="priority", y="opportunities"), use_container_width=True)


def render_update_tracking_section(df: pd.DataFrame) -> None:
    st.markdown("### Weekly Update Tracking")
    week_cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=7)
    update_df = df.copy()
    update_df["updated_at_dt"] = pd.to_datetime(update_df["updated_at"], utc=True)

    user_status = update_df.groupby("owner", as_index=False).agg(
        last_update=("updated_at_dt", "max"),
        opportunities=("id", "count"),
        stale_opportunities=("updated_at_dt", lambda rows: int(rows.lt(week_cutoff).sum())),
    )
    user_status["updated_last_7_days"] = user_status["last_update"].ge(week_cutoff)

    st.markdown("#### Owner Update Status")
    st.dataframe(user_status, use_container_width=True, hide_index=True)

    stale = update_df[update_df["updated_at_dt"].lt(week_cutoff)].drop(columns=["updated_at_dt"])
    st.markdown("#### Opportunities Not Updated in Last 7 Days")
    st.dataframe(stale, use_container_width=True, hide_index=True)


def dashboard_page(read_df: Callable[[str, dict[str, Any] | None], pd.DataFrame]) -> None:
    st.subheader("Dashboard")
    df = filtered_opportunities(read_df)
    if df.empty:
        st.info("No opportunities yet.")
        return

    render_kpi_section(df)
    render_fixed_charts_section(df)
    render_update_tracking_section(df)
    render_data_tables_section(df)


def chart_builder_page(
    user: dict[str, Any],
    read_df: Callable[[str, dict[str, Any] | None], pd.DataFrame],
    run_sql: Callable[[str, dict[str, Any] | None], None],
) -> None:
    st.subheader("Interactive Chart Builder")
    df = filtered_opportunities(read_df)
    if df.empty:
        st.info("No data available.")
        return

    st.markdown("### Chart Controls")
    numeric_cols = ["tcv_unweighted", "weighted_tcv", "probability", "onshore_hc", "onshore_hc2"]
    dimension_cols = ["account", "country", "owner", "status", "priority", "sector", "firm_named_unnamed"]

    c1, c2, c3 = st.columns(3)
    chart_type = c1.selectbox("Chart Type", ["Bar", "Line", "Pie", "Table"])
    x_axis = c2.selectbox("Group By", dimension_cols)
    y_axis = c3.selectbox("Value", numeric_cols)

    chart_df = df.groupby(x_axis, dropna=False, as_index=False)[y_axis].sum()

    st.markdown("### Chart")
    if chart_type == "Bar":
        st.plotly_chart(px.bar(chart_df, x=x_axis, y=y_axis), use_container_width=True)
    elif chart_type == "Line":
        st.plotly_chart(px.line(chart_df, x=x_axis, y=y_axis, markers=True), use_container_width=True)
    elif chart_type == "Pie":
        st.plotly_chart(px.pie(chart_df, names=x_axis, values=y_axis), use_container_width=True)
    else:
        st.dataframe(chart_df, use_container_width=True, hide_index=True)

    st.markdown("### Chart Data Table")
    st.dataframe(chart_df, use_container_width=True, hide_index=True)

    st.markdown("### Save Chart")
    with st.form("save_chart"):
        name = st.text_input("Chart Name")
        submitted = st.form_submit_button("Save Chart")
    if submitted and name:
        run_sql(
            "INSERT INTO saved_charts (name, owner_email, config, created_at) VALUES (:name, :owner_email, :config, :created_at)",
            {
                "name": name,
                "owner_email": user["email"],
                "config": json.dumps({"chart_type": chart_type, "x_axis": x_axis, "y_axis": y_axis}),
                "created_at": now_iso(),
            },
        )
        st.success("Chart saved.")
