"""
Streamlit Debug UI for Orca Core

This module provides a comprehensive debug interface for testing and visualizing
the Orca decision engine with real-time configuration management.
"""

import os
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from ..config import decision_mode, is_ai_enabled

# Import Orca Core modules
from ..engine import evaluate_rules
from ..llm.explain import get_llm_configuration_status, is_llm_configured
from ..ml.model import get_model_info
from ..models import DecisionRequest


class OrcaDebugUI:
    """Main debug UI class for Orca Core."""

    def __init__(self) -> None:
        """Initialize the debug UI."""
        self.setup_page_config()
        self.initialize_session_state()

    def setup_page_config(self) -> None:
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="Orca Core Debug UI",
            page_icon="🐋",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    def initialize_session_state(self) -> None:
        """Initialize session state variables."""
        if "decision_history" not in st.session_state:
            st.session_state.decision_history = []
        if "determinism_results" not in st.session_state:
            st.session_state.determinism_results = []

    def render_sidebar(self) -> None:
        """Render the sidebar with configuration options."""
        st.sidebar.title("🐋 Orca Core Debug")
        st.sidebar.markdown("---")

        # Mode Selection
        st.sidebar.subheader("🔧 Configuration")

        # Decision Mode Toggle
        current_mode = decision_mode()
        mode_options = ["RULES_ONLY", "RULES_PLUS_AI"]
        selected_mode = st.sidebar.selectbox(
            "Decision Mode", options=mode_options, index=mode_options.index(current_mode.value)
        )

        # ML Engine Selection
        use_xgb = os.getenv("ORCA_USE_XGB", "false").lower() == "true"
        ml_engine = st.sidebar.selectbox(
            "ML Engine", options=["stub", "xgboost"], index=1 if use_xgb else 0
        )

        # Update environment variables
        if selected_mode != current_mode.value or (ml_engine == "xgboost") != use_xgb:
            os.environ["ORCA_MODE"] = selected_mode
            os.environ["ORCA_USE_XGB"] = "true" if ml_engine == "xgboost" else "false"
            st.sidebar.success("Configuration updated!")
            st.rerun()

        st.sidebar.markdown("---")

        # Azure OpenAI Configuration
        self.render_azure_config()

        st.sidebar.markdown("---")

        # System Status
        self.render_system_status()

        st.sidebar.markdown("---")

        # Quick Actions
        self.render_quick_actions()

    def render_azure_config(self) -> None:
        """Render Azure OpenAI configuration section."""
        st.sidebar.subheader("🔑 Azure OpenAI Config")

        # Current configuration
        current_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        current_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        current_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

        # Input fields
        new_endpoint = st.sidebar.text_input(
            "Endpoint", value=current_endpoint, help="Azure OpenAI endpoint URL"
        )

        new_api_key = st.sidebar.text_input(
            "API Key", value=current_api_key, type="password", help="Azure OpenAI API key"
        )

        new_deployment = st.sidebar.text_input(
            "Deployment", value=current_deployment, help="Model deployment name"
        )

        # Save configuration
        if st.sidebar.button("💾 Save Config"):
            if new_endpoint and new_api_key:
                self.save_env_config(
                    {
                        "AZURE_OPENAI_ENDPOINT": new_endpoint,
                        "AZURE_OPENAI_API_KEY": new_api_key,
                        "AZURE_OPENAI_DEPLOYMENT": new_deployment,
                    }
                )
                st.sidebar.success("Configuration saved!")
            else:
                st.sidebar.error("Please provide endpoint and API key")

    def render_system_status(self) -> None:
        """Render system status information."""
        st.sidebar.subheader("📊 System Status")

        # Decision mode status
        current_mode = decision_mode()
        ai_enabled = is_ai_enabled()

        st.sidebar.metric("Decision Mode", current_mode.value)
        st.sidebar.metric("AI Enabled", "✅ Yes" if ai_enabled else "❌ No")

        # ML model status
        model_info = get_model_info()
        st.sidebar.metric("ML Model", model_info.get("model_type", "unknown"))

        # LLM status
        llm_configured = is_llm_configured()
        st.sidebar.metric("LLM Status", "✅ Ready" if llm_configured else "❌ Not configured")

    def render_quick_actions(self) -> None:
        """Render quick action buttons."""
        st.sidebar.subheader("⚡ Quick Actions")

        if st.sidebar.button("🧹 Clear History"):
            st.session_state.decision_history = []
            st.session_state.determinism_results = []
            st.sidebar.success("History cleared!")

        if st.sidebar.button("🔄 Refresh Status"):
            st.rerun()

    def save_env_config(self, config: dict[str, str]) -> None:
        """Save configuration to .env.local file."""
        try:
            env_path = ".env.local"
            existing_config = {}

            # Read existing config
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            key, value = line.strip().split("=", 1)
                            existing_config[key] = value

            # Update with new values
            existing_config.update(config)

            # Write back to file
            with open(env_path, "w") as f:
                for key, value in existing_config.items():
                    f.write(f"{key}={value}\n")

        except Exception as e:
            st.sidebar.error(f"Failed to save config: {e}")

    def render_main_content(self) -> None:
        """Render the main content area."""
        st.title("🐋 Orca Core Decision Engine Debug UI")
        st.markdown("Real-time testing and visualization of the Orca decision engine")

        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "🎯 Decision Testing",
                "📊 Decision History",
                "🔍 Determinism Check",
                "📈 Model Analysis",
            ]
        )

        with tab1:
            self.render_decision_testing()

        with tab2:
            self.render_decision_history()

        with tab3:
            self.render_determinism_check()

        with tab4:
            self.render_model_analysis()

    def render_decision_testing(self) -> None:
        """Render the decision testing interface."""
        st.subheader("🎯 Test Decision Engine")

        # Create two columns for input and output
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("#### Input Parameters")

            # Transaction details
            cart_total = st.number_input("Cart Total ($)", min_value=0.0, value=100.0, step=10.0)
            currency = st.selectbox("Currency", ["USD", "EUR", "GBP"], index=0)
            rail = st.selectbox("Rail", ["Card", "ACH"], index=0)
            channel = st.selectbox("Channel", ["online", "pos"], index=0)

            # Features
            st.markdown("#### ML Features")
            amount = st.number_input("Amount", min_value=0.0, value=600.0, step=50.0)
            velocity_24h = st.number_input("Velocity (24h)", min_value=0.0, value=3.0, step=0.5)
            cross_border = st.selectbox("Cross Border", [0, 1], index=1)

            # Additional features
            with st.expander("Advanced Features"):
                velocity_7d = st.number_input("Velocity (7d)", min_value=0.0, value=10.0, step=1.0)
                velocity_30d = st.number_input(
                    "Velocity (30d)", min_value=0.0, value=30.0, step=5.0
                )
                customer_age_days = st.number_input(
                    "Customer Age (days)", min_value=0.0, value=365.0, step=30.0
                )
                loyalty_score = st.slider("Loyalty Score", 0.0, 1.0, 0.5, 0.1)
                chargebacks_12m = st.number_input(
                    "Chargebacks (12m)", min_value=0.0, value=0.0, step=0.1
                )

        with col2:
            st.markdown("#### Decision Result")

            # Test button
            if st.button("🚀 Test Decision", type="primary"):
                with st.spinner("Processing decision..."):
                    try:
                        # Create request
                        request = DecisionRequest(
                            cart_total=cart_total,
                            currency=currency,
                            rail=rail,  # type: ignore
                            channel=channel,  # type: ignore
                            features={
                                "amount": amount,
                                "velocity_24h": velocity_24h,
                                "cross_border": cross_border,
                                "velocity_7d": velocity_7d,
                                "velocity_30d": velocity_30d,
                                "customer_age_days": customer_age_days,
                                "loyalty_score": loyalty_score,
                                "chargebacks_12m": chargebacks_12m,
                            },
                        )

                        # Evaluate decision
                        result = evaluate_rules(request)

                        # Store in history
                        decision_record = {
                            "timestamp": datetime.now().isoformat(),
                            "input": request.dict(),
                            "output": result.dict(),
                        }
                        st.session_state.decision_history.append(decision_record)

                        # Display results
                        self.display_decision_result(result)

                    except Exception as e:
                        st.error(f"Error processing decision: {e}")

    def display_decision_result(self, result: Any) -> None:
        """Display the decision result in a formatted way."""
        # Decision summary
        col1, col2, col3 = st.columns(3)

        with col1:
            decision_color = (
                "green"
                if result.decision == "APPROVE"
                else "red"
                if result.decision == "DECLINE"
                else "orange"
            )
            st.markdown(f"### Decision: :{decision_color}[{result.decision}]")

        with col2:
            risk_score = result.meta.get("ai", {}).get(
                "risk_score", result.meta.get("risk_score", 0.0)
            )
            st.metric("Risk Score", f"{risk_score:.3f}")

        with col3:
            model_type = result.meta.get("ai", {}).get("model_type", "unknown")
            st.metric("Model Type", model_type)

        # Reasons and actions
        st.markdown("#### 📋 Reasons & Actions")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Reasons:**")
            for reason in result.reasons:
                st.markdown(f"• {reason}")

        with col2:
            st.markdown("**Actions:**")
            for action in result.actions:
                st.markdown(f"• {action}")

        # AI-specific information
        if "ai" in result.meta:
            ai_data = result.meta["ai"]
            st.markdown("#### 🤖 AI Analysis")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Reason Codes:**")
                for code in ai_data.get("reason_codes", []):
                    st.markdown(f"• {code}")

            with col2:
                st.markdown("**Model Info:**")
                st.markdown(f"• Version: {ai_data.get('version', 'unknown')}")
                st.markdown(f"• Type: {ai_data.get('model_type', 'unknown')}")

            # LLM Explanation
            if "llm_explanation" in ai_data:
                llm_data = ai_data["llm_explanation"]
                st.markdown("#### 💬 LLM Explanation")

                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**Explanation:** {llm_data.get('explanation', 'N/A')}")

                with col2:
                    st.metric("Confidence", f"{llm_data.get('confidence', 0.0):.2f}")
                    st.metric("Tokens", llm_data.get("tokens_used", 0))
                    st.metric("Time (ms)", llm_data.get("processing_time_ms", 0))

        # Raw JSON
        with st.expander("📄 Raw Decision JSON"):
            st.json(result.dict())

    def render_decision_history(self) -> None:
        """Render the decision history tab."""
        st.subheader("📊 Decision History")

        if not st.session_state.decision_history:
            st.info("No decisions recorded yet. Test some decisions in the 'Decision Testing' tab.")
            return

        # Create a DataFrame for better visualization
        history_data = []
        for record in st.session_state.decision_history:
            history_data.append(
                {
                    "Timestamp": record["timestamp"],
                    "Decision": record["output"]["decision"],
                    "Risk Score": record["output"]["meta"]
                    .get("ai", {})
                    .get("risk_score", record["output"]["meta"].get("risk_score", 0.0)),
                    "Model Type": record["output"]["meta"]
                    .get("ai", {})
                    .get("model_type", "unknown"),
                    "Amount": record["input"]["cart_total"],
                    "Channel": record["input"]["channel"],
                    "Rail": record["input"]["rail"],
                }
            )

        df = pd.DataFrame(history_data)
        st.dataframe(df, use_container_width=True)

        # Summary statistics
        st.markdown("#### 📈 Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Decisions", len(df))

        with col2:
            approve_rate = (df["Decision"] == "APPROVE").mean() * 100
            st.metric("Approve Rate", f"{approve_rate:.1f}%")

        with col3:
            avg_risk = df["Risk Score"].mean()
            st.metric("Avg Risk Score", f"{avg_risk:.3f}")

        with col4:
            xgb_usage = (df["Model Type"] == "xgboost").mean() * 100
            st.metric("XGBoost Usage", f"{xgb_usage:.1f}%")

    def render_determinism_check(self) -> None:
        """Render the determinism check interface."""
        st.subheader("🔍 Determinism Check")
        st.markdown("Test if the decision engine produces consistent results for the same input.")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("#### Test Parameters")

            # Simple test case
            test_amount = st.number_input("Test Amount", min_value=0.0, value=100.0, step=10.0)
            test_velocity = st.number_input("Test Velocity", min_value=0.0, value=2.0, step=0.5)
            test_cross_border = st.selectbox("Test Cross Border", [0, 1], index=0)
            num_tests = st.slider("Number of Tests", 5, 50, 10)

            if st.button("🧪 Run Determinism Test", type="primary"):
                with st.spinner("Running determinism test..."):
                    self.run_determinism_test(
                        test_amount, test_velocity, test_cross_border, num_tests
                    )

        with col2:
            if st.session_state.determinism_results:
                st.markdown("#### Test Results")

                results = st.session_state.determinism_results[-1]

                # Consistency metrics
                col1, col2 = st.columns(2)

                with col1:
                    st.metric(
                        "Consistent Decisions",
                        f"{results['consistent_decisions']}/{results['total_tests']}",
                    )
                    st.metric("Decision Consistency", f"{results['decision_consistency']:.1f}%")

                with col2:
                    st.metric("Risk Score Variance", f"{results['risk_variance']:.6f}")
                    st.metric("Max Risk Difference", f"{results['max_risk_diff']:.6f}")

                # Results table
                st.markdown("#### Detailed Results")
                results_df = pd.DataFrame(results["detailed_results"])
                st.dataframe(results_df, use_container_width=True)

                # Consistency analysis
                if results["decision_consistency"] == 100.0:
                    st.success("✅ Perfect determinism - all decisions are consistent!")
                elif results["decision_consistency"] >= 95.0:
                    st.warning("⚠️ Good determinism - minor variations detected")
                else:
                    st.error("❌ Poor determinism - significant variations detected")

    def run_determinism_test(
        self, amount: float, velocity: float, cross_border: int, num_tests: int
    ) -> None:
        """Run a determinism test with the given parameters."""
        results = []

        for i in range(num_tests):
            try:
                request = DecisionRequest(
                    cart_total=amount,
                    currency="USD",
                    rail="Card",
                    channel="online",
                    features={
                        "amount": amount,
                        "velocity_24h": velocity,
                        "cross_border": cross_border,
                    },
                )

                result = evaluate_rules(request)

                results.append(
                    {
                        "Test": i + 1,
                        "Decision": result.decision,
                        "Risk Score": result.meta.get("ai", {}).get(
                            "risk_score", result.meta.get("risk_score", 0.0)
                        ),
                        "Model Type": result.meta.get("ai", {}).get("model_type", "unknown"),
                    }
                )

            except Exception:
                results.append(
                    {"Test": i + 1, "Decision": "ERROR", "Risk Score": 0.0, "Model Type": "error"}
                )

        # Analyze results
        decisions = [r["Decision"] for r in results if r["Decision"] != "ERROR"]
        risk_scores = [r["Risk Score"] for r in results if r["Risk Score"] != 0.0]

        consistent_decisions = len(set(decisions)) == 1 if decisions else 0
        decision_consistency = (consistent_decisions / len(decisions) * 100) if decisions else 0

        risk_variance = pd.Series(risk_scores).var() if len(risk_scores) > 1 else 0.0
        max_risk_diff = max(risk_scores) - min(risk_scores) if len(risk_scores) > 1 else 0.0

        test_result = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": num_tests,
            "consistent_decisions": consistent_decisions,
            "decision_consistency": decision_consistency,
            "risk_variance": risk_variance,
            "max_risk_diff": max_risk_diff,
            "detailed_results": results,
        }

        st.session_state.determinism_results.append(test_result)

    def render_model_analysis(self) -> None:
        """Render the model analysis tab."""
        st.subheader("📈 Model Analysis")

        # Get model information
        model_info = get_model_info()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Current Model Info")
            st.json(model_info)

        with col2:
            st.markdown("#### LLM Configuration")
            llm_status = get_llm_configuration_status()
            st.json(llm_status)

        # Feature importance (if available)
        if model_info.get("model_type") == "xgboost":
            st.markdown("#### Feature Importance")

            # This would need to be implemented in the model info
            # For now, show a placeholder
            st.info("Feature importance visualization would be displayed here for XGBoost models.")

        # Performance metrics
        st.markdown("#### Performance Metrics")

        if st.session_state.decision_history:
            history_data = []
            for record in st.session_state.decision_history:
                history_data.append(
                    {
                        "Timestamp": record["timestamp"],
                        "Risk Score": record["output"]["meta"]
                        .get("ai", {})
                        .get("risk_score", record["output"]["meta"].get("risk_score", 0.0)),
                        "Model Type": record["output"]["meta"]
                        .get("ai", {})
                        .get("model_type", "unknown"),
                        "Processing Time": record["output"]["meta"]
                        .get("ai", {})
                        .get("llm_explanation", {})
                        .get("processing_time_ms", 0),
                    }
                )

            df = pd.DataFrame(history_data)

            # Risk score distribution
            st.markdown("##### Risk Score Distribution")
            st.line_chart(df.set_index("Timestamp")["Risk Score"])

            # Model usage over time
            st.markdown("##### Model Usage Over Time")
            model_counts = df["Model Type"].value_counts()
            st.bar_chart(model_counts)

    def run(self) -> None:
        """Run the debug UI."""
        self.render_sidebar()
        self.render_main_content()


def main() -> None:
    """Main function to run the debug UI."""
    ui = OrcaDebugUI()
    ui.run()


if __name__ == "__main__":
    main()
