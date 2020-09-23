import re
import urllib.parse
from datetime import datetime
from types import TracebackType
from typing import Dict, Iterable, List, Optional, Protocol, Tuple, Type

import bs4
import mechanicalsoup
import requests
from bs4.element import Tag
from dateutil.parser import parse as parse_datetime

from ._bs_utils import delete_subelements, stringify_contents
from ._emojis import replace_emoji_imgs
from ._settings import TZ
from ._types import (
    Message,
    MessageId,
    MessageInfo,
    NewsItem,
    NewsItemId,
    NewsItemInfo,
    Pupil,
    PupilId,
    ReplyMessage,
)

PUPIL_LINK_RX = re.compile(r'^/!(\d+)/?$')
MESSAGE_NOTIFICATION_LINK_RX = re.compile(r'^/!(\d+)/messages$')
NEWS_ITEM_LINK_RX = re.compile(r'/!(\d+)/news/(?P<news_id>\d+)$')
REPLY_HEADER_RX = re.compile(
    r'(?P<from>.* \(.*\)) .* (?P<date>[0-9][0-9.:/ ]+)$')
YEARLESS_DATE_RX = re.compile(
    r'^((0?[1-9])|[1-2][0-9]|3[01])\.((0?[1-9])|(1[0-2]))\.$')


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
        browser = mechanicalsoup.StatefulBrowser(raise_on_404=True)
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
        self.front_page = self._get_current_page_or_fail()
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
        body = self._fetch_message_body(message_info.pupil_id, message_info.id)
        (body_text, replies) = self._parse_message_body(body)
        message = Message.from_info_and_body(message_info, body_text, replies)
        return message

    def _fetch_message_body(
            self,
            pupil_id: PupilId,
            message_id: MessageId,
    ) -> Tag:
        """
        Get message contents as HTML string.
        """
        url = f'/!{pupil_id}/messages/{message_id}?printable'
        page = self._browse(url)
        body = page.find('body')
        if not body:
            raise Exception(f'Cannot parse message: {url}')
        delete_subelements(body, ['h1', 'table', '.printout-footer'])
        replace_emoji_imgs(body)
        return body

    def _parse_message_body(self, body: Tag) -> Tuple[str, List[ReplyMessage]]:
        reply_divs = body.find_all(attrs={'class': 'm-replybox'})
        replies = [self._parse_reply_message(x) for x in reply_divs]
        for div in reply_divs:
            div.replace_with('')
        body_text = stringify_contents(body)
        return (body_text, replies)

    def _parse_reply_message(self, div: Tag) -> ReplyMessage:
        header = div.find('h2')
        content = div.select_one('.inner')
        match = REPLY_HEADER_RX.match(header.text if header else '')
        if not match or not content:
            raise Exception(f'Cannot parse reply: {div}')
        header_data = match.groupdict()
        return ReplyMessage(
            timestamp=_parse_timestamp(header_data['date']),
            sender=header_data['from'],
            body=stringify_contents(content))

    def fetch_news_list(self, pupil_id: PupilId) -> List[NewsItemInfo]:
        page = self._browse(f'/!{pupil_id}/news')
        link_matches = (
            (a_elem, NEWS_ITEM_LINK_RX.match(a_elem.get('href', '')))
            for a_elem in page.find_all('a', href=True)
            if a_elem and a_elem.get('class')
        )
        news_map = {
            int(match.group('news_id')): a_elem.text.strip()
            for (a_elem, match) in link_matches
            if match
        }
        for well in page.select('.well'):
            title_elem = well.find('h3')
            a_elem = well.find('a', href=True)
            href = a_elem.get('href', '') if a_elem else ''
            match = NEWS_ITEM_LINK_RX.match(href)
            if title_elem and match:
                news_map[int(match.group('news_id'))] = title_elem.text.strip()
        return [
            NewsItemInfo(
                id=NewsItemId(news_id),
                origin=self.url,
                pupil_id=pupil_id,
                subject=subject,
            )
            for (news_id, subject) in sorted(news_map.items())
        ]

    def fetch_news_item(self, news_item_info: NewsItemInfo) -> NewsItem:
        elem = self._fetch_news_item_body(
            news_item_info.pupil_id, news_item_info.id)

        def select(element: Tag, selector: str) -> Tag:
            result = element.select_one(selector)
            if not result:
                raise Exception(
                    f'Cannot find "{selector}" from {news_item_info}')
            return result

        body_element = select(elem, '#news-content')
        metadata = select(elem, '.horizontal-link-container')
        (sender_id, sender) = self._parse_news_item_sender(metadata)
        date_span = select(metadata, 'span.small')
        timestamp = _parse_timestamp(date_span.text.split()[-1])

        return NewsItem.from_info_and_attrs(
            news_item_info,
            timestamp=timestamp,
            sender_id=sender_id,
            sender=sender,
            body=stringify_contents(body_element))

    def _fetch_news_item_body(
            self,
            pupil_id: PupilId,
            news_item_id: NewsItemId,
    ) -> Tag:
        url = f'/!{pupil_id}/news/{news_item_id}'
        page = self._browse(url)
        body = page.select_one('.panel-body')
        if not body:
            raise Exception(f'Cannot parse news item: {url}')
        replace_emoji_imgs(body)
        return body

    def _parse_news_item_sender(
            self,
            metadata: Tag,
    ) -> Tuple[Optional[int], str]:
        teacher_link = metadata.select_one('a.ope')
        if teacher_link:
            return self._parse_teacher_link(teacher_link)
        sender_span = metadata.find('span', attrs={'class': ""})
        text = sender_span.text.strip() if sender_span else ''
        sender = _switch_parenthesed_parts(text)
        return (None, sender)

    def _parse_teacher_link(self, teacher_link: Tag) -> Tuple[int, str]:
        teacher_href = teacher_link.get('href', '')
        if '/profiles/teachers/' not in teacher_href:
            raise Exception(f'Cannot parse teacher link: {teacher_link}')
        teacher_id = int(teacher_href.rsplit('/profiles/teachers/', 1)[-1])
        name = _switch_parenthesed_parts(teacher_link.text)
        return (teacher_id, name)

    def logout(self) -> None:
        """
        Log out of the site.
        """
        logout_url = self.browser.absolute_url('/logout')
        response = self.browser.post(logout_url)
        response.raise_for_status()
        self.browser = mechanicalsoup.StatefulBrowser()

    def _browse(
            self,
            relative_url: str,
    ) -> bs4.BeautifulSoup:
        self._browse_simple(relative_url)
        return self._get_current_page_or_fail()

    def _browse_simple(
            self,
            relative_url: str,
    ) -> requests.Response:
        response = self.browser.open_relative(relative_url)
        response.raise_for_status()
        return response

    def _get_current_page_or_fail(self) -> bs4.BeautifulSoup:
        page = self.browser.get_current_page()
        if not page:
            raise Exception(f'Error reading page at {self.browser.get_url()}')
        return page


class _PytzTimezone(Protocol):
    def localize(self, dt: datetime) -> datetime: ...


def _parse_timestamp(string: str, tz: _PytzTimezone = TZ) -> datetime:
    if YEARLESS_DATE_RX.match(string):
        string += str(datetime.now().year)
    dt = parse_datetime(string, dayfirst=(string.count('.') >= 2))
    if dt.tzinfo:
        return dt
    return tz.localize(dt)


def _switch_parenthesed_parts(string: str) -> str:
    match = re.match(r'^(.*) \((.*)\)$', string)
    if not match:
        return string
    text1 = match.group(1)
    text2 = match.group(2)
    return f'{text2} ({text1})'
