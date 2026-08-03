/**
 * VICTORUS AI — Dashboard Shell
 * Injects the icon-rail sidebar + topnav into any dashboard page that
 * includes <div id="sidebar-root"></div> and <div id="topnav-root"></div>,
 * then wires up auth guard, mobile menu, logout, and live badges.
 */

// The rail only ever shows these four primary destinations, as icons only.
const NAV_ITEMS = [
  { href: 'conversations.html', label: 'Chat', icon: 'chat' },
  { href: 'activity-logs.html', label: 'History', icon: 'clock' },
  { href: 'tasks.html', label: 'Projects', icon: 'folder' },
  { href: 'agents.html', label: 'AI Agents', icon: 'bot' },
];

// Everything else lives one hover away, under the profile avatar.
const PROFILE_MENU = [
  { href: 'overview.html', label: 'Overview', icon: 'grid' },
  { href: 'memory.html', label: 'Memory', icon: 'brain' },
  { href: 'files.html', label: 'Files', icon: 'file' },
  { href: 'integrations.html', label: 'Integrations', icon: 'plug' },
  { href: 'analytics.html', label: 'Analytics', icon: 'chart' },
  { href: 'notifications.html', label: 'Notifications', icon: 'bell', badgeId: 'nav-notif-count' },
  { href: 'billing.html', label: 'Billing', icon: 'card' },
  { divider: true },
  { href: 'profile.html', label: 'Your Profile', icon: 'user' },
  { href: 'settings.html', label: 'Settings', icon: 'settings' },
  { href: 'api-keys.html', label: 'API Keys', icon: 'key' },
  { href: 'security.html', label: 'Security', icon: 'shield' },
  { href: 'help.html', label: 'Help', icon: 'help' },
];

const ICONS = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  chat: '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
  brain: '<path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44A2.5 2.5 0 0 1 4 17.5v-1.05A2.5 2.5 0 0 1 2 14v-2a2.5 2.5 0 0 1 1.5-2.29V8.5A2.5 2.5 0 0 1 6 6h.06A2.5 2.5 0 0 1 9.5 2z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44A2.5 2.5 0 0 0 20 17.5v-1.05a2.5 2.5 0 0 0 2-2.45v-2a2.5 2.5 0 0 0-1.5-2.29V8.5A2.5 2.5 0 0 0 18 6h-.06A2.5 2.5 0 0 0 14.5 2z"/>',
  bot: '<rect x="3" y="8" width="18" height="12" rx="2"/><circle cx="8.5" cy="14" r="1.5"/><circle cx="15.5" cy="14" r="1.5"/><path d="M12 8V4M9 4h6"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
  plug: '<path d="M18 4l2 2M22 6l-2-2M9 8l6 6M9 8l-3 3 6 6 3-3M4 15l3 3"/>',
  chart: '<path d="M3 3v18h18"/><rect x="7" y="12" width="3" height="6"/><rect x="12" y="8" width="3" height="10"/><rect x="17" y="5" width="3" height="13"/>',
  bell: '<path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
  card: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/>',
  user: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  key: '<circle cx="7.5" cy="15.5" r="5.5"/><path d="M21 2l-9.6 9.6M15.5 7.5L18 5l3 3-2.5 2.5"/>',
  shield: '<path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4"/><circle cx="12" cy="17" r="0.6" fill="currentColor"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
  menu: '<path d="M3 12h18M3 6h18M3 18h18"/>',
};

