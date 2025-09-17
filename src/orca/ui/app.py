"""AP2-compliant Streamlit UI for Orca Core decision engine."""

import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from ..core.decision_contract import (
    is_receipt_hash_only,
    is_signing_enabled,
    sign_and_hash_decision,
    validate_ap2_contract,
)
from ..core.decision_legacy_adapter import DecisionLegacyAdapter
from ..core.rules_engine import evaluate_ap2_rules
from ..explain.nlg import explain_ap2_decision
from ..mandates.ap2_types import (
    ActorType,
    AgentPresence,
    AuthRequirement,
    CartItem,
    CartMandate,
    ChannelType,
    GeoLocation,
    IntentMandate,
    IntentType,
    PaymentMandate,
    PaymentModality,
)


class AP2OrcaUI:
    """AP2-compliant Streamlit UI for Orca Core."""

    def __init__(self):
        """Initialize the AP2 Orca UI."""
        self.setup_page_config()
        self.initialize_session_state()

    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="Orca Core AP2 Decision Engine",
            page_icon="🐋",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    def initialize_session_state(self):
        """Initialize session state variables."""
        if "ap2_contract" not in st.session_state:
            st.session_state.ap2_contract = None
        if "decision_result" not in st.session_state:
            st.session_state.decision_result = None
        if "explanation" not in st.session_state:
            st.session_state.explanation = None
        if "rules_mode" not in st.session_state:
            st.session_state.rules_mode = "Rules-Only"
        if "signing_enabled" not in st.session_state:
            st.session_state.signing_enabled = False
        if "receipt_hash_only" not in st.session_state:
            st.session_state.receipt_hash_only = False

    def render_header(self):
        """Render the main header."""
        st.title("🐋 Orca Core AP2 Decision Engine")
        st.markdown("AP2-compliant decision engine with verifiable credentials and receipt hashing")

    def render_sidebar(self):
        """Render the sidebar with configuration options."""
        st.sidebar.header("Configuration")

        # Rules mode toggle
        st.sidebar.subheader("Decision Mode")
        rules_mode = st.sidebar.radio(
            "Select decision mode:",
            ["Rules-Only", "Rules+AI"],
            index=0,
            help="Rules-Only: Use only rule-based decisions. Rules+AI: Enhanced with AI explanations.",
        )
        st.session_state.rules_mode = rules_mode

        # Signing configuration
        st.sidebar.subheader("Signing & Receipts")
        signing_enabled = st.sidebar.checkbox(
            "Enable VC Signing",
            value=st.session_state.signing_enabled,
            help="Enable verifiable credential signing of decisions",
        )
        st.session_state.signing_enabled = signing_enabled

        receipt_hash_only = st.sidebar.checkbox(
            "Receipt Hash Only",
            value=st.session_state.receipt_hash_only,
            help="Generate receipt hashes without VC signing",
        )
        st.session_state.receipt_hash_only = receipt_hash_only

        # Update environment variables
        os.environ["ORCA_SIGN_DECISIONS"] = "true" if signing_enabled else "false"
        os.environ["ORCA_RECEIPT_HASH_ONLY"] = "true" if receipt_hash_only else "false"

        # Sample data section
        st.sidebar.subheader("Sample Data")
        if st.sidebar.button("Load Sample AP2 Contract"):
            self.load_sample_contract()

        if st.sidebar.button("Load Golden File"):
            self.load_golden_file()

    def load_sample_contract(self):
        """Load a sample AP2 contract."""
        try:
            # Create sample contract
            intent = IntentMandate(
                actor=ActorType.HUMAN,
                intent_type=IntentType.PURCHASE,
                channel=ChannelType.WEB,
                agent_presence=AgentPresence.ASSISTED,
                timestamps={
                    "created": datetime.now(UTC),
                    "expires": datetime.now(UTC).replace(hour=23, minute=59, second=59),
                },
            )

            cart = CartMandate(
                items=[
                    CartItem(
                        id="sample_item_1",
                        name="Sample Product",
                        quantity=1,
                        unit_price=Decimal("100.00"),
                        total_price=Decimal("100.00"),
                    )
                ],
                amount=Decimal("100.00"),
                currency="USD",
                mcc="5733",
                geo=GeoLocation(country="US"),
            )

            payment = PaymentMandate(
                instrument_ref="sample_card_123456789",
                modality=PaymentModality.IMMEDIATE,
                auth_requirements=[AuthRequirement.PIN],
            )

            from ..core.decision_contract import create_ap2_decision_contract

            ap2_contract = create_ap2_decision_contract(
                intent=intent,
                cart=cart,
                payment=payment,
                result="APPROVE",
                risk_score=0.1,
                reasons=[],
                actions=[],
            )

            st.session_state.ap2_contract = ap2_contract
            st.success("✅ Sample AP2 contract loaded")

        except Exception as e:
            st.error(f"❌ Error loading sample contract: {e}")

    def load_golden_file(self):
        """Load the golden AP2 file."""
        try:
            golden_file = Path("tests/golden/decision.ap2.json")
            if golden_file.exists():
                with open(golden_file) as f:
                    contract_data = json.load(f)

                ap2_contract = validate_ap2_contract(contract_data)
                st.session_state.ap2_contract = ap2_contract
                st.success("✅ Golden AP2 file loaded")
            else:
                st.error("❌ Golden file not found")

        except Exception as e:
            st.error(f"❌ Error loading golden file: {e}")

    def render_ap2_input_section(self):
        """Render the AP2 input section."""
        st.header("📥 AP2 Decision Request")

        # JSON input
        st.subheader("AP2 JSON Input")
        ap2_json = st.text_area(
            "Paste your AP2 decision request JSON here:",
            height=300,
            placeholder='{"ap2_version": "0.1.0", "intent": {...}, "cart": {...}, "payment": {...}}',
            help="Enter a valid AP2 decision request in JSON format",
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔍 Validate AP2", type="primary"):
                if ap2_json.strip():
                    try:
                        contract_data = json.loads(ap2_json)
                        ap2_contract = validate_ap2_contract(contract_data)
                        st.session_state.ap2_contract = ap2_contract
                        st.success("✅ AP2 contract is valid")
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Invalid JSON: {e}")
                    except ValidationError as e:
                        st.error(f"❌ AP2 validation error: {e}")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                else:
                    st.warning("⚠️ Please enter AP2 JSON")

        with col2:
            if st.button("🚀 Process Decision"):
                if st.session_state.ap2_contract:
                    self.process_decision()
                else:
                    st.warning("⚠️ Please validate AP2 contract first")

    def render_ap2_panes(self):
        """Render collapsible AP2 mandate panes."""
        if not st.session_state.ap2_contract:
            st.info("👆 Please load or validate an AP2 contract first")
            return

        contract = st.session_state.ap2_contract

        st.header("📋 AP2 Mandates")

        # Intent Mandate
        with st.expander("🎯 Intent Mandate", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Actor:**", contract.intent.actor.value)
                st.write("**Intent Type:**", contract.intent.intent_type.value)
                st.write("**Channel:**", contract.intent.channel.value)

            with col2:
                st.write("**Agent Presence:**", contract.intent.agent_presence.value)
                st.write("**Created:**", contract.intent.timestamps["created"])
                st.write("**Expires:**", contract.intent.timestamps["expires"])

        # Cart Mandate
        with st.expander("🛒 Cart Mandate", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Amount:**", f"{contract.cart.amount} {contract.cart.currency}")
                st.write("**MCC:**", contract.cart.mcc or "Not specified")
                st.write("**Items:**", len(contract.cart.items))

            with col2:
                if contract.cart.geo:
                    st.write("**Country:**", contract.cart.geo.country)
                    st.write("**City:**", contract.cart.geo.city or "Not specified")
                else:
                    st.write("**Geo:** Not specified")

            # Cart items table
            if contract.cart.items:
                st.subheader("Cart Items")
                items_data = []
                for item in contract.cart.items:
                    items_data.append(
                        {
                            "ID": item.id,
                            "Name": item.name,
                            "Quantity": item.quantity,
                            "Unit Price": f"${item.unit_price}",
                            "Total": f"${item.total_price}",
                        }
                    )
                st.table(items_data)

        # Payment Mandate
        with st.expander("💳 Payment Mandate", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Modality:**", contract.payment.modality.value)
                st.write("**Instrument Ref:**", contract.payment.instrument_ref or "Not specified")

            with col2:
                st.write(
                    "**Auth Requirements:**",
                    [req.value for req in contract.payment.auth_requirements],
                )
                if contract.payment.routing_hints:
                    st.write("**Routing Hints:**", contract.payment.routing_hints)

    def process_decision(self):
        """Process the AP2 decision through the rules engine."""
        try:
            contract = st.session_state.ap2_contract

            # Process through rules engine
            with st.spinner("🔄 Processing decision..."):
                decision_outcome = evaluate_ap2_rules(contract)

                # Update contract with decision outcome
                contract.decision = decision_outcome

                # Sign and hash if enabled
                signed_contract = sign_and_hash_decision(contract)

                # Generate explanation
                explanation = explain_ap2_decision(signed_contract)

                # Store results
                st.session_state.ap2_contract = signed_contract
                st.session_state.decision_result = decision_outcome
                st.session_state.explanation = explanation

            st.success("✅ Decision processed successfully")

        except Exception as e:
            st.error(f"❌ Error processing decision: {e}")

    def render_decision_result(self):
        """Render the decision result section."""
        if not st.session_state.decision_result:
            return

        st.header("⚖️ Decision Result")

        result = st.session_state.decision_result

        # Decision summary
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Decision", result.result)

        with col2:
            st.metric("Risk Score", f"{result.risk_score:.3f}")

        with col3:
            st.metric("Model", result.meta.model)

        # Reasons
        if result.reasons:
            st.subheader("📝 Decision Reasons")
            for reason in result.reasons:
                st.write(f"**{reason.code}:** {reason.detail}")

        # Actions
        if result.actions:
            st.subheader("🎬 Recommended Actions")
            for action in result.actions:
                st.write(f"**{action.type}:** {action.detail or 'No additional details'}")

        # Explanation
        if st.session_state.explanation:
            st.subheader("💬 Human-Readable Explanation")
            st.info(st.session_state.explanation)

    def render_signature_receipt_section(self):
        """Render the signature and receipt section."""
        if not st.session_state.ap2_contract or not st.session_state.ap2_contract.signing:
            return

        st.header("🔐 Signing & Receipts")

        signing_info = st.session_state.ap2_contract.signing

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📜 Verifiable Credential Proof")
            if signing_info.vc_proof:
                st.success("✅ VC Proof Generated")
                st.json(signing_info.vc_proof)
            else:
                st.info("ℹ️ No VC proof (signing disabled)")

        with col2:
            st.subheader("🧾 Receipt Hash")
            if signing_info.receipt_hash:
                st.success("✅ Receipt Hash Generated")
                st.code(signing_info.receipt_hash, language="text")

                # Copy button for receipt hash
                if st.button("📋 Copy Receipt Hash"):
                    st.code(signing_info.receipt_hash)
                    st.success("Receipt hash copied to clipboard!")
            else:
                st.info("ℹ️ No receipt hash generated")

    def render_output_section(self):
        """Render the output section with copy functionality."""
        if not st.session_state.ap2_contract:
            return

        st.header("📤 Output")

        # Output format selection
        output_format = st.radio("Select output format:", ["AP2 JSON", "Legacy JSON"], index=0)

        # Generate output
        if output_format == "AP2 JSON":
            output_data = st.session_state.ap2_contract.model_dump()
        else:
            # Convert to legacy format
            legacy_response = DecisionLegacyAdapter.ap2_contract_to_legacy_response(
                st.session_state.ap2_contract
            )
            output_data = legacy_response.model_dump()

        # Display output
        st.subheader(f"📄 {output_format} Output")
        output_json = json.dumps(output_data, indent=2, default=str)
        st.code(output_json, language="json")

        # Copy button
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📋 Copy AP2 Decision JSON", type="primary"):
                st.code(output_json)
                st.success("AP2 decision JSON copied to clipboard!")

        with col2:
            if st.button("💾 Download JSON"):
                st.download_button(
                    label="Download JSON File",
                    data=output_json,
                    file_name=f"orca_decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )

    def render_status_section(self):
        """Render the status section."""
        st.sidebar.header("Status")

        # Signing status
        if is_signing_enabled():
            st.sidebar.success("🔐 VC Signing: Enabled")
        elif is_receipt_hash_only():
            st.sidebar.info("🧾 Receipt Hash: Enabled")
        else:
            st.sidebar.warning("⚠️ Signing: Disabled")

        # Decision mode
        st.sidebar.info(f"🤖 Mode: {st.session_state.rules_mode}")

        # Contract status
        if st.session_state.ap2_contract:
            st.sidebar.success("✅ AP2 Contract: Loaded")
        else:
            st.sidebar.warning("⚠️ AP2 Contract: Not loaded")

    def run(self):
        """Run the Streamlit app."""
        self.render_header()
        self.render_sidebar()
        self.render_status_section()

        # Main content
        self.render_ap2_input_section()
        self.render_ap2_panes()
        self.render_decision_result()
        self.render_signature_receipt_section()
        self.render_output_section()


def main():
    """Main entry point for the Streamlit app."""
    app = AP2OrcaUI()
    app.run()


if __name__ == "__main__":
    main()
