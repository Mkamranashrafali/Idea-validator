const appState = {
  rawIdea: "",
  features: [],
  stage1: null,
  suggestions: [],
  selectedSuggestionIds: new Set(),
  srsMarkdown: "",
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

const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:5000" : "";


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

function setStage(index) {
  stageEls.forEach((el, i) => el.classList.toggle("active", i === index));
}

function parseFeatureInput(value) {
  return value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
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
    };

    const srsData = await postJson("/api/stage3", payload);
    appState.srsMarkdown = srsData.srsMarkdown || "";

    srsPreviewEl.textContent = appState.srsMarkdown || "No SRS generated.";
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
