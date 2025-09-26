"""
Simple Orca Demo - No complex imports
A basic Streamlit interface for testing Orca decisions
"""

import streamlit as st
import json
import requests

st.set_page_config(
    page_title="Orca Simple Demo",
    page_icon="🐋",
    layout="wide"
)

st.title("🐋 Orca Simple Demo")
st.markdown("**Open Checkout Network - Simple Decision Testing**")

# Sidebar
st.sidebar.header("🔧 Configuration")
st.sidebar.info("This is a simple demo that tests the Orca API endpoints")

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📊 Test Decision")

    # Simple form
    amount = st.number_input("Amount", min_value=0.0, value=125.50, step=0.01)
    trace_id = st.text_input("Trace ID", value="demo-trace-001")
    risk_tier = st.selectbox("Risk Tier", ["low", "medium", "high"], index=1)
    channel = st.selectbox("Channel", ["ecommerce", "pos", "mobile"], index=0)

    # Create request payload
    request_data = {
        "intent": {
            "amount": amount,
            "currency": "USD",
            "merchant_category_code": "5411",
            "channel": channel
        },
        "actor_profile": {
            "customer_id": "demo_customer",
            "risk_tier": risk_tier,
            "geography": "US"
        },
        "metadata": {
            "trace_id": trace_id,
            "demo": True
        }
    }

with col2:
    st.header("🎯 Results")

    if st.button("🚀 Test Decision", type="primary"):
        try:
            # Test Orca API
            with st.spinner("Calling Orca API..."):
                response = requests.post(
                    "http://localhost:8080/decide",
                    json=request_data,
                    timeout=10
                )

            if response.status_code == 200:
                result = response.json()
                st.success("✅ API Call Successful!")

                # Show outcome
                outcome = result.get("outcome", "unknown")
                if outcome == "approve":
                    st.success(f"🎉 **OUTCOME: APPROVE**")
                elif outcome == "decline":
                    st.error(f"❌ **OUTCOME: DECLINE**")
                else:
                    st.warning(f"⚠️ **OUTCOME: {outcome.upper()}**")

                # Show trace ID
                trace_id_result = result.get("trace_id", "N/A")
                st.info(f"**Trace ID**: {trace_id_result}")

                # Show raw response
                with st.expander("📋 Raw Response"):
                    st.json(result)

            else:
                st.error(f"❌ API Error: {response.status_code}")
                st.text(response.text)

        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to Orca API (port 8080)")
            st.info("Make sure 'make up' is running")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# Test other services
st.header("🔗 Test Other Services")

col3, col4, col5 = st.columns(3)

with col3:
    st.subheader("🐋 Orca Health")
    if st.button("Check Orca"):
        try:
            response = requests.get("http://localhost:8080/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ Healthy")
            else:
                st.error(f"❌ {response.status_code}")
        except:
            st.error("❌ Unavailable")

with col4:
    st.subheader("🚀 Orion Health")
    if st.button("Check Orion"):
        try:
            response = requests.get("http://localhost:8081/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ Healthy")
            else:
                st.error(f"❌ {response.status_code}")
        except:
            st.error("❌ Unavailable")

with col5:
    st.subheader("🌊 Weave Health")
    if st.button("Check Weave"):
        try:
            response = requests.get("http://localhost:8082/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ Healthy")
            else:
                st.error("❌ Unavailable")
        except:
            st.error("❌ Unavailable")

# Demo data section
st.header("📈 Demo Data")
st.markdown("""
**Recent Demo Results:**
- **Orion Optimization**: RTP selected with 98.8/100 score
- **Trace ID**: 06265b5f-3f3c-4536-a9d9-54c9c33f73c0
- **CloudEvents**: Successfully emitted and received by Weave

**API Endpoints:**
- Orca: http://localhost:8080/docs
- Orion: http://localhost:8081/docs
- Weave: http://localhost:8082/docs
""")

# Footer
st.markdown("---")
st.markdown("**Open Checkout Network** | Simple Demo | Phase 2")
