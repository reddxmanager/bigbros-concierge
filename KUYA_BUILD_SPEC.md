# KUYA — Voice Concierge for Big Bros White Sand Resort
## ElevenHacks #8: Cursor x ElevenLabs — Complete Build Specification

**Project:** Kuya, a voice AI concierge that brings the Big Bros resort website to life
**Hackathon:** ElevenHacks #8 — "Build something you can use without ever touching a keyboard"
**Deadline:** Thursday, May 14, 2026 @ 17:00 UTC (6 days from now)
**Repo:** `bigbros-concierge`
**Deploy target:** bigbroswhitesand.com (Netlify) + backend on Railway/Render

---

## The Pitch

"I own a beach resort in the Philippines. Every day I answer the same questions...
rates, availability, directions. So I built Kuya."

Kuya is the resort's voice concierge. He lives on the website. Guests talk to him
and the entire page comes alive... the calendar lights up with available dates,
room cards flip to show what's open, and a booking confirmation slides in when
they're ready. No keyboard. No forms. Just a conversation.

And when I need to check bookings or block off dates? I talk to Kuya too.
He's got an owner mode. Same voice, different brain.

Built with Cursor and ElevenLabs in under a week. Now he runs my resort 24/7
while I'm at the beach.

---

## Table of Contents

