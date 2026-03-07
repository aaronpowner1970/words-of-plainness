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

            // Store via unified reflection system
            try {
                var chapterId = document.body.dataset.chapter || 'unknown';

                // Read current confidence from active stars
                var confidence = 0;
                document.querySelectorAll('.star-btn.active').forEach(function () {
                    confidence++;
                });

                if (window.wopReflections) {
                    window.wopReflections.save({
                        chapterId: chapterId,
                        type: 'commitment',
                        promptLabel: cardTitle,
                        content: labelText,
                        meta: { cardId: 'card-' + card, tier: selected.value, confidence: confidence }
                    });

                    // Save reflection text if present
                    var reflectionArea = document.querySelector('#card-' + card + ' .reflection-area');
                    if (reflectionArea && reflectionArea.value.trim()) {
                        window.wopReflections.save({
                            chapterId: chapterId,
                            type: 'reflection',
                            promptLabel: cardTitle + ' (Reflection)',
                            content: reflectionArea.value.trim(),
                            meta: { cardId: 'card-' + card }
                        });
                    }
                }
            } catch (e) {
                // storage unavailable — fail silently
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

            // Update confidence on all existing commitment entries for this chapter
            if (window.wopReflections) {
                try {
                    var chapterId = document.body.dataset.chapter || 'unknown';
                    var entries = window.wopReflections.load(chapterId);
                    var updated = false;
                    entries.forEach(function (e) {
                        if (e.type === 'commitment' && e.meta) {
                            e.meta.confidence = rating;
                            updated = true;
                        }
                    });
                    if (updated) {
                        // Write back the full array (entries are newest-first from load,
                        // but writeBucket expects any order)
                        localStorage.setItem('wop-reflection-' + chapterId, JSON.stringify(entries));
                    }
                } catch (e) {
                    // fail silently
                }
            }
        });
    });

    // ---- Restore Saved State on Load ----
    function restoreSavedState() {
        if (!window.wopReflections) return;

        try {
            var chapterId = document.body.dataset.chapter || 'unknown';
            var entries = window.wopReflections.load(chapterId);

            // Track which cards have been restored (newest first, first match wins)
            var restoredCards = {};
            var maxConfidence = 0;

            entries.forEach(function (entry) {
                if (entry.type === 'commitment' && entry.meta && entry.meta.cardId) {
                    var cardId = entry.meta.cardId;     // e.g. "card-1"
                    var match = cardId.match(/^card-(\d+)$/);
                    if (!match || restoredCards[cardId]) return;
                    restoredCards[cardId] = true;

                    var cardNum = match[1];
                    var tier = entry.meta.tier;
                    var labelText = entry.content;

                    // Restore radio selection
                    var radio = document.querySelector('input[name="commit-' + cardNum + '"][value="' + tier + '"]');
                    if (radio) {
                        radio.checked = true;
                        var option = radio.closest('.commitment-option');
                        if (option) option.classList.add('selected');
                    }

                    // Restore custom text
                    if (tier === 'custom' && radio) {
                        var customRow = radio.closest('.custom-input-row');
                        if (customRow) {
                            var textInput = customRow.querySelector('input[type="text"]');
                            if (textInput) textInput.value = labelText;
                        }
                    }

                    // Restore summary
                    var summaryItem = document.querySelector('.summary-item[data-summary="' + cardNum + '"]');
                    if (summaryItem && entry.promptLabel) {
                        summaryItem.classList.remove('empty');
                        var itemText = summaryItem.querySelector('.item-text');
                        if (itemText) {
                            itemText.textContent = entry.promptLabel + ': ' + labelText;
                        }
                    }

                    // Track highest confidence
                    if (entry.meta.confidence && entry.meta.confidence > maxConfidence) {
                        maxConfidence = entry.meta.confidence;
                    }
                }

                // Restore card reflections
                if (entry.type === 'reflection' && entry.meta && entry.meta.cardId) {
                    var rCardId = entry.meta.cardId;
                    var rMatch = rCardId.match(/^card-(\d+)$/);
                    if (rMatch) {
                        var reflectionArea = document.querySelector('#card-' + rMatch[1] + ' .reflection-area');
                        if (reflectionArea && !reflectionArea.value) {
                            reflectionArea.value = entry.content || '';
                        }
                    }
                }
            });

            // Restore star rating
            if (maxConfidence > 0) {
                document.querySelectorAll('.star-btn').forEach(function (s) {
                    if (parseInt(s.dataset.star, 10) <= maxConfidence) {
                        s.classList.add('active');
                    }
                });
            }
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
