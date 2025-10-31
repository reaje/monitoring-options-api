"""Pydantic models for data validation and serialization."""

from pydantic import BaseModel, EmailStr, Field, UUID4
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


# =====================================
# ENUMS
# =====================================


class OptionSide(str, Enum):
    """Option side: CALL or PUT."""

    CALL = "CALL"
    PUT = "PUT"


class OptionStrategy(str, Enum):
    """Option strategy types."""

    COVERED_CALL = "COVERED_CALL"
    SHORT_PUT = "SHORT_PUT"
    LONG_PUT = "LONG_PUT"
    OTHER = "OTHER"


class PositionStatus(str, Enum):
    """Position status."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


class AlertStatus(str, Enum):
    """Alert status."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"


# =====================================
# AUTH MODELS
# =====================================


class UserRegister(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=6)
    name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    user_metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


class TokenResponse(BaseModel):
    """Authentication token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: UserResponse


# =====================================
# ACCOUNT MODELS
# =====================================


class AccountBase(BaseModel):
    """Account base model."""

    name: str = Field(..., min_length=1, max_length=100)
    broker: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=100)


class AccountCreate(AccountBase):
    """Account creation request."""

    user_id: UUID4


class AccountUpdate(BaseModel):
    """Account update request."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    broker: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=100)


class Account(AccountBase):
    """Account response."""

    id: UUID4
    user_id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================
# ASSET MODELS
# =====================================


class AssetBase(BaseModel):
    """Asset base model."""

    ticker: str = Field(..., min_length=1, max_length=10)
    account_id: UUID4


class AssetCreate(AssetBase):
    """Asset creation request."""

    pass


class AssetUpdate(BaseModel):
    """Asset update request."""

    ticker: Optional[str] = Field(None, min_length=1, max_length=10)


class Asset(AssetBase):
    """Asset response."""

    id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================
# OPTION POSITION MODELS
# =====================================


class OptionPositionBase(BaseModel):
    """Option position base model."""

    account_id: UUID4
    asset_id: UUID4
    side: OptionSide
    strategy: OptionStrategy
    strike: float = Field(..., gt=0)
    expiration: date
    quantity: int = Field(..., gt=0)
    avg_premium: float = Field(..., gt=0)
    notes: Optional[str] = None


class OptionPositionCreate(OptionPositionBase):
    """Option position creation request."""

    pass


class OptionPositionUpdate(BaseModel):
    """Option position update request."""

    side: Optional[OptionSide] = None
    strategy: Optional[OptionStrategy] = None
    strike: Optional[float] = Field(None, gt=0)
    expiration: Optional[date] = None
    quantity: Optional[int] = Field(None, gt=0)
    avg_premium: Optional[float] = Field(None, gt=0)
    status: Optional[PositionStatus] = None
    notes: Optional[str] = None


class OptionPosition(OptionPositionBase):
    """Option position response."""

    id: UUID4
    status: PositionStatus = PositionStatus.OPEN
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================
# EQUITY POSITION MODELS
# =====================================


class EquityPositionBase(BaseModel):
    """Equity position base model."""

    account_id: UUID4
    asset_id: UUID4
    quantity: int = Field(..., gt=0)
    avg_price: float = Field(..., gt=0)


class EquityPositionCreate(EquityPositionBase):
    """Equity position creation request."""

    pass


class EquityPositionUpdate(BaseModel):
    """Equity position update request."""

    quantity: Optional[int] = Field(None, gt=0)
    avg_price: Optional[float] = Field(None, gt=0)


class EquityPosition(EquityPositionBase):
    """Equity position response."""

    id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================
# ROLL RULE MODELS
# =====================================


class RollRuleBase(BaseModel):
    """Roll rule base model."""

    account_id: UUID4
    delta_threshold: Optional[float] = Field(0.60, ge=0, le=1)
    dte_min: Optional[int] = Field(3, ge=0)
    dte_max: Optional[int] = Field(5, ge=0)
    spread_threshold: Optional[float] = Field(None, ge=0)
    price_to_strike_ratio: Optional[float] = Field(0.98, ge=0, le=1)
    min_volume: Optional[int] = Field(1000, ge=0)
    max_spread: Optional[float] = Field(0.05, ge=0)
    min_oi: Optional[int] = Field(5000, ge=0)
    target_otm_pct_low: Optional[float] = Field(0.03, ge=0)
    target_otm_pct_high: Optional[float] = Field(0.08, ge=0)
    premium_close_threshold: Optional[float] = Field(None, ge=0)
    notify_channels: Optional[List[str]] = Field(default_factory=lambda: ["whatsapp", "sms"])
    is_active: Optional[bool] = Field(True)


