"""Daily Fortune - Personalized 6-Tier Auspicious/Inauspicious Time Engine."""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Tuple

from .astro_core import (
    LORD_NAME_TO_KEY,
    NATURAL_ENEMIES,
    NATURAL_FRIENDS,
    RASHI_LORDS,
    get_nakshatra_pada,
    get_rashi_id,
    lagna_lon_at,
    norm_deg,
    search_sunrise_sunset,
    solar_lunar_lagna_at,
)
from .constants import (
    CHALDEAN_ORDER,
    FIXED_KARANAS,
    MOVABLE_KARANAS,
    WEEKDAYS,
    WEEKDAY_TO_CHALDEAN_IDX,
)

NAKSHATRA_SPAN_DEG = 360.0 / 27.0
PADA_SPAN_DEG = NAKSHATRA_SPAN_DEG / 4.0

# 6-Tier Grade Palette matching customer expectations
GRADE_INFO_6: Dict[str, Dict[str, Any]] = {
    "SUPREME":   {"level": 6, "si": "ඉතාමත් සුභ", "en": "Supreme Auspicious", "css": "supreme",  "auspicious": True},
    "VERY_GOOD": {"level": 5, "si": "ඉතා සුභ",     "en": "Very Good",          "css": "vgood",    "auspicious": True},
    "GOOD":      {"level": 4, "si": "සුභ",         "en": "Good",               "css": "good",     "auspicious": True},
    "NEUTRAL":   {"level": 3, "si": "සාමාන්‍ය",     "en": "Normal",             "css": "neutral",  "auspicious": False},
    "BAD":       {"level": 2, "si": "අසුභ",        "en": "Inauspicious",       "css": "bad",      "auspicious": False},
    "VERY_BAD":  {"level": 1, "si": "ඉතා අසුභ",    "en": "Very Inauspicious",  "css": "vbad",     "auspicious": False},
}

PAKSHI_BIRDS = ["Vulture", "Owl", "Crow", "Cock", "Peacock"]
PAKSHI_ACTIVITY_WEIGHTS: Dict[str, int] = {
    "Rule": 48,
    "Walk": 36,
    "Eat": 30,
    "Sleep": 18,
    "Die": 12,
}
PAKSHI_MAIN_PTS = {"Rule": 17, "Eat": 12, "Walk": 3, "Sleep": -10, "Die": -19}
PAKSHI_SUB_PTS = {"Rule": 8, "Eat": 5, "Walk": 1, "Sleep": -4, "Die": -7}

PAKSHI_PHASE_CONFIG: Dict[Tuple[str, bool], Dict[str, Any]] = {
    ("Shukla", True): {
        "cycle": ["Eat", "Walk", "Rule", "Sleep", "Die"],
        "wheel": ["Vulture", "Owl", "Crow", "Cock", "Peacock"],
        "yama1_eaters": ["Vulture", "Owl", "Vulture", "Owl", "Crow", "Cock", "Peacock"],
        "friend_ring": ["Vulture", "Owl", "Crow", "Cock", "Peacock"],
    },
    ("Shukla", False): {
        "cycle": ["Eat", "Rule", "Die", "Walk", "Sleep"],
        "wheel": ["Vulture", "Peacock", "Cock", "Crow", "Owl"],
        "yama1_eaters": ["Crow", "Cock", "Crow", "Cock", "Peacock", "Vulture", "Owl"],
        "friend_ring": ["Vulture", "Owl", "Crow", "Cock", "Peacock"],
    },
    ("Krishna", True): {
        "cycle": ["Eat", "Die", "Sleep", "Rule", "Walk"],
        "wheel": ["Vulture", "Cock", "Owl", "Peacock", "Crow"],
        "yama1_eaters": ["Cock", "Peacock", "Cock", "Crow", "Owl", "Vulture", "Peacock"],
        "friend_ring": ["Vulture", "Cock", "Owl", "Peacock", "Crow"],
    },
    ("Krishna", False): {
        "cycle": ["Eat", "Sleep", "Walk", "Die", "Rule"],
        "wheel": ["Vulture", "Peacock", "Cock", "Crow", "Owl"],
        "yama1_eaters": ["Vulture", "Cock", "Vulture", "Owl", "Crow", "Peacock", "Cock"],
        "friend_ring": ["Vulture", "Cock", "Owl", "Peacock", "Crow"],
    },
}

# Daytime 8-segment indices (1..8, Sun=0..Sat=6)
RAHU_SEG_DAY = [8, 2, 7, 5, 6, 4, 3]
YAMAGANDA_SEG_DAY = [5, 4, 3, 2, 1, 7, 6]
GULIKA_SEG_DAY = [7, 6, 5, 4, 3, 2, 1]

