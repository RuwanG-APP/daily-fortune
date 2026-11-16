"""WSGI Application adapter for Daily Fortune.
Deployable on PythonAnywhere, Gunicorn, uWSGI, or any standard WSGI server.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fortune_engine import (
    CITIES,
    NAKSHATRAS_INFO,
    RASHIS,
    SRI_LANKA_DISTRICTS,
    db,
    render_fortune_pdf_bytes,
    safe_pdf_filename,
)
from fortune_server import (
    ICONS_DIR,
    WEB_DIR,
    _ALLOWED_ICONS,
    fortune_from_payload,
)

# Ensure DB schema is ready
db.init_database()


def _get_customer_token(environ: Dict[str, Any], query: Dict[str, list]) -> Optional[str]:
    auth = environ.get("HTTP_AUTHORIZATION", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    tok = environ.get("HTTP_X_CUSTOMER_TOKEN")
    if tok:
        return tok.strip()
    if "token" in query:
        return query["token"][0].strip()
    return None


def _get_admin_token(environ: Dict[str, Any], query: Dict[str, list]) -> Optional[str]:
    auth = environ.get("HTTP_AUTHORIZATION", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    tok = environ.get("HTTP_X_ADMIN_TOKEN")
    if tok:
        return tok.strip()
    if "admin_token" in query:
        return query["admin_token"][0].strip()
    return None


def _is_admin(environ: Dict[str, Any], query: Dict[str, list]) -> bool:
    tok = _get_admin_token(environ, query)
    return bool(tok and db.is_admin_session_valid(tok))


def _read_json_body(environ: Dict[str, Any]) -> Dict[str, Any]:
    try:
        length = int(environ.get("CONTENT_LENGTH", 0))
    except (ValueError, TypeError):
        length = 0
    if length <= 0 or length > 5_000_000:
        return {}
    body_bytes = environ["wsgi.input"].read(length)
    return json.loads(body_bytes.decode("utf-8"))


def _serve_file(file_path: Path, start_response, cache_control: str = "no-cache", extra_headers: Optional[List] = None):
    if not file_path.is_file():
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"Not Found"]

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
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(raw))),
        ("Cache-Control", cache_control),
    ]
    if extra_headers:
        headers.extend(extra_headers)

    start_response("200 OK", headers)
    return [raw]


def _json_resp(status_code: int, data: Any, start_response):
    status_str = f"{status_code} " + {
        200: "OK",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        500: "Internal Server Error",
    }.get(status_code, "OK")
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(raw))),
        ("Cache-Control", "no-store"),
    ]
    start_response(status_str, headers)
    return [raw]


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/").rstrip("/")
    if not path:
        path = "/"
    method = environ.get("REQUEST_METHOD", "GET").upper()
    query = parse_qs(environ.get("QUERY_STRING", ""))

    # --------------------------------------------------------------------------
    # GET Requests
    # --------------------------------------------------------------------------
    if method == "GET":
        if path in ("/healthz", "/health"):
            return _json_resp(200, {"status": "ok", "app": "Daily Fortune"}, start_response)

        if path == "/api/meta":
            settings = db.get_settings()
            return _json_resp(200, {
                "app": "Daily Fortune",
                "districts": SRI_LANKA_DISTRICTS,
                "cities": CITIES,
                "nakshatras": NAKSHATRAS_INFO,
                "rashis": RASHIS,
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
            }, start_response)

        if path == "/api/me":
            tok = _get_customer_token(environ, query)
            cust = db.get_customer_by_token(tok) if tok else None
            settings = db.get_settings()
            return _json_resp(200, {
                "customer": cust,
                "settings": {
                    "annual_price_lkr": int(settings.get("annual_price_lkr", 1490)),
                    "promo_price_lkr": int(settings.get("promo_price_lkr", 1000)),
                    "bank_name": settings.get("bank_name", "Commercial Bank of Ceylon"),
                    "account_number": settings.get("bank_account", "8015238548"),
                    "account_name": settings.get("account_name", "G.C.R. Gamage"),
                    "admin_whatsapp": settings.get("admin_whatsapp", "94760829235"),
                },
            }, start_response)

        # Admin Endpoints (Protected)
        if path == "/api/admin/check":
            if not _is_admin(environ, query):
                return _json_resp(401, {"error": "Unauthorized"}, start_response)
            return _json_resp(200, {"authenticated": True}, start_response)

        if path == "/api/admin/dashboard":
            if not _is_admin(environ, query):
                return _json_resp(401, {"error": "Unauthorized"}, start_response)
            return _json_resp(200, db.get_admin_dashboard_stats(), start_response)

        if path == "/api/admin/customers":
            if not _is_admin(environ, query):
                return _json_resp(401, {"error": "Unauthorized"}, start_response)
            q_str = query.get("q", [""])[0]
            limit = int(query.get("limit", [100])[0])
            cust_list = db.list_customers(query=q_str, limit=limit)
            return _json_resp(200, {"customers": cust_list, "total": len(cust_list)}, start_response)

        if path == "/api/admin/payments":
            if not _is_admin(environ, query):
                return _json_resp(401, {"error": "Unauthorized"}, start_response)
            status_filter = query.get("status", [None])[0]
            payments = db.list_payments(status_filter=status_filter)
            return _json_resp(200, {"payments": payments}, start_response)

        if path.startswith("/api/admin/slips/"):
            if not _is_admin(environ, query):
                return _json_resp(401, {"error": "Unauthorized"}, start_response)
            fname = path[len("/api/admin/slips/"):]
            slip_file = db.SLIPS_DIR / fname
            return _serve_file(slip_file, start_response, cache_control="private, max-age=3600")

        # Static Assets
        if path in ("/", "/index.html"):
            return _serve_file(WEB_DIR / "index.html", start_response)

        if path in ("/admin", "/admin.html"):
            return _serve_file(WEB_DIR / "admin.html", start_response)

        if path in ("/manifest.webmanifest", "/manifest.json"):
            return _serve_file(WEB_DIR / "manifest.webmanifest", start_response)

        if path == "/sw.js":
            return _serve_file(
                WEB_DIR / "sw.js",
                start_response,
                cache_control="no-cache",
                extra_headers=[("Service-Worker-Allowed", "/")],
            )

        if path == "/favicon.ico":
            return _serve_file(ICONS_DIR / "daily_fortune.ico", start_response, cache_control="public, max-age=86400")

        if path.startswith("/icons/"):
            icon_name = path[len("/icons/"):]
            if icon_name in _ALLOWED_ICONS:
                return _serve_file(ICONS_DIR / icon_name, start_response, cache_control="public, max-age=86400")

        rel = path.lstrip("/")
        if rel in ("styles.css", "i18n.js", "app.js", "admin.js", "admin.css"):
            return _serve_file(WEB_DIR / rel, start_response)

        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"Not Found"]

    # --------------------------------------------------------------------------
    # POST Requests
    # --------------------------------------------------------------------------
    if method == "POST":
        payload = _read_json_body(environ)

        # 1. Customer Registration
        if path == "/api/register":
            try:
                name = str(payload.get("name") or "").strip()
                whatsapp = str(payload.get("whatsapp") or "").strip()
                address = str(payload.get("address") or "").strip()
                promo_code = str(payload.get("promo_code") or "").strip()

                if not name:
                    return _json_resp(400, {"error": "නම ඇතුළත් කිරීම අනිවාර්යයි."}, start_response)
                if not whatsapp:
                    return _json_resp(400, {"error": "වට්සැප් අංකය ඇතුළත් කිරීම අනිවාර්යයි."}, start_response)

                customer = db.register_customer(name=name, whatsapp=whatsapp, address=address, promo_code=promo_code)
                return _json_resp(200, {
                    "success": True,
                    "customer": customer,
                    "message": "පැය 24 ක නොමිලේ අත්හදාබැලීම සාර්ථකව ආරම්භ විය!",
                }, start_response)
            except Exception as exc:
                return _json_resp(500, {"error": f"Registration failed: {exc}"}, start_response)

        # 2. Fortune Computation
        if path == "/api/fortune":
            try:
                result = fortune_from_payload(payload)
                return _json_resp(200, result, start_response)
            except (ValueError, KeyError, TypeError) as exc:
                return _json_resp(400, {"error": str(exc)}, start_response)
            except Exception as exc:
                return _json_resp(500, {"error": f"Server error: {exc}"}, start_response)

        # 3. PDF Export (Gated: Locked during 24-hour trial & expired)
        if path == "/api/fortune/pdf":
            try:
                tok = payload.get("token") or _get_customer_token(environ, query)
                cust = db.get_customer_by_token(tok) if tok else None

                if not cust or not cust.get("can_print"):
                    msg = (
                        "🔒 මුද්‍රණ (Print / PDF Export) පහසුකම ගෙවීම් කළ පාරිභෝගිකයින් සඳහා පමණක් විවෘත වේ. "
                        "සම්පූර්ණ වසරක් (දින 365) සඳහා ගිණුම සක්‍රිය කරගන්න (රු. 1,490/=)."
                    )
                    return _json_resp(403, {"error": "print_locked", "message": msg, "customer": cust}, start_response)

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
                headers = [
                    ("Content-Type", "application/pdf"),
                    ("Content-Disposition", f'attachment; filename="{fname}"'),
                    ("Content-Length", str(len(pdf_bytes))),
                    ("Cache-Control", "no-store"),
                ]
                start_response("200 OK", headers)
                return [pdf_bytes]
            except Exception as exc:
                return _json_resp(500, {"error": f"PDF error: {exc}"}, start_response)

        # 4. Payment Slip Submission
        if path == "/api/payment/submit":
            try:
                tok = payload.get("token") or _get_customer_token(environ, query)
                cust = db.get_customer_by_token(tok) if tok else None
                if not cust:
                    return _json_resp(400, {"error": "වලංගු පාරිභෝගික ගිණුමක් හමු නොවීය."}, start_response)

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

                return _json_resp(200, {
                    "success": True,
                    "payment": payment,
                    "whatsapp_url": wa_url,
                    "message": "ඔබගේ රිසිට්පත සාර්ථකව ලැබුණි. පරිපාලක විසින් තහවුරු කළ වහාම සක්‍රිය වේ.",
                }, start_response)
            except Exception as exc:
                return _json_resp(500, {"error": f"Payment submission failed: {exc}"}, start_response)

        # 5. Admin Login
        if path == "/api/admin/login":
            try:
                pin = str(payload.get("pin") or "").strip()
                token = db.verify_admin_pin(pin)
                if not token:
                    return _json_resp(401, {"error": "වැරදි මුරපදයකි (Invalid PIN)."}, start_response)
                return _json_resp(200, {"success": True, "token": token}, start_response)
            except Exception as exc:
                return _json_resp(500, {"error": str(exc)}, start_response)

        # 6. Admin Customer Activation
        if path == "/api/admin/customer/activate":
            if not _is_admin(environ, query):
                return _json_resp(401, {"error": "Unauthorized"}, start_response)
            try:
                cust_id = int(payload.get("customer_id"))
                days = int(payload.get("days", 365))
                notes = str(payload.get("notes") or "Admin manual activation")
                updated = db.activate_customer(cust_id=cust_id, days=days, notes=notes)
                return _json_resp(200, {"success": True, "customer": updated}, start_response)
            except Exception as exc:
                return _json_resp(500, {"error": str(exc)}, start_response)

        # 7. Admin Payment Action
        if path == "/api/admin/payment/action":
            if not _is_admin(environ, query):
                return _json_resp(401, {"error": "Unauthorized"}, start_response)
            try:
                pay_id = int(payload.get("payment_id"))
                action = str(payload.get("action") or "approve").strip()
                days = int(payload.get("days", 365))
                notes = str(payload.get("notes") or "")
                ok = db.process_payment(payment_id=pay_id, action=action, days=days, notes=notes)
                if not ok:
                    return _json_resp(400, {"error": "Payment action failed."}, start_response)
                return _json_resp(200, {"success": True, "action": action, "payment_id": pay_id}, start_response)
            except Exception as exc:
                return _json_resp(500, {"error": str(exc)}, start_response)

        # 8. Admin Settings Update
        if path == "/api/admin/settings":
            if not _is_admin(environ, query):
                return _json_resp(401, {"error": "Unauthorized"}, start_response)
            try:
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
                return _json_resp(200, {"success": True, "settings": saved}, start_response)
            except Exception as exc:
                return _json_resp(500, {"error": str(exc)}, start_response)

        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"Unknown API route"]

    start_response("405 Method Not Allowed", [("Content-Type", "text/plain")])
    return [b"Method Not Allowed"]
