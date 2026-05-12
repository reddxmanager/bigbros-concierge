from __future__ import annotations

import calendar
import logging
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import CALENDAR_MAP, GOOGLE_SERVICE_ACCOUNT_INFO, settings

logger = logging.getLogger(__name__)

MANILA = ZoneInfo("Asia/Manila")
SCOPES = ["https://www.googleapis.com/auth/calendar"]

ROOM_FAMILY = "Family Suite"
ROOM_HONEYMOON = "Honeymoon Suite"
ROOM_BUYOUT = "Full Buyout"

SUITE_ROOMS = (ROOM_FAMILY, ROOM_HONEYMOON)


def _calendar_ids_all() -> List[str]:
    return [
        settings.google_calendar_family,
        settings.google_calendar_honeymoon,
        settings.google_calendar_events,
    ]


def _calendar_id_for_room(room_type: str) -> Optional[str]:
    cid = CALENDAR_MAP.get(room_type)
    if not cid or not str(cid).strip():
        return None
    return str(cid).strip()


def _has_credentials() -> bool:
    return GOOGLE_SERVICE_ACCOUNT_INFO is not None


class CalendarService:
    def __init__(self) -> None:
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service
        if not _has_credentials():
            raise RuntimeError("Google Calendar service account is not configured.")
        creds = service_account.Credentials.from_service_account_info(
            GOOGLE_SERVICE_ACCOUNT_INFO,
            scopes=SCOPES,
        )
        self._service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def _list_event_items(
        self,
        calendar_id: str,
        time_min_rfc3339: str,
        time_max_rfc3339: str,
    ) -> List[dict]:
        if not calendar_id:
            return []
        svc = self._get_service()
        items: List[dict] = []
        page_token: Optional[str] = None
        while True:
            resp = (
                svc.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min_rfc3339,
                    timeMax=time_max_rfc3339,
                    singleEvents=True,
                    orderBy="startTime",
                    pageToken=page_token,
                    maxResults=2500,
                )
                .execute()
            )
            items.extend(resp.get("items", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return items

    def list_events(self, time_min: str, time_max: str, calendar_id: str) -> List[dict]:
        """
        List non-cancelled events on a calendar overlapping [time_min, time_max) query window.
        time_min / time_max: RFC3339 strings with offset (e.g. +08:00).
        """
        if not calendar_id or not _has_credentials():
            return []
        try:
            items = self._list_event_items(calendar_id, time_min, time_max)
        except HttpError as exc:
            logger.exception("Calendar list failed: %s", exc)
            raise
        return [e for e in items if e.get("status") != "cancelled"]

    def check_availability(self, check_in: str, check_out: str, calendar_id: str) -> bool:
        """
        True if there are no blocking/booking events overlapping the stay window
        [check_in 14:00, check_out 12:00) Asia/Manila.
        """
        if not calendar_id or not _has_credentials():
            return False
        stay_start, stay_end = stay_window_datetimes(check_in, check_out)
        if stay_end <= stay_start:
            return False
        time_min = (stay_start - timedelta(days=1)).isoformat()
        time_max = (stay_end + timedelta(days=1)).isoformat()
        events = self.list_events(time_min, time_max, calendar_id)
        for ev in events:
            if _event_overlaps_stay(ev, stay_start, stay_end):
                return False
        return True

    def check_all_availability(self, check_in: str, check_out: str) -> Dict[str, bool]:
        """
        Per room type availability.
        Full Buyout is available only if ALL three calendars are empty for the window.
        """
        out: Dict[str, bool] = {}
        fam = _calendar_id_for_room(ROOM_FAMILY)
        hon = _calendar_id_for_room(ROOM_HONEYMOON)
        evs = _calendar_id_for_room(ROOM_BUYOUT)

        out[ROOM_FAMILY] = self.check_availability(check_in, check_out, fam or "")
        out[ROOM_HONEYMOON] = self.check_availability(check_in, check_out, hon or "")
        buyout_ok = (
            self.check_availability(check_in, check_out, fam or "")
            and self.check_availability(check_in, check_out, hon or "")
            and self.check_availability(check_in, check_out, evs or "")
        )
        out[ROOM_BUYOUT] = buyout_ok
        return out

    def get_total_guests(self, check_in: str, check_out: str) -> int:
        """
        Sum of Guests: values from booking-like events across all calendars overlapping the stay window.
        """
        if not _has_credentials():
            return 0
        stay_start, stay_end = stay_window_datetimes(check_in, check_out)
        if stay_end <= stay_start:
            return 0
        time_min = (stay_start - timedelta(days=1)).isoformat()
        time_max = (stay_end + timedelta(days=1)).isoformat()
        total = 0
        seen_refs: set[str] = set()
        for cal_id in _calendar_ids_all():
            if not cal_id:
                continue
            try:
                events = self.list_events(time_min, time_max, cal_id)
            except HttpError:
                raise
            for ev in events:
                if not _event_overlaps_stay(ev, stay_start, stay_end):
                    continue
                desc = ev.get("description") or ""
                parsed = parse_booking_description(desc)
                if not parsed:
                    continue
                ref = parsed.get("booking_ref") or ev.get("id", "")
                if ref in seen_refs:
                    continue
                seen_refs.add(ref)
                try:
                    total += int(parsed.get("guests") or 0)
                except (TypeError, ValueError):
                    continue
        return total

    def create_booking_event(
        self,
        calendar_id: str,
        summary: str,
        description: str,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        if not calendar_id:
            raise ValueError("calendar_id is required")
        svc = self._get_service()
        body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Manila"},
            "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Manila"},
        }
        created = svc.events().insert(calendarId=calendar_id, body=body).execute()
        return {"event_id": created.get("id"), "html_link": created.get("htmlLink")}

    def create_block_event(self, start: str, end: str, reason: str) -> Dict[str, Any]:
        """
        Create an all-day block on ALL configured calendars.
        start/end: YYYY-MM-DD (inclusive start, inclusive end for the owner request).
        Google all-day end date is exclusive, so we use end_exclusive = end_date + 1 day.
        """
        d0 = date.fromisoformat(start)
        d1 = date.fromisoformat(end)
        if d1 < d0:
            raise ValueError("end must be on or after start")
        end_exclusive = d1 + timedelta(days=1)
        body = {
            "summary": f"[BLOCKED] {reason}",
            "start": {"date": d0.isoformat(), "timeZone": "Asia/Manila"},
            "end": {"date": end_exclusive.isoformat(), "timeZone": "Asia/Manila"},
        }
        svc = self._get_service()
        created_ids: Dict[str, str] = {}
        for cal_id in _calendar_ids_all():
            if not cal_id:
                continue
            created = svc.events().insert(calendarId=cal_id, body=body).execute()
            created_ids[cal_id] = created.get("id", "")
        return {"calendar_event_ids": created_ids}


def get_calendar_service() -> CalendarService:
    return CalendarService()


def stay_window_datetimes(check_in: str, check_out: str) -> Tuple[datetime, datetime]:
    tz = MANILA
    d_in = date.fromisoformat(check_in)
    d_out = date.fromisoformat(check_out)
    start = datetime.combine(d_in, time(14, 0), tzinfo=tz)
    end = datetime.combine(d_out, time(12, 0), tzinfo=tz)
    return start, end


def deposit_deadline_iso() -> str:
    dt = datetime.now(MANILA) + timedelta(hours=48)
    return dt.isoformat()


def _parse_google_datetime(event: dict, use_end: bool) -> Optional[datetime]:
    key = "end" if use_end else "start"
    block = event.get(key) or {}
    if "dateTime" in block:
        raw = block["dateTime"]
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=MANILA)
        return dt.astimezone(MANILA)
    if "date" in block:
        d = date.fromisoformat(block["date"])
        if use_end:
            # exclusive end date for all-day -> convert to last instant of previous day start+0?
            # For all-day end "2026-01-05", exclusive means event ends at start of 2026-01-05 00:00 Manila
            return datetime.combine(d, time(0, 0), tzinfo=MANILA)
        return datetime.combine(d, time(0, 0), tzinfo=MANILA)
    return None