# Varjyam start offsets in Ghatis (out of 60 per Nakshatra span, duration = 4 Ghatis)
VARJYAM_START_GHATIS = [
    50, 24, 30, 40, 14, 21, 30, 20, 32,
    30, 20, 18, 21, 20, 14, 14, 10, 14,
    56, 56, 20, 10, 10, 18, 16, 24, 30,
]
AMRITA_OFFSET_SPECIAL = {1: -8, 4: 12, 6: 14, 19: -12}

# Amritadi Yoga Matrix (27 Nakshatras x 7 Weekdays Sun..Sat)
AMRITADI_YOGA_MATRIX: List[Tuple[str, ...]] = [
    ("Siddha", "Siddha", "Siddha", "Marana", "Amrita", "Amrita", "Siddha"),
    ("Prabal", "Siddha", "Siddha", "Siddha", "Siddha", "Siddha", "Siddha"),
    ("Siddha", "Marana", "Siddha", "Amrita", "Marana", "Siddha", "Siddha"),
    ("Siddha", "Amrita", "Amrita", "Siddha", "Marana", "Marana", "Amrita"),
    ("Siddha", "Siddha", "Siddha", "Siddha", "Marana", "Siddha", "Siddha"),
    ("Siddha", "Siddha", "Marana", "Siddha", "Marana", "Siddha", "Siddha"),
    ("Siddha", "Amrita", "Siddha", "Siddha", "Amrita", "Siddha", "Siddha"),
    ("Siddha", "Siddha", "Siddha", "Siddha", "Siddha", "Marana", "Siddha"),
    ("Siddha", "Siddha", "Siddha", "Siddha", "Siddha", "Marana", "Marana"),
    ("Marana", "Marana", "Siddha", "Siddha", "Amrita", "Marana", "Amrita"),
    ("Siddha", "Siddha", "Siddha", "Amrita", "Siddha", "Siddha", "Siddha"),
    ("Amrita", "Siddha", "Amrita", "Amrita", "Marana", "Siddha", "Marana"),
    ("Siddha", "Siddha", "Siddha", "Marana", "Siddha", "Amrita", "Marana"),
    ("Siddha", "Prabal", "Siddha", "Siddha", "Siddha", "Siddha", "Marana"),
    ("Siddha", "Amrita", "Siddha", "Siddha", "Amrita", "Siddha", "Siddha"),
    ("Marana", "Marana", "Marana", "Siddha", "Amrita", "Siddha", "Siddha"),
    ("Marana", "Siddha", "Siddha", "Amrita", "Siddha", "Siddha", "Siddha"),
    ("Siddha", "Siddha", "Siddha", "Siddha", "Marana", "Siddha", "Marana"),
    ("Siddha", "Siddha", "Siddha", "Siddha", "Siddha", "Marana", "Marana"),
    ("Siddha", "Siddha", "Amrita", "Siddha", "Amrita", "Siddha", "Siddha"),
    ("Amrita", "Siddha", "Siddha", "Amrita", "Siddha", "Siddha", "Siddha"),
    ("Siddha", "Amrita", "Siddha", "Marana", "Siddha", "Marana", "Siddha"),
    ("Siddha", "Siddha", "Siddha", "Siddha", "Siddha", "Siddha", "Marana"),
    ("Siddha", "Siddha", "Marana", "Siddha", "Marana", "Siddha", "Siddha"),
    ("Siddha", "Amrita", "Siddha", "Siddha", "Amrita", "Siddha", "Siddha"),
    ("Siddha", "Siddha", "Siddha", "Siddha", "Siddha", "Marana", "Siddha"),
    ("Siddha", "Siddha", "Siddha", "Siddha", "Siddha", "Amrita", "Marana"),
]

DAGDHA_TITHI_BY_WD: Dict[int, set[int]] = {
    0: {12}, 1: {11}, 2: {5}, 3: {2, 3}, 4: {6}, 5: {8}, 6: {9},
}
SIDDHA_TITHI_BY_WD: Dict[int, set[int]] = {
    2: {3, 8, 13},
    3: {2, 7, 12},
    4: {5, 10, 15},
    5: {1, 6, 11},
    6: {4, 9, 14},
}
BHULOKA_BHADRA_RASHIS = {4, 5, 11, 12}

