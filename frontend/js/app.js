// AgriLink Fleet & Logistics Frontend Application

let mockCitizensList = [];
let activeBookings = [];
let currentFleetList = [];
let currentVehicleAvailability = null;

// Initialization
document.addEventListener("DOMContentLoaded", async () => {
  setupTabs();
  setupLanguageSwitcher();
  await initUserSession();
  setupVoice();
  await refreshActiveTab();
});

// Toast notification helper
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✓' : type === 'error' ? '⚠' : 'ℹ'}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Tab Switching
function setupTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      buttons.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
      
      btn.classList.add("active");
      const targetId = btn.getAttribute("data-target");
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) {
        targetPanel.classList.add("active");
      }
      refreshActiveTab();
    });
  });
}

function refreshActiveTab() {
  const activeBtn = document.querySelector(".tab-btn.active");
  const target = activeBtn ? activeBtn.getAttribute("data-target") : "panel-fleet";
  
  if (target === "panel-fleet") {
    loadFleet();
    loadRenterBookings();
  } else if (target === "panel-owner") {
    loadOwnerVehicles();
    loadOwnerListings();
  } else if (target === "panel-agrilink") {
    // Defaults ready
  } else if (target === "panel-admin") {
    loadAdminVerificationQueue();
    loadAuditTrail();
  } else if (target === "panel-hub") {
    loadOutboxEvents();
    loadWalletState();
    loadCatalog();
  }
}

// ----------------- AUTHENTICATION & SESSIONS -----------------
async function initUserSession() {
  const storedToken = localStorage.getItem("agrilink_token");
  if (storedToken) {
    const res = await API.getMe();
    if (res.ok && res.data) {
      setActor(res.data);
      updateUserInterface();
      return;
    }
  }

  // Fallback to loading demo citizen accounts
  await loadDemoAccounts();
}

async function loadDemoAccounts() {
  const res = await API.getMockCitizens();
  if (res.ok && Array.isArray(res.data)) {
    mockCitizensList = res.data;
    const select = document.getElementById("actor-select");
    if (select) {
      select.innerHTML = "";
      mockCitizensList.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.citizen_id;
        opt.textContent = `${c.name} (${c.personas.filter(p => p !== 'CITIZEN').join('/') || 'Renter'})`;
        select.appendChild(opt);
      });

      if (!currentActor.email && mockCitizensList.length > 0) {
        setActor(mockCitizensList[0]);
      }

      select.addEventListener("change", (e) => {
        const selected = mockCitizensList.find(c => c.citizen_id === e.target.value);
        if (selected) {
          setActor(selected);
          updateUserInterface();
          showToast(`Switched account to: ${selected.name}`, "info");
          refreshActiveTab();
        }
      });
    }
  }
  updateUserInterface();
}

function updateUserInterface() {
  const nameEl = document.getElementById("user-display-name");
  const roleEl = document.getElementById("user-display-role");
  const avatarEl = document.getElementById("user-avatar-initials");
  const logoutBtn = document.getElementById("logout-btn");
  const authMainBtn = document.getElementById("auth-main-btn");

  if (nameEl) nameEl.textContent = currentActor.name || "Sign In";
  if (roleEl) {
    const roleText = currentActor.role ? currentActor.role.replace('_', ' ') : (currentActor.personas ? currentActor.personas.filter(p => p !== 'CITIZEN').join(', ') : 'Guest');
    roleEl.textContent = `${roleText} · KYC ${currentActor.kyc_tier || 'T1'}`;
  }
  if (avatarEl) {
    const initials = (currentActor.name || "GU").split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
    avatarEl.textContent = initials;
  }

  if (currentActor.email) {
    if (logoutBtn) logoutBtn.style.display = "inline-flex";
    if (authMainBtn) authMainBtn.style.display = "none";
  } else {
    if (logoutBtn) logoutBtn.style.display = "none";
    if (authMainBtn) authMainBtn.style.display = "inline-flex";
  }

  // Refresh live wallet balance
  API.getWalletState().then(res => {
    if (res.ok && res.data.balances) {
      const bal = res.data.balances[currentActor.citizen_id] || 0;
      const el = document.getElementById("wallet-balance-display");
      if (el) el.textContent = `₹${bal.toLocaleString('en-IN')}`;
    }
  });
}

function openAuthModal(tab = "signin") {
  switchAuthTab(tab);
  document.getElementById("auth-modal").classList.add("active");
}

function switchAuthTab(tab) {
  const signinBtn = document.getElementById("auth-tab-signin");
  const signupBtn = document.getElementById("auth-tab-signup");
  const signinForm = document.getElementById("auth-form-signin");
  const signupForm = document.getElementById("auth-form-signup");
  const title = document.getElementById("auth-modal-title");

  if (tab === "signin") {
    signinBtn.classList.add("active");
    signupBtn.classList.remove("active");
    signinForm.style.display = "block";
    signupForm.style.display = "none";
    title.textContent = "Sign In to Your Account";
  } else {
    signupBtn.classList.add("active");
    signinBtn.classList.remove("active");
    signupForm.style.display = "block";
    signinForm.style.display = "none";
    title.textContent = "Create Your Account";
  }
}

