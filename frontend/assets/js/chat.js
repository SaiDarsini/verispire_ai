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

function markdownToHtml(text) {
  // Escape HTML first so nothing unsafe slips through, then layer markdown on top.
  let html = escapeHtml(text);

  html = html.replace(/^### (.*$)/gim, '<h4>$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2>$1</h2>');

  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/(?<!\*)\*(?!\*)(.+?)\*(?!\*)/g, '<em>$1</em>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bullet lists
  html = html.replace(/(^|\n)([*-] .+(?:\n[*-] .+)*)/g, (match, lead, block) => {
    const items = block.split('\n').map(l => `<li>${l.replace(/^[*-] /, '')}</li>`).join('');
    return `${lead}<ul>${items}</ul>`;
  });

  // Numbered lists
  html = html.replace(/(^|\n)(\d+\. .+(?:\n\d+\. .+)*)/g, (match, lead, block) => {
    const items = block.split('\n').map(l => `<li>${l.replace(/^\d+\. /, '')}</li>`).join('');
    return `${lead}<ol>${items}</ol>`;
  });

  // Paragraph breaks (double newline) -> real breaks; single newline -> <br>
  html = html.split('\n\n').map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');

  return html;
}

function renderMessages(messages) {
  const container = document.getElementById('chat-messages-inner');
  if (messages.length === 0) {
    container.innerHTML = `<div class="empty-state"><div class="icon-wrap">✨</div><h4>Say hello</h4><p>Send your first message to this conversation.</p></div>`;
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

  return `
    <div class="msg-row ${isUser ? 'user' : 'assistant'}" style="animation-delay:${Math.min(i, 6) * 0.04}s">
      <div class="msg-avatar ${isUser ? 'user' : 'assistant'}">${isUser ? '🧑' : 'V'}</div>
      <div style="display:flex;flex-direction:column;gap:4px;max-width:560px;">
        ${routedBadge}
        <div class="msg-bubble">${isUser ? escapeHtml(content) : markdownToHtml(content)}</div>
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
  const convo = await Api.createConversation({ title: 'New Conversation', agent_key: 'personal' });
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
      <div class="msg-avatar assistant thinking">V</div>
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
    const rowId = `msg-${Date.now()}`;
    container.insertAdjacentHTML('beforeend', `
      <div class="msg-row assistant" id="${rowId}">
        <div class="msg-avatar assistant">V</div>
        <div style="display:flex;flex-direction:column;gap:8px;max-width:560px;">
          <div class="msg-bubble typing-target"></div>
        </div>
      </div>
    `);
    const target = document.querySelector(`#${rowId} .typing-target`);
    const words = m.content.split(' ');
    let i = 0;

    function step() {
      i += 2; // reveal a couple words at a time — feels natural, not too slow
      target.textContent = words.slice(0, i).join(' ');
      scrollToBottom();
      if (i < words.length) {
        setTimeout(step, 25);
      } else {
        // Swap to the fully-formatted version (headings, bold, lists, project card)
        document.getElementById(rowId).outerHTML = renderMessageHtml(m);
        resolve();
      }
    }
    step();
  });
}