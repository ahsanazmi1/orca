"""AP2 Mandate Types - Source of Truth for AP2 Compliance.

This module defines the core data structures for AP2 (Agent Protocol 2) compliance,
including IntentMandate, CartMandate, and PaymentMandate types with validation.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class ActorType(str, Enum):
    """Types of actors in the system."""

    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class IntentType(str, Enum):
    """Types of intents that can be expressed."""

    PURCHASE = "purchase"
    REFUND = "refund"
    TRANSFER = "transfer"
    SUBSCRIPTION = "subscription"
    DONATION = "donation"
    INVESTMENT = "investment"


class ChannelType(str, Enum):
    """Communication channels."""

    WEB = "web"
    MOBILE = "mobile"
    API = "api"
    VOICE = "voice"
    CHAT = "chat"
    POS = "pos"


class AgentPresence(str, Enum):
    """Level of agent involvement."""

    NONE = "none"
    ASSISTED = "assisted"
    AUTONOMOUS = "autonomous"


class PaymentModality(str, Enum):
    """Payment processing modalities."""

    IMMEDIATE = "immediate"
    DEFERRED = "deferred"
    RECURRING = "recurring"
    INSTALLMENT = "installment"


class AuthRequirement(str, Enum):
    """Authentication requirements."""

    NONE = "none"
    PIN = "pin"
    BIOMETRIC = "biometric"
    TWO_FACTOR = "two_factor"
    MULTI_FACTOR = "multi_factor"


class RiskFlag(str, Enum):
    """Risk assessment flags."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CartItem(BaseModel):
    """Individual item in a cart."""

    id: str = Field(..., description="Unique item identifier")
    name: str = Field(..., description="Item name")
    description: Optional[str] = Field(None, description="Item description")
    quantity: int = Field(..., ge=1, description="Item quantity")
    unit_price: Decimal = Field(..., ge=0, description="Unit price")
    total_price: Decimal = Field(..., ge=0, description="Total price for this item")
    category: Optional[str] = Field(None, description="Item category")
    sku: Optional[str] = Field(None, description="Stock keeping unit")

    @field_validator("total_price")
    @classmethod
    def validate_total_price(cls, v: Any, info: Any) -> Any:
        """Validate that total_price equals quantity * unit_price."""
        if info.data and "quantity" in info.data and "unit_price" in info.data:
            expected = info.data["quantity"] * info.data["unit_price"]
            if v != expected:
                raise ValueError(f"total_price {v} must equal quantity * unit_price ({expected})")
        return v


class GeoLocation(BaseModel):
    """Geographic location information."""

    country: str = Field(..., description="Country code (ISO 3166-1 alpha-2)")
    region: Optional[str] = Field(None, description="Region/state")
    city: Optional[str] = Field(None, description="City")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    timezone: Optional[str] = Field(None, description="Timezone identifier")


class RoutingHint(BaseModel):
    """Payment routing hints."""

    processor: str = Field(..., description="Payment processor identifier")
    priority: int = Field(..., ge=1, le=10, description="Routing priority (1=highest)")
    constraints: Optional[dict[str, Any]] = Field(
        None, description="Additional routing constraints"
    )


class IntentMandate(BaseModel):
    """AP2 Intent Mandate - Defines the actor's intent and context."""

    actor: ActorType = Field(..., description="Type of actor expressing intent")
    intent_type: IntentType = Field(..., description="Type of intent being expressed")
    channel: ChannelType = Field(..., description="Communication channel")
    agent_presence: AgentPresence = Field(..., description="Level of agent involvement")
    timestamps: dict[str, datetime] = Field(..., description="Relevant timestamps")
    nonce: UUID = Field(default_factory=uuid4, description="Unique identifier for this intent")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("timestamps")
    @classmethod
    def validate_timestamps(cls, v: Any) -> Any:
        """Validate that timestamps contains required keys."""
        required_keys = {"created", "expires"}
        if not required_keys.issubset(v.keys()):
            missing = required_keys - set(v.keys())
            raise ValueError(f"Missing required timestamp keys: {missing}")
        return v

    @field_validator("timestamps")
    @classmethod
    def validate_timestamp_order(cls, v: Any) -> Any:
        """Validate that created timestamp is before expires timestamp."""
        if v["created"] >= v["expires"]:
            raise ValueError("created timestamp must be before expires timestamp")
        return v


