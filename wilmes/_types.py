import textwrap
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, NamedTuple, NewType, Optional

from bs4 import BeautifulSoup

PupilId = NewType('PupilId', str)
MessageId = NewType('MessageId', int)
NewsItemId = NewType('NewsItemId', int)


class Pupil(NamedTuple):
    id: PupilId
    name: str


@dataclass
class Person:
    name: str
    id: Optional[int] = None
    type: Optional[str] = None


@dataclass
class MessageInfo:
    id: MessageId
    origin: str  # URL of the system this message is from
    pupil_id: PupilId
    subject: str
    timestamp: datetime
    folder: str
    sender: Person
    reply_count: int
    is_unread: bool

    def __str__(self) -> str:
        return (
            f'{self.timestamp:%Y-%m-%d %H:%M} '
            f'{self.sender.name:40} '
            f'{"* " if self.is_unread else "  "}'
            f'{self.subject}')


class _MessageWithBody:
    timestamp: datetime
    sender: Person
    body: str

    def __str__(self) -> str:
        return self.to_text()

    def to_text(self, width: int = 70) -> str:
        return (
            f'{self.get_header_lines()}'
            f'\n'
            f'{self.get_cleaned_body_text(width)}')

    def get_header_lines(self) -> str:
        return (
            f'Date: {self.timestamp}\n'
            f'From: {self.sender.name}\n'
        )

    def get_cleaned_body_text(self, width: int = 70) -> str:
        body_text = BeautifulSoup(self.body, features='lxml').get_text()
        return '\n\n'.join(
            '\n'.join(textwrap.wrap(
                line.replace('\xa0', ' ').rstrip(),
                width=width))
            for line in body_text.splitlines())


@dataclass
class ReplyMessage(_MessageWithBody):
    timestamp: datetime
    sender: Person
    body: str


@dataclass
class Message(_MessageWithBody, MessageInfo):
    recipients: List[Person]
    body: str
    replies: List[ReplyMessage]

    @classmethod
    def from_info_and_attrs(
            cls,
            info: MessageInfo,
            recipients: Iterable[Person],
            body: str,
            replies: Iterable[ReplyMessage] = (),
    ) -> 'Message':
        return cls(
            id=info.id,
            origin=info.origin,
            pupil_id=info.pupil_id,
            subject=info.subject,
            timestamp=info.timestamp,
            folder=info.folder,
            sender=info.sender,
            reply_count=info.reply_count,
            is_unread=info.is_unread,
            recipients=list(recipients),
            body=body,
            replies=list(replies),
        )

    def get_header_lines(self) -> str:
        return f'Subject: {self.subject}\n' + super().get_header_lines()


@dataclass
class NewsItemInfo:
    id: NewsItemId
    origin: str  # URL of the system this message is from
    pupil_id: PupilId
    subject: str


@dataclass
class NewsItem(_MessageWithBody, NewsItemInfo):
    timestamp: datetime
    sender: Person
    body: str

    @classmethod
    def from_info_and_attrs(
            cls,
            info: NewsItemInfo,
            *,
            timestamp: datetime,
            sender: Person,
            body: str,
    ) -> 'NewsItem':
        return cls(
            id=info.id,
            origin=info.origin,
            pupil_id=info.pupil_id,
            subject=info.subject,
            timestamp=timestamp,
            sender=sender,
            body=body,
        )

    def get_header_lines(self) -> str:
        return f'Subject: {self.subject}\n' + super().get_header_lines()
