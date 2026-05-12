import secrets
import string
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from googleapiclient.errors import HttpError

from calendar_service import (
    CalendarService,
    compute_suite_buyout_occupancy,
    deposit_deadline_iso,
    get_calendar_service,
    parse_booking_description,
    stay_window_datetimes,
    ROOM_BUYOUT,
    ROOM_FAMILY,
    ROOM_HONEYMOON,
    _parse_google_datetime,
)
from config import CALENDAR_MAP, GOOGLE_SERVICE_ACCOUNT_INFO, settings
from models import (
    AvailabilityRequest,
    AvailabilityResponse,
    AvailabilityRoom,
    RateItem,
    RatesRequest,
    RatesResponse,
    BookingRequest,
    BookingResponse,
    DirectionsRequest,
    DirectionsResponse,
    OwnerBookingsRequest,
    OwnerBookingsResponse,
    OwnerBookingItem,
    BlockDatesRequest,
    OwnerBlockDatesResponse,
    OccupancyRequest,
    OwnerOccupancyResponse,
    OccupancyWeekBreakdown,
)
from resort_data import (
    CURRENCY,
    DIRECTIONS_DATA,
    PROPERTY_MAX_GUESTS_TOTAL,
    RATE_TABLE,
    ROOM_TYPES,
    ROOM_MAX_OCCUPANCY,
    list_room_type_names,
    rate_for_stay_php,
)

