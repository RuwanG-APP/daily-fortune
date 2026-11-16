"""Standalone HTTP API & Mobile-First Web Server for Daily Fortune."""

from __future__ import annotations

import argparse
import base64
import datetime
import json
import mimetypes
import os
import socket
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, quote, urlparse

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fortune_engine import (  # noqa: E402
    CITIES,
    NAKSHATRAS_INFO,
    RASHIS,
    SRI_LANKA_DISTRICTS,
    compute_daily_fortune_schedule,
    db,
    render_fortune_pdf_bytes,
    resolve_birth_profile,
    safe_pdf_filename,
)

WEB_DIR = BASE_DIR / "web"
ICONS_DIR = WEB_DIR / "icons"
_CITIES_BY_ID = {c["id"]: c for c in CITIES}
_ALLOWED_ICONS = {
    "icon.svg",
    "icon-maskable.svg",
    "icon-192.png",
    "icon-512.png",
    "icon-maskable-512.png",
    "apple-touch-icon.png",
    "daily_fortune.ico",
    "qr_code.png",
}


def _detect_lan_ip() -> Optional[str]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return None


def _resolve_city(city_id_val: Any, lat_val: Any = None, lon_val: Any = None, city_name_val: Any = None) -> Tuple[str, str, float, float]:
    if city_id_val is not None and str(city_id_val).strip() != "":
        cid = int(city_id_val)
        c = _CITIES_BY_ID.get(cid)
        if not c:
            raise ValueError(f"Unknown city_id: {cid}")
        return c["name"], c["sinhala"], float(c["lat"]), float(c["lon"])
    if lat_val is not None and lon_val is not None and str(lat_val) != "" and str(lon_val) != "":
        lat = float(lat_val)
        lon = float(lon_val)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ValueError("Latitude / longitude out of range.")
        cname = str(city_name_val or "Custom Location").strip() or "Custom Location"
        return cname, cname, lat, lon
    c0 = _CITIES_BY_ID[1]  # Default Colombo
    return c0["name"], c0["sinhala"], float(c0["lat"]), float(c0["lon"])


def _parse_opt_int(val: Any, lo: int, hi: int, label: str) -> Optional[int]:
    if val is None or str(val).strip() in ("", "auto", "null", "None"):
        return None
    n = int(val)
    if not (lo <= n <= hi):
        raise ValueError(f"{label} must be between {lo} and {hi}.")
    return n


def _parse_hhmm_minutes(val: Any, default_min: int, allow_2400: bool = False) -> int:
    s = str(val or "").strip()
    if not s:
        return default_min
    if s in ("24:00", "24:00:00") and allow_2400:
        return 1440
    parts = s.split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid time format: {s!r}")
    hh = int(parts[0])
    mm = int(parts[1])
    if hh == 24 and mm == 0 and allow_2400:
        return 1440
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise ValueError(f"Invalid time value: {s!r}")
    return hh * 60 + mm


