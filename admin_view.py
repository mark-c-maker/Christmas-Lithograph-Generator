import hmac

import pandas as pd
import streamlit as st

import analytics


def show():
    st.title("Analytics")
    pw = st.text_input("Password", type="password")
    if not pw:
        st.stop()
    try:
        real = st.secrets["admin"]["password"]
    except Exception:
        st.error("No admin password set in Secrets.")
        st.stop()
    if not hmac.compare_digest(pw.encode(), real.encode()):
        st.error("Wrong password.")
        st.stop()

    rows = analytics.fetch_events()
    if not rows:
        st.info("No events yet.")
        st.stop()
    df = pd.DataFrame(rows)
    df["created_at"] = pd.to_datetime(df["created_at"])

    c = st.columns(4)
    c[0].metric("Visits", int((df.event == "visit").sum()))
    c[1].metric("Generate clicks", int((df.event == "generate_click").sum()))
    c[2].metric("Successful generates", int((df.event == "generate_ok").sum()))
    c[3].metric("Downloads", int((df.event == "download").sum()))

    st.subheader("Per day (UTC)")
    daily = (df.assign(day=df.created_at.dt.date)
               .pivot_table(index="day", columns="event", values="session_id",
                            aggfunc="count", fill_value=0))
    st.bar_chart(daily)

    st.subheader("Downloads by file")
    st.dataframe(df[df.event == "download"].detail.value_counts())

    st.subheader("Latest 100 events")
    st.dataframe(df.head(100))
