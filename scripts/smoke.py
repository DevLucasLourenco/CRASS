"""Disposable end-to-end checks for a fresh CRASS installation.

Set CRASS_URL, CRASS_ADMIN_EMAIL and CRASS_ADMIN_PASSWORD before running.
Creates uniquely named test rooms, users and bookings in that installation.
"""

import base64
import hashlib
import hmac
import json
import os
import struct
import time as clock_time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, time, timezone
from http.cookiejar import CookieJar
from uuid import uuid4
from zoneinfo import ZoneInfo


BASE = os.getenv("CRASS_API_URL") or os.environ["CRASS_URL"].rstrip("/") + "/api"
EMAIL = os.environ["CRASS_ADMIN_EMAIL"]
PASSWORD = os.environ["CRASS_ADMIN_PASSWORD"]
ZONE = ZoneInfo("America/Sao_Paulo")


class Client:
    def __init__(self):
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))
        self.csrf = ""

    def call(self, method, path, body=None, expected=200):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if method != "GET":
            headers["X-CSRF-Token"] = self.csrf
        request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request) as response:
                status, content = response.status, response.read()
        except urllib.error.HTTPError as exc:
            status, content = exc.code, exc.read()
        assert status == expected, (method, path, status, content[:500])
        return json.loads(content) if content else None

    def login(self, email=EMAIL, password=None):
        result = self.call("POST", "/auth/login", {"email": email, "password": password or PASSWORD})
        self.csrf = result["csrf"]
        if BASE.startswith("http://localhost"):
            for cookie in self.cookies:
                cookie.secure = False  # Test client only; deployment cookie remains Secure.
        return result["user"]


def iso(day, hour):
    return datetime.combine(day, time(hour), ZONE).isoformat()