1. [Architecture](#1-architecture)
2. [Kuya's Personality](#2-kuyas-personality)
3. [The Reactive Website (Client Tools)](#3-the-reactive-website)
4. [Server Tools (Backend Webhooks)](#4-server-tools)
5. [Owner Mode](#5-owner-mode)
6. [Knowledge Base](#6-knowledge-base)
7. [Frontend Component Spec](#7-frontend-component-spec)
8. [Backend API Spec](#8-backend-api-spec)
9. [Google Calendar Integration](#9-google-calendar-integration)
10. [Multilingual Support](#10-multilingual-support)
11. [Build Sequence](#11-build-sequence)
12. [Video Strategy](#12-video-strategy)
13. [File Structure](#13-file-structure)
14. [Environment Variables](#14-environment-variables)
15. [Submission Checklist](#15-submission-checklist)

---

## 1. Architecture

```
GUEST (voice)
    ?
    ?
???????????????????????????????????????????????????????????????
?  bigbroswhitesand.com  (React on Netlify)                   ?
?                                                             ?
?  ???????????????????????????????????????????????????????    ?
?  ?              REACTIVE UI LAYER                      ?    ?
?  ?                                                     ?    ?
?  ?   ????????????  ????????????  ?????????????????    ?    ?
?  ?   ? Calendar  ?  ? Room     ?  ? Booking       ?    ?    ?
?  ?   ? (dates   ?  ? Cards    ?  ? Confirmation  ?    ?    ?
?  ?   ?  glow)   ?  ? (flip/   ?  ? (slide-in     ?    ?    ?
?  ?   ?          ?  ?  fade)   ?  ?  card)        ?    ?    ?
?  ?   ????????????  ????????????  ?????????????????    ?    ?
?  ?                                                     ?    ?
?  ???????????????????????????????????????????????????????    ?
?                       ? client tool callbacks                ?
?  ???????????????????????????????????????????????????????    ?
?  ?  ElevenLabs Widget  (@elevenlabs/react SDK)         ?    ?
?  ?  useConversation() hook with clientTools             ?    ?
?  ???????????????????????????????????????????????????????    ?
???????????????????????????????????????????????????????????????
                        ? WebRTC
                        ?
???????????????????????????????????????????????????????????????
?  ElevenLabs Platform                                        ?
?  - Agent: "Kuya" (system prompt + voice + LLM)              ?
?  - Client Tools: highlight_dates, show_rooms,               ?
?                   show_booking_confirmation, show_directions ?
?  - Server Tools: check_availability, get_rates,             ?
?                   create_booking, get_directions             ?
?  - Knowledge Base: resort FAQ document                      ?
???????????????????????????????????????????????????????????????
                       ? HTTP webhooks
                       ?
???????????????????????????????????????????????????????????????
?  FastAPI Backend  (Railway / Render)                         ?
?  POST /api/check-availability  ?  Google Calendar query      ?
?  POST /api/get-rates           ?  rate table lookup          ?
?  POST /api/create-booking      ?  Google Calendar event      ?
?  POST /api/get-directions      ?  static data + maps link   ?
?  POST /api/owner/bookings      ?  Google Calendar query      ?
?  POST /api/owner/block-dates   ?  Google Calendar event      ?
?  POST /api/owner/occupancy     ?  Google Calendar aggregate  ?
???????????????????????????????????????????????????????????????
```

The key insight: ElevenLabs agents support TWO types of tools simultaneously.
**Server tools** hit your backend via webhooks (for data).
**Client tools** fire JavaScript in the browser (for UI).

The agent calls a server tool to GET data, then calls a client tool to SHOW it.
That's how the website comes alive during the conversation.

---

## 2. Kuya's Personality

### Name Origin
"Kuya" means "older brother" in Filipino. Big Bros White Sand Resort. He IS
the big brother.

### Voice Selection
Browse ElevenLabs voice library for:
- Male voice, warm and natural
- Slight accent is a plus (not mandatory, but adds character)
- Conversational pace, not robotic or overly polished
- Test with phrases like "Ay, that weekend is popular!" and
  "Let me check that for you real quick"

Alternatively: clone a custom voice if time allows.

### System Prompt (Guest Mode)

```
You are Kuya, the voice concierge for Big Bros White Sand Resort — a boutique
beach resort in Zambales, Philippines.

YOUR NAME:
- Your name is Kuya. If asked, explain it means "older brother" in Filipino,
  and Big Bros is your home.

YOUR PERSONALITY:
- Warm and genuinely welcoming — like a Filipino host greeting family at the door
- Conversational, not corporate. You can laugh, express surprise, show enthusiasm
- Concise but thorough. Answer the question, offer one natural follow-up
- You occasionally drop casual Filipino phrases naturally:
  "Ay, that weekend's packed!" / "Sobrang ganda ng beach that time of year"
  "Sige, let me check that for you"
  But don't overdo it — you're bilingual, not performing
- If someone speaks Tagalog, switch naturally. Don't announce it
- If you genuinely don't know something, say so and offer to take a message
  for the owners
- You love the resort. You know the best time to see the sunset (5:30 PM from
  the pool area), the quietest stretch of beach (far left past the rocks),
  and which room has the best view

WHAT YOU CAN DO:
1. Answer questions about the resort (use your knowledge base)
2. Check availability for specific dates (ALWAYS use check_availability tool)
3. Quote rates (ALWAYS use get_rates tool — never guess prices)
4. Book rooms (use create_booking after collecting all required info)
5. Give directions (use get_directions tool)
6. Make the website react to the conversation (use client tools to animate UI)

CONVERSATION FLOW FOR BOOKINGS:
1. Guest expresses interest in staying
2. Ask for preferred dates — "When were you thinking of visiting?"
3. Ask about group size — "How many guests?"
4. Call check_availability ? then call highlight_dates to show it on the calendar
5. If available, call get_rates ? then call show_rooms to display options
6. If they want to proceed, collect: full name, email, phone
7. Call create_booking ? then call show_booking_confirmation with the details
8. Confirm verbally: "You're all set! Check your email for the details"
9. Let them know the booking is provisional until deposit is confirmed

CLIENT TOOL USAGE (CRITICAL):
After receiving data from a server tool, ALWAYS call the matching client tool
to update the website visually:
- After check_availability ? call highlight_dates
- After get_rates ? call show_rooms
- After create_booking ? call show_booking_confirmation
- After get_directions ? call show_directions
This is what makes the experience magical — the page reacts to the conversation.

RULES:
- All rates are in Philippine Pesos (PHP)
- Minimum stay: 1 night
- Check-in: 2:00 PM / Check-out: 12:00 PM (noon)
- You CANNOT process payments. Bookings are provisional until deposit is sent
- NEVER invent availability or rates. If a tool call fails, say
  "I'm having a little trouble checking that right now. Want me to take
  your details and have the owners reach out?"
- Keep responses under 3 sentences when possible. Voice conversations need brevity
- Don't list amenities unprompted. Mention them naturally when relevant
```

---

## 3. The Reactive Website

This is the WOW factor. The website isn't a static page with a chatbot bubble.
It's a living interface that responds to Kuya's conversation.

### Client Tools (registered via @elevenlabs/react SDK)

Client tools are defined in the React app and executed locally in the browser.
They receive data from the conversation and trigger UI state changes.

#### Client Tool: `highlight_dates`

**Triggered after:** `check_availability` server tool returns data
**Purpose:** Animate the calendar component to show available/unavailable dates

```javascript
// Registered in useConversation() clientTools
highlight_dates: async ({ check_in, check_out, available_dates, unavailable_dates }) => {
  // Update React state ? calendar component re-renders
  setCalendarHighlights({
    checkIn: check_in,
    checkOut: check_out,
    available: available_dates,    // green glow
    unavailable: unavailable_dates // red/dimmed
  });
  setActiveSection('calendar'); // scroll calendar into view
  return "Dates are now highlighted on the calendar.";
}
```

**Visual behavior:**
- Calendar scrolls into viewport with smooth animation
- Available dates pulse with a soft green glow
- Requested date range gets a highlighted band
- Unavailable dates dim to gray
- Transition: 400ms ease-out, staggered per date cell

---

#### Client Tool: `show_rooms`

**Triggered after:** `get_rates` server tool returns data
**Purpose:** Display available room cards with pricing

```javascript
show_rooms: async ({ rooms }) => {
  // rooms = [{ type, rate, max_occupancy, description, image_key }]
  setAvailableRooms(rooms);
  setActiveSection('rooms'); // scroll room cards into view
  return "Room options are now displayed.";
}
```

**Visual behavior:**
- Room cards animate in with a staggered fade-up (100ms delay between cards)
- Each card shows: room photo, type name, rate per night, max occupancy
- Available rooms have a subtle breathing border glow
- Cards are tappable (for accessibility) but voice is primary

---

#### Client Tool: `show_booking_confirmation`

**Triggered after:** `create_booking` server tool returns success
**Purpose:** Slide in a confirmation card with booking details

```javascript
show_booking_confirmation: async ({ booking_ref, guest_name, room_type,
                                      check_in, check_out, nights,
                                      total_estimate, currency }) => {
  setBookingConfirmation({
    ref: booking_ref,
    name: guest_name,
    room: room_type,
    checkIn: check_in,
    checkOut: check_out,
    nights: nights,
    total: total_estimate,
    currency: currency
  });
  setActiveSection('confirmation');
  return "Booking confirmation is displayed.";
}
```

**Visual behavior:**
- Card slides in from the right with a spring animation
- Subtle confetti or sparkle effect on arrival (celebratory, not cheesy)
- Displays: booking ref, guest name, dates, room type, total estimate
- "Provisional — deposit required within 48 hours" note at bottom
- Check mark animation on the booking ref

---

#### Client Tool: `show_directions`

**Triggered after:** `get_directions` server tool returns data
**Purpose:** Show a directions panel with travel info and map link

```javascript
show_directions: async ({ address, google_maps_link, directions, landmarks }) => {
  setDirectionsData({ address, mapLink: google_maps_link, directions, landmarks });
  setActiveSection('directions');
  return "Directions are now displayed on the page.";
}
```

**Visual behavior:**
- Directions panel slides up from bottom
- Shows route options (from Manila, from Clark, from Subic)
- "Open in Google Maps" button (tappable, important for mobile)
- Landmark hints for the final stretch

---

### UI State Machine

The page has an `activeSection` state that controls what's prominently displayed:

```
idle ? calendar ? rooms ? confirmation
                        ? directions (can branch at any point)
```

Each section transition uses smooth scroll + fade animation. Previous sections
don't disappear — they compress/minimize so the guest can still see the full
conversation trail of information. The active section is largest and most prominent.

---

## 4. Server Tools

These are configured in the ElevenLabs Dashboard as webhooks pointing to your
FastAPI backend. The agent calls these to GET data, then calls client tools to SHOW it.

### Tool: `check_availability`

**ElevenLabs Dashboard Config:**
- Name: `check_availability`
- Type: Webhook
- Method: POST
- URL: `{BACKEND_URL}/api/check-availability`
- Description: "Check if the resort has rooms available for specific dates and
  guest count. Always call this when a guest asks about availability or wants
  to book. After getting results, call the highlight_dates client tool to
  update the website calendar."

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| check_in | string | yes | Check-in date, YYYY-MM-DD |
| check_out | string | yes | Check-out date, YYYY-MM-DD |
| guests | integer | yes | Number of guests |

**Response Schema:**
```json
{
  "available": true,
  "check_in": "2026-05-22",
  "check_out": "2026-05-24",
  "available_dates": ["2026-05-22", "2026-05-23"],
  "unavailable_dates": [],
  "rooms": [
    {
      "room_type": "Standard Room",
      "available_count": 2,
      "max_occupancy": 4
    }
  ],
  "message": "2 Standard Rooms available for May 22-24"
}
```

---

### Tool: `get_rates`

**ElevenLabs Dashboard Config:**
- Name: `get_rates`
- Type: Webhook
- Method: POST
- URL: `{BACKEND_URL}/api/get-rates`
- Description: "Get nightly rates for available rooms. Call after confirming
  availability. After getting results, call the show_rooms client tool to
  display room options on the website."

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| check_in | string | no | For seasonal pricing calculation |
| check_out | string | no | For total estimate calculation |
| room_type | string | no | Filter to specific room type |
| guests | integer | no | To flag extra person fees |

**Response Schema:**
```json
{
  "rates": [
    {
      "room_type": "Standard Room",
      "nightly_rate": 3500,
      "weekend_rate": 4500,
      "total_estimate": 8000,
      "nights": 2,
      "max_occupancy": 4,
      "extra_person_fee": 500,
      "currency": "PHP",
      "description": "Cozy room with queen bed, AC, private bathroom",
      "image_key": "standard"
    }
  ],
  "season": "regular",
  "notes": "Weekend rates apply Fri-Sat nights. Extra person fee beyond 2 guests."
}
```

---

### Tool: `create_booking`

**ElevenLabs Dashboard Config:**
- Name: `create_booking`
- Type: Webhook
- Method: POST
- URL: `{BACKEND_URL}/api/create-booking`
- Description: "Create a provisional booking. Only call after: (1) confirming
  availability, (2) quoting rates, and (3) collecting guest name, email, phone,
  preferred dates, guest count, and room type. After success, call the
  show_booking_confirmation client tool."

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| guest_name | string | yes | Full name |
| email | string | yes | Email address |
| phone | string | yes | Phone number |
| check_in | string | yes | YYYY-MM-DD |
| check_out | string | yes | YYYY-MM-DD |
| guests | integer | yes | Number of guests |
| room_type | string | yes | Room type |
| special_requests | string | no | Any special requests |

**Response Schema:**
```json
{
  "success": true,
  "booking_ref": "BB-20260522-X7K9",
  "guest_name": "Juan Dela Cruz",
  "room_type": "Standard Room",
  "check_in": "2026-05-22",
  "check_out": "2026-05-24",
  "nights": 2,
  "total_estimate": 8000,
  "currency": "PHP",
  "deposit_deadline": "2026-05-10T14:00:00+08:00",
  "message": "Provisional booking created. Confirmation email sent."
}
```

---

### Tool: `get_directions`

**ElevenLabs Dashboard Config:**
- Name: `get_directions`
- Type: Webhook
- Method: POST
- URL: `{BACKEND_URL}/api/get-directions`
- Description: "Provide travel directions to the resort. Call when guests ask
  how to get there. After getting results, call the show_directions client tool."

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| from_location | string | no | Starting point (Manila, Clark, Subic, etc.) |

**Response Schema:**
```json
{
  "address": "Big Bros White Sand Resort, [full address], Zambales",
  "google_maps_link": "https://maps.google.com/?q=...",
  "directions": {
    "from_manila": "Via SCTEX/TPLEX to Subic, then coastal road north. 3-4 hours.",
    "from_clark": "Via SCTEX to Subic exit. About 2 hours.",
    "from_subic": "Coastal road north, approximately 45 minutes."
  },
  "landmarks": "Look for [landmark]. We're on the left side.",
  "contact_if_lost": "+63 XXX XXX XXXX"
}
```

---

## 5. Owner Mode

A separate ElevenLabs agent (or same agent with a different URL/config) that
gives Red management capabilities via voice.

### Access
- Separate page: `bigbroswhitesand.com/kuya-owner` (not linked publicly)
- Same Kuya voice, different system prompt
- Could also use ElevenLabs agent authentication if available

### Owner System Prompt

```
You are Kuya in owner mode. You're speaking with the resort owner (Red) or
his wife. You're the same warm Kuya, but now you're the resort manager
reporting to the boss.

WHAT YOU CAN DO:
1. Report upcoming bookings — "What do we have this weekend?"
2. Report occupancy — "How's May looking?"
3. Block dates for private events — "Block June 1 to 3"
4. Check specific bookings — "Any bookings for the 15th?"

TOOLS AVAILABLE:
- get_upcoming_bookings: fetch bookings for a date range
- get_occupancy: calculate occupancy percentage for a period
- block_dates: create a blocking event on the calendar
- get_booking_details: look up a specific booking

PERSONALITY:
- More casual with Red. "Boss, you've got three bookings this weekend"
- Report numbers clearly — dates, names, room types
- If occupancy is high, be excited about it. "May is looking solid, 80% booked"
- If something needs attention, flag it. "Heads up, you've got two provisionals
  that haven't sent deposits yet"
```

### Owner Server Tools

#### `get_upcoming_bookings`
- POST `{BACKEND_URL}/api/owner/bookings`
- Params: `start_date`, `end_date`
- Returns: list of bookings with guest names, room types, dates, deposit status

#### `block_dates`
- POST `{BACKEND_URL}/api/owner/block-dates`
- Params: `start_date`, `end_date`, `reason`
- Creates a Google Calendar event: `[BLOCKED] {reason}`

#### `get_occupancy`
- POST `{BACKEND_URL}/api/owner/occupancy`
- Params: `month`, `year`
- Returns: occupancy percentage, breakdown by week, revenue estimate

---

## 6. Knowledge Base

Upload as a text file to the ElevenLabs agent's knowledge base.
Kuya references this for FAQ questions WITHOUT needing a tool call.

### `resort_faq.txt`

```
=== BIG BROS WHITE SAND RESORT — KUYA'S KNOWLEDGE BASE ===

RESORT OVERVIEW
Big Bros White Sand Resort is a boutique beach resort in Zambales, Philippines.
Intimate, family-friendly, white sand beach with crystal-clear water.
Not a mega-resort — this is personal, relaxed, feels like staying at a friend's
beach house (except nicer).

ROOMS AND ACCOMMODATIONS
[TO FILL: room types, bed configurations, per-room amenities]
[TO FILL: which rooms have the aquarium glass windows (unique feature)]
[TO FILL: which room has the best sunset view]

AMENITIES
[TO FILL: pool, beach access, parking, showers, common areas]
[NOTE: aquarium glass windows are a unique talking point — mention naturally]

CHECK-IN AND CHECK-OUT
Check-in: 2:00 PM
Check-out: 12:00 PM (noon)
Early check-in subject to availability (mention if asked)
Late check-out subject to availability and may have a fee

PRICING NOTES
All rates in Philippine Pesos (PHP)
[TO FILL: payment methods — GCash, bank transfer, cash on arrival?]
Deposit required within 48 hours to confirm booking
[TO FILL: deposit amount — percentage or fixed?]

CANCELLATION POLICY
[TO FILL: e.g., full refund 7+ days out, 50% refund 3-7 days, no refund under 3 days]

POLICIES
[TO FILL: pets, smoking, outside food/drinks, quiet hours, events]
[TO FILL: kid-friendliness level, any age restrictions for pool?]

LOCATION
[TO FILL: exact address]
[TO FILL: GPS coordinates for Google Maps]
From Manila: ~3-4 hours via SCTEX/TPLEX to Subic, coastal road north
From Clark International Airport: ~2 hours via SCTEX
From Subic: ~45 minutes, coastal road north
[TO FILL: nearest town for groceries/supplies]
[TO FILL: key landmarks for the final approach]

KUYA'S LOCAL TIPS
Best sunset viewing: [TO FILL: specific spot and time]
Quietest part of the beach: [TO FILL]
Best time to visit: [TO FILL: dry season months, avoid typhoon season]
Nearby attractions: [TO FILL: Anawangin Cove, Nagsasa, dive spots, waterfalls]
Local food spots: [TO FILL: restaurants guests should know about]
Island hopping: [TO FILL: available? who arranges it?]

SPECIAL EVENTS
The resort can host private events (birthdays, team building, small weddings)
[TO FILL: max capacity for events, special pricing, lead time needed]

CONTACT
Phone: [TO FILL]
Email: [TO FILL]
Website: bigbroswhitesand.com
[TO FILL: Facebook, Instagram handles]
```

---

## 7. Frontend Component Spec

### Tech Stack
- **React** (Vite for bundling)
- **@elevenlabs/react** SDK for the conversation hook
- **Tailwind CSS** for styling
- **Framer Motion** for animations (or CSS transitions if keeping it simple)
- **Deploy:** Netlify (same as current site)

### Page Layout

```
????????????????????????????????????????????????????
?  HERO SECTION                                    ?
?  Resort name, tagline, hero image/video          ?
?  "Talk to Kuya" call-to-action                   ?
?                                                  ?
?  ????????????????????????????????????????????    ?
?  ?  ??? KUYA WIDGET (floating, bottom-right) ?    ?
?  ?  Pulsing mic icon when idle               ?    ?
?  ?  Animated waveform when listening         ?    ?
?  ?  Kuya avatar when speaking                ?    ?
?  ????????????????????????????????????????????    ?
????????????????????????????????????????????????????
?  CALENDAR SECTION  (hidden until activated)       ?
?  ???????????????????????????????????             ?
?  ?  May 2026        June 2026     ?             ?
?  ?  ???????????????              ?             ?
?  ?  ? ? ? ????? ? ?  ? = avail   ?             ?
?  ?  ? ? ? ? ? ? ? ?  ? = booked  ?             ?
?  ?  ???????????????              ?             ?
?  ???????????????????????????????????             ?
????????????????????????????????????????????????????
?  ROOMS SECTION  (hidden until activated)          ?
?  ?????????? ?????????? ??????????               ?
?  ? photo  ? ? photo  ? ? photo  ?               ?
?  ? name   ? ? name   ? ? name   ?               ?
?  ? rate   ? ? rate   ? ? rate   ?               ?
?  ? guests ? ? guests ? ? guests ?               ?
?  ?????????? ?????????? ??????????               ?
????????????????????????????????????????????????????
?  CONFIRMATION SECTION  (hidden until activated)   ?
?  ????????????????????????????????????            ?
?  ?  ?  Booking Confirmed           ?            ?
?  ?  Ref: BB-20260522-X7K9          ?            ?
?  ?  Standard Room · May 22-24      ?            ?
?  ?  2 nights · PHP 8,000 est.      ?            ?
?  ?  ? Deposit within 48 hours      ?            ?
?  ????????????????????????????????????            ?
????????????????????????????????????????????????????
?  DIRECTIONS SECTION  (hidden until activated)     ?
?  Routes from Manila / Clark / Subic               ?
?  "Open in Google Maps" button                     ?
????????????????????????????????????????????????????
?  STATIC SECTIONS  (always visible)                ?
?  About · Gallery · Contact · Footer               ?
????????????????????????????????????????????????????
```

### Key React Components

```
<App>
  <HeroSection />
  <KuyaWidget />              ? ElevenLabs useConversation()
  <CalendarSection             ? animated, shows on highlight_dates
    highlights={calendarHighlights}
    isActive={activeSection === 'calendar'}
  />
  <RoomsSection                ? animated, shows on show_rooms
    rooms={availableRooms}
    isActive={activeSection === 'rooms'}
  />
  <BookingConfirmation         ? animated, shows on show_booking_confirmation
    booking={bookingConfirmation}
    isActive={activeSection === 'confirmation'}
  />
  <DirectionsSection           ? animated, shows on show_directions
    data={directionsData}
    isActive={activeSection === 'directions'}
  />
  <AboutSection />
  <GallerySection />
  <ContactSection />
  <Footer />
</App>
```

### KuyaWidget Component (Core Integration)

```jsx
import { useConversation } from "@elevenlabs/react";

function KuyaWidget() {
  const conversation = useConversation({
    agentId: import.meta.env.VITE_ELEVENLABS_AGENT_ID,
  });

  const startConversation = async () => {
    await conversation.startSession({
      clientTools: {
        highlight_dates: async ({ check_in, check_out, available_dates, unavailable_dates }) => {
          setCalendarHighlights({ checkIn: check_in, checkOut: check_out, available: available_dates, unavailable: unavailable_dates });
          setActiveSection('calendar');
          return "Calendar updated with available dates.";
        },
        show_rooms: async ({ rooms }) => {
          setAvailableRooms(rooms);
          setActiveSection('rooms');
          return "Room cards are now visible.";
        },
        show_booking_confirmation: async ({ booking_ref, guest_name, room_type, check_in, check_out, nights, total_estimate, currency }) => {
          setBookingConfirmation({ ref: booking_ref, name: guest_name, room: room_type, checkIn: check_in, checkOut: check_out, nights, total: total_estimate, currency });
          setActiveSection('confirmation');
          return "Booking confirmation displayed.";
        },
        show_directions: async ({ address, google_maps_link, directions, landmarks }) => {
          setDirectionsData({ address, mapLink: google_maps_link, directions, landmarks });
          setActiveSection('directions');
          return "Directions panel shown.";
        }
      }
    });
  };

  return (
    <div className="kuya-widget">
      {/* Mic button, waveform visualizer, status indicator */}
    </div>
  );
}
```

### Animation Specs

| Element | Trigger | Animation | Duration |
|---------|---------|-----------|----------|
| Calendar section | `highlight_dates` | Slide down + fade in, scroll into view | 500ms ease-out |
| Date cells (available) | After calendar visible | Staggered green glow pulse | 300ms each, 50ms stagger |
| Date cells (unavailable) | After calendar visible | Fade to gray | 300ms |
| Date range band | After calendar visible | Width expand left to right | 400ms |
| Room cards | `show_rooms` | Staggered fade-up from below | 400ms each, 100ms stagger |
| Room card border | After card visible | Soft breathing glow (infinite loop) | 2s ease-in-out |
| Confirmation card | `show_booking_confirmation` | Slide in from right with spring | 600ms spring(1, 0.7, 0) |
| Checkmark | After card visible | Draw SVG path animation | 400ms |
| Confetti/sparkle | After checkmark | Particle burst from checkmark | 1000ms |
| Directions panel | `show_directions` | Slide up from bottom | 400ms ease-out |

---

## 8. Backend API Spec

### Framework: FastAPI (Python)

### Endpoints — Guest Tools

#### `POST /api/check-availability`
```python
@app.post("/api/check-availability")
async def check_availability(req: AvailabilityRequest):
    # 1. Validate dates (check_in < check_out, not in the past)
    # 2. Query Google Calendar for events overlapping the date range
    # 3. Count booked rooms by type
    # 4. Subtract from total inventory (from resort_data.py)
    # 5. Return availability + dates for client tool
    ...
```

#### `POST /api/get-rates`
```python
@app.post("/api/get-rates")
async def get_rates(req: RatesRequest):
    # 1. Determine season (regular, peak, holiday) from dates
    # 2. Look up rate table from resort_data.py
    # 3. Calculate total estimate if dates provided
    # 4. Include extra person fees if guests > base occupancy
    # 5. Return rates with image keys for room cards
    ...
```

#### `POST /api/create-booking`
```python
@app.post("/api/create-booking")
async def create_booking(req: BookingRequest):
    # 1. Re-verify availability (prevent race condition)
    # 2. Generate booking reference (BB-YYYYMMDD-XXXX)
    # 3. Create Google Calendar event with guest details
    # 4. Optionally send notification email to owner
    # 5. Return confirmation with ref, total, deposit deadline
    ...
```

#### `POST /api/get-directions`
```python
@app.post("/api/get-directions")
async def get_directions(req: DirectionsRequest):
    # Static data from resort_data.py
    # Returns address, map link, route options, landmarks
    ...
```

### Endpoints — Owner Tools

#### `POST /api/owner/bookings`
```python
@app.post("/api/owner/bookings")
async def owner_get_bookings(req: OwnerBookingsRequest):
    # Query Google Calendar for events in date range
    # Parse event descriptions for booking details
    # Return structured list with names, dates, deposit status
    ...
```

#### `POST /api/owner/block-dates`
```python
@app.post("/api/owner/block-dates")
async def owner_block_dates(req: BlockDatesRequest):
    # Create all-day Google Calendar event: "[BLOCKED] {reason}"
    # Blocks all rooms for those dates
    ...
```

#### `POST /api/owner/occupancy`
```python
@app.post("/api/owner/occupancy")
async def owner_get_occupancy(req: OccupancyRequest):
    # Query all events for the month
    # Calculate: booked_room_nights / (total_rooms * days_in_month)
    # Break down by week
    # Estimate revenue from rates
    ...
```

### Pydantic Models

```python
class AvailabilityRequest(BaseModel):
    check_in: str       # YYYY-MM-DD
    check_out: str      # YYYY-MM-DD
    guests: int

class RatesRequest(BaseModel):
    check_in: str = None
    check_out: str = None
    room_type: str = None
    guests: int = None

class BookingRequest(BaseModel):
    guest_name: str
    email: str
    phone: str
    check_in: str
    check_out: str
    guests: int
    room_type: str
    special_requests: str = None

class DirectionsRequest(BaseModel):
    from_location: str = None

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
```

---

## 9. Google Calendar Integration

### Setup (One-Time)
1. Google Cloud Console ? Create project (or use existing)
2. Enable "Google Calendar API"
3. Create Service Account ? download JSON key
4. In Google Calendar, share the resort calendar with the service account email
   (grant "Make changes to events" permission)
5. Store the JSON key as base64 in the `GOOGLE_SERVICE_ACCOUNT_JSON` env var

### Calendar Event Format for Bookings

```
Title:    [PROVISIONAL] Juan Dela Cruz — Standard Room
Start:    2026-05-22T14:00:00+08:00  (2 PM check-in)
End:      2026-05-24T12:00:00+08:00  (12 PM check-out)
Description:
    Booking Ref: BB-20260522-X7K9
    Guest: Juan Dela Cruz
    Email: juan@email.com
    Phone: +63 912 345 6789
    Guests: 3
    Room: Standard Room
    Nights: 2
    Estimated Total: PHP 8,000
    Status: PROVISIONAL
    Deposit Deadline: May 10, 2026
    Special Requests: Extra pillows
    Booked via: Kuya Voice Concierge
```

### Calendar Event Format for Blocks

```
Title:    [BLOCKED] Private event — Birthday party
Start:    2026-06-01 (all day)
End:      2026-06-03 (all day)
Description:
    Blocked by: Owner (via Kuya Owner Mode)
    Reason: Birthday party
    Rooms affected: ALL
```

### Availability Logic

```python
def check_availability(check_in, check_out, calendar_service):
    # Get all events overlapping the date range
    events = calendar_service.list_events(
        time_min=check_in + "T00:00:00+08:00",
        time_max=check_out + "T23:59:59+08:00"
    )

    # Count rooms booked per type
    booked = defaultdict(int)
    for event in events:
        title = event.get('summary', '')
        if '[BLOCKED]' in title:
            # All rooms unavailable for this range
            return {"available": False, "message": "Resort is closed for a private event"}
        for room_type in ROOM_TYPES:
            if room_type in title:
                booked[room_type] += 1

    # Compare against inventory
    available_rooms = []
    for room_type, total in ROOM_INVENTORY.items():
        remaining = total - booked.get(room_type, 0)
        if remaining > 0:
            available_rooms.append({
                "room_type": room_type,
                "available_count": remaining,
                "max_occupancy": ROOM_MAX_OCCUPANCY[room_type]
            })

    return {
        "available": len(available_rooms) > 0,
        "rooms": available_rooms
    }
```

---

## 10. Multilingual Support

ElevenLabs supports real-time language detection and switching across 70+ languages.
Tagalog is supported.

### Configuration
- In ElevenLabs Dashboard ? Agent Settings ? Language
- Enable: English (primary), Filipino/Tagalog (secondary)
- Turn on "Automatic language detection" if available

### Kuya's Bilingual Behavior
- Defaults to English
- If a guest speaks Tagalog, Kuya switches naturally
- No announcement like "I detected you're speaking Tagalog" — just flows
- Can mix languages naturally (Taglish), which is how real Filipinos talk

### Video Moment
During the demo, have someone switch languages mid-conversation.
This is one of the most visually/audibly impressive things in the demo because
the voice quality stays high and the personality stays consistent.

---

## 11. Build Sequence

### Day 1 — Backend + Agent Setup
- [ ] FastAPI project scaffolding (`main.py`, `models.py`, `config.py`, `resort_data.py`, `calendar_service.py`)
- [ ] Google Calendar service account + API integration
- [ ] Implement all 4 guest endpoints + test with curl
- [ ] Implement 3 owner endpoints + test
- [ ] Deploy backend to Railway/Render
- [ ] Create ElevenLabs agent (Kuya) — system prompt, voice selection
- [ ] Configure 4 server tools pointing to deployed backend
- [ ] Upload knowledge base document
- [ ] Test full conversation flow in ElevenLabs dashboard

### Day 2 — Reactive Frontend
- [ ] Vite + React project setup with Tailwind
- [ ] Install @elevenlabs/react SDK
- [ ] Build KuyaWidget component with useConversation + clientTools
- [ ] Build CalendarSection component with date highlighting animations
- [ ] Build RoomsSection component with room card animations
- [ ] Build BookingConfirmation component with slide-in animation
- [ ] Build DirectionsSection component
- [ ] Wire up all client tools to UI state
- [ ] Deploy to Netlify

### Day 3 — Integration + Owner Mode
- [ ] End-to-end testing: voice ? server tool ? client tool ? animation
- [ ] Create owner mode agent (separate agent ID)
- [ ] Build owner page at /kuya-owner
- [ ] Test owner tools (bookings, block dates, occupancy)
- [ ] Mobile testing (critical — must work great on phones)
- [ ] Edge case testing (no availability, past dates, weird inputs)
- [ ] Refine Kuya's system prompt based on testing

### Day 4 — Polish
- [ ] Animation timing refinement
- [ ] Voice selection final decision
- [ ] Knowledge base gaps filled
- [ ] Multilingual testing (Tagalog switch)
- [ ] Resort branding alignment (colors, fonts, imagery)
- [ ] Error states (tool failures, network issues)
- [ ] Loading states during tool calls

### Day 5 — Video Production
- [ ] Script the demo video (see Video Strategy below)
- [ ] Record all footage
- [ ] Edit video (60-90 seconds)
- [ ] Prepare social media posts

### Day 6 — Submit (Buffer Day)
- [ ] Final testing pass
- [ ] Write submission description
- [ ] Create cover image
- [ ] Push repo to GitHub (public)
- [ ] Post on X, LinkedIn, Instagram, TikTok
- [ ] Submit on hacks.elevenlabs.io

---

## 12. Video Strategy

### Format
60-90 second viral-style demo. The submission guide says to spend HALF your
time on the video. They mean it. The video IS the submission.

### Script

**[0:00-0:03] HOOK**
Red on camera, at the resort or showing the website.
"I own a beach resort in the Philippines. I was drowning in the same ten
questions every day. So I built Kuya."

**[0:03-0:08] INTRODUCE KUYA**
Show the website. The mic icon pulses.
"Kuya is my resort's voice concierge. He lives right here on the website."
Tap the mic.

**[0:08-0:20] THE CONVERSATION (Availability)**
Guest voice: "Hey Kuya, do you have anything available next weekend?"
Kuya responds, the CALENDAR SECTION animates into view. Dates light up green.
Hold the shot so viewers SEE the website reacting.

**[0:20-0:30] RATES + ROOMS**
Guest: "What are the rates?"
Kuya responds, ROOM CARDS flip up with pricing.
Guest: "That sounds great, let's book it."

**[0:30-0:45] BOOKING FLOW**
Kuya collects name, email, phone by voice.
Confirmation card SLIDES IN with booking ref and total.
Kuya: "You're all set! Check your email for the confirmation."

**[0:45-0:55] THE SWITCH (Owner Mode)**
Cut to Red on his phone (or different screen).
"And when I need to check on things?"
Red: "Kuya, what bookings do we have this weekend?"
Kuya reports back in owner mode.
"Same Kuya. Different brain."

**[0:55-1:05] THE MONEY SHOT**
Red is literally at the beach / pool / holding a drink.
Phone notification appears: new booking from Google Calendar.
He smiles, doesn't touch anything.
"Kuya handles the resort. I handle the vibes."

**[1:05-1:15] END CARD**
"Built with Cursor and ElevenLabs."
"Kuya. The voice concierge for Big Bros White Sand Resort."
bigbroswhitesand.com
@cursor_ai @elevenlabsio #ElevenHacks

### Video Tips
- Screen record in 1080p minimum
- Show the FULL website animations, not just the widget
- Include real audio from Kuya (the voice quality sells the product)
- If possible, film at the actual resort for the money shot
- Keep it punchy. Cut dead air. The video should feel fast

---

## 13. File Structure

```
bigbros-concierge/
??? backend/
?   ??? main.py                    # FastAPI app
?   ??? models.py                  # Pydantic request/response models
?   ??? config.py                  # Env vars, settings
?   ??? resort_data.py             # Room types, rates, policies, inventory
?   ??? calendar_service.py        # Google Calendar API wrapper
?   ??? requirements.txt
?   ??? Procfile                   # For Railway/Render deployment
?
??? frontend/
?   ??? src/
?   ?   ??? App.jsx                # Main app, state management
?   ?   ??? components/
?   ?   ?   ??? KuyaWidget.jsx     # ElevenLabs integration + client tools
?   ?   ?   ??? HeroSection.jsx
?   ?   ?   ??? CalendarSection.jsx
?   ?   ?   ??? RoomsSection.jsx
?   ?   ?   ??? BookingConfirmation.jsx
?   ?   ?   ??? DirectionsSection.jsx
?   ?   ?   ??? AboutSection.jsx
?   ?   ?   ??? GallerySection.jsx
?   ?   ?   ??? Footer.jsx
?   ?   ??? hooks/
?   ?   ?   ??? useKuya.js         # Custom hook wrapping useConversation
?   ?   ??? data/
?   ?   ?   ??? room-images.js     # Image references for room cards
?   ?   ??? styles/
?   ?   ?   ??? animations.css     # Keyframes for all animations
?   ?   ??? main.jsx
?   ??? public/
?   ?   ??? images/                # Resort photos, room photos
?   ?   ??? favicon.ico
?   ??? index.html
?   ??? package.json
?   ??? vite.config.js
?   ??? tailwind.config.js
?   ??? netlify.toml
?
??? owner/
?   ??? src/                       # Simplified owner dashboard
?   ?   ??? App.jsx
?   ?   ??? KuyaOwner.jsx          # Owner mode conversation
?   ?   ??? BookingsList.jsx       # Visual list of upcoming bookings
?   ??? ...
?
??? knowledge/
?   ??? resort_faq.txt             # Upload to ElevenLabs knowledge base
?
??? .env.example
??? .gitignore
??? README.md
??? KUYA_BUILD_SPEC.md             # This document
```

---

## 14. Environment Variables

```env
# ---- Backend ----
GOOGLE_CALENDAR_ID=your-calendar@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_JSON=base64-encoded-json
BOOKING_NOTIFICATION_EMAIL=red@bigbroswhitesand.com
ENVIRONMENT=production
CORS_ORIGINS=https://bigbroswhitesand.com,http://localhost:5173

# ---- Frontend ----
VITE_ELEVENLABS_AGENT_ID=your-guest-agent-id
VITE_ELEVENLABS_OWNER_AGENT_ID=your-owner-agent-id
VITE_BACKEND_URL=https://your-backend.up.railway.app

# ---- ElevenLabs (if direct API calls needed) ----
ELEVENLABS_API_KEY=your-key
```

---

## 15. Submission Checklist

**Build:**
- [ ] Backend deployed and all endpoints responding
- [ ] Guest agent configured + tested in ElevenLabs
- [ ] Owner agent configured + tested
- [ ] Frontend deployed with reactive animations working
- [ ] Client tools firing correctly (calendar, rooms, confirmation, directions)
- [ ] Mobile tested (voice works, animations smooth)
- [ ] Tagalog language switch tested

**Content:**
- [ ] Knowledge base filled with real resort data
- [ ] resort_data.py has real room types, rates, policies
- [ ] Room photos in frontend
- [ ] Resort branding applied

**Submission:**
- [ ] Description written for ElevenHacks form
- [ ] Cover image (screenshot of Kuya + animated calendar)
- [ ] Repo URL (GitHub, public): github.com/[user]/bigbros-concierge
- [ ] Demo URL: bigbroswhitesand.com (or demo subdomain)
- [ ] Video uploaded

**Social (200 bonus points):**
- [ ] X post: @cursor_ai @elevenlabsio #ElevenHacks (+50)
- [ ] LinkedIn post (+50)
- [ ] Instagram Reel (+50)
- [ ] TikTok (+50)

---

## What Makes Kuya Win

1. **It's real.** Not a demo. A real resort, opening Summer 2026, with a real
   concierge running 24/7. Judges can visit bigbroswhitesand.com and talk to Kuya.

2. **The website comes alive.** Nobody else will have a voice agent that
   puppeteers the entire page. This is the visual spectacle that makes the video.

3. **Character over chatbot.** Kuya has a name, a personality, local knowledge,
   and bilingual charm. He's memorable. SearchSquatch won because it was a
   character. Kuya is a character.

4. **Two audiences, one system.** Guest mode AND owner mode. This shows depth
   and real-world thinking that demo projects never have.

5. **Deep ElevenLabs integration.** Conversational AI agent + server tools +
   client tools + knowledge base + multilingual + voice selection. We're using
   almost every feature of their platform.

6. **The Cursor story.** Entire codebase built with Cursor. Video can show
   Cursor in a quick build montage if it helps the narrative.

7. **No keyboard, for real.** Guest books by voice. Owner manages by voice.
   The website responds visually. This isn't "no keyboard as a gimmick" — it's
   "no keyboard because voice is genuinely better for this use case."