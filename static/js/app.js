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
    const data = { original_text: original, modified_text: modified };
    const v1El = document.getElementById('video1-prompt-text');
    const v2El = document.getElementById('video2-prompt-text');
    if (v1El) data.video1_prompt = v1El.value;
    if (v2El) data.video2_prompt = v2El.value;
    const result = await api('/api/scripts/' + scriptId, 'PUT', data);
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

// === Score viral potential ===
async function scoreScript(scriptId) {
    const display = document.getElementById('viral-score-display');
    if (display) display.innerHTML = '<span style="font-size: 14px; color: #9ca3af;">Scoring...</span>';
    const result = await api('/api/scripts/' + scriptId + '/score', 'POST');
    if (result && result.ok) {
        const s = result.viral_score;
        let color = '#9ca3af', label = 'LOW';
        if (s >= 70) { color = '#16a34a'; label = 'HIGH POTENTIAL'; }
        else if (s >= 50) { color = '#ca8a04'; label = 'MODERATE'; }
        if (display) display.innerHTML = '<span style="font-size:32px;font-weight:800;color:' + color + ';">' + s + '</span><span style="font-size:12px;color:' + color + ';display:block;">' + label + '</span>';
        toast('Scored: ' + s + '/100', 'success');
    } else {
        toast('Scoring failed', 'error');
    }
}

// === Classify script ===
async function classifyScript(scriptId) {
    const badge = document.getElementById('character-badge');
    if (badge) badge.innerHTML = '<span class="status-badge status-queued" style="font-size: 13px; padding: 6px 12px;">Classifying...</span>';
    const result = await api('/api/scripts/' + scriptId + '/classify', 'POST');
    if (result && result.ok) {
        const labels = {
            grandpa: {emoji: '&#x1F474;', name: 'Wall Street Grandpa', bg: 'rgba(234,179,8,0.1)', color: '#B45309'},
            techguy: {emoji: '&#x1F468;&#x200D;&#x1F4BB;', name: 'IT Tech Guy', bg: 'rgba(59,130,246,0.1)', color: '#2563EB'},
            cartoon: {emoji: '&#x1F3AC;', name: 'Cartoon', bg: 'rgba(168,85,247,0.1)', color: '#7C3AED'},
        };
        const l = labels[result.character_type] || labels.cartoon;
        if (badge) badge.innerHTML = '<span class="status-badge" style="background:' + l.bg + '; color:' + l.color + '; font-size: 13px; padding: 6px 12px;">' + l.emoji + ' ' + l.name + '</span>';
        toast('Classified as ' + result.character_type, 'success');
    } else {
        toast('Classification failed', 'error');
    }
}

// === Assign script ===
async function assignScript(scriptId, assignee) {
    const result = await api('/api/scripts/' + scriptId + '/assign', 'POST', { assigned_to: assignee });
    if (result && result.ok) {
        toast(assignee ? 'Assigned to ' + assignee : 'Unassigned', 'success');
        location.reload();
    } else {
        toast('Assignment failed', 'error');
    }
}

// === Production status ===
async function updateProduction(scriptId, status) {
    const result = await api('/api/scripts/' + scriptId + '/production', 'POST', { production_status: status });
    if (result && result.ok) {
        toast(status ? 'Status: ' + status : 'Status cleared', 'success');
        location.reload();
    } else {
        toast('Update failed', 'error');
    }
}

// === Toggle publish ===
async function togglePublish(scriptId, platform) {
    const result = await api('/api/scripts/' + scriptId + '/publish', 'POST', { platform: platform });
    if (result && result.ok) {
        toast(result.published ? platform + ' published' : platform + ' unpublished', 'success');
        location.reload();
    } else {
        toast('Publish toggle failed', 'error');
    }
}