def totp(secret):
    raw = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8))
    digest = hmac.new(raw, struct.pack(">Q", int(clock_time.time()) // 30), hashlib.sha1).digest()
    offset = digest[-1] & 15
    return f"{(struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % 1000000:06d}"


def main():
    global PASSWORD
    admin = Client()
    account = admin.login()
    assert account["role"] == "admin"
    if account["must_change_password"]:
        replacement = "qa-updated-" + uuid4().hex
        admin.call("POST", "/auth/password", {"current_password": PASSWORD,
            "new_password": replacement})
        PASSWORD = replacement
    suffix = uuid4().hex[:8]
    building = admin.call("POST", "/buildings", {"name": f"Teste {suffix}"})

    def room(name, approval=False):
        return admin.call("POST", "/rooms", {
            "building_id": building["id"], "name": name, "capacity": 8,
            "features": ["Projetor"], "approval_required": approval,
        })

    normal, approval = room("Livre"), room("Aprovação", True)
    admin.call("PATCH", f"/rooms/{normal['id']}", {"rules": {
        "opening_time": "09:00", "closing_time": "17:00", "max_duration_minutes": 120}})
    admin.call("PATCH", f"/rooms/{normal['id']}",
               {"rules": {"opening_time": "18:00", "closing_time": "08:00"}}, expected=422)
    day = (datetime.now(ZONE) + timedelta(days=3)).date()

    admin.call("PATCH", f"/rooms/{normal['id']}", {"floor": "2º andar"})
    def available_rooms(hour, finish, floor="2º andar"):
        query = urllib.parse.urlencode({"starts_at": iso(day, hour),
            "ends_at": iso(day, finish), "floor": floor})
        return admin.call("GET", f"/rooms?{query}")

    assert any(row["id"] == normal["id"] and row["available"]
               for row in available_rooms(10, 11))
    assert not any(row["id"] == normal["id"] and row["available"]
                   for row in available_rooms(8, 9))
    assert not any(row["id"] == normal["id"] and row["available"]
                   for row in available_rooms(10, 13))
    assert all(row["id"] != normal["id"] for row in available_rooms(10, 11, "1º andar"))

    def booking(room_id, hour=10, title="Reunião de teste"):
        return {"room_id": room_id, "title": title, "attendees": 4,
                "starts_at": iso(day, hour), "ends_at": iso(day, hour + 1)}

    first = admin.call("POST", "/bookings", booking(normal["id"]))
    assert first["status"] == "confirmed"
    admin.call("POST", "/bookings", booking(normal["id"]), expected=409)
    adjacent = admin.call("POST", "/bookings", booking(normal["id"], 11))
    assert adjacent["status"] == "confirmed"

    # Both requests start together; assert exactly one slot survives the race.
    from threading import Barrier
    barrier = Barrier(2)

    def race(_):
        candidate = Client()
        candidate.login()
        barrier.wait()
        try:
            candidate.call("POST", "/bookings", booking(normal["id"], 14))
            return 200
        except AssertionError as exc:
            if exc.args[0][2] == 409:
                return 409
            raise

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(race, range(2))) == [200, 409]

    block = admin.call("POST", "/blocks", {"room_id": normal["id"],
        "starts_at": iso(day, 10), "ends_at": iso(day, 11), "reason": "Manutenção"})
    assert first["id"] in block["affected_bookings"]
    assert admin.call("GET", f"/bookings/{first['id']}")["block_conflict"]
    admin.call("POST", "/bookings", booking(normal["id"], 10), expected=409)

    pending = admin.call("POST", "/bookings", booking(approval["id"]))
    assert pending["status"] == "pending"
    admin.call("POST", "/bookings", booking(approval["id"]), expected=409)
    assert admin.call("POST", f"/bookings/{pending['id']}/approve")["approved"] == 1
    moved_pending = admin.call("POST", "/bookings", booking(approval["id"], 16))
    moved_confirmed = admin.call("PATCH", f"/bookings/{moved_pending['id']}",
                                 {"room_id": normal["id"]})
    assert moved_confirmed["status"] == "confirmed" and moved_confirmed["expires_at"] is None
    assert moved_confirmed["room_id"] == normal["id"]

    conflict_day = day + timedelta(days=7)
    admin.call("POST", "/bookings", {"room_id": approval["id"], "title": "Conflito semanal",
        "attendees": 3, "starts_at": iso(conflict_day, 15), "ends_at": iso(conflict_day, 16)})
    series = admin.call("POST", "/series", {"room_id": approval["id"],
        "title": "Série semanal", "attendees": 3, "starts_at": iso(day, 15),
        "ends_at": iso(day, 16), "frequency": "weekly", "interval": 1})
    assert series["created"] > 1 and series["skipped"], series
    occurrences = admin.call("GET", f"/bookings?room_id={approval['id']}")
    series_rows = [row for row in occurrences if row["series_id"] == series["id"]]
    assert series_rows and all(row["status"] == "pending" for row in series_rows)
    admin.call("POST", f"/bookings/{series_rows[0]['id']}/approve")
    assert admin.call("GET", f"/bookings/{series_rows[0]['id']}")["status"] == "confirmed"
    reference = series_rows[3]
    original_first = series_rows[0]["starts_at"]
    admin.call("POST", f"/series/{series['id']}/change", {
        "scope": "all", "occurrence_id": reference["id"],
        "changes": {"title": "Série completa revisada",
                    "starts_at": reference["starts_at"], "ends_at": reference["ends_at"]}})
    series_rows = [row for row in admin.call("GET", f"/bookings?room_id={approval['id']}")
                   if row["series_id"] == series["id"] and row["status"] == "confirmed"]
    assert any(row["starts_at"] == original_first for row in series_rows)
    cutoff = series_rows[2]
    changed = admin.call("POST", f"/series/{series['id']}/change", {
        "scope": "future", "occurrence_id": cutoff["id"],
        "changes": {"title": "Série revisada"}})
    assert changed["id"] != series["id"] and changed["cancelled"] > 0
    revised = admin.call("POST", f"/series/{changed['id']}/change", {
        "scope": "all", "changes": {"description": "Descrição revisada"}})
    assert revised["id"] == changed["id"]

    provider = admin.call("PATCH", "/integrations/channels/sms", {"provider": "Provedor futuro"})
    assert provider == {"available": False, "enabled": False, "provider": "Provedor futuro"}
    assert not admin.call("GET", "/integrations")["sms"]["enabled"]
    link = admin.call("PATCH", f"/integrations/calendar/rooms/{normal['id']}",
                      {"calendar_id": "sala@example.com"})
    assert link["calendar_id"] == "sala@example.com" and not link["enabled"]
    assert any(row["calendar_id"] == "sala@example.com"
               for row in admin.call("GET", "/integrations/calendar/rooms"))

    manager_data = admin.call("POST", "/users", {"name": "Responsável de Teste",
        "email": f"manager-{suffix}@crass.local", "role": "manager"})
    manager = Client()
    manager.login(manager_data["user"]["email"], manager_data["temporary_password"])
    manager.call("POST", "/auth/password", {"current_password": manager_data["temporary_password"],
        "new_password": "local-manager-updated-" + suffix})
    manager.call("PATCH", f"/rooms/{normal['id']}",
                 {"rules": {"opening_time": "10:00"}}, expected=403)
    manager.call("POST", "/buildings", {"name": f"Outro {suffix}"}, expected=403)

    user = admin.call("POST", "/users", {"name": "Usuário de Teste",
        "email": f"test-{suffix}@crass.local", "role": "user"})
    ordinary = Client()
    assert ordinary.login(user["user"]["email"], user["temporary_password"])["must_change_password"]
    ordinary.call("GET", "/rooms", expected=403)
    ordinary.call("POST", "/auth/password", {"current_password": user["temporary_password"],
        "new_password": "local-test-updated-" + suffix})
    assert ordinary.call("GET", "/rooms")
    ordinary.call("GET", "/users", expected=403)
    ordinary.call("GET", "/audit", expected=403)
    ordinary.call("POST", f"/bookings/{first['id']}/cancel", expected=403)
    setup = ordinary.call("POST", "/auth/totp/setup")
    codes = ordinary.call("POST", "/auth/totp/confirm", {"code": totp(setup["secret"])})
    assert len(codes["recovery_codes"]) == 10
    Client().call("POST", "/auth/login", {"email": user["user"]["email"],
        "password": "local-test-updated-" + suffix, "code": totp(setup["secret"])})
    Client().call("POST", "/auth/login", {"email": user["user"]["email"],
        "password": "local-test-updated-" + suffix, "code": codes["recovery_codes"][0]})

    report_start = urllib.parse.quote(iso(day, 0), safe="")
    report_end = urllib.parse.quote(iso(day + timedelta(days=8), 0), safe="")
    report = admin.call("GET", f"/reports?from_date={report_start}&to_date={report_end}")
    assert any(row["room_id"] == normal["id"] and row["reserved_hours"] >= 2 for row in report)
    assert next(row for row in report if row["room_id"] == normal["id"])["available_hours"] == 64
    with admin.opener.open(BASE + f"/reports.csv?from_date={report_start}&to_date={report_end}") as response:
        assert response.headers.get_content_type() == "text/csv"
        assert b"reserved_hours" in response.read()
    assert admin.call("GET", "/notifications")
    assert admin.call("GET", "/audit")
    assert admin.call("GET", "/dashboard")["changes"]
    print("CRASS smoke: autenticação, TOTP, permissões, concorrência, aprovação, "
          "recorrência e edição, bloqueios, notificações, relatórios e CSV OK")


if __name__ == "__main__":
    main()
