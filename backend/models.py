from pydantic import BaseModel
from typing import Optional, List, Dict


class AvailabilityRequest(BaseModel):
    check_in: str
    check_out: str
    guests: int


class RatesRequest(BaseModel):
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    room_type: Optional[str] = None
    guests: Optional[int] = None


class BookingRequest(BaseModel):
    guest_name: str
    email: str
    phone: str
    check_in: str
    check_out: str
    guests: int
    room_type: str
    special_requests: Optional[str] = None


class DirectionsRequest(BaseModel):
    from_location: Optional[str] = None


class OwnerBookingsRequest(BaseModel):
    start_date: str
    end_date: str


class BlockDatesRequest(BaseModel):
    start_date: str
    end_date: str
    reason: str


class OccupancyRequest(BaseModel):
    month: int
    year: int


class AvailabilityRoom(BaseModel):
    room_type: str
    available_count: int
    max_occupancy: int


class AvailabilityResponse(BaseModel):
    available: bool
    check_in: str
    check_out: str
    available_dates: List[str]
    unavailable_dates: List[str]
    rooms: List[AvailabilityRoom]
    message: str


class RateItem(BaseModel):
    room_type: str
    nightly_rate: int
    weekend_rate: int
    total_estimate: int
    nights: int
    max_occupancy: int
    extra_person_fee: int
    currency: str
    description: str
    image_key: str


class RatesResponse(BaseModel):
    rates: List[RateItem]
    season: str
    notes: str


class BookingResponse(BaseModel):
    success: bool
    booking_ref: str
    guest_name: str
    room_type: str
    check_in: str
    check_out: str
    nights: int
    total_estimate: int
    currency: str
    deposit_deadline: Optional[str] = None
    message: str


class DirectionsDetails(BaseModel):
    from_manila: str
    from_clark: str
    from_subic: str


class DirectionsResponse(BaseModel):
    address: str
    google_maps_link: str
    directions: DirectionsDetails
    landmarks: str
    contact_if_lost: str


class OwnerBookingItem(BaseModel):
    booking_ref: str
    guest_name: str
    room_type: str
    check_in: str
    check_out: str
    deposit_status: str


class OwnerBookingsResponse(BaseModel):
    start_date: str
    end_date: str
    bookings: List[OwnerBookingItem]
    message: str


class OwnerBlockDatesResponse(BaseModel):
    success: bool
    start_date: str
    end_date: str
    reason: str
    message: str


class OccupancyWeekBreakdown(BaseModel):
    week_label: str
    occupancy_percentage: float


class OwnerOccupancyResponse(BaseModel):
    month: int
    year: int
    occupancy_percentage: float
    weekly_breakdown: List[OccupancyWeekBreakdown]
    revenue_estimate: int
    currency: str
    message: str