def fortune_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    name = str(payload.get("name") or "Guest").strip() or "Guest"

    birth_date_raw = str(payload.get("birth_date") or payload.get("date") or "").strip()
    if not birth_date_raw:
        raise ValueError("උපන් දිනය අවශ්‍යයි / Birth date is required.")
    try:
        birth_date = datetime.date.fromisoformat(birth_date_raw)
    except ValueError as exc:
        raise ValueError("වලංගු උපන් දිනයක් ඇතුළත් කරන්න (YYYY-MM-DD).") from exc

    birth_time_raw = str(payload.get("birth_time") or payload.get("time") or "").strip()
    if not birth_time_raw:
        birth_time = datetime.time(12, 0)
    else:
        parts = birth_time_raw.split(":")
        try:
            hh = int(parts[0])
            mm = int(parts[1]) if len(parts) > 1 else 0
            ss = int(parts[2]) if len(parts) > 2 else 0
            birth_time = datetime.time(hh, mm, ss)
        except Exception as exc:
            raise ValueError("වලංගු උපන් වේලාවක් ඇතුළත් කරන්න (HH:MM).") from exc

    b_city_en, b_city_si, b_lat, b_lon = _resolve_city(
        payload.get("birth_city_id", payload.get("city_id")),
        payload.get("birth_latitude", payload.get("latitude")),
        payload.get("birth_longitude", payload.get("longitude")),
        payload.get("birth_city", payload.get("city")),
    )

    # Target calculation city defaults to birth city unless specified
    if any(
        payload.get(k) not in (None, "")
        for k in ("target_city_id", "target_latitude", "target_longitude")
    ):
        t_city_en, t_city_si, t_lat, t_lon = _resolve_city(
            payload.get("target_city_id"),
            payload.get("target_latitude"),
            payload.get("target_longitude"),
            payload.get("target_city"),
        )
    else:
        t_city_en, t_city_si, t_lat, t_lon = b_city_en, b_city_si, b_lat, b_lon

    tz_offset = float(payload.get("tz_offset_hours", 5.5))
    ayanamsa = str(payload.get("ayanamsa_system", "arc_ray") or "arc_ray").strip().lower()

    manual_nak_id = _parse_opt_int(payload.get("nakshatra_id"), 1, 27, "Nakshatra")
    manual_pada = _parse_opt_int(payload.get("pada"), 1, 4, "Pada")
    manual_lagna_id = _parse_opt_int(payload.get("lagna_id"), 1, 12, "Lagna")
    manual_navamsa_id = _parse_opt_int(payload.get("navamsa_id"), 1, 12, "Navamsa")

    start_raw = str(payload.get("start_date") or "").strip()
    start_date = datetime.date.fromisoformat(start_raw) if start_raw else datetime.date.today()

    end_raw = str(payload.get("end_date") or "").strip()
    if end_raw:
        end_date = datetime.date.fromisoformat(end_raw)
        if end_date < start_date:
            raise ValueError("අවසන් දිනය ආරම්භක දිනයට පසු දිනයක් විය යුතුය / End date must be on or after start date.")
        days = (end_date - start_date).days + 1
    else:
        days = int(payload.get("days", 1))

    if days < 1 or days > 31:
        raise ValueError("උපරිම දින ගණන 31 කි / Date range must be between 1 and 31 days.")

    from_min = _parse_hhmm_minutes(payload.get("from_time"), 0, allow_2400=False)
    to_min = _parse_hhmm_minutes(payload.get("to_time"), 1440, allow_2400=True)
    if to_min <= from_min:
        raise ValueError("අවසන් වේලාව ආරම්භක වේලාවට පසුව තිබිය යුතුය / End time must be after start time.")

    profile = resolve_birth_profile(
        name=name,
        birth_date=birth_date,
        birth_time=birth_time,
        lat_deg=b_lat,
        lon_deg=b_lon,
        city_name=b_city_en,
        city_si=b_city_si,
        tz_offset_hours=tz_offset,
        ayanamsa_system=ayanamsa,
        manual_nak_id=manual_nak_id,
        manual_pada=manual_pada,
        manual_lagna_id=manual_lagna_id,
        manual_navamsa_id=manual_navamsa_id,
    )

    return compute_daily_fortune_schedule(
        profile=profile,
        start_date=start_date,
        days=days,
        lat_deg=t_lat,
        lon_deg=t_lon,
        city_name=t_city_en,
        city_si=t_city_si,
        tz_offset_hours=tz_offset,
        ayanamsa_system=ayanamsa,
        from_min=from_min,
        to_min=to_min,
    )


