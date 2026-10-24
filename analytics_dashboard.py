import pandas as pd
import streamlit as st


def render_analytics_dashboard(cases):
    """Render analytics from the cases returned by case_store.get_cases()."""
    st.title("Analytics Dashboard")
    st.caption("Explore saved CivicSentinel AI cases. Charts update when cases are saved or statuses change.")

    if not cases:
        st.info("No saved cases yet. Open AI Grievance Analyzer, analyze a complaint, and save it to see analytics.")
        return

    df = pd.DataFrame(cases).copy()

    # Keep the dashboard robust if older database rows lack optional columns.
    for column, default in {
        "department": "Unknown",
        "priority": "Unknown",
        "status": "Open",
        "sentiment": "Unknown",
        "location": "Unknown",
        "created_at": "",
    }.items():
        if column not in df.columns:
            df[column] = default
        df[column] = df[column].fillna(default).astype(str).replace("", default)

    df["created_at_parsed"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["date"] = df["created_at_parsed"].dt.date

    st.subheader("Filter cases")
    f1, f2, f3 = st.columns(3)
    with f1:
        priorities = sorted(df["priority"].unique().tolist())
        selected_priorities = st.multiselect("Priority", priorities, default=priorities)
    with f2:
        departments = sorted(df["department"].unique().tolist())
        selected_departments = st.multiselect("Department", departments, default=departments)
    with f3:
        statuses = sorted(df["status"].unique().tolist())
        selected_statuses = st.multiselect("Case status", statuses, default=statuses)

    filtered = df[
        df["priority"].isin(selected_priorities)
        & df["department"].isin(selected_departments)
        & df["status"].isin(selected_statuses)
    ].copy()

    total = len(filtered)
    high = int(filtered["priority"].str.lower().isin(["high", "critical", "urgent"]).sum())
    open_cases = int(filtered["status"].str.lower().isin(["open", "in progress", "escalated"]).sum())
    resolved = int(filtered["status"].str.lower().eq("resolved").sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Filtered cases", total)
    m2.metric("High / critical", high)
    m3.metric("Open / active", open_cases)
    m4.metric("Resolved", resolved)

    if filtered.empty:
        st.warning("No cases match these filters. Select more options to see analytics.")
        return

    left, right = st.columns(2)
    with left:
        st.subheader("Cases by priority")
        priority_counts = filtered["priority"].value_counts().rename_axis("Priority").to_frame("Cases")
        st.bar_chart(priority_counts)
    with right:
        st.subheader("Cases by status")
        status_counts = filtered["status"].value_counts().rename_axis("Status").to_frame("Cases")
        st.bar_chart(status_counts)

    left, right = st.columns(2)
    with left:
        st.subheader("Department workload")
        dept_counts = filtered["department"].value_counts().rename_axis("Department").to_frame("Cases")
        st.bar_chart(dept_counts)
    with right:
        st.subheader("Reported locations")
        locations = filtered["location"].replace({"": "Unknown"}).value_counts()
        locations = locations[locations.index.str.lower() != "unknown"]
        if locations.empty:
            st.info("Location analytics will appear when cases are saved with a known location.")
        else:
            st.bar_chart(locations.rename_axis("Location").to_frame("Cases"))

    st.subheader("Complaint trend by date")
    dated = filtered.dropna(subset=["date"])
    if dated.empty:
        st.info("No usable timestamps are available yet.")
    else:
        trend = dated.groupby("date").size().rename("Complaints").to_frame()
        st.line_chart(trend)

    st.subheader("Filtered case records")
    display_columns = [
        c for c in ["id", "complaint", "location", "department", "priority",
                    "priority_score", "sentiment", "status", "created_at"]
        if c in filtered.columns
    ]
    st.dataframe(
        filtered[display_columns].sort_values(
            "created_at", ascending=False, na_position="last"
        ),
        use_container_width=True,
        hide_index=True,
    )

    csv = filtered[display_columns].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered analytics data (CSV)",
        data=csv,
        file_name="civicsentinel_analytics.csv",
        mime="text/csv",
    )
