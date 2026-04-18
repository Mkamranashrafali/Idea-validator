const appState = {
    rawIdea: "",
    features: [],
    stage1: null,
    suggestions: [],
    selectedSuggestionIds: new Set(),
    srsMarkdown: "",
    currentUser: null,
    selectedPlanId: "",
};

const stageEls = [
    document.getElementById("stage-0"),
    document.getElementById("stage-1"),
    document.getElementById("stage-2"),
    document.getElementById("stage-3"),
];

const alertsEl = document.getElementById("alerts");

const rawIdeaEl = document.getElementById("rawIdea");
const featuresEl = document.getElementById("features");

const startAnalysisBtn = document.getElementById("startAnalysisBtn");
const toStage2Btn = document.getElementById("toStage2Btn");
const toStage3Btn = document.getElementById("toStage3Btn");
const downloadBtn = document.getElementById("downloadBtn");

const competitorsEl = document.getElementById("competitors");
const marketSummaryEl = document.getElementById("marketSummary");
const differentiationEl = document.getElementById("differentiation");
const suggestionsListEl = document.getElementById("suggestionsList");
const srsPreviewEl = document.getElementById("srsPreview");
const userNameInputEl = document.getElementById("userNameInput");
const saveNameBtnEl = document.getElementById("saveNameBtn");
const metricIdeasEl = document.getElementById("metricIdeas");
const metricStageEl = document.getElementById("metricStage");
const metricSuggestionsEl = document.getElementById("metricSuggestions");
const metricSrsEl = document.getElementById("metricSrs");
const landingScreenEl = document.getElementById("landingScreen");
const processScreenEl = document.getElementById("processScreen");
const navStartBtnEl = document.getElementById("navStartBtn");
const landingStartBtnEl = document.getElementById("landingStartBtn");
const topLoginBtnEl = document.getElementById("topLoginBtn");
const topLogoutBtnEl = document.getElementById("topLogoutBtn");
const topAuthStatusEl = document.getElementById("topAuthStatus");
const authSectionEl = document.getElementById("authSection");

const authModeSignupBtnEl = document.getElementById("authModeSignupBtn");
const authModeLoginBtnEl = document.getElementById("authModeLoginBtn");
const signupFormEl = document.getElementById("signupForm");
const loginFormEl = document.getElementById("loginForm");
const signupEmailEl = document.getElementById("signupEmail");
const signupUsernameEl = document.getElementById("signupUsername");
const signupPasswordEl = document.getElementById("signupPassword");
const signupConfirmPasswordEl = document.getElementById("signupConfirmPassword");
const loginUsernameEl = document.getElementById("loginUsername");
const loginPasswordEl = document.getElementById("loginPassword");
const authFormMessageEl = document.getElementById("authFormMessage");

const pricingPlansEl = document.getElementById("pricingPlans");
const paymentBoxEl = document.getElementById("paymentBox");
const paymentUsernameEl = document.getElementById("paymentUsername");
const paymentPlanEl = document.getElementById("paymentPlan");
const trxIdEl = document.getElementById("trxId");
const paymentScreenshotEl = document.getElementById("paymentScreenshot");
const submitPaymentBtnEl = document.getElementById("submitPaymentBtn");

const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:5000" : "";
const PAGE_MODE = document.body.dataset.pageMode || "home";
const CHECKOUT_PLAN = (document.body.dataset.checkoutPlan || "").trim().toLowerCase();
const NEXT_PATH = (document.body.dataset.nextPath || "").trim();

const screenMap = {
    home: document.getElementById("landingScreen"),
    auth: document.getElementById("authScreen"),
    pricing: document.getElementById("pricingScreen"),
    checkout: document.getElementById("checkoutScreen"),
    workspace: document.getElementById("processScreen"),
};


function showAlert(message, type = "error") {
    const div = document.createElement("div");
    div.className = `alert ${type === "success" ? "alert-success" : "alert-error"}`;
    div.textContent = message;
    alertsEl.innerHTML = "";
    alertsEl.appendChild(div);
}

function clearAlert() {
    alertsEl.innerHTML = "";
}

