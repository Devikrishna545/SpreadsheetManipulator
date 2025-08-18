// Global fix for removed actionsSection element - kept very early
// Ensures any legacy references to actionsSection don't break the app.
(function () {
  try {
    if (!window.actionsSection || typeof window.actionsSection !== 'object') {
      window.actionsSection = { style: {} };
    } else if (!window.actionsSection.style) {
      window.actionsSection.style = {};
    }
    // Provide a global var alias for legacy code
    // eslint-disable-next-line no-var
    var actionsSection = window.actionsSection; // keep var for legacy scripts
    // Prevent unused var removal in some bundlers
    if (!actionsSection) {
      window.actionsSection = { style: {} };
    }
  } catch (e) {
    // In case window is not available or other oddities
    // eslint-disable-next-line no-console
    console.warn('actionsSection guard failed to initialize', e);
    // Best-effort fallback
    try { window.actionsSection = { style: {} }; } catch (_) {}
  }
})();
