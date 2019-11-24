import re
import urllib.parse
from datetime import datetime
from types import TracebackType
from typing import Dict, Iterable, List, Optional, Protocol, Type

import mechanicalsoup
from bs4.element import Tag
from dateutil.parser import parse as parse_datetime

from ._settings import TZ
from ._types import Message, MessageId, MessageInfo, Pupil, PupilId

PUPIL_LINK_RX = re.compile(r'^/!(\d+)/?$')
MESSAGE_NOTIFICATION_LINK_RX = re.compile(r'^/!(\d+)/messages$')


class Client:
    def __init__(self, url: str, username: str, password: str) -> None:
        self.url = url
        self.username = username
        self.password = password

    def connect(self) -> 'Connection':
        return Connection.open(self.url, self.username, self.password)


class Connection:
    @classmethod
    def open(
            cls,
            url: str,
            username: str,
            password: str,
    ) -> 'Connection':
        """
        Log in to the site.
        """
        browser = mechanicalsoup.StatefulBrowser()
        browser.open(f'{url}/login')
        browser.select_form('.login-form')
        browser['Login'] = username
        browser['Password'] = password
        response = browser.submit_selected()
        response.raise_for_status()
        parsed_url = urllib.parse.urlparse(response.url)
        query = urllib.parse.parse_qs(parsed_url.query, keep_blank_values=True)
        if 'loginfailed' in query:
            raise Exception('Login failed')
        if parsed_url.query:
            raise Exception('Unexpected result')
        return cls(url, browser)

    def close(self) -> None:
        self.logout()

    def __enter__(self) -> 'Connection':
        return self

    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_value: Optional[Exception],
            traceback: Optional[TracebackType],
    ) -> None:
        self.close()

    def __init__(
            self,
            url: str,
            browser: mechanicalsoup.StatefulBrowser,
    ) -> None:
        self.url = url
        self.browser = browser
        self.front_page = browser.get_current_page()
        links = self.front_page.find_all('a', href=True)
        self.pupils = self._parse_pupils(links)
        self.new_message_counts = self._parse_new_message_counts(links)

    def _parse_pupils(self, links: Iterable[Tag]) -> Dict[PupilId, Pupil]:
        """
        Get list of pupils.
        """
        pupil_map: Dict[PupilId, str] = {}
        for link in links:
            match = PUPIL_LINK_RX.match(link.get('href', ''))
            if match:
                pupil_id = PupilId(match.group(1))
                if pupil_id not in pupil_map:
                    pupil_map[pupil_id] = link.text
        return {id: Pupil(id, name) for (id, name) in pupil_map.items()}

    def _parse_new_message_counts(
            self,
            links: Iterable[Tag],
    ) -> Dict[PupilId, int]:
        result: Dict[PupilId, int] = {}
        for link in links:
            match = MESSAGE_NOTIFICATION_LINK_RX.match(link.get('href', ''))
            if match:
                pupil_id = PupilId(match.group(1))
                first_word = link.text.split()[0]
                if first_word.isdigit():
                    amount = int(first_word)
                    result[pupil_id] = amount
        return result

    def get_new_messages(self) -> Dict[Pupil, List[Message]]:
        result: Dict[Pupil, List[Message]] = {}
        for (pupil_id, count) in self.new_message_counts.items():
            pupil = self.pupils[pupil_id]
            message_infos = self.fetch_message_list(pupil_id)
            unreads = (x for x in message_infos if x.is_unread)
            result[pupil] = [self.fetch_message(x) for x in unreads]
        return result

    def fetch_message_list(self, pupil_id: PupilId) -> List[MessageInfo]:
        """
        List messages of a pupil.
        """
        response = self.browser.get(
            self.browser.absolute_url(f'/!{pupil_id}/messages/list'),
            headers={'X-Requested-With': 'XMLHttpRequest'})
        response.raise_for_status()
        return [
            MessageInfo(
                id=MessageId(x['Id']),
                origin=self.url,
                pupil_id=pupil_id,
                subject=x['Subject'],
                timestamp=_parse_timestamp(x['TimeStamp']),
                folder=x['Folder'],
                sender_id=x['SenderId'],
                sender=x['Sender'],
                is_unread=(x.get('Status', 0) == 1),
            )
            for x in response.json()['Messages']
        ]

    def fetch_message(self, message_info: MessageInfo) -> Message:
        if message_info.origin != self.url:
            raise ValueError(
                f'Invalid message origin: '
                f'{message_info.origin} (expected {self.url})')
        body = self.fetch_message_body(message_info.pupil_id, message_info.id)
        message = Message.from_info_and_body(message_info, body)
        return message

    def fetch_message_body(
            self,
            pupil_id: PupilId,
            message_id: MessageId,
    ) -> str:
        """
        Get message contents as HTML string.
        """
        url = f'/!{pupil_id}/messages/{message_id}?printable'
        self.browser.open_relative(url)
        page = self.browser.get_current_page()
        body = page.find('body')
        if not body:
            return ''
        for selector in ['h1', 'table', '.printout-footer']:
            tag_to_clean = body.select_one(selector)
            if tag_to_clean:
                tag_to_clean.replace_with('')
        strings = (str(x) for x in body)
        return '\n'.join(x for x in strings if x.strip())

    def logout(self) -> None:
        """
        Log out of the site.
        """
        logout_url = self.browser.absolute_url('/logout')
        response = self.browser.post(logout_url)
        response.raise_for_status()
        self.browser = mechanicalsoup.StatefulBrowser()


class _PytzTimezone(Protocol):
    def localize(self, dt: datetime) -> datetime: ...


def _parse_timestamp(string: str, tz: _PytzTimezone = TZ) -> datetime:
    dt = parse_datetime(string)
    if dt.tzinfo:
        return dt
    return tz.localize(dt)
