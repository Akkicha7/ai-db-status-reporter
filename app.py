import streamlit as st
from metrics_collector import collect
from analyzer import analyze
from ai_report_generator import generate
from db_config_loader import get_all_db_configs

st.set_page_config(page_title="DB Status Reporter", layout="wide")

st.title("📊 AI Database Status Reporter")

# 🔹 Load DB configs
configs = get_all_db_configs()

if not configs:
    st.error("No databases configured. Please add DB configs in PostgreSQL.")
    st.stop()

# 🔹 Mode selection
mode = st.radio("Choose Mode", ["Single Database", "All Databases"])

# 🔹 SINGLE DB MODE
if mode == "Single Database":

    selected_db = st.selectbox(
        "Select Database",
        configs,
        format_func=lambda x: x["name"]
    )

    if st.button("Run Status Check 🚀"):

        st.info(f"Collecting metrics from {selected_db['name']}...")

        metrics = collect(selected_db)   # ✅ FIXED
        st.success("Metrics collected")

        st.subheader("📌 Metrics")
        st.json(metrics)

        st.info("Analyzing database...")
        analysis = analyze(metrics)

        st.subheader("📊 Status Score")
        st.metric("Status Score", f"{analysis.health_score}/100")

        st.subheader("⚠️ Issues")
        if analysis.issues:
            for issue in analysis.issues:
                st.warning(issue.message)
        else:
            st.success("No issues detected")

        st.info("Generating report...")
        report = generate(analysis)

        st.subheader("📝 AI Report")
        st.markdown(report, unsafe_allow_html=True)


# 🔹 ALL DATABASE MODE (SMART IMPROVEMENT 🔥)
else:

    if st.button("Run Status Check for ALL DBs 🚀"):

        for db in configs:

            st.divider()
            st.header(f"📂 {db['name']}")

            st.info("Collecting metrics...")

            try:
                metrics = collect(db)   # ✅ LOOP MODE
                st.success("Metrics collected")

                st.subheader("📌 Metrics")
                st.json(metrics)

                analysis = analyze(metrics)

                st.subheader("📊 Status Score")
                st.metric("Status Score", f"{analysis.health_score}/100")

                st.subheader("⚠️ Issues")
                if analysis.issues:
                    for issue in analysis.issues:
                        st.warning(issue.message)
                else:
                    st.success("No issues detected")

                report = generate(analysis)

                st.subheader("📝 AI Report")
                st.markdown(report, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Failed for {db['name']}: {e}")