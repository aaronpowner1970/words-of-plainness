/**
 * Interactive Chapter — Path Navigation & Reflection System
 * Words of Plainness — Multi-Path Chapter Experience
 */

(function () {
  // STATE
  const state = {
    screen: 'gateway', // gateway | movement | reflection
    path: null,        // skeptic | seeker | disciple
    movement: 1,       // 1-5
    progress: {}       // path -> highest movement reached
  };

  // Load saved state from localStorage
  try {
    const saved = localStorage.getItem('wop_ch06_interactive_state');
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed.progress) state.progress = parsed.progress;
    }
  } catch (e) { /* ignore */ }

  // Load saved reflections into textareas
  function loadReflections() {
    document.querySelectorAll('.reflection-textarea').forEach(function (ta) {
      const key = 'wop_ch06_ref_' + ta.dataset.path + '_' + ta.dataset.step;
      try {
        const val = localStorage.getItem(key);
        if (val) ta.value = val;
      } catch (e) { /* ignore */ }
    });
  }

  // Save state to localStorage
  function saveState() {
    try {
      localStorage.setItem('wop_ch06_interactive_state', JSON.stringify({
        progress: state.progress
      }));
    } catch (e) { /* ignore */ }
  }

  // Hide all content sections
  function hideAll() {
    document.querySelectorAll('.movement-section, .reflection-section').forEach(function (el) {
      el.style.display = 'none';
    });
  }

  // Update progress dots for current path and movement
  function updateDots() {
    var sections = document.querySelectorAll('.movement-section[data-path="' + state.path + '"]');
    sections.forEach(function (section) {
      section.querySelectorAll('.dot').forEach(function (dot) {
        var m = parseInt(dot.dataset.m);
        dot.classList.remove('active', 'completed');
        if (m === state.movement) dot.classList.add('active');
        else if (m < state.movement) dot.classList.add('completed');
      });
    });
  }

  // Show transition screen then execute callback
  function showTransition(callback) {
    var ts = document.getElementById('transition-screen');
    ts.style.display = 'flex';
    ts.classList.add('ic-fade-in');

    setTimeout(function () {
      ts.classList.remove('ic-fade-in');
      ts.classList.add('ic-fade-out');
      setTimeout(function () {
        ts.style.display = 'none';
        ts.classList.remove('ic-fade-out');
        callback();
      }, 300);
    }, 1200);
  }

  // ============================================================
  // MAIN NAVIGATION FUNCTIONS (exposed globally)
  // ============================================================

  window.selectPath = function (pathKey) {
    state.path = pathKey;
    state.movement = 1;
    state.screen = 'movement';

    if (!state.progress[pathKey]) state.progress[pathKey] = 1;
    saveState();

    document.getElementById('gateway').style.display = 'none';
    document.getElementById('content-area').style.display = 'block';
    document.getElementById('float-back').style.display = 'block';

    showTransition(function () {
      hideAll();
      var target = document.querySelector(
        '.movement-section[data-path="' + pathKey + '"][data-movement="1"]'
      );
      if (target) {
        target.style.display = 'block';
        target.classList.add('ic-fade-in');
        setTimeout(function () { target.classList.remove('ic-fade-in'); }, 600);
      }
      updateDots();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  };

  window.continueOnPath = function () {
    if (state.movement >= 5) return;

    state.movement++;
    if (!state.progress[state.path] || state.progress[state.path] < state.movement) {
      state.progress[state.path] = state.movement;
    }
    saveState();

    showTransition(function () {
      hideAll();
      var target = document.querySelector(
        '.movement-section[data-path="' + state.path + '"][data-movement="' + state.movement + '"]'
      );
      if (target) {
        target.style.display = 'block';
        target.classList.add('ic-fade-in');
        setTimeout(function () { target.classList.remove('ic-fade-in'); }, 600);
      }
      updateDots();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  };

  window.goBackOnPath = function () {
    if (state.movement <= 1) {
      showGateway();
      return;
    }
    state.movement--;
    saveState();
    showTransition(function () {
      hideAll();
      var target = document.querySelector(
        '.movement-section[data-path="' + state.path + '"][data-movement="' + state.movement + '"]'
      );
      if (target) {
        target.style.display = 'block';
        target.classList.add('ic-fade-in');
        setTimeout(function () { target.classList.remove('ic-fade-in'); }, 600);
      }
      updateDots();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  };

  window.showReflection = function () {
    state.screen = 'reflection';

    showTransition(function () {
      hideAll();
      var target = document.querySelector(
        '.reflection-section[data-path="' + state.path + '"]'
      );
      if (target) {
        target.style.display = 'block';
        target.classList.add('ic-fade-in');
        setTimeout(function () { target.classList.remove('ic-fade-in'); }, 600);
      }
      loadReflections();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  };

  window.showGateway = function () {
    state.screen = 'gateway';
    state.path = null;

    document.getElementById('content-area').style.display = 'none';
    document.getElementById('float-back').style.display = 'none';

    var gw = document.getElementById('gateway');
    gw.style.display = 'block';
    gw.classList.add('ic-fade-in');
    setTimeout(function () { gw.classList.remove('ic-fade-in'); }, 800);

    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  window.navigateToFullChapter = function (e) {
    if (e) e.preventDefault();
    window.location.href = '/chapters/06-embrace-the-savior-full/';
  };

  window.saveReflections = function (pathKey) {
    var textareas = document.querySelectorAll(
      '.reflection-textarea[data-path="' + pathKey + '"]'
    );
    textareas.forEach(function (ta) {
      var key = 'wop_ch06_ref_' + ta.dataset.path + '_' + ta.dataset.step;
      try { localStorage.setItem(key, ta.value); } catch (e) { /* ignore */ }
    });

    var status = document.getElementById('save-status-' + pathKey);
    if (status) {
      status.textContent = 'Saved \u2713';
      setTimeout(function () { status.textContent = ''; }, 2500);
    }
  };

  // Auto-save reflections on input
  document.addEventListener('input', function (e) {
    if (e.target.classList.contains('reflection-textarea')) {
      var key = 'wop_ch06_ref_' + e.target.dataset.path + '_' + e.target.dataset.step;
      try { localStorage.setItem(key, e.target.value); } catch (err) { /* ignore */ }
    }
  });

})();