TARABALA_PTS = {
    1: -3, 2: 14, 3: -15, 4: 11, 5: -13, 6: 13, 7: -22, 8: 12, 9: 16,
}
CHANDRABALA_PTS = {
    1: 10, 2: 3, 3: 8, 4: -4, 5: 3, 6: 8, 7: 8, 8: -22, 9: 3, 10: 10, 11: 10, 12: -8,
}
BHAVA_FROM_LAGNA_PTS = {
    1: 6, 2: 3, 3: 3, 4: 5, 5: 6, 6: -7, 7: 4, 8: -9, 9: 6, 10: 6, 11: 6, 12: -7,
}
WEEKDAY_LORD_KEY = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"]


def get_pancha_pakshi_birth_bird(nak_id: int, paksha: str) -> str:
    is_shukla = str(paksha).startswith(("Shukla", "Pura"))
    if nak_id <= 5:
        shukla_idx = 0
    elif nak_id <= 11:
        shukla_idx = 1
    elif nak_id <= 16:
        shukla_idx = 2
    elif nak_id <= 21:
        shukla_idx = 3
    else:
        shukla_idx = 4
    return PAKSHI_BIRDS[shukla_idx if is_shukla else (4 - shukla_idx)]


def get_bird_relationship(paksha: str, main_bird: str, sub_bird: str) -> str:
    if main_bird == sub_bird:
        return "Self"
    ring = PAKSHI_PHASE_CONFIG[(paksha, True)]["friend_ring"]
    diff = (ring.index(sub_bird) - ring.index(main_bird)) % 5
    return "Friend" if diff in (1, 4) else "Enemy"


def _grade_from_score_6(
    score: int,
    has_dosha: bool = False,
    is_vadha: bool = False,
    is_chandrashtama: bool = False,
) -> str:
    if score >= 86 and not has_dosha and not is_vadha and not is_chandrashtama:
        return "SUPREME"
    if score >= 73:
        return "VERY_GOOD"
    if score >= 58:
        return "GOOD"
    if score >= 42:
        return "NEUTRAL"
    if score >= 25:
        return "BAD"
    return "VERY_BAD"


def _fmt_24(minutes: int) -> str:
    if minutes >= 1440:
        return "24:00"
    h, m = divmod(max(0, minutes), 60)
    return f"{h:02d}:{m:02d}"


def _fmt_12_si(minutes: int) -> str:
    if minutes <= 0 or minutes >= 1440:
        return "මැදියම් රෑ 12:00"
    h24, m = divmod(minutes, 60)
    if h24 == 0:
        return f"අලුයම 12:{m:02d}"
    if h24 == 12:
        return f"දහවල් 12:{m:02d}"
    prefix = "පෙ.ව." if h24 < 12 else "ප.ව."
    h12 = h24 % 12
    return f"{prefix} {h12:02d}:{m:02d}"


def _fmt_12_en(minutes: int) -> str:
    if minutes <= 0 or minutes >= 1440:
        return "Midnight 12:00"
    h24, m = divmod(minutes, 60)
    if h24 == 12 and m == 0:
        return "Noon 12:00"
    suffix = "AM" if h24 < 12 else "PM"
    h12 = h24 % 12 or 12
    return f"{h12:02d}:{m:02d} {suffix}"


def _bisect_index_change(
    t_lo: datetime.datetime,
    t_hi: datetime.datetime,
    val_lo: int,
    eval_fn: Any,
) -> datetime.datetime:
    for _ in range(11):
        mid = t_lo + (t_hi - t_lo) / 2
        if eval_fn(mid) == val_lo:
            t_lo = mid
        else:
            t_hi = mid
    sec = (t_hi - datetime.datetime(t_hi.year, t_hi.month, t_hi.day)).total_seconds()
    rounded_min = int(round(sec / 60.0))
    return datetime.datetime(t_hi.year, t_hi.month, t_hi.day) + datetime.timedelta(minutes=rounded_min)


def _scan_transitions(
    start_dt: datetime.datetime,
    end_dt: datetime.datetime,
    step_minutes: int,
    eval_fn: Any,
) -> List[Tuple[datetime.datetime, int, int]]:
    out: List[Tuple[datetime.datetime, int, int]] = []
    cur_t = start_dt
    cur_v = eval_fn(cur_t)
    step = datetime.timedelta(minutes=step_minutes)
    while cur_t < end_dt:
        nxt_t = min(cur_t + step, end_dt)
        nxt_v = eval_fn(nxt_t)
        if nxt_v != cur_v:
            tx = _bisect_index_change(cur_t, nxt_t, cur_v, eval_fn)
            out.append((tx, cur_v, nxt_v))
            cur_v = nxt_v
        cur_t = nxt_t
    return out


