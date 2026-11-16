(() => {
  "use strict";

  const STORAGE_KEY = "daily_fortune_profiles_v1";
  const PREFS_KEY = "daily_fortune_prefs_v1";
  const LAST_RESULT_KEY = "daily_fortune_last_result_v1";
  const CUST_TOKEN_KEY = "daily_fortune_cust_token";
  const NOTIFIED_BUCKET_KEY = "df_notified_bucket";

  const state = {
    lang: "si",
    timeFmt: "12h",
    filter: "all",
    meta: null,
    targetSynced: true,
    profiles: [],
    activeProfileId: null,
    lastResult: null,
    nowTimer: null,
    deferredPrompt: null,
    customer: null,
    settings: null,
  };

  const $ = (id) => document.getElementById(id);
  const t = (key) => (window.DF_I18N[state.lang] && window.DF_I18N[state.lang][key]) || key;

  function todayDate() {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }

  function toISO(dt) {
    const y = dt.getFullYear();
    const m = String(dt.getMonth() + 1).padStart(2, "0");
    const d = String(dt.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }

  function addDays(dt, n) {
    const copy = new Date(dt.getTime());
    copy.setDate(copy.getDate() + n);
    return copy;
  }

  function loadStorage() {
    try {
      const prefs = JSON.parse(localStorage.getItem(PREFS_KEY) || "{}");
      if (prefs.lang === "en" || prefs.lang === "si") state.lang = prefs.lang;
      if (prefs.timeFmt === "24h" || prefs.timeFmt === "12h") state.timeFmt = prefs.timeFmt;
    } catch (_) {}
    try {
      const arr = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      if (Array.isArray(arr)) state.profiles = arr;
    } catch (_) {}
  }

  function savePrefs() {
    try {
      localStorage.setItem(PREFS_KEY, JSON.stringify({ lang: state.lang, timeFmt: state.timeFmt }));
    } catch (_) {}
  }

  const MONTHS_I18N = {
    si: [
      { val: "01", name: "01 - ජනවාරි", short: "ජනවාරි" },
      { val: "02", name: "02 - පෙබරවාරි", short: "පෙබරවාරි" },
      { val: "03", name: "03 - මාර්තු", short: "මාර්තු" },
      { val: "04", name: "04 - අප්‍රේල්", short: "අප්‍රේල්" },
      { val: "05", name: "05 - මැයි", short: "මැයි" },
      { val: "06", name: "06 - ජූනි", short: "ජූනි" },
      { val: "07", name: "07 - ජූලි", short: "ජූලි" },
      { val: "08", name: "08 - අගෝස්තු", short: "අගෝස්තු" },
      { val: "09", name: "09 - සැප්තැම්බර්", short: "සැප්තැම්බර්" },
      { val: "10", name: "10 - ඔක්තෝබර්", short: "ඔක්තෝබර්" },
      { val: "11", name: "11 - නොවැම්බර්", short: "නොවැම්බර්" },
      { val: "12", name: "12 - දෙසැම්බර්", short: "දෙසැම්බර්" },
    ],
    en: [
      { val: "01", name: "01 - January", short: "January" },
      { val: "02", name: "02 - February", short: "February" },
      { val: "03", name: "03 - March", short: "March" },
      { val: "04", name: "04 - April", short: "April" },
      { val: "05", name: "05 - May", short: "May" },
      { val: "06", name: "06 - June", short: "June" },
      { val: "07", name: "07 - July", short: "July" },
      { val: "08", name: "08 - August", short: "August" },
      { val: "09", name: "09 - September", short: "September" },
      { val: "10", name: "10 - October", short: "October" },
      { val: "11", name: "11 - November", short: "November" },
      { val: "12", name: "12 - December", short: "December" },
    ],
  };

  const WEEKDAYS_I18N = {
    si: ["ඉරිදා", "සඳුදා", "අඟහරුවාදා", "බදාදා", "බ්‍රහස්පතින්දා", "සිකුරාදා", "සෙනසුරාදා"],
    en: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
  };

  function getDaysInMonth(year, month) {
    const y = parseInt(year, 10);
    const m = parseInt(month, 10);
    if (!y || !m || isNaN(y) || isNaN(m)) return 31;
    return new Date(y, m, 0).getDate();
  }

  function populateBirthDateDropdowns() {
    const yearSelect = $("bYear");
    const monthSelect = $("bMonth");
    const daySelect = $("bDay");
    if (!yearSelect || !monthSelect || !daySelect) return;

    // Populate Year dropdown (2026 down to 1920)
    const curYear = new Date().getFullYear();
    const curYearVal = yearSelect.value;
    const yearOpts = [`<option value="">${t("selectYear")}</option>`];
    for (let y = curYear; y >= 1920; y--) {
      yearOpts.push(`<option value="${y}">${y}</option>`);
    }
    yearSelect.innerHTML = yearOpts.join("");
    if (curYearVal) yearSelect.value = curYearVal;

    // Populate Month dropdown with current language
    const curMonthVal = monthSelect.value;
    const months = MONTHS_I18N[state.lang] || MONTHS_I18N.si;
    const monthOpts = [`<option value="">${t("selectMonth")}</option>`];
    months.forEach((m) => {
      monthOpts.push(`<option value="${m.val}">${m.name}</option>`);
    });
    monthSelect.innerHTML = monthOpts.join("");
    if (curMonthVal) monthSelect.value = curMonthVal;

    updateDayDropdownOptions();
  }

  function updateDayDropdownOptions() {
    const daySelect = $("bDay");
    if (!daySelect) return;
    const curDay = daySelect.value;
    const y = $("bYear") ? $("bYear").value : "";
    const m = $("bMonth") ? $("bMonth").value : "";
    const maxDays = getDaysInMonth(y, m);

    const dayOpts = [`<option value="">${t("selectDay")}</option>`];
    for (let d = 1; d <= maxDays; d++) {
      const s = String(d).padStart(2, "0");
      dayOpts.push(`<option value="${s}">${s}</option>`);
    }
    daySelect.innerHTML = dayOpts.join("");
    if (curDay && parseInt(curDay, 10) <= maxDays) {
      daySelect.value = curDay;
    }
  }

  function syncBirthDateFromParts() {
    const yearSelect = $("bYear");
    const monthSelect = $("bMonth");
    const daySelect = $("bDay");
    const hiddenDate = $("fBirthDate");
    const directInput = $("bDateDirectInput");
    const preview = $("bDatePreview");
    const previewTxt = $("bDatePreviewTxt");
    if (!yearSelect || !monthSelect || !daySelect || !hiddenDate) return;

    updateDayDropdownOptions();

    const y = parseInt(yearSelect.value, 10);
    const m = monthSelect.value;
    const d = daySelect.value;

    const container = yearSelect.closest(".bdate-container");
    if (container) container.classList.remove("has-bdate-error");

    if (y && y >= 1900 && y <= 2030 && m && d) {
      const maxD = getDaysInMonth(y, m);
      const dNum = parseInt(d, 10);
      if (dNum >= 1 && dNum <= maxD) {
        const iso = `${String(y).padStart(4, "0")}-${m}-${d}`;
        hiddenDate.value = iso;
        if (directInput) directInput.value = iso;

        const dt = new Date(y, parseInt(m, 10) - 1, dNum);
        const weekdayIdx = !isNaN(dt.getTime()) ? dt.getDay() : null;
        const weekday = weekdayIdx !== null ? (WEEKDAYS_I18N[state.lang] || WEEKDAYS_I18N.si)[weekdayIdx] : "";
        const months = MONTHS_I18N[state.lang] || MONTHS_I18N.si;
        const monthObj = months.find((x) => x.val === m);
        const mName = monthObj ? monthObj.short : m;

        if (state.lang === "si") {
          previewTxt.textContent = `✓ ${y} ${mName} ${d} — ${weekday} (${iso})`;
        } else {
          previewTxt.textContent = `✓ ${mName} ${d}, ${y} — ${weekday} (${iso})`;
        }
        preview.classList.add("is-valid");
        return;
      }
    }

    hiddenDate.value = "";
    previewTxt.textContent = t("bDatePrompt");
    preview.classList.remove("is-valid");
  }

  function setBirthDatePartsFromIso(isoDate) {
    const yearSelect = $("bYear");
    const monthSelect = $("bMonth");
    const daySelect = $("bDay");
    const hiddenDate = $("fBirthDate");
    const directInput = $("bDateDirectInput");

    if (!isoDate || typeof isoDate !== "string" || !isoDate.includes("-")) {
      if (yearSelect) yearSelect.value = "";
      if (monthSelect) monthSelect.value = "";
      if (daySelect) daySelect.value = "";
      if (hiddenDate) hiddenDate.value = "";
      if (directInput) directInput.value = "";
      syncBirthDateFromParts();
      return;
    }
    const parts = isoDate.split("-");
    const y = parts[0] || "";
    const m = parts[1] || "";
    const d = parts[2] || "";
    if (yearSelect) yearSelect.value = y;
    if (monthSelect) monthSelect.value = m;
    updateDayDropdownOptions();
    if (daySelect) daySelect.value = d;
    if (hiddenDate) hiddenDate.value = isoDate;
    if (directInput) directInput.value = isoDate;
    syncBirthDateFromParts();
  }

  function initBirthDatePicker() {
    populateBirthDateDropdowns();

    $("bYear").addEventListener("change", syncBirthDateFromParts);
    $("bMonth").addEventListener("change", syncBirthDateFromParts);
    $("bDay").addEventListener("change", syncBirthDateFromParts);

    // Direct text input sync
    const directInput = $("bDateDirectInput");
    if (directInput) {
      directInput.addEventListener("input", () => {
        const val = directInput.value.trim();
        if (/^\d{4}-\d{2}-\d{2}$/.test(val)) {
          setBirthDatePartsFromIso(val);
        }
      });
      directInput.addEventListener("change", () => {
        const val = directInput.value.trim();
        if (/^\d{4}-\d{2}-\d{2}$/.test(val)) {
          setBirthDatePartsFromIso(val);
        }
      });
    }

    // Toggle mode: 3 Dropdowns vs Direct Input
    const btnToggleMode = $("btnToggleDateMode");
    if (btnToggleMode) {
      btnToggleMode.addEventListener("click", () => {
        const isDirect = $("bDateDirectWrap").classList.contains("hidden");
        if (isDirect) {
          $("bDateTriplet").classList.add("hidden");
          $("bDateDirectWrap").classList.remove("hidden");
          btnToggleMode.textContent = "☰ Dropdown";
          btnToggleMode.classList.add("active");
          if (directInput) {
            directInput.value = $("fBirthDate").value || "";
            directInput.focus();
          }
        } else {
          $("bDateDirectWrap").classList.add("hidden");
          $("bDateTriplet").classList.remove("hidden");
          btnToggleMode.textContent = "⌨️ Type";
          btnToggleMode.classList.remove("active");
          if (directInput && directInput.value) {
            setBirthDatePartsFromIso(directInput.value);
          }
        }
      });
    }

    // Native date picker toggle
    $("btnCalToggle").addEventListener("click", () => {
      const nativeInput = $("fBirthDate");
      if (nativeInput.showPicker) {
        try {
          nativeInput.showPicker();
          return;
        } catch (_) {}
      }
      const cur = nativeInput.value || "1990-01-01";
      const userDate = window.prompt(state.lang === "si" ? "උපන් දිනය ඇතුළත් කරන්න (YYYY-MM-DD):" : "Enter Birth Date (YYYY-MM-DD):", cur);
      if (userDate && /^\d{4}-\d{2}-\d{2}$/.test(userDate.trim())) {
        setBirthDatePartsFromIso(userDate.trim());
      }
    });

    $("fBirthDate").addEventListener("change", () => {
      if ($("fBirthDate").value) {
        setBirthDatePartsFromIso($("fBirthDate").value);
      }
    });
  }

  function saveProfilesStorage() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.profiles));
    } catch (_) {}
  }

  function applyTranslations() {
    document.documentElement.lang = state.lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const k = el.getAttribute("data-i18n");
      if (k) el.textContent = t(k);
    });
    document.querySelectorAll("[data-i18n-opt]").forEach((el) => {
      const k = el.getAttribute("data-i18n-opt");
      if (k) el.textContent = t(k);
    });
    $("fName").placeholder = state.lang === "si" ? "උදා: රුවන් පෙරේරා" : "e.g. Ruwan Perera";
    if ($("bYear")) $("bYear").placeholder = state.lang === "si" ? "වර්ෂය" : "Year";
    document.querySelectorAll("[data-lang]").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-lang") === state.lang);
    });
    document.querySelectorAll("[data-timefmt]").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-timefmt") === state.timeFmt);
    });
    if (state.meta) {
      populateDropdownLabelsOnly();
    }
    populateBirthDateDropdowns();
    syncBirthDateFromParts();
    if (state.lastResult) {
      renderResult(state.lastResult);
    }
    updateInstallUI();
  }

  function populateDistrictCity(distSel, citySel, chosenDistrict, chosenCityId) {
    if (!state.meta) return;
    const prevDist = chosenDistrict || distSel.value || "Colombo";
    const prevCity = chosenCityId || citySel.value || "1";

    distSel.innerHTML = state.meta.districts
      .map((d) => `<option value="${d.id}">${state.lang === "si" ? `${d.si} (${d.name})` : d.name}</option>`)
      .join("");
    distSel.value = state.meta.districts.some((d) => d.id === prevDist) ? prevDist : "Colombo";

    const filtered = state.meta.cities.filter((c) => c.district === distSel.value);
    citySel.innerHTML = filtered
      .map((c) => `<option value="${c.id}">${state.lang === "si" ? `${c.sinhala} (${c.name})` : c.name}</option>`)
      .join("");
    if (filtered.some((c) => String(c.id) === String(prevCity))) {
      citySel.value = String(prevCity);
    } else if (filtered.length > 0) {
      citySel.value = String(filtered[0].id);
    }
  }

  function populateChartSelects(keepValues = true) {
    if (!state.meta) return;
    const curNak = keepValues ? $("fNak").value || "auto" : "auto";
    const curLag = keepValues ? $("fLagna").value || "auto" : "auto";
    const curNav = keepValues ? $("fNavamsa").value || "auto" : "auto";

    const autoOpt = `<option value="auto">${t("autoDetect")}</option>`;
    $("fNak").innerHTML =
      autoOpt +
      state.meta.nakshatras
        .map((n) => `<option value="${n.id}">${n.id}. ${state.lang === "si" ? `${n.si} (${n.short_en})` : n.en}</option>`)
        .join("");

    const rashiOpts =
      autoOpt +
      state.meta.rashis
        .map((r) => `<option value="${r.id}">${state.lang === "si" ? `${r.si} (${r.short_en})` : r.en}</option>`)
        .join("");
    $("fLagna").innerHTML = rashiOpts;
    $("fNavamsa").innerHTML = rashiOpts;

    $("fNak").value = curNak;
    $("fLagna").value = curLag;
    $("fNavamsa").value = curNav;
  }

  function populateDropdownLabelsOnly() {
    populateDistrictCity($("fBirthDistrict"), $("fBirthCity"), $("fBirthDistrict").value, $("fBirthCity").value);
    populateDistrictCity($("fTargetDistrict"), $("fTargetCity"), $("fTargetDistrict").value, $("fTargetCity").value);
    populateChartSelects(true);
  }

  function setDatePreset(preset) {
    const tod = todayDate();
    let s = tod;
    let e = tod;
    if (preset === "tomorrow") {
      s = addDays(tod, 1);
      e = s;
    } else if (preset === "week") {
      e = addDays(tod, 6);
    } else if (preset === "month") {
      e = addDays(tod, 29);
    }
    $("fStartDate").value = toISO(s);
    $("fEndDate").value = toISO(e);
    document.querySelectorAll("#dayPresets .chip-btn").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-preset") === preset);
    });
  }

  function syncPresetHighlightFromDates() {
    const tod = todayDate();
    const s = $("fStartDate").value;
    const e = $("fEndDate").value;
    const todIso = toISO(tod);
    const tomIso = toISO(addDays(tod, 1));
    let matched = null;
    if (s === todIso && e === todIso) matched = "today";
    else if (s === tomIso && e === tomIso) matched = "tomorrow";
    else if (s === todIso && e === toISO(addDays(tod, 6))) matched = "week";
    else if (s === todIso && e === toISO(addDays(tod, 29))) matched = "month";
    document.querySelectorAll("#dayPresets .chip-btn").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-preset") === matched);
    });
  }

  function renderSavedProfilesBar() {
    const bar = $("savedBar");
    const box = $("savedChips");
    if (!state.profiles.length) {
      bar.classList.add("hidden");
      return;
    }
    bar.classList.remove("hidden");
    box.innerHTML = state.profiles
      .map((p) => {
        const active = p.id === state.activeProfileId ? "active" : "";
        return `<div class="saved-chip ${active}" data-pid="${p.id}">
          <span class="chip-name">${escapeHtml(p.name)}</span>
          <span class="del-x" data-del="${p.id}" title="Delete">&times;</span>
        </div>`;
      })
      .join("");
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    })[c]);
  }

  function applyProfileToForm(p) {
    state.activeProfileId = p.id;
    $("fName").value = p.name || "";
    setBirthDatePartsFromIso(p.birth_date || "1990-01-01");
    $("fBirthTime").value = p.birth_time || "";
    populateDistrictCity($("fBirthDistrict"), $("fBirthCity"), p.birth_district || "Colombo", p.birth_city_id || "1");
    populateDistrictCity($("fTargetDistrict"), $("fTargetCity"), p.target_district || p.birth_district || "Colombo", p.target_city_id || p.birth_city_id || "1");
    state.targetSynced = !p.target_city_id || String(p.target_city_id) === String(p.birth_city_id);
    $("fNak").value = p.nakshatra_id || "auto";
    $("fPada").value = p.pada || "auto";
    $("fLagna").value = p.lagna_id || "auto";
    $("fNavamsa").value = p.navamsa_id || "auto";
    renderSavedProfilesBar();
  }

  function clearFormForNewPerson() {
    state.activeProfileId = null;
    $("fName").value = "";
    setBirthDatePartsFromIso("");
    $("fBirthTime").value = "06:00";
    $("fNak").value = "auto";
    $("fPada").value = "auto";
    $("fLagna").value = "auto";
    $("fNavamsa").value = "auto";
    populateDistrictCity($("fBirthDistrict"), $("fBirthCity"), "Colombo", "1");
    populateDistrictCity($("fTargetDistrict"), $("fTargetCity"), "Colombo", "1");
    state.targetSynced = true;
    renderSavedProfilesBar();
    $("formCard").classList.remove("hidden");
    $("fName").focus();
  }

  function collectFormPayload() {
    const name = $("fName").value.trim();
    syncBirthDateFromParts();
    const birthDate = $("fBirthDate").value;
    if (!name || !birthDate) {
      const container = $("bYear").closest(".bdate-container");
      if (!birthDate && container) {
        container.classList.add("has-bdate-error");
        if (!$("bYear").value) $("bYear").focus();
        else if (!$("bMonth").value) $("bMonth").focus();
        else if (!$("bDay").value) $("bDay").focus();
      }
      throw new Error(t("errNameDate"));
    }

    const fromTimeVal = $("fFromTime").value || "00:00";
    let toTimeVal = $("fToTime").value || "24:00";
    if (toTimeVal === "23:59") toTimeVal = "24:00";

    return {
      name,
      birth_date: birthDate,
      birth_time: $("fBirthTime").value || "",
      birth_city_id: Number($("fBirthCity").value || 1),
      target_city_id: Number($("fTargetCity").value || $("fBirthCity").value || 1),
      nakshatra_id: $("fNak").value === "auto" ? null : Number($("fNak").value),
      pada: $("fPada").value === "auto" ? null : Number($("fPada").value),
      lagna_id: $("fLagna").value === "auto" ? null : Number($("fLagna").value),
      navamsa_id: $("fNavamsa").value === "auto" ? null : Number($("fNavamsa").value),
      start_date: $("fStartDate").value,
      end_date: $("fEndDate").value,
      from_time: fromTimeVal,
      to_time: toTimeVal,
      tz_offset_hours: 5.5,
      ayanamsa_system: "arc_ray",
    };
  }

  function upsertSavedProfile(payload) {
    if (!$("fSaveProfile").checked) return;
    const entry = {
      id: state.activeProfileId || `p_${Date.now()}`,
      name: payload.name,
      birth_date: payload.birth_date,
      birth_time: payload.birth_time,
      birth_district: $("fBirthDistrict").value,
      birth_city_id: String(payload.birth_city_id),
      target_district: $("fTargetDistrict").value,
      target_city_id: String(payload.target_city_id),
      nakshatra_id: $("fNak").value,
      pada: $("fPada").value,
      lagna_id: $("fLagna").value,
      navamsa_id: $("fNavamsa").value,
    };
    const idx = state.profiles.findIndex(
      (p) => p.id === entry.id || (p.name.toLowerCase() === entry.name.toLowerCase() && p.birth_date === entry.birth_date)
    );
    if (idx >= 0) {
      entry.id = state.profiles[idx].id;
      state.profiles[idx] = entry;
    } else {
      state.profiles.unshift(entry);
      if (state.profiles.length > 12) state.profiles.pop();
    }
    state.activeProfileId = entry.id;
    saveProfilesStorage();
    renderSavedProfilesBar();
  }

  function formatTimeForUI(row, which) {
    if (state.timeFmt === "24h") return which === "from" ? row.from_24 : row.to_24;
    return state.lang === "si"
      ? (which === "from" ? row.from_12_si : row.to_12_si)
      : (which === "from" ? row.from_12_en : row.to_12_en);
  }

  function rowMatchesFilter(row) {
    if (state.filter === "good") return row.level >= 4;
    if (state.filter === "best") return row.level >= 5;
    if (state.filter === "bad") return row.level <= 2;
    return true;
  }

  function updateNowBanner() {
    const banner = $("nowBanner");
    if (!state.lastResult) {
      banner.classList.add("hidden");
      return;
    }
    const now = new Date();
    const todayIso = toISO(now);
    const nowMin = now.getHours() * 60 + now.getMinutes();

    const activeRow = state.lastResult.rows.find(
      (r) => r.date === todayIso && r.m0 <= nowMin && nowMin < r.m1
    );

    if (!activeRow) {
      banner.classList.add("hidden");
      document.querySelectorAll("#fortuneBody tr.is-now").forEach((tr) => tr.classList.remove("is-now"));
      return;
    }

    const minsLeft = Math.max(1, activeRow.m1 - nowMin);
    const curTimeStr = state.timeFmt === "24h"
      ? `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`
      : now.toLocaleTimeString(state.lang === "si" ? "en-US" : "en-US", { hour: "2-digit", minute: "2-digit" });
    const endStr = formatTimeForUI(activeRow, "to");
    const gTxt = state.lang === "si" ? activeRow.grade_si : activeRow.grade_en;

    $("nowCaption").textContent = `${t("nowCaption")} (${curTimeStr})`;
    $("nowSub").textContent =
      state.lang === "si"
        ? `${endStr} ${t("nowUntil")} (${t("nowMinsLeft")} ${minsLeft} ක්)`
        : `${t("nowUntil")} ${endStr} (${minsLeft} ${t("nowMinsLeft")})`;

    const badge = $("nowBadge");
    badge.textContent = gTxt;
    badge.className = `now-badge g-${activeRow.css}`;
    banner.classList.remove("hidden");
  }

  function renderResult(data) {
    state.lastResult = data;
    const p = data.profile;
    const isSi = state.lang === "si";

    $("outName").textContent = p.name;
    $("outBirthDate").textContent = p.birth_date;
    $("outLagna").textContent = isSi ? p.janma_lagna_si : p.janma_lagna_en;
    $("outNak").textContent = isSi
      ? `${p.janma_nak_si} (${t("padaLabel")} ${p.janma_pada})`
      : `${p.janma_nak_en} (${t("padaLabel")} ${p.janma_pada})`;
    $("outNavamsa").textContent = p.navamsa_si
      ? (isSi ? p.navamsa_si : p.navamsa_en)
      : "—";

    const locName = isSi ? data.location.city_si : data.location.city;
    const rangeTxt = data.range.start_date === data.range.end_date
      ? data.range.start_date
      : `${data.range.start_date} – ${data.range.end_date}`;
    $("outRangeMeta").textContent = `${locName}  •  ${rangeTxt}  (${data.range.from_time} – ${data.range.to_time})`;

    // Legend bar
    $("legendStrip").innerHTML = data.grades_legend
      .map((g) => `<span class="leg-pill g-${g.css}">${isSi ? g.si : g.en}</span>`)
      .join("");

    // Filter pills highlight
    document.querySelectorAll("#filterPills .filter-btn").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-filter") === state.filter);
    });

    // Build table rows
    const now = new Date();
    const todayIso = toISO(now);
    const nowMin = now.getHours() * 60 + now.getMinutes();

    const filtered = data.rows.filter(rowMatchesFilter);
    const tbody = $("fortuneBody");
    const empty = $("emptyState");

    if (!filtered.length) {
      tbody.innerHTML = "";
      empty.classList.remove("hidden");
    } else {
      empty.classList.add("hidden");
      const multiDay = data.range.days_count > 1;
      let prevDate = null;
      const htmlParts = [];

      for (const r of filtered) {
        const wd = isSi ? r.weekday_si : r.weekday_en;
        if (multiDay && r.date !== prevDate) {
          htmlParts.push(`<tr class="day-divider"><td colspan="4">📅 ${r.date} — ${wd}</td></tr>`);
          prevDate = r.date;
        }
        const isNow = r.date === todayIso && r.m0 <= nowMin && nowMin < r.m1;
        const fromStr = formatTimeForUI(r, "from");
        const toStr = formatTimeForUI(r, "to");
        const gText = isSi ? r.grade_si : r.grade_en;
        const star = r.grade === "SUPREME" ? "★ " : "";
        const nowTag = isNow ? `<span class="now-tag">${t("nowBadge")}</span>` : "";

        htmlParts.push(
          `<tr class="${isNow ? "is-now" : ""}">
            <td class="td-date">${r.date}<span class="td-wd">${wd}</span></td>
            <td class="td-time">${fromStr}${nowTag}</td>
            <td class="td-time">${toStr}</td>
            <td><span class="grade-badge g-${r.css}">${star}${gText}</span></td>
          </tr>`
        );
      }
      tbody.innerHTML = htmlParts.join("");
    }

    $("resultSection").classList.remove("hidden");
    $("collapseFormBtn").classList.remove("hidden");
    updateNowBanner();
  }

  function buildWhatsAppText() {
    if (!state.lastResult) return "";
    const d = state.lastResult;
    const p = d.profile;
    const isSi = state.lang === "si";
    const rows = d.rows.filter(rowMatchesFilter);

    const lines = [
      `✨ *Daily Fortune — ${p.name}*`,
      isSi
        ? `📅 උපන් දිනය: ${p.birth_date} | ⭐ නැකත: ${p.janma_nak_si} (පාදය ${p.janma_pada})`
        : `📅 Birth: ${p.birth_date} | ⭐ Nakshatra: ${p.janma_nak_en} (Pada ${p.janma_pada})`,
      isSi
        ? `♌ ලග්නය: ${p.janma_lagna_si}${p.navamsa_si ? ` | නවාංශකය: ${p.navamsa_si}` : ""}`
        : `♌ Lagna: ${p.janma_lagna_en}${p.navamsa_en ? ` | Navamsa: ${p.navamsa_en}` : ""}`,
      `📍 ${isSi ? d.location.city_si : d.location.city} (${d.range.start_date === d.range.end_date ? d.range.start_date : `${d.range.start_date} – ${d.range.end_date}`})`,
      "────────────────────────",
    ];

    const icon = {
      SUPREME: "🌟",
      VERY_GOOD: "💚",
      GOOD: "🟢",
      NEUTRAL: "🟡",
      BAD: "🟠",
      VERY_BAD: "🔴",
    };

    let lastDate = null;
    for (const r of rows) {
      if (d.range.days_count > 1 && r.date !== lastDate) {
        lines.push(`\n📅 *${r.date} (${isSi ? r.weekday_si : r.weekday_en})*`);
        lastDate = r.date;
      }
      const gTxt = isSi ? r.grade_si : r.grade_en;
      lines.push(`${icon[r.grade] || "•"} ${formatTimeForUI(r, "from")} – ${formatTimeForUI(r, "to")} : *${gTxt}*`);
    }
    return lines.join("\n");
  }

  function showToast(msg) {
    const toast = $("copyToast");
    toast.textContent = msg;
    toast.classList.remove("hidden");
    setTimeout(() => toast.classList.add("hidden"), 2800);
  }

  async function copyTextToClipboard(txt) {
    try {
      await navigator.clipboard.writeText(txt);
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = txt;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
  }

  function cacheLastResult(data) {
    try {
      localStorage.setItem(LAST_RESULT_KEY, JSON.stringify(data));
    } catch (_) {}
  }

  function loadCachedResult() {
    try {
      const parsed = JSON.parse(localStorage.getItem(LAST_RESULT_KEY) || "null");
      return parsed && Array.isArray(parsed.rows) ? parsed : null;
    } catch (_) {
      return null;
    }
  }

  function tryRestoreCachedSchedule() {
    const cached = loadCachedResult();
    if (!cached) return false;
    $("offlineBanner").classList.remove("hidden");
    renderResult(cached);
    return true;
  }

  function isStandaloneMode() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true
    );
  }

  function isLocalHost() {
    const h = window.location.hostname;
    return h === "127.0.0.1" || h === "localhost" || h === "[::1]";
  }

  function getAppShareUrl() {
    if (isLocalHost() && state.meta && state.meta.lan_url) {
      return state.meta.lan_url;
    }
    return window.location.origin;
  }

  function updateInstallUI() {
    const btn = $("installAppBtn");
    const nativeBox = $("nativeInstallBox");
    if (!btn) return;

    const standalone = isStandaloneMode();
    if (standalone && !isLocalHost()) {
      btn.classList.add("hidden");
    } else {
      btn.classList.remove("hidden");
    }

    if (state.deferredPrompt) {
      btn.textContent = t("btnInstallReady");
      btn.classList.add("is-ready");
      if (nativeBox) nativeBox.classList.remove("hidden");
    } else {
      btn.textContent = t("btnInstallShort");
      btn.classList.remove("is-ready");
      if (nativeBox) nativeBox.classList.add("hidden");
    }

    const urlEl = $("appShareUrl");
    const urlLbl = $("urlBoxLabel");
    if (urlEl) urlEl.textContent = getAppShareUrl();
    if (urlLbl) urlLbl.textContent = isLocalHost() ? t("lanLinkLabel") : t("appUrlLabel");
  }

  function openInstallModal() {
    updateInstallUI();
    $("installModal").classList.remove("hidden");
  }

  function closeInstallModal() {
    $("installModal").classList.add("hidden");
  }

  async function triggerNativeInstallPrompt() {
    if (!state.deferredPrompt) return;
    const promptEv = state.deferredPrompt;
    state.deferredPrompt = null;
    promptEv.prompt();
    try {
      const choice = await promptEv.userChoice;
      if (choice && choice.outcome === "accepted") {
        closeInstallModal();
        showToast(t("installSuccess"));
      }
    } catch (_) {}
    updateInstallUI();
  }

  function registerServiceWorker() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  }

  function canCustomerPrint() {
    return !!(state.customer && state.customer.can_print);
  }

  function notifyPrintLocked() {
    const price = (state.settings && state.settings.annual_price_lkr) || 1490;
    openPaymentModal(
      `🔒 මුද්‍රණ (Print / PDF Export) පහසුකම ගෙවීම් කළ පාරිභෝගිකයින් සඳහා පමණක් විවෘත වේ. ` +
      `සම්පූර්ණ වසරක් සඳහා ගිණුම සක්‍රිය කරගන්න (රු. ${price}/=).`
    );
  }

  async function handleSavePdf() {
    if (!state.lastResult) return;
    if (!canCustomerPrint()) {
      notifyPrintLocked();
      return;
    }

    const btn = $("savePdfBtn");
    btn.disabled = true;
    btn.textContent = t("pdfGenerating");
    try {
      const resp = await fetch("/api/fortune/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          schedule: state.lastResult,
          lang: state.lang,
          time_fmt: state.timeFmt,
          filter: state.filter,
          token: state.customer ? state.customer.token : null,
        }),
      });
      if (resp.status === 403) {
        notifyPrintLocked();
        return;
      }
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || "PDF generation failed");
      }
      const blob = await resp.blob();
      const disp = resp.headers.get("Content-Disposition") || "";
      const match = /filename="([^"]+)"/.exec(disp);
      const fname = match ? match[1] : `Daily_Fortune_${state.lastResult.range.start_date}.pdf`;

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      showToast(t("pdfSaved"));
    } catch (_) {
      if (canCustomerPrint()) {
        window.print();
      } else {
        notifyPrintLocked();
      }
    } finally {
      btn.disabled = false;
      btn.textContent = t("btnSavePdf");
    }
  }

  // --------------------------------------------------------------------------
  // Commercial Subscription & Monetization Controls
  // --------------------------------------------------------------------------
  async function checkSubscriptionStatus() {
    const tok = localStorage.getItem(CUST_TOKEN_KEY) || "";
    try {
      const url = tok ? `/api/me?token=${encodeURIComponent(tok)}` : "/api/me";
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        state.settings = data.settings || null;
        state.customer = data.customer || null;

        if (state.customer) {
          updateSubscriptionUI();
          checkTrialAlert();
        } else {
          openRegModal();
        }
      }
    } catch (e) {
      console.warn("Could not fetch subscription info:", e);
    }
  }

  function updateSubscriptionUI() {
    if (!state.customer) return;
    const c = state.customer;
    const banner = $("trialBanner");
    const msg = $("trialBannerMsg");
    const bannerPrice = $("bannerPrice");
    const userPill = $("userSubPill");
    const price = (state.settings && state.settings.annual_price_lkr) || 1490;

    if (bannerPrice) bannerPrice.textContent = price.toLocaleString();
    if ($("modalPayPrice")) $("modalPayPrice").textContent = price.toLocaleString();

    if (state.settings) {
      if ($("payBankName")) $("payBankName").textContent = state.settings.bank_name || "Commercial Bank of Ceylon";
      if ($("payBankAcc")) $("payBankAcc").textContent = state.settings.account_number || "8015238548";
      if ($("payAccName")) $("payAccName").textContent = state.settings.account_name || "G.C.R. Gamage";
    }

    if (c.status === "active") {
      banner.className = "trial-banner banner-active";
      banner.classList.remove("hidden");
      const daysLeft = Math.max(1, Math.round(c.hours_left / 24));
      msg.textContent = `🌟 වාර්ෂික දායකත්වය සක්‍රියයි (ඉතිරි දින: ${daysLeft})`;
      userPill.textContent = `🌟 Active (${daysLeft}d)`;
      userPill.classList.remove("hidden");
    } else if (c.status === "trial") {
      banner.className = "trial-banner";
      banner.classList.remove("hidden");
      const hrs = Math.floor(c.hours_left);
      const mins = Math.round((c.hours_left % 1) * 60);
      msg.textContent = `⏳ නොමිලේ අත්හදාබැලීමේ කාලය: තව පැය ${hrs} යි විනාඩි ${mins} යි ඉතිරිව ඇත.`;
      userPill.textContent = `⏳ Trial (${hrs}h)`;
      userPill.classList.remove("hidden");
    } else {
      banner.className = "trial-banner banner-expired";
      banner.classList.remove("hidden");
      msg.textContent = `⚠️ ඔබගේ නොමිලේ අත්හදාබැලීමේ කාලය අවසන් වී ඇත. සම්පූර්ණ පහසුකම් සඳහා ගෙවීම් කරන්න.`;
      userPill.textContent = `⚠️ Expired`;
      userPill.classList.remove("hidden");
    }

    updateDirectWhatsappLink();
  }

  function updateDirectWhatsappLink() {
    const btn = $("directWhatsappBtn");
    if (!btn) return;
    const adminWa = ((state.settings && state.settings.admin_whatsapp) || "94760829235").replace(/\D/g, "");
    const custName = state.customer ? state.customer.name : "Customer";
    const custWa = state.customer ? state.customer.whatsapp : "";
    const price = (state.settings && state.settings.annual_price_lkr) || 1490;

    const text = `හෙලෝ, මම Daily Fortune ඇප් එකේ ගෙවීම් කළා.\n\nනම: ${custName}\nවට්සැප් අංකය: ${custWa}\nමුදල: රු. ${price}/=\n\nබැංකු රිසිට්පත මෙහි අමුණා ඇත. කරුණාකර මගේ ගිණුම සක්‍රිය කරන්න.`;
    btn.href = `https://wa.me/${adminWa}?text=${encodeURIComponent(text)}`;
  }

  function checkTrialAlert() {
    if (!state.customer || state.customer.status !== "trial") return;
    const h = state.customer.hours_left;
    let curBucket = 0;
    if (h <= 0) curBucket = 3;
    else if (h <= 8) curBucket = 2;
    else if (h <= 16) curBucket = 1;

    if (curBucket === 0) return;

    const savedBucket = parseInt(localStorage.getItem(NOTIFIED_BUCKET_KEY) || "0", 10);
    if (curBucket > savedBucket) {
      localStorage.setItem(NOTIFIED_BUCKET_KEY, String(curBucket));
      const hrsLeft = Math.floor(h);
      const title = curBucket === 3 ? "⚠️ නොමිලේ කාලය අවසන් විය!" : "⏳ අත්හදාබැලීමේ කාලය අවසන් වෙමින් පවතී!";
      const text = curBucket === 3
        ? "ඔබගේ පැය 24 ක නොමිලේ අත්හදාබැලීමේ කාලය අවසන් වී ඇත. මුද්‍රණ පහසුකම (Print / PDF Export) ඇතුළුව අඛණ්ඩව සේවාව ලබාගැනීමට දැන්ම වාර්ෂික දායකත්වය සක්‍රිය කරගන්න."
        : `ඔබගේ නොමිලේ අත්හදාබැලීමේ කාලය අවසන් වීමට තව පැය ${hrsLeft} ක් පමණක් ඉතිරිව ඇත. කිසිදු බාධාවකින් තොරව සම්පූර්ණ පහසුකම් ලබාගැනීමට දැන්ම ගෙවීම් කරන්න!`;

      openTrialAlertModal(title, text);
    }
  }

  function openTrialAlertModal(title, text) {
    if ($("trialAlertTitle")) $("trialAlertTitle").textContent = title;
    if ($("trialAlertMsg")) $("trialAlertMsg").textContent = text;
    $("trialAlertModal").classList.remove("hidden");
  }

  function closeTrialAlertModal() {
    $("trialAlertModal").classList.add("hidden");
  }

  function openRegModal() {
    $("regModal").classList.remove("hidden");
  }

  function closeRegModal() {
    $("regModal").classList.add("hidden");
  }

  async function handleRegistration(e) {
    e.preventDefault();
    const name = $("regName").value.trim();
    const whatsapp = $("regWhatsapp").value.trim();
    const address = $("regAddress").value.trim();
    const promo_code = $("regPromoCode").value.trim();
    const errEl = $("regError");
    errEl.classList.add("hidden");

    if (!name || !whatsapp) {
      errEl.textContent = "නම සහ වට්සැප් අංකය ඇතුළත් කිරීම අනිවාර්යයි.";
      errEl.classList.remove("hidden");
      return;
    }

    const submitBtn = $("regSubmitBtn");
    submitBtn.disabled = true;
    submitBtn.textContent = "ලියාපදිංචි වෙමින් පවතී...";

    try {
      const res = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, whatsapp, address, promo_code }),
      });
      const data = await res.json();
      if (res.ok && data.success && data.customer) {
        localStorage.setItem(CUST_TOKEN_KEY, data.customer.token);
        state.customer = data.customer;
        closeRegModal();
        updateSubscriptionUI();
        if ($("fName") && !$("fName").value) {
          $("fName").value = data.customer.name;
        }
        showToast("✓ පැය 24 ක නොමිලේ අත්හදාබැලීම ආරම්භ විය!");
      } else {
        errEl.textContent = data.error || "ලියාපදිංචිය අසාර්ථක විය.";
        errEl.classList.remove("hidden");
      }
    } catch (err) {
      errEl.textContent = "සම්බන්ධතා දෝෂයකි: " + err.message;
      errEl.classList.remove("hidden");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "🚀 නොමිලේ අත්හදාබැලීම අරඹන්න (Start 24h Free Trial)";
    }
  }

  function openPaymentModal(customMsg) {
    if (customMsg && $("payModalSub")) {
      $("payModalSub").textContent = customMsg;
    }
    updateDirectWhatsappLink();
    $("paymentModal").classList.remove("hidden");
  }

  function closePaymentModal() {
    $("paymentModal").classList.add("hidden");
  }

  async function handleSlipUpload() {
    const fileInput = $("slipFileInput");
    const statusEl = $("slipUploadStatus");
    statusEl.classList.add("hidden");

    if (!fileInput.files || !fileInput.files[0]) {
      statusEl.className = "slip-status error";
      statusEl.textContent = "කරුණාකර රිසිට්පත් ඡායාරූපය හෝ PDF ගොනුව තෝරන්න.";
      statusEl.classList.remove("hidden");
      return;
    }

    const file = fileInput.files[0];
    const submitBtn = $("submitSlipBtn");
    submitBtn.disabled = true;
    submitBtn.textContent = "යවමින් පවතී...";

    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const base64Data = reader.result;
        const tok = state.customer ? state.customer.token : localStorage.getItem(CUST_TOKEN_KEY);
        const price = (state.settings && state.settings.annual_price_lkr) || 1490;

        const res = await fetch("/api/payment/submit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            token: tok,
            amount: price,
            slip_base64: base64Data,
          }),
        });
        const data = await res.json();
        if (res.ok && data.success) {
          statusEl.className = "slip-status success";
          statusEl.innerHTML = `✓ රිසිට්පත සාර්ථකව ලැබුණි (අංකය #${data.payment.payment_id})! <br>පරිපාලක විසින් තහවුරු කළ වහාම ඔබගේ ගිණුම සක්‍රිය වේ.`;
          statusEl.classList.remove("hidden");
          fileInput.value = "";
          if (data.whatsapp_url) {
            $("directWhatsappBtn").href = data.whatsapp_url;
          }
        } else {
          statusEl.className = "slip-status error";
          statusEl.textContent = data.error || "රිසිට්පත යැවීම අසාර්ථක විය.";
          statusEl.classList.remove("hidden");
        }
      } catch (err) {
        statusEl.className = "slip-status error";
        statusEl.textContent = "සම්බන්ධතා දෝෂයකි: " + err.message;
        statusEl.classList.remove("hidden");
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "📤 රිසිට්පත යවන්න";
      }
    };
    reader.readAsDataURL(file);
  }

  async function copyBankAccount() {
    const acc = ($("payBankAcc") && $("payBankAcc").textContent) || "8015238548";
    await copyTextToClipboard(acc);
    const btn = $("copyBankAccBtn");
    if (btn) {
      const oldTxt = btn.textContent;
      btn.textContent = "✓ Copied";
      setTimeout(() => { btn.textContent = oldTxt; }, 2000);
    }
    showToast("✓ ගිණුම් අංකය පිටපත් විය!");
  }

  async function handleGenerate(e) {
    if (e) e.preventDefault();
    const errEl = $("formError");
    errEl.classList.add("hidden");

    let payload;
    try {
      payload = collectFormPayload();
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.remove("hidden");
      return;
    }

    const btn = $("submitBtn");
    btn.disabled = true;
    btn.textContent = t("generating");
    try {
      const resp = await fetch("/api/fortune", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error || "Request failed");
      }
      upsertSavedProfile(payload);
      cacheLastResult(data);
      $("offlineBanner").classList.add("hidden");
      renderResult(data);
      // Smoothly collapse form on narrow phone screens after generation so chart is visible immediately
      if (window.innerWidth <= 720) {
        $("formCard").classList.add("hidden");
      }
      $("resultSection").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      const isNetworkErr = !navigator.onLine || err instanceof TypeError;
      if (!isNetworkErr || !tryRestoreCachedSchedule()) {
        errEl.textContent = err.message;
        errEl.classList.remove("hidden");
      }
    } finally {
      btn.disabled = false;
      btn.textContent = t("btnGenerate");
    }
  }

  async function init() {
    loadStorage();
    setDatePreset("today");

    // Wire language & time toggles
    document.querySelectorAll("[data-lang]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.lang = btn.getAttribute("data-lang");
        savePrefs();
        applyTranslations();
      });
    });
    document.querySelectorAll("[data-timefmt]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.timeFmt = btn.getAttribute("data-timefmt");
        savePrefs();
        applyTranslations();
      });
    });

    // District -> City cascade
    $("fBirthDistrict").addEventListener("change", () => {
      populateDistrictCity($("fBirthDistrict"), $("fBirthCity"), $("fBirthDistrict").value, null);
      if (state.targetSynced) {
        populateDistrictCity($("fTargetDistrict"), $("fTargetCity"), $("fBirthDistrict").value, $("fBirthCity").value);
      }
    });
    $("fBirthCity").addEventListener("change", () => {
      if (state.targetSynced) {
        populateDistrictCity($("fTargetDistrict"), $("fTargetCity"), $("fBirthDistrict").value, $("fBirthCity").value);
      }
    });
    $("fTargetDistrict").addEventListener("change", () => {
      state.targetSynced = false;
      populateDistrictCity($("fTargetDistrict"), $("fTargetCity"), $("fTargetDistrict").value, null);
    });
    $("fTargetCity").addEventListener("change", () => {
      state.targetSynced = false;
    });

    // Presets
    document.querySelectorAll("#dayPresets .chip-btn").forEach((b) => {
      b.addEventListener("click", () => setDatePreset(b.getAttribute("data-preset")));
    });
    $("fStartDate").addEventListener("change", syncPresetHighlightFromDates);
    $("fEndDate").addEventListener("change", syncPresetHighlightFromDates);

    document.querySelectorAll(".hour-presets .mini-chip").forEach((b) => {
      b.addEventListener("click", () => {
        $("fFromTime").value = b.getAttribute("data-hfrom");
        $("fToTime").value = b.getAttribute("data-hto");
        document.querySelectorAll(".hour-presets .mini-chip").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
      });
    });

    // Filters
    document.querySelectorAll("#filterPills .filter-btn").forEach((b) => {
      b.addEventListener("click", () => {
        state.filter = b.getAttribute("data-filter");
        if (state.lastResult) renderResult(state.lastResult);
      });
    });

    // Saved profile selection & deletion
    $("savedChips").addEventListener("click", (ev) => {
      const delId = ev.target.getAttribute("data-del");
      if (delId) {
        ev.stopPropagation();
        state.profiles = state.profiles.filter((p) => p.id !== delId);
        if (state.activeProfileId === delId) state.activeProfileId = null;
        saveProfilesStorage();
        renderSavedProfilesBar();
        return;
      }
      const chip = ev.target.closest("[data-pid]");
      if (!chip) return;
      const found = state.profiles.find((p) => p.id === chip.getAttribute("data-pid"));
      if (found) {
        applyProfileToForm(found);
        handleGenerate();
      }
    });

    $("newProfileBtn").addEventListener("click", clearFormForNewPerson);
    $("editBtn").addEventListener("click", () => {
      $("formCard").classList.remove("hidden");
      $("formCard").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    $("collapseFormBtn").addEventListener("click", () => {
      $("formCard").classList.add("hidden");
    });

    $("copyWhatsappBtn").addEventListener("click", async () => {
      const txt = buildWhatsAppText();
      if (!txt) return;
      await copyTextToClipboard(txt);
      showToast(t("copiedMsg"));
    });

    // Install / Phone & PC App Modal wiring
    window.addEventListener("beforeinstallprompt", (ev) => {
      ev.preventDefault();
      state.deferredPrompt = ev;
      updateInstallUI();
    });
    window.addEventListener("appinstalled", () => {
      state.deferredPrompt = null;
      closeInstallModal();
      updateInstallUI();
      showToast(t("installSuccess"));
    });
    async function checkServerAndReconnect() {
      try {
        const res = await fetch("/healthz", { cache: "no-store" });
        if (res.ok) {
          $("offlineBanner").classList.add("hidden");
          handleGenerate();
        }
      } catch (_) {}
    }

    if ($("btnRetryOffline")) {
      $("btnRetryOffline").addEventListener("click", () => {
        const btn = $("btnRetryOffline");
        btn.textContent = "...";
        checkServerAndReconnect().finally(() => {
          btn.textContent = t("btnRetry");
        });
      });
    }

    // Periodically check if server returned online when offline banner is displayed
    setInterval(() => {
      const banner = $("offlineBanner");
      if (banner && !banner.classList.contains("hidden")) {
        checkServerAndReconnect();
      }
    }, 5000);

    window.addEventListener("offline", () => {
      if (state.lastResult) $("offlineBanner").classList.remove("hidden");
    });
    window.addEventListener("online", () => {
      checkServerAndReconnect();
    });

    $("installAppBtn").addEventListener("click", () => {
      if (state.deferredPrompt && !isLocalHost()) {
        triggerNativeInstallPrompt();
      } else {
        openInstallModal();
      }
    });
    $("triggerNativeInstall").addEventListener("click", triggerNativeInstallPrompt);
    $("closeInstallModal").addEventListener("click", closeInstallModal);
    $("closeInstallModalFoot").addEventListener("click", closeInstallModal);
    $("installModal").addEventListener("click", (ev) => {
      if (ev.target === $("installModal")) closeInstallModal();
    });
    $("copyAppUrlBtn").addEventListener("click", async () => {
      await copyTextToClipboard(getAppShareUrl());
      const btn = $("copyAppUrlBtn");
      const oldTxt = btn.textContent;
      btn.textContent = "✓ Copied";
      setTimeout(() => { btn.textContent = oldTxt; }, 2000);
      showToast(t("linkCopied"));
    });

    $("savePdfBtn").addEventListener("click", handleSavePdf);
    $("printBtn").addEventListener("click", () => {
      if (!canCustomerPrint()) {
        notifyPrintLocked();
        return;
      }
      window.print();
    });
    $("fortuneForm").addEventListener("submit", handleGenerate);

    // Subscription & Payment UI Listeners
    if ($("bannerUpgradeBtn")) $("bannerUpgradeBtn").addEventListener("click", () => openPaymentModal());
    if ($("userSubPill")) $("userSubPill").addEventListener("click", () => openPaymentModal());
    if ($("closePaymentModal")) $("closePaymentModal").addEventListener("click", closePaymentModal);
    if ($("closePaymentModalFoot")) $("closePaymentModalFoot").addEventListener("click", closePaymentModal);
    if ($("paymentModal")) {
      $("paymentModal").addEventListener("click", (e) => {
        if (e.target === $("paymentModal")) closePaymentModal();
      });
    }

    if ($("regForm")) $("regForm").addEventListener("submit", handleRegistration);
    if ($("copyBankAccBtn")) $("copyBankAccBtn").addEventListener("click", copyBankAccount);
    if ($("submitSlipBtn")) $("submitSlipBtn").addEventListener("click", handleSlipUpload);

    if ($("trialAlertPayBtn")) {
      $("trialAlertPayBtn").addEventListener("click", () => {
        closeTrialAlertModal();
        openPaymentModal();
      });
    }
    if ($("closeTrialAlertBtn")) $("closeTrialAlertBtn").addEventListener("click", closeTrialAlertModal);

    // Check subscription / registration status on load
    checkSubscriptionStatus();
    setInterval(checkSubscriptionStatus, 60000);

    // Fetch /api/meta
    try {
      const res = await fetch("/api/meta");
      state.meta = await res.json();
      populateDistrictCity($("fBirthDistrict"), $("fBirthCity"), "Colombo", "1");
      populateDistrictCity($("fTargetDistrict"), $("fTargetCity"), "Colombo", "1");
      populateChartSelects(false);
    } catch (err) {
      $("formError").textContent = "Server connection failed.";
      $("formError").classList.remove("hidden");
    }

    initBirthDatePicker();
    renderSavedProfilesBar();
    applyTranslations();
    updateInstallUI();
    registerServiceWorker();

    // Auto-load most recent saved profile if present, with offline cache fallback
    if (state.profiles.length > 0) {
      applyProfileToForm(state.profiles[0]);
      if (navigator.onLine) {
        handleGenerate();
      } else {
        tryRestoreCachedSchedule();
      }
    } else if (!navigator.onLine) {
      tryRestoreCachedSchedule();
    }

    state.nowTimer = setInterval(updateNowBanner, 30000);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
