"""
CloudEvents Integration for Orca Core

This module provides CloudEvents emission capabilities for decision and explanation events,
following the ocn-common event schemas.
"""

import logging
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from ocn_common.trace import inject_trace_id_ce
from pydantic import BaseModel, Field

from .contract_validation import get_contract_validator

logger = logging.getLogger(__name__)


class CloudEvent(BaseModel):
    """CloudEvent envelope following CloudEvents 1.0 specification."""

    specversion: str = Field(default="1.0", description="CloudEvents specification version")
    id: str = Field(description="Unique identifier for the event")
    source: str = Field(description="URI identifying the event producer")
    type: str = Field(description="Event type identifier")
    subject: str = Field(description="Subject for correlation")
    time: str = Field(description="Event timestamp in RFC3339 format")
    datacontenttype: str = Field(default="application/json", description="Content type of data")
    dataschema: str | None = Field(default=None, description="Schema URI for data payload")
    data: dict[str, Any] = Field(description="Event data payload")


class CloudEventEmitter:
    """CloudEvents emitter for Orca decision and explanation events."""

    def __init__(self, subscriber_url: str | None = None):
        """
        Initialize CloudEvents emitter.

        Args:
            subscriber_url: Optional URL to POST CloudEvents to
        """
        self.subscriber_url = subscriber_url or os.getenv("ORCA_CE_SUBSCRIBER_URL")
        self.source_uri = os.getenv("ORCA_CE_SOURCE_URI", "https://orca.ocn.ai/decision-engine")

        if self.subscriber_url:
            logger.info(
                f"CloudEvents emitter initialized with subscriber URL: {self.subscriber_url}"
            )
        else:
            logger.info("CloudEvents emitter initialized without subscriber URL")

    def emit_decision_event(
        self, decision_data: dict[str, Any], trace_id: str, emit_to_subscriber: bool = True
    ) -> CloudEvent | None:
        """
        Emit a decision CloudEvent.

        Args:
            decision_data: AP2 decision payload
            trace_id: Transaction trace ID
            emit_to_subscriber: Whether to POST to subscriber URL

        Returns:
            CloudEvent object if successful, None otherwise
        """
        try:
            # Validate required fields
            if not trace_id or not trace_id.startswith("txn_"):
                raise ValueError(f"Invalid trace_id format: {trace_id}")

            # Validate AP2 decision contract using ocn-common
            validator = get_contract_validator()
            if not validator.validate_ap2_decision(decision_data):
                logger.error("AP2 decision contract validation failed")
                return None

            # Create CloudEvent
            ce_data = {
                "specversion": "1.0",
                "id": str(uuid4()),
                "source": self.source_uri,
                "type": "ocn.orca.decision.v1",
                "time": datetime.now(UTC).isoformat(),
                "datacontenttype": "application/json",
                "dataschema": "https://schemas.ocn.ai/ap2/v1/decision.schema.json",
                "data": decision_data,
            }

            # Inject trace ID into CloudEvent subject using centralized utility
            ce_data = inject_trace_id_ce(ce_data, trace_id)

            ce = CloudEvent(**ce_data)

            # Validate CloudEvent contract using ocn-common
            if not validator.validate_cloud_event(ce.model_dump(), "orca.decision.v1"):
                logger.error("CloudEvent contract validation failed")
                return None

            logger.info(f"Created decision CloudEvent {ce.id} for trace_id {trace_id}")

            # Emit to subscriber if configured
            if emit_to_subscriber and self.subscriber_url:
                self._emit_to_subscriber(ce)

            return ce

        except Exception as e:
            logger.error(f"Failed to emit decision CloudEvent: {e}")
            return None

    def emit_explanation_event(
        self, explanation_data: dict[str, Any], trace_id: str, emit_to_subscriber: bool = True
    ) -> CloudEvent | None:
        """
        Emit an explanation CloudEvent.

        Args:
            explanation_data: Explanation payload
            trace_id: Transaction trace ID
            emit_to_subscriber: Whether to POST to subscriber URL

        Returns:
            CloudEvent object if successful, None otherwise
        """
        try:
            # Validate required fields
            if not trace_id or not trace_id.startswith("txn_"):
                raise ValueError(f"Invalid trace_id format: {trace_id}")

            # Validate AP2 explanation contract using ocn-common
            validator = get_contract_validator()
            if not validator.validate_ap2_explanation(explanation_data):
                logger.error("AP2 explanation contract validation failed")
                return None

            # Create CloudEvent
            ce_data = {
                "specversion": "1.0",
                "id": str(uuid4()),
                "source": self.source_uri,
                "type": "ocn.orca.explanation.v1",
                "time": datetime.now(UTC).isoformat(),
                "datacontenttype": "application/json",
                "dataschema": "https://schemas.ocn.ai/ap2/v1/explanation.schema.json",
                "data": explanation_data,
            }

            # Inject trace ID into CloudEvent subject using centralized utility
            ce_data = inject_trace_id_ce(ce_data, trace_id)

            ce = CloudEvent(**ce_data)

            # Validate CloudEvent contract using ocn-common
            if not validator.validate_cloud_event(ce.model_dump(), "orca.explanation.v1"):
                logger.error("CloudEvent contract validation failed")
                return None

            logger.info(f"Created explanation CloudEvent {ce.id} for trace_id {trace_id}")

            # Emit to subscriber if configured
            if emit_to_subscriber and self.subscriber_url:
                self._emit_to_subscriber(ce)

            return ce

        except Exception as e:
            logger.error(f"Failed to emit explanation CloudEvent: {e}")
            return None

    def _emit_to_subscriber(self, ce: CloudEvent) -> bool:
        """
        POST CloudEvent to subscriber URL.

        Args:
            ce: CloudEvent to emit

        Returns:
            True if successful, False otherwise
        """
        if not self.subscriber_url:
            logger.warning("No subscriber URL configured, skipping emission")
            return False

        try:
            # Serialize CloudEvent
            ce_json = ce.model_dump_json()

            # POST to subscriber
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.subscriber_url,
                    content=ce_json,
                    headers={
                        "Content-Type": "application/cloudevents+json",
                        "User-Agent": "Orca-Core-CloudEvents/1.0",
                    },
                )
                response.raise_for_status()

                logger.info(f"Successfully emitted CloudEvent {ce.id} to {self.subscriber_url}")
                return True

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error emitting CloudEvent {ce.id}: {e.response.status_code} {e.response.text}"
            )
            return False
        except httpx.RequestError as e:
            logger.error(f"Request error emitting CloudEvent {ce.id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error emitting CloudEvent {ce.id}: {e}")
            return False


def get_cloud_event_emitter() -> CloudEventEmitter:
    """Get configured CloudEvents emitter instance."""
    return CloudEventEmitter()


def emit_decision_event(decision_data: dict[str, Any], trace_id: str) -> CloudEvent | None:
    """
    Convenience function to emit a decision CloudEvent.

    Args:
        decision_data: AP2 decision payload
        trace_id: Transaction trace ID

    Returns:
        CloudEvent object if successful, None otherwise
    """
    emitter = get_cloud_event_emitter()
    return emitter.emit_decision_event(decision_data, trace_id)


def emit_explanation_event(explanation_data: dict[str, Any], trace_id: str) -> CloudEvent | None:
    """
    Convenience function to emit an explanation CloudEvent.

    Args:
        explanation_data: Explanation payload
        trace_id: Transaction trace ID

    Returns:
        CloudEvent object if successful, None otherwise
    """
    emitter = get_cloud_event_emitter()
    return emitter.emit_explanation_event(explanation_data, trace_id)