// === Generate video prompts (split into Video 1 + Video 2) ===
async function generatePrompt(scriptId) {
    const btn = document.getElementById('generate-prompt-btn');

    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin w-3 h-3 mr-1" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.3"/><path d="M12 2a10 10 0 0110 10" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>Generating...';

    const result = await api('/api/scripts/' + scriptId + '/generate-prompt', 'POST');
    if (result && result.ok) {
        const v1 = document.getElementById('video1-prompt-text');
        const v2 = document.getElementById('video2-prompt-text');
        const v3 = document.getElementById('video3-prompt-text');
        if (v1) v1.value = result.video1_prompt;
        if (v2) v2.value = result.video2_prompt;
        if (v3) v3.value = result.video3_prompt || '';
        // Show ready badges
        const b1 = document.getElementById('v1-ready-badge');
        const b2 = document.getElementById('v2-ready-badge');
        const b3 = document.getElementById('v3-ready-badge');
        if (b1) b1.style.display = 'inline-flex';
        if (b2) b2.style.display = 'inline-flex';
        if (b3 && result.video3_prompt) b3.style.display = 'inline-flex';
        toast('Video prompts generated!', 'success');
    } else {
        toast('Prompt generation failed', 'error');
    }
    btn.disabled = false;
    btn.innerHTML = '<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>Generate Prompts';
}

// === Cinema Studio: Generate Video ===
async function generateVideo(scriptId, videoNumber) {
    const avatarId = document.getElementById('cs-avatar')?.value;
    if (!avatarId) { toast('Select an avatar first', 'error'); return; }

    const btn = document.getElementById('cs-gen-v' + videoNumber);
    if (btn) { btn.disabled = true; btn.innerHTML = '<svg class="animate-spin w-3 h-3 mr-1" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.3"/><path d="M12 2a10 10 0 0110 10" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>Starting...'; }

    const body = {
        video_number: videoNumber,
        avatar_id: parseInt(avatarId),
        model_id: document.getElementById('cs-model')?.value || 'higgsfield-ai/dop/standard',
        duration: parseInt(document.getElementById('cs-duration')?.value || '5'),
        aspect_ratio: document.getElementById('cs-ratio')?.value || '9:16',
        camera_movement: document.getElementById('cs-camera')?.value || '',
        sound: document.getElementById('cs-sound')?.checked || false,
        slow_motion: document.getElementById('cs-slowmo')?.checked || false,
    };

    const result = await api('/api/scripts/' + scriptId + '/generate-video', 'POST', body);
    if (result && result.ok && result.generation_id) {
        toast('Video ' + videoNumber + ' generation started!', 'info');
        const area = document.getElementById('cs-v' + videoNumber + '-area');
        if (area) area.style.display = 'block';
        updateVideoStatus(videoNumber, 'queued');
        pollVideoStatus(scriptId, result.generation_id, videoNumber);
    } else {
        toast('Generation failed: ' + (result?.detail || result?.error || 'Unknown error'), 'error');
    }
    if (btn) { btn.disabled = false; btn.innerHTML = '<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/></svg>Generate Video ' + videoNumber; }
}

function updateVideoStatus(videoNumber, status) {
    const badge = document.getElementById('cs-v' + videoNumber + '-status');
    if (!badge) return;
    badge.textContent = status;
    badge.className = 'status-badge ' + (
        status === 'completed' ? 'status-completed' :
        status === 'failed' || status === 'nsfw' ? 'status-failed' :
        status === 'in_progress' ? 'status-running' : 'status-queued'
    );
}

function pollVideoStatus(scriptId, generationId, videoNumber) {
    // Store generation ID for subtitle button
    window['_csV' + videoNumber + 'GenId'] = generationId;

    const interval = setInterval(async () => {
        const result = await api('/api/scripts/' + scriptId + '/video-status/' + generationId);
        if (!result) return;

        updateVideoStatus(videoNumber, result.status);

        if (result.status === 'completed' && result.video_url) {
            clearInterval(interval);
            const player = document.getElementById('cs-v' + videoNumber + '-player');
            const video = document.getElementById('cs-v' + videoNumber + '-video');
            const download = document.getElementById('cs-v' + videoNumber + '-download');
            if (player) player.style.display = 'block';
            if (video) video.src = result.video_url;
            if (download) download.href = result.video_url;
            toast('Video ' + videoNumber + ' ready!', 'success');

            // Show subtitle button or start polling if auto-triggered
            showSubtitleUI(scriptId, generationId, videoNumber, result.subtitle_status || '');
        } else if (result.status === 'failed' || result.status === 'nsfw') {
            clearInterval(interval);
            toast('Video ' + videoNumber + ' failed: ' + (result.error || result.status), 'error');
        }
    }, 3000);
}

