// CYRIS Frontend Application Engine - SIH 2026

const API_BASE_URL = window.location.protocol + "//" + window.location.hostname + (window.location.port ? ":" + window.location.port : "");
const WS_URL = (window.location.protocol === "https:" ? "wss://" : "ws://") + window.location.hostname + (window.location.port ? ":" + window.location.port : "") + "/ws/alerts";

// Global State
let currentUser = null;
let currentSelectedAuthority = "CYBER_AUTHORITY";
let complaintsData = [];
let activeComplaint = null;
let leafletMap = null;
let mapMarkers = [];
let pendingOTPPhone = "";
let simulatedOTPCode = "123456";
let socket = null;

// Initialization
document.addEventListener("DOMContentLoaded", () => {
    console.log("CYRIS Platform Initializing...");
    initWebSocket();
    fetchComplaints();
    fetchGISLocations();
});

// WebSocket Real-Time Alert Listener
function initWebSocket() {
    const badge = document.getElementById("live-socket-badge");
    try {
        socket = new WebSocket(WS_URL);

        socket.onopen = () => {
            console.log("WebSocket Alert Feed Connected!");
            if (badge) {
                badge.className = "badge-socket connected";
                badge.innerHTML = `<span class="dot"></span> Live Alerts: Connected`;
            }
        };

        socket.onmessage = (event) => {
            const payload = JSON.parse(event.data);
            console.log("Real-time WS Event Received:", payload);
            handleRealTimeSocketEvent(payload);
        };

        socket.onclose = () => {
            if (badge) {
                badge.className = "badge-socket disconnected";
                badge.innerHTML = `<span class="dot"></span> Live Alerts: Offline`;
            }
            // Reconnect after 3 seconds
            setTimeout(initWebSocket, 3000);
        };
    } catch (e) {
        console.warn("WebSocket init error:", e);
    }
}

function handleRealTimeSocketEvent(data) {
    if (data.event === "NEW_COMPLAINT_SUBMITTED") {
        showToastAlert(`🚨 New Complaint Registered: ${data.complaintId}`, `High Risk ${data.fraudType} (₹${data.amount.toLocaleString()}) filed in ${data.location.city}. Score: ${data.riskScore}`);
        fetchComplaints();
        fetchGISLocations();
    } else if (data.event === "PREDICTION_VERIFIED") {
        showToastAlert(`✓ Prediction Updated`, `Complaint ${data.complaintId} verified as ${data.verificationStatus}`);
        if (activeComplaint && activeComplaint.complaintId === data.complaintId) {
            document.getElementById("prediction-verify-status").innerText = `Status: ${data.verificationStatus}`;
        }
    } else if (data.event === "STATUS_UPDATED") {
        fetchComplaints();
    }
}

function showToastAlert(title, body) {
    const container = document.getElementById("alert-toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast-alert";
    toast.innerHTML = `
        <div class="toast-title">${title}</div>
        <div class="toast-body">${body}</div>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Navigation & Screen Management
function showScreen(screenId) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    const target = document.getElementById(screenId);
    if (target) target.classList.add("active");

    if (screenId === "screen-authority") {
        fetchComplaints();
        setTimeout(() => {
            initLeafletMap();
            fetchGISLocations();
        }, 200);
    }
}

function openCitizenLogin() {
    showScreen("screen-citizen");
}

function openAuthorityModal() {
    openModal("modal-authority");
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove("active");
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add("active");
}

function selectAuthorityOption(authRole) {
    currentSelectedAuthority = authRole;
    document.querySelectorAll(".auth-option").forEach(opt => opt.classList.remove("active"));
    
    if (authRole === "CYBER_AUTHORITY") {
        document.getElementById("auth-opt-cyber").classList.add("active");
        document.getElementById("auth-username").value = "cyber_authority";
    } else if (authRole === "POLICE") {
        document.getElementById("auth-opt-police").classList.add("active");
        document.getElementById("auth-username").value = "police_officer";
    } else if (authRole === "BANK_AUTHORITY") {
        document.getElementById("auth-opt-bank").classList.add("active");
        document.getElementById("auth-username").value = "bank_officer";
    }
}

// Authority Login Submit
async function handleAuthorityLoginSubmit(e) {
    e.preventDefault();
    const username = document.getElementById("auth-username").value.trim();
    const password = document.getElementById("auth-password").value.trim();

    try {
        const res = await fetch(`${API_BASE_URL}/api/auth/authority-login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                authority_type: currentSelectedAuthority,
                username: username,
                password: password
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Authentication failed");

        currentUser = data;
        closeModal("modal-authority");

        // Update Nav User Pill
        document.getElementById("current-user-pill").style.display = "flex";
        document.getElementById("user-role-label").innerText = `${data.role}: ${data.username}`;

        // Header Title
        const titleHeading = document.getElementById("authority-title-heading");
        if (data.role === "POLICE") titleHeading.innerText = "Police & Investigator Cyber Dashboard";
        else if (data.role === "BANK_AUTHORITY") titleHeading.innerText = "Nodal Bank Officer Dashboard";
        else titleHeading.innerText = "Cybercrime Authority Intelligence Dashboard";

        showScreen("screen-authority");
    } catch (err) {
        alert("Authority Login Failed: " + err.message);
    }
}

