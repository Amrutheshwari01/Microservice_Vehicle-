// AgriLink Commercial Fleet & Logistics Platform API Client
const API_BASE = "/v1";

// Active user session state
let currentActor = {
  citizen_id: "GUEST_VISITOR",
  name: "Guest Visitor",
  email: "",
  role: "GUEST",
  personas: ["CITIZEN"],
  kyc_tier: "T0",
  driving_licence_classes: ["LMV"],
  jwt_token: localStorage.getItem("agrilink_token") || ""
};

function setActor(actor) {
  currentActor = {
    ...currentActor,
    ...actor,
    citizen_id: actor.id || actor.citizen_id,
    jwt_token: actor.jwt_token || actor.access_token || currentActor.jwt_token
  };
  if (currentActor.jwt_token) {
    localStorage.setItem("agrilink_token", currentActor.jwt_token);
  }
}

function clearSession() {
  localStorage.removeItem("agrilink_token");
  currentActor = {
    citizen_id: "GUEST_VISITOR",
    name: "Guest Visitor",
    email: "",
    role: "GUEST",
    personas: ["CITIZEN"],
    kyc_tier: "T0",
    driving_licence_classes: ["LMV"],
    jwt_token: ""
  };
}

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

async function apiRequest(endpoint, method = "GET", body = null, customHeaders = {}) {
  const correlationId = generateUUID();
  const headers = {
    "Content-Type": "application/json",
    "X-Correlation-ID": correlationId,
    "X-Citizen-ID": currentActor.citizen_id,
    ...customHeaders
  };

  const token = currentActor.jwt_token || localStorage.getItem("agrilink_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const options = {
    method,
    headers
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, options);
    const contentType = res.headers.get("content-type");
    
    if (contentType && contentType.includes("text/csv")) {
      const text = await res.text();
      return { ok: res.ok, status: res.status, data: text, isBlob: true };
    }

    const data = await res.json();
    return {
      ok: res.ok,
      status: res.status,
      data: data,
      correlationId: res.headers.get("X-Correlation-ID") || correlationId
    };
  } catch (err) {
    console.error("API Error:", err);
    return { ok: false, status: 500, data: { detail: err.message }, correlationId };
  }
}

const API = {
  // Authentication & Profile
  signUp: (userData) => apiRequest("/auth/signup", "POST", userData),
  login: (credentials) => apiRequest("/auth/login", "POST", credentials),
  faceLogin: (payload) => apiRequest("/auth/face-login", "POST", payload),
  enrollFace: (payload) => apiRequest("/auth/enroll-face", "POST", payload),
  getMe: () => apiRequest("/auth/me"),

  // Fleet & Registration
  registerVehicle: (vehData) => apiRequest("/vehicles", "POST", vehData),
  extractOcr: (text) => apiRequest("/vehicles/ocr-extract", "POST", { raw_text_or_filename: text }),
  listVehicles: (ownerId = null, status = null) => {
    let url = "/vehicles?";
    if (ownerId) url += `owner_citizen_id=${encodeURIComponent(ownerId)}&`;
    if (status) url += `status_filter=${encodeURIComponent(status)}&`;
    return apiRequest(url);
  },
  getVehicle: (id) => apiRequest(`/vehicles/${id}`),
  searchFleet: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return apiRequest(`/vehicles/search?${query}`);
  },
  getAvailability: (id) => apiRequest(`/vehicles/${id}/availability`),
  transitionVehicleStatus: (id, targetStatus, reason = "") => 
    apiRequest(`/vehicles/${id}/status`, "PATCH", { target_status: targetStatus, reason }),
  reviewVerification: (id, decision, reason = "") => 
    apiRequest(`/vehicles/${id}/verification-review`, "POST", { decision, reason }),

  // Listings & Rates
  createListing: (listingData) => apiRequest("/listings", "POST", listingData),
  updateListing: (id, updateData) => apiRequest(`/listings/${id}`, "PATCH", updateData),
  listListings: () => apiRequest("/listings"),

  // Bookings, Handover & Settlement
  estimatePrice: (vehicleId, startTime, endTime) => 
    apiRequest("/bookings/estimate-price", "POST", { vehicle_id: vehicleId, start_time: startTime, end_time: endTime }),
  createBooking: (bookingData) => 
    apiRequest("/bookings", "POST", { ...bookingData, idempotency_key: `idemp-${generateUUID()}` }),
  listBookings: (renterId = null) => 
    apiRequest(renterId ? `/bookings?renter_citizen_id=${encodeURIComponent(renterId)}` : "/bookings"),
  recordHandover: (bookingId, handoverData) => 
    apiRequest(`/bookings/${bookingId}/handover`, "POST", handoverData),
  recordReturn: (bookingId, returnData) => 
    apiRequest(`/bookings/${bookingId}/return`, "POST", returnData),
  cancelBooking: (bookingId, reason) => 
    apiRequest(`/bookings/${bookingId}/cancel`, "POST", { reason }),

  // Logistics & Delivery Integration
  assignAgriLinkVehicle: (jobData) => 
    apiRequest("/vehicle-requests", "POST", { ...jobData, idempotency_key: `idemp-agl-${generateUUID()}` }),

  // Compliance & Audit
  uploadDocument: (vehicleId, docData) => 
    apiRequest(`/vehicles/${vehicleId}/documents`, "POST", docData),
  getCompliance: (vehicleId) => 
    apiRequest(`/vehicles/${vehicleId}/compliance`),
  runComplianceSweep: () => 
    apiRequest("/compliance/sweep", "POST"),
  getAuditRecords: (limit = 50) => 
    apiRequest(`/records?limit=${limit}`),
  exportCsvRecords: () => 
    apiRequest("/records/export?format=csv"),
  exportVehicleRegistry: () => 
    apiRequest("/records/export/vehicles"),

  // Outbox & Activity Hub
  getOutboxEvents: (published = null) => 
    apiRequest(published !== null ? `/inter-service/outbox?published_filter=${published}` : "/inter-service/outbox"),
  dispatchOutbox: () => 
    apiRequest("/inter-service/outbox/dispatch", "POST"),
  getWalletState: () => 
    apiRequest("/inter-service/mock-wallet/state"),
  getMockCitizens: () => 
    apiRequest("/inter-service/mock-identity/citizens"),
  getCatalog: () => 
    apiRequest("/inter-service/catalog")
};
