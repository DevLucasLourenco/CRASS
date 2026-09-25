import hashlib
import io
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession
from PIL import Image

from .db import Base, SessionLocal, engine, get_db
from .integrations import Message, in_app_messaging
from .models import Audit, Block, Booking, Building, ChannelProviderConfig, Incident, Notification, Room, RoomCalendarLink, RoomPhoto, Series, Session as UserSession, Settings, User, now
from .scheduling import ACTIVE, booking_conflicts_block, expand_series, has_conflict, make_booking, overlap, rules_for, utc, validate_interval
from .security import (COOKIE_NAME, SESSION_DAYS, create_session, csrf_for, current_user,
                       generate_recovery_codes, hash_password, new_totp_secret,
                       recovery_hash, require, session_hash, verify_password, verify_totp)


UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="CRASS API", version="0.1.0")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def startup():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.get(Settings, 1):
            db.add(Settings(id=1))
        if not db.scalar(select(User.id).limit(1)):
            email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
            password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
            if not email or len(password) < 12:
                raise RuntimeError("Configure BOOTSTRAP_ADMIN_EMAIL e BOOTSTRAP_ADMIN_PASSWORD (mínimo 12 caracteres).")
            db.add(User(name="Administrador", email=email, password_hash=hash_password(password),
                        role="admin", must_change_password=True))
        db.commit()


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path != "/auth/login":
        token = request.cookies.get(COOKIE_NAME)
        if token and request.headers.get("X-CSRF-Token") != csrf_for(token):
            return Response("Token de segurança inválido.", status_code=403)
    return await call_next(request)


def user_data(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role,
            "active": user.active, "must_change_password": user.must_change_password,
            "totp_enabled": bool(user.totp_secret)}


def audit(db: DbSession, actor: User | None, action: str, subject: str,
          subject_id: str, detail: dict | None = None):
    db.add(Audit(actor_id=actor.id if actor else None, action=action, subject=subject,
                 subject_id=subject_id, detail=detail or {}))


def notify(db: DbSession, user: User, kind: str, title: str, body: str, link: str = ""):
    in_app_messaging(db).send("in_app", user, Message(kind, title, body, link))


def booking_data(db: DbSession, booking: Booking) -> dict:
    return {"id": booking.id, "room_id": booking.room_id, "room_name": booking.room.name,
            "organizer_id": booking.organizer_id, "organizer_name": booking.organizer.name,
            "series_id": booking.series_id, "title": booking.title,
            "description": booking.description, "attendees": booking.attendees,
            "starts_at": booking.starts_at, "ends_at": booking.ends_at,
            "status": booking.status, "expires_at": booking.expires_at,
            "ended_at": booking.ended_at, "block_conflict": booking_conflicts_block(db, booking)}


class LoginIn(BaseModel):
    email: str
    password: str
    code: str | None = None


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12)


class CodeIn(BaseModel):
    code: str


class UserIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: str
    role: str = "user"


class UserPatch(BaseModel):
    name: str | None = None
    role: str | None = None
    active: bool | None = None


class SettingsPatch(BaseModel):
    organization: str | None = None
    timezone: str | None = None
    pending_minutes: int | None = Field(default=None, ge=1)
    opening_time: str | None = None
    closing_time: str | None = None
    min_notice_minutes: int | None = Field(default=None, ge=0)
    max_duration_minutes: int | None = Field(default=None, ge=1)
    cancel_notice_minutes: int | None = Field(default=None, ge=0)


class BuildingIn(BaseModel):
    name: str = Field(min_length=2)
    address: str = ""


class RoomIn(BaseModel):
    building_id: str
    name: str = Field(min_length=2)
    floor: str = ""
    location: str = ""
    capacity: int = Field(ge=1)
    features: list[str] = []
    approval_required: bool = False
    rules: dict = {}
    active: bool = True


class RoomPatch(BaseModel):
    building_id: str | None = None
    name: str | None = None
    floor: str | None = None
    location: str | None = None
    capacity: int | None = Field(default=None, ge=1)
    features: list[str] | None = None
    approval_required: bool | None = None
    rules: dict | None = None
    active: bool | None = None


def validate_room_rules(db: DbSession, rules: dict):
    if not isinstance(rules, dict):
        raise HTTPException(422, "As regras da sala devem ser um objeto.")
    allowed = {"opening_time", "closing_time", "min_notice_minutes",
               "max_duration_minutes", "cancel_notice_minutes"}
    if set(rules) - allowed:
        raise HTTPException(422, "Regra da sala desconhecida.")
    settings = db.get(Settings, 1)
    merged = {key: rules.get(key, getattr(settings, key)) for key in allowed}
    try:
        opening = datetime.strptime(merged["opening_time"], "%H:%M").time()
        closing = datetime.strptime(merged["closing_time"], "%H:%M").time()
        if opening >= closing:
            raise ValueError()
        for key in ("min_notice_minutes", "max_duration_minutes", "cancel_notice_minutes"):
            value = merged[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < (1 if key == "max_duration_minutes" else 0):
                raise ValueError()
    except (TypeError, ValueError):
        raise HTTPException(422, "Regras da sala inválidas. Confira horários e prazos.")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login")
def login(data: LoginIn, response: Response, db: DbSession = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if not user or not user.active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "E-mail ou senha inválidos.")
    if user.totp_secret:
        hashes = list(user.recovery_hashes or [])
        candidate = recovery_hash(data.code or "")
        if verify_totp(user.totp_secret, data.code or ""):
            pass
        elif candidate in hashes:
            hashes.remove(candidate)
            user.recovery_hashes = hashes
            db.commit()
        else:
            raise HTTPException(401, "Código de verificação inválido.")
    token = create_session(db, user)
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_DAYS * 86400,
                        httponly=True, secure=os.getenv("COOKIE_SECURE", "true") == "true",
                        samesite="lax", path="/")
    return {"user": user_data(user), "csrf": csrf_for(token)}


