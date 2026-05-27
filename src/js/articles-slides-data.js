/* ============================================================
   ARTICLE STUDY SLIDES — Data
   Companion to articles-slides.js (the viewer).

   Defines window.WOP_ARTICLE_SLIDES — the per-article slide
   sets consumed by the viewer. Loaded BEFORE articles-slides.js
   in src/_includes/layouts/articles.njk.

   ADDING ARTICLES: append a key (e.g. "A02") to the object.
   Article id is derived from each section's data-audio (AP_A##_...)
   by the viewer.

   Slide types: title | points | concept | scripture | discuss | doorway
   Full schema/anatomy reference: working-folder/WoP_Article_Slides_SpinUp_Prompt.md
   ============================================================ */

window.WOP_ARTICLE_SLIDES = {
    "A01": {
        eyebrow: "Articles of Interfaith Discipleship · Of Plainness",
        slides: [
            {
                type: "title",
                number: "Article 1",
                title: "Of Plainness",
                lead: "We accept that human knowledge of truth is limited by mortality—for now."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "We know in part. No mortal has walked the full ranges of heaven to chart its glories.",
                    "We honor institutions, creeds, and traditions—but we will not dogmatize beyond what God has revealed plainly.",
                    "The weighty things of God are plain, and they exist in plainness for our salvation.",
                    "The secret things belong to God. They are not ours to dictate or dogmatize."
                ]
            },
            {
                type: "concept",
                label: "A word for the posture",
                term: "Merognosis",
                def: "Partial knowing—holding firmly to what God has made plain, while leaving the unrevealed to Him.",
                sub: "It refuses two errors: the overreach of gnosis (claiming hidden knowledge) and the underreach of agnosis (claiming nothing can be known)."
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "For we know in part, and we prophesy in part.", ref: "1 Corinthians 13:9", url: "nt/1-cor/13?id=p9#p9" },
                    { text: "The secret things belong unto the LORD our God…", ref: "Deuteronomy 29:29", url: "ot/deut/29?id=p29#p29" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "Is there a conviction you hold about God or faith that may be built more on what you inherited than on what you have personally witnessed?" },
                    { tag: "Together", text: "How might keeping justice, mercy, and faithfulness at the center—while still holding our convictions charitably—reduce contention and condemnation among believers?" }
                ]
            },
            {
                type: "doorway",
                label: "Go deeper",
                title: "Merognosticism — A Plain Confession of Partial Knowing",
                blurb: "How “knowing in part” becomes a posture of peace rather than a confession of defeat.",
                href: "https://www.wordsofplainness.org/studies/merognosticism/"
            }
        ],
        facilitator: {
            intro: "Examples to seed the discussion.",
            scriptureExamples: [
                "The Pharisees tithed mint, dill, and cumin yet neglected the weightier matters (Matthew 23:23)—precision in the small, blindness to the heart.",
                "Jews and Samaritans despised each other as the false chosen, while both watched for the same Messiah (John 4).",
                "The first church nearly broke over circumcision and the law of Moses until the Jerusalem council sorted the essential from the non-essential (Acts 15)."
            ],
            liveExamples: [
                "Are the spiritual gifts for today? (cessationism / continuationism)",
                "Which canon and translation carry God’s word",
                "How grace and the human will meet (Calvinism / Arminianism)",
                "Infant or believer’s baptism",
                "Catholic and Orthodox, and the long schisms of the church"
            ],
            frame: "The point isn’t to decide who is right—Article 1 won’t. It is to ask: has the conviction become a test of fellowship or a weapon against a brother or sister? And do justice, mercy, and faithfulness still hold the center?",
            probe: "What is one teaching God never made plain that you’ve seen turned into a test of fellowship?"
        }
    }
};