class RollRuleCreate(RollRuleBase):
    """Roll rule creation request."""

    pass


class RollRuleUpdate(BaseModel):
    """Roll rule update request."""

    delta_threshold: Optional[float] = Field(None, ge=0, le=1)
    dte_min: Optional[int] = Field(None, ge=0)
    dte_max: Optional[int] = Field(None, ge=0)
    spread_threshold: Optional[float] = Field(None, ge=0)
    price_to_strike_ratio: Optional[float] = Field(None, ge=0, le=1)
    min_volume: Optional[int] = Field(None, ge=0)
    max_spread: Optional[float] = Field(None, ge=0)
    min_oi: Optional[int] = Field(None, ge=0)
    target_otm_pct_low: Optional[float] = Field(None, ge=0)
    target_otm_pct_high: Optional[float] = Field(None, ge=0)
    premium_close_threshold: Optional[float] = Field(None, ge=0)
    notify_channels: Optional[List[str]] = None
    is_active: Optional[bool] = None


class RollRule(RollRuleBase):
    """Roll rule response."""

    id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================
# ALERT MODELS
# =====================================


class AlertQueueBase(BaseModel):
    """Alert queue base model."""

    account_id: UUID4
    option_position_id: Optional[UUID4] = None
    reason: str
    payload: Dict[str, Any]


class AlertQueueCreate(AlertQueueBase):
    """Alert queue creation request."""

    pass


class AlertQueue(AlertQueueBase):
    """Alert queue response."""

    id: UUID4
    created_at: datetime
    status: AlertStatus = AlertStatus.PENDING

    class Config:
        from_attributes = True


class AlertLogBase(BaseModel):
    """Alert log base model."""

    queue_id: UUID4
    channel: str
    target: str
    message: str
    status: str


class AlertLogCreate(AlertLogBase):
    """Alert log creation request."""

    provider_msg_id: Optional[str] = None


class AlertLog(AlertLogBase):
    """Alert log response."""

    id: UUID4
    sent_at: Optional[datetime] = None
    provider_msg_id: Optional[str] = None

    class Config:
        from_attributes = True


# =====================================
# ROLL EXECUTION MODELS
# =====================================


class RollExecutionBase(BaseModel):
    """Roll execution base model."""

    account_id: UUID4
    from_option_id: UUID4
    to_option: Dict[str, Any]
    net_credit: float
    notes: Optional[str] = None


class RollExecutionCreate(RollExecutionBase):
    """Roll execution creation request."""

    executed_by: UUID4


class RollExecution(RollExecutionBase):
    """Roll execution response."""

    id: UUID4
    executed_by: UUID4
    executed_at: datetime

    class Config:
        from_attributes = True


# =====================================
# MARKET DATA MODELS
# =====================================


class MarketSnapshot(BaseModel):
    """Market snapshot model."""

    asset_id: UUID4
    ticker: str
    ts: datetime
    last_price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    delta: Optional[float] = None
    theta: Optional[float] = None
    volume: Optional[int] = None
    oi: Optional[int] = None
    spread: Optional[float] = None


# =====================================
# NOTIFICATION MODELS
# =====================================


class NotificationRequest(BaseModel):
    """Manual notification request."""

    account_id: UUID4
    message: str
    channels: List[str] = Field(default_factory=lambda: ["whatsapp"])
    phone: str


# =====================================
# ROLL PREVIEW MODELS
# =====================================


class RollPreviewRequest(BaseModel):
    """Roll preview request."""

    option_position_id: UUID4


class RollSuggestion(BaseModel):
    """Roll suggestion."""

    strike: float
    expiration: date
    otm_pct: float
    premium: float
    net_credit: float
    spread: float
    volume: int
    oi: int
    score: float


class RollPreviewResponse(BaseModel):
    """Roll preview response."""

    current_position: OptionPosition
    suggestions: List[RollSuggestion]