class DailyFortuneHandler(BaseHTTPRequestHandler):
    server_version = "DailyFortune/2.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, data: Any) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(
        self,
        file_path: Path,
        cache_control: str = "no-cache",
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        if not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return
        ext = file_path.suffix.lower()
        mime_map = {
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".html": "text/html; charset=utf-8",
            ".webmanifest": "application/manifest+json; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".ico": "image/x-icon",
            ".pdf": "application/pdf",
        }
        content_type = mime_map.get(ext)
        if not content_type:
            guessed, _ = mimetypes.guess_type(str(file_path))
            content_type = guessed or "application/octet-stream"
        raw = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", cache_control)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 5_000_000:
            raise ValueError("Invalid request body size.")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_pdf(self, pdf_bytes: bytes, filename: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(pdf_bytes)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(pdf_bytes)

    # --------------------------------------------------------------------------
    # Auth Extraction Helpers
    # --------------------------------------------------------------------------
    def _get_customer_token(self, parsed_qs: Optional[Dict[str, list]] = None) -> Optional[str]:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        tok = self.headers.get("X-Customer-Token")
        if tok:
            return tok.strip()
        if parsed_qs and "token" in parsed_qs:
            return parsed_qs["token"][0].strip()
        return None

    def _get_admin_token(self, parsed_qs: Optional[Dict[str, list]] = None) -> Optional[str]:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        tok = self.headers.get("X-Admin-Token")
        if tok:
            return tok.strip()
        if parsed_qs and "admin_token" in parsed_qs:
            return parsed_qs["admin_token"][0].strip()
        return None

    def _require_admin(self, parsed_qs: Optional[Dict[str, list]] = None) -> bool:
        tok = self._get_admin_token(parsed_qs)
        if not tok or not db.is_admin_session_valid(tok):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Unauthorized: Admin login required."})
            return False
        return True

    # --------------------------------------------------------------------------
    # GET Router
    # --------------------------------------------------------------------------
    def do_GET(self) -> None:
        u = urlparse(self.path)
        path = u.path
        query = parse_qs(u.query)

        if path in ("/healthz", "/health"):
            self._send_json(HTTPStatus.OK, {"status": "ok", "app": "Daily Fortune"})
            return

        if path == "/api/meta":
            lan_ip = _detect_lan_ip()
            port = self.server.server_address[1]
            settings = db.get_settings()
            self._send_json(HTTPStatus.OK, {
                "app": "Daily Fortune",
                "districts": SRI_LANKA_DISTRICTS,
                "cities": CITIES,
                "nakshatras": NAKSHATRAS_INFO,
                "rashis": RASHIS,
                "lan_url": f"http://{lan_ip}:{port}" if lan_ip else None,
                "pwa": True,
                "pricing": {
                    "annual_price_lkr": int(settings.get("annual_price_lkr", 1490)),
                    "promo_price_lkr": int(settings.get("promo_price_lkr", 1000)),
                },
                "bank": {
                    "bank_name": settings.get("bank_name", "Commercial Bank of Ceylon"),
                    "account_number": settings.get("bank_account", "8015238548"),
                    "account_name": settings.get("account_name", "G.C.R. Gamage"),
                    "admin_whatsapp": settings.get("admin_whatsapp", "94760829235"),
                },
            })
            return

        # Customer Subscription & Status Check
        if path == "/api/me":
            token = self._get_customer_token(query)
            cust = db.get_customer_by_token(token) if token else None
            settings = db.get_settings()
            self._send_json(HTTPStatus.OK, {
                "customer": cust,
                "settings": {
                    "annual_price_lkr": int(settings.get("annual_price_lkr", 1490)),
                    "promo_price_lkr": int(settings.get("promo_price_lkr", 1000)),
                    "bank_name": settings.get("bank_name", "Commercial Bank of Ceylon"),
                    "account_number": settings.get("bank_account", "8015238548"),
                    "account_name": settings.get("account_name", "G.C.R. Gamage"),
                    "admin_whatsapp": settings.get("admin_whatsapp", "94760829235"),
                },
            })
            return

        # Admin Endpoints (Protected)
        if path == "/api/admin/check":
            if not self._require_admin(query):
                return
            self._send_json(HTTPStatus.OK, {"authenticated": True})
            return

        if path == "/api/admin/dashboard":
            if not self._require_admin(query):
                return
            stats = db.get_admin_dashboard_stats()
            self._send_json(HTTPStatus.OK, stats)
            return

        if path == "/api/admin/customers":
            if not self._require_admin(query):
                return
            q_str = query.get("q", [""])[0]
            limit = int(query.get("limit", [100])[0])
            cust_list = db.list_customers(query=q_str, limit=limit)
            self._send_json(HTTPStatus.OK, {"customers": cust_list, "total": len(cust_list)})
            return

        if path == "/api/admin/payments":
            if not self._require_admin(query):
                return
            status_filter = query.get("status", [None])[0]
            payments = db.list_payments(status_filter=status_filter)
            self._send_json(HTTPStatus.OK, {"payments": payments})
            return

        if path.startswith("/api/admin/slips/"):
            if not self._require_admin(query):
                return
            fname = path[len("/api/admin/slips/"):]
            slip_file = db.SLIPS_DIR / fname
            if not slip_file.is_file():
                self.send_error(HTTPStatus.NOT_FOUND, "Slip file not found")
                return
            self._send_file(slip_file, cache_control="private, max-age=3600")
            return

        # HTML and Static Assets
        if path in ("/", "/index.html"):
            self._send_file(WEB_DIR / "index.html")
            return

        if path in ("/admin", "/admin.html"):
            self._send_file(WEB_DIR / "admin.html")
            return

        if path in ("/manifest.webmanifest", "/manifest.json"):
            self._send_file(WEB_DIR / "manifest.webmanifest")
            return

        if path == "/sw.js":
            self._send_file(
                WEB_DIR / "sw.js",
                cache_control="no-cache",
                extra_headers={"Service-Worker-Allowed": "/"},
            )
            return

        if path == "/favicon.ico":
            self._send_file(ICONS_DIR / "daily_fortune.ico", cache_control="public, max-age=86400")
            return

        if path.startswith("/icons/"):
            icon_name = path[len("/icons/"):]
            if icon_name in _ALLOWED_ICONS:
                self._send_file(ICONS_DIR / icon_name, cache_control="public, max-age=86400")
                return

        rel = path.lstrip("/")
        if rel in ("styles.css", "i18n.js", "app.js", "admin.js", "admin.css"):
            self._send_file(WEB_DIR / rel)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    # --------------------------------------------------------------------------
    # POST Router
    # --------------------------------------------------------------------------
    def do_POST(self) -> None:
        u = urlparse(self.path)
        path = u.path

        # 1. Customer Registration
        if path == "/api/register":
            try:
                payload = self._read_json()
                name = str(payload.get("name") or "").strip()
                whatsapp = str(payload.get("whatsapp") or "").strip()
                address = str(payload.get("address") or "").strip()
                promo_code = str(payload.get("promo_code") or "").strip()

                if not name:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "නම ඇතුළත් කිරීම අනිවාර්යයි (Name is required)."})
                    return
                if not whatsapp:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "වට්සැප් අංකය ඇතුළත් කිරීම අනිවාර්යයි (WhatsApp number is required)."})
                    return

                customer = db.register_customer(name=name, whatsapp=whatsapp, address=address, promo_code=promo_code)
                self._send_json(HTTPStatus.OK, {
                    "success": True,
                    "customer": customer,
                    "message": "පැය 24 ක නොමිලේ අත්හදාබැලීම සාර්ථකව ආරම්භ විය!",
                })
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Registration failed: {exc}"})
            return

        # 2. Fortune Generation
        if path == "/api/fortune":
            try:
                payload = self._read_json()
                result = fortune_from_payload(payload)
                self._send_json(HTTPStatus.OK, result)
            except (ValueError, KeyError, TypeError) as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Server error: {exc}"})
            return

        # 3. PDF Export (Gated: Locked during 24-hour trial & expired state)
        if path == "/api/fortune/pdf":
            try:
                payload = self._read_json()
                # Check authorization token
                tok = payload.get("token") or self._get_customer_token()
                cust = db.get_customer_by_token(tok) if tok else None

                # Require active subscription for Print / PDF export
                if not cust or not cust.get("can_print"):
                    msg = (
                        "🔒 මුද්‍රණ (Print / PDF Export) පහසුකම ගෙවීම් කළ පාරිභෝගිකයින් සඳහා පමණක් විවෘත වේ. "
                        "සම්පූර්ණ වසරක් (දින 365) සඳහා ගිණුම සක්‍රිය කරගන්න (රු. 1,490/=)."
                    )
                    self._send_json(HTTPStatus.FORBIDDEN, {
                        "error": "print_locked",
                        "message": msg,
                        "customer": cust,
                    })
                    return

                schedule = payload.get("schedule")
                if not isinstance(schedule, dict) or "profile" not in schedule or "rows" not in schedule:
                    schedule = fortune_from_payload(payload)
                lang = str(payload.get("lang") or "si")
                if lang not in ("si", "en"):
                    lang = "si"
                time_fmt = str(payload.get("time_fmt") or "12h")
                if time_fmt not in ("12h", "24h"):
                    time_fmt = "12h"
                filter_key = str(payload.get("filter") or "all")
                pdf_bytes = render_fortune_pdf_bytes(
                    schedule=schedule,
                    lang=lang,
                    time_fmt=time_fmt,
                    filter_key=filter_key,
                )
                fname = safe_pdf_filename(
                    schedule["profile"].get("name", "Report"),
                    schedule["range"].get("start_date", "today"),
                )
                self._send_pdf(pdf_bytes, fname)
            except (ValueError, KeyError, TypeError) as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"PDF generation failed: {exc}"})
            return

        # 4. Payment Slip Submission (Customer Uploads Slip & gets WhatsApp Link)
        if path == "/api/payment/submit":
            try:
                payload = self._read_json()
                tok = payload.get("token") or self._get_customer_token()
                cust = db.get_customer_by_token(tok) if tok else None
                if not cust:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "වලංගු පාරිභෝගික ගිණුමක් හමු නොවීය."})
                    return

                settings = db.get_settings()
                annual_price = int(settings.get("annual_price_lkr", 1490))
                amount = int(payload.get("amount") or annual_price)

                slip_b64 = payload.get("slip_base64")
                ext = "jpg"
                slip_bytes = None
                if slip_b64:
                    if "," in slip_b64:
                        prefix, slip_b64 = slip_b64.split(",", 1)
                        if "png" in prefix:
                            ext = "png"
                        elif "pdf" in prefix:
                            ext = "pdf"
                    slip_bytes = base64.b64decode(slip_b64)

                payment = db.submit_payment_slip(cust_id=cust["id"], amount=amount, slip_bytes=slip_bytes, ext=ext)

                # Generate direct WhatsApp message link
                admin_wa = settings.get("admin_whatsapp", "94760829235").strip("+")
                wa_msg = (
                    f"හෙලෝ, මම Daily Fortune ඇප් එකේ ගෙවීම් කළා.\n\n"
                    f"නම: {cust['name']}\n"
                    f"වට්සැප් අංකය: {cust['whatsapp']}\n"
                    f"මුදල: රු. {amount}/=\n"
                    f"ගෙවීම් අංකය: #{payment['payment_id']}\n\n"
                    f"බැංකු රිසිට්පත මෙහි අමුණා ඇත. කරුණාකර මගේ ගිණුම සක්‍රිය කරන්න."
                )
                wa_url = f"https://wa.me/{admin_wa}?text={quote(wa_msg)}"

                self._send_json(HTTPStatus.OK, {
                    "success": True,
                    "payment": payment,
                    "whatsapp_url": wa_url,
                    "message": "ඔබගේ රිසිට්පත සාර්ථකව ලැබුණි. පරිපාලක විසින් තහවුරු කළ වහාම සක්‍රිය වේ.",
                })
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Payment submission failed: {exc}"})
            return

        # 5. Admin Login (PIN Authentication)
        if path == "/api/admin/login":
            try:
                payload = self._read_json()
                pin = str(payload.get("pin") or "").strip()
                token = db.verify_admin_pin(pin)
                if not token:
                    self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "වැරදි මුරපදයකි (Invalid PIN)."})
                    return
                self._send_json(HTTPStatus.OK, {"success": True, "token": token})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        # 6. Admin 1-Click Activate Customer
        if path == "/api/admin/customer/activate":
            if not self._require_admin():
                return
            try:
                payload = self._read_json()
                cust_id = int(payload.get("customer_id"))
                days = int(payload.get("days", 365))
                notes = str(payload.get("notes") or "Admin manual activation")
                updated = db.activate_customer(cust_id=cust_id, days=days, notes=notes)
                self._send_json(HTTPStatus.OK, {"success": True, "customer": updated})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        # 7. Admin Payment Action (Approve / Reject Slip)
        if path == "/api/admin/payment/action":
            if not self._require_admin():
                return
            try:
                payload = self._read_json()
                pay_id = int(payload.get("payment_id"))
                action = str(payload.get("action") or "approve").strip()
                days = int(payload.get("days", 365))
                notes = str(payload.get("notes") or "")
                ok = db.process_payment(payment_id=pay_id, action=action, days=days, notes=notes)
                if not ok:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Payment action failed."})
                    return
                self._send_json(HTTPStatus.OK, {"success": True, "action": action, "payment_id": pay_id})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        # 8. Admin Settings Update (Pricing, Bank, WhatsApp, PIN)
        if path == "/api/admin/settings":
            if not self._require_admin():
                return
            try:
                payload = self._read_json()
                allowed_keys = {
                    "annual_price_lkr",
                    "promo_price_lkr",
                    "admin_pin",
                    "bank_name",
                    "bank_account",
                    "account_name",
                    "admin_whatsapp",
                }
                updates = {k: str(v) for k, v in payload.items() if k in allowed_keys}
                saved = db.update_settings(updates)
                self._send_json(HTTPStatus.OK, {"success": True, "settings": saved})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown API route")


def create_server(host: str = "0.0.0.0", port: int = 8795) -> ThreadingHTTPServer:
    # Ensure database schema is ready
    db.init_database()
    return ThreadingHTTPServer((host, port), DailyFortuneHandler)


def main() -> None:
    default_host = os.environ.get("HOST", "0.0.0.0")
    try:
        default_port = int(os.environ.get("PORT", "8795"))
    except ValueError:
        default_port = 8795

    parser = argparse.ArgumentParser(description="Daily Fortune Standalone Server")
    parser.add_argument("--host", default=default_host)
    parser.add_argument("--port", type=int, default=default_port)
    args = parser.parse_args()

    srv = create_server(args.host, args.port)
    lan_ip = _detect_lan_ip()
    print(f"Daily Fortune server running locally at: http://127.0.0.1:{args.port}", flush=True)
    print(f"Admin Dashboard available at:           http://127.0.0.1:{args.port}/admin", flush=True)
    if lan_ip:
        print(f"Open on your Phone (same Wi-Fi) at:     http://{lan_ip}:{args.port}", flush=True)
        print(f"Phone Admin Dashboard at:               http://{lan_ip}:{args.port}/admin", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Daily Fortune server.")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
