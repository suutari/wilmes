import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import NamedTuple, NewType

from bs4 import BeautifulSoup

PupilId = NewType('PupilId', str)
MessageId = NewType('MessageId', int)
NewsItemId = NewType('NewsItemId', int)


class Pupil(NamedTuple):
    id: PupilId
    name: str


@dataclass
class MessageInfo:
    id: MessageId
    origin: str  # URL of the system this message is from
    pupil_id: PupilId
    subject: str
    timestamp: datetime
    folder: str
    sender_id: int
    sender: str
    is_unread: bool

    def __str__(self) -> str:
        return (
            f'{self.timestamp:%Y-%m-%d %H:%M} '
            f'{self.sender:40} '
            f'{"* " if self.is_unread else "  "}'
            f'{self.subject}')


@dataclass
class Message(MessageInfo):
    body: str

    @classmethod
    def from_info_and_body(cls, info: MessageInfo, body: str) -> 'Message':
        message_data = dict(asdict(info), body=body)
        return cls(**message_data)

    def __str__(self) -> str:
        return self.to_text()

    def to_text(self, width: int = 70) -> str:
        return (
            f'Subject: {self.subject}\n'
            f'Date: {self.timestamp}\n'
            f'From: {self.sender}\n'
            f'\n'
            f'{self.get_cleaned_body_text(width)}')

    def get_cleaned_body_text(self, width: int = 70) -> str:
        body_text = BeautifulSoup(self.body, features='lxml').get_text()
        return '\n\n'.join(
            '\n'.join(textwrap.wrap(
                line.replace('\xa0', ' ').rstrip(),
                width=width))
            for line in body_text.splitlines())


@dataclass
class NewsItemInfo:
    id: NewsItemId
    origin: str  # URL of the system this message is from
    pupil_id: PupilId
    subject: str


@dataclass
class NewsItem(NewsItemInfo):
    timestamp: datetime
    sender_id: int
    sender: str
    body: str

    @classmethod
    def from_info_and_attrs(
            cls,
            info: NewsItemInfo,
            *,
            timestamp: datetime,
            sender_id: int,
            sender: str,
            body: str,
    ) -> 'NewsItem':
        return cls(
            timestamp=timestamp,
            sender_id=sender_id,
            sender=sender,
            body=body,
            **asdict(info))
