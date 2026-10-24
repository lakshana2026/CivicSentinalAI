import pandas as pd
import streamlit as st
from analytics_dashboard import render_analytics_dashboard

from ai_engine import analyze_grievance, find_similar_complaints
from case_store import (
    init_db,
    save_case,
    get_cases,
    update_case_status,
)

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="CivicSentinel AI",
    page_icon="🛡️",
    layout="wide",
)

init_db()

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None

if "analysis_complaint" not in st.session_state:
    st.session_state["analysis_complaint"] = ""

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def load_cases():
    """Load the current saved cases from SQLite."""
    return get_cases()


def make_dataframe(cases):
    """Convert saved case records into a DataFrame."""
    return pd.DataFrame(cases)


def metric_count(series, value):
    """Count labels without case sensitivity."""
    return int(
        series.astype(str).str.strip().str.lower().eq(
            value.lower()
        ).sum()
    )


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.title("🛡️ CivicSentinel AI")
st.sidebar.caption("GITCHX · Bihar Police Cyber Hackathon 2026")
st.sidebar.divider()

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Overview",
        "About the Prototype",
        "Grievance Explorer",
        "AI Grievance Analyzer",
        "Case Management",
        "Hotspot & Trends",
        "Analytics Dashboard",
    ],
)

st.sidebar.divider()
st.sidebar.subheader("DATA MODE")
st.sidebar.info("Local SQLite case database")
st.sidebar.caption(
    "Metrics use saved cases. Live social-media feeds "
    "and government integrations are not connected."
)

# --------------------------------------------------
# OVERVIEW - LIVE DATABASE ANALYTICS
# --------------------------------------------------

if page == "Overview":
    st.title("🛡️ CivicSentinel AI Dashboard")
    st.caption("Public grievance intelligence and resolution monitoring")

    try:
        cases = load_cases()
        df = make_dataframe(cases)
    except Exception as error:
        st.error("Could not load saved grievances from the database.")
        st.exception(error)
        st.stop()

    if df.empty:
        st.info(
            "No saved grievances yet. Open AI Grievance Analyzer "
            "to analyse and save your first case."
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Grievances", 0)
        c2.metric("Open Cases", 0)
        c3.metric("Resolved Cases", 0)
        c4.metric("High-Priority Cases", 0)

    else:
        total = len(df)
        open_cases = metric_count(df["status"], "Open")
        resolved = metric_count(df["status"], "Resolved")
        in_progress = metric_count(df["status"], "In Progress")
        escalated = metric_count(df["status"], "Escalated")
        high_priority = metric_count(df["priority"], "High")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Grievances", total)
        c2.metric("Open Cases", open_cases)
        c3.metric("Resolved Cases", resolved)
        c4.metric("High-Priority Cases", high_priority)

        st.divider()

        st.subheader("📊 Case Status Overview")

        status_order = [
            "Open",
            "In Progress",
            "Escalated",
            "Resolved",
        ]
        status_counts = (
            df["status"].fillna("Unknown")
            .value_counts()
            .reindex(status_order, fill_value=0)
        )
        st.bar_chart(status_counts, horizontal=True)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏢 Department Workload")
            department_counts = (
                df["department"]
                .fillna("Unknown")
                .value_counts()
            )
            st.bar_chart(department_counts, horizontal=True)

        with col2:
            st.subheader("🚦 Priority Distribution")
            priority_counts = (
                df["priority"]
                .fillna("Unknown")
                .value_counts()
            )
            st.bar_chart(priority_counts, horizontal=True)
        
        # --------------------------------------------------
        # LOCATION-BASED HOTSPOT ANALYTICS
        # --------------------------------------------------

        st.divider()
        st.subheader("📍 Grievance Hotspots by Area")

        if "location" not in df.columns:
            st.warning(
                "Location data is unavailable. "
                "Check that the database migration has run."
            )
        else:
            locations = (
                df["location"]
                .fillna("Unknown")
                .astype(str)
                .str.strip()
            )

            known_locations = locations[
                (locations != "")
                & (locations.str.lower() != "unknown")
            ]

            if known_locations.empty:
                st.info(
                    "No known locations yet. Enter an area "
                    "when saving new grievances."
                )
            else:
                hotspot_counts = (
                    known_locations
                    .value_counts()
                    .rename_axis("Area")
                    .reset_index(name="Grievances")
                )

                h1, h2 = st.columns(2)

                with h1:
                    st.metric(
                        "Areas Reported",
                        len(hotspot_counts),
                    )

                with h2:
                    st.metric(
                        "Most Reported Area",
                        hotspot_counts.iloc[0]["Area"],
                    )

                st.bar_chart(
                    hotspot_counts.set_index("Area")["Grievances"],
                    horizontal=True,
                )

                st.dataframe(
                    hotspot_counts,
                    use_container_width=True,
                    hide_index=True,
                )

        st.subheader("📌 Workload Summary")
        w1, w2, w3 = st.columns(3)
        w1.metric("In Progress", in_progress)
        w2.metric("Escalated", escalated)
        w3.metric(
            "Resolution Rate",
            f"{resolved / total:.0%}" if total else "0%",
        )

        st.divider()
        st.subheader("🕒 Recent Saved Grievances")

        display_columns = [
            "id",
            "complaint",
            "location",
            "department",
            "priority",
            "status",
            "created_at",
        ]
        display_columns = [
            col for col in display_columns if col in df.columns
        ]

        recent = df[display_columns].head(10).copy()

        if "id" in recent.columns:
            recent = recent.rename(columns={"id": "Case ID"})

        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True,
        )

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Export Saved Cases as CSV",
            data=csv_data,
            file_name="civicsentinel_saved_cases.csv",
            mime="text/csv",
        )

