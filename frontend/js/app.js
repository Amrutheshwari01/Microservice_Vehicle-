// AgriLink Commercial Fleet & Logistics Frontend Application

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
  }, 4500);
}

// Tab Switching
function setupTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      switchTab(btn.getAttribute("data-target"));
    });
  });
}

function switchTab(targetId) {
  const buttons = document.querySelectorAll(".tab-btn");
  buttons.forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));

  const targetBtn = document.querySelector(`.tab-btn[data-target="${targetId}"]`);
  if (targetBtn) targetBtn.classList.add("active");

  const targetPanel = document.getElementById(targetId);
  if (targetPanel) {
    targetPanel.classList.add("active");
  }
  refreshActiveTab();
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
    // Ready for dispatch
  } else if (target === "panel-admin") {
    loadAdminVerificationQueue();
    loadAuditTrail();
  } else if (target === "panel-hub") {
    loadOutboxEvents();
    loadWalletState();
    loadCatalog();
  }
}

// ----------------- AUTHENTICATION & CUSTOM CREDENTIALS -----------------
async function initUserSession() {
  const storedToken = localStorage.getItem("agrilink_token");
  if (storedToken) {
    try {
      const res = await API.getMe();
      if (res.ok && res.data) {
        setActor(res.data);
        updateUserInterface();
        return;
      }
    } catch (e) {
      console.warn("Session restore failed, falling back to guest mode", e);
    }
  }

  // Set initial clean guest state
  clearSession();
  await loadDemoAccounts();
  updateUserInterface();
}

async function loadDemoAccounts() {
  try {
    const res = await API.getMockCitizens();
    if (res.ok && Array.isArray(res.data)) {
      mockCitizensList = res.data;
      const select = document.getElementById("actor-select");
      if (select) {
        select.innerHTML = '<option value="" disabled selected>Switch to Demo Account</option>';
        mockCitizensList.forEach(c => {
          const opt = document.createElement("option");
          opt.value = c.citizen_id;
          opt.textContent = `${c.name} (${c.personas.filter(p => p !== 'CITIZEN').join('/') || 'Renter'})`;
          select.appendChild(opt);
        });

        select.addEventListener("change", (e) => {
          const selected = mockCitizensList.find(c => c.citizen_id === e.target.value);
          if (selected) {
            setActor(selected);
            updateUserInterface();
            showToast(`Switched account to demo user: ${selected.name}`, "info");
            refreshActiveTab();
          }
        });
      }
    }
  } catch (err) {
    console.error("Could not fetch mock citizens", err);
  }
}

function updateUserInterface() {
  const nameEl = document.getElementById("user-display-name");
  const roleEl = document.getElementById("user-display-role");
  const avatarEl = document.getElementById("user-avatar-initials");
  const logoutBtn = document.getElementById("logout-btn");
  const userWidget = document.getElementById("user-profile-widget");
  const walletWidget = document.getElementById("wallet-badge-widget");
  const loggedOutControls = document.getElementById("logged-out-controls");
  const guestBanner = document.getElementById("top-guest-banner");

  const isLoggedIn = !!(currentActor && currentActor.email);

  if (isLoggedIn) {
    if (guestBanner) guestBanner.style.display = "none";
    if (loggedOutControls) loggedOutControls.style.display = "none";
    if (userWidget) userWidget.style.display = "flex";
    if (walletWidget) walletWidget.style.display = "flex";
    if (logoutBtn) logoutBtn.style.display = "inline-flex";

    if (nameEl) nameEl.textContent = currentActor.name || "My Account";
    if (roleEl) {
      let roleDisplay = "Customer / Renter";
      if (currentActor.role === "VEHICLE_OWNER") roleDisplay = "Vehicle Owner";
      else if (currentActor.role === "DELIVERY_PERSON") roleDisplay = "Logistics Partner";
      else if (currentActor.role === "ADMIN") roleDisplay = "Platform Admin";
      roleEl.textContent = roleDisplay;
    }
    const avatarImgEl = document.getElementById("user-avatar-img");
    if (currentActor.face_thumbnail && avatarImgEl) {
      avatarImgEl.src = currentActor.face_thumbnail;
      avatarImgEl.style.display = "inline-block";
      if (avatarEl) avatarEl.style.display = "none";
    } else {
      if (avatarImgEl) avatarImgEl.style.display = "none";
      if (avatarEl) {
        avatarEl.style.display = "flex";
        const initials = (currentActor.name || "US")
          .split(" ")
          .map(n => n[0])
          .join("")
          .toUpperCase()
          .slice(0, 2);
        avatarEl.textContent = initials;
      }
    }

    // Refresh live wallet balance
    API.getWalletState().then(res => {
      if (res.ok && res.data && res.data.balances) {
        const bal = res.data.balances[currentActor.citizen_id] || 30000;
        const el = document.getElementById("wallet-balance-display");
        if (el) el.textContent = `₹${bal.toLocaleString('en-IN')}`;
      }
    });
  } else {
    // Guest State
    if (guestBanner) guestBanner.style.display = "block";
    if (loggedOutControls) loggedOutControls.style.display = "flex";
    if (userWidget) userWidget.style.display = "none";
    if (walletWidget) walletWidget.style.display = "none";
    if (logoutBtn) logoutBtn.style.display = "none";
  }
}