def _event_overlaps_stay(event: dict, stay_start: datetime, stay_end: datetime) -> bool:
    ev_start = _parse_google_datetime(event, use_end=False)
    ev_end = _parse_google_datetime(event, use_end=True)
    if ev_start is None or ev_end is None:
        return False
    # All-day end is exclusive date at midnight; treat as interval [ev_start, ev_end)
    if "date" in (event.get("start") or {}) and "date" in (event.get("end") or {}):
        # start at beginning of start date; end exclusive already at midnight of end.date
        if ev_end <= ev_start:
            ev_end = ev_start + timedelta(days=1)
    # Standard overlap on half-open [stay_start, stay_end)
    return ev_start < stay_end and ev_end > stay_start


def parse_booking_description(description: str) -> Optional[Dict[str, Any]]:
    if not description or not description.strip():
        return None
    text = description.replace("\r\n", "\n")
    if "Booking Ref:" not in text:
        return None
    data: Dict[str, Any] = {}
    patterns = {
        "booking_ref": re.compile(r"^Booking Ref:\s*(.+)$", re.MULTILINE),
        "guest_name": re.compile(r"^Guest:\s*(.+)$", re.MULTILINE),
        "email": re.compile(r"^Email:\s*(.+)$", re.MULTILINE),
        "phone": re.compile(r"^Phone:\s*(.+)$", re.MULTILINE),
        "guests": re.compile(r"^Guests:\s*(\d+)\s*$", re.MULTILINE),
        "room": re.compile(r"^Room:\s*(.+)$", re.MULTILINE),
        "nights": re.compile(r"^Nights:\s*(\d+)\s*$", re.MULTILINE),
        "estimated_total": re.compile(r"^Estimated Total:\s*(.+)$", re.MULTILINE),
        "status": re.compile(r"^Status:\s*(.+)$", re.MULTILINE),
        "deposit_deadline": re.compile(r"^Deposit Deadline:\s*(.+)$", re.MULTILINE),
        "special_requests": re.compile(r"^Special Requests:\s*(.+)$", re.MULTILINE),
    }
    for key, rx in patterns.items():
        m = rx.search(text)
        if not m:
            continue
        val = m.group(1).strip()
        if key == "guests":
            try:
                data[key] = int(val)
            except ValueError:
                data[key] = 0
        elif key == "nights":
            try:
                data[key] = int(val)
            except ValueError:
                data[key] = 0
        else:
            data[key] = val
    if "booking_ref" not in data:
        return None
    return data


