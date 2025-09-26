"""
Streamlit UI for Orca Demo
Fixed version with proper imports for Docker container
"""

import os
import sys
import json
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, '/app/src')

import streamlit as st

# Now we can import Orca modules
try:
    from orca_core.engine import evaluate_rules
    from orca_core.config import decision_mode, is_ai_enabled
    from orca_core.models import DecisionRequest
    from orca_core.llm.explain import get_llm_configuration_status, is_llm_configured
    from orca_core.ml.model import get_model_info
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

st.set_page_config(
    page_title="Orca AI Decision Engine Demo",
    page_icon="🐋",
    layout="wide"
)

st.title("🐋 Orca AI Decision Engine Demo")
st.markdown("**Open Checkout Network - AI Explainability Demo**")

# Sidebar for configuration
st.sidebar.header("🔧 Configuration")

# System Status
st.sidebar.subheader("System Status")
st.sidebar.success(f"Decision Mode: {decision_mode()}")
st.sidebar.success(f"AI Enabled: {is_ai_enabled()}")

# LLM Status
llm_status = get_llm_configuration_status()
if is_llm_configured():
    st.sidebar.success("✅ LLM Configured")
else:
    st.sidebar.warning("⚠️ LLM Not Configured (using deterministic mode)")

# Model Info
try:
    model_info = get_model_info()
    st.sidebar.subheader("Model Information")
    st.sidebar.json(model_info)
except Exception as e:
    st.sidebar.error(f"Model info unavailable: {e}")

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📊 Decision Testing")

    # Create a sample AP2 request
    sample_request = {
        "intent": {
            "amount": 125.50,
            "currency": "USD",
            "merchant_category_code": "5411",
            "channel": "ecommerce"
        },
        "cart": {
            "items": [
                {
                    "description": "Office Supplies",
                    "amount": 125.50,
                    "category": "office_supplies"
                }
            ],
            "total_amount": 125.50
        },
        "actor_profile": {
            "customer_id": "demo_customer_001",
            "risk_tier": "medium",
            "geography": "US"
        },
        "modality": {
            "payment_method": "credit_card",
            "device_type": "desktop",
            "session_id": "demo_session_123"
        },
        "metadata": {
            "demo": True,
            "trace_id": "demo_trace_orca_001",
            "timestamp": "2025-01-25T10:00:00Z"
        }
    }

    # Amount input
    amount = st.number_input(
        "Transaction Amount",
        min_value=0.0,
        value=125.50,
        step=0.01,
        help="Enter the transaction amount to test"
    )

    # Update amount in request
    sample_request["intent"]["amount"] = amount
    sample_request["cart"]["total_amount"] = amount
    sample_request["cart"]["items"][0]["amount"] = amount

    # Trace ID input
    trace_id = st.text_input(
        "Trace ID",
        value="demo_trace_orca_001",
        help="Unique identifier for this transaction"
    )
    sample_request["metadata"]["trace_id"] = trace_id

    # Risk tier selection
    risk_tier = st.selectbox(
        "Risk Tier",
        ["low", "medium", "high"],
        index=1,
        help="Customer risk profile"
    )
    sample_request["actor_profile"]["risk_tier"] = risk_tier

    # Channel selection
    channel = st.selectbox(
        "Channel",
        ["ecommerce", "pos", "mobile", "atm"],
        index=0,
        help="Transaction channel"
    )
    sample_request["intent"]["channel"] = channel

with col2:
    st.header("🎯 Decision Results")

    if st.button("🚀 Make Decision", type="primary"):
        try:
            # Create decision request
            decision_request = DecisionRequest(**sample_request)

            # Make decision
            with st.spinner("Processing decision..."):
                decision_result = evaluate_rules(decision_request)

            # Display results
            st.success("✅ Decision Complete!")

            # Outcome
            outcome = decision_result.outcome
            if outcome == "approve":
                st.success(f"🎉 **OUTCOME: APPROVE**")
            elif outcome == "decline":
                st.error(f"❌ **OUTCOME: DECLINE**")
            else:
                st.warning(f"⚠️ **OUTCOME: {outcome.upper()}**")

            # Confidence
            confidence = getattr(decision_result, 'confidence', None)
            if confidence:
                st.metric("Confidence", f"{confidence:.1%}")

            # Explanation
            explanation = getattr(decision_result, 'explanation', None)
            if explanation:
                st.subheader("🤖 AI Explanation")
                st.info(explanation)

            # Raw result
            with st.expander("📋 Raw Decision Data"):
                st.json(decision_result.__dict__)

        except Exception as e:
            st.error(f"Decision failed: {e}")
            st.exception(e)

# Footer
st.markdown("---")
st.markdown("**Open Checkout Network** | AI Explainability Demo | Phase 2")

# Add some demo data
st.header("📈 Live Demo Data")
st.markdown("This UI is connected to the live OCN demo. Try the Orion API at http://localhost:8081/docs")

# Show recent trace IDs
st.subheader("Recent Trace IDs")
st.code("""
Recent transactions:
• 06265b5f-3f3c-4536-a9d9-54c9c33f73c0 (Orion RTP optimization)
• demo_trace_orca_001 (Current session)
• demo_session_123 (Active session)
""")
