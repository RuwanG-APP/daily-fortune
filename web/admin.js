/**
 * Daily Fortune — Admin Dashboard Controller
 */

(function () {
  "use strict";

  const STORAGE_KEY = "df_admin_token";
  let adminToken = localStorage.getItem(STORAGE_KEY) || "";

  const $ = (id) => document.getElementById(id);

  // Initialize
  document.addEventListener("DOMContentLoaded", () => {
    initEvents();
    if (adminToken) {
      verifyAndLoad();
    } else {
      showPinOverlay(true);
    }
  });

  function showPinOverlay(show) {
    if (show) {
      $("pinOverlay").classList.remove("hidden");
      $("adminLayout").classList.add("hidden");
      $("adminPinInput").value = "";
      $("adminPinInput").focus();
    } else {
      $("pinOverlay").classList.add("hidden");
      $("adminLayout").classList.remove("hidden");
    }
  }

  function initEvents() {
    // PIN Submission
    $("pinForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const pin = $("adminPinInput").value.trim();
      if (!pin) return;

      try {
        const res = await fetch("/api/admin/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pin }),
        });
        const data = await res.json();
        if (res.ok && data.success && data.token) {
          adminToken = data.token;
          localStorage.setItem(STORAGE_KEY, adminToken);
          $("pinError").classList.add("hidden");
          showPinOverlay(false);
          loadDashboard();
        } else {
          $("pinError").textContent = data.error || "වැරදි මුරපදයකි!";
          $("pinError").classList.remove("hidden");
        }
      } catch (err) {
        $("pinError").textContent = "සම්බන්ධතා දෝෂයකි: " + err.message;
        $("pinError").classList.remove("hidden");
      }
    });

    // Logout
    $("logoutBtn").addEventListener("click", () => {
      localStorage.removeItem(STORAGE_KEY);
      adminToken = "";
      showPinOverlay(true);
    });

    // Tab Switching
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".tab-pane").forEach((p) => p.classList.add("hidden"));
        btn.classList.add("active");
        const targetId = btn.getAttribute("data-tab");
        $(targetId).classList.remove("hidden");

        if (targetId === "slipsTab") loadSlips();
        if (targetId === "customersTab") loadCustomers();
        if (targetId === "settingsTab") loadSettings();
      });
    });

    // Refresh Buttons
    $("refreshSlipsBtn").addEventListener("click", loadSlips);
    $("refreshCustBtn").addEventListener("click", loadCustomers);
    $("custSearchInput").addEventListener("input", debounce(loadCustomers, 300));

    // Settings Form
    $("settingsForm").addEventListener("submit", saveSettings);

    // Slip Modal Close
    $("closeSlipModal").addEventListener("click", () => $("slipModal").classList.add("hidden"));
    $("slipModal").addEventListener("click", (e) => {
      if (e.target === $("slipModal")) $("slipModal").classList.add("hidden");
    });
  }

  async function apiFetch(endpoint, options = {}) {
    options.headers = options.headers || {};
    options.headers["Authorization"] = `Bearer ${adminToken}`;
    const res = await fetch(endpoint, options);
    if (res.status === 401) {
      localStorage.removeItem(STORAGE_KEY);
      adminToken = "";
      showPinOverlay(true);
      throw new Error("Admin session expired. Please log in again.");
    }
    return res;
  }

  async function verifyAndLoad() {
    try {
      const res = await apiFetch("/api/admin/check");
      if (res.ok) {
        showPinOverlay(false);
        loadDashboard();
      } else {
        showPinOverlay(true);
      }
    } catch {
      showPinOverlay(true);
    }
  }

  async function loadDashboard() {
    try {
      const res = await apiFetch("/api/admin/dashboard");
      const data = await res.json();
      if (!res.ok) return;

      $("statTotalCust").textContent = data.total_customers;
      $("statActiveCust").textContent = data.active_customers;
      $("statTrialCust").textContent = data.trial_customers;
      $("statPendingSlips").textContent = data.pending_slips;
      $("tabSlipBadge").textContent = data.pending_slips;
      $("statRevenue").textContent = `රු. ${(data.total_revenue || 0).toLocaleString()}/=`;

      // Prepopulate settings form
      $("cfgAnnualPrice").value = data.annual_price_lkr || 1490;
      $("cfgPromoPrice").value = data.promo_price_lkr || 1000;
      $("cfgBankAccount").value = data.bank_account || "";
      $("cfgBankName").value = data.bank_name || "";
      $("cfgAccountName").value = data.account_name || "";
      $("cfgAdminWhatsapp").value = data.admin_whatsapp || "";

      // Load initial tab
      loadSlips();
    } catch (err) {
      console.error("Dashboard load failed:", err);
    }
  }

  // --------------------------------------------------------------------------
  // Tab 1: Slips Management
  // --------------------------------------------------------------------------
  async function loadSlips() {
    const tbody = $("slipsBody");
    tbody.innerHTML = `<tr><td colspan="7" class="loading-cell">ලෝඩ් වෙමින් පවතී...</td></tr>`;

    try {
      const res = await apiFetch("/api/admin/payments?status=pending");
      const data = await res.json();
      const list = data.payments || [];
      $("tabSlipBadge").textContent = list.length;
      $("statPendingSlips").textContent = list.length;

      if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:24px; color:#64748b;">පොරොත්තු රිසිට්පත් කිසිවක් නොමැත (No pending slips).</td></tr>`;
        return;
      }

      tbody.innerHTML = list
        .map((p) => {
          const dateStr = p.created_at ? new Date(p.created_at).toLocaleString() : "—";
          const waClean = (p.whatsapp || "").replace(/\D/g, "");
          const waLink = waClean ? `<a href="https://wa.me/${waClean}" target="_blank" style="color:#059669; font-weight:700;">🟢 ${p.whatsapp}</a>` : "—";
          const slipBtn = p.slip_filename
            ? `<button type="button" class="btn-slip-view" onclick="window.viewSlip('${p.slip_filename}', ${p.id}, '${escapeHtml(p.name)}', ${p.amount})">👁️ රිසිට්පත බලන්න</button>`
            : `<span style="color:#94a3b8;">No Slip</span>`;

          return `
            <tr>
              <td><strong>#${p.id}</strong></td>
              <td><strong>${escapeHtml(p.name)}</strong></td>
              <td>${waLink}</td>
              <td><strong>රු. ${p.amount}/=</strong></td>
              <td style="font-size:0.8rem; color:#64748b;">${dateStr}</td>
              <td>${slipBtn}</td>
              <td>
                <div class="action-btns">
                  <button type="button" class="btn-action-approve" onclick="window.actionPayment(${p.id}, 'approve')">✅ Approve (1 Year)</button>
                  <button type="button" class="btn-action-reject" onclick="window.actionPayment(${p.id}, 'reject')">❌ Reject</button>
                </div>
              </td>
            </tr>
          `;
        })
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" style="color:red; text-align:center;">දෝෂයකි: ${err.message}</td></tr>`;
    }
  }

  window.viewSlip = function (filename, payId, name, amount) {
    const url = `/api/admin/slips/${filename}?admin_token=${encodeURIComponent(adminToken)}`;
    $("slipFullImg").src = url;
    $("slipModalFoot").innerHTML = `
      <span style="margin-right:auto; font-weight:700; align-self:center;">#${payId} - ${escapeHtml(name)} (රු. ${amount}/=)</span>
      <button type="button" class="btn-action-approve" onclick="window.actionPayment(${payId}, 'approve'); document.getElementById('slipModal').classList.add('hidden');">✅ Approve (1 Year)</button>
      <button type="button" class="btn-action-reject" onclick="window.actionPayment(${payId}, 'reject'); document.getElementById('slipModal').classList.add('hidden');">❌ Reject</button>
    `;
    $("slipModal").classList.remove("hidden");
  };

  window.actionPayment = async function (payId, action) {
    const confirmMsg = action === "approve"
      ? `මෙම රිසිට්පත තහවුරු කර පාරිභෝගිකයාගේ ගිණුම වසර 1ක් (දින 365) සඳහා සක්‍රිය කිරීමට අවශ්‍යද?`
      : `මෙම රිසිට්පත ප්‍රතික්ෂේප (Reject) කිරීමට අවශ්‍යද?`;

    if (!confirm(confirmMsg)) return;

    try {
      const res = await apiFetch("/api/admin/payment/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payment_id: payId, action, days: 365 }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        alert(action === "approve" ? "✓ ගිණුම සාර්ථකව සක්‍රිය කරන ලදී (365 Days)!" : "✓ රිසිට්පත ප්‍රතික්ෂේප විය.");
        loadDashboard();
      } else {
        alert("දෝෂයකි: " + (data.error || "Action failed"));
      }
    } catch (err) {
      alert("සම්බන්ධතා දෝෂයකි: " + err.message);
    }
  };

  // --------------------------------------------------------------------------
  // Tab 2: Customers Management
  // --------------------------------------------------------------------------
  async function loadCustomers() {
    const tbody = $("customersBody");
    const q = $("custSearchInput").value.trim();

    try {
      const res = await apiFetch(`/api/admin/customers?q=${encodeURIComponent(q)}&limit=100`);
      const data = await res.json();
      const list = data.customers || [];

      if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:24px; color:#64748b;">පාරිභෝගිකයින් හමු නොවීය.</td></tr>`;
        return;
      }

      tbody.innerHTML = list
        .map((c) => {
          let badgeClass = "badge-trial";
          let badgeText = `⏳ Trial (${c.hours_left}h)`;
          if (c.status === "active") {
            badgeClass = "badge-active";
            const daysLeft = Math.round(c.hours_left / 24);
            badgeText = `🌟 Active (${daysLeft}d)`;
          } else if (c.status === "expired") {
            badgeClass = "badge-expired";
            badgeText = `⚠️ Expired`;
          }

          const regDate = c.created_at ? new Date(c.created_at).toLocaleDateString() : "—";
          const waClean = (c.whatsapp || "").replace(/\D/g, "");
          const waLink = waClean ? `<a href="https://wa.me/${waClean}" target="_blank" style="color:#059669; font-weight:700;">🟢 ${c.whatsapp}</a>` : "—";

          return `
            <tr>
              <td><strong>#${c.id}</strong></td>
              <td><strong>${escapeHtml(c.name)}</strong></td>
              <td>${waLink}</td>
              <td style="font-size:0.8rem; color:#64748b;">${escapeHtml(c.address || "—")}</td>
              <td><span class="badge ${badgeClass}">${badgeText}</span></td>
              <td style="font-size:0.82rem;">${c.hours_left} hours</td>
              <td style="font-size:0.8rem; color:#64748b;">${regDate}</td>
              <td>
                <div class="action-btns">
                  <button type="button" class="btn-action-extend" onclick="window.manualActivate(${c.id}, 365)">⚡ 1 Year</button>
                  <button type="button" class="btn-action-extend" style="background:#475569;" onclick="window.manualActivate(${c.id}, 30)">+30d</button>
                </div>
              </td>
            </tr>
          `;
        })
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="8" style="color:red; text-align:center;">දෝෂයකි: ${err.message}</td></tr>`;
    }
  }

  window.manualActivate = async function (custId, days) {
    if (!confirm(`පාරිභෝගික #${custId} සඳහා දින ${days} ක සක්‍රිය කිරීමක් ලබාදීමට අවශ්‍යද?`)) return;

    try {
      const res = await apiFetch("/api/admin/customer/activate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: custId, days, notes: `Manual activation (+${days}d)` }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        alert(`✓ පාරිභෝගිකයා සාර්ථකව සක්‍රිය කරන ලදී (දින ${days})!`);
        loadDashboard();
        loadCustomers();
      } else {
        alert("දෝෂයකි: " + (data.error || "Failed"));
      }
    } catch (err) {
      alert("සම්බන්ධතා දෝෂයකි: " + err.message);
    }
  };

  // --------------------------------------------------------------------------
  // Tab 3: Settings Management
  // --------------------------------------------------------------------------
  async function loadSettings() {
    try {
      const res = await apiFetch("/api/admin/dashboard");
      const data = await res.json();
      if (!res.ok) return;

      $("cfgAnnualPrice").value = data.annual_price_lkr || 1490;
      $("cfgPromoPrice").value = data.promo_price_lkr || 1000;
      $("cfgBankAccount").value = data.bank_account || "";
      $("cfgBankName").value = data.bank_name || "";
      $("cfgAccountName").value = data.account_name || "";
      $("cfgAdminWhatsapp").value = data.admin_whatsapp || "";
      $("cfgAdminPin").value = "";
    } catch (err) {
      console.error("Settings load failed:", err);
    }
  }

  async function saveSettings(e) {
    e.preventDefault();
    const payload = {
      annual_price_lkr: $("cfgAnnualPrice").value.trim(),
      promo_price_lkr: $("cfgPromoPrice").value.trim(),
      bank_name: $("cfgBankName").value.trim(),
      bank_account: $("cfgBankAccount").value.trim(),
      account_name: $("cfgAccountName").value.trim(),
      admin_whatsapp: $("cfgAdminWhatsapp").value.trim(),
    };
    const pin = $("cfgAdminPin").value.trim();
    if (pin) {
      payload.admin_pin = pin;
    }

    try {
      const res = await apiFetch("/api/admin/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        $("saveToast").classList.remove("hidden");
        setTimeout(() => $("saveToast").classList.add("hidden"), 3000);
      } else {
        alert("දෝෂයකි: " + (data.error || "Save failed"));
      }
    } catch (err) {
      alert("සම්බන්ධතා දෝෂයකි: " + err.message);
    }
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function debounce(fn, wait) {
    let timeout;
    return function (...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn.apply(this, args), wait);
    };
  }
})();
