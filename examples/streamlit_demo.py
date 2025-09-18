"""Orca Streamlit demo."""

import json

import streamlit as st

from src.orca.engine import decide

st.title("Orca — Open Checkout Agent (Demo)")

amount = st.number_input("Amount", min_value=0.0, value=664.0)
trace_id = st.text_input("Trace ID", "demo-123")

features = {"amount": amount, "trace_id": trace_id}

if st.button("Decide"):
    d = decide(features)
    st.code(json.dumps(d.__dict__, indent=2, default=lambda o: o.__dict__), language="json")