// Robust API error formatter to prevent [object Object]
function formatApiError(detail, fallback = "An unexpected error occurred") {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map(err => {
      const field = err.loc ? err.loc[err.loc.length - 1] : "Field";
      return `${field}: ${err.msg || 'invalid value'}`;
    }).join("; ");
  }
  if (typeof detail === "object") {
    if (detail.message) return detail.message;
    if (detail.msg) return detail.msg;
    return JSON.stringify(detail);
  }
  return String(detail);
}

// Active camera stream state
let activeCameraStream = null;

function stopActiveCamera() {
  if (activeCameraStream) {
    try {
      activeCameraStream.getTracks().forEach(track => track.stop());
    } catch (e) {
      console.warn("Could not stop camera stream:", e);
    }
    activeCameraStream = null;
  }
}

async function startCameraForElement(videoEl) {
  stopActiveCamera();
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error("Webcam access is not supported by your browser. Please use photo upload instead.");
  }
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
    audio: false
  });
  activeCameraStream = stream;
  videoEl.srcObject = stream;
  await videoEl.play();
  return stream;
}

function captureVideoFrameAsBase64(videoEl, canvasEl, maxWidth = 320) {
  if (!videoEl || !canvasEl) return null;
  const vw = videoEl.videoWidth || 320;
  const vh = videoEl.videoHeight || 240;
  const scale = Math.min(1, maxWidth / vw);
  canvasEl.width = Math.round(vw * scale);
  canvasEl.height = Math.round(vh * scale);
  const ctx = canvasEl.getContext("2d");
  ctx.translate(canvasEl.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);
  return canvasEl.toDataURL("image/jpeg", 0.90);
}

function openAuthModal(tab = "signin") {
  switchAuthTab(tab);
  document.getElementById("auth-modal").classList.add("active");
}

function switchAuthTab(tab) {
  stopActiveCamera();

  const signinBtn = document.getElementById("auth-tab-signin");
  const faceloginBtn = document.getElementById("auth-tab-facelogin");
  const signupBtn = document.getElementById("auth-tab-signup");

  const signinForm = document.getElementById("auth-form-signin");
  const faceloginForm = document.getElementById("auth-form-facelogin");
  const signupForm = document.getElementById("auth-form-signup");

  const title = document.getElementById("auth-modal-title");
  const sub = document.getElementById("auth-modal-sub");

  [signinBtn, faceloginBtn, signupBtn].forEach(b => b && b.classList.remove("active"));
  [signinForm, faceloginForm, signupForm].forEach(f => f && (f.style.display = "none"));

  if (tab === "signin") {
    if (signinBtn) signinBtn.classList.add("active");
    if (signinForm) signinForm.style.display = "block";
    title.textContent = "Sign In to Your Account";
    sub.textContent = "Enter your credentials or use instant face scan to access your account";
  } else if (tab === "facelogin") {
    if (faceloginBtn) faceloginBtn.classList.add("active");
    if (faceloginForm) faceloginForm.style.display = "block";
    title.textContent = "Biometric Face Recognition Sign In";
    sub.textContent = "Look into your camera or upload a photo to authenticate instantly";
    startFaceLoginCamera();
  } else {
    if (signupBtn) signupBtn.classList.add("active");
    if (signupForm) signupForm.style.display = "block";
    title.textContent = "Create Your Account";
    sub.textContent = "Register with your custom credentials and optional face biometric login";
  }
}

// Face Login Handlers
async function startFaceLoginCamera() {
  const videoEl = document.getElementById("face-login-video");
  const statusEl = document.getElementById("face-login-status");
  const capturedImg = document.getElementById("face-login-captured-img");
  const overlay = document.getElementById("face-login-scan-overlay");

  if (capturedImg) capturedImg.style.display = "none";
  if (overlay) overlay.style.display = "flex";

  if (!videoEl || !statusEl) return;

  try {
    statusEl.textContent = "Starting camera...";
    await startCameraForElement(videoEl);
    statusEl.textContent = "Position your face in the circle and click 'Scan Face & Sign In'";
  } catch (err) {
    statusEl.innerHTML = `<span style="color: #dc2626;">Camera unavailable (${err.message}). You can upload a photo below.</span>`;
  }
}

