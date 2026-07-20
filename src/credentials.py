import os
import re

import bs4
import dotenv
import requests
import requests.compat

dotenv.load_dotenv()
BASE_URL: str = os.getenv('BASE_URL', '')
LOGIN_USERNAME: str = os.getenv('LOGIN_USERNAME', '')
LOGIN_PASSWORD: str = os.getenv('LOGIN_PASSWORD', '')

if not BASE_URL or not LOGIN_USERNAME or not LOGIN_PASSWORD:
  raise RuntimeError('Missing base url or credentials in .env file')


def login(session: requests.Session):
  response = session.get(BASE_URL, allow_redirects=True)
  soup = bs4.BeautifulSoup(response.text, 'html.parser')

  form: bs4.Tag = soup.find('form')
  if not form:
    raise RuntimeError('Login form not found')

  payload = {}
  for field in form.find_all('input'):
    field: bs4.Tag
    name = field.get('name')
    if name:
      payload[name] = field.get('value', '')

  username_field: bs4.Tag = form.find(id='username')
  password_field: bs4.Tag = form.find(id='password')

  if not username_field or not password_field:
    raise RuntimeError('Login fields not found')

  payload[username_field.get('name', 'username')] = LOGIN_USERNAME
  payload[password_field.get('name', 'password')] = LOGIN_PASSWORD
  action = form.get('action')
  login_url = requests.compat.urljoin(BASE_URL, action) if action else BASE_URL
  return session.post(login_url, data=payload, allow_redirects=True)


def extract_credentials(session: requests.Session, response: requests.Response):
  csrf_match = re.search(r"window\.CM_CSRF_TOKEN\s*=\s*['\"]([^'\"]+)['\"]", response.text)
  csrf_token = csrf_match.group(1) if csrf_match else None

  cookie = None
  for found_cookie in session.cookies:
    if 'joomla' in found_cookie.name:
      continue

    cookie = f'{found_cookie.name}={found_cookie.value}'

  if not cookie:
    raise RuntimeError('Cookie extraction failed')

  if not csrf_token:
    raise RuntimeError('CSRF token extraction failed')

  return cookie, csrf_token


def get_credentials():
  session = requests.Session()
  response = login(session)
  cookie, csrf_token = extract_credentials(session, response)
  return cookie, csrf_token


if __name__ == '__main__':
  cookie, csrf_token = get_credentials()
  print(f'Cookie: {cookie}, CSRF token: {csrf_token}')