function showAuthFormMessage(message, type = "error") {
    if (!authFormMessageEl) {
        return;
    }
    authFormMessageEl.classList.remove("error", "success");
    authFormMessageEl.classList.add(type === "success" ? "success" : "error");
    authFormMessageEl.textContent = message;
}

function clearAuthFormMessage() {
    if (!authFormMessageEl) {
        return;
    }
    authFormMessageEl.classList.remove("error", "success");
    authFormMessageEl.textContent = "";
}

function setStage(index) {
    stageEls.forEach((el, i) => el.classList.toggle("active", i === index));

    if (metricStageEl) {
        const labels = ["Input", "Market", "Improvements", "SRS"];
        metricStageEl.textContent = labels[index] || "Input";
    }

    if (metricSrsEl) {
        metricSrsEl.textContent = appState.srsMarkdown ? "Ready" : "Pending";
    }
}

function updateMetrics() {
    if (metricIdeasEl) {
        metricIdeasEl.textContent = appState.rawIdea ? "1" : "0";
    }

    if (metricSuggestionsEl) {
        metricSuggestionsEl.textContent = String(appState.selectedSuggestionIds.size);
    }

    if (metricSrsEl) {
        metricSrsEl.textContent = appState.srsMarkdown ? "Ready" : "Pending";
    }

    if (metricStageEl) {
        const activeIndex = stageEls.findIndex((el) => el?.classList.contains("active"));
        const labels = ["Input", "Market", "Improvements", "SRS"];
        metricStageEl.textContent = labels[activeIndex >= 0 ? activeIndex : 0] || "Input";
    }
}

function openProcessScreen() {
    if (!appState.currentUser) {
        window.location.href = "/auth?next=/workspace";
        return;
    }

    window.location.href = "/workspace";
}

function redirectAfterAuthSuccess() {
    if (!NEXT_PATH) {
        return;
    }

    if (!NEXT_PATH.startsWith("/") || NEXT_PATH.startsWith("//")) {
        return;
    }

    window.location.href = NEXT_PATH;
}

function activateScreen(mode) {
    Object.values(screenMap).forEach((el) => {
        if (!el) {
            return;
        }
        el.classList.remove("active");
    });

    const target = screenMap[mode] || screenMap.home;
    if (target) {
        target.classList.add("active");
    }
}

function parseFeatureInput(value) {
    return value
        .split(/\n|,/)
        .map((item) => item.trim())
        .filter(Boolean);
}

function buildCompetitorReferences() {
    const competitors = appState.stage1?.analysis?.competitors || [];
    if (!Array.isArray(competitors)) {
        return [];
    }

    return competitors
        .map((comp) => ({
            name: String(comp?.name || "").trim(),
            url: String(comp?.url || "").trim(),
            problem: String(comp?.problem || "").trim(),
            solution: String(comp?.solution || "").trim(),
            relationToIdea: String(comp?.relationToIdea || "").trim(),
        }))
        .filter((comp) => comp.name && comp.url);
}

function renderCompetitors(competitors = []) {
    competitorsEl.innerHTML = "";

    if (!competitors.length) {
        competitorsEl.innerHTML = "<p>No competitors returned from analysis.</p>";
        return;
    }

    competitors.forEach((comp) => {
        const card = document.createElement("article");
        card.className = "competitor-card";

        const features = Array.isArray(comp.mainFeatures) ? comp.mainFeatures.join(", ") : "N/A";

        card.innerHTML = `
      <h4>${comp.name || "Unknown"}</h4>
      <a href="${comp.url || "#"}" target="_blank" rel="noopener noreferrer">${comp.url || "No URL"}</a>
      <p><strong>Similarity:</strong> ${comp.similarityScore ?? "N/A"}/10</p>
      <p><strong>Problem:</strong> ${comp.problem || "-"}</p>
      <p><strong>Approach:</strong> ${comp.solution || "-"}</p>
      <p><strong>Features:</strong> ${features || "-"}</p>
      <p><strong>Relation:</strong> ${comp.relationToIdea || "-"}</p>
    `;

        competitorsEl.appendChild(card);
    });
}

