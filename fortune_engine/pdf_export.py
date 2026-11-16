"""Clean A4 Commercial PDF Export for Daily Fortune (via headless Chromium / Edge)."""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional


_GRADE_STYLE = {
    "SUPREME":   ("linear-gradient(135deg,#065f46,#047857)", "#fef08a", "#d97706"),
    "VERY_GOOD": ("#059669", "#ffffff", "#047857"),
    "GOOD":      ("#dcfce7", "#166534", "#86efac"),
    "NEUTRAL":   ("#fef3c7", "#92400e", "#fcd34d"),
    "BAD":       ("#ffedd5", "#c2410c", "#fdba74"),
    "VERY_BAD":  ("#dc2626", "#ffffff", "#b91c1c"),
}


def find_browser_binary() -> Optional[str]:
    """Locate Chrome or Edge executable for lossless HarfBuzz Sinhala A4 PDF rendering."""
    for env_key in ("DF_CHROME_PATH", "CHROME_BIN"):
        env_path = os.environ.get(env_key, "").strip()
        if env_path and Path(env_path).is_file():
            return env_path

    for cmd in ("chrome", "google-chrome", "chromium", "chromium-browser", "msedge"):
        found = shutil.which(cmd)
        if found:
            return found

    local_app = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    if local_app:
        candidates.insert(0, str(Path(local_app) / "Google" / "Chrome" / "Application" / "chrome.exe"))
        candidates.append(str(Path(local_app) / "Microsoft" / "Edge" / "Application" / "msedge.exe"))

    for path_str in candidates:
        if Path(path_str).is_file():
            return path_str
    return None


def _fmt_time(row: Dict[str, Any], which: str, lang: str, time_fmt: str) -> str:
    if time_fmt == "24h":
        return row["from_24"] if which == "from" else row["to_24"]
    if lang == "si":
        return row["from_12_si"] if which == "from" else row["to_12_si"]
    return row["from_12_en"] if which == "from" else row["to_12_en"]