function quickFillSignIn(email, password) {
  document.getElementById("signin-email").value = email;
  document.getElementById("signin-password").value = password;
  handleSignIn();
}

async function handleSignIn() {
  const email = document.getElementById("signin-email").value.trim();
  const password = document.getElementById("signin-password").value;

  if (!email || !password) {
    showToast("Please enter email and password.", "error");
    return;
  }

  showToast("Signing in...", "info");
  const res = await API.login({ email, password });
  if (res.ok && res.data) {
    setActor(res.data.user);
    if (res.data.access_token) {
      localStorage.setItem("agrilink_token", res.data.access_token);
      currentActor.jwt_token = res.data.access_token;
    }
    closeModals();
    updateUserInterface();
    showToast(`Welcome back, ${res.data.user.name}!`, "success");
    refreshActiveTab();
  } else {
    showToast(`Sign in failed: ${res.data?.detail || 'Invalid email or password'}`, "error");
  }
}

async function handleSignUp() {
  const name = document.getElementById("signup-name").value.trim();
  const email = document.getElementById("signup-email").value.trim();
  const password = document.getElementById("signup-password").value;
  const phone = document.getElementById("signup-phone").value.trim();
  const role = document.getElementById("signup-role").value;
  const licence = document.getElementById("signup-licence").value;

  if (!name || !email || !password) {
    showToast("Please fill in your name, email, and password.", "error");
    return;
  }

  showToast("Creating your account...", "info");
  const res = await API.signUp({
    name,
    email,
    password,
    phone: phone || null,
    role,
    driving_licence_classes: licence,
    kyc_tier: "T2"
  });

  if (res.ok && res.data) {
    setActor(res.data.user);
    if (res.data.access_token) {
      localStorage.setItem("agrilink_token", res.data.access_token);
      currentActor.jwt_token = res.data.access_token;
    }
    closeModals();
    updateUserInterface();
    showToast(`Account created! Welcome, ${res.data.user.name}. ₹30,000 welcome credit added to your wallet!`, "success");
    refreshActiveTab();
  } else {
    showToast(`Sign up failed: ${res.data?.detail || 'Registration error'}`, "error");
  }
}

function handleSignOut() {
  clearSession();
  updateUserInterface();
  showToast("Signed out successfully.", "info");
  refreshActiveTab();
}

// Language Switcher
function setupLanguageSwitcher() {
  const select = document.getElementById("lang-select");
  if (select) {
    select.addEventListener("change", (e) => {
      setLanguage(e.target.value);
      showToast(`Language set to ${e.target.value.toUpperCase()}`, "info");
    });
  }
}

// Voice Search
function setupVoice() {
  const voiceBtn = document.getElementById("voice-search-btn");
  const searchInput = document.getElementById("fleet-search-input");
  
  if (voiceBtn) {
    voiceBtn.addEventListener("click", () => {
      toggleVoiceRecognition(
        (transcript) => {
          searchInput.value = transcript;
          showToast(`Voice transcribed: "${transcript}"`, "success");
          triggerFleetSearch();
        },
        (recording) => {
          if (recording) {
            voiceBtn.classList.add("recording");
            showToast(t("voice_listening"), "info");
          } else {
            voiceBtn.classList.remove("recording");
          }
        }
      );
    });
  }

  const searchBtn = document.getElementById("do-search-btn");
  if (searchBtn) {
    searchBtn.addEventListener("click", triggerFleetSearch);
  }
}

function triggerFleetSearch() {
  const query = document.getElementById("fleet-search-input").value.trim();
  const vClass = document.getElementById("filter-class").value;
  const minCap = document.getElementById("filter-capacity").value;
  const maxPrice = document.getElementById("filter-price").value;

  const params = {};
  if (query) params.location = query;
  if (vClass) params.vehicle_class = vClass;
  if (minCap) params.min_capacity_kg = minCap;
  if (maxPrice) params.max_rate_per_day = maxPrice;

  loadFleet(params);
}

