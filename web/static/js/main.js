/**
 * Support Ticket Triage Agent - UI Frontend
 * Vanilla JavaScript with Fetch API
 */

const UI_CONFIG = {
    MIN_CHARS: 10,
    MAX_CHARS: 5000,
    API_ENDPOINT: "/triage",
    DEBOUNCE_MS: 300,
};

// State management
const state = {
    isLoading: false,
    currentResult: null,
    debounceTimer: null,
};

// DOM elements
const elements = {
    description: document.getElementById("description"),
    charCount: document.getElementById("char-count"),
    maxChars: document.getElementById("max-chars"),
    charCounter: document.querySelector(".char-counter"),
    validationMessage: document.getElementById("validation-message"),
    submitBtn: document.getElementById("submit-btn"),
    buttonText: document.getElementById("button-text"),
    loadingSpinner: document.getElementById("loading-spinner"),
    resultsSection: document.getElementById("results-section"),
    errorSection: document.getElementById("error-section"),
    copyJsonBtn: document.getElementById("copy-json-btn"),
    editBtn: document.getElementById("edit-btn"),
    retryBtn: document.getElementById("retry-btn"),
    resultSummary: document.getElementById("result-summary"),
    resultCategory: document.getElementById("result-category"),
    resultSeverity: document.getElementById("result-severity"),
    resultKnownIssue: document.getElementById("result-known-issue"),
    resultAction: document.getElementById("result-action"),
    kbMatchesCard: document.getElementById("kb-matches-card"),
    kbMatchesList: document.getElementById("kb-matches-list"),
    resultProvider: document.getElementById("result-provider"),
    resultLatency: document.getElementById("result-latency"),
    resultCacheHit: document.getElementById("result-cache-hit"),
    resultRetryUsed: document.getElementById("result-retry-used"),
    resultJson: document.getElementById("result-json"),
    errorMessage: document.getElementById("error-message"),
    errorDetails: document.getElementById("error-details"),
};

// Utility Functions
function debounce(fn, ms) {
    return function (...args) {
        clearTimeout(state.debounceTimer);
        state.debounceTimer = setTimeout(() => fn(...args), ms);
    };
}

function validateDescription(text) {
    const trimmed = text.trim();
    if (trimmed.length === 0) {
        return { valid: false, message: "Description cannot be empty" };
    }
    if (trimmed.length < UI_CONFIG.MIN_CHARS) {
        return {
            valid: false,
            message: `Description must be at least ${UI_CONFIG.MIN_CHARS} characters`,
        };
    }
    if (trimmed.length > UI_CONFIG.MAX_CHARS) {
        return {
            valid: false,
            message: `Description must not exceed ${UI_CONFIG.MAX_CHARS} characters`,
        };
    }
    return { valid: true, message: "" };
}

function sanitizeHTML(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatLatency(ms) {
    if (ms < 1000) {
        return `${ms.toFixed(0)}ms`;
    }
    return `${(ms / 1000).toFixed(2)}s`;
}

function getSeverityClass(severity) {
    const severity_lower = severity.toLowerCase();
    if (severity_lower === "critical") return "severity-badge critical";
    if (severity_lower === "high") return "severity-badge high";
    if (severity_lower === "medium") return "severity-badge medium";
    return "severity-badge low";
}

// Event Handlers
function handleDescriptionInput(e) {
    const text = e.target.value;
    const count = text.length;

    // Update character count
    elements.charCount.textContent = count;

    // Update visual feedback
    if (count > UI_CONFIG.MAX_CHARS * 0.8) {
        elements.charCounter.classList.add("warning");
    } else {
        elements.charCounter.classList.remove("warning", "error");
    }

    if (count > UI_CONFIG.MAX_CHARS) {
        elements.charCounter.classList.add("error");
    }

    // Validate with debounce
    debounceValidate();
}

function debounceValidate() {
    clearTimeout(state.debounceTimer);
    state.debounceTimer = setTimeout(() => {
        const validation = validateDescription(elements.description.value);
        if (validation.valid) {
            elements.validationMessage.className = "validation-message success";
            elements.validationMessage.textContent = "✓ Ready to submit";
        } else {
            elements.validationMessage.className = "validation-message error";
            elements.validationMessage.textContent = "⚠️ " + validation.message;
        }
    }, UI_CONFIG.DEBOUNCE_MS);
}

async function handleSubmit(e) {
    e.preventDefault();

    const text = elements.description.value.trim();
    const validation = validateDescription(text);

    if (!validation.valid) {
        elements.validationMessage.className = "validation-message error";
        elements.validationMessage.textContent = "⚠️ " + validation.message;
        return;
    }

    await submitTicket(text);
}

async function submitTicket(description) {
    state.isLoading = true;
    updateSubmitButtonState();
    hideAllResultSections();

    try {
        const response = await fetch(UI_CONFIG.API_ENDPOINT, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ description }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(
                error.detail?.details ||
                error.detail ||
                `HTTP ${response.status}: ${response.statusText}`
            );
        }

        const data = await response.json();
        state.currentResult = data;
        displayResults(data);
        elements.resultsSection.style.display = "block";
        elements.validationMessage.textContent = "";
    } catch (error) {
        displayError(error.message);
        elements.errorSection.style.display = "block";
    } finally {
        state.isLoading = false;
        updateSubmitButtonState();
    }
}

