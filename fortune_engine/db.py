"""
Daily Fortune Commercial Database Layer (SQLite).
Handles customer registration, 24-hour trial enforcement, annual subscriptions,
Commercial Bank payment slips, dynamic pricing, and admin management.
"""

from __future__ import annotations

import datetime
import os
import secrets
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "fortune.db"
SLIPS_DIR = DATA_DIR / "slips"

DEFAULT_SETTINGS = {
    "annual_price_lkr": "1490",
    "promo_price_lkr": "1000",
    "admin_pin": "0779",
    "bank_name": "Commercial Bank of Ceylon",
    "bank_account": "8015238548",
    "account_name": "G.C.R. Gamage",
    "admin_whatsapp": "94760829235",
}


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SLIPS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Create tables and seed initial settings."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Settings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        for k, v in DEFAULT_SETTINGS.items():
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

        # Customers Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                whatsapp TEXT NOT NULL,
                address TEXT DEFAULT '',
                promo_code TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                trial_ends_at TEXT NOT NULL,
                subscription_status TEXT NOT NULL DEFAULT 'trial',
                subscription_ends_at TEXT,
                activated_at TEXT,
                notes TEXT DEFAULT ''
            )
        """)

        # Payments / Slips Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                slip_filename TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                approved_at TEXT,
                notes TEXT DEFAULT '',
                FOREIGN KEY (customer_id) REFERENCES customers (id)
            )
        """)

        # Admin Sessions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_sessions (
                token TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)

        conn.commit()


# ==============================================================================
# Settings Management
# ==============================================================================

def get_settings() -> Dict[str, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        settings = dict(DEFAULT_SETTINGS)
        for r in rows:
            settings[r["key"]] = r["value"]
        return settings


def update_settings(updates: Dict[str, str]) -> Dict[str, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        for k, v in updates.items():
            if k in DEFAULT_SETTINGS or k.startswith("custom_"):
                cursor.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (k, str(v)),
                )
        conn.commit()
    return get_settings()


# ==============================================================================
# Customer Registration & Subscription Verification
# ==============================================================================

def register_customer(name: str, whatsapp: str, address: str = "", promo_code: str = "") -> Dict[str, Any]:
    """Register a new customer, grant 24-hour trial, and return auth token."""
    name_clean = name.strip() or "Guest"
    # Clean phone digits
    phone_clean = "".join(ch for ch in whatsapp if ch.isdigit())
    if phone_clean.startswith("0") and len(phone_clean) == 10:
        phone_clean = "94" + phone_clean[1:]
    elif not phone_clean.startswith("94") and len(phone_clean) == 9:
        phone_clean = "94" + phone_clean

    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()
    trial_ends = now + datetime.timedelta(hours=24)
    trial_ends_iso = trial_ends.isoformat()

    token = "df_" + secrets.token_hex(20)

    # If registered with town promo / agent bypass or special promo
    settings = get_settings()
    is_promo_direct = bool(promo_code and promo_code.strip().upper() == "PROMO1000")

    sub_status = "active" if is_promo_direct else "trial"
    sub_ends_iso = (now + datetime.timedelta(days=365)).isoformat() if is_promo_direct else None
    act_iso = now_iso if is_promo_direct else None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customers (
                token, name, whatsapp, address, promo_code,
                created_at, trial_ends_at, subscription_status,
                subscription_ends_at, activated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            token, name_clean, phone_clean, address.strip(), promo_code.strip(),
            now_iso, trial_ends_iso, sub_status, sub_ends_iso, act_iso
        ))
        cust_id = cursor.lastrowid
        conn.commit()

    return get_customer_by_token(token)


def get_customer_by_token(token: str) -> Optional[Dict[str, Any]]:
    if not token or not token.startswith("df_"):
        return None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE token = ?", (token,))
        row = cursor.fetchone()
        if not row:
            return None
        return _format_customer(dict(row))


def get_customer_by_id(cust_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE id = ?", (cust_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return _format_customer(dict(row))


def _format_customer(row: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc)

    # Check status & expiry
    status = row["subscription_status"]
    trial_ends = datetime.datetime.fromisoformat(row["trial_ends_at"])
    sub_ends = datetime.datetime.fromisoformat(row["subscription_ends_at"]) if row.get("subscription_ends_at") else None

    # Compute actual dynamic state
    if status == "active":
        if sub_ends and now > sub_ends:
            status = "expired"
    elif status == "trial":
        if now > trial_ends:
            status = "expired"

    # Print / PDF export is strictly locked during trial or expired
    can_print = status == "active"

    # Remaining hours calculation
    hours_left = 0.0
    if status == "trial":
        delta = trial_ends - now
        hours_left = max(0.0, round(delta.total_seconds() / 3600.0, 1))
    elif status == "active" and sub_ends:
        delta = sub_ends - now
        hours_left = max(0.0, round(delta.total_seconds() / 3600.0, 1))

    return {
        "id": row["id"],
        "token": row["token"],
        "name": row["name"],
        "whatsapp": row["whatsapp"],
        "address": row.get("address", ""),
        "created_at": row["created_at"],
        "status": status,
        "is_trial": status == "trial",
        "is_active": status == "active",
        "is_expired": status == "expired",
        "trial_ends_at": row["trial_ends_at"],
        "subscription_ends_at": row.get("subscription_ends_at"),
        "hours_left": hours_left,
        "can_print": can_print,
    }


def activate_customer(cust_id: int, days: int = 365, notes: str = "") -> Optional[Dict[str, Any]]:
    now = datetime.datetime.now(datetime.timezone.utc)
    sub_ends = now + datetime.timedelta(days=max(1, int(days)))

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE customers
            SET subscription_status = 'active',
                subscription_ends_at = ?,
                activated_at = ?,
                notes = COALESCE(notes, '') || ' ' || ?
            WHERE id = ?
        """, (sub_ends.isoformat(), now.isoformat(), notes, cust_id))
        conn.commit()

    return get_customer_by_id(cust_id)


# ==============================================================================
# Payment Slips & Submissions
# ==============================================================================

def submit_payment_slip(cust_id: int, amount: int, slip_bytes: Optional[bytes] = None, ext: str = "jpg") -> Dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc)
    filename = None
    if slip_bytes:
        filename = f"slip_c{cust_id}_{int(now.timestamp())}.{ext.lstrip('.')}"
        slip_path = SLIPS_DIR / filename
        slip_path.write_bytes(slip_bytes)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO payments (customer_id, amount, slip_filename, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
        """, (cust_id, int(amount), filename, now.isoformat()))
        pay_id = cursor.lastrowid
        conn.commit()

    return {
        "payment_id": pay_id,
        "customer_id": cust_id,
        "amount": amount,
        "slip_filename": filename,
        "status": "pending",
        "created_at": now.isoformat(),
    }