function logout() {
    currentUser = null;
    document.getElementById("current-user-pill").style.display = "none";
    showScreen("screen-landing");
}

// Citizen Form Submit & Real-Time OTP Flow
async function handleComplaintSubmit(e) {
    e.preventDefault();
    const phone = document.getElementById("c-phone").value.trim();

    if (!phone) {
        alert("Mobile number is required for OTP verification.");
        return;
    }

    pendingOTPPhone = phone;

    // Request Real-Time OTP
    try {
        const res = await fetch(`${API_BASE_URL}/api/auth/register-otp`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identifier: phone })
        });
        const data = await res.json();
        if (data.otp_simulated) {
            simulatedOTPCode = data.otp_simulated;
            document.getElementById("otp-code-display").innerText = data.otp_simulated;
        }
        openModal("modal-otp");
    } catch (err) {
        // Fallback for hackathon demo preview
        document.getElementById("otp-code-display").innerText = "123456";
        openModal("modal-otp");
    }
}

async function submitOTPVerification() {
    const inputOtp = document.getElementById("input-otp").value.trim();
    if (!inputOtp) {
        alert("Please enter the 6-digit OTP code.");
        return;
    }

    closeModal("modal-otp");

    // Proceed to post complaint
    const payload = {
        full_name: document.getElementById("c-name").value.trim(),
        phone_number: pendingOTPPhone,
        email: document.getElementById("c-email").value.trim() || null,
        fraud_type: document.getElementById("c-fraud-type").value,
        transaction_id: document.getElementById("c-txid").value.trim() || null,
        amount: parseFloat(document.getElementById("c-amount").value),
        upi_id: document.getElementById("c-upi").value.trim() || null,
        city: document.getElementById("c-city").value.trim() || "Bhubaneswar",
        state: "Odisha",
        latitude: 20.2961,
        longitude: 85.8245,
        description: document.getElementById("c-desc").value.trim()
    };

    try {
        const res = await fetch(`${API_BASE_URL}/api/complaints`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to register complaint");

        alert(`✅ Cybercrime Complaint Registered Successfully!\n\nUnique Complaint ID: ${data.complaintId}\nStatus: Under Review\nAssigned Authority: Cyber Authority`);

        // Add to Citizen's My Complaints tab
        renderCitizenComplaint(data);
        switchCitizenTab("my-tab");
        document.getElementById("form-complaint").reset();

    } catch (err) {
        alert("Error registering complaint: " + err.message);
    }
}

function switchCitizenTab(tabId) {
    document.querySelectorAll("#screen-citizen .tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll("#screen-citizen .tab-content").forEach(c => c.classList.remove("active"));

    if (tabId === "file-tab") {
        document.querySelectorAll("#screen-citizen .tab-btn")[0].classList.add("active");
        document.getElementById("file-tab").classList.add("active");
    } else {
        document.querySelectorAll("#screen-citizen .tab-btn")[1].classList.add("active");
        document.getElementById("my-tab").classList.add("active");
    }
}

function renderCitizenComplaint(c) {
    const list = document.getElementById("citizen-complaint-list");
    if (list.querySelector("p")) list.innerHTML = "";

    const item = document.createElement("div");
    item.className = "complaint-item";
    item.innerHTML = `
        <div class="ci-header">
            <span class="ci-id">${c.complaintId}</span>
            <span class="ci-amt">₹${parseFloat(c.amount || 25000).toLocaleString()}</span>
        </div>
        <div class="ci-title">${c.fraudType || 'UPI Fraud'}</div>
        <div class="ci-footer">
            <span>Status: <b class="badge badge-status">${c.status || 'Under Review'}</b></span>
            <span>Routed to Cyber Authority</span>
        </div>
    `;
    list.prepend(item);
}

// Authority Complaints Fetch & Rendering
async function fetchComplaints(preserveSelectedId = null) {
    try {
        const res = await fetch(`${API_BASE_URL}/api/complaints`);
        const data = await res.json();
        complaintsData = data;
        renderComplaintList(data);

        // Calculate Stats
        document.getElementById("metric-total").innerText = data.length;
        document.getElementById("metric-high").innerText = data.filter(c => c.riskLevel === "HIGH").length;

        // Auto select complaint while preserving currently active selection
        if (data.length > 0) {
            const targetId = preserveSelectedId || (activeComplaint ? activeComplaint.complaintId : null);
            const selectedCase = targetId ? data.find(c => c.complaintId === targetId) : (data.find(c => c.complaintId === "CMP-2026-1001") || data[0]);
            if (selectedCase) {
                selectComplaint(selectedCase.complaintId);
            }
        }
    } catch (e) {
        console.error("Error fetching complaints:", e);
    }
}

function renderComplaintList(items) {
    const container = document.getElementById("complaints-scroll-list");
    if (!container) return;

    container.innerHTML = "";
    if (items.length === 0) {
        container.innerHTML = `<p class="text-muted" style="padding: 20px;">No matching complaints found.</p>`;
        return;
    }

    items.forEach(c => {
        const div = document.createElement("div");
        div.className = `complaint-item ${activeComplaint && activeComplaint.complaintId === c.complaintId ? 'selected' : ''}`;
        div.onclick = () => selectComplaint(c.complaintId);

        const badgeClass = c.riskLevel === "HIGH" ? "badge-danger" : (c.riskLevel === "MEDIUM" ? "badge-warning" : "badge-success");

        div.innerHTML = `
            <div class="ci-header">
                <span class="ci-id">${c.complaintId}</span>
                <span class="ci-amt">₹${c.amount.toLocaleString()}</span>
            </div>
            <div class="ci-title">${c.fraudType}</div>
            <div class="ci-footer">
                <span>Risk: <b class="badge ${badgeClass}">${c.riskLevel}</b></span>
                <span>Status: ${c.status}</span>
            </div>
        `;
        container.appendChild(div);
    });
}

function handleSearch() {
    const query = document.getElementById("search-input").value.toLowerCase().trim();
    if (!query) {
        renderComplaintList(complaintsData);
        return;
    }

    const filtered = complaintsData.filter(c => 
        c.complaintId.toLowerCase().includes(query) ||
        (c.upiIdMasked && c.upiIdMasked.toLowerCase().includes(query)) ||
        (c.phoneNumberMasked && c.phoneNumberMasked.includes(query)) ||
        c.fraudType.toLowerCase().includes(query)
    );

    renderComplaintList(filtered);
}

// Case Details Inspector View
async function selectComplaint(complaintId) {
    try {
        const res = await fetch(`${API_BASE_URL}/api/complaints/${complaint_id_encode(complaintId)}`);
        const c = await res.json();
        activeComplaint = c;

        // Re-render list selection border
        document.querySelectorAll(".complaint-item").forEach(el => {
            if (el.querySelector(".ci-id").innerText === complaintId) el.classList.add("selected");
            else el.classList.remove("selected");
        });

        document.getElementById("case-detail-empty").style.display = "none";
        document.getElementById("case-detail-content").style.display = "block";

        // Fill Data
        document.getElementById("detail-cmp-id").innerText = c.complaintId;
        document.getElementById("detail-status").innerText = c.status;
        document.getElementById("detail-fraud-title").innerText = `${c.fraudType} - ₹${c.amount.toLocaleString()}`;
        document.getElementById("detail-timestamp").innerText = `Filed ${c.timestamp.substring(0, 10)} by ${c.fullName}`;

        document.getElementById("detail-phone").innerText = c.phoneNumberMasked || "+91 98****3210";
        document.getElementById("detail-upi").innerText = c.upiIdMasked || "N/A";
        document.getElementById("detail-txid").innerText = c.transactionId || "TXN-88421";
        document.getElementById("detail-city").innerText = `${c.city}, ${c.state}`;

        // AI Score
        const riskObj = c.prediction || { riskScore: 0.87, riskLevel: "HIGH", confidence: 0.89, status: "Pending Verification" };
        document.getElementById("detail-risk-score").innerText = riskObj.riskScore;
        document.getElementById("detail-risk-level").innerText = riskObj.riskLevel;
        document.getElementById("detail-confidence").innerText = `${Math.round((riskObj.confidence || 0.85) * 100)}%`;
        document.getElementById("prediction-verify-status").innerText = `Status: ${riskObj.status || "Pending Verification"}`;

        const circle = document.getElementById("detail-risk-circle");
        const scoreElem = document.getElementById("detail-risk-score");
        if (riskObj.riskLevel === "HIGH") {
            circle.style.borderColor = "#f43f5e";
            scoreElem.style.color = "#f43f5e";
        } else if (riskObj.riskLevel === "MEDIUM") {
            circle.style.borderColor = "#f59e0b";
            scoreElem.style.color = "#f59e0b";
        } else {
            circle.style.borderColor = "#10b981";
            scoreElem.style.color = "#10b981";
        }

        // Status Select
        document.getElementById("status-select").value = c.status;

        // Similar cases
        const simList = document.getElementById("similar-cases-list");
        simList.innerHTML = "";
        if (c.relatedCases && c.relatedCases.length > 0) {
            c.relatedCases.forEach(rc => {
                simList.innerHTML += `
                    <div class="similar-item" style="display:flex; justify-content:space-between; margin-top:6px; font-size:0.85rem;">
                        <span class="badge badge-id">${rc.complaintId}</span>
                        <span class="badge badge-sm badge-warning">${rc.similarityReason}</span>
                    </div>
                `;
            });
        } else {
            simList.innerHTML = `<span class="text-muted" style="font-size:0.8rem;">No related complaints detected for this entity.</span>`;
        }

    } catch (e) {
        console.error("Error selecting complaint:", e);
    }
}

function complaint_id_encode(id) {
    return encodeURIComponent(id);
}

// Update Case Status
async function updateCaseStatus() {
    if (!activeComplaint) return;
    const newStatus = document.getElementById("status-select").value;

    try {
        const res = await fetch(`${API_BASE_URL}/api/complaints/${activeComplaint.complaintId}/status`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus, notes: "Updated by authority user" })
        });
        if (res.ok) {
            document.getElementById("detail-status").innerText = newStatus;
            showToastAlert("Status Updated", `Complaint ${activeComplaint.complaintId} changed to ${newStatus}`);
            fetchComplaints(activeComplaint.complaintId);
        }
    } catch (e) {
        alert("Failed to update status");
    }
}

