/* ============================================================
   CARD-CHAPTER INTERACTIVITY
   Tab switching, commitment saves, summary updates, star rating
   ============================================================ */

(function () {
    'use strict';

    // ---- Tab Switching ----
    document.querySelectorAll('.card-tab').forEach(function (tab) {
        tab.addEventListener('click', function () {
            var card = this.dataset.card;
            var target = this.dataset.tab;

            document.querySelectorAll('.card-tab[data-card="' + card + '"]').forEach(function (t) {
                t.classList.remove('active');
            });
            document.querySelectorAll('.card-panel[data-card="' + card + '"]').forEach(function (p) {
                p.classList.remove('active');
            });

            this.classList.add('active');
            var panel = document.querySelector('.card-panel[data-card="' + card + '"][data-panel="' + target + '"]');
            if (panel) panel.classList.add('active');
        });
    });

    // ---- Commitment Option Visual Feedback ----
    document.querySelectorAll('.commitment-option').forEach(function (opt) {
        opt.addEventListener('click', function () {
            var group = this.closest('.commitment-options');
            if (!group) return;
            group.querySelectorAll('.commitment-option').forEach(function (o) {
                o.classList.remove('selected');
            });
            this.classList.add('selected');
        });
    });

    // ---- Save Button Handler ----
    document.querySelectorAll('.card-save-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var card = this.dataset.card;
            var selected = document.querySelector('input[name="commit-' + card + '"]:checked');

            if (!selected) {
                this.style.animation = 'cardShake 0.3s ease';
                var self = this;
                setTimeout(function () { self.style.animation = ''; }, 300);
                return;
            }

            var labelText = selected.value;

            // Check for custom input
            if (selected.value === 'custom') {
                var customRow = selected.closest('.custom-input-row');
                if (customRow) {
                    var customField = customRow.querySelector('input[type="text"]');
                    labelText = (customField && customField.value) ? customField.value : 'Custom practice (not specified)';
                }
            } else if (selected.value === 'na') {
                labelText = 'Skipped';
            } else {
                // Use the visible option text
                var optionEl = selected.closest('.commitment-option');
                if (optionEl) {
                    var textEl = optionEl.querySelector('.option-text');
                    if (textEl) {
                        // Get text without the tag span
                        var clone = textEl.cloneNode(true);
                        var tagEl = clone.querySelector('.option-tag');
                        if (tagEl) tagEl.remove();
                        labelText = clone.textContent.trim();
                    }
                }
            }

            // Get card title from header
            var cardEl = document.getElementById('card-' + card);
            var cardTitle = '';
            if (cardEl) {
                var h3 = cardEl.querySelector('.card-header-text h3');
                if (h3) cardTitle = h3.textContent;
            }

            // Truncate label if too long
            if (labelText.length > 80) {
                labelText = labelText.substring(0, 77) + '…';
            }

            // Update summary
            var summaryItem = document.querySelector('.summary-item[data-summary="' + card + '"]');
            if (summaryItem) {
                summaryItem.classList.remove('empty');
                var itemText = summaryItem.querySelector('.item-text');
                if (itemText) {
                    itemText.textContent = cardTitle + ': ' + labelText;
                }
            }

            // Visual feedback on button
            var originalHTML = this.innerHTML;
            this.classList.add('saved');
            this.innerHTML = '✓ Saved';
            var feedback = document.querySelector('.save-feedback[data-card="' + card + '"]');
            if (feedback) feedback.classList.add('show');

            var self = this;
            setTimeout(function () {
                self.classList.remove('saved');
                self.innerHTML = originalHTML;
                if (feedback) feedback.classList.remove('show');
            }, 2500);

            // Store in localStorage for persistence
            try {
                var chapterKey = 'wop-card-' + (document.body.dataset.chapter || 'unknown');
                var saved = JSON.parse(localStorage.getItem(chapterKey) || '{}');
                saved['card-' + card] = {
                    value: selected.value,
                    label: labelText,
                    title: cardTitle,
                    timestamp: new Date().toISOString()
                };
                // Save reflection text if present
                var reflectionArea = document.querySelector('#card-' + card + ' .reflection-area');
                if (reflectionArea && reflectionArea.value.trim()) {
                    saved['card-' + card].reflection = reflectionArea.value.trim();
                }
                localStorage.setItem(chapterKey, JSON.stringify(saved));
            } catch (e) {
                // localStorage unavailable — fail silently
            }
        });
    });

    // ---- Star Rating ----
    document.querySelectorAll('.star-btn').forEach(function (star) {
        star.addEventListener('click', function () {
            var rating = parseInt(this.dataset.star, 10);
            document.querySelectorAll('.star-btn').forEach(function (s) {
                if (parseInt(s.dataset.star, 10) <= rating) {
                    s.classList.add('active');
                } else {
                    s.classList.remove('active');
                }
            });

            // Store rating
            try {
                var chapterKey = 'wop-card-' + (document.body.dataset.chapter || 'unknown');
                var saved = JSON.parse(localStorage.getItem(chapterKey) || '{}');
                saved.confidence = rating;
                localStorage.setItem(chapterKey, JSON.stringify(saved));
            } catch (e) {
                // fail silently
            }
        });
    });

    // ---- Restore Saved State on Load ----
    function restoreSavedState() {
        try {
            var chapterKey = 'wop-card-' + (document.body.dataset.chapter || 'unknown');
            var saved = JSON.parse(localStorage.getItem(chapterKey) || '{}');

            Object.keys(saved).forEach(function (key) {
                if (key === 'confidence') {
                    var rating = saved.confidence;
                    document.querySelectorAll('.star-btn').forEach(function (s) {
                        if (parseInt(s.dataset.star, 10) <= rating) {
                            s.classList.add('active');
                        }
                    });
                    return;
                }

                var match = key.match(/^card-(\d+)$/);
                if (!match) return;
                var cardNum = match[1];
                var data = saved[key];

                // Restore radio selection
                var radio = document.querySelector('input[name="commit-' + cardNum + '"][value="' + data.value + '"]');
                if (radio) {
                    radio.checked = true;
                    var option = radio.closest('.commitment-option');
                    if (option) option.classList.add('selected');
                }

                // Restore custom text
                if (data.value === 'custom') {
                    var customRow = radio ? radio.closest('.custom-input-row') : null;
                    if (customRow) {
                        var textInput = customRow.querySelector('input[type="text"]');
                        if (textInput) textInput.value = data.label;
                    }
                }

                // Restore reflection
                if (data.reflection) {
                    var reflectionArea = document.querySelector('#card-' + cardNum + ' .reflection-area');
                    if (reflectionArea) reflectionArea.value = data.reflection;
                }

                // Restore summary
                var summaryItem = document.querySelector('.summary-item[data-summary="' + cardNum + '"]');
                if (summaryItem && data.title) {
                    summaryItem.classList.remove('empty');
                    var itemText = summaryItem.querySelector('.item-text');
                    if (itemText) {
                        itemText.textContent = data.title + ': ' + data.label;
                    }
                }
            });
        } catch (e) {
            // fail silently
        }
    }

    document.addEventListener('DOMContentLoaded', restoreSavedState);

    // ---- Learning Tools Accordion ----
    var ccLtToggle = document.getElementById('ccLtToggle');
    var ccLtPanel = document.getElementById('ccLtPanel');
    if (ccLtToggle && ccLtPanel) {
        ccLtToggle.addEventListener('click', function () {
            var expanded = this.getAttribute('aria-expanded') === 'true';
            this.setAttribute('aria-expanded', !expanded);
            ccLtPanel.hidden = expanded;
        });
    }
})();