# --------------------------------------------------
# GRIEVANCE EXPLORER - SAVED CASES
# --------------------------------------------------

elif page == "Grievance Explorer":
    st.title("📋 Grievance Explorer")
    st.caption("Search and filter grievances saved in SQLite.")

    try:
        cases = load_cases()
        df = make_dataframe(cases)
    except Exception as error:
        st.error("Could not load saved grievances.")
        st.exception(error)
        st.stop()

    if df.empty:
        st.info(
            "No saved grievances to explore. Analyse and save a case first."
        )
    else:
        col1, col2 = st.columns(2)

        departments = sorted(
            df["department"].dropna().astype(str).unique().tolist()
        )
        priorities = sorted(
            df["priority"].dropna().astype(str).unique().tolist()
        )
        statuses = sorted(
            df["status"].dropna().astype(str).unique().tolist()
        )

        with col1:
            department_filter = st.selectbox(
                "Department",
                ["All"] + departments,
            )
            priority_filter = st.selectbox(
                "Priority",
                ["All"] + priorities,
            )

        with col2:
            status_filter = st.selectbox(
                "Status",
                ["All"] + statuses,
            )
            search_text = st.text_input(
                "Search complaint text",
                placeholder="Enter keywords...",
            )

        filtered = df.copy()

        if department_filter != "All":
            filtered = filtered[
                filtered["department"] == department_filter
            ]

        if priority_filter != "All":
            filtered = filtered[
                filtered["priority"] == priority_filter
            ]

        if status_filter != "All":
            filtered = filtered[
                filtered["status"] == status_filter
            ]

        if search_text.strip():
            filtered = filtered[
                filtered["complaint"].astype(str).str.contains(
                    search_text.strip(),
                    case=False,
                    na=False,
                    regex=False,
                )
            ]

        st.metric("Matching Grievances", len(filtered))

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True,
        )

# --------------------------------------------------
# AI GRIEVANCE ANALYZER
# --------------------------------------------------

