import { initParticleBackground } from './particleEffects.js';

function initManualParticles() {
  try {
    initParticleBackground();
  } catch (e) {
    console.warn('Particle system failed to initialize:', e);
  }
}
function setupSmoothAnchors() {
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (!href || href === '#') return;
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}
function setupSectionAnimations() {
  const observerOptions = { threshold: 0.1, rootMargin: '0px 0px -50px 0px' };
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add('slide-in');
    });
  }, observerOptions);
  document.querySelectorAll('.manual-section').forEach((section) => observer.observe(section));
}
function highlightStep(stepNumber) {
  document.querySelectorAll('.demo-step').forEach((step) => {
    step.style.background = 'rgba(0, 191, 255, 0.1)';
    step.style.borderColor = 'rgba(0, 191, 255, 0.3)';
  });
  const selected = document.querySelectorAll('.demo-step')[stepNumber - 1];
  if (selected) {
    selected.style.background = 'rgba(0, 191, 255, 0.3)';
    selected.style.borderColor = 'var(--main-accent)';
    showStepInfo(stepNumber);
  }
}

function showStepInfo(stepNumber) {
  const infoMessages = {
    1: 'Split View allows you to see your original data on the left and create a template on the right side. This is essential for schema transformations.',
    2: 'In the right panel, you can edit column headers, add sample data, and define patterns like sequences, constants, or date ranges.',
    3: 'The Update Template function captures your template structure and analyzes the patterns you\'ve created for replication.',
    4: 'Transform to Template applies your template to the entire dataset, potentially processing thousands of rows in seconds.',
  };
  let infoDisplay = document.getElementById('step-info-display');
  if (!infoDisplay) {
    infoDisplay = document.createElement('div');
    infoDisplay.id = 'step-info-display';
    infoDisplay.style.cssText = `position: fixed; top: 50%; right: 20px; transform: translateY(-50%); max-width: 300px; padding: 20px; background: var(--glass-bg-color); backdrop-filter: blur(var(--glass-blur-amount)); border: 1px solid var(--main-accent); border-radius: var(--border-radius); color: var(--text-primary); box-shadow: 0 8px 32px rgba(0,0,0,0.3); z-index: 1000; transition: all 0.3s ease;`;
    document.body.appendChild(infoDisplay);
  }
  infoDisplay.innerHTML = `<h6><i class="fas fa-info-circle me-2 text-primary"></i>Transform Step ${stepNumber} Details:</h6><p></p><p>${infoMessages[stepNumber]}</p><button onclick="closeStepInfo()" style="background: rgb(160, 160, 160); color: black; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; float: right;"><i class="fas fa-times me-1"></i>Close</button>`;
  infoDisplay.style.display = 'block';
}

function showFlowStepInfo(stepNumber) {
  const flowMessages = {
    1: 'Upload your Excel or CSV file by clicking the upload area or dragging and dropping your file. Supported formats include .xlsx, .xls, and .csv files.',
    2: 'Review your data structure in the preview table. You can examine column headers, data types, and sample rows to understand your dataset.',
    3: 'Use the AI command interface to describe what you want to do with your data in natural language. Examples: "Remove empty rows", "Sort by date", "Calculate totals".',
    4: 'Download your processed results in Excel format. The transformed data maintains your original structure while applying the requested changes.',
  };
  let infoDisplay = document.getElementById('step-info-display');
  if (!infoDisplay) {
    infoDisplay = document.createElement('div');
    infoDisplay.id = 'step-info-display';
    infoDisplay.style.cssText = `position: fixed; top: 50%; right: 20px; transform: translateY(-50%); max-width: 300px; padding: 20px; background: var(--glass-bg-color); backdrop-filter: blur(var(--glass-blur-amount)); border: 1px solid var(--main-accent); border-radius: var(--border-radius); color: var(--text-primary); box-shadow: 0 8px 32px rgba(0,0,0,0.3); z-index: 1000; transition: all 0.3s ease;`;
    document.body.appendChild(infoDisplay);
  }
  infoDisplay.innerHTML = `<h6><i class="fas fa-info-circle me-2 text-primary"></i>Workflow Step ${stepNumber}:</h6><p>${flowMessages[stepNumber]}</p><p></p><button onclick="closeStepInfo()" style="background: rgb(160, 160, 160); color: black; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; float: right;"><i class="fas fa-times me-1"></i>Close</button>`;
  infoDisplay.style.display = 'block';
}

