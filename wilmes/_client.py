import re
import urllib.parse
from datetime import date, datetime, timedelta
from types import TracebackType
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Tuple,
    Type,
)

import bs4
import mechanicalsoup
import requests
from bs4.element import Tag
from dateutil.parser import parse as parse_datetime

from ._bs_utils import stringify_contents
from ._emojis import replace_emoji_imgs
from ._settings import TZ
from ._types import (
    Message,
    MessageId,
    MessageInfo,
    NewsItem,
    NewsItemId,
    NewsItemInfo,
    Person,
    Pupil,
    PupilId,
    ReplyMessage,
)

PUPIL_LINK_RX = re.compile(r'^/!(\d+)/?$')
MESSAGE_NOTIFICATION_LINK_RX = re.compile(r'^/!(\d+)/messages$')
PERSON_LIST_RX = re.compile(r'([^(,]+(\([^)]*\)[^(,]*)*)((, )|$)')
PROFILE_HREF_RX = re.compile(r'.*/profiles/([^/]+)/(\d+)')
NEWS_ITEM_LINK_RX = re.compile(r'/!(\d+)/news/(?P<news_id>\d+)$')
REPLY_HEADER_RX = re.compile(
    r'(?P<from>.*)\xa0? replied [^0-9]*(?P<date>[0-9][0-9.:/ ]+)$')
SPECIAL_DATES: Dict[str, Callable[[], date]] = {
    'today': date.today,
    'yesterday': lambda: date.today() - timedelta(days=1),
}
YEARLESS_DATE_RX = re.compile(
    r'^((0?[1-9])|[1-2][0-9]|3[01])\.((0?[1-9])|(1[0-2]))\.$')

ENGLISH_LANG_ID = 3