function renderSuggestions(suggestions = []) {
    suggestionsListEl.innerHTML = "";

    if (!suggestions.length) {
        suggestionsListEl.innerHTML = "<p>No suggestions returned.</p>";
        return;
    }

    suggestions.forEach((item, idx) => {
        const id = item.id || `sg-${idx + 1}`;
        const wrapper = document.createElement("article");
        wrapper.className = "suggestion-item";

        wrapper.innerHTML = `
      <label>
        <input type="checkbox" data-suggestion-id="${id}" checked>
        <span>
          <strong>${item.title || "Untitled Suggestion"}</strong><br>
          ${item.description || ""}<br>
          <span class="suggestion-type">${item.type || "feature"}</span><br>
          <small>Source: ${item.sourceInspiration || "N/A"}</small>
        </span>
      </label>
    `;

        suggestionsListEl.appendChild(wrapper);
        appState.selectedSuggestionIds.add(id);
    });

    suggestionsListEl.querySelectorAll("input[type='checkbox']").forEach((checkbox) => {
        checkbox.addEventListener("change", (e) => {
            const id = e.target.dataset.suggestionId;
            if (e.target.checked) {
                appState.selectedSuggestionIds.add(id);
            } else {
                appState.selectedSuggestionIds.delete(id);
            }
            updateMetrics();
        });
    });
}