// === Cinema Studio: Load Avatars dropdown + thumbnail strip ===
async function loadAvatarsDropdown() {
    const select = document.getElementById('cs-avatar');
    if (!select) return;
    const data = await api('/api/avatars');
    if (!data || !Array.isArray(data)) return;

    // Populate hidden select
    data.forEach(a => {
        if (a.image_url) {
            const opt = document.createElement('option');
            opt.value = a.id;
            opt.textContent = a.name + (a.character_type ? ' (' + a.character_type + ')' : '');
            select.appendChild(opt);
        }
    });

    // Build avatar thumbnail strip
    const thumbs = document.getElementById('cs-avatar-thumbs');
    if (!thumbs) return;
    const avatarsWithImage = data.filter(a => a.image_url);
    if (avatarsWithImage.length === 0) {
        thumbs.innerHTML = '<span style="font-size:11px;color:#6b7280;">No actors with images. Go to Avatar Gallery to create one.</span>';
        return;
    }
    thumbs.innerHTML = avatarsWithImage.map((a, i) => {
        return '<div onclick="selectCSAvatar(' + a.id + ', this)" style="cursor:pointer;text-align:center;" class="cs-avatar-opt' + (i === 0 ? ' cs-av-active' : '') + '">' +
            '<div style="width:42px;height:42px;border-radius:8px;overflow:hidden;border:2px solid ' + (i === 0 ? '#c8ff00' : 'rgba(255,255,255,0.1)') + ';transition:all 0.15s;">' +
            '<img src="' + a.image_url + '" alt="' + a.name + '" style="width:100%;height:100%;object-fit:cover;">' +
            '</div>' +
            '<div style="font-size:9px;color:#9ca3af;margin-top:2px;max-width:42px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + a.name + '</div>' +
            '</div>';
    }).join('');

    // Auto-select first avatar
    if (avatarsWithImage.length > 0) {
        select.value = avatarsWithImage[0].id;
    }
}

function selectCSAvatar(id, el) {
    const select = document.getElementById('cs-avatar');
    if (select) select.value = id;
    // Update highlights
    document.querySelectorAll('.cs-avatar-opt div:first-child').forEach(d => d.style.borderColor = 'rgba(255,255,255,0.1)');
    if (el) {
        const thumb = el.querySelector('div:first-child');
        if (thumb) thumb.style.borderColor = '#c8ff00';
    }
}

