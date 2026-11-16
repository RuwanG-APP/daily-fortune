"""Astronomical core & lightweight Natal Profile resolver for Daily Fortune."""

from __future__ import annotations

import datetime
import math
from typing import Any, Dict, Optional, Tuple

import astronomy

from .constants import NAKSHATRAS_INFO, RASHIS, WEEKDAYS

J2000_JD = 2451545.0
J1900_STAR_JD = 2415020.0
NAKSHATRA_SPAN_DEG = 360.0 / 27.0
PADA_SPAN_DEG = NAKSHATRA_SPAN_DEG / 4.0

RASHI_LORDS: Dict[int, str] = {
    1: "mars",
    2: "venus",
    3: "mercury",
    4: "moon",
    5: "sun",
    6: "mercury",
    7: "venus",
    8: "mars",
    9: "jupiter",
    10: "saturn",
    11: "saturn",
    12: "jupiter",
}

LORD_NAME_TO_KEY: Dict[str, str] = {
    "ravi": "sun",
    "sun": "sun",
    "chandra": "moon",
    "sandu": "moon",
    "moon": "moon",
    "kuja": "mars",
    "mars": "mars",
    "budha": "mercury",
    "mercury": "mercury",
    "guru": "jupiter",
    "jupiter": "jupiter",
    "sikuru": "venus",
    "venus": "venus",
    "shani": "saturn",
    "saturn": "saturn",
}

PLANET_DIGNITIES: Dict[str, Dict[str, set[int]]] = {
    "sun":     {"exalted": {1},     "debilitated": {7},  "own": {5}},
    "moon":    {"exalted": {2},     "debilitated": {8},  "own": {4}},
    "mars":    {"exalted": {10},    "debilitated": {4},  "own": {1, 8}},
    "mercury": {"exalted": {6},     "debilitated": {12}, "own": {3, 6}},
    "jupiter": {"exalted": {4},     "debilitated": {10}, "own": {9, 12}},
    "venus":   {"exalted": {12},    "debilitated": {6},  "own": {2, 7}},
    "saturn":  {"exalted": {7},     "debilitated": {1},  "own": {10, 11}},
}

NATURAL_FRIENDS: Dict[str, set[str]] = {
    "sun":     {"moon", "mars", "jupiter"},
    "moon":    {"sun", "mercury"},
    "mars":    {"sun", "moon", "jupiter"},
    "mercury": {"sun", "venus"},
    "jupiter": {"sun", "moon", "mars"},
    "venus":   {"mercury", "saturn"},
    "saturn":  {"mercury", "venus"},
}

NATURAL_ENEMIES: Dict[str, set[str]] = {
    "sun":     {"venus", "saturn"},
    "moon":    set(),
    "mars":    {"mercury"},
    "mercury": {"moon"},
    "jupiter": {"mercury", "venus"},
    "venus":   {"sun", "moon"},
    "saturn":  {"sun", "moon", "mars"},
}


def norm_deg(angle: float) -> float:
    return angle % 360.0


def norm_hours(hours: float) -> float:
    return hours % 24.0


def make_astro_time(utc_dt: datetime.datetime) -> astronomy.Time:
    return astronomy.Time.Make(
        utc_dt.year, utc_dt.month, utc_dt.day,
        utc_dt.hour, utc_dt.minute, float(utc_dt.second),
    )


def calc_ayanamsa(jd_ut: float, system: str = "arc_ray") -> float:
    """Compute Sri Lankan Arc-Ray (default) or Lahiri/KP/Raman Ayanamsa in degrees."""
    sys_key = system.lower()
    if sys_key == "sayana":
        return 0.0
    if sys_key == "arc_ray":
        days = jd_ut - J1900_STAR_JD
        return ((days / 365.0 - 1.0) * 0.00011125 + 50.2564) * days / 1314000.0 + 22.42762714

    t_j2000 = (jd_ut - J2000_JD) / 36525.0
    prec_deg = (5029.0966 * t_j2000 + 1.11113 * t_j2000 * t_j2000) / 3600.0
    if sys_key == "lahiri":
        return 23.857092 + prec_deg
    if sys_key == "kp":
        return 23.766528 + prec_deg
    if sys_key == "raman":
        return 22.411194 + prec_deg
    return 23.857092 + prec_deg