app = FastAPI(title="Kuya Concierge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MANILA = ZoneInfo("Asia/Manila")

# Seasonal pricing hook (no uplift yet).
SEASON_MULTIPLIER = 1.0


def _parse_ymd(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date: {value}") from exc


def _validate_stay_dates(check_in: str, check_out: str) -> Tuple[date, date]:
    d_in = _parse_ymd(check_in)
    d_out = _parse_ymd(check_out)
    if d_out <= d_in:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")
    return d_in, d_out


def _daterange_strings(d0: date, d1_exclusive: date) -> List[str]:
    out: List[str] = []
    cur = d0
    while cur < d1_exclusive:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def _generate_booking_ref(check_in: date) -> str:
    alphabet = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"BB-{check_in.strftime('%Y%m%d')}-{suffix}"


def _booking_description(
    *,
    booking_ref: str,
    guest_name: str,
    email: str,
    phone: str,
    guests: int,
    room_type: str,
    nights: int,
    total: int,
    deposit_deadline: str,
    special_requests: Optional[str],
) -> str:
    spec = (special_requests or "").strip() or "None"
    total_fmt = f"PHP {total:,}"
    return (
        f"Booking Ref: {booking_ref}\n"
        f"Guest: {guest_name}\n"
        f"Email: {email}\n"
        f"Phone: {phone}\n"
        f"Guests: {guests}\n"
        f"Room: {room_type}\n"
        f"Nights: {nights}\n"
        f"Estimated Total: {total_fmt}\n"
        f"Status: PROVISIONAL\n"
        f"Deposit Deadline: {deposit_deadline}\n"
        f"Special Requests: {spec}\n"
        f"Booked via: Kuya Voice Concierge"
    )


def _room_available_for_type(svc: CalendarService, room_type: str, check_in: str, check_out: str) -> bool:
    if room_type == ROOM_BUYOUT:
        return svc.check_all_availability(check_in, check_out).get(ROOM_BUYOUT, False)
    cal_id = CALENDAR_MAP.get(room_type, "")
    return svc.check_availability(check_in, check_out, cal_id)


def _owner_range_iso(start_date: str, end_date: str) -> Tuple[str, str]:
    s = _parse_ymd(start_date)
    e = _parse_ymd(end_date)
    if e < s:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")
    start_dt = datetime.combine(s, time(0, 0), tzinfo=MANILA)
    end_dt = datetime.combine(e + timedelta(days=1), time(0, 0), tzinfo=MANILA)
    query_min = (start_dt - timedelta(days=1)).isoformat()
    query_max = (end_dt + timedelta(days=1)).isoformat()
    return query_min, query_max


def _event_overlaps_owner_range(
    event: dict,
    range_start: datetime,
    range_end_exclusive: datetime,
) -> bool:
    ev_start = _parse_google_datetime(event, use_end=False)
    ev_end = _parse_google_datetime(event, use_end=True)
    if ev_start is None or ev_end is None:
        return False
    return ev_start < range_end_exclusive and ev_end > range_start


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/api/check-availability", response_model=AvailabilityResponse)
async def check_availability(req: AvailabilityRequest) -> AvailabilityResponse:
    d_in, d_out = _validate_stay_dates(req.check_in, req.check_out)
    if req.guests < 1:
        raise HTTPException(status_code=400, detail="guests must be at least 1")

    if not GOOGLE_SERVICE_ACCOUNT_INFO:
        return AvailabilityResponse(
            available=False,
            check_in=req.check_in,
            check_out=req.check_out,
            available_dates=[],
            unavailable_dates=_daterange_strings(d_in, d_out),
            rooms=[
                AvailabilityRoom(
                    room_type=name,
                    available_count=0,
                    max_occupancy=ROOM_MAX_OCCUPANCY.get(name, 0),
                )
                for name in ROOM_MAX_OCCUPANCY.keys()
            ],
            message="Google Calendar is not configured (service account missing).",
        )

    try:
        svc = get_calendar_service()
        per_room = svc.check_all_availability(req.check_in, req.check_out)
        overlapping_guests = svc.get_total_guests(req.check_in, req.check_out)
    except HttpError as exc:
        raise HTTPException(status_code=502, detail=f"Google Calendar error: {exc}") from exc

    cap_ok = overlapping_guests + req.guests <= PROPERTY_MAX_GUESTS_TOTAL
    rooms: List[AvailabilityRoom] = []
    any_available = False
    for name in ("Family Suite", "Honeymoon Suite", "Full Buyout"):
        max_occ = ROOM_MAX_OCCUPANCY.get(name, 0)
        cal_free = bool(per_room.get(name))
        bookable = 1 if (cal_free and cap_ok) else 0
        if bookable:
            any_available = True
        rooms.append(
            AvailabilityRoom(
                room_type=name,
                available_count=bookable,
                max_occupancy=max_occ,
            )
        )

    stay_dates = _daterange_strings(d_in, d_out)
    if any_available and cap_ok:
        available_dates = stay_dates
        unavailable_dates: List[str] = []
        msg = (
            f"Rooms open for these dates (property guests currently {overlapping_guests}; "
            f"cap {PROPERTY_MAX_GUESTS_TOTAL})."
        )
    elif not cap_ok:
        available_dates = []
        unavailable_dates = stay_dates
        msg = (
            f"Guest count would exceed the property cap ({PROPERTY_MAX_GUESTS_TOTAL}). "
            f"Overlapping bookings total {overlapping_guests} guests; requested {req.guests}."
        )
    else:
        available_dates = []
        unavailable_dates = stay_dates
        msg = "No rooms available for the selected stay window."

    return AvailabilityResponse(
        available=any_available and cap_ok,
        check_in=req.check_in,
        check_out=req.check_out,
        available_dates=available_dates,
        unavailable_dates=unavailable_dates,
        rooms=rooms,
        message=msg,
    )


def _rates_target_room_types(room_type: Optional[str]) -> List[str]:
    if room_type is None or not str(room_type).strip():
        return list_room_type_names()
    key = str(room_type).strip()
    if key not in RATE_TABLE:
        raise HTTPException(status_code=400, detail=f"Unknown room_type: {room_type}")
    return [key]


def _guest_count_for_quote(room_type: str, guests: Optional[int]) -> int:
    cfg = ROOM_TYPES.get(room_type)
    if not cfg:
        return 1
    base = cfg["base_guests_included"]
    cap = cfg["max_guests"]
    if guests is None:
        return base
    return max(1, min(int(guests), cap))


@app.post("/api/get-rates", response_model=RatesResponse)
async def get_rates(req: RatesRequest) -> RatesResponse:
    has_in = req.check_in is not None and str(req.check_in).strip() != ""
    has_out = req.check_out is not None and str(req.check_out).strip() != ""
    if has_in ^ has_out:
        raise HTTPException(
            status_code=400,
            detail="Provide both check_in and check_out for a stay total, or omit both for rate card only.",
        )

    nights = 0
    if has_in and has_out:
        d_in, d_out = _validate_stay_dates(str(req.check_in).strip(), str(req.check_out).strip())
        nights = (d_out - d_in).days

    room_names = _rates_target_room_types(req.room_type)
    rates_out: List[RateItem] = []

    for name in room_names:
        row = RATE_TABLE[name]
        cfg = ROOM_TYPES[name]
        nightly_base = int(row["nightly_rate"] * SEASON_MULTIPLIER)
        weekend_base = int(row["weekend_rate"] * SEASON_MULTIPLIER)
        extra_fee_each = int(row["extra_person_fee_php"])
        guests_for_calc = _guest_count_for_quote(name, req.guests)

        total_estimate = 0
        if nights > 0:
            raw = rate_for_stay_php(name, nights, guests_for_calc)
            total_estimate = int(round(raw * SEASON_MULTIPLIER))

        desc = (cfg.get("description") or "").strip()
        inc = (cfg.get("includes") or "").strip()
        if inc:
            desc = f"{desc} {inc}".strip() if desc else inc

        rates_out.append(
            RateItem(
                room_type=name,
                nightly_rate=nightly_base,
                weekend_rate=weekend_base,
                total_estimate=total_estimate,
                nights=nights,
                max_occupancy=cfg["max_guests"],
                extra_person_fee=extra_fee_each,
                currency=CURRENCY,
                description=desc,
                image_key=name.lower().replace(" ", "-"),
            )
        )

    notes_parts = [
        f"Season multiplier {SEASON_MULTIPLIER} (regular season; no date-based uplift yet).",
        "Extra-person fees apply per billing night when guests exceed the included count (see resort rate table).",
    ]
    if any(ROOM_TYPES[n].get("rate_unit") == "day" for n in room_names):
        notes_parts.append(
            "Full Buyout is priced per day for the stay span; the listed headline rate is the daily buyout rate."
        )

    return RatesResponse(
        rates=rates_out,
        season="regular",
        notes=" ".join(notes_parts),
    )


@app.post("/api/create-booking", response_model=BookingResponse)
async def create_booking(req: BookingRequest) -> BookingResponse:
    d_in, d_out = _validate_stay_dates(req.check_in, req.check_out)
    if req.guests < 1:
        raise HTTPException(status_code=400, detail="guests must be at least 1")

    room_type = req.room_type.strip()
    if room_type not in CALENDAR_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown room_type: {req.room_type}")

    max_guests = ROOM_MAX_OCCUPANCY.get(room_type, 0)
    if req.guests > max_guests:
        raise HTTPException(
            status_code=400,
            detail=f"guests ({req.guests}) exceeds max occupancy ({max_guests}) for {room_type}.",
        )

    if not GOOGLE_SERVICE_ACCOUNT_INFO:
        return BookingResponse(
            success=False,
            booking_ref="",
            guest_name=req.guest_name,
            room_type=room_type,
            check_in=req.check_in,
            check_out=req.check_out,
            nights=0,
            total_estimate=0,
            currency=CURRENCY,
            deposit_deadline=None,
            message="Google Calendar is not configured (service account missing).",
        )

    nights = (d_out - d_in).days
    total = rate_for_stay_php(room_type, nights, req.guests)
    dep_deadline = deposit_deadline_iso()

    try:
        svc = get_calendar_service()
        if not _room_available_for_type(svc, room_type, req.check_in, req.check_out):
            return BookingResponse(
                success=False,
                booking_ref="",
                guest_name=req.guest_name,
                room_type=room_type,
                check_in=req.check_in,
                check_out=req.check_out,
                nights=nights,
                total_estimate=total,
                currency=CURRENCY,
                deposit_deadline=dep_deadline,
                message="Selected room is no longer available for those dates.",
            )

        overlapping = svc.get_total_guests(req.check_in, req.check_out)
        if overlapping + req.guests > PROPERTY_MAX_GUESTS_TOTAL:
            return BookingResponse(
                success=False,
                booking_ref="",
                guest_name=req.guest_name,
                room_type=room_type,
                check_in=req.check_in,
                check_out=req.check_out,
                nights=nights,
                total_estimate=total,
                currency=CURRENCY,
                deposit_deadline=dep_deadline,
                message=(
                    f"Property guest cap exceeded ({PROPERTY_MAX_GUESTS_TOTAL}). "
                    f"Current overlapping guests: {overlapping}."
                ),
            )

        booking_ref = _generate_booking_ref(d_in)
        calendar_id = CALENDAR_MAP[room_type]
        if not str(calendar_id).strip():
            return BookingResponse(
                success=False,
                booking_ref=booking_ref,
                guest_name=req.guest_name,
                room_type=room_type,
                check_in=req.check_in,
                check_out=req.check_out,
                nights=nights,
                total_estimate=total,
                currency=CURRENCY,
                deposit_deadline=dep_deadline,
                message="Calendar ID for this room type is not configured.",
            )

        start_dt, end_dt = stay_window_datetimes(req.check_in, req.check_out)
        summary = f"[PROVISIONAL] {req.guest_name} — {room_type}"
        description = _booking_description(
            booking_ref=booking_ref,
            guest_name=req.guest_name,
            email=req.email,
            phone=req.phone,
            guests=req.guests,
            room_type=room_type,
            nights=nights,
            total=total,
            deposit_deadline=dep_deadline,
            special_requests=req.special_requests,
        )
        svc.create_booking_event(
            calendar_id=str(calendar_id).strip(),
            summary=summary,
            description=description,
            start=start_dt,
            end=end_dt,
        )
    except HttpError as exc:
        return BookingResponse(
            success=False,
            booking_ref="",
            guest_name=req.guest_name,
            room_type=room_type,
            check_in=req.check_in,
            check_out=req.check_out,
            nights=nights,
            total_estimate=total,
            currency=CURRENCY,
            deposit_deadline=dep_deadline,
            message=f"Google Calendar error: {exc}",
        )
    except RuntimeError as exc:
        return BookingResponse(
            success=False,
            booking_ref="",
            guest_name=req.guest_name,
            room_type=room_type,
            check_in=req.check_in,
            check_out=req.check_out,
            nights=nights,
            total_estimate=total,
            currency=CURRENCY,
            deposit_deadline=dep_deadline,
            message=str(exc),
        )

    return BookingResponse(
        success=True,
        booking_ref=booking_ref,
        guest_name=req.guest_name,
        room_type=room_type,
        check_in=req.check_in,
        check_out=req.check_out,
        nights=nights,
        total_estimate=total,
        currency=CURRENCY,
        deposit_deadline=dep_deadline,
        message="Booking created as provisional. Please complete deposit within the deadline.",
    )


@app.post("/api/get-directions", response_model=DirectionsResponse)
async def get_directions(req: DirectionsRequest) -> DirectionsResponse:
    d = DIRECTIONS_DATA
    return DirectionsResponse(
        address=d["address"],
        google_maps_link=d["google_maps_link"],
        directions={
            "from_manila": d["directions"]["from_manila"],
            "from_clark": d["directions"]["from_clark"],
            "from_subic": d["directions"]["from_subic"],
        },
        landmarks=d["landmarks"],
        contact_if_lost=settings.booking_notification_email or "Contact the resort office.",
    )


@app.post("/api/owner/bookings", response_model=OwnerBookingsResponse)
async def owner_get_bookings(req: OwnerBookingsRequest) -> OwnerBookingsResponse:
    query_min, query_max = _owner_range_iso(req.start_date, req.end_date)
    s = _parse_ymd(req.start_date)
    e = _parse_ymd(req.end_date)
    range_start = datetime.combine(s, time(0, 0), tzinfo=MANILA)
    range_end_excl = datetime.combine(e + timedelta(days=1), time(0, 0), tzinfo=MANILA)

    if not GOOGLE_SERVICE_ACCOUNT_INFO:
        return OwnerBookingsResponse(
            start_date=req.start_date,
            end_date=req.end_date,
            bookings=[],
            message="Google Calendar is not configured (service account missing).",
        )

    svc = get_calendar_service()
    seen: set[str] = set()
    items: List[OwnerBookingItem] = []

    for cal_id in (
        settings.google_calendar_family,
        settings.google_calendar_honeymoon,
        settings.google_calendar_events,
    ):
        if not cal_id:
            continue
        try:
            events = svc.list_events(query_min, query_max, cal_id)
        except HttpError as exc:
            return OwnerBookingsResponse(
                start_date=req.start_date,
                end_date=req.end_date,
                bookings=[],
                message=f"Google Calendar error: {exc}",
            )
        for ev in events:
            if not _event_overlaps_owner_range(ev, range_start, range_end_excl):
                continue
            desc = ev.get("description") or ""
            parsed = parse_booking_description(desc)
            if not parsed:
                continue
            ref = str(parsed.get("booking_ref") or "").strip()
            if not ref or ref in seen:
                continue
            seen.add(ref)
            ev_start = _parse_google_datetime(ev, use_end=False)
            ev_end = _parse_google_datetime(ev, use_end=True)
            check_in = ev_start.astimezone(MANILA).date().isoformat() if ev_start else req.start_date
            check_out = ev_end.astimezone(MANILA).date().isoformat() if ev_end else req.end_date
            deposit_status = str(parsed.get("status") or "UNKNOWN").strip()
            items.append(
                OwnerBookingItem(
                    booking_ref=ref,
                    guest_name=str(parsed.get("guest_name") or "").strip() or "Unknown",
                    room_type=str(parsed.get("room") or "").strip() or "Unknown",
                    check_in=check_in,
                    check_out=check_out,
                    deposit_status=deposit_status,
                )
            )

    return OwnerBookingsResponse(
        start_date=req.start_date,
        end_date=req.end_date,
        bookings=items,
        message=f"Found {len(items)} booking(s) across calendars.",
    )


@app.post("/api/owner/block-dates", response_model=OwnerBlockDatesResponse)
async def owner_block_dates(req: BlockDatesRequest) -> OwnerBlockDatesResponse:
    _parse_ymd(req.start_date)
    _parse_ymd(req.end_date)
    if not GOOGLE_SERVICE_ACCOUNT_INFO:
        return OwnerBlockDatesResponse(
            success=False,
            start_date=req.start_date,
            end_date=req.end_date,
            reason=req.reason,
            message="Google Calendar is not configured (service account missing).",
        )
    try:
        svc = get_calendar_service()
        svc.create_block_event(req.start_date, req.end_date, req.reason)
    except (HttpError, RuntimeError, ValueError) as exc:
        return OwnerBlockDatesResponse(
            success=False,
            start_date=req.start_date,
            end_date=req.end_date,
            reason=req.reason,
            message=str(exc),
        )
    return OwnerBlockDatesResponse(
        success=True,
        start_date=req.start_date,
        end_date=req.end_date,
        reason=req.reason,
        message="Blocking events created on all configured calendars.",
    )


@app.post("/api/owner/occupancy", response_model=OwnerOccupancyResponse)
async def owner_get_occupancy(req: OccupancyRequest) -> OwnerOccupancyResponse:
    if req.month < 1 or req.month > 12:
        raise HTTPException(status_code=400, detail="month must be 1-12")

    if not GOOGLE_SERVICE_ACCOUNT_INFO:
        return OwnerOccupancyResponse(
            month=req.month,
            year=req.year,
            occupancy_percentage=0.0,
            weekly_breakdown=[],
            revenue_estimate=0,
            currency=CURRENCY,
            message="Google Calendar is not configured (service account missing).",
        )

    try:
        svc = get_calendar_service()
        suite_pct, buyout_msg, weeks_raw, revenue = compute_suite_buyout_occupancy(svc, req.year, req.month)
    except HttpError as exc:
        return OwnerOccupancyResponse(
            month=req.month,
            year=req.year,
            occupancy_percentage=0.0,
            weekly_breakdown=[],
            revenue_estimate=0,
            currency=CURRENCY,
            message=f"Google Calendar error: {exc}",
        )

    weeks = [OccupancyWeekBreakdown(**row) for row in weeks_raw]
    return OwnerOccupancyResponse(
        month=req.month,
        year=req.year,
        occupancy_percentage=suite_pct,
        weekly_breakdown=weeks,
        revenue_estimate=revenue,
        currency=CURRENCY,
        message=(
            f"Suite occupancy (Family + Honeymoon nights vs 2 rooms × days in month): {suite_pct}%. "
            f"{buyout_msg}"
        ),
    )
