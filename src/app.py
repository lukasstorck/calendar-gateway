import asyncio
import contextlib
import os

import apscheduler.schedulers.asyncio
import fastapi
import fastapi.responses

import src.process_calendars as process_calendars

API_TOKEN = os.getenv('API_TOKEN', '')
CALENDAR_NAME = os.getenv('CALENDAR_NAME', '')

if not API_TOKEN:
  raise RuntimeError('Missing API token environment variable')

if not CALENDAR_NAME:
  raise RuntimeError('Missing calendar name environment variable')

if not CALENDAR_NAME.endswith('.ics'):
  raise RuntimeError('Calendar name must end with .ics')

scheduler = apscheduler.schedulers.asyncio.AsyncIOScheduler()


async def update_calendar():
  print('Updating calendars...')
  await asyncio.to_thread(process_calendars.update_calendar)


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
  if not process_calendars.OUTPUT_CALENDAR_PATH.exists():
    await update_calendar()

  scheduler.add_job(
    update_calendar,
    trigger='interval',
    minutes=5,
    id='calendar_update',
    max_instances=1,
    coalesce=True,
  )

  scheduler.start()

  try:
    yield
  finally:
    scheduler.shutdown(wait=False)


app = fastapi.FastAPI(lifespan=lifespan)


@app.get(f'/{CALENDAR_NAME}')
async def calendar(token: str = fastapi.Query(...)):
  if token != API_TOKEN:
    raise fastapi.HTTPException(status_code=401, detail='Invalid token')

  if not process_calendars.OUTPUT_CALENDAR_PATH.exists():
    raise fastapi.HTTPException(status_code=503, detail='Calendar unavailable')

  return fastapi.responses.FileResponse(
    process_calendars.OUTPUT_CALENDAR_PATH,
    media_type='text/calendar',
    filename=CALENDAR_NAME,
  )


@app.get('/health')
async def health():
  return {
    'ok': True,
    'calendar_exists': process_calendars.OUTPUT_CALENDAR_PATH.exists(),
  }