// ----------------- FLEET & RENTER MODULE -----------------
async function loadFleet(filters = {}) {
  const grid = document.getElementById("fleet-grid");
  if (!grid) return;
  grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2rem;">Loading fleet...</div>`;

  const res = await API.searchFleet(filters);
  if (res.ok && Array.isArray(res.data)) {
    currentFleetList = res.data;
    if (currentFleetList.length === 0) {
      grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--text-muted);">No bookable vehicles found matching your criteria.</div>`;
      return;
    }
    grid.innerHTML = currentFleetList.map(item => `
      <div class="card">
        <div class="card-header">
          <div>
            <span class="badge badge-blue">${item.vehicle_class.replace('_', ' ')}</span>
            <div class="card-title" style="margin-top: 0.35rem;">${item.make_model}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${item.registration_number}</div>
          </div>
          <span class="badge badge-green">${item.status}</span>
        </div>
        <div style="margin: 0.75rem 0; font-size: 0.88rem; display: flex; flex-direction: column; gap: 0.35rem;">
          <div><strong>Capacity:</strong> ${item.capacity_kg} kg payload</div>
          <div><strong>Fuel:</strong> ${item.fuel_type}</div>
          <div><strong>Pickup Location:</strong> 📍 ${item.pickup_location}</div>
        </div>
        <div style="display: flex; align-items: baseline; justify-content: space-between; border-top: 1px solid #f1f5f9; padding-top: 0.75rem; margin-top: 0.75rem;">
          <div>
            <span style="font-size: 1.25rem; font-weight: 700; color: var(--primary);">₹${item.rate_per_day}</span>
            <span style="font-size: 0.8rem; color: var(--text-muted);">/ day</span>
            <div style="font-size: 0.75rem; color: var(--text-muted);">(₹${item.rate_per_hour}/hr · ₹${item.rate_per_km}/km)</div>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-secondary btn-sm" onclick="openAvailabilityModal('${item.vehicle_id}')">Calendar</button>
            <button class="btn btn-primary btn-sm" onclick="openBookingModal('${item.vehicle_id}', '${item.make_model}', ${item.rate_per_day}, ${item.security_deposit})">${t("book_now_btn")}</button>
          </div>
        </div>
      </div>
    `).join("");
  } else {
    grid.innerHTML = `<div style="color: var(--danger); padding: 1rem;">Failed to load fleet: ${res.data?.detail || 'Server error'}</div>`;
  }
}

