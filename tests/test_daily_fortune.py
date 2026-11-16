"""Verification test suite for standalone Daily Fortune application."""

from __future__ import annotations

import datetime
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from fortune_engine import (  # noqa: E402
    CITIES,
    NAKSHATRAS_INFO,
    RASHIS,
    SRI_LANKA_DISTRICTS,
    compute_daily_fortune_schedule,
    resolve_birth_profile,
)
from fortune_server import create_server  # noqa: E402


class TestDailyFortuneEngine(unittest.TestCase):
    """Verify astronomical profile resolution, manual overrides, 6-tier grades & clipping."""

    def test_auto_natal_matches_known_chart(self) -> None:
        prof = resolve_birth_profile(
            name="RUWAN",
            birth_date=datetime.date(1973, 8, 4),
            birth_time=datetime.time(2, 28),
            lat_deg=6.883333,
            lon_deg=79.85,
            city_name="Colombo",
            city_si="කොළඹ",
        )
        self.assertEqual(prof["janma_lagna_en"], "Wrushaba")
        self.assertEqual(prof["janma_lagna_si"], "වෘෂභ")
        self.assertEqual(prof["navamsa_en"], "Kanya")
        self.assertEqual(prof["janma_nak_en"], "Sita")
        self.assertEqual(prof["janma_nak_si"], "සිත")
        self.assertEqual(prof["janma_pada"], 1)
        self.assertEqual(prof["janma_paksha"], "Shukla")
        self.assertEqual(prof["nak_source"], "auto")

    def test_manual_chart_overrides_and_boundary_pada(self) -> None:
        prof1 = resolve_birth_profile(
            name="Kasun",
            birth_date=datetime.date(1992, 5, 10),
            birth_time=datetime.time(12, 0),
            lat_deg=7.116667,
            lon_deg=80.633333,
            city_name="Kandy",
            city_si="මහනුවර",
            manual_nak_id=3,   # Keti straddles Mesha (pada 1) & Wrushaba (pada 2..4)
            manual_pada=1,
            manual_lagna_id=1,
            manual_navamsa_id=5,
        )
        self.assertEqual(prof1["janma_nak_id"], 3)
        self.assertEqual(prof1["janma_rashi_id"], 1)  # Mesha
        self.assertEqual(prof1["janma_lagna_id"], 1)
        self.assertEqual(prof1["navamsa_id"], 5)
        self.assertEqual(prof1["nak_source"], "manual")

        prof2 = resolve_birth_profile(
            name="Kasun",
            birth_date=datetime.date(1992, 5, 10),
            birth_time=datetime.time(12, 0),
            lat_deg=7.116667,
            lon_deg=80.633333,
            city_name="Kandy",
            city_si="මහනුවර",
            manual_nak_id=3,
            manual_pada=2,
            manual_lagna_id=9,
            manual_navamsa_id=None,
        )
        self.assertEqual(prof2["janma_rashi_id"], 2)  # Wrushaba
        self.assertIsNone(prof2["navamsa_id"])

    def test_30_day_schedule_and_time_clipping(self) -> None:
        prof = resolve_birth_profile(
            name="RUWAN",
            birth_date=datetime.date(1973, 8, 4),
            birth_time=datetime.time(2, 28),
            lat_deg=6.883333,
            lon_deg=79.85,
            city_name="Colombo",
            city_si="කොළඹ",
        )
        full = compute_daily_fortune_schedule(
            prof, datetime.date(2026, 11, 12), days=30, from_min=0, to_min=1440,
        )
        self.assertEqual(len(full["days"]), 30)
        seen_grades = set()
        for day in full["days"]:
            rows = day["rows"]
            self.assertEqual(rows[0]["m0"], 0)
            self.assertEqual(rows[0]["from_12_si"], "මැදියම් රෑ 12:00")
            self.assertEqual(rows[0]["from_12_en"], "Midnight 12:00")
            self.assertEqual(rows[-1]["m1"], 1440)
            self.assertEqual(rows[-1]["to_12_si"], "මැදියම් රෑ 12:00")
            for idx, r in enumerate(rows):
                seen_grades.add(r["grade"])
                self.assertNotIn("පෙ.ව. 12:", r["from_12_si"])
                self.assertNotIn("ප.ව. 12:", r["from_12_si"])
                if idx > 0:
                    self.assertEqual(rows[idx - 1]["m1"], r["m0"])
                    # Adjacent rows within the same day must always differ in displayed status
                    self.assertNotEqual(rows[idx - 1]["grade"], r["grade"])
                for jargon_key in ("pakshi", "tara", "hora", "doshas_si", "yogas_si"):
                    self.assertNotIn(jargon_key, r)

        self.assertEqual(seen_grades, {"SUPREME", "VERY_GOOD", "GOOD", "NEUTRAL", "BAD", "VERY_BAD"})

        # Clipped working-hours window (08:00 - 17:30 => 480..1050)
        clipped = compute_daily_fortune_schedule(
            prof, datetime.date(2026, 11, 12), days=3, from_min=480, to_min=1050,
        )
        for day in clipped["days"]:
            rows = day["rows"]
            self.assertEqual(rows[0]["m0"], 480)
            self.assertEqual(rows[0]["from_24"], "08:00")
            self.assertEqual(rows[-1]["m1"], 1050)
            self.assertEqual(rows[-1]["to_24"], "17:30")


