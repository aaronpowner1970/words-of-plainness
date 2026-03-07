/**
 * Concert Player — Movement-level playback for the Virtual Concert Hall
 * Words of Plainness Ministry
 *
 * Handles: play/pause, movement navigation, auto-advance with interstitial,
 * script toggle, closing reflection, mobile now-playing bar.
 */
(function () {
  'use strict';

  var ConcertPlayer = {
    manifest: null,
    audio: null,
    currentIndex: 0,
    isPlaying: false,
    interstitialTimer: null,

    /* ---- Initialization ---- */

    init: function () {
      var dataEl = document.getElementById('concertManifest');
      if (!dataEl) return;

      this.manifest = JSON.parse(dataEl.textContent);
      this.audio = document.getElementById('concertAudio');
      if (!this.audio || !this.manifest) return;

      this.bindEvents();
      this.loadMovement(0);
      this.setupMobileBar();
    },

    bindEvents: function () {
      var self = this;

      // Play / Pause
      var playBtn = document.getElementById('playerPlayPause');
      if (playBtn) playBtn.addEventListener('click', function () { self.togglePlay(); });

      var mobilePlayBtn = document.getElementById('mobileNpPlay');
      if (mobilePlayBtn) mobilePlayBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        self.togglePlay();
      });

      // Prev / Next
      var prevBtn = document.getElementById('playerPrev');
      if (prevBtn) prevBtn.addEventListener('click', function () { self.prevMovement(); });

      var nextBtn = document.getElementById('playerNext');
      if (nextBtn) nextBtn.addEventListener('click', function () { self.nextMovement(); });

      // Timeline clicks (event delegation)
      var timeline = document.getElementById('concertTimeline');
      if (timeline) {
        timeline.addEventListener('click', function (e) {
          var btn = e.target.closest('[data-movement]');
          if (btn) {
            var idx = parseInt(btn.dataset.movement, 10);
            self.loadMovement(idx);
            self.play();
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }
        });
      }

      // Audio events
      this.audio.addEventListener('timeupdate', function () { self.updateProgress(); });
      this.audio.addEventListener('loadedmetadata', function () { self.updateDuration(); });
      this.audio.addEventListener('ended', function () { self.onMovementEnd(); });
      this.audio.addEventListener('play', function () { self.onPlay(); });
      this.audio.addEventListener('pause', function () { self.onPause(); });

      // Seek bar
      var seekInput = document.getElementById('playerSeek');
      if (seekInput) {
        seekInput.addEventListener('input', function (e) {
          var pct = parseFloat(e.target.value);
          if (self.audio.duration) {
            self.audio.currentTime = (pct / 100) * self.audio.duration;
          }
        });
      }

      // Script toggle
      var scriptBtn = document.getElementById('btnScriptToggle');
      if (scriptBtn) scriptBtn.addEventListener('click', function () { self.toggleScript(); });

      // Program notes toggle (event delegation)
      document.addEventListener('click', function (e) {
        var toggleBtn = e.target.closest('[data-action="toggle-program-notes"]');
        if (toggleBtn) {
          self.toggleProgramNotes(toggleBtn);
        }
      });

      // Mobile bar tap → scroll to player
      var mobileBar = document.getElementById('mobileNowPlaying');
      if (mobileBar) {
        mobileBar.addEventListener('click', function (e) {
          if (!e.target.closest('.mobile-np-play')) {
            var player = document.getElementById('concertPlayer');
            if (player) player.scrollIntoView({ behavior: 'smooth' });
          }
        });
      }
    },

    /* ---- Movement Loading ---- */

    loadMovement: function (index) {
      if (index < 0 || index >= this.manifest.movements.length) return;

      this.currentIndex = index;
      var mvt = this.manifest.movements[index];

      // Hide interstitial and closing
      this.hideInterstitial();
      this.hideClosing();

      // Set audio source
      this.audio.src = mvt.audioUrl;
      this.audio.load();

      // Update movement info
      var numEl = document.getElementById('playerMvtNumber');
      var titleEl = document.getElementById('playerMvtTitle');
      var graceEl = document.getElementById('playerGraceLabel');
      if (numEl) numEl.textContent = 'Movement ' + mvt.number;
      if (titleEl) titleEl.textContent = mvt.title;
      if (graceEl) graceEl.textContent = mvt.graceLabel;

      // Update timeline active state
      var buttons = document.querySelectorAll('.timeline-mvt');
      for (var i = 0; i < buttons.length; i++) {
        if (i === index) {
          buttons[i].classList.add('timeline-mvt--active');
        } else {
          buttons[i].classList.remove('timeline-mvt--active');
        }
      }

      // Scroll active timeline button into view
      if (buttons[index]) {
        buttons[index].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      }

      // Script toggle visibility
      var scriptToggle = document.getElementById('playerScriptToggle');
      var scriptPanel = document.getElementById('playerScriptPanel');
      if (mvt.script) {
        if (scriptToggle) scriptToggle.style.display = '';
        var contentEl = document.getElementById('playerScriptContent');
        if (contentEl) contentEl.innerHTML = mvt.script;
      } else {
        if (scriptToggle) scriptToggle.style.display = 'none';
        if (scriptPanel) scriptPanel.style.display = 'none';
      }

      // Reset progress
      var fill = document.getElementById('playerProgressFill');
      var seek = document.getElementById('playerSeek');
      var curTime = document.getElementById('playerCurrentTime');
      var durTime = document.getElementById('playerDuration');
      if (fill) fill.style.width = '0%';
      if (seek) seek.value = 0;
      if (curTime) curTime.textContent = '0:00';
      if (durTime) durTime.textContent = '--:--';

      // Update mobile bar
      this.updateMobileBar();

      // Update program notes
      this.updateProgramNotes(mvt);
    },

    /* ---- Playback Controls ---- */

    play: function () {
      this.audio.play().catch(function () {});
    },

    pause: function () {
      this.audio.pause();
    },

    togglePlay: function () {
      if (this.audio.paused) {
        this.play();
      } else {
        this.pause();
      }
    },

    onPlay: function () {
      this.isPlaying = true;
      this.updatePlayButtons(true);
    },

    onPause: function () {
      this.isPlaying = false;
      this.updatePlayButtons(false);
    },

    updatePlayButtons: function (playing) {
      // Main player
      var mainPlay = document.querySelector('#playerPlayPause .icon-play');
      var mainPause = document.querySelector('#playerPlayPause .icon-pause');
      if (mainPlay) mainPlay.style.display = playing ? 'none' : '';
      if (mainPause) mainPause.style.display = playing ? '' : 'none';

      // Mobile bar
      var mobilePlay = document.querySelector('#mobileNpPlay .icon-play');
      var mobilePause = document.querySelector('#mobileNpPlay .icon-pause');
      if (mobilePlay) mobilePlay.style.display = playing ? 'none' : '';
      if (mobilePause) mobilePause.style.display = playing ? '' : 'none';
    },

    prevMovement: function () {
      if (this.currentIndex > 0) {
        this.loadMovement(this.currentIndex - 1);
        this.play();
      }
    },

    nextMovement: function () {
      if (this.currentIndex < this.manifest.movements.length - 1) {
        this.loadMovement(this.currentIndex + 1);
        this.play();
      }
    },

    /* ---- Movement End / Auto-Advance ---- */

    onMovementEnd: function () {
      var self = this;
      var mvt = this.manifest.movements[this.currentIndex];
      var isLast = this.currentIndex === this.manifest.movements.length - 1;

      if (isLast) {
        // Final movement: show closing reflection
        this.showClosing();
      } else if (mvt.interstitial) {
        // Show interstitial text, pause 4 seconds, then auto-advance
        this.showInterstitial(mvt.interstitial, function () {
          self.loadMovement(self.currentIndex + 1);
          self.play();
        });
      } else {
        // No interstitial: advance directly
        this.loadMovement(this.currentIndex + 1);
        this.play();
      }
    },

    /* ---- Interstitial Display ---- */

    showInterstitial: function (text, callback) {
      var el = document.getElementById('concertInterstitial');
      var textEl = document.getElementById('interstitialText');
      var player = document.getElementById('concertPlayer');

      // Dim the player
      if (player) player.classList.add('concert-hall-player--dimmed');

      if (textEl) textEl.textContent = text;
      if (el) {
        el.style.display = '';
        // Force reflow for transition
        el.offsetHeight;
        el.classList.add('interstitial--visible');
      }

      this.interstitialTimer = setTimeout(function () {
        ConcertPlayer.hideInterstitial();
        if (callback) callback();
      }, 4000);
    },

    hideInterstitial: function () {
      if (this.interstitialTimer) {
        clearTimeout(this.interstitialTimer);
        this.interstitialTimer = null;
      }
      var el = document.getElementById('concertInterstitial');
      if (el) {
        el.classList.remove('interstitial--visible');
        el.style.display = 'none';
      }
      var player = document.getElementById('concertPlayer');
      if (player) player.classList.remove('concert-hall-player--dimmed');
    },

    /* ---- Closing Reflection ---- */

    showClosing: function () {
      var el = document.getElementById('concertClosing');
      if (el) {
        el.style.display = '';
        el.offsetHeight;
        el.classList.add('closing--visible');
      }

      // After 10 seconds, reveal the chapter link
      setTimeout(function () {
        var link = document.getElementById('closingChapterLink');
        if (link) {
          link.style.display = '';
          link.offsetHeight;
          link.classList.add('closing-link--visible');
        }
      }, 10000);
    },

    hideClosing: function () {
      var el = document.getElementById('concertClosing');
      if (el) {
        el.classList.remove('closing--visible');
        el.style.display = 'none';
      }
      var link = document.getElementById('closingChapterLink');
      if (link) {
        link.style.display = 'none';
        link.classList.remove('closing-link--visible');
      }
    },

    /* ---- Script Panel ---- */

    toggleScript: function () {
      var panel = document.getElementById('playerScriptPanel');
      var btn = document.getElementById('btnScriptToggle');
      if (!panel || !btn) return;

      if (panel.style.display === 'none') {
        panel.style.display = '';
        btn.textContent = 'Hide the Script';
      } else {
        panel.style.display = 'none';
        btn.textContent = 'Read the Script';
      }
    },

    /* ---- Progress / Time ---- */

    updateProgress: function () {
      if (!this.audio.duration) return;
      var pct = (this.audio.currentTime / this.audio.duration) * 100;

      var fill = document.getElementById('playerProgressFill');
      var seek = document.getElementById('playerSeek');
      var curTime = document.getElementById('playerCurrentTime');

      if (fill) fill.style.width = pct + '%';
      if (seek) seek.value = pct;
      if (curTime) curTime.textContent = this.formatTime(this.audio.currentTime);
    },

    updateDuration: function () {
      if (this.audio.duration && isFinite(this.audio.duration)) {
        var durEl = document.getElementById('playerDuration');
        if (durEl) durEl.textContent = this.formatTime(this.audio.duration);
      }
    },

    formatTime: function (seconds) {
      var m = Math.floor(seconds / 60);
      var s = Math.floor(seconds % 60);
      return m + ':' + (s < 10 ? '0' : '') + s;
    },

    /* ---- Mobile Now-Playing Bar ---- */

    setupMobileBar: function () {
      var self = this;
      var bar = document.getElementById('mobileNowPlaying');
      var player = document.getElementById('concertPlayer');
      if (!bar || !player) return;

      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (self.isPlaying || self.audio.currentTime > 0) {
            bar.style.display = entry.isIntersecting ? 'none' : 'flex';
          }
        });
      }, { threshold: 0.1 });

      observer.observe(player);
    },

    /* ---- Program Notes Panel ---- */

    updateProgramNotes: function (mvt) {
      var panel = document.getElementById('chProgramPanel');
      if (!panel) return;

      // Collapse panel on movement change
      panel.classList.remove('ch-program-panel--expanded');
      var toggleBtn = panel.querySelector('[data-action="toggle-program-notes"]');
      if (toggleBtn) toggleBtn.innerHTML = 'Read more &darr;';

      // Populate fields
      var teaserEl = document.getElementById('chProgramTeaser');
      var arcEl = document.getElementById('chProgramArc');
      var noteEl = document.getElementById('chProgramNote');
      var keyEl = document.getElementById('chProgramKey');
      var tempoEl = document.getElementById('chProgramTempo');
      var leitmotifEl = document.getElementById('chProgramLeitmotif');
      var formEl = document.getElementById('chProgramForm');
      var dynamicEl = document.getElementById('chProgramDynamic');
      var instrumentsEl = document.getElementById('chProgramInstruments');
      var beatitudeRow = document.getElementById('chProgramBeatitudeRow');
      var beatitudeEl = document.getElementById('chProgramBeatitude');

      if (teaserEl) teaserEl.textContent = mvt.teaser || '';
      if (arcEl) arcEl.textContent = mvt.emotionalArc || '';
      if (noteEl) noteEl.textContent = mvt.programNote || '';
      if (keyEl) keyEl.textContent = mvt.key || '';
      if (tempoEl) tempoEl.textContent = mvt.tempo || '';
      if (formEl) formEl.textContent = mvt.formType || '';
      if (dynamicEl) dynamicEl.textContent = mvt.dynamicRange || '';

      // Leitmotif tier with indicator
      if (leitmotifEl) {
        var tier = mvt.leitmotifTier || 'Absent';
        var slug = 'absent';
        var indicator = '\u25CB'; // ○
        if (tier === 'Full Statement') { slug = 'full'; indicator = '\u25CF'; } // ●
        else if (tier === 'Echo Fragment') { slug = 'echo'; indicator = '\u25C9'; } // ◉
        leitmotifEl.className = 'ch-program-leitmotif ch-leitmotif-' + slug;
        leitmotifEl.textContent = indicator + ' ' + tier;
      }

      // Featured instruments as pill tags
      if (instrumentsEl) {
        instrumentsEl.innerHTML = '';
        var instruments = mvt.featuredInstruments || [];
        for (var i = 0; i < instruments.length; i++) {
          var tag = document.createElement('span');
          tag.className = 'ch-instrument-tag';
          tag.textContent = instruments[i];
          instrumentsEl.appendChild(tag);
        }
      }

      // Beatitude row: show/hide
      if (beatitudeRow) {
        beatitudeRow.style.display = mvt.beatitude ? '' : 'none';
      }
      if (beatitudeEl) {
        beatitudeEl.textContent = mvt.beatitude || '';
      }
    },

    toggleProgramNotes: function (btn) {
      var panel = document.getElementById('chProgramPanel');
      if (!panel) return;
      var expanded = panel.classList.toggle('ch-program-panel--expanded');
      if (btn) btn.innerHTML = expanded ? 'Close &uarr;' : 'Read more &darr;';
    },

    updateMobileBar: function () {
      var mvt = this.manifest.movements[this.currentIndex];
      var numEl = document.getElementById('mobileNpNumber');
      var titleEl = document.getElementById('mobileNpTitle');
      if (numEl) numEl.textContent = mvt.number + '.';
      if (titleEl) titleEl.textContent = mvt.title;
    }
  };

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { ConcertPlayer.init(); });
  } else {
    ConcertPlayer.init();
  }
})();