async function performFaceLogin(overrideImage = null) {
  const statusEl = document.getElementById("face-login-status");
  const emailInput = document.getElementById("face-login-email");
  const email = emailInput ? emailInput.value.trim() : "";

  let faceImage = overrideImage;
  if (!faceImage) {
    const videoEl = document.getElementById("face-login-video");
    const canvasEl = document.getElementById("face-login-canvas");
    if (!activeCameraStream) {
      try {
        await startFaceLoginCamera();
        return;
      } catch (e) {
        showToast("Please enable camera access or upload a photo.", "error");
        return;
      }
    }
    faceImage = captureVideoFrameAsBase64(videoEl, canvasEl, 320);
  }

  if (!faceImage) {
    showToast("Please position your face or upload a photo.", "error");
    return;
  }

  const capturedImg = document.getElementById("face-login-captured-img");
  if (capturedImg) {
    capturedImg.src = faceImage;
    capturedImg.style.display = "block";
  }

  if (statusEl) statusEl.innerHTML = `<span style="color: #0284c7;">Analyzing biometric facial features...</span>`;
  showToast("Scanning face biometrics...", "info");

  const res = await API.faceLogin({
    email: email || null,
    face_image: faceImage
  });

  if (res.ok && res.data) {
    stopActiveCamera();
    setActor(res.data.user);
    if (res.data.access_token) {
      localStorage.setItem("agrilink_token", res.data.access_token);
      currentActor.jwt_token = res.data.access_token;
    }
    closeModals();
    updateUserInterface();
    showToast(`Face recognized! Welcome back, ${res.data.user.name}.`, "success");

    if (res.data.user.role === "VEHICLE_OWNER") {
      switchTab("panel-owner");
    } else {
      refreshActiveTab();
    }
  } else {
    const errMsg = formatApiError(res.data?.detail, "Face not recognized. Please center face or use password.");
    if (statusEl) statusEl.innerHTML = `<span style="color: #dc2626;">${errMsg}</span>`;
    showToast(`Face verification failed: ${errMsg}`, "error");
  }
}

function handleFaceLoginFile(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(evt) {
    const b64 = evt.target.result;
    performFaceLogin(b64);
  };
  reader.readAsDataURL(file);
}

// Sign Up Face Enrollment Handlers
async function startSignupCamera() {
  const cameraWrap = document.getElementById("signup-camera-wrap");
  const videoEl = document.getElementById("signup-face-video");
  const btnStart = document.getElementById("btn-start-signup-camera");
  const btnCapture = document.getElementById("btn-capture-signup-face");
  const previewWrap = document.getElementById("signup-face-preview-wrap");

  try {
    if (cameraWrap) cameraWrap.style.display = "block";
    if (previewWrap) previewWrap.style.display = "none";
    await startCameraForElement(videoEl);
    if (btnStart) btnStart.style.display = "none";
    if (btnCapture) btnCapture.style.display = "inline-block";
  } catch (err) {
    showToast(`Camera error: ${err.message}. Please upload a photo instead.`, "error");
  }
}

function captureSignupFace() {
  const videoEl = document.getElementById("signup-face-video");
  const canvasEl = document.getElementById("signup-face-canvas");
  const hiddenInput = document.getElementById("signup-face-image");
  const previewWrap = document.getElementById("signup-face-preview-wrap");
  const previewImg = document.getElementById("signup-face-preview-img");
  const cameraWrap = document.getElementById("signup-camera-wrap");
  const btnCapture = document.getElementById("btn-capture-signup-face");
  const btnRetake = document.getElementById("btn-retake-signup-face");

  const b64 = captureVideoFrameAsBase64(videoEl, canvasEl, 280);
  if (!b64) return;

  stopActiveCamera();
  if (cameraWrap) cameraWrap.style.display = "none";
  if (hiddenInput) hiddenInput.value = b64;
  if (previewImg) previewImg.src = b64;
  if (previewWrap) previewWrap.style.display = "block";
  if (btnCapture) btnCapture.style.display = "none";
  if (btnRetake) btnRetake.style.display = "inline-block";
  showToast("Face biometric captured! You can now complete registration.", "success");
}

function retakeSignupFace() {
  const hiddenInput = document.getElementById("signup-face-image");
  const previewWrap = document.getElementById("signup-face-preview-wrap");
  const btnRetake = document.getElementById("btn-retake-signup-face");
  if (hiddenInput) hiddenInput.value = "";
  if (previewWrap) previewWrap.style.display = "none";
  if (btnRetake) btnRetake.style.display = "none";
  startSignupCamera();
}

