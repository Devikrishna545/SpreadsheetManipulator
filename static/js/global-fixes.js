(function () {
  try {
    if (!window.actionsSection || typeof window.actionsSection !== 'object') {
      window.actionsSection = { style: {} };
    } else if (!window.actionsSection.style) {
      window.actionsSection.style = {};
    }
    // eslint-disable-next-line no-var
    var actionsSection = window.actionsSection;
    if (!actionsSection) {
      window.actionsSection = { style: {} };
    }
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('actionsSection guard failed to initialize', e);
    try { window.actionsSection = { style: {} }; } catch (_) {}
  }
})();
