"""Streamlit demo for Orca Core decision engine."""

import glob
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import streamlit as st
from orca_core.core.explainer import explain_decision
from orca_core.engine import evaluate_rules
from orca_core.models import DecisionRequest

st.set_page_config(page_title="Orca Core Decision Engine", page_icon="🐋", layout="wide")

st.title("🐋 Orca Core Decision Engine")
st.markdown("Interactive demo for the decision engine")

# Sidebar for input
st.sidebar.header("Decision Request")

# Preset selection
st.sidebar.subheader("Preset")
preset_files = []
fixtures_dir = Path("fixtures/requests")
if fixtures_dir.exists():
    preset_files = glob.glob(str(fixtures_dir / "*.json"))
    preset_files = [os.path.basename(f) for f in preset_files]

if preset_files:
    preset_options = ["Custom"] + sorted(preset_files)
    selected_preset = st.sidebar.selectbox("Choose a preset", preset_options, index=0)
else:
    selected_preset = "Custom"
    st.sidebar.info("No fixture files found in fixtures/requests/")

# Load preset data if selected
preset_data = None
if selected_preset != "Custom" and preset_files:
    preset_path = fixtures_dir / selected_preset
    try:
        with open(preset_path) as f:
            preset_data = json.load(f)
    except Exception as e:
        st.sidebar.error(f"Error loading preset: {e}")
        preset_data = None

# Basic inputs
st.sidebar.subheader("Basic Information")
cart_total = st.sidebar.number_input(
    "Cart Total ($)",
    min_value=0.01,
    max_value=10000.0,
    value=preset_data.get("cart_total", 250.0) if preset_data else 250.0,
    step=0.01,
    help="Total amount in the shopping cart",
)

currency = st.sidebar.selectbox(
    "Currency",
    ["USD", "EUR", "GBP", "CAD", "AUD"],
    index=(
        0
        if not preset_data
        else ["USD", "EUR", "GBP", "CAD", "AUD"].index(preset_data.get("currency", "USD"))
    ),
)

# Features section
st.sidebar.subheader("Features")
features = preset_data.get("features", {}) if preset_data else {}
velocity_24h = st.sidebar.number_input(
    "Velocity (24h)",
    min_value=0.0,
    max_value=10.0,
    value=float(features.get("velocity_24h", 1.0)),
    step=0.1,
    help="Number of transactions in last 24 hours",
)

high_ip_distance = st.sidebar.checkbox(
    "High IP Distance",
    value=features.get("high_ip_distance", False),
    help="Transaction originates from high-risk IP distance",
)

# Context section
st.sidebar.subheader("Context")
context = preset_data.get("context", {}) if preset_data else {}

# Location information
location_ip_country = st.sidebar.selectbox(
    "IP Country",
    ["US", "CA", "GB", "DE", "FR", "AU", "JP", "Other"],
    index=(
        0
        if not context
        else ["US", "CA", "GB", "DE", "FR", "AU", "JP", "Other"].index(
            context.get("location_ip_country", "US")
        )
    ),
)

billing_country = st.sidebar.selectbox(
    "Billing Country",
    ["US", "CA", "GB", "DE", "FR", "AU", "JP", "Other"],
    index=(
        0
        if not context
        else ["US", "CA", "GB", "DE", "FR", "AU", "JP", "Other"].index(
            context.get("billing_country", "US")
        )
    ),
)

# Customer information
customer = context.get("customer", {}) if context else {}
loyalty_tier = st.sidebar.selectbox(
    "Loyalty Tier",
    ["NONE", "SILVER", "GOLD", "PLATINUM"],
    index=(
        0
        if not customer
        else ["NONE", "SILVER", "GOLD", "PLATINUM"].index(customer.get("loyalty_tier", "NONE"))
    ),
)

chargebacks_12m = st.sidebar.number_input(
    "Chargebacks (12m)",
    min_value=0,
    max_value=10,
    value=customer.get("chargebacks_12m", 0),
    help="Number of chargebacks in last 12 months",
)

# Decision buttons
st.sidebar.markdown("---")
st.sidebar.subheader("Evaluate Decision")

col_btn1, col_btn2 = st.sidebar.columns(2)
with col_btn1:
    rules_only_clicked = st.button("Decide (Rules only)", help="Evaluate using rules only, no ML")
with col_btn2:
    rules_ml_clicked = st.button(
        "Decide (Rules + ML)", help="Evaluate using rules and ML risk prediction"
    )

# Build request data
request_data: dict[str, Any] = {
    "cart_total": cart_total,
    "currency": currency,
    "features": {"velocity_24h": velocity_24h, "high_ip_distance": high_ip_distance},
    "context": {
        "location_ip_country": location_ip_country,
        "billing_country": billing_country,
        "customer": {"loyalty_tier": loyalty_tier, "chargebacks_12m": chargebacks_12m},
    },
}

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("Request JSON")
    st.json(request_data)

with col2:
    st.header("Decision Response")

    # Check if any button was clicked
    if rules_only_clicked or rules_ml_clicked:
        use_ml = rules_ml_clicked

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

            # Create summary table
            summary_data = {
                "Field": ["Decision", "Risk Score", "Rules Evaluated"],
                "Value": [
                    response.decision,
                    (
                        f"{response.meta.get('risk_score', 'N/A'):.3f}"
                        if use_ml
                        else "N/A (Rules only)"
                    ),
                    ", ".join(response.meta.get("rules_evaluated", [])) or "None",
                ],
            }
            st.table(summary_data)

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

            # Add tabs for output format
            st.markdown("---")
            output_tab = st.radio(
                "Output Format",
                ["JSON Output", "Plain-English Explanation"],
                horizontal=True,
                help="Choose how to display the decision response",
            )

            if output_tab == "JSON Output":
                # Display full response JSON
                st.subheader("Response JSON")
                response_dict = response.model_dump()
                st.json(response_dict)
            else:
                # Display plain-English explanation
                st.subheader("Plain-English Explanation")
                explanation = explain_decision(response)

                # Display in a nicely formatted box
                st.markdown(
                    f"""
                    <div style="
                        background-color: #f0f2f6;
                        padding: 20px;
                        border-radius: 10px;
                        border-left: 4px solid #1f77b4;
                        margin: 10px 0;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                    ">
                        {explanation.replace(chr(10), "<br>")}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        except Exception as e:
            st.error(f"Error evaluating decision: {e}")
    else:
        st.info("Click a decision button to evaluate the request")

# Footer
st.markdown("---")
st.markdown(
    "**Orca Core Decision Engine** - A production-ready decision engine for e-commerce applications"
)