function svgIcon(name) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ICONS.grid}</svg>`;
}

function buildSidebar(activePage, user) {
  const rail = NAV_ITEMS.map(l => {
  if (l.href === 'activity-logs.html' && l.label === 'History') {
    return `
      <div class="rail-link history-trigger" data-tooltip="History">
        ${svgIcon(l.icon)}
        <div class="profile-flyout history-flyout" id="history-flyout">
          <div class="profile-flyout-header"><div class="sidebar-user-name">Recent Chats</div></div>
          <div class="profile-menu-links" id="history-list">
            <div class="skeleton" style="height:40px;margin-bottom:6px;"></div>
            <div class="skeleton" style="height:40px;"></div>
          </div>
        </div>
      </div>
    `;
  }
  return `
    <a href="${l.href}" class="rail-link ${l.href === activePage ? 'active' : ''}" data-tooltip="${l.label}">
      ${svgIcon(l.icon)}
    </a>
  `;
}).join('');

  const menuItems = PROFILE_MENU.map(l => {
    if (l.divider) return '<div class="profile-menu-divider"></div>';
    return `
      <a href="${l.href}" class="profile-menu-link ${l.href === activePage ? 'active' : ''}">
        ${svgIcon(l.icon)}
        <span>${l.label}</span>
        ${l.badgeId ? `<span class="count" id="${l.badgeId}" style="display:none">0</span>` : ''}
      </a>
    `;
  }).join('');

  return `
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-logo" data-tooltip="VICTORUS AI">
        <div class="mark">V</div>
      </div>
      <nav class="rail-nav">${rail}</nav>
      <div class="sidebar-footer">
        <div class="profile-trigger" id="profile-trigger">
          <div class="avatar">${user?.avatar_url ? `<img src="${user.avatar_url}" alt="">` : initials(user?.full_name)}</div>
          <div class="profile-flyout" id="profile-flyout">
            <div class="profile-flyout-header">
              <div class="avatar avatar-lg">${user?.avatar_url ? `<img src="${user.avatar_url}" alt="">` : initials(user?.full_name)}</div>
              <div>
                <div class="sidebar-user-name" id="flyout-user-name">${escapeHtml(user?.full_name || 'Loading...')}</div>
                <div class="sidebar-user-email" id="flyout-user-email">${escapeHtml(user?.email || '')}</div>
              </div>
            </div>
            <div class="profile-menu-links">${menuItems}</div>
            <div class="profile-menu-divider"></div>
            <button class="profile-menu-link profile-menu-logout" id="sidebar-user-btn">
              ${svgIcon('logout')}
              <span>Log out</span>
            </button>
          </div>
        </div>
      </div>
    </aside>
    <div class="sidebar-overlay" id="sidebar-overlay"></div>
  `;
}

function buildTopnav(title) {
  return `
    <div class="topnav">
      <div style="display:flex;align-items:center;gap:14px;">
        <button class="icon-btn mobile-menu-btn" id="mobile-menu-btn">${svgIcon('menu')}</button>
        <h1>${title}</h1>
      </div>
      <div class="topnav-actions">
        <a href="notifications.html" class="icon-btn" title="Notifications">
          ${svgIcon('bell')}
          <span class="dot" id="topnav-notif-dot" style="display:none"></span>
        </a>
      </div>
    </div>
  `;
}

async function initDashboardShell(pageTitle) {
  if (!requireAuth()) return null;

  const activePage = window.location.pathname.split('/').pop();
  let user = Storage.user;

  const sidebarRoot = document.getElementById('sidebar-root');
  const topnavRoot = document.getElementById('topnav-root');
  if (sidebarRoot) sidebarRoot.outerHTML = buildSidebar(activePage, user);
  if (topnavRoot) topnavRoot.outerHTML = buildTopnav(pageTitle);

  document.getElementById('sidebar-user-btn')?.addEventListener('click', logoutUser);

  // Click-to-toggle for touch devices (hover still works via CSS on desktop)
  const trigger = document.getElementById('profile-trigger');
  const flyout = document.getElementById('profile-flyout');
  trigger?.addEventListener('click', (e) => {
    if (e.target.closest('#sidebar-user-btn')) return;
    flyout.classList.toggle('force-open');
  });
  document.addEventListener('click', (e) => {
    if (!trigger?.contains(e.target)) flyout?.classList.remove('force-open');
  });

  const menuBtn = document.getElementById('mobile-menu-btn');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  menuBtn?.addEventListener('click', () => { sidebar.classList.add('open'); overlay.classList.add('show'); });
  overlay?.addEventListener('click', () => { sidebar.classList.remove('open'); overlay.classList.remove('show'); });

  // Refresh user + notification badge in the background
  try {
    user = await Api.me();
    Storage.user = user;
    document.querySelectorAll('#flyout-user-name').forEach(el => el.textContent = user.full_name);
    document.querySelectorAll('#flyout-user-email').forEach(el => el.textContent = user.email);
  } catch { /* keep cached user */ }

  try {
    const { unread_count } = await Api.unreadCount();
    const navBadge = document.getElementById('nav-notif-count');
    const dot = document.getElementById('topnav-notif-dot');
    if (unread_count > 0) {
      if (navBadge) { navBadge.textContent = unread_count; navBadge.style.display = 'inline-flex'; }
      if (dot) dot.style.display = 'block';
    }
  } catch { /* ignore */ }

 try {
  const convos = await Api.listConversations();
  const list = document.getElementById('history-list');
  if (list) {
    list.innerHTML = convos.length
      ? convos.map(c => `
          <div class="history-item" data-id="${c.id}">
            <a href="conversations.html?id=${c.id}" class="history-item-link"><span>${escapeHtml(c.title)}</span></a>
            <button class="history-delete-btn" data-id="${c.id}" title="Delete conversation">×</button>
          </div>
        `).join('')
      : `<div style="padding:10px;color:var(--text-muted);font-size:12.5px;">No chats yet</div>`;

    list.querySelectorAll('.history-delete-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        const id = btn.dataset.id;
        if (!confirm('Delete this conversation? This can\'t be undone.')) return;
        try {
          await Api.deleteConversation(id);
          btn.closest('.history-item').remove();
          const params = new URLSearchParams(window.location.search);
          if (params.get('id') === id) {
            window.location.href = 'conversations.html';
          }
        } catch (err) {
          toast(err.message, 'error');
        }
      });
    });
  }
} catch { /* ignore */ }

  return user;
}