async function loadRenterBookings() {
  const tbody = document.getElementById("renter-bookings-tbody");
  if (!tbody) return;

  const res = await API.listBookings(currentActor.citizen_id);
  if (res.ok && Array.isArray(res.data)) {
    activeBookings = res.data;
    if (activeBookings.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No active bookings for this account.</td></tr>`;
      return;
    }
    tbody.innerHTML = activeBookings.map(b => `
      <tr>
        <td><strong>${b.booking_ref}</strong></td>
        <td>${new Date(b.start_time).toLocaleDateString()} ${new Date(b.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
        <td>₹${b.total_hold_amount} (${b.wallet_hold_status})</td>
        <td><span class="badge ${b.status === 'CONFIRMED' ? 'badge-blue' : b.status === 'ACTIVE' ? 'badge-purple' : b.status === 'COMPLETED' ? 'badge-green' : 'badge-red'}">${b.status}</span></td>
        <td>${b.agrilink_job_ref || 'Direct Rental'}</td>
        <td>
          ${b.status === 'CONFIRMED' ? `
            <button class="btn btn-primary btn-sm" onclick="openHandoverModal('${b.id}', '${b.booking_ref}')">${t("handover_btn")}</button>
            <button class="btn btn-secondary btn-sm" onclick="openCancelModal('${b.id}', '${b.booking_ref}')">${t("cancel_btn")}</button>
          ` : b.status === 'ACTIVE' ? `
            <button class="btn btn-primary btn-sm" onclick="openReturnModal('${b.id}', '${b.booking_ref}')">${t("return_btn")}</button>
          ` : `
            <span style="font-size: 0.8rem; color: var(--text-muted);">Settled</span>
          `}
        </td>
      </tr>
    `).join("");
  }
}

// Availability Calendar Modal
async function openAvailabilityModal(vehicleId) {
  const modal = document.getElementById("calendar-modal");
  const body = document.getElementById("calendar-modal-body");
  modal.classList.add("active");
  body.innerHTML = `<div>Loading calendar slots...</div>`;

  const res = await API.getAvailability(vehicleId);
  if (res.ok && res.data) {
    const data = res.data;
    body.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h4>${data.registration_number}</h4>
        <div style="font-size: 0.85rem; color: var(--text-muted);">Status: <span class="badge badge-green">${data.vehicle_status}</span> · Listing: ${data.listing_status}</div>
      </div>
      <div>
        <h5 style="margin-bottom: 0.5rem;">Reserved / Confirmed Time Slots:</h5>
        ${data.busy_slots.length === 0 ? `<div style="padding: 1rem; background: #f8fafc; border-radius: var(--radius-sm); color: var(--text-muted);">No existing bookings. All slots currently available!</div>` : `
          <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.5rem;">
            ${data.busy_slots.map(s => `
              <li style="padding: 0.6rem 0.85rem; background: #fee2e2; border-radius: var(--radius-sm); font-size: 0.85rem; display: flex; justify-content: space-between;">
                <span>🔒 ${new Date(s.start_time).toLocaleString()} — ${new Date(s.end_time).toLocaleString()}</span>
                <strong>${s.booking_ref}</strong>
              </li>
            `).join("")}
          </ul>
        `}
      </div>
      <div style="margin-top: 1.25rem; font-size: 0.82rem; color: #166534; background: #dcfce7; padding: 0.65rem; border-radius: var(--radius-sm);">
        ✓ Guaranteed calendar exclusion prevents overlapping reservations for this vehicle.
      </div>
    `;
  }
}

// Booking Modal
let bookingVehicleId = null;
function openBookingModal(vehicleId, makeModel, ratePerDay, deposit) {
  bookingVehicleId = vehicleId;
  const modal = document.getElementById("booking-modal");
  document.getElementById("booking-modal-title").textContent = `Book ${makeModel}`;
  
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(9, 0, 0, 0);
  const end = new Date(tomorrow);
  end.setHours(18, 0, 0, 0);

  const formatIsoForInput = (d) => d.toISOString().slice(0, 16);
  document.getElementById("booking-start-time").value = formatIsoForInput(tomorrow);
  document.getElementById("booking-end-time").value = formatIsoForInput(end);

  updatePricePreview();
  modal.classList.add("active");
}

async function updatePricePreview() {
  const start = document.getElementById("booking-start-time").value;
  const end = document.getElementById("booking-end-time").value;
  if (!start || !end || !bookingVehicleId) return;

  const res = await API.estimatePrice(bookingVehicleId, new Date(start).toISOString(), new Date(end).toISOString());
  const previewDiv = document.getElementById("booking-price-preview");
  if (res.ok && res.data) {
    const p = res.data;
    previewDiv.innerHTML = `
      <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0.85rem; font-size: 0.88rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
          <span>Estimated Duration:</span>
          <strong>${p.duration_hours} hours (${p.duration_days} days)</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
          <span>Base Rent Amount:</span>
          <strong>₹${p.base_rent_amount}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
          <span>Security Deposit (Refundable):</span>
          <strong>₹${p.deposit_amount}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; border-top: 1px solid var(--border); padding-top: 0.5rem; margin-top: 0.5rem; font-size: 1rem; color: var(--primary);">
          <span>Total Wallet Fund Hold:</span>
          <strong>₹${p.total_hold_amount}</strong>
        </div>
      </div>
    `;
  }
}

async function confirmBooking() {
  const start = document.getElementById("booking-start-time").value;
  const end = document.getElementById("booking-end-time").value;
  
  const payload = {
    vehicle_id: bookingVehicleId,
    start_time: new Date(start).toISOString(),
    end_time: new Date(end).toISOString()
  };

  showToast("Reserving funds from wallet and confirming booking...", "info");
  const res = await API.createBooking(payload);
  if (res.ok) {
    showToast(`Booking Confirmed! Ref: ${res.data.booking_ref} (Funds Held: ₹${res.data.total_hold_amount})`, "success");
    closeModals();
    loadFleet();
    loadRenterBookings();
    updateUserInterface();
  } else {
    showToast(`Booking Failed: ${res.data?.detail || 'Eligibility or overlap conflict'}`, "error");
  }
}

// Handover Modal
let currentActionBookingId = null;
function openHandoverModal(bookingId, bookingRef) {
  currentActionBookingId = bookingId;
  document.getElementById("handover-ref-display").textContent = bookingRef;
  document.getElementById("handover-modal").classList.add("active");
}

async function submitHandover() {
  const odo = parseFloat(document.getElementById("handover-odo").value);
  const fuel = parseFloat(document.getElementById("handover-fuel").value);
  const notes = document.getElementById("handover-notes").value;

  const res = await API.recordHandover(currentActionBookingId, {
    odometer_reading: odo,
    fuel_level_percent: fuel,
    condition_notes: notes,
    photos: ["enc://photos/handover_reading.jpg"]
  });

  if (res.ok) {
    showToast("Vehicle Handover recorded! Trip is now active.", "success");
    closeModals();
    loadRenterBookings();
    loadFleet();
  } else {
    showToast(`Handover error: ${res.data?.detail}`, "error");
  }
}

// Return Modal
function openReturnModal(bookingId, bookingRef) {
  currentActionBookingId = bookingId;
  document.getElementById("return-ref-display").textContent = bookingRef;
  document.getElementById("return-modal").classList.add("active");
}

async function submitReturn() {
  const odo = parseFloat(document.getElementById("return-odo").value);
  const fuel = parseFloat(document.getElementById("return-fuel").value);
  const damageDetected = document.getElementById("return-damage-toggle").checked;
  const damageAmount = damageDetected ? parseFloat(document.getElementById("return-damage-amount").value || 0) : 0.0;
  const notes = document.getElementById("return-notes").value;

  const res = await API.recordReturn(currentActionBookingId, {
    odometer_reading: odo,
    fuel_level_percent: fuel,
    condition_notes: notes,
    damage_detected: damageDetected,
    damage_amount: damageAmount,
    photos: ["enc://photos/return_finish.jpg"]
  });

  if (res.ok) {
    showToast(`Trip complete! Base rent paid to owner and ₹${res.data.refund_amount} deposit refunded to your wallet.`, "success");
    closeModals();
    loadRenterBookings();
    loadFleet();
    updateUserInterface();
  } else {
    showToast(`Return settlement error: ${res.data?.detail}`, "error");
  }
}

// Cancel Modal
function openCancelModal(bookingId, bookingRef) {
  currentActionBookingId = bookingId;
  document.getElementById("cancel-ref-display").textContent = bookingRef;
  document.getElementById("cancel-modal").classList.add("active");
}

async function submitCancellation() {
  const reason = document.getElementById("cancel-reason").value.trim() || "Customer cancellation";
  const res = await API.cancelBooking(currentActionBookingId, reason);
  if (res.ok) {
    showToast(`Booking cancelled. Fee: ₹${res.data.cancellation_fee}, Refund: ₹${res.data.refund_amount}`, "info");
    closeModals();
    loadRenterBookings();
    loadFleet();
    updateUserInterface();
  } else {
    showToast(`Cancellation error: ${res.data?.detail}`, "error");
  }
}

// ----------------- VEHICLE OWNER MODULE -----------------
async function loadOwnerVehicles() {
  const listDiv = document.getElementById("owner-vehicles-list");
  if (!listDiv) return;
  listDiv.innerHTML = `<div>Loading fleet vehicles...</div>`;

  const res = await API.listVehicles(currentActor.citizen_id);
  if (res.ok && Array.isArray(res.data)) {
    if (res.data.length === 0) {
      listDiv.innerHTML = `<div style="color: var(--text-muted); padding: 1rem;">No vehicles registered under this account yet. Use the registration form to add your first commercial vehicle.</div>`;
      return;
    }
    listDiv.innerHTML = res.data.map(v => `
      <div class="card" style="margin-bottom: 1rem;">
        <div class="card-header">
          <div>
            <span class="badge badge-blue">${v.vehicle_class.replace('_', ' ')}</span>
            <span class="card-title" style="margin-top: 0.25rem;">${v.make_model}</span>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${v.registration_number} · Owner: ${v.owner_name}</div>
          </div>
          <div>
            <span class="badge ${v.verification_status === 'VERIFIED' ? 'badge-green' : v.verification_status === 'REJECTED' ? 'badge-red' : 'badge-yellow'}">${v.verification_status}</span>
            <span class="badge badge-purple">${v.status}</span>
          </div>
        </div>
        <div style="font-size: 0.85rem; margin-bottom: 0.75rem;">
          <div>Payload: ${v.capacity_kg} kg · Fuel: ${v.fuel_type} · Seating: ${v.seating_capacity}</div>
          ${v.verification_reason ? `<div style="color: var(--text-muted); font-size: 0.8rem; margin-top: 0.25rem;">Verification Note: ${v.verification_reason}</div>` : ''}
        </div>
        <div style="display: flex; gap: 0.5rem; border-top: 1px solid #f1f5f9; padding-top: 0.75rem;">
          <button class="btn btn-secondary btn-sm" onclick="openComplianceModal('${v.id}', '${v.registration_number}')">Compliance Documents</button>
          <button class="btn btn-primary btn-sm" onclick="prefillListingModal('${v.id}')">Publish / Edit Listing</button>
        </div>
      </div>
    `).join("");
  }
}

async function loadOwnerListings() {
  const container = document.getElementById("owner-listings-table");
  if (!container) return;
  const res = await API.listListings();
  if (res.ok && Array.isArray(res.data)) {
    const myListings = res.data.filter(l => l.owner_citizen_id === currentActor.citizen_id);
    container.innerHTML = myListings.map(l => `
      <tr>
        <td><strong>${l.pickup_location}</strong></td>
        <td>₹${l.rate_per_day}</td>
        <td>₹${l.security_deposit}</td>
        <td><span class="badge ${l.status === 'ACTIVE' ? 'badge-green' : 'badge-gray'}">${l.status}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="toggleListingStatus('${l.id}', '${l.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE'}')">
            ${l.status === 'ACTIVE' ? 'Pause' : 'Activate'}
          </button>
        </td>
      </tr>
    `).join("");
  }
}

async function toggleListingStatus(listingId, newStatus) {
  const res = await API.updateListing(listingId, { status: newStatus });
  if (res.ok) {
    showToast(`Listing status updated to ${newStatus}`, "success");
    loadOwnerListings();
    loadFleet();
  } else {
    showToast(`Update rejected: ${res.data?.detail}`, "error");
  }
}

// Vehicle Registration Submit
async function submitVehicleRegistration() {
  const regNo = document.getElementById("reg-number").value.trim().toUpperCase();
  const vClass = document.getElementById("reg-class").value;
  const makeModel = document.getElementById("reg-make").value.trim();
  const cap = parseFloat(document.getElementById("reg-cap").value);
  const seats = parseInt(document.getElementById("reg-seats").value);
  const fuel = document.getElementById("reg-fuel").value;
  const rcDoc = document.getElementById("reg-rc-doc").value.trim();

  if (!regNo || !makeModel || !rcDoc) {
    showToast("Please fill all required registration and RC fields.", "error");
    return;
  }

  showToast("Submitting vehicle & verifying against State Vahan Registry...", "info");
  const res = await API.registerVehicle({
    registration_number: regNo,
    vehicle_class: vClass,
    make_model: makeModel,
    capacity_kg: cap,
    seating_capacity: seats,
    fuel_type: fuel,
    rc_document_number: rcDoc,
    rc_file_data: `MOCK_RC_ENCRYPTED_STREAM_${regNo}`
  });

  if (res.ok) {
    showToast(`Vehicle ${res.data.registration_number} Registered! Status: ${res.data.verification_status}`, "success");
    loadOwnerVehicles();
    refreshActiveTab();
  } else {
    showToast(`Registration failed: ${res.data?.detail}`, "error");
  }
}

// Smart OCR Helper
async function runOcrExtract() {
  const prompt = document.getElementById("reg-make").value || "KA-04-MK-4421 Tata Ace Gold";
  showToast("Invoking Smart OCR extraction...", "info");
  const res = await API.extractOcr(prompt);
  if (res.ok && res.data) {
    const o = res.data;
    document.getElementById("reg-number").value = o.registration_number;
    document.getElementById("reg-class").value = o.vehicle_class;
    document.getElementById("reg-make").value = o.make_model;
    document.getElementById("reg-cap").value = o.capacity_kg;
    document.getElementById("reg-rc-doc").value = o.rc_document_number;
    showToast(`OCR Extracted: ${o.registration_number} (${o.make_model}) Confidence: ${(o.confidence_score * 100).toFixed(0)}%`, "success");
  }
}

// Compliance Modal
let currentComplianceVehicleId = null;
async function openComplianceModal(vehicleId, regNo) {
  currentComplianceVehicleId = vehicleId;
  document.getElementById("comp-modal-reg").textContent = regNo;
  const modal = document.getElementById("compliance-modal");
  const listDiv = document.getElementById("comp-docs-list");
  modal.classList.add("active");
  listDiv.innerHTML = "<div>Loading compliance documents...</div>";

  const res = await API.getCompliance(vehicleId);
  if (res.ok && res.data) {
    const c = res.data;
    const badgeClass = c.is_compliant ? "badge-green" : "badge-red";
    listDiv.innerHTML = `
      <div style="margin-bottom: 1rem; padding: 0.75rem; background: ${c.is_compliant ? '#dcfce7' : '#fee2e2'}; border-radius: var(--radius-sm);">
        <strong>Compliance Status:</strong> <span class="badge ${badgeClass}">${c.status_summary}</span>
        ${c.blocking_reason ? `<div style="font-size: 0.85rem; color: #b91c1c; margin-top: 0.35rem;">⚠️ ${c.blocking_reason}</div>` : ''}
      </div>
      <h5>Registered Certificates:</h5>
      <ul style="list-style: none; margin-top: 0.5rem; display: flex; flex-direction: column; gap: 0.5rem;">
        ${c.valid_documents.concat(c.expired_documents).map(d => `
          <li style="padding: 0.5rem 0.75rem; background: #f8fafc; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.85rem; display: flex; justify-content: space-between;">
            <span>${d.document_type}: ${d.document_number}</span>
            <span class="badge ${new Date(d.expiry_date) < new Date() ? 'badge-red' : 'badge-green'}">
              Expires: ${new Date(d.expiry_date).toLocaleDateString()}
            </span>
          </li>
        `).join("")}
      </ul>
    `;
  }
}

async function uploadNewComplianceDoc() {
  const type = document.getElementById("comp-new-type").value;
  const num = document.getElementById("comp-new-num").value.trim();
  const exp = document.getElementById("comp-new-exp").value;

  if (!num || !exp) {
    showToast("Please enter certificate number and expiry date", "error");
    return;
  }

  const res = await API.uploadDocument(currentComplianceVehicleId, {
    document_type: type,
    document_number: num,
    file_reference: `enc://docs/${type.toLowerCase()}_${num}.pdf`,
    expiry_date: new Date(exp).toISOString()
  });

  if (res.ok) {
    showToast(`${type} document uploaded successfully!`, "success");
    openComplianceModal(currentComplianceVehicleId, document.getElementById("comp-modal-reg").textContent);
  } else {
    showToast(`Upload failed: ${res.data?.detail}`, "error");
  }
}

// ----------------- AGRILINK DELIVERY SIMULATOR -----------------
async function submitAgriLinkAssignment() {
  const jobRef = document.getElementById("agl-job-ref").value.trim();
  const vClass = document.getElementById("agl-vclass").value;
  const minCap = parseFloat(document.getElementById("agl-min-cap").value);
  const dest = document.getElementById("agl-dest").value.trim();

  const start = new Date();
  start.setHours(start.getHours() + 1);
  const end = new Date(start);
  end.setHours(end.getHours() + 6);

  showToast(`Dispatching vehicle request for job ${jobRef}...`, "info");
  const res = await API.assignAgriLinkVehicle({
    agrilink_job_ref: jobRef,
    delivery_person_citizen_id: currentActor.citizen_id,
    delivery_person_name: currentActor.name,
    delivery_person_kyc_tier: currentActor.kyc_tier || "T2",
    delivery_person_licence_classes: (currentActor.driving_licence_classes || ["LMV"]).join(','),
    vehicle_class: vClass,
    min_capacity_kg: minCap,
    start_time: start.toISOString(),
    end_time: end.toISOString(),
    destination: dest
  });

  const outputDiv = document.getElementById("agl-result-display");
  if (res.ok) {
    const b = res.data;
    showToast(`Vehicle assigned! Ref: ${b.booking_ref} (Vehicle in In Transit status)`, "success");
    outputDiv.innerHTML = `
      <div style="background: #dcfce7; border: 1px solid #86efac; border-radius: var(--radius-sm); padding: 1rem; color: #166534;">
        <h4 style="margin-bottom: 0.5rem;">✓ Logistics Vehicle Assignment Succeeded</h4>
        <div><strong>AgriLink Job Reference:</strong> ${b.agrilink_job_ref}</div>
        <div><strong>Assigned Booking Ref:</strong> ${b.booking_ref}</div>
        <div><strong>Delivery Partner:</strong> ${b.renter_name} (${b.renter_citizen_id})</div>
        <div><strong>Vehicle Status:</strong> <span class="badge badge-purple">In Transit</span></div>
        <div><strong>Delivery Hold Amount:</strong> ₹${b.total_hold_amount}</div>
        <div style="margin-top: 0.5rem; font-size: 0.8rem; color: #15803d;">
          Cross-microservice event 'VehicleAssigned' dispatched to Outbox for logistics tracking.
        </div>
      </div>
    `;
    loadFleet();
    loadOutboxEvents();
  } else {
    showToast(`Assignment failed: ${res.data?.detail}`, "error");
    outputDiv.innerHTML = `<div style="background: #fee2e2; border: 1px solid #fca5a5; padding: 1rem; color: #b91c1c;">${res.data?.detail}</div>`;
  }
}

// ----------------- ADMIN & OFFICIAL CONSOLE -----------------
async function loadAdminVerificationQueue() {
  const container = document.getElementById("admin-review-queue");
  if (!container) return;

  const res = await API.listVehicles(null, null);
  if (res.ok && Array.isArray(res.data)) {
    const reviewQueue = res.data.filter(v => v.verification_status === "REQUIRES_ADMIN_REVIEW" || v.verification_status === "PENDING");
    if (reviewQueue.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); padding: 1rem;">No pending vehicle verifications in queue. All clear!</div>`;
      return;
    }
    container.innerHTML = reviewQueue.map(v => `
      <div class="card" style="margin-bottom: 1rem; border-left: 4px solid var(--accent);">
        <div class="card-header">
          <div>
            <strong>${v.registration_number}</strong> (${v.make_model})
            <div style="font-size: 0.8rem; color: var(--text-muted);">Owner: ${v.owner_name} (${v.owner_citizen_id})</div>
          </div>
          <span class="badge badge-yellow">${v.verification_status}</span>
        </div>
        <div style="font-size: 0.85rem; margin-bottom: 0.75rem;">
          Note: ${v.verification_reason || 'Pending verification retry or administrator review'}
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <button class="btn btn-primary btn-sm" onclick="adminReviewAction('${v.id}', 'VERIFIED')">Approve & Verify</button>
          <button class="btn btn-danger btn-sm" onclick="adminReviewAction('${v.id}', 'REJECTED')">Reject</button>
        </div>
      </div>
    `).join("");
  }
}

async function adminReviewAction(vehicleId, decision) {
  const res = await API.reviewVerification(vehicleId, decision, `Administrative review by ${currentActor.name}`);
  if (res.ok) {
    showToast(`Vehicle verification updated: ${decision}`, "success");
    loadAdminVerificationQueue();
    loadFleet();
    loadAuditTrail();
  } else {
    showToast(`Review action failed: ${res.data?.detail}`, "error");
  }
}

async function runSweepAction() {
  showToast("Scanning fleet for compliance document expirations...", "info");
  const res = await API.runComplianceSweep();
  if (res.ok) {
    const s = res.data;
    showToast(`Scan complete: Checked ${s.total_vehicles_checked} vehicles (${s.non_compliant_vehicles} non-compliant). ${s.actions_taken.length} listings automatically paused.`, "success");
    loadFleet();
    loadOwnerListings();
    loadAuditTrail();
  }
}

async function loadAuditTrail() {
  const tbody = document.getElementById("admin-audit-tbody");
  if (!tbody) return;
  const res = await API.getAuditRecords(20);
  if (res.ok && Array.isArray(res.data)) {
    tbody.innerHTML = res.data.map(e => `
      <tr>
        <td>${new Date(e.timestamp).toLocaleTimeString()}</td>
        <td><strong>${e.action}</strong></td>
        <td>${e.actor_id} (${e.actor_role})</td>
        <td>${e.entity_type}:${e.entity_id.slice(0, 8)}</td>
        <td style="font-family: monospace; font-size: 0.75rem;">${e.correlation_id ? e.correlation_id.slice(0, 8) + '...' : '-'}</td>
      </tr>
    `).join("");
  }
}

function exportCsvRecordsAction() {
  window.open(`${API_BASE}/records/export?format=csv`, '_blank');
}

function exportVehiclesCsvAction() {
  window.open(`${API_BASE}/records/export/vehicles`, '_blank');
}

// ----------------- MICROSERVICE HUB -----------------
async function loadOutboxEvents() {
  const tbody = document.getElementById("outbox-events-tbody");
  if (!tbody) return;
  const res = await API.getOutboxEvents();
  if (res.ok && Array.isArray(res.data)) {
    tbody.innerHTML = res.data.map(e => `
      <tr>
        <td><strong>${e.event_type}</strong></td>
        <td>${e.aggregate_type}</td>
        <td>${e.aggregate_id.slice(0, 8)}...</td>
        <td><span class="badge ${e.published ? 'badge-green' : 'badge-yellow'}">${e.published ? 'PUBLISHED' : 'PENDING'}</span></td>
        <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.75rem;">${e.payload}</td>
      </tr>
    `).join("");
  }
}

async function dispatchOutboxAction() {
  showToast("Publishing pending events to AgriLink message broker...", "info");
  const res = await API.dispatchOutbox();
  if (res.ok) {
    showToast(`Dispatched ${res.data.dispatched_count} events successfully!`, "success");
    loadOutboxEvents();
  }
}

async function loadWalletState() {
  const container = document.getElementById("hub-wallet-state");
  if (!container) return;
  const res = await API.getWalletState();
  if (res.ok && res.data) {
    const d = res.data;
    container.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h5>Citizen Balances:</h5>
        <div style="display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 0.5rem;">
          ${Object.entries(d.balances).map(([cid, bal]) => `
            <div style="background: #f8fafc; border: 1px solid var(--border); padding: 0.5rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.85rem;">
              <strong>${cid}:</strong> ₹${bal.toLocaleString('en-IN')}
            </div>
          `).join("")}
        </div>
      </div>
      <div>
        <h5>Active Funds Holds:</h5>
        ${d.holds.length === 0 ? `<div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">No active holds.</div>` : `
          <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.5rem;">
            ${d.holds.map(h => `
              <li style="padding: 0.5rem 0.75rem; background: #e0f2fe; border-radius: var(--radius-sm); font-size: 0.85rem; display: flex; justify-content: space-between;">
                <span>🔒 <strong>${h.hold_id}</strong> (${h.citizen_id}) — Ref: ${h.reference_id}</span>
                <strong>₹${h.amount} [${h.status}]</strong>
              </li>
            `).join("")}
          </ul>
        `}
      </div>
    `;
  }
}

async function loadCatalog() {
  const container = document.getElementById("hub-catalog-content");
  if (!container) return;
  const res = await API.getCatalog();
  if (res.ok) {
    container.textContent = JSON.stringify(res.data, null, 2);
  }
}

// Listing Modal Creation & Edit
let activeListingVehicleId = null;

function prefillListingModal(vehicleId) {
  activeListingVehicleId = vehicleId;
  const modal = document.getElementById("listing-modal");
  document.getElementById("listing-vehicle-id").value = vehicleId;
  modal.classList.add("active");
}

async function submitRentalListingForm() {
  const vId = activeListingVehicleId || document.getElementById("listing-vehicle-id").value;
  const rHour = parseFloat(document.getElementById("listing-rate-hour").value);
  const rDay = parseFloat(document.getElementById("listing-rate-day").value);
  const rKm = parseFloat(document.getElementById("listing-rate-km").value);
  const deposit = parseFloat(document.getElementById("listing-deposit").value);
  const pickup = document.getElementById("listing-pickup").value.trim();
  const rules = document.getElementById("listing-rules").value.trim();

  if (!pickup || !rDay) {
    showToast("Please provide daily rate and pickup location", "error");
    return;
  }

  showToast("Publishing rental listing...", "info");
  const res = await API.createListing({
    vehicle_id: vId,
    rate_per_hour: rHour,
    rate_per_day: rDay,
    rate_per_km: rKm,
    security_deposit: deposit,
    pickup_location: pickup,
    rental_rules: rules
  });

  if (res.ok) {
    showToast("Rental listing published! Vehicle is now available for booking.", "success");
    closeModals();
    loadOwnerListings();
    loadOwnerVehicles();
    loadFleet();
  } else {
    if (res.status === 409) {
      showToast("Listing already exists, updating listing parameters...", "info");
      const allListings = await API.listListings();
      const existing = allListings.data.find(l => l.vehicle_id === vId);
      if (existing) {
        const updateRes = await API.updateListing(existing.id, {
          rate_per_hour: rHour,
          rate_per_day: rDay,
          rate_per_km: rKm,
          security_deposit: deposit,
          pickup_location: pickup,
          rental_rules: rules,
          status: "ACTIVE"
        });
        if (updateRes.ok) {
          showToast("Listing updated successfully!", "success");
          closeModals();
          loadOwnerListings();
          loadFleet();
          return;
        }
      }
    }
    showToast(`Listing failed: ${res.data?.detail}`, "error");
  }
}

// Modal helper
function closeModals() {
  document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
}