// === Cinema Studio: Load previous generations ===
async function loadVideoGenerations(scriptId) {
    const data = await api('/api/scripts/' + scriptId + '/video-generations');
    if (!data || !Array.isArray(data) || data.length === 0) return;
    const container = document.getElementById('cs-history');
    const list = document.getElementById('cs-history-list');
    if (!container || !list) return;
    container.style.display = 'block';
    list.innerHTML = data.map(g => {
        const statusClass = g.status === 'completed' ? 'status-completed' : g.status === 'failed' ? 'status-failed' : 'status-queued';
        const subBadge = g.subtitle_status === 'completed' ? '<span class="status-badge status-completed ml-1">Subs</span>' :
                         g.subtitle_status === 'processing' ? '<span class="status-badge status-running ml-1">Subs...</span>' :
                         g.subtitle_status === 'failed' ? '<span class="status-badge status-failed ml-1">Subs failed</span>' : '';
        const subDl = g.subtitle_status === 'completed' ? '<a href="/api/scripts/' + scriptId + '/download-subtitled/' + g.id + '" class="text-green-500 hover:underline mr-2">Subtitled</a>' : '';
        return '<div class="flex items-center justify-between text-xs p-2 bg-gray-50 rounded-lg">' +
            '<div><span class="font-medium text-gray-700">Video ' + g.video_number + '</span> <span class="status-badge ' + statusClass + '">' + g.status + '</span>' + subBadge + '</div>' +
            '<div class="text-gray-400">' + subDl + (g.video_url ? '<a href="' + g.video_url + '" target="_blank" class="text-blue-500 hover:underline mr-2">Watch</a>' : '') + g.model_id.split('/').pop() + ' / ' + g.duration + 's</div>' +
            '</div>';
    }).join('');
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

// === Subtitles ===

function showSubtitleUI(scriptId, generationId, videoNumber, subtitleStatus) {
    const subBtn = document.getElementById('cs-v' + videoNumber + '-sub-btn');
    const subStatus = document.getElementById('cs-v' + videoNumber + '-sub-status');

    if (subtitleStatus === 'processing') {
        if (subBtn) subBtn.style.display = 'none';
        if (subStatus) {
            subStatus.style.display = 'inline-flex';
            subStatus.innerHTML = '<span class="status-badge status-running">Subtitles processing...</span>';
        }
        pollSubtitleStatus(scriptId, generationId, videoNumber);
    } else if (subtitleStatus === 'completed') {
        if (subBtn) subBtn.style.display = 'none';
        _showSubtitledPlayer(scriptId, generationId, videoNumber);
    } else {
        // Show "Add Subtitles" button
        if (subBtn) subBtn.style.display = 'inline-flex';
    }
}

async function addSubtitles(scriptId, generationId, videoNumber) {
    if (!generationId) { toast('No video generation to subtitle', 'error'); return; }

    const btn = document.getElementById('cs-v' + videoNumber + '-sub-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<svg class="animate-spin w-3 h-3 mr-1" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.3"/><path d="M12 2a10 10 0 0110 10" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>Processing...'; }

    const result = await api('/api/scripts/' + scriptId + '/add-subtitles/' + generationId, 'POST');
    if (result && result.ok) {
        toast('Subtitle generation started!', 'info');
        if (btn) btn.style.display = 'none';
        const subStatus = document.getElementById('cs-v' + videoNumber + '-sub-status');
        if (subStatus) {
            subStatus.style.display = 'inline-flex';
            subStatus.innerHTML = '<span class="status-badge status-running">Subtitles processing...</span>';
        }
        pollSubtitleStatus(scriptId, generationId, videoNumber);
    } else {
        toast('Subtitle generation failed: ' + (result?.detail || 'Unknown error'), 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = '<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/></svg>Add Subtitles'; }
    }
}

function pollSubtitleStatus(scriptId, generationId, videoNumber) {
    const interval = setInterval(async () => {
        const result = await api('/api/scripts/' + scriptId + '/subtitle-status/' + generationId);
        if (!result) return;

        if (result.subtitle_status === 'completed') {
            clearInterval(interval);
            const subStatus = document.getElementById('cs-v' + videoNumber + '-sub-status');
            if (subStatus) {
                subStatus.innerHTML = '<span class="status-badge status-completed">Subtitles ready</span>';
            }
            _showSubtitledPlayer(scriptId, generationId, videoNumber);
            toast('Subtitles ready for Video ' + videoNumber + '!', 'success');
        } else if (result.subtitle_status === 'failed') {
            clearInterval(interval);
            const subStatus = document.getElementById('cs-v' + videoNumber + '-sub-status');
            if (subStatus) {
                subStatus.innerHTML = '<span class="status-badge status-failed">Subtitles failed</span>';
            }
            // Re-show button for retry
            const btn = document.getElementById('cs-v' + videoNumber + '-sub-btn');
            if (btn) {
                btn.style.display = 'inline-flex';
                btn.disabled = false;
                btn.innerHTML = '<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/></svg>Retry Subtitles';
            }
            toast('Subtitles failed: ' + (result.subtitle_error || 'Unknown error'), 'error');
        }
    }, 3000);
}

function _showSubtitledPlayer(scriptId, generationId, videoNumber) {
    const downloadUrl = '/api/scripts/' + scriptId + '/download-subtitled/' + generationId;
    const subPlayer = document.getElementById('cs-v' + videoNumber + '-sub-player');
    const subVideo = document.getElementById('cs-v' + videoNumber + '-sub-video');
    const subDownload = document.getElementById('cs-v' + videoNumber + '-sub-download');
    if (subPlayer) subPlayer.style.display = 'block';
    if (subVideo) subVideo.src = downloadUrl;
    if (subDownload) subDownload.href = downloadUrl;
}