// ============================================================
// LEARNING TOOLS — Modal & Slide Carousel (global scope)
// ============================================================

function openCcModal(id) {
    var modal = document.getElementById(id);
    var backdrop = document.getElementById('ccModalBackdrop');
    if (modal) modal.classList.add('open');
    if (backdrop) backdrop.classList.add('visible');
    document.body.style.overflow = 'hidden';
}

function closeCcModals() {
    document.querySelectorAll('.cc-modal').forEach(function (m) {
        m.classList.remove('open');
    });
    var backdrop = document.getElementById('ccModalBackdrop');
    if (backdrop) backdrop.classList.remove('visible');
    document.body.style.overflow = '';
    // Pause testimony audio if playing
    var audio = document.getElementById('ccTestimonyAudio');
    if (audio) audio.pause();
}

// Backdrop click closes modals
(function () {
    var backdrop = document.getElementById('ccModalBackdrop');
    if (backdrop) {
        backdrop.addEventListener('click', closeCcModals);
    }
    // Escape key closes modals
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && document.querySelector('.cc-modal.open')) {
            closeCcModals();
        }
    });
})();

// ---- Slide Carousel ----
var ccCurrentSlide = 1;
var ccTotalSlides = 1;

(function () {
    var counterEl = document.querySelector('.cc-slide-counter');
    if (counterEl) {
        var match = counterEl.textContent.match(/\/\s*(\d+)/);
        if (match) ccTotalSlides = parseInt(match[1], 10);
    }
})();

function ccSlideNav(dir) {
    ccCurrentSlide += dir;
    if (ccCurrentSlide < 1) ccCurrentSlide = ccTotalSlides;
    if (ccCurrentSlide > ccTotalSlides) ccCurrentSlide = 1;
    var num = String(ccCurrentSlide).padStart(2, '0');
    var img = document.getElementById('ccSlideImg');
    if (img) {
        // Replace the slide number in the existing src path
        img.src = img.src.replace(/slide-\d+\.png/, 'slide-' + num + '.png');
        img.alt = 'Study slide ' + ccCurrentSlide + ' of ' + ccTotalSlides;
    }
    var numEl = document.getElementById('ccSlideNum');
    if (numEl) numEl.textContent = ccCurrentSlide;
}