async function postJson(url, body) {
    let res;
    try {
        res = await fetch(`${API_BASE}${url}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
    } catch (_) {
        throw new Error("Could not reach backend API. Start Flask server with 'python app.py' and open http://127.0.0.1:5000.");
    }

    if (!res.ok) {
        let error = "Unknown error";
        try {
            const payload = await res.json();
            error = payload.details || payload.error || error;
            if (payload.error && payload.details) {
                error = `${payload.error}: ${payload.details}`;
            }
        } catch (_) {
            error = `Request failed (${res.status})`;
        }
        throw new Error(error);
    }

    return res.json();
}

async function getJson(url) {
    let res;
    try {
        res = await fetch(`${API_BASE}${url}`);
    } catch (_) {
        throw new Error("Could not reach backend API. Start Flask server with 'python app.py' and open http://127.0.0.1:5000.");
    }

    if (!res.ok) {
        let error = `Request failed (${res.status})`;
        try {
            const payload = await res.json();
            error = payload.error || payload.details || error;
        } catch (_) {
            // Keep fallback error.
        }
        throw new Error(error);
    }

    return res.json();
}

async function postFormData(url, formData) {
    let res;
    try {
        res = await fetch(`${API_BASE}${url}`, {
            method: "POST",
            body: formData,
        });
    } catch (_) {
        throw new Error("Could not reach backend API. Start Flask server with 'python app.py' and open http://127.0.0.1:5000.");
    }

    if (!res.ok) {
        let error = `Request failed (${res.status})`;
        try {
            const payload = await res.json();
            error = payload.error || payload.details || error;
        } catch (_) {
            // Keep fallback error.
        }
        throw new Error(error);
    }

    return res.json();
}

function updateAuthStatus() {
    if (!topAuthStatusEl) {
        return;
    }

    if (!appState.currentUser) {
        topAuthStatusEl.textContent = "Not logged in";
        if (topLoginBtnEl) {
            topLoginBtnEl.classList.remove("is-hidden");
        }
        if (topLogoutBtnEl) {
            topLogoutBtnEl.classList.add("is-hidden");
        }
        return;
    }

    const tier = appState.currentUser.isPremium ? `Premium (${appState.currentUser.planId})` : "Free";
    topAuthStatusEl.textContent = `Logged in as ${appState.currentUser.username} • ${tier} • Idea quota: ${appState.currentUser.ideaQuota}`;

    if (topLoginBtnEl) {
        topLoginBtnEl.classList.add("is-hidden");
    }
    if (topLogoutBtnEl) {
        topLogoutBtnEl.classList.remove("is-hidden");
    }

    if (paymentUsernameEl) {
        paymentUsernameEl.value = appState.currentUser.username;
    }
}

function setAuthMode(mode) {
    const isSignup = mode === "signup";

    if (authModeSignupBtnEl) {
        authModeSignupBtnEl.classList.toggle("active", isSignup);
    }
    if (authModeLoginBtnEl) {
        authModeLoginBtnEl.classList.toggle("active", !isSignup);
    }
    if (signupFormEl) {
        signupFormEl.classList.toggle("active", isSignup);
    }
    if (loginFormEl) {
        loginFormEl.classList.toggle("active", !isSignup);
    }

    clearAuthFormMessage();
}

function renderPricingPlans(plans = []) {
    if (!pricingPlansEl) {
        return;
    }

    pricingPlansEl.innerHTML = "";
    plans.forEach((plan) => {
        const card = document.createElement("article");
        card.className = "plan-card";
        const features = Array.isArray(plan.features) ? plan.features : [];
        const featuresHtml = features.map((item) => `<li>${item}</li>`).join("");
        card.innerHTML = `
            <h3>${plan.name}</h3>
            <p class="plan-price">PKR ${plan.pricePkr.toLocaleString()}</p>
            <p class="plan-meta">${plan.ideaQuota} ideas included</p>
            <ul class="plan-features">${featuresHtml}</ul>
            <button class="btn-primary" type="button" data-plan-id="${plan.id}">Pay Now</button>
        `;
        pricingPlansEl.appendChild(card);
    });

    pricingPlansEl.querySelectorAll("button[data-plan-id]").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const planId = e.currentTarget.dataset.planId;
            window.location.href = `/checkout/${planId}`;
        });
    });
}

startAnalysisBtn.addEventListener("click", async () => {
    try {
        clearAlert();
        startAnalysisBtn.disabled = true;
        startAnalysisBtn.textContent = "Analyzing...";

        const rawIdea = rawIdeaEl.value.trim();
        if (!rawIdea) {
            throw new Error("Please enter your raw idea first.");
        }

        appState.rawIdea = rawIdea;
        appState.features = parseFeatureInput(featuresEl.value);

        const data = await postJson("/api/stage1", {
            rawIdea: appState.rawIdea,
            features: appState.features,
        });

        appState.stage1 = data.structured;

        const competitors = appState.stage1?.analysis?.competitors || [];
        renderCompetitors(competitors);
        marketSummaryEl.textContent = appState.stage1?.analysis?.summary || "No summary available.";
        differentiationEl.textContent = appState.stage1?.analysis?.differentiationFactor || "No differentiation insight available.";

        updateMetrics();
        setStage(1);
        showAlert("Stage 1 complete. Market analysis is ready.", "success");
    } catch (err) {
        showAlert(err.message || "Failed to run Stage 1.");
    } finally {
        startAnalysisBtn.disabled = false;
        startAnalysisBtn.textContent = "Start Analysis";
    }
});

toStage2Btn.addEventListener("click", async () => {
    try {
        clearAlert();
        toStage2Btn.disabled = true;
        toStage2Btn.textContent = "Generating Suggestions...";

        if (!appState.stage1) {
            throw new Error("Stage 1 data missing. Please run analysis first.");
        }

        appState.selectedSuggestionIds.clear();
        updateMetrics();

        const payload = {
            title: appState.stage1.title || "Untitled Product",
            problem: appState.stage1.problem || "",
            solution: appState.stage1.solution || "",
            summary: appState.stage1.analysis?.summary || "",
            competitors: appState.stage1.analysis?.competitors || [],
        };

        const suggestionsData = await postJson("/api/stage2", payload);
        appState.suggestions = Array.isArray(suggestionsData.suggestions) ? suggestionsData.suggestions : [];

        renderSuggestions(appState.suggestions);
        updateMetrics();
        setStage(2);
        showAlert("Stage 2 complete. Choose suggestions and proceed.", "success");
    } catch (err) {
        showAlert(err.message || "Failed to run Stage 2.");
    } finally {
        toStage2Btn.disabled = false;
        toStage2Btn.textContent = "Next";
    }
});

toStage3Btn.addEventListener("click", async () => {
    try {
        clearAlert();
        toStage3Btn.disabled = true;
        toStage3Btn.textContent = "Generating SRS...";

        if (!appState.stage1) {
            throw new Error("Stage 1 data missing.");
        }

        const selectedFeatures = appState.suggestions
            .filter((item, idx) => {
                const id = item.id || `sg-${idx + 1}`;
                return appState.selectedSuggestionIds.has(id);
            })
            .map((item) => `${item.title}: ${item.description}`);

        const finalFeatures = [...appState.features, ...selectedFeatures];

        const payload = {
            title: appState.stage1.title || "Untitled Product",
            problem: appState.stage1.problem || "",
            solution: appState.stage1.solution || "",
            finalFeatures,
            competitorReferences: buildCompetitorReferences(),
        };

        const srsData = await postJson("/api/stage3", payload);
        appState.srsMarkdown = srsData.srsMarkdown || "";

        srsPreviewEl.textContent = appState.srsMarkdown || "No SRS generated.";
        updateMetrics();
        setStage(3);
        showAlert("Stage 3 complete. Your SRS is ready to download.", "success");
    } catch (err) {
        showAlert(err.message || "Failed to generate SRS.");
    } finally {
        toStage3Btn.disabled = false;
        toStage3Btn.textContent = "Next";
    }
});

downloadBtn.addEventListener("click", async () => {
    try {
        clearAlert();
        downloadBtn.disabled = true;
        downloadBtn.textContent = "Preparing Download...";

        if (!appState.srsMarkdown) {
            throw new Error("No SRS available. Generate Stage 3 first.");
        }

        let res;
        try {
            res = await fetch(`${API_BASE}/api/download`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: appState.stage1?.title || "software_requirements_specification",
                    srsMarkdown: appState.srsMarkdown,
                }),
            });
        } catch (_) {
            throw new Error("Could not reach backend API. Start Flask server with 'python app.py' and open http://127.0.0.1:5000.");
        }

        if (!res.ok) {
            throw new Error("Download failed.");
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        const disposition = res.headers.get("Content-Disposition") || "";
        const fileNameMatch = disposition.match(/filename=\"?([^\";]+)\"?/i);
        a.href = url;
        a.download = fileNameMatch ? fileNameMatch[1] : "srs.docx";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        showAlert("SRS downloaded successfully.", "success");
    } catch (err) {
        showAlert(err.message || "Could not download SRS.");
    } finally {
        downloadBtn.disabled = false;
        downloadBtn.textContent = "Download";
    }
});

(async function checkBackendHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        if (!response.ok) {
            throw new Error("Health check failed");
        }
    } catch (_) {
        showAlert("Backend is not reachable. Run 'python app.py' and open http://127.0.0.1:5000.");
    }
})();

if (saveNameBtnEl && userNameInputEl) {
    const existingName = localStorage.getItem("ideaValidatorUserName") || "";
    if (existingName) {
        userNameInputEl.value = existingName;
    }

    saveNameBtnEl.addEventListener("click", () => {
        const userName = userNameInputEl.value.trim();
        if (!userName) {
            showAlert("Please enter your name.");
            return;
        }
        localStorage.setItem("ideaValidatorUserName", userName);
        showAlert(`Welcome, ${userName}.`, "success");
    });
}

async function refreshSession() {
    try {
        const data = await getJson("/api/auth/session");
        appState.currentUser = data.authenticated ? data.user : null;
    } catch (_) {
        appState.currentUser = null;
    }
    updateAuthStatus();
}

async function handleSignup() {
    const email = (signupEmailEl?.value || "").trim();
    const username = (signupUsernameEl?.value || "").trim();
    const password = (signupPasswordEl?.value || "").trim();
    const confirmPassword = (signupConfirmPasswordEl?.value || "").trim();

    if (!email || !username || !password || !confirmPassword) {
        showAuthFormMessage("Email, username, password, and confirm password are required.");
        return;
    }

    if (password !== confirmPassword) {
        showAuthFormMessage("Password and confirm password must match.");
        return;
    }

    const data = await postJson("/api/auth/signup", { email, username, password });
    appState.currentUser = data.user;
    updateAuthStatus();
    showAuthFormMessage("Signup successful. You are now logged in.", "success");
    redirectAfterAuthSuccess();
}

async function handleLogin() {
    const username = (loginUsernameEl?.value || "").trim();
    const password = (loginPasswordEl?.value || "").trim();

    if (!username || !password) {
        showAuthFormMessage("Username and password are required.");
        return;
    }

    const data = await postJson("/api/auth/login", { username, password });
    appState.currentUser = data.user;
    updateAuthStatus();
    showAuthFormMessage("Login successful.", "success");
    redirectAfterAuthSuccess();
}

async function handleLogout() {
    if (!appState.currentUser) {
        showAuthFormMessage("You are not logged in.");
        return;
    }

    await postJson("/api/auth/logout", {});
    appState.currentUser = null;
    updateAuthStatus();
    showAuthFormMessage("Logged out.", "success");
}

async function loadPricing() {
    try {
        const data = await getJson("/api/pricing");
        renderPricingPlans(Array.isArray(data.plans) ? data.plans : []);
    } catch (err) {
        showAlert(err.message || "Could not load pricing.");
    }
}

async function handlePaymentSubmit() {
    if (!appState.currentUser) {
        showAlert("Please login before payment submission.");
        return;
    }

    const username = (paymentUsernameEl?.value || "").trim();
    const trxId = (trxIdEl?.value || "").trim();
    const planId = (paymentPlanEl?.value || appState.selectedPlanId || "growth").trim();
    const screenshotFile = paymentScreenshotEl?.files?.[0];

    if (!username || !trxId || !screenshotFile) {
        showAlert("Username, transaction ID, and screenshot are required.");
        return;
    }

    const formData = new FormData();
    formData.append("username", username);
    formData.append("trxId", trxId);
    formData.append("planId", planId);
    formData.append("screenshot", screenshotFile);

    const data = await postFormData("/api/payment/submit", formData);
    appState.currentUser = data.user;
    updateAuthStatus();
    showAlert("Payment submitted. Premium activated.", "success");
}

updateMetrics();

if (navStartBtnEl) {
    navStartBtnEl.addEventListener("click", openProcessScreen);
}

if (landingStartBtnEl) {
    landingStartBtnEl.addEventListener("click", openProcessScreen);
}

if (topLoginBtnEl) {
    topLoginBtnEl.addEventListener("click", () => {
        window.location.href = "/auth";
    });
}

if (authModeSignupBtnEl) {
    authModeSignupBtnEl.addEventListener("click", () => setAuthMode("signup"));
}

if (authModeLoginBtnEl) {
    authModeLoginBtnEl.addEventListener("click", () => setAuthMode("login"));
}

if (signupFormEl) {
    signupFormEl.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
            clearAuthFormMessage();
            await handleSignup();
        } catch (err) {
            showAuthFormMessage(err.message || "Signup failed.");
        }
    });
}

if (loginFormEl) {
    loginFormEl.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
            clearAuthFormMessage();
            await handleLogin();
        } catch (err) {
            showAuthFormMessage(err.message || "Login failed.");
        }
    });
}

if (topLogoutBtnEl) {
    topLogoutBtnEl.addEventListener("click", async () => {
        try {
            clearAuthFormMessage();
            await handleLogout();
        } catch (err) {
            showAuthFormMessage(err.message || "Logout failed.");
        }
    });
}

if (submitPaymentBtnEl) {
    submitPaymentBtnEl.addEventListener("click", async () => {
        try {
            clearAlert();
            submitPaymentBtnEl.disabled = true;
            submitPaymentBtnEl.textContent = "Submitting...";
            await handlePaymentSubmit();
        } catch (err) {
            showAlert(err.message || "Payment submission failed.");
        } finally {
            submitPaymentBtnEl.disabled = false;
            submitPaymentBtnEl.textContent = "Submit Payment Proof";
        }
    });
}

async function initializeRouteView() {
    await refreshSession();
    await loadPricing();

    if (PAGE_MODE === "workspace" && !appState.currentUser) {
        window.location.href = "/auth";
        return;
    }

    if (PAGE_MODE === "checkout") {
        if (!appState.currentUser) {
            window.location.href = "/auth";
            return;
        }

        if (paymentPlanEl) {
            paymentPlanEl.value = CHECKOUT_PLAN || "growth";
        }

        if (paymentUsernameEl && appState.currentUser?.username) {
            paymentUsernameEl.value = appState.currentUser.username;
        }
    }

    if (PAGE_MODE === "workspace") {
        setStage(0);
        updateMetrics();
    }

    activateScreen(PAGE_MODE);
}

initializeRouteView();
setAuthMode("signup");