def _true_obliquity_deg(jd_ut: float) -> float:
    t = (jd_ut - J2000_JD) / 36525.0
    eps0_arcsec = (
        84381.448
        - 46.8150 * t
        - 0.00059 * (t ** 2)
        + 0.001813 * (t ** 3)
    )
    omega = math.radians(125.04452 - 1934.136261 * t)
    lsun = math.radians(280.4665 + 36000.7698 * t)
    d_eps_arcsec = 9.20 * math.cos(omega) + 0.57 * math.cos(2.0 * lsun)
    return (eps0_arcsec + d_eps_arcsec) / 3600.0


def calc_lagna_tropical(jd_ut: float, lat_deg: float, lmst_hours: float) -> float:
    ramc = math.radians(lmst_hours * 15.0)
    eps = math.radians(_true_obliquity_deg(jd_ut))
    phi = math.radians(lat_deg)
    y = math.cos(ramc)
    x = -(math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps))
    return norm_deg(math.degrees(math.atan2(y, x)))


def solar_lunar_lagna_at(
    local_dt: datetime.datetime,
    lat_deg: float,
    lon_deg: float,
    tz_offset_hours: float = 5.5,
    ayanamsa_system: str = "arc_ray",
) -> Tuple[float, float, float]:
    """Return sidereal (sun_lon, moon_lon, lagna_lon) in degrees."""
    utc_dt = local_dt - datetime.timedelta(seconds=round(tz_offset_hours * 3600.0))
    t_astro = make_astro_time(utc_dt)
    jd_ut = t_astro.ut + J2000_JD
    ayan = calc_ayanamsa(jd_ut, ayanamsa_system)

    sun_ecl = astronomy.Ecliptic(astronomy.GeoVector(astronomy.Body.Sun, t_astro, True))
    moon_ecl = astronomy.Ecliptic(astronomy.GeoVector(astronomy.Body.Moon, t_astro, True))
    gast_h = norm_hours(astronomy.SiderealTime(t_astro))
    lmst_h = norm_hours(gast_h + lon_deg / 15.0)
    trop_lagna = calc_lagna_tropical(jd_ut, lat_deg, lmst_h)

    return (
        norm_deg(sun_ecl.elon - ayan),
        norm_deg(moon_ecl.elon - ayan),
        norm_deg(trop_lagna - ayan),
    )


def lagna_lon_at(
    local_dt: datetime.datetime,
    lat_deg: float,
    lon_deg: float,
    tz_offset_hours: float = 5.5,
    ayanamsa_system: str = "arc_ray",
) -> float:
    """Fast sidereal Lagna only (avoids Sun/Moon ephemeris lookups during horizon scan)."""
    utc_dt = local_dt - datetime.timedelta(seconds=round(tz_offset_hours * 3600.0))
    t_astro = make_astro_time(utc_dt)
    jd_ut = t_astro.ut + J2000_JD
    ayan = calc_ayanamsa(jd_ut, ayanamsa_system)
    gast_h = norm_hours(astronomy.SiderealTime(t_astro))
    lmst_h = norm_hours(gast_h + lon_deg / 15.0)
    return norm_deg(calc_lagna_tropical(jd_ut, lat_deg, lmst_h) - ayan)


def search_sunrise_sunset(
    local_date: datetime.date,
    lat_deg: float,
    lon_deg: float,
    tz_offset_hours: float = 5.5,
) -> Tuple[datetime.datetime, datetime.datetime]:
    """Find astronomical Sunrise & Sunset in local civil datetime for local_date."""
    obs = astronomy.Observer(lat_deg, lon_deg, 0.0)
    local_midnight = datetime.datetime(local_date.year, local_date.month, local_date.day, 0, 0, 0)
    utc_start = local_midnight - datetime.timedelta(seconds=round(tz_offset_hours * 3600.0))
    t_start = make_astro_time(utc_start)

    rise = astronomy.SearchRiseSet(astronomy.Body.Sun, obs, astronomy.Direction.Rise, t_start, 1.5)
    sunset = astronomy.SearchRiseSet(astronomy.Body.Sun, obs, astronomy.Direction.Set, t_start, 1.5)

    def _to_local(at: Optional[astronomy.Time], fallback_h: int) -> datetime.datetime:
        if at is None:
            return local_midnight + datetime.timedelta(hours=fallback_h)
        u = at.Utc()
        sec_int = int(round(u.second))
        base = datetime.datetime(u.year, u.month, u.day, u.hour, u.minute, 0)
        return base + datetime.timedelta(seconds=sec_int + round(tz_offset_hours * 3600.0))

    return _to_local(rise, 6), _to_local(sunset, 18)