def list_payments(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if status_filter:
            cursor.execute("""
                SELECT p.*, c.name, c.whatsapp
                FROM payments p
                JOIN customers c ON p.customer_id = c.id
                WHERE p.status = ?
                ORDER BY p.id DESC
            """, (status_filter,))
        else:
            cursor.execute("""
                SELECT p.*, c.name, c.whatsapp
                FROM payments p
                JOIN customers c ON p.customer_id = c.id
                ORDER BY p.id DESC
            """)
        return [dict(r) for r in cursor.fetchall()]


def process_payment(payment_id: int, action: str, days: int = 365, notes: str = "") -> bool:
    action = action.lower().strip()
    if action not in ("approve", "reject"):
        return False

    now = datetime.datetime.now(datetime.timezone.utc)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT customer_id FROM payments WHERE id = ?", (payment_id,))
        row = cursor.fetchone()
        if not row:
            return False
        cust_id = row["customer_id"]

        status = "approved" if action == "approve" else "rejected"
        cursor.execute("""
            UPDATE payments
            SET status = ?, approved_at = ?, notes = ?
            WHERE id = ?
        """, (status, now.isoformat(), notes, payment_id))
        conn.commit()

    if action == "approve":
        activate_customer(cust_id, days=days, notes=f"Payment #{payment_id} approved")

    return True


# ==============================================================================
# Admin Authentication & Dashboard
# ==============================================================================

def verify_admin_pin(pin: str) -> Optional[str]:
    settings = get_settings()
    stored_pin = settings.get("admin_pin", "0779").strip()
    if str(pin).strip() != stored_pin:
        return None

    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(days=7)
    session_token = "adm_" + secrets.token_hex(24)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO admin_sessions (token, created_at, expires_at) VALUES (?, ?, ?)",
            (session_token, now.isoformat(), expires.isoformat()),
        )
        conn.commit()

    return session_token


def is_admin_session_valid(token: str) -> bool:
    if not token or not token.startswith("adm_"):
        return False
    now = datetime.datetime.now(datetime.timezone.utc)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT expires_at FROM admin_sessions WHERE token = ?", (token,))
        row = cursor.fetchone()
        if not row:
            return False
        expires = datetime.datetime.fromisoformat(row["expires_at"])
        return now < expires


def get_admin_dashboard_stats() -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM customers")
        total_customers = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS active FROM customers WHERE subscription_status = 'active'")
        active_customers = cursor.fetchone()["active"]

        cursor.execute("SELECT COUNT(*) AS trial FROM customers WHERE subscription_status = 'trial'")
        trial_customers = cursor.fetchone()["trial"]

        cursor.execute("SELECT COUNT(*) AS pending_slips FROM payments WHERE status = 'pending'")
        pending_slips = cursor.fetchone()["pending_slips"]

        cursor.execute("SELECT SUM(amount) AS total_rev FROM payments WHERE status = 'approved'")
        rev_row = cursor.fetchone()
        total_revenue = rev_row["total_rev"] or 0

        settings = get_settings()

    return {
        "total_customers": total_customers,
        "active_customers": active_customers,
        "trial_customers": trial_customers,
        "pending_slips": pending_slips,
        "total_revenue": total_revenue,
        "annual_price_lkr": int(settings.get("annual_price_lkr", 1490)),
        "promo_price_lkr": int(settings.get("promo_price_lkr", 1000)),
        "bank_account": settings.get("bank_account", "8015238548"),
        "bank_name": settings.get("bank_name", "Commercial Bank of Ceylon"),
        "account_name": settings.get("account_name", "G.C.R. Gamage"),
        "admin_whatsapp": settings.get("admin_whatsapp", "94760829235"),
    }


def list_customers(query: str = "", limit: int = 100) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if query:
            q_like = f"%{query.strip()}%"
            cursor.execute("""
                SELECT * FROM customers
                WHERE name LIKE ? OR whatsapp LIKE ? OR address LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (q_like, q_like, q_like, limit))
        else:
            cursor.execute("SELECT * FROM customers ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [_format_customer(dict(r)) for r in rows]
