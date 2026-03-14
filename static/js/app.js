// === API helper ===
async function api(url, method = 'GET', body = null) {
    const opts = { method, headers: {} };
    if (body) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(body);
    }
    try {
        const res = await fetch(url, opts);
        return await res.json();
    } catch (e) {
        console.error('API error:', e);
        toast('Network error', 'error');
        return null;
    }
}

// === Toast ===
function toast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const el = document.createElement('div');
    el.className = 'toast toast-' + type;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateX(100%)';
        el.style.transition = 'all 0.3s';
        setTimeout(() => el.remove(), 300);
    }, 3000);
}

// === Search ===
async function doSearch(query, category = '') {
    if (!query.trim()) return;
    const btn = document.getElementById('search-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<svg class="animate-spin w-4 h-4 mr-2" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.3"/><path d="M12 2a10 10 0 0110 10" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>Searching...'; }
    const result = await api('/api/search', 'POST', { query, category });
    if (result && result.search_id) {
        window.location.href = '/search?search_id=' + result.search_id;
    } else {
        toast(result?.error || 'Search failed', 'error');
        if (btn) { btn.disabled = false; btn.textContent = 'Search'; }
    }
}

// === Extract script with polling ===
async function extractScript(videoId) {
    const btn = document.getElementById('btn-' + videoId);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<svg class="animate-spin w-3 h-3 mr-1" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.3"/><path d="M12 2a10 10 0 0110 10" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>Extracting...';
    }

    const result = await api('/api/scripts/extract/' + videoId, 'POST');
    if (!result || !result.ok) {
        toast('Failed to start extraction', 'error');
        if (btn) { btn.disabled = false; btn.textContent = 'Extract Script'; }
        return;
    }

    if (result.already_done && result.script_id) {
        window.location.href = '/scripts/' + result.script_id;
        return;
    }

    // Poll every 2 seconds
    const pollInterval = setInterval(async () => {
        const status = await api('/api/search/status/' + videoId);
        if (!status) return;

        if (status.status === 'extracted' && status.script_id) {
            clearInterval(pollInterval);
            // Update card
            const card = document.getElementById('card-' + videoId);
            if (card) {
                const btnContainer = btn.parentElement;
                btnContainer.innerHTML = '<a href="/scripts/' + status.script_id + '" class="btn-sm btn-primary flex-1 justify-center">View Script</a>';
            }
            toast('Script extracted!', 'success');
        } else if (status.status === 'failed') {
            clearInterval(pollInterval);
            toast('Extraction failed: ' + (status.error || 'Unknown error'), 'error');
            if (btn) { btn.disabled = false; btn.textContent = 'Retry'; btn.className = 'btn-sm btn-danger flex-1 justify-center'; }
        }
    }, 2000);
}

// === Rewrite script ===
async function rewriteScript(scriptId) {
    const btn = document.getElementById('rewrite-btn');
    const target = document.getElementById('modified-text');

    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin w-4 h-4 mr-2" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.3"/><path d="M12 2a10 10 0 0110 10" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>Rewriting...';

    const result = await api('/api/scripts/' + scriptId + '/rewrite', 'POST');
    if (result && result.ok) {
        target.value = result.modified_text;
        toast('Script rewritten!', 'success');
    } else {
        toast('Rewrite failed', 'error');
    }
    btn.disabled = false;
    btn.innerHTML = '<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>Make Provocative';
}

// === Save script ===
async function saveScript(scriptId) {
    const original = document.getElementById('original-text').value;
    const modified = document.getElementById('modified-text').value;
    const result = await api('/api/scripts/' + scriptId, 'PUT', { original_text: original, modified_text: modified });
    if (result && result.ok) {
        toast('Saved!', 'success');
    } else {
        toast('Save failed', 'error');
    }
}

// === Delete script ===
async function deleteScript(scriptId) {
    if (!confirm('Delete this script?')) return;
    const result = await api('/api/scripts/' + scriptId, 'DELETE');
    if (result && result.ok) {
        toast('Deleted', 'success');
        location.reload();
    }
}

// === Copy to clipboard ===
function copyText(elementId) {
    const el = document.getElementById(elementId);
    const text = el.value || el.textContent;
    navigator.clipboard.writeText(text)
        .then(() => toast('Copied!', 'success'))
        .catch(() => toast('Copy failed', 'error'));
}

// === Presets ===
async function addPreset(category) {
    const input = document.getElementById(category + '-new-preset');
    const query = input.value.trim();
    if (!query) return;
    const result = await api('/api/presets', 'POST', { category, query });
    if (result && result.id) {
        toast('Preset added', 'success');
        location.reload();
    }
}

async function deletePreset(presetId) {
    const result = await api('/api/presets/' + presetId, 'DELETE');
    if (result && result.ok) {
        const el = document.getElementById('preset-' + presetId);
        if (el) el.remove();
        toast('Preset deleted', 'success');
    }
}