@app.get("/auth/me")
def me(request: Request, user: User = Depends(current_user)):
    return {"user": user_data(user), "csrf": csrf_for(request.cookies[COOKIE_NAME])}


@app.post("/auth/logout")
def logout(request: Request, response: Response, db: DbSession = Depends(get_db),
           user: User = Depends(current_user)):
    from .models import Session
    session = db.get(Session, session_hash(request.cookies[COOKIE_NAME]))
    if session:
        db.delete(session)
        db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.post("/auth/password")
def change_password(data: PasswordIn, db: DbSession = Depends(get_db),
                    user: User = Depends(current_user)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Senha atual incorreta.")
    user.password_hash = hash_password(data.new_password)
    user.must_change_password = False
    audit(db, user, "password_changed", "user", user.id)
    db.commit()
    return {"ok": True}


@app.post("/auth/totp/setup")
def totp_setup(db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    user.totp_pending = new_totp_secret()
    db.commit()
    return {"secret": user.totp_pending,
            "otpauth_url": f"otpauth://totp/CRASS:{user.email}?secret={user.totp_pending}&issuer=CRASS"}


@app.post("/auth/totp/confirm")
def totp_confirm(data: CodeIn, db: DbSession = Depends(get_db),
                 user: User = Depends(current_user)):
    if not user.totp_pending or not verify_totp(user.totp_pending, data.code):
        raise HTTPException(400, "Código inválido.")
    codes, hashes = generate_recovery_codes()
    user.totp_secret, user.totp_pending, user.recovery_hashes = user.totp_pending, None, hashes
    db.commit()
    return {"recovery_codes": codes}


@app.post("/auth/totp/disable")
def totp_disable(data: CodeIn, db: DbSession = Depends(get_db),
                 user: User = Depends(current_user)):
    if not user.totp_secret or not verify_totp(user.totp_secret, data.code):
        raise HTTPException(400, "Código inválido.")
    user.totp_secret, user.recovery_hashes = None, []
    db.commit()
    return {"ok": True}


@app.get("/users")
def list_users(db: DbSession = Depends(get_db), user: User = Depends(require("admin", "manager"))):
    return [user_data(item) for item in db.scalars(select(User).order_by(User.name)).all()]


@app.post("/users")
def create_user(data: UserIn, db: DbSession = Depends(get_db), user: User = Depends(require("admin"))):
    if data.role not in ("admin", "manager", "user"):
        raise HTTPException(422, "Perfil inválido.")
    password = secrets.token_urlsafe(18)
    item = User(name=data.name.strip(), email=data.email.strip().lower(), role=data.role,
                password_hash=hash_password(password), must_change_password=True)
    db.add(item)
    try:
        db.flush()
        audit(db, user, "user_created", "user", item.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "E-mail já cadastrado.")
    return {"user": user_data(item), "temporary_password": password}


@app.patch("/users/{user_id}")
def patch_user(user_id: str, data: UserPatch, db: DbSession = Depends(get_db),
               user: User = Depends(require("admin"))):
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(404, "Usuário não encontrado.")
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if changes.get("role") and changes["role"] not in ("admin", "manager", "user"):
        raise HTTPException(422, "Perfil inválido.")
    if item.id == user.id and (changes.get("active") is False or changes.get("role", "admin") != "admin"):
        raise HTTPException(400, "Não é possível remover seu próprio acesso administrativo.")
    for key, value in changes.items():
        setattr(item, key, value)
    audit(db, user, "user_updated", "user", item.id, changes)
    db.commit()
    return user_data(item)


@app.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, db: DbSession = Depends(get_db),
                   user: User = Depends(require("admin"))):
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(404, "Usuário não encontrado.")
    password = secrets.token_urlsafe(18)
    item.password_hash = hash_password(password)
    item.must_change_password = True
    item.totp_secret, item.totp_pending, item.recovery_hashes = None, None, []
    db.execute(delete(UserSession).where(UserSession.user_id == item.id))
    audit(db, user, "password_reset", "user", item.id)
    db.commit()
    return {"temporary_password": password}


@app.get("/settings")
def get_settings(db: DbSession = Depends(get_db), user: User = Depends(require("admin", "manager"))):
    settings = db.get(Settings, 1)
    return {key: getattr(settings, key) for key in SettingsPatch.model_fields} | {
        "channels": settings.channels, "calendar_enabled": False}


@app.patch("/settings")
def patch_settings(data: SettingsPatch, db: DbSession = Depends(get_db),
                   user: User = Depends(require("admin"))):
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if "timezone" in changes:
        try:
            ZoneInfo(changes["timezone"])
        except (KeyError, TypeError):
            raise HTTPException(422, "Fuso horário inválido.")
    for key in ("opening_time", "closing_time"):
        if key in changes:
            try:
                datetime.strptime(changes[key], "%H:%M")
            except ValueError:
                raise HTTPException(422, "Use HH:MM para horários de funcionamento.")
    settings = db.get(Settings, 1)
    for key, value in changes.items():
        setattr(settings, key, value)
    if settings.opening_time >= settings.closing_time:
        raise HTTPException(422, "O horário de abertura deve anteceder o fechamento.")
    audit(db, user, "settings_updated", "settings", "1", changes)
    db.commit()
    return get_settings(db, user)


@app.get("/buildings")
def buildings(db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    return [{"id": item.id, "name": item.name, "address": item.address}
            for item in db.scalars(select(Building).order_by(Building.name)).all()]


@app.post("/buildings")
def create_building(data: BuildingIn, db: DbSession = Depends(get_db),
                    user: User = Depends(require("admin"))):
    item = Building(name=data.name.strip(), address=data.address.strip())
    db.add(item)
    try:
        db.flush()
        audit(db, user, "building_created", "building", item.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Prédio já cadastrado.")
    return {"id": item.id, "name": item.name, "address": item.address}


def room_data(room: Room) -> dict:
    photos = [photo.path for photo in room.photos]
    if room.photo and room.photo not in photos:
        photos.insert(0, room.photo)
    return {"id": room.id, "building_id": room.building_id,
            "building_name": room.building.name, "name": room.name,
            "floor": room.floor, "location": room.location,
            "capacity": room.capacity, "features": room.features,
            "photo": photos[-1] if photos else None, "photos": photos,
            "approval_required": room.approval_required,
            "rules": room.rules, "active": room.active}


@app.get("/rooms")
def rooms(building_id: str | None = None, floor: str | None = None,
          capacity: int | None = None, feature: str | None = None, q: str | None = None,
          starts_at: datetime | None = None, ends_at: datetime | None = None,
          db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    query = select(Room).order_by(Room.name)
    if building_id:
        query = query.where(Room.building_id == building_id)
    if floor:
        query = query.where(Room.floor == floor)
    if capacity:
        query = query.where(Room.capacity >= capacity)
    if q:
        query = query.where(Room.name.ilike(f"%{q.strip()}%"))
    if (starts_at is None) != (ends_at is None):
        raise HTTPException(422, "Informe início e término para consultar disponibilidade.")
    if starts_at and ends_at:
        start, end = utc(starts_at), utc(ends_at)
        if start >= end:
            raise HTTPException(422, "O término deve ocorrer depois do início.")
    result = []
    for room in db.scalars(query).all():
        if feature and feature not in (room.features or []):
            continue
        item = room_data(room)
        if starts_at and ends_at:
            try:
                validate_interval(db, room, start, end, capacity or 1)
                item["available"] = not has_conflict(db, room.id, start, end)
            except HTTPException:
                item["available"] = False
        result.append(item)
    return result


@app.post("/rooms")
def create_room(data: RoomIn, db: DbSession = Depends(get_db),
                user: User = Depends(require("admin", "manager"))):
    if not db.get(Building, data.building_id):
        raise HTTPException(404, "Prédio não encontrado.")
    if user.role != "admin" and (data.rules or data.approval_required):
        raise HTTPException(403, "Somente o administrador configura regras de reserva.")
    validate_room_rules(db, data.rules)
    item = Room(**data.model_dump())
    db.add(item)
    try:
        db.flush()
        audit(db, user, "room_created", "room", item.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe sala com esse nome no prédio.")
    return room_data(item)


@app.patch("/rooms/{room_id}")
def patch_room(room_id: str, data: RoomPatch, db: DbSession = Depends(get_db),
               user: User = Depends(require("admin", "manager"))):
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(404, "Sala não encontrada.")
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if user.role != "admin" and ("rules" in changes or "approval_required" in changes):
        raise HTTPException(403, "Somente o administrador configura regras de reserva.")
    if changes.get("building_id") and not db.get(Building, changes["building_id"]):
        raise HTTPException(404, "Prédio não encontrado.")
    if "rules" in changes:
        validate_room_rules(db, changes["rules"])
    for key, value in changes.items():
        setattr(room, key, value)
    audit(db, user, "room_updated", "room", room.id, changes)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe sala com esse nome no prédio.")
    return room_data(room)


@app.post("/rooms/{room_id}/photo")
async def room_photo(room_id: str, file: UploadFile = File(...),
                     db: DbSession = Depends(get_db),
                     user: User = Depends(require("admin", "manager"))):
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(404, "Sala não encontrada.")
    raw = await file.read(5_000_001)
    if len(raw) > 5_000_000:
        raise HTTPException(413, "Foto maior que 5 MB.")
    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        image.thumbnail((1600, 1200))
    except Exception as exc:
        raise HTTPException(422, "Imagem inválida.") from exc
    name = f"{room.id}-{secrets.token_hex(5)}.jpg"
    image.save(UPLOAD_DIR / name, format="JPEG", quality=85)
    db.add(RoomPhoto(room_id=room.id, path=f"/api/uploads/{name}"))
    audit(db, user, "room_photo_added", "room", room.id)
    db.commit()
    return room_data(room)


class BookingIn(BaseModel):
    room_id: str
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    attendees: int = Field(ge=1)
    starts_at: datetime
    ends_at: datetime


class BookingPatch(BaseModel):
    room_id: str | None = None
    title: str | None = None
    description: str | None = None
    attendees: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class SeriesIn(BookingIn):
    frequency: str
    interval: int = Field(default=1, ge=1, le=52)
    weekdays: list[int] = []
    until: datetime | None = None


class SeriesChange(BaseModel):
    scope: str
    occurrence_id: str | None = None
    changes: BookingPatch
    frequency: str | None = None
    interval: int | None = Field(default=None, ge=1, le=52)
    weekdays: list[int] | None = None
    until: datetime | None = None


def can_manage_booking(user: User, booking: Booking):
    if user.role not in ("admin", "manager") and user.id != booking.organizer_id:
        raise HTTPException(403, "Você não pode alterar esta reserva.")


def check_cancel_window(db: DbSession, booking: Booking):
    policy = rules_for(db.get(Settings, 1), booking.room)
    if booking.starts_at < now() + timedelta(minutes=int(policy["cancel_notice_minutes"])):
        raise HTTPException(422, "O prazo de alteração ou cancelamento terminou.")


@app.get("/bookings")
def bookings(room_id: str | None = None, from_date: datetime | None = None,
             to_date: datetime | None = None, mine: bool = False,
             status: str | None = None, db: DbSession = Depends(get_db),
             user: User = Depends(current_user)):
    query = select(Booking).order_by(Booking.starts_at)
    if room_id:
        query = query.where(Booking.room_id == room_id)
    if from_date:
        query = query.where(Booking.ends_at > utc(from_date))
    if to_date:
        query = query.where(Booking.starts_at < utc(to_date))
    if mine:
        query = query.where(Booking.organizer_id == user.id)
    if status:
        query = query.where(Booking.status == status)
    return [booking_data(db, item) for item in db.scalars(query.limit(1000)).all()]


@app.post("/bookings")
def create_booking(data: BookingIn, db: DbSession = Depends(get_db),
                   user: User = Depends(current_user)):
    room = db.get(Room, data.room_id)
    if not room:
        raise HTTPException(404, "Sala não encontrada.")
    try:
        item = make_booking(db, room=room, organizer_id=user.id, title=data.title,
                            description=data.description, attendees=data.attendees,
                            start=data.starts_at, end=data.ends_at)
        audit(db, user, "booking_created", "booking", item.id)
        notify(db, user, "booking_created", "Reserva solicitada" if item.status == "pending" else "Reserva confirmada",
               f"{room.name}: {item.title}", f"/reservas/{item.id}")
        db.commit()
        return booking_data(db, item)
    except HTTPException:
        db.rollback()
        raise


@app.get("/bookings/{booking_id}")
def get_booking(booking_id: str, db: DbSession = Depends(get_db),
                user: User = Depends(current_user)):
    item = db.get(Booking, booking_id)
    if not item:
        raise HTTPException(404, "Reserva não encontrada.")
    return booking_data(db, item)


@app.patch("/bookings/{booking_id}")
def patch_booking(booking_id: str, data: BookingPatch,
                  db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    item = db.get(Booking, booking_id)
    if not item:
        raise HTTPException(404, "Reserva não encontrada.")
    can_manage_booking(user, item)
    if item.status not in ACTIVE:
        raise HTTPException(409, "Esta reserva não pode ser alterada.")
    check_cancel_window(db, item)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    room = db.get(Room, changes.get("room_id", item.room_id))
    if not room:
        raise HTTPException(404, "Sala não encontrada.")
    start = changes.get("starts_at", item.starts_at)
    end = changes.get("ends_at", item.ends_at)
    attendees = changes.get("attendees", item.attendees)
    start, end = validate_interval(db, room, start, end, attendees)
    conflict = has_conflict(db, room.id, start, end, item.id)
    if conflict:
        raise HTTPException(409, conflict)
    for key, value in changes.items():
        if key != "room_id":
            setattr(item, key, value)
    item.starts_at, item.ends_at = start, end
    item.room = room
    if "room_id" in changes or "starts_at" in changes or "ends_at" in changes:
        item.status = "pending" if room.approval_required else "confirmed"
        item.expires_at = (now() + timedelta(minutes=db.get(Settings, 1).pending_minutes)
                           if item.status == "pending" else None)
    try:
        db.flush()
        audit(db, user, "booking_updated", "booking", item.id, list(changes))
        notify(db, item.organizer, "booking_updated", "Reserva alterada", item.title, f"/reservas/{item.id}")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A sala acabou de ser reservada nesse horário.")
    return booking_data(db, item)


@app.post("/bookings/{booking_id}/approve")
def approve_booking(booking_id: str, db: DbSession = Depends(get_db),
                    user: User = Depends(require("admin", "manager"))):
    item = db.get(Booking, booking_id)
    if not item or item.status != "pending":
        raise HTTPException(409, "Reserva pendente não encontrada.")
    if item.expires_at and item.expires_at <= now():
        item.status = "expired"
        db.commit()
        raise HTTPException(409, "A solicitação expirou.")
    items = [item]
    if item.series_id:
        items = db.scalars(select(Booking).where(Booking.series_id == item.series_id,
                    Booking.status == "pending")).all()
        series = db.get(Series, item.series_id)
        series.approval_status = "confirmed"
    for row in items:
        row.status, row.expires_at = "confirmed", None
    audit(db, user, "booking_approved", "booking", item.id, {"count": len(items)})
    notify(db, item.organizer, "booking_approved", "Reserva aprovada", item.title,
           f"/reservas/{item.id}")
    db.commit()
    return {"approved": len(items)}


@app.post("/bookings/{booking_id}/reject")
def reject_booking(booking_id: str, db: DbSession = Depends(get_db),
                   user: User = Depends(require("admin", "manager"))):
    item = db.get(Booking, booking_id)
    if not item or item.status != "pending":
        raise HTTPException(409, "Reserva pendente não encontrada.")
    items = [item]
    if item.series_id:
        items = db.scalars(select(Booking).where(Booking.series_id == item.series_id,
                    Booking.status == "pending")).all()
        db.get(Series, item.series_id).active = False
    for row in items:
        row.status = "rejected"
    audit(db, user, "booking_rejected", "booking", item.id, {"count": len(items)})
    notify(db, item.organizer, "booking_rejected", "Reserva rejeitada", item.title,
           f"/reservas/{item.id}")
    db.commit()
    return {"rejected": len(items)}


@app.post("/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: str, db: DbSession = Depends(get_db),
                   user: User = Depends(current_user)):
    item = db.get(Booking, booking_id)
    if not item:
        raise HTTPException(404, "Reserva não encontrada.")
    can_manage_booking(user, item)
    if item.status not in ACTIVE:
        raise HTTPException(409, "Esta reserva não pode ser cancelada.")
    check_cancel_window(db, item)
    item.status = "cancelled"
    audit(db, user, "booking_cancelled", "booking", item.id)
    notify(db, item.organizer, "booking_cancelled", "Reserva cancelada", item.title,
           f"/reservas/{item.id}")
    db.commit()
    return booking_data(db, item)


@app.post("/bookings/{booking_id}/no-show")
def mark_no_show(booking_id: str, db: DbSession = Depends(get_db),
                 user: User = Depends(require("admin", "manager"))):
    item = db.get(Booking, booking_id)
    if not item or item.status != "confirmed":
        raise HTTPException(409, "Reserva confirmada não encontrada.")
    if now() < item.starts_at:
        raise HTTPException(422, "A reunião ainda não começou.")
    item.status, item.ended_at = "no_show", now()
    audit(db, user, "no_show", "booking", item.id)
    notify(db, item.organizer, "no_show", "Ausência registrada", item.title,
           f"/reservas/{item.id}")
    db.commit()
    return booking_data(db, item)


@app.post("/bookings/{booking_id}/end")
def end_booking(booking_id: str, db: DbSession = Depends(get_db),
                user: User = Depends(current_user)):
    item = db.get(Booking, booking_id)
    if not item:
        raise HTTPException(404, "Reserva não encontrada.")
    can_manage_booking(user, item)
    if item.status != "confirmed" or not item.starts_at <= now() < item.ends_at:
        raise HTTPException(409, "A reunião não está em andamento.")
    item.status, item.ended_at = "ended", now()
    audit(db, user, "booking_ended", "booking", item.id)
    db.commit()
    return booking_data(db, item)


@app.post("/series")
def create_series(data: SeriesIn, db: DbSession = Depends(get_db),
                  user: User = Depends(current_user)):
    if data.frequency not in ("daily", "weekly", "monthly") or any(d not in range(7) for d in data.weekdays):
        raise HTTPException(422, "Recorrência inválida.")
    room = db.get(Room, data.room_id)
    if not room:
        raise HTTPException(404, "Sala não encontrada.")
    start, end = validate_interval(db, room, data.starts_at, data.ends_at, data.attendees)
    until = utc(data.until) if data.until else None
    if until and until < start:
        raise HTTPException(422, "Data final anterior ao início da série.")
    series = Series(organizer_id=user.id, room_id=room.id, title=data.title.strip(),
                    description=data.description.strip(), attendees=data.attendees,
                    frequency=data.frequency, interval=data.interval, weekdays=data.weekdays,
                    starts_at=start, ends_at=end, until=until,
                    generated_until=start - timedelta(seconds=1),
                    approval_status="pending" if room.approval_required else "confirmed")
    db.add(series)
    db.flush()
    skipped = expand_series(db, series)
    audit(db, user, "series_created", "series", series.id, {"skipped": len(skipped)})
    notify(db, user, "series_created", "Série criada", data.title,
           f"/reservas?series={series.id}")
    db.commit()
    return {"id": series.id, "skipped": skipped,
            "created": db.scalar(select(func.count()).select_from(Booking).where(Booking.series_id == series.id))}


@app.get("/series/{series_id}")
def get_series(series_id: str, db: DbSession = Depends(get_db),
               user: User = Depends(current_user)):
    series = db.get(Series, series_id)
    if not series:
        raise HTTPException(404, "Série não encontrada.")
    return {key: getattr(series, key) for key in ("id", "organizer_id", "room_id", "title",
        "description", "attendees", "frequency", "interval", "weekdays", "starts_at",
        "ends_at", "until", "generated_until", "skipped", "approval_status", "active")}


@app.post("/series/{series_id}/change")
def change_series(series_id: str, data: SeriesChange, db: DbSession = Depends(get_db),
                  user: User = Depends(current_user)):
    series = db.get(Series, series_id)
    if not series or not series.active:
        raise HTTPException(404, "Série ativa não encontrada.")
    if user.role not in ("admin", "manager") and user.id != series.organizer_id:
        raise HTTPException(403, "Você não pode alterar esta série.")
    if data.scope not in ("occurrence", "future", "all"):
        raise HTTPException(422, "Escopo da alteração inválido.")
    if data.scope == "occurrence":
        item = db.get(Booking, data.occurrence_id)
        if not item or item.series_id != series.id:
            raise HTTPException(404, "Ocorrência não encontrada.")
        return {"booking": patch_booking(item.id, data.changes, db, user)}
    reference = None
    if data.scope == "future":
        cutoff_booking = db.get(Booking, data.occurrence_id)
        if not cutoff_booking or cutoff_booking.series_id != series.id:
            raise HTTPException(404, "Ocorrência inicial não encontrada.")
        cutoff = cutoff_booking.starts_at
    else:
        cutoff = now()
        if data.occurrence_id:
            reference = db.get(Booking, data.occurrence_id)
            if not reference or reference.series_id != series.id:
                raise HTTPException(404, "Ocorrência de referência não encontrada.")
    changes = data.changes.model_dump(exclude_unset=True, exclude_none=True)
    new_room_id = changes.get("room_id", series.room_id)
    room = db.get(Room, new_room_id)
    if not room:
        raise HTTPException(404, "Sala não encontrada.")
    if data.frequency and data.frequency not in ("daily", "weekly", "monthly"):
        raise HTTPException(422, "Recorrência inválida.")
    if data.weekdays is not None and any(day not in range(7) for day in data.weekdays):
        raise HTTPException(422, "Dias da semana inválidos.")
    if data.scope == "all" and reference:
        new_start = series.starts_at + (utc(changes["starts_at"]) - reference.starts_at) if "starts_at" in changes else series.starts_at
        new_end = series.ends_at + (utc(changes["ends_at"]) - reference.ends_at) if "ends_at" in changes else series.ends_at
    else:
        new_start = utc(changes.get("starts_at", cutoff if data.scope == "future" else series.starts_at))
        new_end = utc(changes.get("ends_at", cutoff_booking.ends_at if data.scope == "future" else series.ends_at))
    validate_interval(db, room, new_start, new_end, changes.get("attendees", series.attendees),
                      check_notice=False)
    future_rows = db.scalars(select(Booking).where(Booking.series_id == series.id,
        Booking.starts_at >= cutoff, Booking.status.in_(ACTIVE))).all()
    for row in future_rows:
        row.status = "cancelled"
    if data.scope == "future":
        series.until = cutoff - timedelta(seconds=1)
        target = Series(organizer_id=series.organizer_id, room_id=new_room_id,
                        title=changes.get("title", series.title),
                        description=changes.get("description", series.description),
                        attendees=changes.get("attendees", series.attendees),
                        frequency=data.frequency or series.frequency,
                        interval=data.interval or series.interval,
                        weekdays=data.weekdays if data.weekdays is not None else series.weekdays,
                        starts_at=new_start, ends_at=new_end,
                        until=utc(data.until) if data.until else None,
                        generated_until=now() - timedelta(seconds=1),
                        approval_status="pending" if room.approval_required else "confirmed")
        db.add(target)
        db.flush()
    else:
        target = series
        for key in ("room_id", "title", "description", "attendees"):
            if key in changes:
                setattr(target, key, changes[key])
        target.starts_at, target.ends_at = new_start, new_end
        if data.frequency:
            target.frequency = data.frequency
        if data.interval:
            target.interval = data.interval
        if data.weekdays is not None:
            target.weekdays = data.weekdays
        if data.until:
            target.until = utc(data.until)
        target.generated_until = now() - timedelta(seconds=1)
        target.skipped = []
        target.approval_status = "pending" if room.approval_required else "confirmed"
    db.flush()
    skipped = expand_series(db, target)
    audit(db, user, "series_changed", "series", target.id,
          {"scope": data.scope, "cancelled": len(future_rows), "skipped": len(skipped)})
    notify(db, db.get(User, series.organizer_id), "series_changed", "Série alterada", target.title)
    db.commit()
    return {"id": target.id, "cancelled": len(future_rows), "skipped": skipped}


class SeriesCancel(BaseModel):
    scope: str = "all"
    occurrence_id: str | None = None


@app.post("/series/{series_id}/cancel")
def cancel_series(series_id: str, data: SeriesCancel, db: DbSession = Depends(get_db),
                  user: User = Depends(current_user)):
    series = db.get(Series, series_id)
    if not series:
        raise HTTPException(404, "Série não encontrada.")
    if user.role not in ("admin", "manager") and user.id != series.organizer_id:
        raise HTTPException(403, "Você não pode cancelar esta série.")
    if data.scope == "occurrence":
        item = db.get(Booking, data.occurrence_id)
        if not item or item.series_id != series.id:
            raise HTTPException(404, "Ocorrência não encontrada.")
        return {"booking": cancel_booking(item.id, db, user)}
    if data.scope not in ("future", "all"):
        raise HTTPException(422, "Escopo inválido.")
    cutoff = now()
    if data.scope == "future":
        item = db.get(Booking, data.occurrence_id)
        if not item or item.series_id != series.id:
            raise HTTPException(404, "Ocorrência inicial não encontrada.")
        cutoff = item.starts_at
        series.until = cutoff - timedelta(seconds=1)
    else:
        series.active = False
    rows = db.scalars(select(Booking).where(Booking.series_id == series.id,
        Booking.starts_at >= cutoff, Booking.status.in_(ACTIVE))).all()
    for row in rows:
        row.status = "cancelled"
    audit(db, user, "series_cancelled", "series", series.id,
          {"scope": data.scope, "count": len(rows)})
    db.commit()
    return {"cancelled": len(rows)}


class BlockIn(BaseModel):
    room_id: str
    starts_at: datetime
    ends_at: datetime
    reason: str = Field(min_length=2)


@app.get("/blocks")
def list_blocks(room_id: str | None = None, db: DbSession = Depends(get_db),
                user: User = Depends(current_user)):
    query = select(Block).order_by(Block.starts_at.desc())
    if room_id:
        query = query.where(Block.room_id == room_id)
    return [{"id": row.id, "room_id": row.room_id, "starts_at": row.starts_at,
             "ends_at": row.ends_at, "reason": row.reason}
            for row in db.scalars(query.limit(500)).all()]


@app.post("/blocks")
def create_block(data: BlockIn, db: DbSession = Depends(get_db),
                 user: User = Depends(require("admin", "manager"))):
    if not db.get(Room, data.room_id):
        raise HTTPException(404, "Sala não encontrada.")
    start, end = utc(data.starts_at), utc(data.ends_at)
    if start >= end:
        raise HTTPException(422, "Período inválido.")
    item = Block(room_id=data.room_id, author_id=user.id, starts_at=start,
                 ends_at=end, reason=data.reason.strip())
    db.add(item)
    db.flush()
    affected = db.scalars(select(Booking).where(Booking.room_id == item.room_id,
        Booking.status == "confirmed", overlap(start, end, Booking.starts_at, Booking.ends_at))).all()
    for booking in affected:
        notify(db, booking.organizer, "block_conflict", "Conflito com bloqueio",
               f"A reserva {booking.title} coincide com um bloqueio.", f"/reservas/{booking.id}")
    audit(db, user, "block_created", "block", item.id, {"affected": len(affected)})
    db.commit()
    return {"id": item.id, "affected_bookings": [row.id for row in affected]}


@app.delete("/blocks/{block_id}")
def delete_block(block_id: str, db: DbSession = Depends(get_db),
                 user: User = Depends(require("admin", "manager"))):
    item = db.get(Block, block_id)
    if not item:
        raise HTTPException(404, "Bloqueio não encontrado.")
    db.delete(item)
    audit(db, user, "block_removed", "block", block_id)
    db.commit()
    return {"ok": True}


class IncidentIn(BaseModel):
    room_id: str
    title: str = Field(min_length=2)
    description: str = ""


class IncidentPatch(BaseModel):
    status: str


@app.get("/incidents")
def list_incidents(room_id: str | None = None, status: str | None = None,
                   db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    query = select(Incident).order_by(Incident.created_at.desc())
    if room_id:
        query = query.where(Incident.room_id == room_id)
    if status:
        query = query.where(Incident.status == status)
    return [{"id": row.id, "room_id": row.room_id, "reporter_id": row.reporter_id,
             "title": row.title, "description": row.description, "status": row.status,
             "created_at": row.created_at, "resolved_at": row.resolved_at}
            for row in db.scalars(query.limit(500)).all()]


@app.post("/incidents")
def create_incident(data: IncidentIn, db: DbSession = Depends(get_db),
                    user: User = Depends(current_user)):
    if not db.get(Room, data.room_id):
        raise HTTPException(404, "Sala não encontrada.")
    item = Incident(room_id=data.room_id, reporter_id=user.id,
                    title=data.title.strip(), description=data.description.strip())
    db.add(item)
    db.flush()
    audit(db, user, "incident_created", "incident", item.id)
    db.commit()
    return {"id": item.id, "status": item.status}


@app.patch("/incidents/{incident_id}")
def patch_incident(incident_id: str, data: IncidentPatch, db: DbSession = Depends(get_db),
                   user: User = Depends(require("admin", "manager"))):
    item = db.get(Incident, incident_id)
    if not item:
        raise HTTPException(404, "Ocorrência não encontrada.")
    if data.status not in ("open", "in_progress", "resolved"):
        raise HTTPException(422, "Estado inválido.")
    item.status = data.status
    item.resolved_at = now() if data.status == "resolved" else None
    audit(db, user, "incident_updated", "incident", item.id, {"status": item.status})
    db.commit()
    return {"id": item.id, "status": item.status}


@app.get("/notifications")
def notifications(db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id)
                      .order_by(Notification.created_at.desc()).limit(100)).all()
    return [{"id": row.id, "kind": row.kind, "title": row.title, "body": row.body,
             "link": row.link, "created_at": row.created_at, "read_at": row.read_at}
            for row in rows]


@app.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, db: DbSession = Depends(get_db),
                           user: User = Depends(current_user)):
    item = db.get(Notification, notification_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Aviso não encontrado.")
    item.read_at = now()
    db.commit()
    return {"ok": True}


@app.get("/dashboard")
def dashboard(db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    settings = db.get(Settings, 1)
    zone = ZoneInfo(settings.timezone)
    local = now().astimezone(zone)
    start = datetime.combine(local.date(), datetime.min.time(), zone).astimezone(timezone.utc)
    end = datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), zone).astimezone(timezone.utc)
    rooms = db.scalars(select(Room).where(Room.active.is_(True)).order_by(Room.name)).all()
    day = db.scalars(select(Booking).where(Booking.status.in_(ACTIVE),
                    overlap(start, end, Booking.starts_at, Booking.ends_at))
                    .order_by(Booking.starts_at)).all()
    blocks = db.scalars(select(Block).where(
        overlap(start, end, Block.starts_at, Block.ends_at))).all()
    busy = {row.room_id for row in day if row.status == "confirmed" and row.starts_at <= now() < row.ends_at}
    unavailable = {row.room_id for row in blocks if row.starts_at <= now() < row.ends_at}
    unavailable.update(row.room_id for row in day if row.status == "pending" and row.starts_at <= now() < row.ends_at)
    busy -= unavailable
    next_by_room = {}
    for row in day:
        if row.starts_at > now() and row.room_id not in next_by_room:
            next_by_room[row.room_id] = row.starts_at
    pending = []
    incidents = []
    changes = []
    if user.role in ("admin", "manager"):
        seen = set()
        for row in db.scalars(select(Booking).where(Booking.status == "pending")
                              .order_by(Booking.created_at).limit(500)).all():
            key = row.series_id or row.id
            if key not in seen:
                pending.append(booking_data(db, row))
                seen.add(key)
            if len(pending) == 20:
                break
        incidents = list_incidents(status="open", db=db, user=user)[:20]
        action_labels = {"booking_created": "Reserva criada", "booking_updated": "Reserva alterada",
                         "booking_cancelled": "Reserva cancelada", "booking_approved": "Reserva aprovada",
                         "booking_rejected": "Reserva rejeitada", "no_show": "Ausência registrada",
                         "booking_ended": "Reunião encerrada", "block_created": "Sala bloqueada",
                         "incident_created": "Ocorrência registrada", "incident_updated": "Ocorrência alterada"}
        for row in db.scalars(select(Audit).where(Audit.action.in_(action_labels))
                              .order_by(Audit.created_at.desc()).limit(8)).all():
            changes.append({"id": row.id, "label": action_labels[row.action],
                            "actor": db.get(User, row.actor_id).name if row.actor_id else "Sistema",
                            "created_at": row.created_at,
                            "link": f"/reservas/{row.subject_id}" if row.subject == "booking"
                            else "/ocorrencias" if row.subject == "incident" else "/salas"})
    return {"date": local.date().isoformat(), "timezone": settings.timezone,
            "counts": {"total": len(rooms), "available": len(rooms) - len(busy | unavailable),
                       "busy": len(busy), "unavailable": len(unavailable)},
            "rooms": [room_data(room) | {"state": "unavailable" if room.id in unavailable else
                       "busy" if room.id in busy else "upcoming" if room.id in next_by_room else "available",
                       "next_booking": next_by_room.get(room.id)} for room in rooms],
            "bookings": [booking_data(db, row) for row in day],
            "blocks": [{"id": row.id, "room_id": row.room_id,
                        "starts_at": row.starts_at, "ends_at": row.ends_at, "reason": row.reason}
                       for row in blocks],
            "pending": pending, "incidents": incidents, "changes": changes}


@app.get("/reports")
def reports(from_date: datetime, to_date: datetime, room_id: str | None = None,
            db: DbSession = Depends(get_db), user: User = Depends(require("admin", "manager"))):
    start, end = utc(from_date), utc(to_date)
    if start >= end or end - start > timedelta(days=366):
        raise HTTPException(422, "Selecione um período de até 366 dias.")
    settings = db.get(Settings, 1)
    zone = ZoneInfo(settings.timezone)
    rooms = db.scalars(select(Room).where(Room.id == room_id) if room_id else select(Room)).all()
    rows = []
    for room in rooms:
        bookings = db.scalars(select(Booking).where(Booking.room_id == room.id,
            overlap(start, end, Booking.starts_at, Booking.ends_at))).all()
        reserved = sum((min(end, row.ends_at) - max(start, row.starts_at)).total_seconds()
                       for row in bookings if row.status in ("confirmed", "ended", "no_show")) / 3600
        policy = rules_for(settings, room)
        opening = datetime.strptime(policy["opening_time"], "%H:%M").time()
        closing = datetime.strptime(policy["closing_time"], "%H:%M").time()
        local_day = start.astimezone(zone).date()
        last_day = end.astimezone(zone).date()
        available_seconds = 0.0
        while local_day <= last_day:
            opens = datetime.combine(local_day, opening, zone).astimezone(timezone.utc)
            closes = datetime.combine(local_day, closing, zone).astimezone(timezone.utc)
            available_seconds += max(0.0, (min(end, closes) - max(start, opens)).total_seconds())
            local_day += timedelta(days=1)
        total_hours = available_seconds / 3600
        rows.append({"room_id": room.id, "room_name": room.name,
                     "building": room.building.name, "reserved_hours": round(reserved, 2),
                     "available_hours": round(total_hours, 2),
                     "occupancy_percent": round(100 * reserved / total_hours, 1) if total_hours else 0,
                     "cancellations": sum(row.status == "cancelled" for row in bookings),
                     "no_shows": sum(row.status == "no_show" for row in bookings)})
    return rows


@app.get("/reports.csv")
def reports_csv(from_date: datetime, to_date: datetime, room_id: str | None = None,
                db: DbSession = Depends(get_db), user: User = Depends(require("admin", "manager"))):
    import csv
    import io as csv_io
    rows = reports(from_date, to_date, room_id, db, user)
    output = csv_io.StringIO()
    fields = ("room_name", "building", "reserved_hours", "available_hours",
              "occupancy_percent", "cancellations", "no_shows")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response("\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=crass-relatorio.csv"})


@app.get("/audit")
def audit_log(db: DbSession = Depends(get_db), user: User = Depends(require("admin"))):
    rows = db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(300)).all()
    return [{"id": row.id, "actor_id": row.actor_id, "action": row.action,
             "subject": row.subject, "subject_id": row.subject_id,
             "detail": row.detail, "created_at": row.created_at} for row in rows]


@app.get("/integrations")
def integrations(db: DbSession = Depends(get_db), user: User = Depends(require("admin"))):
    channels = {item.channel: item for item in db.scalars(select(ChannelProviderConfig)).all()}
    return {"in_app": {"available": True, "enabled": True},
            **{channel: {"available": False, "enabled": False,
                         "provider": channels[channel].provider if channel in channels else None}
               for channel in ("sms", "email", "whatsapp")},
            "google_calendar": {"available": False, "enabled": False}}


class ChannelProviderIn(BaseModel):
    provider: str | None = Field(default=None, max_length=80)


@app.patch("/integrations/channels/{channel}")
def configure_channel(channel: str, data: ChannelProviderIn,
                      db: DbSession = Depends(get_db),
                      user: User = Depends(require("admin"))):
    if channel not in ("sms", "email", "whatsapp"):
        raise HTTPException(404, "Canal externo não encontrado.")
    item = db.get(ChannelProviderConfig, channel)
    if not item:
        item = ChannelProviderConfig(channel=channel)
        db.add(item)
    item.provider = data.provider.strip() if data.provider else None
    if item.provider == "":
        item.provider = None
    item.enabled = False
    audit(db, user, "channel_provider_prepared", "channel", channel,
          {"provider": item.provider})
    db.commit()
    return {"available": False, "enabled": False, "provider": item.provider}


@app.get("/integrations/calendar/rooms")
def room_calendar_links(db: DbSession = Depends(get_db),
                        user: User = Depends(require("admin"))):
    links = {item.room_id: item.calendar_id for item in db.scalars(select(RoomCalendarLink)).all()}
    return [{"room_id": room.id, "room_name": room.name,
             "building_name": room.building.name, "calendar_id": links.get(room.id)}
            for room in db.scalars(select(Room).order_by(Room.name)).all()]


class CalendarLinkIn(BaseModel):
    calendar_id: str | None = Field(default=None, max_length=255)


@app.patch("/integrations/calendar/rooms/{room_id}")
def configure_room_calendar(room_id: str, data: CalendarLinkIn,
                            db: DbSession = Depends(get_db),
                            user: User = Depends(require("admin"))):
    if not db.get(Room, room_id):
        raise HTTPException(404, "Sala não encontrada.")
    item = db.get(RoomCalendarLink, room_id)
    if not item:
        item = RoomCalendarLink(room_id=room_id)
        db.add(item)
    item.calendar_id = data.calendar_id.strip() if data.calendar_id else None
    if item.calendar_id == "":
        item.calendar_id = None
    audit(db, user, "room_calendar_prepared", "room", room_id,
          {"calendar_id": item.calendar_id})
    db.commit()
    return {"room_id": room_id, "calendar_id": item.calendar_id,
            "available": False, "enabled": False}