def _build_pakshi_subperiods(
    span_start: datetime.datetime,
    span_end: datetime.datetime,
    vara_wd_idx: int,
    is_day: bool,
    natal_bird: str,
    cache: Dict[datetime.datetime, Tuple[float, float, float]],
    eval_coords: Tuple[float, float, float, str],
) -> List[Dict[str, Any]]:
    lat, lon, tz, ayan_sys = eval_coords
    total_sec = (span_end - span_start).total_seconds()
    if total_sec <= 0:
        return []
    yama_sec = total_sec / 5.0
    subperiods: List[Dict[str, Any]] = []

    for y_idx in range(5):
        y_start = span_start + datetime.timedelta(seconds=yama_sec * y_idx)
        y_end = span_start + datetime.timedelta(seconds=yama_sec * (y_idx + 1))
        y_mid = y_start + (y_end - y_start) / 2
        if y_mid not in cache:
            cache[y_mid] = solar_lunar_lagna_at(y_mid, lat, lon, tz, ayan_sys)
        sun_lon, moon_lon, _ = cache[y_mid]
        paksha = "Shukla" if norm_deg(moon_lon - sun_lon) < 180.0 else "Krishna"

        cfg = PAKSHI_PHASE_CONFIG[(paksha, is_day)]
        cycle = cfg["cycle"]
        wheel = cfg["wheel"]
        eater = cfg["yama1_eaters"][vara_wd_idx]

        main_pos = wheel.index(natal_bird)
        main_act_idx = (main_pos - wheel.index(eater) + y_idx) % 5
        main_act = cycle[main_act_idx]

        cur_t = y_start
        for step_k in range(5):
            sub_bird = wheel[(main_pos + step_k) % 5]
            sub_act = cycle[(main_act_idx + step_k) % 5]
            w_frac = PAKSHI_ACTIVITY_WEIGHTS[sub_act] / 144.0
            nxt_t = y_end if step_k == 4 else cur_t + datetime.timedelta(seconds=yama_sec * w_frac)
            subperiods.append({
                "start": cur_t,
                "end": nxt_t,
                "main_act": main_act,
                "sub_act": sub_act,
                "relationship": get_bird_relationship(paksha, natal_bird, sub_bird),
            })
            cur_t = nxt_t
    return subperiods


def _lookup_pakshi(items: List[Dict[str, Any]], mid_dt: datetime.datetime) -> Dict[str, Any]:
    for it in items:
        if it["start"] <= mid_dt <= it["end"]:
            return it
    return items[0]


