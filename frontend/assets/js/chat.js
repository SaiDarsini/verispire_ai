let activeConvoId = null;

(async () => {
  const user = await initDashboardShell('Chat');
  if (!user) return;

  const params = new URLSearchParams(window.location.search);
  const idFromUrl = params.get('id');
  if (idFromUrl) {
    await openConversation(idFromUrl);
    const prefill = sessionStorage.getItem('prefillPrompt');
    if (prefill) {
      const input = document.getElementById('chat-input');
      input.value = prefill;
      input.dispatchEvent(new Event('input'));
      sessionStorage.removeItem('prefillPrompt');
    }
  } else {
    document.getElementById('chat-input').disabled = false;
  }

  document.getElementById('send-btn').addEventListener('click', sendCurrentMessage);
  const input = document.getElementById('chat-input');
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendCurrentMessage(); }
  });
  input.addEventListener('input', () => {
    document.getElementById('send-btn').disabled = !input.value.trim();
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 160) + 'px';
  });
})();

async function openConversation(id) {
  activeConvoId = id;
  document.getElementById('chat-input').disabled = false;
  try {
    const convo = await Api.getConversation(id);
    renderMessages(convo.messages);
  } catch (err) {
    toast(err.message, 'error');
  }
}

function splitAudit(text) {
  const marker = '<!--VERISPIRE_AUDIT-->';
  const idx = (text || '').indexOf(marker);
  if (idx < 0) return { body: text || '', auditRaw: '' };
  return { body: text.slice(0, idx).trim(), auditRaw: text.slice(idx + marker.length).trim() };
}

function highlightCode(code, lang) {
  let html = escapeHtml(code.replace(/\n$/, ''));
  const strings = [];
  html = html.replace(/(&quot;.*?&quot;|&#39;.*?&#39;)/g, (m) => {
    strings.push(`<span class="tok-str">${m}</span>`);
    return `\u0000S${strings.length - 1}\u0000`;
  });
  html = html.replace(/\b(def|class|return|import|from|as|if|elif|else|for|while|try|except|finally|with|async|await|yield|lambda|pass|break|continue|True|False|None|and|or|not|in|is|new|const|let|var|function|return|typeof|catch)\b/g, '<span class="tok-kw">$1</span>');
  html = html.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="tok-num">$1</span>');
  html = html.replace(/(^|[^:])(\/\/.*$|#.*$)/gm, '$1<span class="tok-cmt">$2</span>');
  html = html.replace(/\u0000S(\d+)\u0000/g, (_, i) => strings[Number(i)]);
  return html;
}

function renderMarkdownTable(block) {
  const lines = block.trim().split('\n').filter(Boolean);
  if (lines.length < 2) return null;
  const splitRow = (line) => line.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
  const header = splitRow(lines[0]);
  const divider = lines[1];
  if (!/^\s*\|?[\s:|-]+\|[\s:|-]+/.test(divider) && !/^[\s|:-]+$/.test(divider)) return null;
  const rows = lines.slice(2).map(splitRow);
  const thead = `<thead><tr>${header.map((h) => `<th>${inlineMarkdown(h)}</th>`).join('')}</tr></thead>`;
  const tbody = `<tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${inlineMarkdown(c)}</td>`).join('')}</tr>`).join('')}</tbody>`;
  return `<div class="md-table-wrap"><table class="md-table">${thead}${tbody}</table></div>`;
}

function inlineMarkdown(html) {
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/(?<!\*)\*(?!\*)(.+?)\*(?!\*)/g, '<em>$1</em>');
  return html;
}

