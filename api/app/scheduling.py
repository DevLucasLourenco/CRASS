from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from dateutil import rrule
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Block, Booking, Room, Series, Settings, now


ACTIVE = ("pending", "confirmed")


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(422, "Informe data e horário com fuso horário.")
    return value.astimezone(timezone.utc)


def overlap(start: datetime, end: datetime, other_start, other_end):
    return and_(other_start < end, other_end > start)


def rules_for(settings: Settings, room: Room) -> dict:
    names = ("opening_time", "closing_time", "min_notice_minutes",
             "max_duration_minutes", "cancel_notice_minutes")
    return {name: (room.rules or {}).get(name, getattr(settings, name)) for name in names}


def validate_interval(db: Session, room: Room, start: datetime, end: datetime,
                      attendees: int, *, check_notice: bool = True) -> tuple[datetime, datetime]:
    start, end = utc(start), utc(end)
    if not room.active:
        raise HTTPException(409, "A sala está indisponível.")
    if start >= end:
        raise HTTPException(422, "O término deve ocorrer depois do início.")
    if attendees < 1 or attendees > room.capacity:
        raise HTTPException(422, "Quantidade de pessoas incompatível com a capacidade da sala.")
    settings = db.get(Settings, 1)
    policy = rules_for(settings, room)
    local_zone = ZoneInfo(settings.timezone)
    local_start, local_end = start.astimezone(local_zone), end.astimezone(local_zone)
    opening = time.fromisoformat(policy["opening_time"])
    closing = time.fromisoformat(policy["closing_time"])
    if local_start.date() != local_end.date() or not opening <= local_start.time().replace(tzinfo=None) < closing or local_end.time().replace(tzinfo=None) > closing:
        raise HTTPException(422, "A reserva deve ocorrer no horário de funcionamento da sala.")
    if (end - start).total_seconds() > int(policy["max_duration_minutes"]) * 60:
        raise HTTPException(422, "A duração excede o limite da sala.")
    if check_notice and start < now() + timedelta(minutes=int(policy["min_notice_minutes"])):
        raise HTTPException(422, "A antecedência mínima não foi atendida.")
    return start, end


def has_conflict(db: Session, room_id: str, start: datetime, end: datetime,
                 exclude_booking_id: str | None = None) -> str | None:
    query = select(Booking.id).where(Booking.room_id == room_id,
        Booking.status.in_(ACTIVE), overlap(start, end, Booking.starts_at, Booking.ends_at))
    if exclude_booking_id:
        query = query.where(Booking.id != exclude_booking_id)
    if db.scalar(query.limit(1)):
        return "Já existe uma reserva nesse horário."
    if db.scalar(select(Block.id).where(Block.room_id == room_id,
        overlap(start, end, Block.starts_at, Block.ends_at)).limit(1)):
        return "A sala está bloqueada nesse horário."
    return None


def make_booking(db: Session, *, room: Room, organizer_id: str, title: str,
                 description: str, attendees: int, start: datetime, end: datetime,
                 series_id: str | None = None, approval_status: str | None = None,
                 check_notice: bool = True) -> Booking:
    start, end = validate_interval(db, room, start, end, attendees, check_notice=check_notice)
    conflict = has_conflict(db, room.id, start, end)
    if conflict:
        raise HTTPException(409, conflict)
    status = approval_status or ("pending" if room.approval_required else "confirmed")
    settings = db.get(Settings, 1)
    booking = Booking(room_id=room.id, organizer_id=organizer_id, title=title.strip(),
                      description=description.strip(), attendees=attendees,
                      starts_at=start, ends_at=end, status=status, series_id=series_id,
                      expires_at=now() + timedelta(minutes=settings.pending_minutes)
                      if status == "pending" else None)
    db.add(booking)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(409, "A sala acabou de ser reservada nesse horário.") from exc
    return booking


def recurrence_dates(series: Series, settings: Settings, after: datetime, horizon: datetime):
    zone = ZoneInfo(settings.timezone)
    local_start = series.starts_at.astimezone(zone)
    naive_start = local_start.replace(tzinfo=None)
    frequency = {"daily": rrule.DAILY, "weekly": rrule.WEEKLY,
                 "monthly": rrule.MONTHLY}[series.frequency]
    kwargs = {"freq": frequency, "interval": series.interval, "dtstart": naive_start}
    if series.weekdays and series.frequency == "weekly":
        kwargs["byweekday"] = [int(day) for day in series.weekdays]
    iterator = rrule.rrule(**kwargs)
    from_local = after.astimezone(zone).replace(tzinfo=None)
    to_local = horizon.astimezone(zone).replace(tzinfo=None)
    duration = series.ends_at - series.starts_at
    for local_date in iterator.between(from_local, to_local, inc=True):
        start = local_date.replace(tzinfo=zone).astimezone(timezone.utc)
        if start < after or start < now():
            continue
        if series.until and start > series.until:
            break
        yield start, start + duration


def expand_series(db: Session, series: Series, *, horizon: datetime | None = None) -> list[str]:
    settings = db.get(Settings, 1)
    room = db.get(Room, series.room_id)
    horizon = horizon or now() + relativedelta(months=12)
    skipped = list(series.skipped or [])
    from_date = series.generated_until + timedelta(seconds=1)
    for start, end in recurrence_dates(series, settings, from_date, horizon):
        try:
            with db.begin_nested():
                make_booking(db, room=room, organizer_id=series.organizer_id,
                             title=series.title, description=series.description,
                             attendees=series.attendees, start=start, end=end,
                             series_id=series.id, approval_status=series.approval_status,
                             check_notice=False)
        except (HTTPException, IntegrityError):
            skipped.append(start.isoformat())
    series.skipped = skipped
    series.generated_until = horizon
    db.flush()
    return skipped


def booking_conflicts_block(db: Session, booking: Booking) -> bool:
    return db.scalar(select(Block.id).where(Block.room_id == booking.room_id,
        overlap(booking.starts_at, booking.ends_at, Block.starts_at, Block.ends_at)).limit(1)) is not None