// AI Verification
async function verifyPrediction(statusVal) {
    if (!activeComplaint) return;
    try {
        const res = await fetch(`${API_BASE_URL}/api/predictions/${activeComplaint.complaintId}/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: statusVal, notes: "Verified by investigator" })
        });
        const data = await res.json();
        document.getElementById("prediction-verify-status").innerText = `Status: ${statusVal}`;
        alert(`Prediction marked as '${statusVal}'`);
    } catch (e) {
        alert("Error verifying prediction");
    }
}

// Bank Transaction Lookup Modal
async function lookupBankTransaction() {
    if (!activeComplaint) return;
    const txId = activeComplaint.transactionId || "TXN-88421";

    try {
        const res = await fetch(`${API_BASE_URL}/api/transactions/${txId}`);
        const tx = await res.json();

        const content = document.getElementById("bank-modal-content");
        content.innerHTML = `
            <div style="display:flex; flex-direction:column; gap:12px; font-size:0.95rem;">
                <div class="entity-row">
                    <span class="entity-lbl">Transaction Reference:</span>
                    <span class="entity-val highlight">${tx.transactionId}</span>
                </div>
                <div class="entity-row">
                    <span class="entity-lbl">Sender Account (Masked):</span>
                    <span class="entity-val masked">${tx.senderAccountMasked}</span>
                </div>
                <div class="entity-row">
                    <span class="entity-lbl">Receiver UPI ID (Masked):</span>
                    <span class="entity-val masked">${tx.receiverUpiMasked}</span>
                </div>
                <div class="entity-row">
                    <span class="entity-lbl">Amount:</span>
                    <span class="entity-val" style="color:#34d399; font-weight:700;">₹${tx.amount.toLocaleString()}</span>
                </div>
                <div class="entity-row">
                    <span class="entity-lbl">Timestamp:</span>
                    <span class="entity-val">${tx.timestamp}</span>
                </div>
                <div class="entity-row">
                    <span class="entity-lbl">ATM / Cash-Out Location:</span>
                    <span class="entity-val">${tx.atmLocation}</span>
                </div>
                <div class="entity-row">
                    <span class="entity-lbl">Transaction Status:</span>
                    <span class="badge badge-danger">${tx.status}</span>
                </div>
            </div>
        `;

        openModal("modal-bank-txn");
    } catch (e) {
        alert("Could not retrieve bank transaction details.");
    }
}

// Leaflet GIS High-Risk Cash-Out Map Integration
function initLeafletMap() {
    if (leafletMap) return;

    const mapContainer = document.getElementById("gis-map");
    if (!mapContainer) return;

    // Center on Bhubaneswar (20.2961, 85.8245)
    leafletMap = L.map("gis-map").setView([20.2961, 85.8245], 12);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(leafletMap);
}

async function fetchGISLocations() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/risk-locations`);
        const locations = await res.json();
        renderMapMarkers(locations);
    } catch (e) {
        console.error("GIS fetch error:", e);
    }
}

