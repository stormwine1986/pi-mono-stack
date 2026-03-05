const messagesDiv = document.getElementById('messages');
const memoryDiv = document.getElementById('memory-events');
const promptInput = document.getElementById('prompt');
const userIdInput = document.getElementById('user-id');
const tgSwitch = document.getElementById('tg-switch');
const statusDot = document.getElementById('status-dot');

// Load persisted User ID
userIdInput.value = localStorage.getItem('gate_user_id') || 'test-user';

// ── Dkron Jobs ──────────────────────────────────────────────

async function fetchDkronJobs() {
    try {
        const res = await fetch('/api/jobs');
        const jobs = await res.json();
        const container = document.getElementById('job-list-content');
        const failedOnly = document.getElementById('failed-only-switch').checked;

        if (!jobs || jobs.length === 0) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #999;">No jobs found</div>';
            return;
        }

        // Filter jobs if toggle is on
        const filteredJobs = failedOnly ? jobs.filter(job => {
            if (job.last_run) {
                return !(job.last_success && new Date(job.last_success) >= new Date(job.last_run));
            }
            return false;
        }) : jobs;

        if (filteredJobs.length === 0) {
            container.innerHTML = `<div style="padding: 20px; text-align: center; color: #999;">${failedOnly ? 'No failed jobs found' : 'No jobs found'}</div>`;
            return;
        }

        container.innerHTML = filteredJobs.map(job => {
            let lastStatus = 'unknown';
            if (job.last_run) {
                if (job.last_success && new Date(job.last_success) >= new Date(job.last_run)) {
                    lastStatus = 'success';
                } else {
                    lastStatus = 'failed';
                }
            } else if (job.last_success) {
                lastStatus = 'success';
            }

            const statusClass = 'status-' + lastStatus;
            const lastRun = job.last_run ? new Date(job.last_run).toLocaleString() :
                (job.last_success ? 'Success at ' + new Date(job.last_success).toLocaleString() : 'Never');

            return `
                <div class="job-item">
                    <div class="job-header">
                        <span class="job-name">${job.name}</span>
                        <span class="job-status ${statusClass}">${lastStatus.toUpperCase()}</span>
                    </div>
                    <div class="job-meta">
                        <span>Owner: ${job.owner}</span>
                        <span>Last run: ${lastRun}</span>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Failed to fetch Dkron jobs:', err);
    }
}

// ── Job Summaries ──────────────────────────────────────────

async function fetchSummaries() {
    try {
        const res = await fetch('/api/summaries');
        const summaries = await res.json();
        const container = document.getElementById('summary-list');

        if (!summaries || summaries.length === 0) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #999;">No summaries found</div>';
            return;
        }

        container.innerHTML = summaries.map(s => renderSummaryHTML(s)).join('');
    } catch (err) {
        console.error('Failed to fetch summaries:', err);
    }
}

function renderSummaryHTML(s) {
    const time = new Date(s.timestamp).toLocaleString();
    return `
        <div class="job-item">
            <div class="job-header">
                <span class="job-name">${s.job}</span>
                <span style="font-size: 0.7em; color: #999;">${time}</span>
            </div>
            <div style="font-size: 0.85em; color: #444; margin-top: 5px; line-height: 1.4; border-left: 2px solid #2196f3; padding-left: 8px;">
                ${s.summary}
            </div>
        </div>
    `;
}

function appendSummary(s) {
    const container = document.getElementById('summary-list');
    if (container.querySelector('div[style*="color: #999"]')) {
        container.innerHTML = '';
    }
    const div = document.createElement('div');
    div.innerHTML = renderSummaryHTML(s);
    container.insertBefore(div.firstElementChild, container.firstChild);

    // Keep latest 20
    while (container.children.length > 20) {
        container.removeChild(container.lastChild);
    }
}

// ── Telegram Toggle ─────────────────────────────────────────

async function fetchTGStatus() {
    try {
        const res = await fetch('/api/tg-status');
        const data = await res.json();
        tgSwitch.checked = data.enabled;
    } catch (err) {
        console.error('Failed to fetch TG status:', err);
    }
}

async function toggleTG() {
    const enabled = tgSwitch.checked;
    try {
        await fetch('/api/tg-toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
    } catch (err) {
        alert('Failed to toggle TG: ' + err.message);
        tgSwitch.checked = !enabled;
    }
}

// ── Memory Events ───────────────────────────────────────────

function appendMemoryEvent(event) {
    const div = document.createElement('div');
    div.className = 'mem-event ' + event.event;

    const time = new Date(event.timestamp).toLocaleTimeString();
    div.innerHTML = `
        <span class="mem-time">${time} · <span class="mem-user">${event.user_id}</span></span>
        <span class="mem-fact">${event.fact}</span>
        <small style="color: #666; font-size: 0.8em">${event.event} | ID: ${event.memory_id.substring(0, 8)}</small>
    `;

    memoryDiv.insertBefore(div, memoryDiv.firstChild);

    // Keep only latest 10
    while (memoryDiv.children.length > 10) {
        memoryDiv.removeChild(memoryDiv.lastChild);
    }
}

// ── Chat Messages ───────────────────────────────────────────

function appendMessage(text, type, data = null) {
    const div = document.createElement('div');
    div.className = 'message ' + type;
    const content = document.createElement('pre');
    content.textContent = text;
    div.appendChild(content);

    if (data && data.images && data.images.length > 0) {
        data.images.forEach(img => {
            const imgEl = document.createElement('img');
            imgEl.src = img;
            imgEl.style.maxWidth = '200px';
            imgEl.style.display = 'block';
            imgEl.style.marginTop = '10px';
            div.appendChild(imgEl);
        });
    }

    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function send() {
    const prompt = promptInput.value.trim();
    const user_id = userIdInput.value.trim() || 'test-user';
    if (!prompt) return;

    appendMessage('[' + user_id + '] To agent_in: ' + prompt, 'sent');
    promptInput.value = '';

    try {
        const res = await fetch('/api/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, user_id })
        });
        if (!res.ok) throw new Error('Failed to send');
    } catch (err) {
        appendMessage('Error: ' + err.message, 'error');
    }
}

async function resetSession() {
    const user_id = userIdInput.value.trim() || 'test-user';
    if (!confirm('Are you sure you want to reset the session? All history for this user will be cleared.')) return;

    try {
        const res = await fetch('/api/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id })
        });
        if (!res.ok) throw new Error('Failed to reset session');
        appendMessage('Session reset command sent for ' + user_id, 'progress');
        messagesDiv.innerHTML = ''; // Clear local messages
    } catch (err) {
        appendMessage('Error resetting session: ' + err.message, 'error');
    }
}

// ── SSE Connection ──────────────────────────────────────────

function connect() {
    const eventSource = new EventSource('/api/events');

    eventSource.onopen = () => {
        statusDot.className = 'status-dot status-online';
        console.log('SSE Connected');
    };

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.status === 'success') {
            appendMessage('From agent_out: ' + data.response, 'received', data);
        } else if (data.status === 'error') {
            appendMessage('Error from agent_out: ' + data.error, 'error');
        } else if (data.status === 'progress') {
            appendMessage('Progress: ' + data.event + (data.data ? ' ' + JSON.stringify(data.data) : ''), 'progress');
        } else if (data.event && ['ADD', 'UPDATE', 'DELETE'].includes(data.event)) {
            appendMemoryEvent(data);
        } else if (data.type === 'job_summary') {
            appendSummary(data);
        }
    };

    eventSource.onerror = (err) => {
        statusDot.className = 'status-dot status-offline';
        console.error('SSE Error:', err);
        eventSource.close();
        setTimeout(connect, 3000);
    };
}

// ── Init ────────────────────────────────────────────────────

fetchTGStatus();
fetchDkronJobs();
fetchSummaries();
setInterval(fetchDkronJobs, 30000);
connect();
