# Calendar Gateway

Small service that logs into a calendar provider, downloads available iCal calendars, merges them, and exposes one protected `.ics` feed.
Can be used to access calendars behind a login wall on third-party sites (e.g. import web calendar on Google Calendar via URL).

## Install

Requirements:

- Docker
- Docker Compose

Create `.env`:

| Variable            | Description                        |
| ------------------- | ---------------------------------- |
| `BASE_URL`          | Calendar provider URL              |
| `CALENDAR_URL_PATH` | Path containing calendar list      |
| `CALENDAR_NAME`     | Output calendar filename (`.ics`)  |
| `LOGIN_USERNAME`    | Provider username                  |
| `LOGIN_PASSWORD`    | Provider password                  |
| `API_TOKEN`         | Access token for calendar endpoint |

Example:

```ini
BASE_URL=https://site.example.com
CALENDAR_URL_PATH=/path/to/calendars
CALENDAR_NAME=calendar.ics
LOGIN_USERNAME=user
LOGIN_PASSWORD=password
API_TOKEN=secret
```

Start:

```bash
docker compose up -d --build
```

## Usage

Calendar feed:

```
http://localhost:8000/<CALENDAR_NAME>?token=<API_TOKEN>

# Example:
http://localhost:8000/calendar.ics?token=secret
```

Calendar updates run automatically every 5 minutes.