def _month_bounds(year: int, month: int) -> Tuple[datetime, datetime]:
    first = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)
    start = datetime.combine(first, time(0, 0), tzinfo=MANILA)
    end = datetime.combine(last, time(23, 59, 59), tzinfo=MANILA) + timedelta(seconds=1)
    return start, end


def _daterange_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _event_nights_spanning_month(
    ev_start: datetime,
    ev_end: datetime,
    year: int,
    month: int,
) -> int:
    month_first = date(year, month, 1)
    month_last = date(year, month, calendar.monthrange(year, month)[1])
    stay_start_d = ev_start.astimezone(MANILA).date()
    stay_end_d = ev_end.astimezone(MANILA).date()
    nights = max(0, (stay_end_d - stay_start_d).days)
    if nights == 0:
        return 0
    counted = 0
    for i in range(nights):
        night_anchor = stay_start_d + timedelta(days=i)
        if month_first <= night_anchor <= month_last:
            counted += 1
    return counted


def compute_suite_buyout_occupancy(
    calendar: CalendarService,
    year: int,
    month: int,
) -> Tuple[float, str, List[Dict[str, Any]], int]:
    """
    Returns (suite_occupancy_pct, buyout_message, weekly_breakdown, revenue_estimate)
    suite occupancy = booked_suite_room_nights / (2 * days_in_month)
    Buyouts counted separately (message only).
    """
    days_in_month = _daterange_in_month(year, month)
    if days_in_month <= 0:
        return 0.0, "", [], 0

    month_start, month_end = _month_bounds(year, month)
    query_min = (month_start - timedelta(days=1)).isoformat()
    query_max = (month_end + timedelta(days=1)).isoformat()

    suite_nights = 0
    buyout_days_in_month = 0
    revenue = 0

    if not _has_credentials():
        weeks = _weekly_suite_occupancy_empty(year, month, days_in_month)
        return 0.0, "Calendar credentials not configured.", weeks, 0

    def collect_for_calendar(cal_id: str, room_filter: Optional[str]) -> None:
        nonlocal suite_nights, buyout_days_in_month, revenue
        if not cal_id:
            return
        try:
            events = calendar.list_events(query_min, query_max, cal_id)
        except HttpError:
            raise
        for ev in events:
            desc = ev.get("description") or ""
            parsed = parse_booking_description(desc)
            if not parsed:
                continue
            room = (parsed.get("room") or "").strip()
            ev_start = _parse_google_datetime(ev, use_end=False)
            ev_end = _parse_google_datetime(ev, use_end=True)
            if ev_start is None or ev_end is None:
                continue
            if not (ev_start < month_end and ev_end > month_start):
                continue
            total_field = parsed.get("estimated_total") or ""
            rev = _parse_money_php(total_field)

            if cal_id == settings.google_calendar_events:
                if room == ROOM_BUYOUT:
                    buyout_days_in_month += _buyout_days_in_month(ev_start, ev_end, year, month)
                    revenue += rev
                continue

            if room_filter and room != room_filter:
                continue
            if room not in SUITE_ROOMS:
                continue
            revenue += rev
            suite_nights += _event_nights_spanning_month(ev_start, ev_end, year, month)

    fam = settings.google_calendar_family
    hon = settings.google_calendar_honeymoon
    evs = settings.google_calendar_events

    collect_for_calendar(fam, ROOM_FAMILY)
    collect_for_calendar(hon, ROOM_HONEYMOON)
    collect_for_calendar(evs, None)

    denom = 2 * days_in_month
    suite_pct = (suite_nights / denom * 100.0) if denom else 0.0
    buyout_msg = (
        f"Buyout property-days overlapping this month (events calendar): {buyout_days_in_month}."
        if buyout_days_in_month
        else "No buyout bookings counted on the events calendar for this month."
    )
    weeks = _weekly_breakdown_suite(calendar, year, month, days_in_month)
    return round(suite_pct, 2), buyout_msg, weeks, revenue