function handleSignupFaceFile(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(evt) {
    const b64 = evt.target.result;
    const hiddenInput = document.getElementById("signup-face-image");
    const previewWrap = document.getElementById("signup-face-preview-wrap");
    const previewImg = document.getElementById("signup-face-preview-img");
    const btnStart = document.getElementById("btn-start-signup-camera");
    const btnRetake = document.getElementById("btn-retake-signup-face");

    if (hiddenInput) hiddenInput.value = b64;
    if (previewImg) previewImg.src = b64;
    if (previewWrap) previewWrap.style.display = "block";
    if (btnStart) btnStart.style.display = "none";
    if (btnRetake) btnRetake.style.display = "inline-block";
    showToast("Face photo uploaded and ready for enrollment!", "success");
  };
  reader.readAsDataURL(file);
}

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "Hide";
  } else {
    input.type = "password";
    btn.textContent = "Show";
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
    showToast("Please enter your email and password.", "error");
    return;
  }

  showToast("Signing in...", "info");
  const res = await API.login({ email, password });
  if (res.ok && res.data) {
    stopActiveCamera();
    setActor(res.data.user);
    if (res.data.access_token) {
      localStorage.setItem("agrilink_token", res.data.access_token);
      currentActor.jwt_token = res.data.access_token;
    }
    closeModals();
    updateUserInterface();
    showToast(`Welcome back, ${res.data.user.name}!`, "success");

    // Seamless navigation based on role
    if (res.data.user.role === "VEHICLE_OWNER") {
      switchTab("panel-owner");
    } else {
      refreshActiveTab();
    }
  } else {
    showToast(`Sign in failed: ${formatApiError(res.data?.detail, 'Invalid email or password')}`, "error");
  }
}

async function handleSignUp() {
  const name = document.getElementById("signup-name").value.trim();
  const email = document.getElementById("signup-email").value.trim();
  const password = document.getElementById("signup-password").value;
  const phone = document.getElementById("signup-phone").value.trim();
  const role = document.getElementById("signup-role").value;
  const licence = document.getElementById("signup-licence").value;
  const autoLogin = document.getElementById("signup-auto-login").checked;
  const faceImage = document.getElementById("signup-face-image")?.value || null;

  if (!name || !email || !password) {
    showToast("Please fill in your name, email/username, and password.", "error");
    return;
  }

  if (password.length < 4) {
    showToast("Password must be at least 4 characters.", "error");
    return;
  }

  showToast("Registering your new account...", "info");
  const res = await API.signUp({
    name,
    email,
    password,
    phone: phone || null,
    role,
    driving_licence_classes: licence,
    kyc_tier: "T2",
    face_image: faceImage
  });

  if (res.ok && res.data) {
    stopActiveCamera();
    if (autoLogin) {
      // Auto sign in user immediately
      setActor(res.data.user);
      if (res.data.access_token) {
        localStorage.setItem("agrilink_token", res.data.access_token);
        currentActor.jwt_token = res.data.access_token;
      }
      closeModals();
      updateUserInterface();
      showToast(`Account created! Welcome, ${res.data.user.name}. ₹30,000 welcome credit added to your wallet!`, "success");

      if (role === "VEHICLE_OWNER") {
        switchTab("panel-owner");
      } else {
        refreshActiveTab();
      }
    } else {
      // User opted for the luxury of typing credentials and logging in themselves!
      switchAuthTab("signin");
      document.getElementById("signin-email").value = email;
      document.getElementById("signin-password").value = "";
      document.getElementById("signin-password").focus();
      showToast(`Account created for ${name}! Please enter your password to sign in.`, "success");
    }
  } else {
    showToast(`Registration failed: ${formatApiError(res.data?.detail, 'Please check your inputs')}`, "error");
  }
}

function handleSignOut() {
  clearSession();
  updateUserInterface();
  showToast("You have been signed out.", "info");
  refreshActiveTab();
}

