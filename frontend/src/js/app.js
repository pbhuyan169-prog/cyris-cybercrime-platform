// CYRIS Frontend Application Engine - SIH 2026 Inter-Agency Multi-Persona System

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
    console.log("CYRIS Platform Initializing Inter-Agency Multi-Persona Engine...");
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
    } else if (data.event === "BANK_DETAILS_REQUESTED") {
        showToastAlert(`📩 Bank Info Requested`, `Cyber Cell requested transaction details for ${data.complaintId}`);
        if (currentSelectedAuthority === "BANK_AUTHORITY") {
            triggerQuickResponseAlert("📩 URGENT BANK REQUEST", `Cyber Cell requested transaction details for ${data.complaintId}`, "Approve & Provide Details");
        }
        fetchComplaints(data.complaintId);
    } else if (data.event === "BANK_DETAILS_PROVIDED") {
        showToastAlert(`🏦 Bank Details Provided`, `Bank approved & provided transaction details for ${data.complaintId}`);
        fetchComplaints(data.complaintId);
    } else if (data.event === "NOTIFIED_TO_POLICE") {
        showToastAlert(`🚓 Dispatched to Police`, `Cyber Cell analyzed and notified Police of case ${data.complaintId}`);
        if (currentSelectedAuthority === "POLICE") {
            triggerQuickResponseAlert("🚨 QUICK RESPONSE DISPATCH ALERT", `Case ${data.complaintId} analyzed by Cyber Cell and dispatched to Police!`, "Inspect & Respond Now");
        }
        fetchComplaints(data.complaintId);
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

function triggerQuickResponseAlert(title, desc, buttonText) {
    const qrBanner = document.getElementById("quick-response-banner-box");
    if (!qrBanner) return;
    qrBanner.style.display = "flex";
    const qrTitle = document.getElementById("qr-title");
    const qrDesc = document.getElementById("qr-desc");
    const qrBtn = document.getElementById("qr-action-btn");
    if (qrTitle) qrTitle.innerText = title;
    if (qrDesc) qrDesc.innerText = desc;
    if (qrBtn) qrBtn.innerText = buttonText;
}

// Navigation & Screen Management
function showScreen(screenId) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    const target = document.getElementById(screenId);
    if (target) target.classList.add("active");

    if (screenId === "screen-authority") {
        applyPersonaTheme(currentSelectedAuthority);
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

// Persona Interface Theme Customizer
function applyPersonaTheme(role) {
    const screenAuth = document.getElementById("screen-authority");
    if (!screenAuth) return;

    const roleBadge = document.getElementById("authority-role-badge");
    const titleHeading = document.getElementById("authority-title-heading");
    const subtitleHeading = document.getElementById("authority-subtitle-heading");
    const qrBanner = document.getElementById("quick-response-banner-box");
    const metricLbl1 = document.getElementById("metric-lbl-1");
    const metricLbl2 = document.getElementById("metric-lbl-2");
    const metricLbl3 = document.getElementById("metric-lbl-3");
    const metricLbl4 = document.getElementById("metric-lbl-4");
    const qrIcon = document.getElementById("qr-icon");
    const qrTitle = document.getElementById("qr-title");
    const qrDesc = document.getElementById("qr-desc");
    const qrBtn = document.getElementById("qr-action-btn");

    screenAuth.classList.remove("persona-theme-cyber", "persona-theme-bank", "persona-theme-police");

    if (role === "POLICE") {
        screenAuth.classList.add("persona-theme-police");
        if (roleBadge) { roleBadge.innerText = "POLICE FIELD COMMANDER"; roleBadge.className = "badge badge-sm badge-danger"; }
        if (titleHeading) titleHeading.innerText = "🚓 Police Field Unit Dispatch & Quick Response Console";
        if (subtitleHeading) subtitleHeading.innerText = "Tactical response console displaying cases analyzed by Cyber Cell for immediate field unit dispatch & GIS heatmap.";
        if (metricLbl1) metricLbl1.innerText = "Dispatched Police Cases";
        if (metricLbl2) metricLbl2.innerText = "Critical Response Cases";
        if (metricLbl3) metricLbl3.innerText = "Pending Field Actions";
        if (metricLbl4) metricLbl4.innerText = "Resolved Interceptions";
        if (qrBanner) qrBanner.style.display = "flex";
        if (qrIcon) qrIcon.innerText = "🚨";
        if (qrTitle) qrTitle.innerText = "QUICK RESPONSE DISPATCH ALERT";
        if (qrDesc) qrDesc.innerText = "Cases analyzed by Cyber Cell dispatched for immediate field response.";
        if (qrBtn) qrBtn.innerText = "Inspect & Dispatch Unit Now";

    } else if (role === "BANK_AUTHORITY") {
        screenAuth.classList.add("persona-theme-bank");
        if (roleBadge) { roleBadge.innerText = "BANK NODAL OFFICER"; roleBadge.className = "badge badge-sm badge-success"; }
        if (titleHeading) titleHeading.innerText = "🏦 Nodal Bank Officer — Transaction Inspection Console";
        if (subtitleHeading) subtitleHeading.innerText = "Authorised bank transaction inspection portal. Displays ONLY complaints for which Cyber Cell requested bank details.";
        if (metricLbl1) metricLbl1.innerText = "Incoming Bank Requests";
        if (metricLbl2) metricLbl2.innerText = "High-Value Transactions";
        if (metricLbl3) metricLbl3.innerText = "Pending Info Requests";
        if (metricLbl4) metricLbl4.innerText = "Released Account Records";
        if (qrBanner) qrBanner.style.display = "flex";
        if (qrIcon) qrIcon.innerText = "📩";
        if (qrTitle) qrTitle.innerText = "TRANSACTION DETAIL REQUEST";
        if (qrDesc) qrDesc.innerText = "Cyber Cell requested transaction details for cybercrime complaints.";
        if (qrBtn) qrBtn.innerText = "Approve & Provide Details";

    } else {
        // CYBER_AUTHORITY (default)
        screenAuth.classList.add("persona-theme-cyber");
        if (roleBadge) { roleBadge.innerText = "CYBER CELL CHIEF"; roleBadge.className = "badge badge-sm badge-accent"; }
        if (titleHeading) titleHeading.innerText = "🛡️ Cyber Cell Command & AI Intelligence Center";
        if (subtitleHeading) subtitleHeading.innerText = "Receives registered citizen complaints, requests bank transaction details, runs AI risk analysis, and notifies Police.";
        if (metricLbl1) metricLbl1.innerText = "Total Citizen Complaints";
        if (metricLbl2) metricLbl2.innerText = "High-Risk AI Signals";
        if (metricLbl3) metricLbl3.innerText = "Pending Bank Requests";
        if (metricLbl4) metricLbl4.innerText = "Verified AI Predictions";
        if (qrBanner) qrBanner.style.display = "none";
    }
}

function handleQuickResponseAction() {
    if (complaintsData && complaintsData.length > 0) {
        selectComplaint(complaintsData[0].complaintId);
        showToastAlert("Quick Response Action", `Inspecting case ${complaintsData[0].complaintId}`);
    } else {
        showToastAlert("Queue Clear", "No active quick response cases pending in queue.");
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

        // Show the authority screen FIRST, then apply persona (elements must be in DOM)
        showScreen("screen-authority");
        // applyPersonaTheme is also called inside showScreen — double-call is safe due to null-guards
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

        alert(`✅ Cybercrime Complaint Registered Successfully!\n\nUnique Complaint ID: ${data.complaintId}\nStatus: Under Cyber Cell Review\nAssigned Authority: Cyber Cell`);

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
            <span>Status: <b class="badge badge-status">${c.status || 'Under Cyber Cell Review'}</b></span>
            <span>Assigned to Cyber Cell</span>
        </div>
    `;
    list.prepend(item);
}

// Authority Complaints Fetch & Filtering per Persona
async function fetchComplaints(preserveSelectedId = null) {
    try {
        const roleParam = currentSelectedAuthority ? `?authority_role=${currentSelectedAuthority}` : "";
        const res = await fetch(`${API_BASE_URL}/api/complaints${roleParam}`);
        const data = await res.json();
        complaintsData = data;
        renderComplaintList(data);

        document.getElementById("metric-total").innerText = data.length;
        document.getElementById("metric-high").innerText = data.filter(c => c.riskLevel === "HIGH").length;

        if (data.length > 0) {
            const targetId = preserveSelectedId || (activeComplaint ? activeComplaint.complaintId : null);
            const selectedCase = targetId ? data.find(c => c.complaintId === targetId) : data[0];
            if (selectedCase) {
                selectComplaint(selectedCase.complaintId);
            }
        } else {
            document.getElementById("case-detail-empty").style.display = "block";
            document.getElementById("case-detail-content").style.display = "none";
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
        container.innerHTML = `<p class="text-muted" style="padding: 20px;">No matching cases in this queue.</p>`;
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
                <span>${c.status}</span>
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

// Case Details Inspector View & Persona-based Actions
async function selectComplaint(complaintId) {
    try {
        const res = await fetch(`${API_BASE_URL}/api/complaints/${complaint_id_encode(complaintId)}`);
        const c = await res.json();
        activeComplaint = c;

        document.querySelectorAll(".complaint-item").forEach(el => {
            if (el.querySelector(".ci-id").innerText === complaintId) el.classList.add("selected");
            else el.classList.remove("selected");
        });

        document.getElementById("case-detail-empty").style.display = "none";
        document.getElementById("case-detail-content").style.display = "block";

        document.getElementById("detail-cmp-id").innerText = c.complaintId;
        document.getElementById("detail-status").innerText = c.status;
        document.getElementById("detail-fraud-title").innerText = `${c.fraudType} - ₹${c.amount.toLocaleString()}`;
        document.getElementById("detail-timestamp").innerText = `Filed ${c.timestamp.substring(0, 10)} by ${c.fullName}`;

        document.getElementById("detail-phone").innerText = c.phoneNumberMasked || "+91 98****3210";
        document.getElementById("detail-upi").innerText = c.upiIdMasked || "N/A";
        document.getElementById("detail-txid").innerText = c.transactionId || "TXN-88421";
        document.getElementById("detail-city").innerText = `${c.city}, ${c.state}`;

        // Persona Action Control Toggle
        const btnRequestBank = document.getElementById("btn-request-bank");
        const btnProvideBank = document.getElementById("btn-provide-bank");
        const btnNotifyPolice = document.getElementById("btn-notify-police");

        if (currentSelectedAuthority === "CYBER_AUTHORITY") {
            btnRequestBank.style.display = "inline-block";
            btnNotifyPolice.style.display = "inline-block";
            btnProvideBank.style.display = "none";

            btnRequestBank.innerText = c.bankRequestStatus === "REQUESTED_FROM_BANK" ? "⏳ Bank Info Requested" : (c.bankRequestStatus === "PROVIDED_BY_BANK" ? "✓ Bank Details Received" : "📩 Request Bank Details");
            btnNotifyPolice.innerText = c.policeNotified ? "✓ Notified to Police" : "调度 Notify & Dispatch to Police";
        } else if (currentSelectedAuthority === "BANK_AUTHORITY") {
            btnRequestBank.style.display = "none";
            btnNotifyPolice.style.display = "none";
            btnProvideBank.style.display = "inline-block";

            btnProvideBank.innerText = c.bankRequestStatus === "PROVIDED_BY_BANK" ? "✓ Details Provided to Cyber Cell" : "🏦 Provide Details to Cyber Cell";
        } else if (currentSelectedAuthority === "POLICE") {
            btnRequestBank.style.display = "none";
            btnProvideBank.style.display = "none";
            btnNotifyPolice.style.display = "none";
        }

        // AI Score Display
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

        document.getElementById("status-select").value = c.status;

        // Similar Cases
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

// Persona Inter-Agency Workflow Handlers
async function requestBankDetailsAction() {
    if (!activeComplaint) return;
    try {
        const res = await fetch(`${API_BASE_URL}/api/complaints/${activeComplaint.complaintId}/request-bank-details`, {
            method: "POST"
        });
        const data = await res.json();
        if (res.ok) {
            showToastAlert("📩 Bank Info Requested", `Transaction details requested from Bank for ${activeComplaint.complaintId}`);
            fetchComplaints(activeComplaint.complaintId);
        }
    } catch (e) {
        alert("Error sending bank details request");
    }
}

async function provideBankDetailsAction() {
    if (!activeComplaint) return;
    try {
        const res = await fetch(`${API_BASE_URL}/api/complaints/${activeComplaint.complaintId}/provide-bank-details`, {
            method: "POST"
        });
        const data = await res.json();
        if (res.ok) {
            showToastAlert("🏦 Details Provided", `Transaction details for ${activeComplaint.complaintId} provided to Cyber Cell.`);
            fetchComplaints(activeComplaint.complaintId);
        }
    } catch (e) {
        alert("Error providing bank details");
    }
}

async function notifyPoliceAction() {
    if (!activeComplaint) return;
    try {
        const res = await fetch(`${API_BASE_URL}/api/complaints/${activeComplaint.complaintId}/notify-police`, {
            method: "POST"
        });
        const data = await res.json();
        if (res.ok) {
            showToastAlert("调度 Police Notified", `Complaint ${activeComplaint.complaintId} analyzed & dispatched to Police.`);
            fetchComplaints(activeComplaint.complaintId);
        }
    } catch (e) {
        alert("Error notifying Police");
    }
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

// Leaflet GIS High-Risk Cash-Out Heatmap Integration
function initLeafletMap() {
    if (leafletMap) return;

    const mapContainer = document.getElementById("gis-map");
    if (!mapContainer) return;

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
                <small style="color: #666; font-style: italic;">* Interactive GIS Heatmap hotspot.</small>
            </div>
        `;

        circleMarker.bindPopup(popupContent);
        mapMarkers.push(circleMarker);
    });
}
