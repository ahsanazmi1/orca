"""Streamlit demo for Orca Core decision engine."""

from typing import Any
from unittest.mock import patch

import orjson
import streamlit as st

from orca_core.engine import evaluate_rules
from orca_core.models import DecisionRequest

st.set_page_config(page_title="Orca Core Decision Engine", page_icon="🐋", layout="wide")

st.title("🐋 Orca Core Decision Engine")
st.markdown("Interactive demo for the decision engine")

# Sidebar for input
st.sidebar.header("Decision Request")

# Mode toggle
st.sidebar.subheader("Mode")
use_ml = st.sidebar.toggle("Rules + ML", value=True, help="Enable ML risk prediction")
if not use_ml:
    st.sidebar.info("Rules only mode - ML risk prediction disabled")

# Basic inputs
cart_total = st.sidebar.number_input(
    "Cart Total ($)",
    min_value=0.01,
    max_value=10000.0,
    value=250.0,
    step=0.01,
    help="Total amount in the shopping cart",
)

currency = st.sidebar.selectbox("Currency", ["USD", "EUR", "GBP", "CAD", "AUD"], index=0)

# Features section
st.sidebar.subheader("Features")
velocity_24h = st.sidebar.number_input(
    "Velocity (24h)",
    min_value=0.0,
    max_value=10.0,
    value=1.0,
    step=0.1,
    help="Number of transactions in last 24 hours",
)

customer_age = st.sidebar.number_input(
    "Customer Age", min_value=18, max_value=100, value=30, help="Customer age in years"
)

# Context section
st.sidebar.subheader("Context")
ip_country = st.sidebar.selectbox(
    "IP Country", ["US", "CA", "GB", "DE", "FR", "AU", "JP", "Other"], index=0
)

device_type = st.sidebar.selectbox("Device Type", ["desktop", "mobile", "tablet"], index=0)

previous_orders = st.sidebar.number_input(
    "Previous Orders", min_value=0, max_value=100, value=0, help="Number of previous orders"
)

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("Request JSON")

    # Build request data
    request_data: dict[str, Any] = {
        "cart_total": cart_total,
        "currency": currency,
        "features": {"velocity_24h": velocity_24h, "customer_age": customer_age},
        "context": {
            "ip_country": ip_country,
            "device_type": device_type,
            "previous_orders": previous_orders,
        },
    }

    # Display formatted JSON
    st.json(request_data)

with col2:
    st.header("Decision Response")

    # Evaluate decision
    try:
        request = DecisionRequest(**request_data)

        # Apply ML toggle
        if use_ml:
            response = evaluate_rules(request)
        else:
            # Rules only mode - disable ML by patching predict_risk to return 0.0
            with (
                patch("orca_core.engine.predict_risk", return_value=0.0),
                patch("orca_core.rules.high_risk.predict_risk", return_value=0.0),
            ):
                response = evaluate_rules(request)

        # Display decision result
        decision_color = {"APPROVE": "🟢", "REVIEW": "🟡", "DECLINE": "🔴"}.get(
            response.decision, "⚪"
        )

        st.markdown(f"### {decision_color} Decision: {response.decision}")

        # Display risk score if ML is enabled
        if use_ml and "risk_score" in response.meta:
            risk_score = response.meta["risk_score"]
            risk_color = "🔴" if risk_score > 0.8 else "🟡" if risk_score > 0.5 else "🟢"
            st.metric("Risk Score", f"{risk_score:.3f}", help=f"{risk_color} ML predicted risk")
        elif not use_ml:
            st.info("ML risk prediction disabled")

        # Display reasons
        if response.reasons:
            st.subheader("Reasons")
            for reason in response.reasons:
                st.write(f"• {reason}")

        # Display actions
        if response.actions:
            st.subheader("Recommended Actions")
            for action in response.actions:
                st.write(f"• {action}")

        # Display metadata
        if response.meta:
            st.subheader("Metadata")
            st.json(response.meta)

    except Exception as e:
        st.error(f"Error evaluating decision: {e}")

# Response JSON section
st.header("Response JSON")
try:
    request = DecisionRequest(**request_data)

    # Apply ML toggle
    if use_ml:
        response = evaluate_rules(request)
    else:
        # Rules only mode - disable ML by patching predict_risk to return 0.0
        with (
            patch("orca_core.engine.predict_risk", return_value=0.0),
            patch("orca_core.rules.high_risk.predict_risk", return_value=0.0),
        ):
            response = evaluate_rules(request)

    # Convert to dict and display
    response_dict = response.model_dump()
    st.json(response_dict)

    # Show compact JSON
    st.subheader("Compact JSON")
    compact_json = orjson.dumps(
        response_dict, option=orjson.OPT_COMPACT | orjson.OPT_SORT_KEYS
    ).decode()
    st.code(compact_json, language="json")

except Exception as e:
    st.error(f"Error generating response: {e}")

# Footer
st.markdown("---")
st.markdown(
    "**Orca Core Decision Engine** - A production-ready decision engine for e-commerce applications"
)