// Language Switcher
function setupLanguageSwitcher() {
  const select = document.getElementById("lang-select");
  if (select) {
    select.addEventListener("change", (e) => {
      setLanguage(e.target.value);
      showToast(`Language changed to ${e.target.value.toUpperCase()}`, "info");
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
          showToast(`Voice query transcribed: "${transcript}"`, "success");
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

function resetFleetFilters() {
  document.getElementById("fleet-search-input").value = "";
  document.getElementById("filter-class").value = "";
  document.getElementById("filter-capacity").value = "";
  document.getElementById("filter-price").value = "";
  loadFleet();
}

// ----------------- FLEET MARKETPLACE MODULE -----------------
async function loadFleet(filters = {}) {
  const grid = document.getElementById("fleet-grid");
  const badge = document.getElementById("fleet-count-badge");
  if (!grid) return;
  grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2.5rem; color: var(--text-muted);">Loading available fleet...</div>`;

  const res = await API.searchFleet(filters);
  if (res.ok && Array.isArray(res.data)) {
    currentFleetList = res.data;
    if (badge) badge.textContent = `${currentFleetList.length} Vehicles Available`;

    if (currentFleetList.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 3rem 1.5rem; background: white; border-radius: var(--radius-md); border: 1px dashed var(--border);">
          <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🚜</div>
          <h3 style="font-weight: 700; color: #1e293b; margin-bottom: 0.35rem;">No commercial vehicles found matching your criteria</h3>
          <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.25rem;">Try clearing your filters or searching another market yard or vehicle category.</p>
          <button class="btn btn-outline btn-sm" onclick="resetFleetFilters()">Reset All Filters</button>
        </div>
      `;
      return;
    }

    grid.innerHTML = currentFleetList.map(item => {
      let icon = "🚛";
      if (item.vehicle_class === "TRACTOR") icon = "🚜";
      else if (item.vehicle_class === "AUTO_RICKSHAW") icon = "🛺";
      else if (item.vehicle_class === "HEAVY_COMMERCIAL") icon = "🚚";

      const formattedClass = item.vehicle_class.replace(/_/g, ' ');

      return `
        <div class="card vehicle-card">
          <div class="card-header">
            <div>
              <span class="vehicle-category-badge">${icon} ${formattedClass}</span>
              <div class="card-title">${item.make_model}</div>
              <div style="font-size: 0.8rem; font-weight: 700; color: #475569; letter-spacing: 0.05em; margin-top: 0.15rem;">
                ${item.registration_number}
              </div>
            </div>
            <span class="badge badge-green">✓ ${item.status}</span>
          </div>

          <div style="margin: 0.75rem 0 1rem 0; font-size: 0.88rem; display: flex; flex-direction: column; gap: 0.4rem; color: #334155;">
            <div><strong>Payload Capacity:</strong> ${item.capacity_kg.toLocaleString()} kg</div>
            <div><strong>Fuel Type:</strong> ${item.fuel_type}</div>
            <div><strong>Pickup Location:</strong> 📍 ${item.pickup_location}</div>
          </div>

          <div style="margin-top: auto; border-top: 1px solid #f1f5f9; padding-top: 0.85rem; display: flex; align-items: flex-end; justify-content: space-between;">
            <div>
              <div>
                <span style="font-size: 1.4rem; font-weight: 800; color: var(--primary);">₹${item.rate_per_day.toLocaleString()}</span>
                <span style="font-size: 0.82rem; color: var(--text-muted); font-weight: 600;">/ day</span>
              </div>
              <div style="font-size: 0.74rem; color: var(--text-muted);">
                ₹${item.rate_per_hour}/hr · ₹${item.rate_per_km}/km · Deposit: ₹${item.security_deposit}
              </div>
            </div>

            <div style="display: flex; gap: 0.45rem;">
              <button class="btn btn-secondary btn-sm" onclick="openAvailabilityModal('${item.vehicle_id}')" title="Check busy/free calendar slots">
                Calendar
              </button>
              <button class="btn btn-primary btn-sm" onclick="openBookingModal('${item.vehicle_id}', '${item.make_model}', ${item.rate_per_day}, ${item.security_deposit})">
                ${t("book_now_btn")}
              </button>
            </div>
          </div>
        </div>
      `;
    }).join("");
  } else {
    grid.innerHTML = `<div style="color: var(--danger); padding: 1.5rem; text-align: center;">Failed to load fleet: ${formatApiError(res.data?.detail, 'Server error')}</div>`;
  }
}

async function loadRenterBookings() {
  const tbody = document.getElementById("renter-bookings-tbody");
  if (!tbody) return;

  // If user is guest, show friendly notice
  if (!currentActor.email) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Please <button class="link-btn" onclick="openAuthModal('signin')">sign in</button> or <button class="link-btn" onclick="openAuthModal('signup')">create an account</button> to view your active bookings.</td></tr>`;
    return;
  }

  const res = await API.listBookings(currentActor.citizen_id);
  if (res.ok && Array.isArray(res.data)) {
    activeBookings = res.data;
    if (activeBookings.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No active bookings for this account. Browse the fleet above to book your first vehicle!</td></tr>`;
      return;
    }
    tbody.innerHTML = activeBookings.map(b => `
      <tr>
        <td><strong>${b.booking_ref}</strong></td>
        <td>${new Date(b.start_time).toLocaleDateString()} ${new Date(b.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
        <td><strong>₹${b.total_hold_amount.toLocaleString()}</strong> <span style="font-size: 0.78rem; color: var(--text-muted);">(${b.wallet_hold_status})</span></td>
        <td><span class="badge ${b.status === 'CONFIRMED' ? 'badge-blue' : b.status === 'ACTIVE' ? 'badge-purple' : b.status === 'COMPLETED' ? 'badge-green' : 'badge-red'}">${b.status}</span></td>
        <td>${b.agrilink_job_ref || 'Direct Customer Rental'}</td>
        <td>
          ${b.status === 'CONFIRMED' ? `
            <div style="display: flex; gap: 0.35rem;">
              <button class="btn btn-primary btn-sm" onclick="openHandoverModal('${b.id}', '${b.booking_ref}')">${t("handover_btn")}</button>
              <button class="btn btn-secondary btn-sm" onclick="openCancelModal('${b.id}', '${b.booking_ref}')">${t("cancel_btn")}</button>
            </div>
          ` : b.status === 'ACTIVE' ? `
            <button class="btn btn-primary btn-sm" onclick="openReturnModal('${b.id}', '${b.booking_ref}')">${t("return_btn")}</button>
          ` : `
            <span style="font-size: 0.82rem; color: var(--success); font-weight: 700;">✓ Settled</span>
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
  body.innerHTML = `<div style="padding: 1.5rem; text-align: center;">Loading availability calendar...</div>`;

  const res = await API.getAvailability(vehicleId);
  if (res.ok && res.data) {
    const data = res.data;
    body.innerHTML = `
      <div style="margin-bottom: 1.25rem;">
        <h4>${data.registration_number}</h4>
        <div style="font-size: 0.86rem; color: var(--text-muted); margin-top: 0.25rem;">Status: <span class="badge badge-green">${data.vehicle_status}</span> · Listing: ${data.listing_status}</div>
      </div>
      <div>
        <h5 style="margin-bottom: 0.65rem; color: #1e293b;">Reserved Time Slots:</h5>
        ${data.busy_slots.length === 0 ? `
          <div style="padding: 1.25rem; background: #f0fdf4; border-radius: var(--radius-sm); color: #166534; border: 1px solid #bbf7d0;">
            ✓ All calendar slots are currently open and available for instant booking!
          </div>
        ` : `
          <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.5rem;">
            ${data.busy_slots.map(s => `
              <li style="padding: 0.65rem 0.95rem; background: #fee2e2; border-radius: var(--radius-sm); font-size: 0.85rem; display: flex; justify-content: space-between; border: 1px solid #fecaca;">
                <span>🔒 ${new Date(s.start_time).toLocaleString()} — ${new Date(s.end_time).toLocaleString()}</span>
                <strong>Ref: ${s.booking_ref}</strong>
              </li>
            `).join("")}
          </ul>
        `}
      </div>
      <div style="margin-top: 1.25rem; font-size: 0.82rem; color: #166534; background: #dcfce7; padding: 0.75rem; border-radius: var(--radius-sm);">
        ✓ Strict calendar lock guarantees zero overlapping reservations on this commercial vehicle.
      </div>
    `;
  }
}

// Booking Modal
let bookingVehicleId = null;
function openBookingModal(vehicleId, makeModel, ratePerDay, deposit) {
  // Guard for guest users: require login/signup
  if (!currentActor.email) {
    showToast("Please sign in or create an account to book vehicles.", "info");
    openAuthModal("signin");
    return;
  }

  bookingVehicleId = vehicleId;
  const modal = document.getElementById("booking-modal");
  document.getElementById("booking-modal-title").textContent = `Book ${makeModel}`;
  
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(9, 0, 0, 0);
  const end = new Date(tomorrow);
  end.setHours(18, 0, 0, 0);

  const formatIsoForInput = (d) => {
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

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
      <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0.95rem; font-size: 0.88rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
          <span>Rental Duration:</span>
          <strong>${p.duration_hours} hours (${p.duration_days} days)</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
          <span>Base Rent:</span>
          <strong>₹${p.base_rent_amount.toLocaleString()}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
          <span>Security Deposit (100% Refundable):</span>
          <strong>₹${p.deposit_amount.toLocaleString()}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; border-top: 1px solid var(--border); padding-top: 0.5rem; margin-top: 0.5rem; font-size: 1.05rem; color: var(--primary);">
          <span>Total Wallet Escrow Hold:</span>
          <strong>₹${p.total_hold_amount.toLocaleString()}</strong>
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

  showToast("Confirming booking and securing funds from wallet...", "info");
  const res = await API.createBooking(payload);
  if (res.ok) {
    showToast(`Booking Confirmed! Reference: ${res.data.booking_ref} (Funds Reserved: ₹${res.data.total_hold_amount})`, "success");
    closeModals();
    loadFleet();
    loadRenterBookings();
    updateUserInterface();
  } else {
    showToast(`Booking Failed: ${formatApiError(res.data?.detail, 'Schedule conflict or insufficient wallet balance')}`, "error");
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
    showToast("Vehicle handover recorded! Trip is now in progress.", "success");
    closeModals();
    loadRenterBookings();
    loadFleet();
  } else {
    showToast(`Handover error: ${formatApiError(res.data?.detail)}`, "error");
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
    showToast(`Return settlement error: ${formatApiError(res.data?.detail)}`, "error");
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
    showToast(`Cancellation error: ${formatApiError(res.data?.detail)}`, "error");
  }
}

// ----------------- VEHICLE OWNER MODULE -----------------
async function loadOwnerVehicles() {
  const listDiv = document.getElementById("owner-vehicles-list");
  if (!listDiv) return;

  if (!currentActor.email) {
    listDiv.innerHTML = `<div style="color: var(--text-muted); padding: 1.5rem; text-align: center;">Please <button class="link-btn" onclick="openAuthModal('signin')">sign in</button> or <button class="link-btn" onclick="openAuthModal('signup')">create an account</button> to view your registered fleet.</div>`;
    return;
  }

  listDiv.innerHTML = `<div style="padding: 1rem; color: var(--text-muted);">Loading fleet vehicles...</div>`;

  const res = await API.listVehicles(currentActor.citizen_id);
  if (res.ok && Array.isArray(res.data)) {
    if (res.data.length === 0) {
      listDiv.innerHTML = `<div style="color: var(--text-muted); padding: 1.25rem;">No vehicles registered under this account yet. Use the registration form to add your first commercial vehicle.</div>`;
      return;
    }
    listDiv.innerHTML = res.data.map(v => `
      <div class="card" style="margin-bottom: 1rem; border-left: 4px solid var(--primary);">
        <div class="card-header">
          <div>
            <span class="vehicle-category-badge">${v.vehicle_class.replace(/_/g, ' ')}</span>
            <div class="card-title">${v.make_model}</div>
            <div style="font-size: 0.82rem; font-weight: 700; color: #475569; letter-spacing: 0.05em; margin-top: 0.15rem;">
              ${v.registration_number}
            </div>
          </div>
          <div style="display: flex; gap: 0.4rem; flex-wrap: wrap; justify-content: flex-end;">
            <span class="badge ${v.verification_status === 'VERIFIED' ? 'badge-green' : v.verification_status === 'REJECTED' ? 'badge-red' : 'badge-yellow'}">
              ${v.verification_status}
            </span>
            <span class="badge badge-purple">${v.status}</span>
          </div>
        </div>
        <div style="font-size: 0.86rem; margin-bottom: 0.75rem; color: #334155;">
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

  if (!currentActor.email) {
    container.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Please sign in to view your published listings.</td></tr>`;
    return;
  }

  const res = await API.listListings();
  if (res.ok && Array.isArray(res.data)) {
    const myListings = res.data.filter(l => l.owner_citizen_id === currentActor.citizen_id);
    if (myListings.length === 0) {
      container.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 1.25rem;">No published listings yet. Register a vehicle and click Publish Listing!</td></tr>`;
      return;
    }
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
    showToast(`Update rejected: ${formatApiError(res.data?.detail)}`, "error");
  }
}

// Vehicle Registration Submit
async function submitVehicleRegistration() {
  if (!currentActor.email) {
    showToast("Please sign in or create an account to register commercial vehicles.", "info");
    openAuthModal("signin");
    return;
  }

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
    showToast(`Registration failed: ${formatApiError(res.data?.detail)}`, "error");
  }
}

// Smart OCR Helper
async function runOcrExtract() {
  const prompt = document.getElementById("reg-make").value || "KA-04-MK-4421 Tata Ace Gold";
  showToast("Running Smart OCR document extraction...", "info");
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
  listDiv.innerHTML = "<div style='padding: 1rem;'>Loading compliance certificates...</div>";

  const res = await API.getCompliance(vehicleId);
  if (res.ok && res.data) {
    const c = res.data;
    const badgeClass = c.is_compliant ? "badge-green" : "badge-red";
    listDiv.innerHTML = `
      <div style="margin-bottom: 1.25rem; padding: 0.85rem; background: ${c.is_compliant ? '#dcfce7' : '#fee2e2'}; border-radius: var(--radius-sm); border: 1px solid ${c.is_compliant ? '#bbf7d0' : '#fecaca'};">
        <strong>Compliance Status:</strong> <span class="badge ${badgeClass}">${c.status_summary}</span>
        ${c.blocking_reason ? `<div style="font-size: 0.85rem; color: #b91c1c; margin-top: 0.4rem;">⚠️ ${c.blocking_reason}</div>` : ''}
      </div>
      <h5>Registered Certificates:</h5>
      <ul style="list-style: none; margin-top: 0.65rem; display: flex; flex-direction: column; gap: 0.5rem;">
        ${c.valid_documents.concat(c.expired_documents).map(d => `
          <li style="padding: 0.6rem 0.85rem; background: #f8fafc; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.86rem; display: flex; justify-content: space-between;">
            <span><strong>${d.document_type}:</strong> ${d.document_number}</span>
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
    showToast(`${type} certificate uploaded successfully!`, "success");
    openComplianceModal(currentComplianceVehicleId, document.getElementById("comp-modal-reg").textContent);
  } else {
    showToast(`Upload failed: ${formatApiError(res.data?.detail)}`, "error");
  }
}

// ----------------- LOGISTICS & DISPATCH SIMULATOR -----------------
async function submitAgriLinkAssignment() {
  const jobRef = document.getElementById("agl-job-ref").value.trim();
  const vClass = document.getElementById("agl-vclass").value;
  const minCap = parseFloat(document.getElementById("agl-min-cap").value);
  const dest = document.getElementById("agl-dest").value.trim();

  const start = new Date();
  start.setHours(start.getHours() + 1);
  const end = new Date(start);
  end.setHours(end.getHours() + 6);

  showToast(`Dispatching vehicle matching request for job ${jobRef}...`, "info");
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
    showToast(`Vehicle assigned! Reference: ${b.booking_ref} (Vehicle in In Transit status)`, "success");
    outputDiv.innerHTML = `
      <div style="background: #dcfce7; border: 1px solid #86efac; border-radius: var(--radius-sm); padding: 1.25rem; color: #166534;">
        <h4 style="margin-bottom: 0.65rem; font-weight: 800;">✓ Logistics Vehicle Assigned Successfully</h4>
        <div style="display: flex; flex-direction: column; gap: 0.35rem; font-size: 0.9rem;">
          <div><strong>Delivery Job Reference:</strong> ${b.agrilink_job_ref}</div>
          <div><strong>Assigned Booking Ref:</strong> ${b.booking_ref}</div>
          <div><strong>Delivery Partner:</strong> ${b.renter_name}</div>
          <div><strong>Vehicle Status:</strong> <span class="badge badge-purple">In Transit</span></div>
          <div><strong>Logistics Escrow Hold:</strong> ₹${b.total_hold_amount}</div>
        </div>
        <div style="margin-top: 0.75rem; font-size: 0.82rem; color: #15803d; border-top: 1px solid #bbf7d0; padding-top: 0.5rem;">
          Real-time event 'VehicleAssigned' dispatched to outbox for logistics route tracking.
        </div>
      </div>
    `;
    loadFleet();
    loadOutboxEvents();
  } else {
    const errMsg = formatApiError(res.data?.detail);
    showToast(`Assignment failed: ${errMsg}`, "error");
    outputDiv.innerHTML = `<div style="background: #fee2e2; border: 1px solid #fca5a5; padding: 1.25rem; color: #b91c1c; border-radius: var(--radius-sm);">${errMsg}</div>`;
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
      container.innerHTML = `<div style="color: var(--text-muted); padding: 1.25rem;">No pending vehicle verifications in queue. All vehicles verified!</div>`;
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
  const res = await API.reviewVerification(vehicleId, decision, `Administrative review by ${currentActor.name || 'Official'}`);
  if (res.ok) {
    showToast(`Vehicle verification updated: ${decision}`, "success");
    loadAdminVerificationQueue();
    loadFleet();
    loadAuditTrail();
  } else {
    showToast(`Review action failed: ${formatApiError(res.data?.detail)}`, "error");
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

// ----------------- PLATFORM ACTIVITY & HUB -----------------
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
  showToast("Dispatching pending events...", "info");
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
      <div style="margin-bottom: 1.25rem;">
        <h5 style="margin-bottom: 0.5rem;">Citizen Digital Balances:</h5>
        <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
          ${Object.entries(d.balances).map(([cid, bal]) => `
            <div style="background: #f8fafc; border: 1px solid var(--border); padding: 0.5rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.85rem;">
              <strong>${cid}:</strong> ₹${bal.toLocaleString('en-IN')}
            </div>
          `).join("")}
        </div>
      </div>
      <div>
        <h5 style="margin-bottom: 0.5rem;">Active Escrow Holds:</h5>
        ${d.holds.length === 0 ? `<div style="font-size: 0.85rem; color: var(--text-muted);">No active escrow holds.</div>` : `
          <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.5rem;">
            ${d.holds.map(h => `
              <li style="padding: 0.55rem 0.85rem; background: #e0f2fe; border-radius: var(--radius-sm); font-size: 0.85rem; display: flex; justify-content: space-between;">
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
    showToast("Rental listing published! Vehicle is now available in the fleet marketplace.", "success");
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
    showToast(`Listing failed: ${formatApiError(res.data?.detail)}`, "error");
  }
}

// Modal helper
function closeModals() {
  if (typeof stopActiveCamera === "function") {
    stopActiveCamera();
  }
  document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
}