function markdownToHtml(text) {
  const fences = [];
  let src = text || '';
  src = src.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const id = fences.length;
    const language = (lang || 'text').toLowerCase();
    fences.push(
      `<pre class="code-block" data-lang="${escapeHtml(language)}"><div class="code-lang">${escapeHtml(language)}</div><code>${highlightCode(code, language)}</code></pre>`
    );
    return `\u0000FENCE${id}\u0000`;
  });

  src = escapeHtml(src);

  const tableBlocks = [];
  src = src.replace(/(^|\n)((?:\|.+\|(?:\n|$))+)/g, (match, lead, block) => {
    const table = renderMarkdownTable(block.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'));
    if (!table) return match;
    const id = tableBlocks.length;
    tableBlocks.push(table);
    return `${lead}\u0000TABLE${id}\u0000`;
  });

  src = src.replace(/^### (.*$)/gim, '<h4>$1</h4>');
  src = src.replace(/^## (.*$)/gim, '<h3>$1</h3>');
  src = src.replace(/^# (.*$)/gim, '<h2>$1</h2>');
  src = src.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  src = src.replace(/(?<!\*)\*(?!\*)(.+?)\*(?!\*)/g, '<em>$1</em>');
  src = src.replace(/`([^`]+)`/g, '<code>$1</code>');
  src = src.replace(/^&gt; (.*$)/gim, '<blockquote>$1</blockquote>');

  src = src.replace(/(^|\n)([*-] .+(?:\n[*-] .+)*)/g, (match, lead, block) => {
    const items = block.split('\n').map((l) => `<li>${l.replace(/^[*-] /, '')}</li>`).join('');
    return `${lead}<ul>${items}</ul>`;
  });
  src = src.replace(/(^|\n)(\d+\. .+(?:\n\d+\. .+)*)/g, (match, lead, block) => {
    const items = block.split('\n').map((l) => `<li>${l.replace(/^\d+\. /, '')}</li>`).join('');
    return `${lead}<ol>${items}</ol>`;
  });

  src = src.split('\n\n').map((p) => {
    if (p.includes('<h2') || p.includes('<h3') || p.includes('<h4') || p.includes('<ul') || p.includes('<ol') || p.includes('<pre') || p.includes('<blockquote') || p.includes('\u0000TABLE') || p.includes('\u0000FENCE')) {
      return p.replace(/\n/g, '');
    }
    return `<p>${p.replace(/\n/g, '<br>')}</p>`;
  }).join('');

  src = src.replace(/\u0000TABLE(\d+)\u0000/g, (_, i) => tableBlocks[Number(i)]);
  src = src.replace(/\u0000FENCE(\d+)\u0000/g, (_, i) => fences[Number(i)]);
  return src;
}

function parseAuditJson(raw) {
  const m = raw.match(/```json\s*([\s\S]*?)```/);
  if (!m) return null;
  try {
    return JSON.parse(m[1]);
  } catch {
    return null;
  }
}

function statusBadge(status) {
  const s = String(status || 'FAIL').toUpperCase();
  const cls = s === 'PASS' ? 'pass' : s === 'REJECT' ? 'reject' : 'fail';
  return `<span class="verify-badge ${cls}">${escapeHtml(s)}</span>`;
}

function renderAuditTrail(raw) {
  if (!raw) return '';
  const audit = parseAuditJson(raw);
  if (!audit) {
    return `<details class="audit-trail"><summary>Verification Audit Trail</summary><div class="audit-body">${markdownToHtml(raw)}</div></details>`;
  }
  const matrix = audit.confidence_matrix || {};
  const traces = audit.execution_traces || [];
  const sandbox = audit.sandbox_runs || [];
  const conf = matrix.composite_confidence ?? '—';
  const risk = audit.hallucination_risk ?? matrix.hallucination_risk ?? '—';
  const traceRows = traces.map((t) => (
    `<tr><td>${escapeHtml(t.stage || '')}</td><td>${statusBadge(t.status)}</td><td>${escapeHtml(String(t.detail || ''))}</td><td>${escapeHtml(String(t.latency_ms ?? ''))} ms</td></tr>`
  )).join('') || '<tr><td colspan="4">No traces</td></tr>';
  const sandboxRows = sandbox.map((r) => (
    `<tr><td><code>${escapeHtml(r.run_id || '')}</code></td><td>${statusBadge(r.ok ? 'PASS' : (r.timed_out ? 'FAIL' : 'FAIL'))}</td><td>${escapeHtml(String(r.exit_code ?? '—'))}</td><td>${escapeHtml(String(r.duration_ms ?? ''))} ms</td><td>${escapeHtml(String(r.error || 'ok'))}</td></tr>`
  )).join('') || '<tr><td colspan="5">No Python blocks executed</td></tr>';
  const matrixRows = Object.entries(matrix).map(([k, v]) => (
    `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(String(v))}</td></tr>`
  )).join('');

  return `
    <details class="audit-trail">
      <summary>
        ${statusBadge(audit.final_status)}
        <span class="audit-meta">confidence ${escapeHtml(String(conf))}</span>
        <span class="audit-meta">hallucination risk ${escapeHtml(String(risk))}</span>
        <span class="audit-meta">${escapeHtml(String(audit.total_latency_ms ?? ''))} ms</span>
      </summary>
      <div class="audit-body">
        <p class="audit-critique">${escapeHtml(audit.critique || '')}</p>
        <h4>Confidence matrix</h4>
        <div class="md-table-wrap"><table class="md-table"><thead><tr><th>Signal</th><th>Score</th></tr></thead><tbody>${matrixRows}</tbody></table></div>
        <h4>Execution traces</h4>
        <div class="md-table-wrap"><table class="md-table"><thead><tr><th>Stage</th><th>Status</th><th>Detail</th><th>Latency</th></tr></thead><tbody>${traceRows}</tbody></table></div>
        <h4>Sandbox telemetry</h4>
        <div class="md-table-wrap"><table class="md-table"><thead><tr><th>Run</th><th>Status</th><th>Exit</th><th>Duration</th><th>Error</th></tr></thead><tbody>${sandboxRows}</tbody></table></div>
      </div>
    </details>
  `;
}

function renderMessages(messages) {
  const container = document.getElementById('chat-messages-inner');
  if (messages.length === 0) {
    container.innerHTML = `<div class="empty-state"><div class="icon-wrap">✨</div><h4>Ask VeriSpire</h4><p>Every reply is planned, sandboxed when needed, independently verified, and scored for hallucination risk.</p></div>`;
    return;
  }
  container.innerHTML = messages.map((m, i) => renderMessageHtml(m, i)).join('');
  scrollToBottom();
}

function renderMessageHtml(m, i = 0) {
  const isUser = m.role === 'user';
  let content = m.content;
  let routedBadge = '';

  const routeMatch = !isUser && content.match(/^🔀 Routed to (.+?)\n\n([\s\S]*)$/);
  if (routeMatch) {
    routedBadge = `<div class="routed-badge">🔀 Routed to <strong>${escapeHtml(routeMatch[1])}</strong></div>`;
    content = routeMatch[2];
  }

  const { body, auditRaw } = isUser ? { body: content, auditRaw: '' } : splitAudit(content);
  const bubble = isUser ? escapeHtml(body) : markdownToHtml(body);
  const audit = isUser ? '' : renderAuditTrail(auditRaw);

  return `
    <div class="msg-row ${isUser ? 'user' : 'assistant'}" style="animation-delay:${Math.min(i, 6) * 0.04}s">
      <div class="msg-avatar ${isUser ? 'user' : 'assistant'}">${isUser ? '🧑' : 'VS'}</div>
      <div class="msg-stack">
        ${routedBadge}
        <div class="msg-bubble">${bubble}</div>
        ${audit}
      </div>
    </div>
  `;
}

function scrollToBottom() {
  const scrollEl = document.getElementById('chat-messages');
  scrollEl.scrollTop = scrollEl.scrollHeight;
}

async function ensureConversation() {
  if (activeConvoId) return activeConvoId;
  const params = new URLSearchParams(window.location.search);
  const agentKey = params.get('agent') || 'personal';
  const convo = await Api.createConversation({ title: 'New Conversation', agent_key: agentKey });
  activeConvoId = convo.id;
  history.replaceState(null, '', `conversations.html?id=${convo.id}`);
  return activeConvoId;
}

async function sendCurrentMessage() {
  const input = document.getElementById('chat-input');
  const content = input.value.trim();
  if (!content) return;

  const sendBtn = document.getElementById('send-btn');
  input.disabled = true;
  sendBtn.disabled = true;

  try {
    await ensureConversation();
  } catch (err) {
    toast(err.message, 'error');
    input.disabled = false;
    return;
  }

  const container = document.getElementById('chat-messages-inner');
  if (container.querySelector('.empty-state')) container.innerHTML = '';
  container.insertAdjacentHTML('beforeend', renderMessageHtml({ role: 'user', content }));
  scrollToBottom();
  input.value = '';
  input.style.height = 'auto';

  const typingId = 'typing-indicator';
  container.insertAdjacentHTML('beforeend', `
    <div class="msg-row assistant" id="${typingId}">
      <div class="msg-avatar assistant thinking">VS</div>
      <div class="msg-bubble typing-dots"><span></span><span></span><span></span></div>
    </div>
  `);
  scrollToBottom();

  try {
    const reply = await Api.sendMessage(activeConvoId, content);
    document.getElementById(typingId)?.remove();
    await typeOutMessage(container, reply);
    scrollToBottom();
  } catch (err) {
    document.getElementById(typingId)?.remove();
    toast(err.message, 'error');
  } finally {
    input.disabled = false;
    input.focus();
  }
}

function typeOutMessage(container, m) {
  return new Promise((resolve) => {
    const { body } = splitAudit(m.content || '');
    const rowId = `msg-${Date.now()}`;
    container.insertAdjacentHTML('beforeend', `
      <div class="msg-row assistant" id="${rowId}">
        <div class="msg-avatar assistant">VS</div>
        <div class="msg-stack">
          <div class="msg-bubble typing-target"></div>
        </div>
      </div>
    `);
    const target = document.querySelector(`#${rowId} .typing-target`);
    const words = body.split(' ');
    let i = 0;

    function step() {
      i += 4;
      target.textContent = words.slice(0, i).join(' ');
      scrollToBottom();
      if (i < words.length) {
        setTimeout(step, 18);
      } else {
        document.getElementById(rowId).outerHTML = renderMessageHtml(m);
        resolve();
      }
    }
    step();
  });
}
