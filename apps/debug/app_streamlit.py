"""Streamlit Debug App for Orca Core Decision Engine."""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from orca_core.engine import evaluate_rules  # noqa: E402
from orca_core.llm.adapter import explain_decision  # noqa: E402
from orca_core.models import DecisionRequest  # noqa: E402

# Page configuration
st.set_page_config(
    page_title="Orca Core Debug UI", page_icon="🐋", layout="wide", initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .decision-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 2px solid #e0e0e0;
        margin: 1rem 0;
    }
    .decision-approve {
        border-color: #28a745;
        background-color: #d4edda;
    }
    .decision-decline {
        border-color: #dc3545;
        background-color: #f8d7da;
    }
    .decision-review {
        border-color: #ffc107;
        background-color: #fff3cd;
    }
    .json-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        max-height: 400px;
        overflow-y: auto;
    }
</style>
""",
    unsafe_allow_html=True,
)


def main():
    """Main Streamlit app."""

    # Header
    st.markdown('<h1 class="main-header">🐋 Orca Core Debug UI</h1>', unsafe_allow_html=True)
    st.markdown("Interactive debugging interface for the Orca Core Decision Engine")

    # Sidebar controls
    st.sidebar.header("🔧 Configuration")

    # Rail selection
    rail = st.sidebar.selectbox(
        "Payment Rail", options=["Card", "ACH"], index=0, help="Select the payment rail type"
    )

    # Channel selection
    channel = st.sidebar.selectbox(
        "Transaction Channel",
        options=["online", "pos"],
        index=0,
        help="Select the transaction channel",
    )

    # ML toggle
    use_ml = st.sidebar.checkbox(
        "Enable ML Scoring", value=True, help="Enable/disable machine learning risk scoring"
    )

    # Explanation style
    explain_style = st.sidebar.selectbox(
        "Explanation Style",
        options=["merchant", "developer"],
        index=0,
        help="Select the explanation style for human-readable output",
    )

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<h2 class="section-header">📝 Input</h2>', unsafe_allow_html=True)

        # Input method selection
        input_method = st.radio(
            "Input Method", options=["Upload JSON", "Manual Entry"], horizontal=True
        )

        if input_method == "Upload JSON":
            uploaded_file = st.file_uploader(
                "Upload JSON file",
                type=["json"],
                help="Upload a JSON file with decision request data",
            )

            if uploaded_file is not None:
                try:
                    content = uploaded_file.read().decode("utf-8")
                    input_data = json.loads(content)
                    st.success("✅ JSON file loaded successfully!")
                except Exception as e:
                    st.error(f"❌ Error loading JSON file: {e}")
                    input_data = None
            else:
                input_data = None
        else:
            # Manual entry form
            st.markdown("**Manual Input Form**")

            cart_total = st.number_input(
                "Cart Total ($)",
                min_value=0.01,
                max_value=100000.0,
                value=150.0,
                step=0.01,
                format="%.2f",
            )

            # Context fields
            st.markdown("**Context Information**")
            col_ctx1, col_ctx2 = st.columns(2)

            with col_ctx1:
                velocity_24h = st.number_input(
                    "Velocity (24h)",
                    min_value=0,
                    max_value=100,
                    value=1,
                    help="Number of transactions in the last 24 hours",
                )

                item_count = st.number_input(
                    "Item Count",
                    min_value=1,
                    max_value=1000,
                    value=1,
                    help="Number of items in the cart",
                )

            with col_ctx2:
                location_mismatch = st.number_input(
                    "Location Mismatch",
                    min_value=0,
                    max_value=1,
                    value=0,
                    help="Location mismatch flag (0 or 1)",
                )

                user_age_days = st.number_input(
                    "User Age (days)",
                    min_value=0,
                    max_value=36500,
                    value=30,
                    help="User account age in days",
                )

            # Additional features
            st.markdown("**Additional Features**")
            previous_chargebacks = st.number_input(
                "Previous Chargebacks",
                min_value=0,
                max_value=100,
                value=0,
                help="Number of previous chargebacks",
            )

            account_verification = st.selectbox(
                "Account Verification Status",
                options=[0, 1],
                index=1,
                help="Account verification status (0=unverified, 1=verified)",
            )

            # Build input data
            input_data = {
                "cart_total": cart_total,
                "rail": rail,
                "channel": channel,
                "context": {
                    "velocity_24h": velocity_24h,
                    "item_count": item_count,
                    "location_mismatch": location_mismatch,
                    "user_age_days": user_age_days,
                    "previous_chargebacks": previous_chargebacks,
                    "account_verification_status": account_verification,
                },
            }

    with col2:
        st.markdown('<h2 class="section-header">🎯 Decision Output</h2>', unsafe_allow_html=True)

        if input_data is not None:
            # Process decision
            if st.button("🚀 Evaluate Decision", type="primary"):
                try:
                    # Create request
                    request = DecisionRequest(**input_data)

                    # Evaluate decision
                    with st.spinner("Evaluating decision..."):
                        response = evaluate_rules(request, use_ml=use_ml)

                    # Display decision result
                    decision = response.decision
                    risk_score = response.meta_structured.risk_score

                    # Decision card with styling
                    if decision == "APPROVE":
                        st.markdown(
                            f"""
                        <div class="decision-card decision-approve">
                            <h3>✅ APPROVED</h3>
                            <p><strong>Risk Score:</strong> {risk_score:.3f}</p>
                            <p><strong>Model Version:</strong> {response.meta_structured.model_version}</p>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    elif decision == "DECLINE":
                        st.markdown(
                            f"""
                        <div class="decision-card decision-decline">
                            <h3>❌ DECLINED</h3>
                            <p><strong>Risk Score:</strong> {risk_score:.3f}</p>
                            <p><strong>Model Version:</strong> {response.meta_structured.model_version}</p>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    else:  # REVIEW
                        st.markdown(
                            f"""
                        <div class="decision-card decision-review">
                            <h3>⏳ UNDER REVIEW</h3>
                            <p><strong>Risk Score:</strong> {risk_score:.3f}</p>
                            <p><strong>Model Version:</strong> {response.meta_structured.model_version}</p>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                    # Human explanation
                    st.markdown(
                        '<h3 class="section-header">💬 Human Explanation</h3>',
                        unsafe_allow_html=True,
                    )
                    explanation = explain_decision(response, explain_style)
                    st.info(explanation)

                    # Reasons and actions
                    col_reasons, col_actions = st.columns(2)

                    with col_reasons:
                        st.markdown("**Reasons:**")
                        for reason in response.reasons:
                            st.write(f"• {reason}")

                    with col_actions:
                        st.markdown("**Actions:**")
                        for action in response.actions:
                            st.write(f"• {action}")

                    # Signals panel
                    st.markdown(
                        '<h3 class="section-header">📊 Signals Panel</h3>', unsafe_allow_html=True
                    )

                    signals_data = {
                        "Signal": response.signals_triggered,
                        "Status": ["Triggered"] * len(response.signals_triggered),
                    }

                    if signals_data["Signal"]:
                        signals_df = pd.DataFrame(signals_data)
                        st.dataframe(signals_df, use_container_width=True)
                    else:
                        st.info("No signals triggered")

                    # ML Features (if ML is enabled)
                    if use_ml and response.meta_structured.features_used:
                        st.markdown(
                            '<h3 class="section-header">🤖 ML Features</h3>', unsafe_allow_html=True
                        )

                        features_data = {
                            "Feature": response.meta_structured.features_used,
                            "Used": ["Yes"] * len(response.meta_structured.features_used),
                        }

                        features_df = pd.DataFrame(features_data)
                        st.dataframe(features_df, use_container_width=True)

                    # JSON output
                    st.markdown(
                        '<h3 class="section-header">📄 Decision JSON</h3>', unsafe_allow_html=True
                    )

                    # Copy and download buttons
                    col_copy, col_download = st.columns(2)

                    with col_copy:
                        if st.button("📋 Copy JSON"):
                            st.code(json.dumps(response.model_dump(), indent=2), language="json")
                            st.success("JSON copied to clipboard!")

                    with col_download:
                        # Generate filename with timestamp
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"decision_{timestamp}.json"

                        # Create download button
                        json_str = json.dumps(response.model_dump(), indent=2)
                        st.download_button(
                            label="💾 Download JSON",
                            data=json_str,
                            file_name=filename,
                            mime="application/json",
                        )

                    # Report case button
                    st.markdown(
                        '<h3 class="section-header">📝 Case Reporting</h3>', unsafe_allow_html=True
                    )

                    if st.button("📤 Report This Case"):
                        # Create debug reports directory
                        debug_reports_dir = Path("docs/samples/debug-reports")
                        debug_reports_dir.mkdir(parents=True, exist_ok=True)

                        # Save case data
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        case_filename = debug_reports_dir / f"case_{timestamp}.json"

                        case_data = {
                            "timestamp": timestamp,
                            "input": input_data,
                            "output": response.model_dump(),
                            "config": {
                                "rail": rail,
                                "channel": channel,
                                "use_ml": use_ml,
                                "explain_style": explain_style,
                            },
                        }

                        with open(case_filename, "w") as f:
                            json.dump(case_data, f, indent=2, default=str)

                        st.success(f"✅ Case reported and saved to: {case_filename}")

                except Exception as e:
                    st.error(f"❌ Error evaluating decision: {e}")
                    st.exception(e)
        else:
            st.info("👈 Please provide input data to evaluate a decision")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "🐋 Orca Core Debug UI | Built with Streamlit | Phase 2 - AI/LLM Integration"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