function closeStepInfo() {
  const infoDisplay = document.getElementById('step-info-display');
  if (infoDisplay) infoDisplay.style.display = 'none';
}

// Keyboard shortcuts highlight cycle (auto-run with Ctrl+H toggle)
const shortcutCycle = { timerId: null, index: 0, running: false };

function getShortcutItems() {
  return Array.from(document.querySelectorAll('.shortcut-item'));
}

function clearShortcutHighlights() {
  getShortcutItems().forEach((el) => el.classList.remove('highlight-active'));
}

function stepShortcutHighlight() {
  const items = getShortcutItems();
  if (!items.length) return;
  clearShortcutHighlights();
  const idx = shortcutCycle.index % items.length;
  items[idx].classList.add('highlight-active');
  shortcutCycle.index = (shortcutCycle.index + 1) % items.length;
}

function startShortcutHighlight() {
  if (shortcutCycle.running) return;
  shortcutCycle.running = true;
  stepShortcutHighlight();
  shortcutCycle.timerId = setInterval(stepShortcutHighlight, 1500);
}

function stopShortcutHighlight() {
  if (shortcutCycle.timerId) {
    clearInterval(shortcutCycle.timerId);
    shortcutCycle.timerId = null;
  }
  shortcutCycle.running = false;
  clearShortcutHighlights();
}

function setupShortcutHighlightCycle() {
  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey && e.key.toLowerCase() === 'h') {
      e.preventDefault();
      if (shortcutCycle.running) stopShortcutHighlight();
      else startShortcutHighlight();
    }
  });
  startShortcutHighlight();
}
function setupFeatureCardHover() {
  document.querySelectorAll('.feature-card').forEach((card) => {
    card.addEventListener('mouseenter', function () {
      this.style.transform = 'translateY(-5px) scale(1.02)';
    });
    card.addEventListener('mouseleave', function () {
      this.style.transform = 'translateY(0) scale(1)';
    });
  });
}
function setupErrorCardToggle() {
  document.querySelectorAll('.error-card').forEach((card) => {
    card.addEventListener('click', function () {
      const solutionCard = this.querySelector('.solution-card');
      if (solutionCard) {
        solutionCard.style.maxHeight = solutionCard.style.maxHeight ? null : solutionCard.scrollHeight + 'px';
      }
    });
  });
}
function createHelpAndTopButtons() {
  const helpButton = document.createElement('div');
  helpButton.setAttribute('aria-label', 'Help');
  helpButton.setAttribute('title', 'Help');
  helpButton.innerHTML = '<i class="fas fa-question-circle"></i>';
  helpButton.style.cssText = 'position: fixed; bottom: 20px; left: 20px; width: 50px; height: 50px; background: var(--main-accent); color: var(--base-bg); border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 1.5em; box-shadow: 0 4px 16px rgba(0, 191, 255, 0.5); z-index: 1000; transition: all 0.3s ease;';
  helpButton.addEventListener('mouseenter', function () { this.style.transform = 'scale(1.1)'; this.style.boxShadow = '0 6px 20px rgba(0, 191, 255, 0.7)'; });
  helpButton.addEventListener('mouseleave', function () { this.style.transform = 'scale(1)'; this.style.boxShadow = '0 4px 16px rgba(0, 191, 255, 0.5)'; });
  helpButton.addEventListener('click', function () {
    const helpText = 'Tip: The shortcuts highlight animates automatically. Press Ctrl+H to pause or resume. You can also click any demo step to see details.';
    let helpPopup = document.getElementById('help-popup');
    if (helpPopup) {
      helpPopup.remove();
      return;
    }
    helpPopup = document.createElement('div');
    helpPopup.id = 'help-popup';
    helpPopup.innerHTML = `
      <h6><i class="fas fa-info-circle me-2 text-primary"></i>Help & Tips:</h6>
      <p></p>
      <p>${helpText}</p>
      <button onclick="document.getElementById('help-popup').remove()" style="background: rgb(160, 160, 160); color: black; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; float: right;">
        <i class="fas fa-times me-1"></i>Close
      </button>
    `;
    helpPopup.style.cssText = 'position: fixed; bottom: 80px; left: 20px; max-width: 280px; padding: 15px; background: var(--glass-bg-color); backdrop-filter: blur(var(--glass-blur-amount)); border: 1px solid var(--main-accent); border-radius: var(--border-radius); color: var(--text-primary); z-index: 1001; box-shadow: 0 8px 32px rgba(0,0,0,0.3); animation: slideIn 0.3s ease-out;';
    document.body.appendChild(helpPopup);
  });
  document.body.appendChild(helpButton);

  const backToTop = document.createElement('button');
  backToTop.type = 'button';
  backToTop.setAttribute('aria-label', 'Back to top');
  backToTop.setAttribute('title', 'Back to top');
  backToTop.innerHTML = '<i class="fas fa-arrow-up"></i>';
  backToTop.style.cssText = 'position: fixed; bottom: 20px; right: 20px; width: 50px; height: 50px; background: var(--main-accent); color: var(--base-bg); border: none; border-radius: 50%; display: none; align-items: center; justify-content: center; cursor: pointer; font-size: 1.25em; box-shadow: 0 4px 16px rgba(0, 191, 255, 0.5); z-index: 1000; transition: opacity 0.2s ease, transform 0.2s ease;';
  backToTop.addEventListener('mouseenter', function () { this.style.transform = 'scale(1.1)'; this.style.boxShadow = '0 6px 20px rgba(0, 191, 255, 0.7)'; });
  backToTop.addEventListener('mouseleave', function () { this.style.transform = 'scale(1)'; this.style.boxShadow = '0 4px 16px rgba(0, 191, 255, 0.5)'; });
  backToTop.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
  document.body.appendChild(backToTop);
  window.addEventListener('scroll', function () {
    if (window.scrollY > 200) { backToTop.style.display = 'flex'; backToTop.style.opacity = '1'; }
    else { backToTop.style.opacity = '0'; backToTop.style.display = 'none'; }
  });
}
window.addEventListener('DOMContentLoaded', function () {
  initInstructionsSessionLifecycle();

  if ('requestIdleCallback' in window) {
    requestIdleCallback(() => initManualParticles(), { timeout: 1500 });
  } else {
    setTimeout(() => initManualParticles(), 0);
  }
  setupSmoothAnchors();
  setupSectionAnimations();
  setupShortcutHighlightCycle();
  setupFeatureCardHover();
  setupErrorCardToggle();
  document.querySelectorAll('.demo-step').forEach((step, index) => {
    step.addEventListener('click', () => highlightStep(index + 1));
  });
  setTimeout(createHelpAndTopButtons, 500);
});