function displayResults(data) {
    // Summary
    elements.resultSummary.textContent = sanitizeHTML(data.summary || "No summary available");

    // Category and Severity
    elements.resultCategory.textContent = data.category || "Unknown";
    const severityClass = getSeverityClass(data.severity || "Low");
    elements.resultSeverity.className = severityClass;
    elements.resultSeverity.textContent = data.severity || "Unknown";

    // Known Issue
    elements.resultKnownIssue.textContent = data.known_issue ? "✓ Yes" : "✗ No";

    // Suggested Action
    elements.resultAction.textContent = sanitizeHTML(data.suggested_action || "No action suggested");

    // KB Matches
    if (data.kb_matches && data.kb_matches.length > 0) {
        elements.kbMatchesCard.style.display = "block";
        elements.kbMatchesList.innerHTML = data.kb_matches
            .map((match) => renderKBMatch(match))
            .join("");
    } else {
        elements.kbMatchesCard.style.display = "none";
    }

    // Metadata
    if (data.meta) {
        elements.resultProvider.textContent = data.meta.provider || "Unknown";
        elements.resultLatency.textContent = formatLatency(data.meta.latency_ms || 0);
        elements.resultCacheHit.textContent = data.meta.cache_hit ? "✓ Yes" : "✗ No";
        elements.resultRetryUsed.textContent = data.meta.llm_retry_used ? "✓ Yes" : "✗ No";
    }

    // JSON
    elements.resultJson.textContent = JSON.stringify(data, null, 2);
}

function renderKBMatch(match) {
    const sanitizedTitle = sanitizeHTML(match.title || "Untitled");
    const sanitizedSnippet = sanitizeHTML(match.snippet || "No snippet");
    const score = (match.score * 100).toFixed(1);

    return `
        <div class="kb-item">
            <a class="kb-item-title" href="/kb/${match.id}" target="_blank">
                ${sanitizedTitle}
            </a>
            <div class="kb-item-snippet">${sanitizedSnippet}</div>
            <div class="kb-item-score">Relevance: ${score}%</div>
        </div>
    `;
}

function displayError(message) {
    elements.errorMessage.textContent = message || "An unexpected error occurred";
    elements.errorDetails.textContent = "";
}

function hideAllResultSections() {
    elements.resultsSection.style.display = "none";
    elements.errorSection.style.display = "none";
    elements.validationMessage.textContent = "";
}

function updateSubmitButtonState() {
    if (state.isLoading) {
        elements.submitBtn.disabled = true;
        elements.buttonText.style.display = "none";
        elements.loadingSpinner.style.display = "inline-block";
    } else {
        elements.submitBtn.disabled = false;
        elements.buttonText.style.display = "inline";
        elements.loadingSpinner.style.display = "none";
    }
}

function handleCopyJSON() {
    if (!state.currentResult) return;

    const json = JSON.stringify(state.currentResult, null, 2);
    navigator.clipboard
        .writeText(json)
        .then(() => {
            const originalText = elements.copyJsonBtn.textContent;
            elements.copyJsonBtn.textContent = "✓ Copied!";
            setTimeout(() => {
                elements.copyJsonBtn.textContent = originalText;
            }, 2000);
        })
        .catch((err) => console.error("Failed to copy JSON:", err));
}

function handleEdit() {
    // Scroll to textarea and focus
    elements.description.focus();
    elements.description.scrollIntoView({ behavior: "smooth" });
}

function handleRetry() {
    // Clear and retry last submission
    if (state.currentResult) {
        hideAllResultSections();
        const lastDescription = elements.description.value;
        if (lastDescription.trim()) {
            submitTicket(lastDescription.trim());
        }
    }
}

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
    // Set max characters display
    elements.maxChars.textContent = UI_CONFIG.MAX_CHARS;

    // Input event with debounce
    elements.description.addEventListener(
        "input",
        debounce(handleDescriptionInput, 100)
    );

    // Submit
    elements.submitBtn.addEventListener("click", handleSubmit);
    elements.description.addEventListener("keydown", (e) => {
        if (e.ctrlKey && e.key === "Enter") {
            handleSubmit(e);
        }
    });

    // Results actions
    elements.copyJsonBtn.addEventListener("click", handleCopyJSON);
    elements.editBtn.addEventListener("click", handleEdit);
    elements.retryBtn.addEventListener("click", handleRetry);

    // Focus management for accessibility
    elements.submitBtn.addEventListener("focus", () => {
        elements.validationMessage.setAttribute("role", "status");
    });

    // Initial validation message
    elements.validationMessage.textContent = "Describe your issue to get started...";
});