class CartMandate(BaseModel):
    """AP2 Cart Mandate - Defines the shopping cart contents and context."""

    items: list[CartItem] = Field(..., min_length=1, description="Cart items")
    amount: Decimal = Field(..., ge=0, description="Total cart amount")
    currency: str = Field(..., min_length=3, max_length=3, description="Currency code (ISO 4217)")
    mcc: Optional[str] = Field(None, description="Merchant category code")
    geo: Optional[GeoLocation] = Field(None, description="Geographic location")
    risk_flags: list[RiskFlag] = Field(default_factory=list, description="Risk assessment flags")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Any, info: Any) -> Any:
        """Validate that amount equals sum of item total prices."""
        if info.data and "items" in info.data:
            expected = sum(item.total_price for item in info.data["items"])
            if v != expected:
                raise ValueError(f"amount {v} must equal sum of item total prices ({expected})")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Any) -> Any:
        """Validate currency code format."""
        if not v.isalpha() or not v.isupper():
            raise ValueError("currency must be a 3-letter uppercase code")
        return v


class PaymentMandate(BaseModel):
    """AP2 Payment Mandate - Defines payment instrument and processing requirements."""

    instrument_ref: Optional[str] = Field(None, description="Payment instrument reference")
    instrument_token: Optional[str] = Field(None, description="Payment instrument token")
    modality: PaymentModality = Field(..., description="Payment processing modality")
    constraints: Optional[dict[str, Any]] = Field(None, description="Payment constraints")
    routing_hints: list[RoutingHint] = Field(
        default_factory=list, description="Payment routing hints"
    )
    auth_requirements: list[AuthRequirement] = Field(
        default_factory=list, description="Authentication requirements"
    )
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")

    @model_validator(mode="after")
    def validate_instrument_required(self) -> "PaymentMandate":
        """Validate that at least one instrument identifier is provided."""
        if not self.instrument_ref and not self.instrument_token:
            raise ValueError("Either instrument_ref or instrument_token must be provided")
        return self


# Validation helper functions
def validate_intent(data: Union[dict[str, Any], str]) -> IntentMandate:
    """Validate and create an IntentMandate from JSON data."""
    if isinstance(data, str):
        import json

        data_dict: dict[str, Any] = json.loads(data)
    else:
        data_dict = data

    return IntentMandate(**data_dict)


def validate_cart(data: Union[dict[str, Any], str]) -> CartMandate:
    """Validate and create a CartMandate from JSON data."""
    if isinstance(data, str):
        import json

        data_dict: dict[str, Any] = json.loads(data)
    else:
        data_dict = data

    return CartMandate(**data_dict)


def validate_payment(data: Union[dict[str, Any], str]) -> PaymentMandate:
    """Validate and create a PaymentMandate from JSON data."""
    if isinstance(data, str):
        import json

        data_dict: dict[str, Any] = json.loads(data)
    else:
        data_dict = data

    return PaymentMandate(**data_dict)


# JSON serialization helpers
def intent_to_json(intent: IntentMandate) -> str:
    """Convert IntentMandate to JSON string."""
    return intent.model_dump_json()


def cart_to_json(cart: CartMandate) -> str:
    """Convert CartMandate to JSON string."""
    return cart.model_dump_json()


def payment_to_json(payment: PaymentMandate) -> str:
    """Convert PaymentMandate to JSON string."""
    return payment.model_dump_json()


def intent_from_json(json_str: str) -> IntentMandate:
    """Create IntentMandate from JSON string."""
    return IntentMandate.model_validate_json(json_str)


def cart_from_json(json_str: str) -> CartMandate:
    """Create CartMandate from JSON string."""
    return CartMandate.model_validate_json(json_str)


def payment_from_json(json_str: str) -> PaymentMandate:
    """Create PaymentMandate from JSON string."""
    return PaymentMandate.model_validate_json(json_str)