def build_fortune_pdf_html(
    schedule: Dict[str, Any],
    rows: Optional[List[Dict[str, Any]]] = None,
    lang: str = "si",
    time_fmt: str = "12h",
    filter_key: str = "all",
) -> str:
    """Build print-ready A4 HTML with native Windows Sinhala fonts."""
    is_si = lang == "si"
    p = schedule["profile"]
    loc = schedule["location"]
    rng = schedule["range"]

    all_rows = rows if rows is not None else schedule["rows"]
    if filter_key == "good":
        filtered = [r for r in all_rows if int(r["level"]) >= 4]
    elif filter_key == "best":
        filtered = [r for r in all_rows if int(r["level"]) >= 5]
    elif filter_key == "bad":
        filtered = [r for r in all_rows if int(r["level"]) <= 2]
    else:
        filtered = list(all_rows)

    title_txt = "පුද්ගලික සුභ–අසුභ කාලසටහන" if is_si else "Personal Auspicious Time Schedule"
    sub_brand = "Daily Fortune"
    lbl_bdate = "උපන් දිනය" if is_si else "Birth Date"
    lbl_lagna = "ලග්නය" if is_si else "Lagna"
    lbl_nak = "නැකත" if is_si else "Nakshatra"
    lbl_nav = "නවාංශකය" if is_si else "Navamsa"
    pada_word = "පාදය" if is_si else "Pada"

    lagna_val = p["janma_lagna_si"] if is_si else p["janma_lagna_en"]
    nak_base = p["janma_nak_si"] if is_si else p["janma_nak_en"]
    nak_val = f"{nak_base} ({pada_word} {p['janma_pada']})"
    nav_val = (p["navamsa_si"] if is_si else p["navamsa_en"]) if p.get("navamsa_si") else "—"

    city_val = loc["city_si"] if is_si else loc["city"]
    range_str = rng["start_date"] if rng["start_date"] == rng["end_date"] else f"{rng['start_date']} – {rng['end_date']}"

    filter_names_si = {"all": "සියලුම වේලාවන්", "good": "සුභ වේලාවන්", "best": "ඉතා සුභ / ඉතාමත් සුභ", "bad": "අසුභ වේලාවන්"}
    filter_names_en = {"all": "All Times", "good": "Auspicious (Good+)", "best": "Very Good & Supreme", "bad": "Inauspicious Only"}
    flt_txt = (filter_names_si if is_si else filter_names_en).get(filter_key, "")

    col_date = "දිනය" if is_si else "Date"
    col_from = "වේලාව (සිට)" if is_si else "From"
    col_to = "දක්වා" if is_si else "To"
    col_status = "තත්වය" if is_si else "Condition"

    legend_html = "".join(
        f'<span class="leg" style="background:{_GRADE_STYLE[g["grade"]][0]};'
        f'color:{_GRADE_STYLE[g["grade"]][1]};border-color:{_GRADE_STYLE[g["grade"]][2]};">'
        f'{html.escape(g["si"] if is_si else g["en"])}</span>'
        for g in schedule.get("grades_legend", [])
    )

    body_rows: List[str] = []
    multi_day = rng["days_count"] > 1
    prev_d = None
    for r in filtered:
        wd = r["weekday_si"] if is_si else r["weekday_en"]
        if multi_day and r["date"] != prev_d:
            body_rows.append(
                f'<tr class="day-div"><td colspan="4">{html.escape(r["date"])} — {html.escape(wd)}</td></tr>'
            )
            prev_d = r["date"]

        bg, fg, bd = _GRADE_STYLE.get(r["grade"], ("#eee", "#222", "#ccc"))
        g_txt = r["grade_si"] if is_si else r["grade_en"]
        star = "★ " if r["grade"] == "SUPREME" else ""
        from_s = _fmt_time(r, "from", lang, time_fmt)
        to_s = _fmt_time(r, "to", lang, time_fmt)

        body_rows.append(
            f'<tr>'
            f'<td class="c-date"><strong>{html.escape(r["date"])}</strong><span class="wd">{html.escape(wd)}</span></td>'
            f'<td class="c-time">{html.escape(from_s)}</td>'
            f'<td class="c-time">{html.escape(to_s)}</td>'
            f'<td><span class="badge" style="background:{bg};color:{fg};border-color:{bd};">{star}{html.escape(g_txt)}</span></td>'
            f'</tr>'
        )

    if not body_rows:
        empty_msg = "තෝරාගත් පෙරහනට ගැලපෙන වේලාවන් නොමැත." if is_si else "No time windows match."
        body_rows.append(f'<tr><td colspan="4" class="empty">{html.escape(empty_msg)}</td></tr>')

    return f"""<!DOCTYPE html>
<html lang="{html.escape(lang)}">
<head>
<meta charset="utf-8" />
<title>{html.escape(sub_brand)} — {html.escape(p["name"])}</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 11mm 12mm;
  }}
  * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  body {{
    margin: 0;
    font-family: "Nirmala UI", "Iskoola Pota", "Noto Sans Sinhala", "Segoe UI", sans-serif;
    color: #221d17;
    background: #ffffff;
    font-size: 11.5px;
    line-height: 1.45;
  }}
  .cert-card {{
    border: 1.5px solid #d97706;
    border-top: 5px solid #b45309;
    border-radius: 12px;
    padding: 12px 14px;
    background: #fffcf5;
    margin-bottom: 10px;
  }}
  .cert-top {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 8px;
  }}
  .kicker {{
    font-size: 10px;
    font-weight: 700;
    color: #b45309;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }}
  .pname {{
    font-size: 19px;
    font-weight: 800;
    margin: 2px 0 0;
    color: #1f1710;
  }}
  .brand-pill {{
    background: #5c3718;
    color: #fde68a;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 700;
  }}
  .id-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 7px;
  }}
  .id-box {{
    background: #ffffff;
    border: 1px solid #eadfcd;
    border-radius: 8px;
    padding: 6px 9px;
  }}
  .id-lbl {{ display: block; font-size: 9.5px; color: #6c6155; font-weight: 600; }}
  .id-val {{ display: block; font-size: 12px; font-weight: 800; color: #221d17; }}
  .meta-line {{
    margin-top: 8px;
    font-size: 10.5px;
    color: #5c5044;
    font-weight: 600;
  }}
  .legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-bottom: 9px;
  }}
  .leg {{
    font-size: 9.5px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid transparent;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    border: 1px solid #dfd2be;
  }}
  thead {{ display: table-header-group; }}
  tr {{ break-inside: avoid; }}
  th {{
    background: #f5ebd8;
    color: #5c3718;
    text-align: left;
    padding: 7px 9px;
    font-size: 10.5px;
    font-weight: 800;
    border-bottom: 1.5px solid #d5c3a8;
  }}
  td {{
    padding: 6px 9px;
    border-bottom: 1px solid #f0e6d6;
    vertical-align: middle;
  }}
  tr.day-div td {{
    background: #faf3e4;
    color: #78350f;
    font-weight: 800;
    font-size: 10.5px;
    padding: 5px 9px;
    border-top: 1.5px solid #dfd2be;
  }}
  .c-date strong {{ display: block; font-size: 11px; }}
  .wd {{ display: block; font-size: 9.5px; color: #6c6155; }}
  .c-time {{ font-weight: 700; white-space: nowrap; font-variant-numeric: tabular-nums; font-size: 11.5px; }}
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    border: 1px solid transparent;
    font-weight: 800;
    font-size: 10.5px;
    white-space: nowrap;
  }}
  .empty {{ text-align: center; padding: 18px; color: #6c6155; }}
  .footer-note {{
    margin-top: 10px;
    text-align: right;
    font-size: 9px;
    color: #8a7e70;
  }}
</style>
</head>
<body>
  <div class="cert-card">
    <div class="cert-top">
      <div>
        <div class="kicker">{html.escape(title_txt)}</div>
        <div class="pname">{html.escape(p["name"])}</div>
      </div>
      <span class="brand-pill">{html.escape(sub_brand)}</span>
    </div>
    <div class="id-grid">
      <div class="id-box"><span class="id-lbl">{html.escape(lbl_bdate)}</span><span class="id-val">{html.escape(p["birth_date"])}</span></div>
      <div class="id-box"><span class="id-lbl">{html.escape(lbl_lagna)}</span><span class="id-val">{html.escape(lagna_val)}</span></div>
      <div class="id-box"><span class="id-lbl">{html.escape(lbl_nak)}</span><span class="id-val">{html.escape(nak_val)}</span></div>
      <div class="id-box"><span class="id-lbl">{html.escape(lbl_nav)}</span><span class="id-val">{html.escape(nav_val)}</span></div>
    </div>
    <div class="meta-line">{html.escape(city_val)} &nbsp;•&nbsp; {html.escape(range_str)} ({html.escape(rng["from_time"])} – {html.escape(rng["to_time"])}) &nbsp;•&nbsp; {html.escape(flt_txt)}</div>
  </div>

  <div class="legend">{legend_html}</div>

  <table>
    <thead>
      <tr>
        <th>{html.escape(col_date)}</th>
        <th>{html.escape(col_from)}</th>
        <th>{html.escape(col_to)}</th>
        <th>{html.escape(col_status)}</th>
      </tr>
    </thead>
    <tbody>
      {"".join(body_rows)}
    </tbody>
  </table>

  <div class="footer-note">Daily Fortune • {html.escape(city_val)}</div>
</body>
</html>
"""


