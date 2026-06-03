const API_URL = "http://localhost:8000";

/* -------------------------------
Helpers
-------------------------------- */

function getPublishedAt() {
return `r${document.getElementById("publishedAt").value}`;
}

function getKeywords() {
return document
.getElementById("keywords")
.value
.split("\n")
.map(k => k.trim())
.filter(Boolean);
}

function buildScrapePayload() {
return {
keywords: getKeywords(),
location: document.getElementById("location").value,

```
    experience_levels: [
        "entry-level",
        "associate"
    ],

    work_types: [
        "remote"
    ],

    published_at: getPublishedAt(),

    max_items: Number(
        document.getElementById("maxItems").value
    ),

    min_employees: Number(
        document.getElementById("minEmployees").value
    ),

    max_employees: Number(
        document.getElementById("maxEmployees").value
    )
};
```

}

function setRunId(runId) {
document.getElementById("runId").value = runId;
}

function showStatus(data) {
document.getElementById("statusOutput").textContent =
JSON.stringify(data, null, 4);
}

/* -------------------------------
Generic POST Request
-------------------------------- */

async function postRequest(endpoint, payload) {
try {

```
    const response = await fetch(
        `${API_URL}${endpoint}`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        }
    );

    if (!response.ok) {
        throw new Error(
            `Server Error (${response.status})`
        );
    }

    return await response.json();

} catch (error) {
    console.error(error);
    alert(error.message);
    return null;
}
```

}

/* -------------------------------
Run Scraper
-------------------------------- */

async function runPipeline() {

```
const payload = buildScrapePayload();

const data = await postRequest(
    "/run-pipeline",
    payload
);

if (!data) return;

setRunId(data.run_id);

alert(
    `Pipeline Started\n\nRun ID: ${data.run_id}`
);
```

}

/* -------------------------------
Run Scoring
-------------------------------- */

async function runScoring() {

```
const payload = {
    job_id:
        document.getElementById("jobId").value
        || null
};

const data = await postRequest(
    "/run-scoring",
    payload
);

if (!data) return;

setRunId(data.run_id);

alert(
    `Scoring Started\n\nRun ID: ${data.run_id}`
);
```

}

/* -------------------------------
Run Full Pipeline
-------------------------------- */

async function runFull() {

```
const payload = buildScrapePayload();

const data = await postRequest(
    "/run-full",
    payload
);

if (!data) return;

setRunId(data.run_id);

alert(
    `Full Pipeline Started\n\nRun ID: ${data.run_id}`
);
```

}

/* -------------------------------
Check Status
-------------------------------- */

async function checkStatus() {

```
const runId =
    document.getElementById("runId").value;

if (!runId) {
    alert("Please enter a Run ID");
    return;
}

try {

    const response = await fetch(
        `${API_URL}/status/${runId}`
    );

    if (!response.ok) {
        throw new Error(
            `Run ID not found`
        );
    }

    const data = await response.json();

    showStatus(data);

    return data;

} catch (error) {

    console.error(error);

    document.getElementById("statusOutput")
        .textContent = error.message;
}
```

}

/* -------------------------------
Auto Refresh Status
-------------------------------- */

let refreshInterval = null;

function startAutoRefresh() {

```
if (refreshInterval) {
    clearInterval(refreshInterval);
}

refreshInterval = setInterval(
    async () => {

        const data =
            await checkStatus();

        if (!data) return;

        if (
            data.status === "done" ||
            data.status === "error"
        ) {
            clearInterval(refreshInterval);
        }

    },
    5000
);
```

}

function stopAutoRefresh() {

```
if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
}
```

}