(function makeScrollPassive(){
  try {
    const origAdd = window.addEventListener;
    window.addEventListener('scroll', () => {}, { passive: true });
  } catch(_) {}
})();

window.highlightStep = highlightStep;
window.showStepInfo = showStepInfo;
window.showFlowStepInfo = showFlowStepInfo;
window.closeStepInfo = closeStepInfo;
let instrHeartbeatTimer = null;

async function initInstructionsSessionLifecycle() {
  try {
    const res = await fetch('/api/session/start', { method: 'POST' });
    if (!res.ok) return;
    const data = await res.json();
    window.currentSessionId = data.sessionId;

    fetch('/usermanual', {
      method: 'GET',
      headers: { 'X-Session-Id': window.currentSessionId },
      cache: 'no-store',
      keepalive: true
    }).catch(() => {});

    instrHeartbeatTimer = setInterval(() => {
      if (!window.currentSessionId) return;
      navigator.sendBeacon('/api/session/heartbeat', new Blob([
        JSON.stringify({ sessionId: window.currentSessionId })
      ], { type: 'application/json' }));
    }, 25000);

    window.addEventListener('beforeunload', endInstructionsSessionLifecycle);
  } catch (e) {
    console.warn('Instructions session start failed', e);
  }
}

function endInstructionsSessionLifecycle() {
  if (instrHeartbeatTimer) {
    clearInterval(instrHeartbeatTimer);
    instrHeartbeatTimer = null;
  }
  if (window.currentSessionId) {
    navigator.sendBeacon('/api/session/end', new Blob([
      JSON.stringify({ sessionId: window.currentSessionId })
    ], { type: 'application/json' }));
  }
}