def safe_pdf_filename(name: str, start_date: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "Report"
    return f"Daily_Fortune_{slug}_{start_date}.pdf"


def render_fortune_pdf_bytes(
    schedule: Dict[str, Any],
    lang: str = "si",
    time_fmt: str = "12h",
    filter_key: str = "all",
) -> bytes:
    """Render the Daily Fortune schedule directly into a crisp multi-page A4 PDF file."""
    browser = find_browser_binary()
    if not browser:
        raise RuntimeError("Chrome or Edge browser not found for server PDF rendering.")

    html_doc = build_fortune_pdf_html(
        schedule=schedule,
        lang=lang,
        time_fmt=time_fmt,
        filter_key=filter_key,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        in_html = tmp / "fortune_report.html"
        out_pdf = tmp / "fortune_report.pdf"
        user_data = tmp / "chrome_profile"
        in_html.write_text(html_doc, encoding="utf-8")

        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--no-pdf-header-footer",
        ]
        if os.name != "nt":
            # Cloud/Linux containers typically lack Chromium sandbox user namespaces or large /dev/shm
            cmd.extend(["--no-sandbox", "--disable-dev-shm-usage"])
        cmd.extend([
            f"--user-data-dir={user_data}",
            f"--print-to-pdf={out_pdf}",
            in_html.as_uri(),
        ])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0 or not out_pdf.is_file():
            err = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"PDF export failed (code {proc.returncode}): {err}")
        return out_pdf.read_bytes()
