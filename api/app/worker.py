import logging
import time
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import delete, select

from .db import SessionLocal
from .integrations import Message, in_app_messaging
from .models import Booking, Notification, Series, Session, User, now
from .scheduling import expand_series


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("crass.worker")


def run_once():
    with SessionLocal() as db:
        current = now()
        expired = db.scalars(select(Booking).where(Booking.status == "pending",
            Booking.expires_at <= current)).all()
        for booking in expired:
            booking.status = "expired"
            user = db.get(User, booking.organizer_id)
            if user:
                in_app_messaging(db).send("in_app", user, Message(
                    "booking_expired", "Solicitação expirada", booking.title,
                    f"/reservas/{booking.id}"))
        for series in db.scalars(select(Series).where(Series.active.is_(True),
            Series.generated_until < current + relativedelta(months=11))).all():
            expand_series(db, series, horizon=current + relativedelta(months=12))
        reminder_start = current + timedelta(minutes=29)
        reminder_end = current + timedelta(minutes=31)
        upcoming = db.scalars(select(Booking).where(Booking.status == "confirmed",
            Booking.starts_at >= reminder_start, Booking.starts_at < reminder_end)).all()
        for booking in upcoming:
            link = f"/reservas/{booking.id}"
            exists = db.scalar(select(Notification.id).where(
                Notification.user_id == booking.organizer_id,
                Notification.kind == "booking_reminder", Notification.link == link).limit(1))
            if not exists:
                user = db.get(User, booking.organizer_id)
                if user:
                    in_app_messaging(db).send("in_app", user, Message(
                        "booking_reminder", "Reunião em 30 minutos", booking.title, link))
        db.execute(delete(Session).where(Session.expires_at < current))
        db.commit()
        log.info("expiradas=%d lembretes=%d", len(expired), len(upcoming))


if __name__ == "__main__":
    while True:
        try:
            run_once()
        except Exception:
            log.exception("Falha no processamento; nova tentativa em 60 segundos")
        time.sleep(60)
