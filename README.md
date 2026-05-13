# KUYA — Voice Concierge for Big Bros White Sand Resort

**Knowledgeable Universal Year-round Attendant**

KUYA is an AI voice concierge for [Big Bros White Sand Resort](https://bigbroswhitesand.com), a boutique beach resort in Zambales, Philippines. Guests talk to Kuya on the website — he checks real-time availability, quotes rates, creates bookings, and provides directions. No keyboard needed.

Built for [ElevenHacks #8](https://hacks.elevenlabs.io/) (Cursor x ElevenLabs).

## Live Demo

**[bigbroswhitesand.com](https://bigbroswhitesand.com)** — click the widget in the bottom right corner.

## How It Works

1. Guest taps "Start a call" on the resort website
2. Kuya greets them by voice
3. Guest asks about availability, rates, or directions — all by speaking
4. Kuya calls the backend API, which reads/writes to live Google Calendars
5. Booking appears on the resort's calendar instantly

## Architecture

```
Guest (voice) ? ElevenLabs Conversational AI Agent
                    ? server tools (webhooks)
                FastAPI Backend (Render)
                    ? Google Calendar API
                3 Google Calendars (Family Suite, Honeymoon Suite, Events)
```

## Tech Stack

- **Voice AI:** ElevenLabs Conversational AI (agent, server tools, knowledge base)
- **Backend:** FastAPI (Python), deployed on Render
- **Calendar:** Google Calendar API (3 calendars, service account auth)
- **Frontend:** ElevenLabs embed widget on Netlify
- **Built with:** Cursor

## Backend Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/check-availability` | Check room availability against live calendars |
| `POST /api/get-rates` | Quote nightly rates with extra person fees |
| `POST /api/create-booking` | Create provisional booking (writes to Google Calendar) |
| `POST /api/get-directions` | Travel directions to the resort |
| `POST /api/owner/bookings` | Owner: view upcoming bookings |
| `POST /api/owner/block-dates` | Owner: block dates across all calendars |
| `POST /api/owner/occupancy` | Owner: monthly occupancy and revenue estimate |

## Features

- Real-time availability from 3 separate Google Calendars
- 50-person property capacity cap enforced across all booking types
- Provisional booking creation with auto-generated reference codes
- Rate calculation with extra person fees (?1,000/person/night beyond base occupancy)
- Cancellation policy: 14+ days full refund, 7-13 days 50%, under 7 days none
- English and Filipino language support
- Owner management tools (bookings, date blocking, occupancy reports)

## Room Types

| Room | Base Guests | Max | Rate |
|------|------------|-----|------|
| Family Suite | 4 | 8 | ?8,000/night |
| Honeymoon Suite | 2 | 8 | ?8,000/night |
| Full Buyout | — | 50 | ?40,000/day |

## Setup

### Backend
```bash
cd backend
cp .env.example .env
# Fill in Google Calendar IDs and service account JSON (base64)
pip install -r requirements.txt
uvicorn main:app --reload
```

### ElevenLabs Agent
1. Create a Conversational AI agent in ElevenLabs
2. Add four server tools pointing to the deployed backend
3. Upload the knowledge base (`knowledge/resort_faq.txt`)
4. Embed the widget on your site:
```html
<script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>
<elevenlabs-convai agent-id="YOUR_AGENT_ID"></elevenlabs-convai>
```

## License

MIT