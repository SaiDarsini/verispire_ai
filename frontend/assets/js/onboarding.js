/**
 * VeriSpire AI — Onboarding Wizard
 * 6 steps: occupation -> interests -> skills -> familiarity -> resume -> review.
 */

const TOTAL_STEPS = 6;
let currentStep = 1;

const state = {
  occupation: null,
  ai_interests: [],
  skills: [],
  ai_familiarity: null,
  resume_uploaded: false,
  resume_name: null,
};

function goToStep(step) {
  currentStep = Math.max(1, Math.min(TOTAL_STEPS, step));
  document.querySelectorAll('.onboard-step').forEach(el => el.classList.remove('active'));
  document.querySelector(`.onboard-step[data-step="${currentStep}"]`).classList.add('active');

  document.getElementById('progress-current').textContent = currentStep;
  const pct = (currentStep / TOTAL_STEPS) * 100;
  document.getElementById('onboard-progress-fill').style.width = `${pct}%`;

  document.querySelectorAll('.step-dots span').forEach((dot, i) => {
    dot.classList.toggle('active', i === currentStep - 1);
  });

  document.getElementById('back-btn').style.visibility = currentStep === 1 ? 'hidden' : 'visible';
  const nextBtn = document.getElementById('next-btn');
  nextBtn.textContent = currentStep === TOTAL_STEPS ? 'Complete Setup' : (currentStep === 5 && !state.resume_uploaded ? 'Skip for now' : 'Continue');

  if (currentStep === 6) renderReview();
}

function validateStep(step) {
  if (step === 1 && !state.occupation) { toast('Please select who you are.', 'warning'); return false; }
  if (step === 2 && state.ai_interests.length === 0) { toast('Select at least one area to get help with.', 'warning'); return false; }
  if (step === 4 && !state.ai_familiarity) { toast('Select your AI familiarity level.', 'warning'); return false; }
  return true;
}

document.addEventListener('DOMContentLoaded', () => {
  if (!requireAuth()) return;

  // ---- Step 1: Occupation ----
  document.querySelectorAll('#step-1 .option-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('#step-1 .option-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      state.occupation = card.dataset.value;
    });
  });

  // ---- Step 2: AI interests (multi) ----
  document.querySelectorAll('#step-2 .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const val = chip.dataset.value;
      if (state.ai_interests.includes(val)) {
        state.ai_interests = state.ai_interests.filter(v => v !== val);
        chip.classList.remove('selected');
      } else {
        state.ai_interests.push(val);
        chip.classList.add('selected');
      }
    });
  });

  // ---- Step 3: Skills autocomplete ----
  const skillInput = document.getElementById('skill-input');
  const suggestionsBox = document.getElementById('skill-suggestions');
  let debounceTimer;

  skillInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = skillInput.value.trim();
    if (!q) { suggestionsBox.classList.remove('show'); return; }
    debounceTimer = setTimeout(async () => {
      try {
        const matches = await Api.autocompleteSkills(q);
        renderSkillSuggestions(matches.filter(m => !state.skills.includes(m)));
      } catch { /* ignore */ }
    }, 200);
  });

  skillInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && skillInput.value.trim()) {
      e.preventDefault();
      addSkill(skillInput.value.trim());
    }
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.skill-input-wrap')) suggestionsBox.classList.remove('show');
  });

  // ---- Step 4: AI familiarity ----
  document.querySelectorAll('#step-4 .familiarity-option').forEach(opt => {
    opt.addEventListener('click', () => {
      document.querySelectorAll('#step-4 .familiarity-option').forEach(o => o.classList.remove('selected'));
      opt.classList.add('selected');
      state.ai_familiarity = opt.dataset.value;
    });
  });

  // ---- Step 5: Resume upload ----
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('resume-file-input');
  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) handleResumeFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleResumeFile(fileInput.files[0]);
  });

  // ---- Nav buttons ----
  document.getElementById('next-btn').addEventListener('click', async () => {
    if (!validateStep(currentStep)) return;
    if (currentStep === TOTAL_STEPS) {
      await submitOnboarding();
      return;
    }
    goToStep(currentStep + 1);
  });
  document.getElementById('back-btn').addEventListener('click', () => goToStep(currentStep - 1));
  document.getElementById('edit-btn')?.addEventListener('click', () => goToStep(1));

  goToStep(1);
});

function renderSkillSuggestions(matches) {
  const box = document.getElementById('skill-suggestions');
  if (!matches.length) { box.classList.remove('show'); return; }
  box.innerHTML = matches.map(m => `<div class="skill-suggestion-item" data-value="${escapeHtml(m)}">${escapeHtml(m)}</div>`).join('');
  box.classList.add('show');
  box.querySelectorAll('.skill-suggestion-item').forEach(item => {
    item.addEventListener('click', () => addSkill(item.dataset.value));
  });
}

function addSkill(name) {
  if (!state.skills.includes(name)) state.skills.push(name);
  document.getElementById('skill-input').value = '';
  document.getElementById('skill-suggestions').classList.remove('show');
  renderSelectedSkills();
}

function removeSkill(name) {
  state.skills = state.skills.filter(s => s !== name);
  renderSelectedSkills();
}

function renderSelectedSkills() {
  const wrap = document.getElementById('selected-skills');
  wrap.innerHTML = state.skills.map(s => `
    <span class="chip selected">${escapeHtml(s)} <span class="remove" onclick="removeSkill('${s.replace(/'/g, "\\'")}')">✕</span></span>
  `).join('');
}

async function handleResumeFile(file) {
  const allowed = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/png', 'image/jpeg'];
  if (!allowed.includes(file.type)) {
    toast('Please upload a PDF, DOCX, or image file.', 'warning');
    return;
  }
  const row = document.getElementById('uploaded-file-row');
  row.style.display = 'flex';
  row.querySelector('.file-name').textContent = file.name;
  row.querySelector('.file-status').innerHTML = '<span class="spinner"></span>';

  try {
    const formData = new FormData();
    formData.append('file', file);
    await Api.uploadResume(formData);
    state.resume_uploaded = true;
    state.resume_name = file.name;
    row.querySelector('.file-status').innerHTML = '<span class="badge badge-accent">Uploaded</span>';
    document.getElementById('next-btn').textContent = 'Continue';
  } catch (err) {
    row.querySelector('.file-status').innerHTML = '<span class="badge badge-error">Failed</span>';
    toast(err.message, 'error');
  }
}

function renderReview() {
  document.getElementById('review-occupation').textContent = state.occupation || '—';
  document.getElementById('review-interests').textContent = state.ai_interests.length ? state.ai_interests.join(', ') : '—';
  document.getElementById('review-skills').textContent = state.skills.length ? state.skills.join(', ') : '—';
  document.getElementById('review-familiarity').textContent = state.ai_familiarity || '—';
  document.getElementById('review-resume').textContent = state.resume_name || 'Not uploaded';
}

async function submitOnboarding() {
  const btn = document.getElementById('next-btn');
  setButtonLoading(btn, true, 'Setting up workspace...');
  try {
    await Api.completeOnboarding({
      occupation: state.occupation,
      ai_interests: state.ai_interests,
      skills: state.skills,
      ai_familiarity: state.ai_familiarity,
      bio: null,
    });
    const user = Storage.user;
    if (user) { user.has_completed_onboarding = true; Storage.user = user; }
    toast('Workspace ready! Redirecting to your dashboard...', 'success');
    setTimeout(() => window.location.href = '/dashboard/overview.html', 1200);
  } catch (err) {
    toast(err.message, 'error');
    setButtonLoading(btn, false);
  }
}
