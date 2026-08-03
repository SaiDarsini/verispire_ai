/**
 * VICTORUS AI — Auth page behaviors shared across login/register/reset/otp.
 */

function setFieldError(fieldEl, message) {
  fieldEl.classList.toggle('has-error', !!message);
  const errEl = fieldEl.querySelector('.error-text');
  if (errEl) errEl.textContent = message || '';
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function togglePasswordVisibility(inputId, btnEl) {
  const input = document.getElementById(inputId);
  const show = input.type === 'password';
  input.type = show ? 'text' : 'password';
  btnEl.textContent = show ? 'Hide' : 'Show';
}

function passwordStrength(pw) {
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return score; // 0-4
}

function renderPwStrength(barsContainer, pw) {
  const score = passwordStrength(pw);
  const colors = ['#EF4444', '#F59E0B', '#38BDF8', '#22C55E'];
  const bars = barsContainer.querySelectorAll('span');
  bars.forEach((b, i) => { b.style.background = i < score ? colors[Math.min(score, 4) - 1] : 'var(--border)'; });
}

function setButtonLoading(btn, loading, loadingText = 'Please wait...') {
  if (loading) {
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span> ${loadingText}`;
    btn.disabled = true;
  } else {
    btn.innerHTML = btn.dataset.originalText || btn.innerHTML;
    btn.disabled = false;
  }
}

function saveAuthResult(data) {
  Storage.access = data.tokens.access_token;
  Storage.refresh = data.tokens.refresh_token;
  Storage.user = data.user;
}

function postLoginRedirect(user) {
  if (!user.has_completed_onboarding) {
    window.location.href = '/onboarding/onboarding.html';
  } else {
    window.location.href = '/dashboard/overview.html';
  }
}
