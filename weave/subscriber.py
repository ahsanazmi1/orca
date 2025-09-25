"""
Weave CloudEvents Subscriber

This module provides HTTP endpoints to receive CloudEvents from Orca and other services,
validates them against schemas, and stores receipt hashes in the Weave blockchain.
"""

import hashlib
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

# Add src to path for contract validation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from orca.core.contract_validation import get_contract_validator

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Weave CloudEvents Subscriber",
    description="HTTP endpoint for receiving and processing CloudEvents",
    version="1.0.0",
)


class CloudEventData(BaseModel):
    """CloudEvent data payload validation."""

    pass  # Will be validated against specific schemas


class CloudEventRequest(BaseModel):
    """CloudEvent envelope validation."""

    specversion: str = Field(..., description="CloudEvents specification version")
    id: str = Field(..., description="Unique identifier for the event")
    source: str = Field(..., description="URI identifying the event producer")
    type: str = Field(..., description="Event type identifier")
    subject: str = Field(..., description="Subject for correlation")
    time: str = Field(..., description="Event timestamp in RFC3339 format")
    datacontenttype: str = Field(default="application/json", description="Content type of data")
    dataschema: str | None = Field(default=None, description="Schema URI for data payload")
    data: dict[str, Any] = Field(..., description="Event data payload")


class WeaveReceipt(BaseModel):
    """Weave receipt model."""

    trace_id: str = Field(..., description="Transaction ID for correlation")
    receipt_hash: str = Field(..., description="SHA-256 hash of the original data")
    event_type: str = Field(..., description="Type of event (decision, explanation)")
    timestamp: str = Field(..., description="When the receipt was created")
    block_height: int = Field(..., description="Block height where receipt was stored")
    transaction_hash: str = Field(..., description="Weave transaction hash")
    gas_used: int = Field(default=0, description="Gas used for the transaction")
    gas_price: str = Field(default="0", description="Gas price in wei")
    status: str = Field(default="success", description="Transaction status")
    error_message: str | None = Field(default=None, description="Error message if failed")


class WeaveClient:
    """Mock Weave blockchain client for storing receipts."""

    def __init__(self) -> None:
        """Initialize Weave client."""
        self.weave_endpoint = os.getenv("WEAVE_ENDPOINT", "http://localhost:8545")
        self.block_height = 1000000  # Mock block height

    def store_receipt(self, trace_id: str, receipt_hash: str, event_type: str) -> WeaveReceipt:
        """
        Store receipt hash in Weave blockchain.

        Args:
            trace_id: Transaction ID for correlation
            receipt_hash: SHA-256 hash of the original data
            event_type: Type of event (decision, explanation)

        Returns:
            WeaveReceipt with transaction details
        """
        try:
            # In a real implementation, this would:
            # 1. Create a transaction to store the receipt hash
            # 2. Submit to Weave network
            # 3. Wait for confirmation
            # 4. Return actual transaction hash and block height

            # For now, simulate the process
            mock_tx_hash = f"0x{hashlib.sha256(f'{trace_id}_{receipt_hash}'.encode()).hexdigest()}"
            mock_gas_used = 21000  # Standard gas limit for simple transaction

            receipt = WeaveReceipt(
                trace_id=trace_id,
                receipt_hash=receipt_hash,
                event_type=event_type,
                timestamp=datetime.now(UTC).isoformat(),
                block_height=self.block_height,
                transaction_hash=mock_tx_hash,
                gas_used=mock_gas_used,
                gas_price="20000000000",  # 20 gwei
                status="success",
            )

            # Increment mock block height
            self.block_height += 1

            logger.info(f"Stored receipt for {trace_id} in block {receipt.block_height}")
            return receipt

        except Exception as e:
            logger.error(f"Failed to store receipt for {trace_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to store receipt: {e}") from e