def get_rashi_id(lon_deg: float) -> int:
    return (int(norm_deg(lon_deg) // 30.0) % 12) + 1


def get_nakshatra_pada(lon_deg: float) -> Tuple[int, int]:
    lon = norm_deg(lon_deg)
    nak0 = int(lon // NAKSHATRA_SPAN_DEG) % 27
    rem = lon - nak0 * NAKSHATRA_SPAN_DEG
    pada = min(int(rem // PADA_SPAN_DEG) + 1, 4)
    return nak0 + 1, pada


def calc_navamsa_id(lon_deg: float) -> int:
    return (int(norm_deg(lon_deg) // PADA_SPAN_DEG) % 12) + 1


def moon_rashi_from_nak_pada(nak_id: int, pada: int) -> int:
    """Exact 1..12 Rashi containing (nak_id 1..27, pada 1..4)."""
    quarter = (nak_id - 1) * 4 + (max(1, min(4, pada)) - 1)
    return (quarter // 9) + 1


def _evaluate_hora_roles(
    lagna_id: int,
    navamsa_id: Optional[int],
    natal_rashi_map: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """Compute functional benefic/malefic + natal dignity + Navamsa weights (-14..+14) for 7 Hora lords."""
    kendra_trikona = {1, 4, 5, 7, 9, 10}
    trikona = {1, 5, 9}
    kendra = {1, 4, 7, 10}
    dusthana = {6, 8, 12}

    roles: Dict[str, int] = {}
    for planet in ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"):
        owned_houses = [
            h for h in range(1, 13)
            if RASHI_LORDS[((lagna_id - 1 + h - 1) % 12) + 1] == planet
        ]
        owns_t = any(h in trikona for h in owned_houses)
        owns_k = any(h in kendra for h in owned_houses)
        owns_d = any(h in dusthana for h in owned_houses)

        if 1 in owned_houses or (owns_t and owns_k):
            func_score = 9
        elif owns_t and not owns_d:
            func_score = 7
        elif owns_k and not owns_d and not (set(owned_houses) <= {3, 6, 11}):
            func_score = 5
        elif owns_d and not owns_t and 1 not in owned_houses:
            func_score = -6 if set(owned_houses).isdisjoint(kendra_trikona) else 1
        elif set(owned_houses) <= {2, 3, 11}:
            func_score = 0 if 11 in owned_houses else -2
        else:
            func_score = 2

        dig_score = 0
        if natal_rashi_map and planet in natal_rashi_map:
            r_id = natal_rashi_map[planet]
            dig = PLANET_DIGNITIES[planet]
            lord = RASHI_LORDS[r_id]
            if r_id in dig["exalted"] or r_id in dig["own"]:
                dig_score = 4
            elif r_id in dig["debilitated"]:
                dig_score = -4
            elif lord == planet or lord in NATURAL_FRIENDS.get(planet, set()):
                dig_score = 2
            elif lord in NATURAL_ENEMIES.get(planet, set()):
                dig_score = -2

        nav_bonus = 0
        if navamsa_id is not None:
            nav_trines = {
                RASHI_LORDS[((navamsa_id - 1 + h - 1) % 12) + 1]
                for h in (1, 5, 9)
            }
            if planet in nav_trines:
                nav_bonus = 2

        roles[planet] = func_score + dig_score + nav_bonus
    return roles


def resolve_birth_profile(
    name: str,
    birth_date: datetime.date,
    birth_time: datetime.time,
    lat_deg: float,
    lon_deg: float,
    city_name: str,
    city_si: str,
    tz_offset_hours: float = 5.5,
    ayanamsa_system: str = "arc_ray",
    manual_nak_id: Optional[int] = None,
    manual_pada: Optional[int] = None,
    manual_lagna_id: Optional[int] = None,
    manual_navamsa_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Resolve the user's natal horoscope parameters concisely without needing a full birth-chart UI.
    - Computes exact sidereal positions for (birth_date, birth_time, lat_deg, lon_deg).
    - Honors manual Nakshatra / Pada / Lagna / Navamsa if user already knows them from their birth chart.
    """
    birth_dt = datetime.datetime.combine(birth_date, birth_time)
    utc_dt = birth_dt - datetime.timedelta(seconds=round(tz_offset_hours * 3600.0))
    t_astro = make_astro_time(utc_dt)
    jd_ut = t_astro.ut + J2000_JD
    ayan = calc_ayanamsa(jd_ut, ayanamsa_system)

    bodies = [
        ("sun", astronomy.Body.Sun),
        ("moon", astronomy.Body.Moon),
        ("mercury", astronomy.Body.Mercury),
        ("venus", astronomy.Body.Venus),
        ("mars", astronomy.Body.Mars),
        ("jupiter", astronomy.Body.Jupiter),
        ("saturn", astronomy.Body.Saturn),
    ]
    sid_lons: Dict[str, float] = {}
    natal_rashi_map: Dict[str, int] = {}
    for key, body in bodies:
        ecl = astronomy.Ecliptic(astronomy.GeoVector(body, t_astro, True))
        lon = norm_deg(ecl.elon - ayan)
        sid_lons[key] = lon
        natal_rashi_map[key] = get_rashi_id(lon)

    gast_h = norm_hours(astronomy.SiderealTime(t_astro))
    lmst_h = norm_hours(gast_h + lon_deg / 15.0)
    auto_lagna_lon = norm_deg(calc_lagna_tropical(jd_ut, lat_deg, lmst_h) - ayan)

    auto_lagna_id = get_rashi_id(auto_lagna_lon)
    auto_navamsa_id = calc_navamsa_id(auto_lagna_lon)
    auto_nak_id, auto_pada = get_nakshatra_pada(sid_lons["moon"])
    auto_moon_rashi_id = natal_rashi_map["moon"]

    diff = norm_deg(sid_lons["moon"] - sid_lons["sun"])
    paksha = "Shukla" if diff < 180.0 else "Krishna"

    # Resolve Nakshatra & Pada
    if manual_nak_id is not None and 1 <= int(manual_nak_id) <= 27:
        nak_id = int(manual_nak_id)
        nak_source = "manual"
        if manual_pada is not None and 1 <= int(manual_pada) <= 4:
            pada = int(manual_pada)
        elif nak_id == auto_nak_id:
            pada = auto_pada
        else:
            # Check if Moon Rashi at birth overlaps one side of this Nakshatra; otherwise default Pada 2
            possible_rashis = {p: moon_rashi_from_nak_pada(nak_id, p) for p in range(1, 5)}
            matching = [p for p, r in possible_rashis.items() if r == auto_moon_rashi_id]
            pada = matching[0] if matching else 2
        rashi_id = moon_rashi_from_nak_pada(nak_id, pada)
    else:
        nak_id = auto_nak_id
        pada = int(manual_pada) if (manual_pada is not None and 1 <= int(manual_pada) <= 4) else auto_pada
        rashi_id = moon_rashi_from_nak_pada(nak_id, pada) if manual_pada else auto_moon_rashi_id
        nak_source = "auto"

    # Resolve Lagna & Navamsa
    if manual_lagna_id is not None and 1 <= int(manual_lagna_id) <= 12:
        lagna_id = int(manual_lagna_id)
        lagna_source = "manual"
    else:
        lagna_id = auto_lagna_id
        lagna_source = "auto"

    if manual_navamsa_id is not None and 1 <= int(manual_navamsa_id) <= 12:
        navamsa_id: Optional[int] = int(manual_navamsa_id)
        navamsa_source = "manual"
    elif lagna_id == auto_lagna_id:
        navamsa_id = auto_navamsa_id
        navamsa_source = "auto"
    else:
        navamsa_id = None
        navamsa_source = "unspecified"

    nak_meta = NAKSHATRAS_INFO[nak_id - 1]
    lagna_meta = RASHIS[lagna_id - 1]
    rashi_meta = RASHIS[rashi_id - 1]
    navamsa_meta = RASHIS[navamsa_id - 1] if navamsa_id is not None else None

    hora_weights = _evaluate_hora_roles(lagna_id, navamsa_id, natal_rashi_map)

    return {
        "name": name.strip() or "Guest",
        "birth_date": birth_date.isoformat(),
        "birth_time": birth_time.strftime("%H:%M"),
        "birth_city": city_name,
        "birth_city_si": city_si,
        "janma_lagna_id": lagna_id,
        "janma_lagna_en": lagna_meta["short_en"],
        "janma_lagna_si": lagna_meta["si"],
        "lagna_source": lagna_source,
        "navamsa_id": navamsa_id,
        "navamsa_en": navamsa_meta["short_en"] if navamsa_meta else None,
        "navamsa_si": navamsa_meta["si"] if navamsa_meta else None,
        "navamsa_source": navamsa_source,
        "janma_nak_id": nak_id,
        "janma_nak_en": nak_meta["short_en"],
        "janma_nak_si": nak_meta["si"],
        "janma_pada": pada,
        "nak_source": nak_source,
        "janma_rashi_id": rashi_id,
        "janma_rashi_en": rashi_meta["short_en"],
        "janma_rashi_si": rashi_meta["si"],
        "janma_paksha": paksha,
        "hora_weights": hora_weights,
    }
