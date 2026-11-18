/* ============================================================
   G5 · REFLECTION INVITED, NEVER REQUIRED
   Teaching Practices Standard v1.1, gate G5 and its model wording
   (WoP\ops\WoP-Teaching-Practices-Standard.md). Word for word; do not edit
   here without amending the standard. CODE-SITE-20, SITE step 30.

     first  the first reflection prompt on a page, or in a separately opened
            panel (the Reflections panel; the Reflect · Journal · Witness
            pause panel)
     later  each later prompt on the same page or panel

     read      the reader is reading
     continue  the reader is watching a film or working through an
               interactive module ("read on" becomes "continue")

   The line sits between the prompt and its response field and is tied to
   the field (aria-describedby). Templates use macros/g5.njk; the Reflections
   panel receives its line from components/reflections-panel.njk.
   ============================================================ */
module.exports = {
  first: {
    read: "You are invited to pause and write a personal reflection here, or simply to read on.",
    continue: "You are invited to pause and write a personal reflection here, or simply to continue."
  },
  later: {
    read: "Pause to reflect, or simply read on.",
    continue: "Pause to reflect, or simply continue."
  }
};