class SchemaValidator:
    """CloudEvent schema validator using ocn-common."""

    def __init__(self) -> None:
        """Initialize schema validator."""
        self.contract_validator = get_contract_validator()

    def validate_cloud_event(self, ce: CloudEventRequest) -> bool:
        """
        Validate CloudEvent against ocn-common schema.

        Args:
            ce: CloudEvent to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic CloudEvent structure validation
            required_fields = ["specversion", "id", "source", "type", "subject", "time", "data"]
            for field in required_fields:
                if not hasattr(ce, field):
                    logger.error(f"Missing required field: {field}")
                    return False

            # Validate specversion
            if ce.specversion != "1.0":
                logger.error(f"Invalid specversion: {ce.specversion}")
                return False

            # Validate event type
            if ce.type not in ["ocn.orca.decision.v1", "ocn.orca.explanation.v1"]:
                logger.error(f"Unsupported event type: {ce.type}")
                return False

            # Validate subject format (should be trace_id)
            if not ce.subject.startswith("txn_"):
                logger.error(f"Invalid subject format: {ce.subject}")
                return False

            # Validate timestamp format
            try:
                datetime.fromisoformat(ce.time.replace("Z", "+00:00"))
            except ValueError:
                logger.error(f"Invalid timestamp format: {ce.time}")
                return False

            # Validate CloudEvent using ocn-common contract validator
            ce_data = ce.model_dump()
            event_type = ce.type.replace("ocn.", "")

            if not self.contract_validator.validate_cloud_event(ce_data, event_type):
                logger.error(f"CloudEvent contract validation failed for {ce.type}")
                return False

            logger.info(f"CloudEvent validation passed for {ce.type}")
            return True

        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False


# Initialize services
weave_client = WeaveClient()
schema_validator = SchemaValidator()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}


@app.post("/events")
async def receive_cloud_event(request: Request):
    """
    Receive and process CloudEvents.

    This endpoint:
    1. Validates the CloudEvent against schemas
    2. Extracts the data payload
    3. Creates a receipt hash
    4. Stores the hash in Weave blockchain
    5. Emits an audit CloudEvent
    """
    try:
        # Parse CloudEvent
        body = await request.json()
        ce = CloudEventRequest(**body)

        logger.info(f"Received CloudEvent {ce.id} of type {ce.type} for subject {ce.subject}")

        # Validate CloudEvent
        if not schema_validator.validate_cloud_event(ce):
            raise HTTPException(status_code=400, detail="CloudEvent validation failed")

        # Determine event type for storage
        event_type = "decision" if "decision" in ce.type else "explanation"

        # Create receipt hash from the data payload
        data_json = json.dumps(ce.data, sort_keys=True)
        receipt_hash = f"sha256:{hashlib.sha256(data_json.encode()).hexdigest()}"

        # Store receipt in Weave
        receipt = weave_client.store_receipt(ce.subject, receipt_hash, event_type)

        # Emit audit CloudEvent
        audit_ce = await _emit_audit_cloud_event(ce, receipt)

        # Return success response
        response_data = {
            "status": "success",
            "message": f"CloudEvent {ce.id} processed successfully",
            "receipt": receipt.model_dump(),
            "audit_event_id": audit_ce.get("id") if audit_ce else None,
        }

        logger.info(f"Successfully processed CloudEvent {ce.id}")
        return JSONResponse(status_code=200, content=response_data)

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid CloudEvent format: {e}") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing CloudEvent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


async def _emit_audit_cloud_event(
    original_ce: CloudEventRequest, receipt: WeaveReceipt
) -> dict[str, Any] | None:
    """
    Emit audit CloudEvent to notify other services.

    Args:
        original_ce: Original CloudEvent that was processed
        receipt: Weave receipt details

    Returns:
        Audit CloudEvent data if successful, None otherwise
    """
    try:
        # Create audit CloudEvent
        audit_ce = {
            "specversion": "1.0",
            "id": str(uuid4()),
            "source": "https://weave.ocn.ai/audit-service",
            "type": "ocn.weave.audit.v1",
            "subject": original_ce.subject,
            "time": datetime.now(UTC).isoformat(),
            "datacontenttype": "application/json",
            "dataschema": "https://schemas.ocn.ai/weave/v1/audit.schema.json",
            "data": receipt.model_dump(),
        }

        # In a real implementation, this would emit to an event bus
        # For now, just log the audit event
        logger.info(f"Emitted audit CloudEvent {audit_ce['id']} for {original_ce.subject}")

        return audit_ce

    except Exception as e:
        logger.error(f"Failed to emit audit CloudEvent: {e}")
        return None


@app.get("/receipts/{trace_id}")
async def get_receipt(trace_id: str) -> dict[str, Any]:
    """
    Get receipt information for a trace_id.

    Args:
        trace_id: Transaction ID to look up

    Returns:
        Receipt information if found
    """
    try:
        # In a real implementation, this would query the Weave blockchain
        # For now, return a mock response
        if not trace_id.startswith("txn_"):
            raise HTTPException(status_code=400, detail="Invalid trace_id format")

        # Mock receipt lookup
        mock_receipt = WeaveReceipt(
            trace_id=trace_id,
            receipt_hash=f"sha256:{hashlib.sha256(trace_id.encode()).hexdigest()}",
            event_type="decision",
            timestamp=datetime.now(UTC).isoformat(),
            block_height=1000001,
            transaction_hash=f"0x{hashlib.sha256(trace_id.encode()).hexdigest()}",
            gas_used=21000,
            gas_price="20000000000",
            status="success",
        )

        return {"status": "success", "receipt": mock_receipt.model_dump()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving receipt for {trace_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)  # nosec B104
