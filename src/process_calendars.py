import datetime
import json
import os
import pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed

import bs4
import dotenv
import icalendar
import requests
import tqdm

import src.credentials as credentials

dotenv.load_dotenv()
BASE_URL: str = os.getenv('BASE_URL', '')
CALENDAR_URL_PATH: str = os.getenv('CALENDAR_URL_PATH', '')
OUTPUT_ANALYSIS_PATH: str = pathlib.Path(os.getenv('OUTPUT_ANALYSIS_PATH', ''))
OUTPUT_CALENDAR_PATH: str = pathlib.Path(os.getenv('OUTPUT_CALENDAR_PATH', ''))

if not BASE_URL or not CALENDAR_URL_PATH or not OUTPUT_ANALYSIS_PATH or not OUTPUT_CALENDAR_PATH:
  raise RuntimeError('Missing environment variables')

def create_session():
  session = requests.Session()
  cookie, _ = credentials.get_credentials()
  name, value = cookie.split('=', 1)
  session.cookies.set(name, value)

  return session


def get_calendars() -> list[dict[str, str | int]]:
  session = create_session()
  response = session.get(BASE_URL + CALENDAR_URL_PATH)
  response.raise_for_status()

  soup = bs4.BeautifulSoup(response.text, 'html.parser')

  calendars = []
  seen = set()

  no_id = 0

  for cal in soup.select('.dp-calendar'):
    title_el = cal.select_one('.dp-calendar__title')
    if not title_el:
      continue

    title = title_el.get_text(strip=True)
    link = next((a['href'] for a in cal.select('.dp-calendar__links a') if a.get_text(strip=True) == '[iCal]'), None)
    try:
      calendar_id = int(link.split('id=')[-1])
    except ValueError:
      no_id += 1
      calendar_id = -no_id

    if not link or link in seen:
      continue

    seen.add(link)
    calendars.append({'title': title, 'url': link, 'id': calendar_id})
  return calendars


def download_single_calendar(calendar_info):
  session = create_session()
  response = session.get(calendar_info['url'], allow_redirects=True)
  response.raise_for_status()

  return {'calendar': calendar_info, 'ical': response.content}


def download_calendars(calendars: list[dict]):
  downloads = []

  with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(download_single_calendar, cal) for cal in calendars]

    for future in tqdm.tqdm(as_completed(futures), total=len(futures), desc='Downloading calendars'):
      downloads.append(future.result())

  return downloads


def process_calendars(downloads):
  results = []
  merged = icalendar.Calendar()
  merged.add('version', '2.0')

  seen_uids = set()
  seen_timezones = set()
  merged_dates = []
  total_events = 0

  for item in downloads:
    calinfo = item['calendar']
    source = icalendar.Calendar.from_ical(item['ical'])

    events = []
    dates = []

    for component in source.walk():
      if component.name == 'VTIMEZONE':
        key = component.to_ical()

        if key not in seen_timezones:
          merged.add_component(component)
          seen_timezones.add(key)

      elif component.name == 'VEVENT':
        uid = str(component.get('uid'))

        if uid in seen_uids:
          continue

        seen_uids.add(uid)

        component.add('X-SOURCE-CALENDAR', f'{calinfo["title"]} (id={calinfo["id"]})')
        events.append(component)

        start = component.get('dtstart')

        if start:
          value = start.dt

          if isinstance(value, datetime.datetime):
            value = value.date()

          dates.append(value)
          merged_dates.append(value)

    for event in events:
      merged.add_component(event)

    results.append(
      {
        'title': calinfo['title'],
        'id': calinfo['id'],
        'url': calinfo['url'],
        'events': len(events),
        'start': str(min(dates)) if dates else None,
        'end': str(max(dates)) if dates else None,
      }
    )

    total_events += len(events)

  stats = {
    'calendars': len(results),
    'events': total_events,
    'start': min(merged_dates) if merged_dates else None,
    'end': max(merged_dates) if merged_dates else None,
  }

  return results, merged, stats


def update_calendar():
  calendars = get_calendars()

  downloads = download_calendars(calendars)
  downloads.sort(key=lambda d: d['calendar']['id'])

  results, merged_calendar, stats = process_calendars(downloads)

  with OUTPUT_ANALYSIS_PATH.open('w', encoding='utf-8') as file:
    json.dump(results, file, indent=2, default=str)

  with OUTPUT_CALENDAR_PATH.open('wb') as file:
    file.write(merged_calendar.to_ical())

  return stats


if __name__ == '__main__':
  stats = update_calendar()

  print(f'Merged calendars: {stats["calendars"]}')
  print(f'Total events: {stats["events"]}')

  if stats['start'] and stats['end']:
    print(f'Date range: {stats["start"]} -> {stats["end"]}')

  print(f'Wrote {OUTPUT_ANALYSIS_PATH}')
  print(f'Wrote {OUTPUT_CALENDAR_PATH}')
