from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from .models import Notification, User


@dataclass(frozen=True)
class Message:
    kind: str
    title: str
    body: str
    link: str = ""


class MessageProvider(Protocol):
    def send(self, recipient: User, message: Message) -> None: ...


class CalendarPublisher(Protocol):
    def upsert(self, booking_id: str, room_id: str) -> None: ...
    def remove(self, booking_id: str, room_id: str) -> None: ...


class InAppProvider:
    def __init__(self, db: Session):
        self.db = db

    def send(self, recipient: User, message: Message) -> None:
        self.db.add(Notification(user_id=recipient.id, kind=message.kind,
                                 title=message.title, body=message.body, link=message.link))


class Messaging:
    """Channels are injected at composition time; missing providers never send."""

    def __init__(self, providers: dict[str, MessageProvider]):
        self.providers = providers

    def send(self, channel: str, recipient: User, message: Message) -> None:
        provider = self.providers.get(channel)
        if provider is None:
            raise ValueError(f"Canal {channel} não está configurado.")
        provider.send(recipient, message)


def in_app_messaging(db: Session) -> Messaging:
    return Messaging({"in_app": InAppProvider(db)})