function renderMapMarkers(locations) {
    if (!leafletMap) return;

    // Clear existing markers
    mapMarkers.forEach(m => m.remove());
    mapMarkers = [];

    locations.forEach(loc => {
        const color = loc.riskLevel === "HIGH" || loc.riskLevel === "CRITICAL" ? "#f43f5e" : (loc.riskLevel === "MEDIUM" ? "#f59e0b" : "#10b981");

        const circleMarker = L.circleMarker([loc.latitude, loc.longitude], {
            radius: 12,
            fillColor: color,
            color: "#fff",
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
        }).addTo(leafletMap);

        const popupContent = `
            <div style="font-family: 'Outfit', sans-serif; color: #111; padding: 4px;">
                <h4 style="margin: 0 0 6px 0; color: ${color};">${loc.name}</h4>
                <div><b>City:</b> ${loc.city}, ${loc.state}</div>
                <div><b>Predicted Risk:</b> <span style="font-weight:700; color: ${color};">${loc.riskLevel} (${loc.riskScore})</span></div>
                <div><b>Related Cases Count:</b> ${loc.relatedCasesCount}</div>
                <div><b>Suspicious Tx Count:</b> ${loc.suspiciousTxCount}</div>
                <div><b>Last Tx Time:</b> ${loc.lastTxTime}</div>
                <hr style="margin: 6px 0; border: none; border-top: 1px solid #ddd;">
                <small style="color: #666; font-style: italic;">* Decision-support prediction of potential cash-out area.</small>
            </div>
        `;

        circleMarker.bindPopup(popupContent);
        mapMarkers.push(circleMarker);
    });
}