class TestDailyFortuneHTTPServer(unittest.TestCase):
    """Verify standalone HTTP server routes, static assets, and validations."""

    def test_http_server_endpoints(self) -> None:
        server = create_server(host="127.0.0.1", port=0)
        port = server.server_address[1]
        th = threading.Thread(target=server.serve_forever, daemon=True)
        th.start()
        base = f"http://127.0.0.1:{port}"
        try:
            for path in ("/", "/styles.css", "/i18n.js", "/app.js"):
                with urllib.request.urlopen(f"{base}{path}") as r:
                    self.assertEqual(r.status, 200)
                    self.assertGreater(len(r.read()), 500)

            with urllib.request.urlopen(f"{base}/healthz") as r:
                self.assertEqual(r.status, 200)
                hc = json.loads(r.read().decode("utf-8"))
                self.assertEqual(hc["status"], "ok")

            with urllib.request.urlopen(f"{base}/manifest.webmanifest") as r:
                self.assertEqual(r.status, 200)
                self.assertIn("application/manifest+json", r.headers.get("Content-Type", ""))
                mf = json.loads(r.read().decode("utf-8"))
                self.assertEqual(mf["display"], "standalone")
                self.assertGreaterEqual(len(mf["icons"]), 3)

            with urllib.request.urlopen(f"{base}/sw.js") as r:
                self.assertEqual(r.status, 200)
                self.assertEqual(r.headers.get("Service-Worker-Allowed"), "/")
                self.assertIn("SHELL_CACHE", r.read().decode("utf-8"))

            for icon_path in (
                "/icons/icon-192.png",
                "/icons/icon-512.png",
                "/icons/icon-maskable-512.png",
                "/icons/apple-touch-icon.png",
            ):
                with urllib.request.urlopen(f"{base}{icon_path}") as r:
                    self.assertEqual(r.status, 200)
                    self.assertEqual(r.headers.get("Content-Type"), "image/png")
                    self.assertTrue(r.read().startswith(b"\x89PNG\r\n\x1a\n"))

            with urllib.request.urlopen(f"{base}/icons/icon.svg") as r:
                self.assertEqual(r.status, 200)
                self.assertIn("<svg", r.read().decode("utf-8"))

            with urllib.request.urlopen(f"{base}/favicon.ico") as r:
                self.assertEqual(r.status, 200)
                self.assertGreater(len(r.read()), 1000)

            with self.assertRaises(urllib.error.HTTPError) as bad_icon:
                urllib.request.urlopen(f"{base}/icons/../../fortune_server.py")
            self.assertEqual(bad_icon.exception.code, 404)
            bad_icon.exception.close()

            with urllib.request.urlopen(f"{base}/api/meta") as r:
                meta = json.loads(r.read().decode("utf-8"))
                self.assertTrue(meta.get("pwa"))
                self.assertEqual(len(meta["districts"]), len(SRI_LANKA_DISTRICTS))
                self.assertEqual(len(meta["cities"]), len(CITIES))
                self.assertGreaterEqual(len(meta["cities"]), 331)
                city_names = {c["name"] for c in meta["cities"]}
                self.assertTrue(any("wathupitiwala" in n.lower() for n in city_names))
                self.assertTrue(any("narammala" in n.lower() for n in city_names))
                self.assertEqual(len(meta["nakshatras"]), len(NAKSHATRAS_INFO))
                self.assertEqual(len(meta["rashis"]), len(RASHIS))

            # Auto-detect request
            req1 = urllib.request.Request(
                f"{base}/api/fortune",
                data=json.dumps({
                    "name": "Ruwan",
                    "birth_date": "1973-08-04",
                    "birth_time": "02:28",
                    "birth_city_id": 1,
                    "start_date": "2026-11-12",
                    "end_date": "2026-11-14",
                    "from_time": "06:00",
                    "to_time": "22:00",
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req1) as r:
                self.assertEqual(r.status, 200)
                d1 = json.loads(r.read().decode("utf-8"))
                self.assertEqual(d1["profile"]["janma_nak_en"], "Sita")
                self.assertEqual(d1["range"]["days_count"], 3)
                self.assertEqual(d1["days"][0]["rows"][0]["m0"], 360)
                self.assertEqual(d1["days"][0]["rows"][-1]["m1"], 1320)

            # Manual Nakshatra + unknown birth time + target city override
            req2 = urllib.request.Request(
                f"{base}/api/fortune",
                data=json.dumps({
                    "name": "Nimali",
                    "birth_date": "1995-03-18",
                    "birth_time": "",
                    "birth_city_id": 4,   # Kandy
                    "target_city_id": 1,  # Colombo
                    "nakshatra_id": 13,   # Hata
                    "pada": 2,
                    "lagna_id": 2,
                    "navamsa_id": 4,
                    "start_date": "2026-11-12",
                    "days": 1,
                    "from_time": "00:00",
                    "to_time": "24:00",
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req2) as r:
                self.assertEqual(r.status, 200)
                d2 = json.loads(r.read().decode("utf-8"))
                self.assertEqual(d2["profile"]["janma_nak_en"], "Hata")
                self.assertEqual(d2["profile"]["janma_lagna_en"], "Wrushaba")
                self.assertEqual(d2["profile"]["navamsa_en"], "Kataka")
                self.assertEqual(d2["location"]["city"], "Colombo")

            # PDF Export endpoint (/api/fortune/pdf) - Gated by Commercial Paywall
            req_pdf_unauthed = urllib.request.Request(
                f"{base}/api/fortune/pdf",
                data=json.dumps({
                    "schedule": d1,
                    "lang": "si",
                    "time_fmt": "12h",
                    "filter": "all",
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            # Unauthenticated / Trial must be 403 Forbidden
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req_pdf_unauthed)
            self.assertEqual(ctx.exception.code, 403)

            # Register & activate customer for test
            from fortune_engine import db
            test_cust = db.register_customer(name="Test User", whatsapp="0771234567")
            db.activate_customer(test_cust["id"], days=365)
            active_cust = db.get_customer_by_id(test_cust["id"])
            self.assertTrue(active_cust["can_print"])

            req_pdf = urllib.request.Request(
                f"{base}/api/fortune/pdf",
                data=json.dumps({
                    "schedule": d1,
                    "lang": "si",
                    "time_fmt": "12h",
                    "filter": "all",
                    "token": active_cust["token"],
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req_pdf) as r:
                self.assertEqual(r.status, 200)
                self.assertEqual(r.headers.get("Content-Type"), "application/pdf")
                self.assertIn("Daily_Fortune_Ruwan_2026-11-12.pdf", r.headers.get("Content-Disposition", ""))
                pdf_bytes = r.read()
                self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
                self.assertGreater(len(pdf_bytes), 10_000)

            # Invalid validations -> HTTP 400
            for bad_body in (
                {"name": "X", "birth_date": "1990-01-01", "start_date": "2026-11-12", "days": 45},
                {"name": "X", "birth_date": "1990-01-01", "start_date": "2026-11-15", "end_date": "2026-11-12"},
                {"name": "X", "birth_date": "1990-01-01", "from_time": "18:00", "to_time": "09:00"},
                {"name": "X"},
            ):
                bad_req = urllib.request.Request(
                    f"{base}/api/fortune",
                    data=json.dumps(bad_body).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(bad_req)
                self.assertEqual(ctx.exception.code, 400)
                ctx.exception.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