elif page == "AI Grievance Analyzer":
    st.title("🧠 AI Grievance Analyzer")
    st.caption(
        "Experimental local classifier. Results need human validation."
    )

    complaint = st.text_area(
        "Enter a public grievance",
        placeholder=(
            "Example: Large potholes are damaging our road. "
            "Please repair the road urgently."
        ),
        height=150,
        max_chars=5000,
        key="grievance_input",
    )
    location = st.text_input(
    "Complaint location / area",
    placeholder="Example: Patna, Kankarbagh",
    max_chars=200,
    key="grievance_location",
)

    if st.button(
        "Analyse grievance",
        type="primary",
        key="analyse_btn",
    ):
        if not complaint.strip():
            st.warning("Please enter a grievance first.")
        else:
            try:
                with st.spinner("Analysing complaint..."):
                    result = analyze_grievance(complaint.strip())

                st.session_state["analysis_result"] = result
                st.session_state["analysis_complaint"] = complaint.strip()

            except Exception as error:
                st.session_state["analysis_result"] = None
                st.error("The analyzer encountered an error.")
                st.exception(error)

    result = st.session_state["analysis_result"]
    analysed_text = st.session_state["analysis_complaint"]

    if result is not None and analysed_text == complaint.strip() and complaint.strip():
        st.success("Analysis complete!")

        c1, c2, c3 = st.columns(3)
        c1.metric("Predicted Department", result["department"])
        c2.metric("Predicted Priority", result["priority"])
        c3.metric("Sentiment", result["sentiment"])

        st.subheader("Analysis Details")
        st.write(
            "Classification confidence indicator:",
            f'{result["classification_confidence"]:.0%}',
        )
        st.write(
            "Sentiment score:",
            f'{result["sentiment_score"]:.3f}',
        )
        st.write(
            "Priority score:",
            f'{result["priority_score"]}/100',
        )

        if result.get("priority_reasons"):
            st.write(
                "Priority indicators:",
                ", ".join(result["priority_reasons"]),
            )

        st.subheader("Similarity Check")

        try:
            existing_cases = load_cases()
            existing_complaints = [
                case["complaint"]
                for case in existing_cases
                if case["complaint"].strip() != complaint.strip()
            ]

            matches = find_similar_complaints(
                complaint.strip(),
                existing_complaints,
                threshold=0.20
            )

            if matches:
                st.dataframe(
                    pd.DataFrame(matches),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No strong text-similarity matches found.")

        except Exception as error:
            st.warning(f"Similarity check unavailable: {error}")

        st.warning(
            "Experimental baseline only. Predictions can be incorrect "
            "and are not calibrated probabilities."
        )

        if st.button(
            "💾 Save grievance as case",
            type="primary",
            key="save_case_btn",
        ):
            try:
                
                case_id = save_case(
                    complaint=complaint.strip(),
                    department=result["department"],
                    priority=result["priority"],
                    priority_score=result["priority_score"],
                    sentiment=result["sentiment"],
                    location=location.strip() or "Unknown",
                )
                st.success(
                    f"Case CS-{case_id:05d} saved successfully!"
                )
            except Exception as error:
                st.error("Could not save the grievance.")
                st.exception(error)

# --------------------------------------------------
# CASE MANAGEMENT
# --------------------------------------------------

elif page == "Case Management":
    st.title("📂 Case Management")

    try:
        cases = load_cases()
    except Exception as error:
        st.error("Could not load the case database.")
        st.exception(error)
        st.stop()

    if not cases:
        st.info("No saved cases yet. Analyse and save a grievance first.")
    else:
        case_df = make_dataframe(cases)
        st.dataframe(
            case_df,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Update Case Status")

        case_ids = [case["id"] for case in cases]
        selected_id = st.selectbox(
            "Select case",
            case_ids,
            format_func=lambda case_id: f"CS-{case_id:05d}",
        )

        new_status = st.selectbox(
            "New status",
            ["Open", "In Progress", "Resolved", "Escalated"],
        )

        if st.button("Update status", type="primary"):
            try:
                updated = update_case_status(selected_id, new_status)

                if updated:
                    st.success(
                        f"Case CS-{selected_id:05d} updated successfully!"
                    )
                    st.rerun()
                else:
                    st.error("Case not found.")
            except Exception as error:
                st.error("Could not update case status.")
                st.exception(error)

# --------------------------------------------------
# ABOUT
# --------------------------------------------------

# --------------------------------------------------
# HOTSPOT & TRENDS
# --------------------------------------------------

elif page == "Hotspot & Trends":
    st.title("📍 Hotspot & Trends")
    st.caption("Area-wise public grievance monitoring")

    cases = get_cases()
    df = make_dataframe(cases)

    if df.empty:
        st.info("No saved grievances available yet.")
    else:
        if "location" not in df.columns:
            st.error(
                "Location column is missing. "
                "Run the database migration first."
            )
        else:
            df["location"] = (
                df["location"]
                .fillna("Unknown")
                .astype(str)
                .str.strip()
            )

            df["location"] = df["location"].replace(
                "", "Unknown"
            )

            known = df[
                df["location"].str.lower() != "unknown"
            ].copy()

            if known.empty:
                st.info(
                    "No known locations yet. Save complaints "
                    "with an area name to generate hotspots."
                )
            else:
                st.subheader("📊 Top Complaint Areas")

                area_counts = (
                    known.groupby("location")
                    .size()
                    .sort_values(ascending=False)
                )

                st.bar_chart(area_counts, horizontal=True)

                st.subheader("🏢 Department by Area")

                department_area = (
                    known.groupby(
                        ["location", "department"]
                    )
                    .size()
                    .reset_index(name="complaints")
                )

                st.dataframe(
                    department_area.sort_values(
                        "complaints", ascending=False
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                st.subheader("🚦 High-Priority Complaints")

                high_priority = known[
                    known["priority"]
                    .astype(str)
                    .str.lower()
                    .eq("high")
                ]

                st.metric(
                    "High-Priority Cases with Known Locations",
                    len(high_priority),
                )

                st.dataframe(
                    high_priority[
                        [
                            "complaint",
                            "location",
                            "department",
                            "priority",
                            "status",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
elif page == "Analytics Dashboard":
    render_analytics_dashboard(load_cases())


elif page == "About the Prototype":
    st.title("ℹ️ About CivicSentinel AI")

    st.write("""
    CivicSentinel AI is a prototype for public grievance intelligence
    and resolution monitoring.

    **Current features**
    - Local baseline grievance classification
    - Sentiment analysis and priority scoring
    - Similarity checks against saved complaints
    - SQLite case storage and status management
    - Live database-based dashboard metrics and charts
    - Grievance filtering and CSV export

    **Current limitations**
    - AI predictions need human validation.
    - No live social-media feeds are connected.
    - No government-system integration is connected.
    - Dashboard data represents saved prototype cases.
    """)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()
st.caption("CivicSentinel AI · GITCHX · Prototype build")