def compute_daily_fortune_schedule(
    profile: Dict[str, Any],
    start_date: datetime.date,
    days: int = 1,
    lat_deg: float = 6.883333,
    lon_deg: float = 79.85,
    city_name: str = "Colombo",
    city_si: str = "කොළඹ",
    tz_offset_hours: float = 5.5,
    ayanamsa_system: str = "arc_ray",
    from_min: int = 0,
    to_min: int = 1440,
) -> Dict[str, Any]:
    """Compute a clean, 6-tier personalized Daily Fortune chart over [start_date..+days) & [from_min..to_min]."""
    days = max(1, min(31, int(days)))
    from_min = max(0, min(1439, int(from_min)))
    to_min = max(from_min + 1, min(1440, int(to_min)))

    birth_bird = get_pancha_pakshi_birth_bird(profile["janma_nak_id"], profile["janma_paksha"])
    hora_weights = profile["hora_weights"]
    coords = (lat_deg, lon_deg, tz_offset_hours, ayanamsa_system)

    sr_ss: Dict[datetime.date, Tuple[datetime.datetime, datetime.datetime]] = {}
    for d_off in range(-1, days + 2):
        d = start_date + datetime.timedelta(days=d_off)
        sr_ss[d] = search_sunrise_sunset(d, lat_deg, lon_deg, tz_offset_hours)

    astro_cache: Dict[datetime.datetime, Tuple[float, float, float]] = {}

    def _get_astro(dt: datetime.datetime) -> Tuple[float, float, float]:
        k = dt.replace(microsecond=0)
        val = astro_cache.get(k)
        if val is None:
            val = solar_lunar_lagna_at(k, lat_deg, lon_deg, tz_offset_hours, ayanamsa_system)
            astro_cache[k] = val
        return val

    # Scan Nakshatra boundaries across horizon for exact Varjyam & Amrita Kalam spans
    nak_scan_start = datetime.datetime.combine(start_date - datetime.timedelta(days=2), datetime.time(0, 0))
    nak_scan_end = datetime.datetime.combine(start_date + datetime.timedelta(days=days + 2), datetime.time(0, 0))
    nak_tx = _scan_transitions(
        nak_scan_start, nak_scan_end, 180,
        lambda dt: (int(_get_astro(dt)[1] // NAKSHATRA_SPAN_DEG) % 27) + 1,
    )
    nak_spans: List[Dict[str, Any]] = []
    for i in range(len(nak_tx) - 1):
        t0, _, n_id = nak_tx[i]
        t1, _, _ = nak_tx[i + 1]
        span = t1 - t0
        varj_g = VARJYAM_START_GHATIS[n_id - 1]
        amr_g = varj_g + AMRITA_OFFSET_SPECIAL.get(n_id, 24)
        nak_spans.append({
            "varjyam_start": t0 + span * (varj_g / 60.0),
            "varjyam_end": t0 + span * ((varj_g + 4) / 60.0),
            "amrita_start": t0 + span * (amr_g / 60.0),
            "amrita_end": t0 + span * ((amr_g + 4) / 60.0),
        })

    # Precompute Pancha Pakshi sub-periods
    pakshi_by_date: Dict[datetime.date, List[Dict[str, Any]]] = {}
    for d_off in range(-1, days + 1):
        d = start_date + datetime.timedelta(days=d_off)
        sr, ss = sr_ss[d]
        next_sr, _ = sr_ss[d + datetime.timedelta(days=1)]
        vara_wd = (d.weekday() + 1) % 7
        pakshi_by_date[d] = (
            _build_pakshi_subperiods(sr, ss, vara_wd, True, birth_bird, astro_cache, coords)
            + _build_pakshi_subperiods(ss, next_sr, vara_wd, False, birth_bird, astro_cache, coords)
        )

    day_summaries: List[Dict[str, Any]] = []
    all_rows: List[Dict[str, Any]] = []

    for d_idx in range(days):
        cur_date = start_date + datetime.timedelta(days=d_idx)
        day_start = datetime.datetime.combine(cur_date, datetime.time(0, 0))
        day_end = day_start + datetime.timedelta(days=1)

        prev_date = cur_date - datetime.timedelta(days=1)
        prev_sr, _ = sr_ss[prev_date]
        sr_today, ss_today = sr_ss[cur_date]
        next_sr, _ = sr_ss[cur_date + datetime.timedelta(days=1)]

        civil_wd_idx = (cur_date.weekday() + 1) % 7
        prev_wd_idx = (prev_date.weekday() + 1) % 7
        wd_meta = WEEKDAYS[civil_wd_idx]

        day_len = ss_today - sr_today
        seg8 = day_len / 8.0
        rahu_i = RAHU_SEG_DAY[civil_wd_idx] - 1
        yama_i = YAMAGANDA_SEG_DAY[civil_wd_idx] - 1
        guli_i = GULIKA_SEG_DAY[civil_wd_idx] - 1

        rahu_span = (sr_today + seg8 * rahu_i, sr_today + seg8 * (rahu_i + 1))
        yamaganda_span = (sr_today + seg8 * yama_i, sr_today + seg8 * (yama_i + 1))
        gulika_span = (sr_today + seg8 * guli_i, sr_today + seg8 * (guli_i + 1))
        midday = sr_today + day_len / 2
        abhijit_span = (midday - day_len / 30.0, midday + day_len / 30.0)

        hora_bounds: List[datetime.datetime] = []
        for h in range(25):
            ht = prev_sr + datetime.timedelta(hours=h)
            if day_start < ht < sr_today:
                hora_bounds.append(ht)
        for h in range(25):
            ht = sr_today + datetime.timedelta(hours=h)
            if sr_today <= ht < day_end:
                hora_bounds.append(ht)

        half_tithi_tx = _scan_transitions(
            day_start, day_end, 120,
            lambda dt: int(norm_deg(_get_astro(dt)[1] - _get_astro(dt)[0]) // 6.0) + 1,
        )
        lagna_tx = _scan_transitions(
            day_start, day_end, 45,
            lambda dt: get_rashi_id(lagna_lon_at(dt, lat_deg, lon_deg, tz_offset_hours, ayanamsa_system)),
        )

        day_varjyam: List[Tuple[datetime.datetime, datetime.datetime]] = []
        day_amrita: List[Tuple[datetime.datetime, datetime.datetime]] = []
        for sp in nak_spans:
            vs, ve = sp["varjyam_start"], sp["varjyam_end"]
            if ve > day_start and vs < day_end:
                day_varjyam.append((max(vs, day_start), min(ve, day_end)))
            as_, ae = sp["amrita_start"], sp["amrita_end"]
            if ae > day_start and as_ < day_end:
                day_amrita.append((max(as_, day_start), min(ae, day_end)))

        pak_pool = pakshi_by_date[prev_date] + pakshi_by_date[cur_date]

        bp_set = {
            day_start, day_end,
            rahu_span[0], rahu_span[1],
            yamaganda_span[0], yamaganda_span[1],
            gulika_span[0], gulika_span[1],
            abhijit_span[0], abhijit_span[1],
            sr_today, ss_today,
        }
        for ht in hora_bounds:
            bp_set.add(ht)
        for sp in pak_pool:
            if day_start < sp["start"] < day_end:
                bp_set.add(sp["start"])
            if day_start < sp["end"] < day_end:
                bp_set.add(sp["end"])
        for tx_dt, _, _ in half_tithi_tx:
            bp_set.add(tx_dt)
        for tx_dt, _, _ in lagna_tx:
            bp_set.add(tx_dt)
        for v0, v1 in day_varjyam:
            bp_set.add(v0)
            bp_set.add(v1)
        for a0, a1 in day_amrita:
            bp_set.add(a0)
            bp_set.add(a1)

        minute_marks = sorted({
            min(1440, max(0, int(round((bp - day_start).total_seconds() / 60.0))))
            for bp in bp_set
        })
        if minute_marks[0] != 0:
            minute_marks.insert(0, 0)
        if minute_marks[-1] != 1440:
            minute_marks.append(1440)

        atomic_slots: List[Dict[str, Any]] = []
        for m_i in range(len(minute_marks) - 1):
            m0 = minute_marks[m_i]
            m1 = minute_marks[m_i + 1]
            if m1 - m0 < 1:
                continue
            mid = day_start + datetime.timedelta(minutes=(m0 + m1) / 2.0)

            sun_lon, moon_lon, lagna_lon = _get_astro(mid)
            nak_id, _ = get_nakshatra_pada(moon_lon)
            moon_rashi_id = get_rashi_id(moon_lon)
            tatkal_lagna_id = get_rashi_id(lagna_lon)

            diff = norm_deg(moon_lon - sun_lon)
            tithi_idx0 = int(diff // 12.0) % 30
            tithi_num = (tithi_idx0 + 1) if tithi_idx0 < 15 else (15 if tithi_idx0 == 29 else (tithi_idx0 - 14))
            half_tithi = int(diff // 6.0) + 1
            karana_name = FIXED_KARANAS[half_tithi] if half_tithi in FIXED_KARANAS else MOVABLE_KARANAS[(half_tithi - 2) % 7]

            if mid >= sr_today:
                vara_wd = civil_wd_idx
                peyas = ((mid - sr_today).total_seconds() / 3600.0) * 2.5
            else:
                vara_wd = prev_wd_idx
                peyas = ((mid - prev_sr).total_seconds() / 3600.0) * 2.5

            hora_idx = (WEEKDAY_TO_CHALDEAN_IDX[vara_wd] + int(peyas / 2.5)) % 7
            hora_key = LORD_NAME_TO_KEY[CHALDEAN_ORDER[hora_idx].lower()]

            # 1. Pancha Pakshi score
            pak_item = _lookup_pakshi(pak_pool, mid)
            main_act = pak_item["main_act"]
            sub_act = pak_item["sub_act"]
            rel = pak_item["relationship"]
            if rel == "Self":
                rel_pts = 5 if sub_act in ("Rule", "Eat", "Walk") else -2
            elif rel == "Friend":
                rel_pts = 4 if sub_act in ("Rule", "Eat", "Walk") else 1
            else:
                rel_pts = -5 if sub_act not in ("Die", "Sleep") else -8
            pakshi_pts = PAKSHI_MAIN_PTS[main_act] + PAKSHI_SUB_PTS[sub_act] + rel_pts

            # 2. Tarabala & Chandrabala
            tara_num = ((nak_id - profile["janma_nak_id"]) % 27) % 9 + 1
            tara_pts = TARABALA_PTS[tara_num]
            chandra_house = ((moon_rashi_id - profile["janma_rashi_id"]) % 12) + 1
            chandra_pts = CHANDRABALA_PTS[chandra_house]

            # 3. Hora & Tatkal Lagna
            hora_pts = hora_weights[hora_key]
            vara_lord = WEEKDAY_LORD_KEY[vara_wd]
            if hora_key in NATURAL_FRIENDS.get(vara_lord, set()):
                hora_pts += 2
            elif hora_key in NATURAL_ENEMIES.get(vara_lord, set()):
                hora_pts -= 2

            tl_house = ((tatkal_lagna_id - profile["janma_lagna_id"]) % 12) + 1
            tl_lord_key = RASHI_LORDS[tatkal_lagna_id]
            tl_bonus = round(hora_weights[tl_lord_key] * 0.35)
            lagna_pts = BHAVA_FROM_LAGNA_PTS[tl_house] + tl_bonus

            # 4. Sri Lankan Litha Doshas & Yogas
            is_rahu = rahu_span[0] <= mid <= rahu_span[1]
            is_yama = yamaganda_span[0] <= mid <= yamaganda_span[1]
            is_gulika = gulika_span[0] <= mid <= gulika_span[1]
            is_abhijit = abhijit_span[0] <= mid <= abhijit_span[1]
            is_varjyam = any(v0 <= mid <= v1 for v0, v1 in day_varjyam)
            is_amrita_kalam = any(a0 <= mid <= a1 for a0, a1 in day_amrita)
            is_vishti = karana_name in ("Vishti", "Wishti")

            amritadi = AMRITADI_YOGA_MATRIX[nak_id - 1][vara_wd]
            is_dagdha = tithi_num in DAGDHA_TITHI_BY_WD[vara_wd]
            is_siddha_tithi = tithi_num in SIDDHA_TITHI_BY_WD.get(vara_wd, set())

            litha_pts = 0
            hard_cap = 100

            if is_rahu:
                litha_pts -= 28
                hard_cap = min(hard_cap, 38)
            if is_varjyam:
                litha_pts -= 24
                hard_cap = min(hard_cap, 40)
            if is_vishti:
                is_bhuloka = moon_rashi_id in BHULOKA_BHADRA_RASHIS
                litha_pts -= 22 if is_bhuloka else 15
                hard_cap = min(hard_cap, 41 if is_bhuloka else 48)
            if is_yama:
                litha_pts -= 15
                hard_cap = min(hard_cap, 52)
            if is_gulika:
                litha_pts -= 12
                hard_cap = min(hard_cap, 55)

            if amritadi in ("Marana", "Prabal"):
                litha_pts -= 18 if amritadi == "Marana" else 20
                hard_cap = min(hard_cap, 49)
            elif amritadi == "Amrita":
                litha_pts += 14
            elif amritadi == "Siddha":
                litha_pts += 10

            if is_dagdha:
                litha_pts -= 14
                hard_cap = min(hard_cap, 54)
            elif is_siddha_tithi and amritadi != "Marana":
                litha_pts += 6 if amritadi == "Siddha" else 10

            if is_amrita_kalam and not is_varjyam and not is_rahu:
                litha_pts += 18
            if is_abhijit and not is_rahu and not is_varjyam:
                litha_pts += 5 if civil_wd_idx == 3 else 14

            if tithi_num in (4, 9, 14) or tithi_idx0 == 29:
                litha_pts -= 6
            elif tithi_num in (5, 7, 10, 11, 15) and tithi_idx0 != 29:
                litha_pts += 4

            is_vadha = tara_num == 7
            is_chandrash = chandra_house == 8
            if is_vadha or is_chandrash:
                hard_cap = min(hard_cap, 72)

            has_dosha = (
                is_rahu or is_varjyam or is_vishti or is_yama or is_gulika
                or is_dagdha or (amritadi in ("Marana", "Prabal"))
            )

            delta = pakshi_pts + tara_pts + chandra_pts + hora_pts + lagna_pts + litha_pts
            raw_score = 50 + (delta * 0.72 if delta > 0 else delta * 0.85)
            score = max(3, min(hard_cap, min(99, round(raw_score))))
            grade = _grade_from_score_6(score, has_dosha=has_dosha, is_vadha=is_vadha, is_chandrashtama=is_chandrash)

            atomic_slots.append({
                "m0": m0,
                "m1": m1,
                "score": score,
                "grade": grade,
                "hard_flags": (is_rahu, is_varjyam, is_vishti, is_abhijit, is_amrita_kalam),
            })

        def _build_block(subs: List[Dict[str, Any]], forced_grade: str) -> Dict[str, Any]:
            m0 = subs[0]["m0"]
            m1 = subs[-1]["m1"]
            tot_m = max(1, m1 - m0)
            w_score = round(sum(s["score"] * (s["m1"] - s["m0"]) for s in subs) / tot_m)
            return {
                "m0": m0,
                "m1": m1,
                "duration_min": tot_m,
                "score": w_score,
                "grade": forced_grade,
                "hard_flags": subs[len(subs) // 2]["hard_flags"],
                "sub_slots": subs,
            }

        # Step 1: Group identical grades
        merged: List[Dict[str, Any]] = []
        for s in atomic_slots:
            if merged and merged[-1]["grade"] == s["grade"] and merged[-1]["hard_flags"] == s["hard_flags"]:
                merged[-1] = _build_block(merged[-1]["sub_slots"] + [s], s["grade"])
            else:
                merged.append(_build_block([s], s["grade"]))

        # Step 2: Smooth midnight boundary slivers (< 8m) and brief inner slivers (< 11m)
        if len(merged) >= 2 and merged[0]["duration_min"] < 8 and merged[0]["hard_flags"] == merged[1]["hard_flags"]:
            merged[:2] = [_build_block(merged[0]["sub_slots"] + merged[1]["sub_slots"], merged[1]["grade"])]
        if len(merged) >= 2 and merged[-1]["duration_min"] < 8 and merged[-1]["hard_flags"] == merged[-2]["hard_flags"]:
            merged[-2:] = [_build_block(merged[-2]["sub_slots"] + merged[-1]["sub_slots"], merged[-2]["grade"])]

        changed = True
        while changed and len(merged) >= 3:
            changed = False
            i = 1
            while i < len(merged) - 1:
                cur, left, right = merged[i], merged[i - 1], merged[i + 1]
                cur_d = cur["duration_min"]
                same_fl = cur["hard_flags"] == left["hard_flags"]
                same_fr = cur["hard_flags"] == right["hard_flags"]
                same_pol = (cur["score"] < 50) == (left["score"] < 50) == (right["score"] < 50)
                if cur_d < 15 and same_fl and same_fr and left["grade"] == right["grade"]:
                    merged[i - 1 : i + 2] = [_build_block(left["sub_slots"] + cur["sub_slots"] + right["sub_slots"], left["grade"])]
                    changed = True
                    break
                if cur_d < 11 and same_pol and (same_fl or same_fr):
                    merge_left = same_fl and (not same_fr or abs(cur["score"] - left["score"]) <= abs(cur["score"] - right["score"]))
                    if merge_left:
                        merged[i - 1 : i + 1] = [_build_block(left["sub_slots"] + cur["sub_slots"], left["grade"])]
                    else:
                        merged[i : i + 2] = [_build_block(cur["sub_slots"] + right["sub_slots"], right["grade"])]
                    changed = True
                    break
                i += 1

        # Step 3: Coalesce ALL adjacent rows sharing the EXACT same displayed grade
        # so the customer never sees two consecutive rows with identical "තත්වය".
        coalesced: List[Dict[str, Any]] = []
        for blk in merged:
            if coalesced and coalesced[-1]["grade"] == blk["grade"]:
                coalesced[-1] = _build_block(coalesced[-1]["sub_slots"] + blk["sub_slots"], blk["grade"])
            else:
                coalesced.append(blk)

        # Step 4: Clip cleanly to requested [from_min, to_min] window
        day_rows: List[Dict[str, Any]] = []
        date_str = cur_date.isoformat()
        for blk in coalesced:
            c0 = max(blk["m0"], from_min)
            c1 = min(blk["m1"], to_min)
            if c1 <= c0:
                continue
            g_meta = GRADE_INFO_6[blk["grade"]]
            row = {
                "date": date_str,
                "weekday_si": wd_meta["si"],
                "weekday_en": wd_meta["en"],
                "m0": c0,
                "m1": c1,
                "from_24": _fmt_24(c0),
                "to_24": _fmt_24(c1),
                "from_12_si": _fmt_12_si(c0),
                "to_12_si": _fmt_12_si(c1),
                "from_12_en": _fmt_12_en(c0),
                "to_12_en": _fmt_12_en(c1),
                "duration_min": c1 - c0,
                "grade": blk["grade"],
                "level": g_meta["level"],
                "grade_si": g_meta["si"],
                "grade_en": g_meta["en"],
                "css": g_meta["css"],
                "is_auspicious": g_meta["auspicious"],
                "score": blk["score"],
            }
            day_rows.append(row)
            all_rows.append(row)

        day_summaries.append({
            "date": date_str,
            "weekday_si": wd_meta["si"],
            "weekday_en": wd_meta["en"],
            "rows": day_rows,
        })

    public_profile = {k: v for k, v in profile.items() if k != "hora_weights"}

    return {
        "profile": public_profile,
        "location": {
            "city": city_name,
            "city_si": city_si,
            "lat": round(lat_deg, 6),
            "lon": round(lon_deg, 6),
            "tz_offset_hours": tz_offset_hours,
        },
        "range": {
            "start_date": start_date.isoformat(),
            "end_date": (start_date + datetime.timedelta(days=days - 1)).isoformat(),
            "days_count": days,
            "from_min": from_min,
            "to_min": to_min,
            "from_time": _fmt_24(from_min),
            "to_time": _fmt_24(to_min),
        },
        "grades_legend": [
            {"grade": key, **meta}
            for key, meta in GRADE_INFO_6.items()
        ],
        "days": day_summaries,
        "rows": all_rows,
    }