SENDER_TYPES = {
    1: 'teachers',
    2: 'unknown2',
    3: 'personnel',
    4: 'others',
}


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
        browser.open(f'{url}/?langid={ENGLISH_LANG_ID}')
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
        self._check_language(links)
        self.pupils = self._parse_pupils(links)
        self.new_message_counts = self._parse_new_message_counts(links)
        own_name_span = self.front_page.select_one('.name-container .teacher')
        if not own_name_span:
            raise Exception('Cannot find the span containing your name')
        self.own_name = own_name_span.text

    def _check_language(self, links: Iterable[Tag]) -> None:
        for a_elem in links:
            if a_elem.get('href', '').endswith('passwd/settings'):
                if a_elem.text == "Account settings":
                    return
                raise Exception(
                    f"Invalid language: 'Account settings' is {a_elem.text!r}")
        raise Exception("Cannot find element for checking language")

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
                last_timestamp=_parse_timestamp(x['TimeStamp']),
                folder=x['Folder'],
                sender=Person(
                    name=x['Sender'],
                    id=x['SenderId'],
                    type=SENDER_TYPES.get(x['SenderType']),
                ),
                reply_count=x.get('Replies', 0),
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
        timestamp = self._parse_sent_time(body)
        recipients = self._parse_recipients(body)
        message_content = self._parse_message_content(body)
        replies = self._parse_replies(body)
        message = Message.from_info_and_attrs(
            message_info, timestamp, recipients, message_content, replies)
        return message

    def _fetch_message_body(
            self,
            pupil_id: PupilId,
            message_id: MessageId,
    ) -> Tag:
        """
        Get message contents as HTML string.
        """
        url = f'/!{pupil_id}/messages/{message_id}?recipients'
        page = self._browse(url)
        body = page.find('body')
        if not body:
            raise Exception(f'Cannot parse message: {url}')
        replace_emoji_imgs(body)
        return body

    def _parse_sent_time(self, body: Tag) -> datetime:
        table_ths = body.select('table th')
        sent_ths = [x for x in table_ths if x.text.startswith('Sent:')]
        if len(sent_ths) == 1 and sent_ths[0].parent:
            sent_td = sent_ths[0].parent.find('td')
            if sent_td:
                return _parse_timestamp(sent_td.text)
        raise Exception(f'Cannot find table cell contaiting sending time')

    def _parse_recipients(self, body: Tag) -> List[Person]:
        recip_div = body.select_one('#recipients-cell')
        if not recip_div:
            raise Exception('Cannot find recipients div')
        result: List[Person] = []
        for part in recip_div:
            if isinstance(part, str):
                matches = PERSON_LIST_RX.finditer(part.strip().rstrip(','))
                names = (x.group(1).strip() for x in matches)
                result.extend(Person(x) for x in names if x)
            else:
                result.append(self._parse_person_element(part))
        if len(result) == 1 and result[0] == Person('Hidden'):
            return []
        return result

    def _parse_message_content(self, body: Tag) -> str:
        message_div = body.select_one('.ckeditor.hidden')
        if not message_div:
            raise Exception('Cannot find message div')
        return stringify_contents(message_div)

    def _parse_replies(self, body: Tag) -> List[ReplyMessage]:
        reply_divs = body.find_all(attrs={'class': 'm-replybox'})
        replies = [self._parse_reply_message(x) for x in reply_divs]
        return replies

    def _parse_reply_message(self, div: Tag) -> ReplyMessage:
        header = div.find('h2')
        content = div.select_one('.inner')
        match = REPLY_HEADER_RX.match(header.text if header else '')
        if not header or not match or not content:
            raise Exception(f'Cannot parse reply: {div}')
        header_data = match.groupdict()
        profile_link = header.select_one('a.profile-link')
        if profile_link:
            person = self._parse_profile_link(profile_link)
        else:
            from_text = header_data['from']
            name = from_text if from_text.lower() != 'you' else self.own_name
            person = Person(name)
        return ReplyMessage(
            timestamp=_parse_timestamp(header_data['date']),
            sender=person,
            body=stringify_contents(content))

    def fetch_news_list(self, pupil_id: PupilId) -> List[NewsItemInfo]:
        page = self._browse(f'/!{pupil_id}/news')
        link_matches = (
            (a_elem, NEWS_ITEM_LINK_RX.match(a_elem.get('href', '')))
            for a_elem in page.find_all('a', href=True)
            if a_elem and a_elem.get('class')
        )
        news_map: Dict[int, Tuple[str, Optional[datetime], bool]] = {
            # news_id -> (subject, date)
            int(match.group('news_id')): (a_elem.text.strip(), None, False)
            for (a_elem, match) in link_matches
            if match
        }
        for well in page.select('.well'):
            date_h2 = well.find_previous('h2')
            date = _parse_timestamp(date_h2.text) if date_h2 else None
            title_elem = well.find('h3')
            a_elem = well.find('a', href=True)
            href = a_elem.get('href', '') if a_elem else ''
            match = NEWS_ITEM_LINK_RX.match(href)
            if title_elem and match:
                (subject, is_new) = self._parse_news_title(title_elem)
                news_map[int(match.group('news_id'))] = (subject, date, is_new)
        return [
            NewsItemInfo(
                id=NewsItemId(news_id),
                origin=self.url,
                pupil_id=pupil_id,
                subject=subject,
                timestamp=timestamp,
                is_unread=is_new,
            )
            for (news_id, (subject, timestamp, is_new)) in sorted(
                    news_map.items())
        ]

    def _parse_news_title(self, title_elem: Tag) -> Tuple[str, bool]:
        labels = set()
        for label in title_elem.select("span.label"):
            labels.add(label.text.lower())
            label.replace_with('')
        subject = title_elem.text.strip()
        is_new = ('new' in labels)
        return (subject, is_new)

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
        date_span = select(metadata, 'span.small')
        timestamp = _parse_timestamp(date_span.text.split()[-1])
        date_span.replace_with('')
        sender = self._parse_news_item_sender(metadata)

        return NewsItem.from_info_and_attrs(
            news_item_info,
            timestamp=timestamp,
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

    def _parse_news_item_sender(self, metadata: Tag) -> Person:
        person = self._parse_person_element(metadata)
        person.name = _switch_parenthesed_parts(person.name)
        return person

    def _parse_person_element(self, element: Tag) -> Person:
        profile_link: Optional[Tag]
        if element.name == 'a' and 'profile-link' in element.get('class', []):
            profile_link = element
        else:
            profile_link = element.select_one('a.profile-link')
        if profile_link:
            return self._parse_profile_link(profile_link)
        else:
            text_lines = element.text.strip().splitlines() or ['']
            return Person(text_lines[0].strip())

    def _parse_profile_link(self, profile_link: Tag) -> Person:
        profile_href = profile_link.get('href', '')
        match = PROFILE_HREF_RX.match(profile_href)
        if not match:
            raise Exception(f'Cannot parse profile link: {profile_link}')
        return Person(
            name=profile_link.text,
            id=int(match.group(2)),
            type=match.group(1),
        )

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
    special_date_function = SPECIAL_DATES.get(string.strip().lower())
    if special_date_function:
        string = str(special_date_function())
    elif YEARLESS_DATE_RX.match(string):
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