def _buyout_days_in_month(ev_start: datetime, ev_end: datetime, year: int, month: int) -> int:
    month_first = date(year, month, 1)
    month_last = date(year, month, calendar.monthrange(year, month)[1])
    d0 = max(ev_start.astimezone(MANILA).date(), month_first)
    d1 = min((ev_end.astimezone(MANILA) - timedelta(seconds=1)).date(), month_last)
    if d1 < d0:
        return 0
    return (d1 - d0).days + 1


def _parse_money_php(text: str) -> int:
    if not text:
        return 0
    digits = re.sub(r"[^\d]", "", text)
    try:
        return int(digits) if digits else 0
    except ValueError:
        return 0


def _weekly_suite_occupancy_empty(year: int, month: int, days_in_month: int) -> List[Dict[str, Any]]:
    return _weekly_breakdown_suite(None, year, month, days_in_month)


def _weekly_breakdown_suite(
    calendar: Optional[CalendarService],
    year: int,
    month: int,
    days_in_month: int,
) -> List[Dict[str, Any]]:
    """
    Seven-day chunks from the first of the month (partial last chunk allowed).
    Suite occupancy % = suite room-nights in chunk / (2 * days_in_chunk).
    """
    breakdown: List[Dict[str, Any]] = []
    month_start, month_end = _month_bounds(year, month)
    day_cursor = 1
    chunk_idx = 1
    while day_cursor <= days_in_month:
        chunk_start = date(year, month, day_cursor)
        chunk_end = date(year, month, min(day_cursor + 6, days_in_month))
        days_in_chunk = (chunk_end - chunk_start).days + 1
        suite_nights = 0
        if calendar and _has_credentials():
            query_min = (datetime.combine(chunk_start, time(0, 0), tzinfo=MANILA) - timedelta(days=1)).isoformat()
            query_max = (datetime.combine(chunk_end, time(23, 59, 59), tzinfo=MANILA) + timedelta(days=2)).isoformat()
            for cal_id, room_name in (
                (settings.google_calendar_family, ROOM_FAMILY),
                (settings.google_calendar_honeymoon, ROOM_HONEYMOON),
            ):
                if not cal_id:
                    continue
                try:
                    events = calendar.list_events(query_min, query_max, cal_id)
                except HttpError:
                    events = []
                for ev in events:
                    desc = ev.get("description") or ""
                    parsed = parse_booking_description(desc)
                    if not parsed:
                        continue
                    room = (parsed.get("room") or "").strip()
                    if room != room_name:
                        continue
                    ev_start = _parse_google_datetime(ev, use_end=False)
                    ev_end = _parse_google_datetime(ev, use_end=True)
                    if ev_start is None or ev_end is None:
                        continue
                    if not (ev_start < month_end and ev_end > month_start):
                        continue
                    suite_nights += _nights_in_date_range_for_week(
                        ev_start, ev_end, chunk_start, chunk_end, year, month
                    )
        denom = 2 * days_in_chunk
        pct = (suite_nights / denom * 100.0) if denom else 0.0
        breakdown.append(
            {
                "week_label": f"{year}-{month:02d} chunk {chunk_idx} ({chunk_start.isoformat()}–{chunk_end.isoformat()})",
                "occupancy_percentage": round(pct, 2),
            }
        )
        chunk_idx += 1
        day_cursor += 7
    return breakdown


def _nights_in_date_range_for_week(
    ev_start: datetime,
    ev_end: datetime,
    week_start: date,
    week_end: date,
    year: int,
    month: int,
) -> int:
    month_first = date(year, month, 1)
    month_last = date(year, month, calendar.monthrange(year, month)[1])
    stay_start_d = ev_start.astimezone(MANILA).date()
    stay_end_d = ev_end.astimezone(MANILA).date()
    nights = max(0, (stay_end_d - stay_start_d).days)
    counted = 0
    for i in range(nights):
        night_anchor = stay_start_d + timedelta(days=i)
        if month_first <= night_anchor <= month_last and week_start <= night_anchor <= week_end:
            counted += 1
    return counted
