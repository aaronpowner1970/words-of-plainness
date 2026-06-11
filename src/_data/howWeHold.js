/* ============================================================
   HOW-WE-HOLD-THIS — reader-facing confessional clarifications
   Keyed by article-section id (matches WOP_GODEEPER keying).
   Consumed in articles.njk as window.WOP_HOLD and injected by
   src/js/articles-howwehold.js. Authored prose (Aaron).
   Touches neither the locked declaration markup nor the apparatus.

   Per entry:
     targetArticle  data-article of the span the inline cue attaches to
     targetSpan     data-span of that span
     label          inline cue label + disclosure title
     scent          one-line subtitle under the disclosure toggle
     html           disclosure body (trusted authored HTML)
   ============================================================ */

module.exports = {
  'of-fellow-believers': {
    targetArticle: 'A08',
    targetSpan: 's7',
    label: 'How we hold this',
    scent: 'A word on the body of Christ — larger, older, and held in grace',
    html: [
      '<p>This article is written as a sanctuary, not a verdict. When we say the body of Christ is larger than any single denomination and older than every division, we mean it in the widest and most generous sense the words will bear — in the spirit of grace, not of audit.</p>',

      '<p>The Good Shepherd said, <em>“Other sheep I have, which are not of this fold”</em> ' +
        '(<a class="hw-scripture" href="https://www.churchofjesuschrist.org/study/scriptures/nt/john/10?id=p16#p16" target="_blank" rel="noopener">John 10:16</a>). ' +
        'We take Him at His word: the fold is His to name, not ours.</p>',

      '<p>We read even the hardest scriptures this way. When the Book of Mormon speaks of two churches ' +
        '(<a class="hw-scripture" href="https://www.churchofjesuschrist.org/study/scriptures/bofm/1-ne/14?id=p10#p10" target="_blank" rel="noopener">1 Nephi 14:10</a>), ' +
        'we do not hear a roll call of denominations — the church of the Lamb is every soul who comes to Christ, in every tradition. ' +
        'In opposition to this is the spirit of contention itself. When the disciples asked to call down fire on a village that did not receive Christ in the way they imagined, He turned and rebuked them: ' +
        '<em>“Ye know not what manner of spirit ye are of”</em> ' +
        '(<a class="hw-scripture" href="https://www.churchofjesuschrist.org/study/scriptures/nt/luke/9?id=p55-p56#p55" target="_blank" rel="noopener">Luke 9:55–56</a>).</p>',

      '<p>What the creeds call the communion of saints, what the Reformed call the invisible church, what we confess as the Church of the Lamb of God — these are three vocabularies for one trans-temporal body. We do not ask you to trade your words for ours; we ask only to recognize one another within the one body.</p>',

      '<p>When we say the walls were not built by Him, and that we refuse to defend them, we are not dismissing your doctrine or your tradition. We ask only that we stop building walls out of them. We may hold our doctrine as firmly as ever and still refuse to let differences over orthodoxy, reformation, restoration, or the interpretation of scripture decide who belongs to Christ or who may sit at His table. <em>The conviction stays; the gatekeeping goes.</em></p>',

      '<p>Each church rightly governs its own membership, its own ordinances, its own table. We make no claim on how any tradition orders its house. We say only this: none of us has the right to stand between the sheep and the Good Shepherd.</p>'
    ].join('')
  }
};
