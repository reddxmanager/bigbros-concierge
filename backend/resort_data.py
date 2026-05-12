"""
Canonical resort configuration (rates, inventory, policies).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


CURRENCY = "PHP"

# --- Property-wide ---
PROPERTY_MAX_GUESTS_TOTAL = 50

CHECK_IN_TIME = "14:00"  # 2 PM
CHECK_OUT_TIME = "12:00"  # 12 PM
CHECK_IN_LABEL = "2:00 PM"
CHECK_OUT_LABEL = "12:00 PM (noon)"

DEPOSIT_AMOUNT_PHP = 5000
DEPOSIT_DUE_WITHIN_HOURS = 48

PAYMENT_METHODS: List[str] = ["GCash", "bank transfer"]


class RoomTypeConfig(TypedDict, total=False):
    key: str
    inventory_count: int
    base_guests_included: int
    max_guests: int
    base_rate_php: int
    extra_person_fee_php: int
    rate_unit: str  # "night" | "day"
    weekend_same_as_base: bool
    weekend_rate_php: int
    description: str
    includes: str


ROOM_TYPES: Dict[str, RoomTypeConfig] = {
    "Family Suite": {
        "key": "Family Suite",
        "inventory_count": 1,
        "base_guests_included": 4,
        "max_guests": 8,
        "base_rate_php": 8000,
        "extra_person_fee_php": 1000,
        "rate_unit": "night",
        "weekend_same_as_base": True,
        "weekend_rate_php": 8000,
        "description": "One family suite; base rate covers up to 4 guests.",
    },
    "Honeymoon Suite": {
        "key": "Honeymoon Suite",
        "inventory_count": 1,
        "base_guests_included": 2,
        "max_guests": 8,
        "base_rate_php": 8000,
        "extra_person_fee_php": 1000,
        "rate_unit": "night",
        "weekend_same_as_base": True,
        "weekend_rate_php": 8000,
        "description": "One honeymoon suite; base rate covers up to 2 guests.",
    },
    "Full Buyout": {
        "key": "Full Buyout",
        "inventory_count": 1,
        "base_guests_included": 50,
        "max_guests": 50,
        "base_rate_php": 40000,
        "extra_person_fee_php": 0,
        "rate_unit": "day",
        "weekend_same_as_base": True,
        "weekend_rate_php": 40000,
        "description": "Exclusive use of the property for up to 50 guests.",
        "includes": "Both suites, event terrace, and full property for the day.",
    },
}


# Flat maps for simple consumers / legacy-style lookups
ROOM_INVENTORY = {name: cfg["inventory_count"] for name, cfg in ROOM_TYPES.items()}

ROOM_BASE_GUESTS = {name: cfg["base_guests_included"] for name, cfg in ROOM_TYPES.items()}

ROOM_MAX_OCCUPANCY = {name: cfg["max_guests"] for name, cfg in ROOM_TYPES.items()}

RATE_TABLE = {
    name: {
        "base_rate_php": cfg["base_rate_php"],
        "nightly_rate": cfg["base_rate_php"],
        "weekend_rate": cfg["weekend_rate_php"],
        "rate_unit": cfg["rate_unit"],
        "extra_person_fee_php": cfg["extra_person_fee_php"],
        "base_guests_included": cfg["base_guests_included"],
    }
    for name, cfg in ROOM_TYPES.items()
}


CANCELLATION_POLICY_TEXT = (
    "14+ days before check-in: full refund. "
    "7-13 days before check-in: 50% refund. "
    "Under 7 days before check-in: no refund."
)

# Reference tiers (see cancellation_refund_percent for applied logic).
CANCELLATION_TIERS: List[Dict[str, Any]] = [
    {"min_days_before_checkin": 14, "refund_percent": 100, "summary": "14+ days: full refund"},
    {"min_days_before_checkin": 7, "refund_percent": 50, "summary": "7-13 days: 50% refund"},
    {"min_days_before_checkin": 0, "refund_percent": 0, "summary": "Under 7 days: no refund"},
]


DEPOSIT_POLICY_TEXT = (
    f"Deposit {DEPOSIT_AMOUNT_PHP:,} {CURRENCY} due within {DEPOSIT_DUE_WITHIN_HOURS} hours of booking confirmation."
)


DIRECTIONS_DATA = {
    "address": "Big Bros White Sand Resort, Zambales, Philippines",
    "google_maps_link": "https://maps.google.com",
    "directions": {
        "from_manila": "Via SCTEX/TPLEX to Subic, then coastal road north.",
        "from_clark": "Via SCTEX to Subic exit.",
        "from_subic": "Coastal road north.",
    },
    "landmarks": "Final landmarks to be filled.",
}


def list_room_type_names() -> List[str]:
    return list(ROOM_TYPES.keys())


def get_room_config(room_type: str) -> Optional[RoomTypeConfig]:
    return ROOM_TYPES.get(room_type)


def cancellation_refund_percent(days_before_checkin: int) -> int:
    """
    Refund percent (0–100) based on full days before check-in.
    >=14 -> 100%, 7-13 -> 50%, <7 -> 0%.
    """
    if days_before_checkin >= 14:
        return 100
    if days_before_checkin >= 7:
        return 50
    return 0


def extra_guest_count(room_type: str, total_guests: int) -> int:
    cfg = ROOM_TYPES.get(room_type)
    if not cfg:
        return 0
    base = cfg["base_guests_included"]
    return max(0, total_guests - base)


def extra_guest_fee_php(room_type: str, total_guests: int) -> int:
    cfg = ROOM_TYPES.get(room_type)
    if not cfg:
        return 0
    fee_each = cfg.get("extra_person_fee_php") or 0
    return extra_guest_count(room_type, total_guests) * fee_each


def rate_for_stay_php(room_type: str, num_rate_units: int, total_guests: int) -> int:
    """
    num_rate_units: nights for suites, days for Full Buyout.
    """
    cfg = ROOM_TYPES.get(room_type)
    if not cfg or num_rate_units <= 0:
        return 0
    base = cfg["base_rate_php"] * num_rate_units
    extras = extra_guest_fee_php(room_type, total_guests) * num_rate_units
    return base + extras
