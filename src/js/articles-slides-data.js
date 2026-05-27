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
    },
    "A02": {
        eyebrow: "Articles of Interfaith Discipleship · Of God",
        slides: [
            {
                type: "title",
                number: "Article 2",
                title: "Of God",
                lead: "We believe in God, the Eternal Father of our spirits, whose love for His children is without limit."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "God is the Eternal Father of our spirits—His purposes good, His love without limit.",
                    "His power sustains our existence; nothing is beyond His knowledge, and nothing beyond His care.",
                    "No mortal can claim to know the full nature of God; we know only what He reveals plainly.",
                    "Of heaven’s eternal order and populations we stay carefully neutral, for the sake of unity."
                ]
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "For as the heavens are higher than the earth, so are my ways higher than your ways, and my thoughts than your thoughts.", ref: "Isaiah 55:9", url: "ot/isa/55?id=p9#p9" },
                    { text: "Shall we not much rather be in subjection unto the Father of spirits, and live?", ref: "Hebrews 12:9", url: "nt/heb/12?id=p9#p9" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "When did you last experience something you could not attribute to anything but God?" },
                    { tag: "Together", text: "Our traditions describe God’s nature in different language. What can we affirm together about who He is—without requiring one another to speak of Him in identical terms?" }
                ]
            }
        ],
        facilitator: {
            intro: "Article 2 confesses the God we share while declining to map what He has not revealed. Use these to surface where confidence and restraint meet.",
            scriptureExamples: [
                "Moses asked to see God’s glory and was shown His goodness, not His full face (Exodus 33:18–23)—even the prophet knew in part.",
                "Job demanded answers and received the whirlwind’s questions instead (Job 38)—the LORD’s ways are higher, not smaller.",
                "Paul on Mars’ Hill named the ‘unknown God’ the Athenians already groped after (Acts 17:23)—common ground before correction."
            ],
            liveExamples: [
                "How the persons of the Godhead relate (Trinitarian formulations across traditions)",
                "Whether God is impassible or genuinely moved by His creatures",
                "How divine sovereignty and human freedom fit together",
                "What can be known of God by reason versus by revelation alone"
            ],
            frame: "Article 2 does not settle these. It confesses the Father whose love is without limit and leaves the unrevealed to Him. The question is not whose formulation wins, but whether we can worship together the God we both confess.",
            probe: "Where have you seen a description of God’s nature become a wall between believers who actually love the same God?"
        }
    },
    "A03": {
        eyebrow: "Articles of Interfaith Discipleship · Of Creation and Life",
        slides: [
            {
                type: "title",
                number: "Article 3",
                title: "Of Creation and Life",
                lead: "We believe this life is not an accident and not a punishment, but a sphere God designed for our benefit."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "God made this world for His children—to live in flesh, walk by agency, meet good and evil, and grow.",
                    "This life is not an accident, not a punishment; even the fall was not beyond God’s plans.",
                    "Every soul has room to choose, to fall, to rise, and to be made new through His grace.",
                    "We are free to deny the Creator or to see the blessings—either way, the shaping takes place."
                ]
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "Thorns also and thistles shall it bring forth to thee… In the sweat of thy face shalt thou eat bread.", ref: "Genesis 3:18–19", url: "ot/gen/3?id=p18#p18" },
                    { text: "…tribulation worketh patience; and patience, experience; and experience, hope.", ref: "Romans 5:3–4", url: "nt/rom/5?id=p3#p3" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "What is something difficult in your life that, if it truly came from a loving God’s hand, you might receive differently?" },
                    { tag: "Together", text: "When have you seen hardship shape someone’s character toward Christ? How can a community hold that truth without ever telling a suffering person that their pain is ‘good for them’?" }
                ]
            }
        ],
        facilitator: {
            intro: "Article 3 confesses a purposeful creation without dogmatizing the mechanics of how it came to be. Keep the focus on meaning, not models.",
            scriptureExamples: [
                "Joseph told his brothers, ‘Ye thought evil against me; but God meant it unto good’ (Genesis 50:20)—the same events, two readings.",
                "The man born blind was not punished for sin, but born so ‘that the works of God should be made manifest’ (John 9:1–3).",
                "Paul’s thorn was not removed; grace was made sufficient in the weakness (2 Corinthians 12:7–9)."
            ],
            liveExamples: [
                "How and over what span God created (young-earth, old-earth, evolutionary creation)",
                "The historicity and shape of the Fall",
                "Whether there was death before the Fall",
                "The origin of the human soul"
            ],
            frame: "Article 3 takes no side on the how. It confesses that the conditions of mortality are God-designed for our growth. Disagreement over mechanism is not disagreement over the Maker.",
            probe: "Where has a debate about how God created drawn energy away from the harder, plainer work of trusting why He did?"
        }
    },
    "A04": {
        eyebrow: "Articles of Interfaith Discipleship · Of God’s Word",
        slides: [
            {
                type: "title",
                number: "Article 4",
                title: "Of God’s Word",
                lead: "We receive God’s word through prophets—imperfect servants whose witness survives because the revelation was God’s, not theirs."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "God’s word comes through prophets, mortal men and women, whose witness survives despite their flaws.",
                    "We worship God only. We respect—but do not worship—prophets or scriptures as idols.",
                    "God spoke in ages past, speaks today, and will yet speak in generations to come.",
                    "Each tradition keeps its own canon; we exhort every soul to search for what brings them to Christ."
                ]
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "…holy men of God spake as they were moved by the Holy Ghost.", ref: "2 Peter 1:21", url: "nt/2-pet/1?id=p21#p21" },
                    { text: "Trust in the Lord with all thine heart; and lean not unto thine own understanding.", ref: "Proverbs 3:5", url: "ot/prov/3?id=p5#p5" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "What has brought you closest to Christ — scripture, experience, community, or something else entirely?" },
                    { tag: "Together", text: "We hold different canons and read them differently. How can we honor one another’s scriptures as roads toward Christ without pretending our differences don’t exist?" }
                ]
            },
            {
                type: "doorway",
                label: "Go deeper",
                title: "Broken Vessels — Universal Fallibility and the Reach of Grace",
                blurb: "Why God’s choice of imperfect, breakable servants is not a flaw in His word but a feature of His grace.",
                href: "https://www.wordsofplainness.org/studies/broken-vessels/"
            }
        ],
        facilitator: {
            intro: "Article 4 holds revelation high and the messengers humble. The live disagreements here are about which words are God’s word—keep them framed as posture.",
            scriptureExamples: [
                "Moses, slow of speech, and Jonah, in flight—God spoke through reluctant and flawed men (Exodus 4:10; Jonah 1:3).",
                "The Bereans ‘searched the scriptures daily’ to test even Paul’s preaching (Acts 17:11)—reverence and scrutiny together.",
                "Peter wrote that prophecy came not ‘by the will of man,’ yet Peter himself was later rebuked to his face (2 Peter 1:21; Galatians 2:11)—the vessel broken, the word still true."
            ],
            liveExamples: [
                "Which books belong in the canon (Protestant, Catholic, Orthodox, Restoration)",
                "Which translation carries God’s word most faithfully",
                "Whether revelation continues today or closed with the apostles",
                "How to weigh scripture, tradition, and the Spirit’s present witness"
            ],
            frame: "Article 4 will not adjudicate whose canon is complete. It confesses that what God spoke plainly has been preserved, and that the Spirit confirms what He still speaks. The dividing line is never ‘whose Bible is bigger’ but ‘what brings this soul to Christ.’",
            probe: "Where have you seen reverence for the messenger quietly slide into worship of the messenger—or contempt for a brother whose canon differs from yours?"
        }
    },
    "A05": {
        eyebrow: "Articles of Interfaith Discipleship · Of Jesus Christ",
        slides: [
            {
                type: "title",
                number: "Article 5",
                title: "Of Jesus Christ",
                lead: "We proclaim Jesus of Nazareth, the promised Messiah—Divinity made flesh, the living image of the Father’s heart."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "God sent the promised Messiah—Jesus of Nazareth, the true Christ, Divinity made flesh.",
                    "What the prophets spoke only in part, Christ embodied in whole and in perfection.",
                    "Born of Mary, He lived sinless, healed the sick, forgave the broken, and loved without measure.",
                    "He suffered for our sins, died on the cross, and rose in glory on the third day."
                ]
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "And the Word was made flesh, and dwelt among us… full of grace and truth.", ref: "John 1:14", url: "nt/john/1?id=p14#p14" },
                    { text: "…who went about doing good… for God was with him.", ref: "Acts 10:38", url: "nt/acts/10?id=p38#p38" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "Who is Jesus Christ to you — right now, in this moment of your life?" },
                    { tag: "Together", text: "What is one thing about Jesus Christ that you could affirm shoulder to shoulder with a believer from a very different tradition—no caveats, no qualifications?" }
                ]
            }
        ],
        facilitator: {
            intro: "Article 5 is the cluster’s center of gravity—the one place the declaration proclaims rather than restrains. The facilitator’s task here is less to surface disagreement than to deepen worship.",
            scriptureExamples: [
                "Peter confessed, ‘Thou art the Christ, the Son of the living God,’ and Jesus called it revealed by the Father (Matthew 16:16–17).",
                "Thomas, who doubted, fell to ‘My Lord and my God’ when he saw the risen Christ (John 20:28).",
                "Even a Roman centurion at the cross said, ‘Truly this man was the Son of God’ (Mark 15:39)—the confession crosses every line."
            ],
            liveExamples: [
                "How the two natures of Christ relate (the historic Christological councils)",
                "How the Atonement accomplishes our salvation (the various theories)",
                "The manner of Christ’s presence in the Lord’s Supper",
                "How Mary is to be honored"
            ],
            frame: "Article 5 does not arbitrate the councils or the theories. It proclaims the person—born, crucified, risen—and lets Him be the living reference by whom every witness is measured. Here, agreement runs deeper than our explanations of it.",
            probe: "Where do our explanations of how Christ saves get treated as more essential than the fact that He does?"
        }
    },
    "A06": {
        eyebrow: "Articles of Interfaith Discipleship · Of Salvation",
        slides: [
            {
                type: "title",
                number: "Article 6",
                title: "Of Salvation",
                lead: "We believe salvation is offered through the grace of Jesus Christ—and we refuse to judge whom the Lord has saved."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "Salvation is offered through Christ’s grace, received by faith, made real through repentance.",
                    "It bears fruit in keeping His commandments and is sealed upon us by the Spirit of God.",
                    "We do not claim to know salvation’s full mechanism—and we refuse to judge whom the Lord has saved or rejected.",
                    "We proclaim only the person by whom salvation is offered: Jesus Christ."
                ]
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "For by grace are ye saved through faith; and that not of yourselves: it is the gift of God.", ref: "Ephesians 2:8", url: "nt/eph/2?id=p8#p8" },
                    { text: "Neither is there salvation in any other: for there is none other name under heaven given among men, whereby we must be saved.", ref: "Acts 4:12", url: "nt/acts/4?id=p12#p12" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "Is there someone you have mentally placed outside the reach of God’s grace? What would change if you were wrong?" },
                    { tag: "Together", text: "We disagree on how salvation works. How might we hold our convictions about the mechanism firmly while leaving the verdict—who is saved—entirely in God’s hands?" }
                ]
            }
        ],
        facilitator: {
            intro: "Article 6 is bold about the source of salvation and silent about the bookkeeping. The live disagreements here are old and deep—frame them as posture, never as a roster of the saved.",
            scriptureExamples: [
                "The thief on the cross was promised paradise with no time to be baptized or to prove his works (Luke 23:42–43).",
                "Peter learned at Cornelius’s house that ‘God is no respecter of persons,’ pouring His Spirit where He wills (Acts 10:34–35, 44–47).",
                "Jesus said the publican, not the proud Pharisee, ‘went down to his house justified’ (Luke 18:9–14)."
            ],
            liveExamples: [
                "How faith and works relate in justification (the Reformation-era divide and after)",
                "Whether saving grace can be resisted or finally lost",
                "The fate of those who never hear the gospel",
                "Predestination and human freedom"
            ],
            frame: "Article 6 will not draw the boundary of the saved. It proclaims Christ as the only Savior and then leaves the judgment to Him. We can argue the mechanism for a lifetime; we may not appoint ourselves the judge.",
            probe: "Whose name came to mind on the personal question—and what has it cost you to keep them on the outside of grace?"
        }
    },
    "A07": {
        eyebrow: "Articles of Interfaith Discipleship · Of the Kingdom at Hand",
        slides: [
            {
                type: "title",
                number: "Article 7",
                title: "Of the Kingdom at Hand",
                lead: "We proclaim the kingdom of heaven is not only for a distant day—Christ proclaimed it at hand, now."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "The kingdom of heaven is not only a distant promise—Christ proclaimed it at hand, within reach now.",
                    "Eternal life is not merely endless existence; it is knowing God and fellowship with His Son, beginning now.",
                    "We need not wait for death to find His rest, for perfection to taste His joy, or for glory to know His peace.",
                    "The Father’s will was never that we merely endure mortality—but that we should really live, beginning now."
                ]
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "…The time is fulfilled, and the kingdom of God is at hand: repent ye, and believe the gospel.", ref: "Mark 1:15", url: "nt/mark/1?id=p15#p15" },
                    { text: "And this is life eternal, that they might know thee the only true God, and Jesus Christ, whom thou hast sent.", ref: "John 17:3", url: "nt/john/17?id=p3#p3" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "Where do you most need to begin living now as though His kingdom were already yours?" },
                    { tag: "Together", text: "What does it look like, practically, for a community to ‘build the kingdom’ now—and how do we keep that work from becoming one more thing we use to measure each other?" }
                ]
            }
        ],
        facilitator: {
            intro: "Article 7 collapses the distance between ‘someday’ and ‘now.’ The disagreements here are about timing and the shape of the kingdom—frame them as posture, and keep the room’s eyes on the fruits already available.",
            scriptureExamples: [
                "Jesus told the Pharisees, ‘the kingdom of God is within you’ (Luke 17:20–21)—not only ahead, but among and within.",
                "Zacchaeus heard ‘this day is salvation come to this house’ before any waiting (Luke 19:9).",
                "The Samaritan woman left her waterpot to tell the city—joy arrived at the well, not at some later hour (John 4:28–29)."
            ],
            liveExamples: [
                "The timing and order of the last things (the millennial views)",
                "How ‘already’ and ‘not yet’ hold together in the kingdom",
                "Whether signs and gifts mark the kingdom’s present power",
                "How much the kingdom is realized in the visible church"
            ],
            frame: "Article 7 will not settle the eschatological charts. It proclaims that the kingdom’s peace, joy, and rest are within reach today, and that their fruits are the witness. We may differ on the timeline and still taste the same firstfruits now.",
            probe: "Where are you waiting for permission, perfection, or glory to begin living a life Christ says is already available?"
        }
    },
    "A08": {
        eyebrow: "Articles of Interfaith Discipleship · Of Fellow Believers",
        slides: [
            {
                type: "title",
                number: "Article 8",
                title: "Of Fellow Believers",
                lead: "We receive every soul who comes to Jesus Christ as brother, as sister, as fellow child of the same Father."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "We receive every soul who comes to Christ as brother, as sister—whether they return our love or not.",
                    "The body of Christ is larger than any single denomination and older than every division.",
                    "The walls that separate the Lord’s people were not built by Him—we refuse to defend them.",
                    "Nor will we defend any doctrine made into a weapon against a brother or sister who names His name."
                ]
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "For by one Spirit are we all baptized into one body… and have been all made to drink into one Spirit.", ref: "1 Corinthians 12:13", url: "nt/1-cor/12?id=p13#p13" },
                    { text: "Not rendering evil for evil, or railing for railing: but contrariwise blessing.", ref: "1 Peter 3:9", url: "nt/1-pet/3?id=p9#p9" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "Who is the hardest person for you to call family in Christ? What would it cost you to hold the door open to them?" },
                    { tag: "Together", text: "Where have you defended a wall between believers that, in honest reflection, Christ never built? What would it cost you to lay one brick of it down?" }
                ]
            },
            {
                type: "doorway",
                label: "Go deeper",
                title: "Contention, Gatekeeping, and the Reach of Christ",
                blurb: "How contention masquerades as conviction—and how the Shepherd reaches past the gates we build to keep His sheep apart.",
                href: "https://www.wordsofplainness.org/studies/contention-and-the-reach-of-christ/"
            }
        ],
        facilitator: {
            intro: "Article 8 is the cluster’s pivot from confession to fellowship. The disagreement here is not what to believe—it is who counts as family. Keep the dogma discipline tight: name the act (hardened into dogma, used as a weapon), never swipe at any tradition’s defined doctrines.",
            scriptureExamples: [
                "Paul rebuked the Corinthian factions—‘I am of Paul; and I of Apollos’—when Christ alone was crucified for them (1 Corinthians 1:10–13).",
                "John tried to silence one casting out devils ‘because he followeth not us,’ and Jesus answered, ‘he that is not against us is on our part’ (Mark 9:38–40).",
                "Christ prayed that His disciples ‘may be one’ so the world might believe (John 17:20–21)—unity as witness, not strategy."
            ],
            liveExamples: [
                "Whether sacraments performed in another tradition are valid",
                "Open vs. closed communion",
                "Whether Christians of other traditions are ‘fellow believers’ or mission targets",
                "Recognition of other churches’ baptisms and ordinations",
                "When a doctrinal difference rises to the level of separating fellowship"
            ],
            frame: "Article 8 will not adjudicate whose ordinances are valid or whose fellowship is real. It refuses to defend walls Christ did not build, and refuses to wield doctrine as a weapon against any soul who names His name. The discipline is the dogma/dogmatize line: we do not condemn doctrine; we refuse the weaponization of it.",
            probe: "Where has a true conviction in your tradition quietly hardened into a test of fellowship—and started to function as a wall instead of a witness?"
        }
    },
    "A09": {
        eyebrow: "Articles of Interfaith Discipleship · Of Finding Our Way",
        slides: [
            {
                type: "title",
                number: "Article 9",
                title: "Of Finding Our Way",
                lead: "We hold Jesus the Christ as the fixed point by whom every soul may find the way to God."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "Christ is the fixed North Star above every traveler’s path—what He taught is what He taught, what He was is what He was.",
                    "Trusting Him is more important than understanding Him; relationship precedes the accuracy of doctrine.",
                    "The Spirit is a compass within—but it must be calibrated to Christ; the scriptures are the sure map marking the way.",
                    "We walk by none of these alone—we walk by Christ, and by His Spirit, who leads us toward Him and never away."
                ]
            },
            {
                type: "concept",
                label: "The navigation Christ gives",
                term: "North Star · Compass · Map",
                def: "Three fixed gifts for finding the way: Christ Himself (the North Star), His Spirit within us (the compass), and the scriptures (the map).",
                sub: "The compass must be calibrated to the North Star; the map marks the way to the same Star. When any one of them seems to pull us away from Christ, we return our sighting to Him."
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "I am the way, the truth, and the life: no man cometh unto the Father, but by me.", ref: "John 14:6", url: "nt/john/14?id=p6#p6" },
                    { text: "…when he, the Spirit of truth, is come, he will guide you into all truth.", ref: "John 16:13", url: "nt/john/16?id=p13#p13" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "When you feel spiritually lost, which do you reach for first — scripture, the Spirit’s witness, or Christ as the fixed reference? Which do you tend to neglect?" },
                    { tag: "Together", text: "Christians have argued for centuries about which of the three—Christ, Spirit, scripture—should hold final authority. What does it look like to honor all three without forcing them to compete?" }
                ]
            }
        ],
        facilitator: {
            intro: "Article 9 is the cluster’s navigation chapter. The temptation in the room will be to elevate one instrument above the others. Hold the triangulation: any reading of Spirit or scripture that points away from Christ is a disturbed compass.",
            scriptureExamples: [
                "Jesus rebuked the scribes who ‘search the scriptures’ yet would not come to Him, the One the scriptures testified of (John 5:39–40)—the map mistaken for the destination.",
                "John taught his readers to ‘try the spirits whether they are of God,’ because not every inward whisper is His (1 John 4:1).",
                "The Bereans tested Paul’s preaching against scripture and received it gladly (Acts 17:11)—Spirit-led teaching, calibrated by the written word."
            ],
            liveExamples: [
                "Sola Scriptura vs. scripture-and-tradition (the Reformation-era divides)",
                "Whether the Spirit speaks fresh revelation today—and how to discern it",
                "How much weight to give the consensus of the historic church",
                "Whether private interpretation or confessional standards govern the disciple’s reading"
            ],
            frame: "Article 9 will not settle the authority question. It confesses that none of the three—Christ, Spirit, scripture—replaces the other. The Spirit calibrates to Christ; the map points to the same Star; the disciple walks by all three.",
            probe: "Where in your own walk has one instrument been so loud that the other two went silent—and what did that cost you?"
        }
    },
    "A10": {
        eyebrow: "Articles of Interfaith Discipleship · Of Living by Grace",
        slides: [
            {
                type: "title",
                number: "Article 10",
                title: "Of Living by Grace",
                lead: "We believe grace is not a license to sin—it is a divine trait and power, the character of God actively shaping us toward Christ."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "God speaks to every conscience open to hearing Him, whether we feel worthy or not.",
                    "Grace is not a license to sin—it is a divine trait and power, shaping us toward Christ.",
                    "The Christian life is a walk, a maturing, a becoming; no soul finishes in a day, and no soul is beyond His reach.",
                    "We do not stand between the Shepherd and His lambs—and we call to repentance any who try."
                ]
            },
            {
                type: "concept",
                label: "A word for what grace is",
                term: "Grace",
                def: "Not a license to sin—a divine trait and power: God’s own character actively shaping the disciple toward the likeness of Christ.",
                sub: "Grace saves; grace also changes. It is the power that makes the walk, the maturing, the becoming possible. No soul finishes in a day; no soul is beyond its reach."
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "But whoso shall offend one of these little ones which believe in me, it were better for him that a millstone were hanged about his neck, and that he were drowned in the depth of the sea.", ref: "Matthew 18:6", url: "nt/matt/18?id=p6#p6" },
                    { text: "Him that is weak in the faith receive ye, but not to doubtful disputations.", ref: "Romans 14:1", url: "nt/rom/14?id=p1#p1" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "Have you ever — even quietly, even unintentionally — stood between someone and the Shepherd? What did that look like?" },
                    { tag: "Together", text: "Christ’s harshest warnings landed not on outsiders but on insiders who gatekept God’s grace. What postures or habits in our communities could quietly slide us into the same role—and how do we help each other notice them in time?" }
                ]
            },
            {
                type: "doorway",
                label: "Go deeper",
                title: "Lord, Is It I? — A Call to Repentance",
                blurb: "Christ’s hardest warnings land on the insider, not the outsider. The disciple’s question is never ‘who do they think they are?’ but ‘Lord, is it I?’",
                href: "https://www.wordsofplainness.org/studies/lord-is-it-i/"
            }
        ],
        facilitator: {
            intro: "Article 10 is the cluster’s call to repentance—Christ’s protective warning aimed at His own community, not at outsiders. Keep the dogma discipline: this is the article where ‘modern Pharisees’ is named, but the aim is the disciple’s mirror, not the next tradition over.",
            scriptureExamples: [
                "Jesus saved His sharpest words for the lawyers who ‘took away the key of knowledge’ and the Pharisees who ‘shut up the kingdom of heaven against men’ (Luke 11:52; Matthew 23:13).",
                "Peter resisted Cornelius until the Spirit fell and forced the question: ‘who was I, that I could withstand God?’ (Acts 11:17)—the gatekeeper rebuked by God’s own visible welcome.",
                "When the disciples heard, ‘one of you shall betray me,’ not one of them pointed at another—each asked, ‘Lord, is it I?’ (Matthew 26:21–22)."
            ],
            liveExamples: [
                "How much of church discipline is correction and how much has become exclusion",
                "Whether ‘doctrinal soundness’ has, in practice, become a test of fellowship",
                "How traditions police their own members vs. how they treat outsiders who confess Christ",
                "Where preaching against sin slides into contempt for sinners"
            ],
            frame: "Article 10 names a discipline, not a target. The ‘modern Pharisees’ it warns against are not other traditions—they are the impulse in every disciple, including the author and the reader, to manage Christ’s grace toward someone else. The mirror is for us first.",
            probe: "Whose name surfaced when the millstone verse was read—and was it a sinner you’ve quietly judged, or a soul Christ would say you’ve stood between?"
        }
    },
    "A11": {
        eyebrow: "Articles of Interfaith Discipleship · Of Covenants and Commitments",
        slides: [
            {
                type: "title",
                number: "Article 11",
                title: "Of Covenants and Commitments",
                lead: "We are children of God by birth. We become disciples of Christ by covenant—and then we live it."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "We are children of God by birth; we become disciples of Christ by covenant.",
                    "We surrender our will into His—and then we live it. Not merely profess it. Live it.",
                    "The apostolic answer to ‘what shall we do?’ is as plain now as then: repent and be baptized in His name.",
                    "We walk, we pray, we endure—seeking the Kingdom that is at hand for eyes that see and willing hearts."
                ]
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "But be ye doers of the word, and not hearers only, deceiving your own selves.", ref: "James 1:22", url: "nt/james/1?id=p22#p22" },
                    { text: "Repent, and be baptized every one of you in the name of Jesus Christ for the remission of sins…", ref: "Acts 2:38", url: "nt/acts/2?id=p38#p38" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "What covenant or commitment do you most readily profess — and find hardest to actually live?" },
                    { tag: "Together", text: "Where in our shared life has the line between professing and living grown blurry—and what would it look like to help each other close that gap without slipping into judgment?" }
                ]
            }
        ],
        facilitator: {
            intro: "Article 11 is the cluster’s structural spine—where confession turns into committed life. The disagreements here are about forms (which ordinances, how, when) and about how covenant relates to grace. Hold the focus on doing, not on the comparative table of forms.",
            scriptureExamples: [
                "James taught that ‘faith without works is dead’—not because works save, but because living faith always moves (James 2:17–18).",
                "Christ Himself was baptized ‘to fulfil all righteousness,’ though He had no need (Matthew 3:13–15)—the form mattered enough for Him to enter it.",
                "The Ephesian disciples were re-baptized when their understanding caught up to the gospel of Christ (Acts 19:1–5)—the act mattered enough to be done rightly."
            ],
            liveExamples: [
                "Mode of baptism (immersion, pouring, sprinkling) and the proper subjects",
                "Frequency and meaning of the Lord’s Supper / Eucharist / Sacrament",
                "Whether ordinances are means of grace, signs of grace, or both",
                "The role of confirmation and the laying on of hands",
                "How explicit a covenant must be to count as one"
            ],
            frame: "Article 11 will not legislate the forms. It confesses that disciples become disciples by covenant and that covenants are lived, not merely held. Where the form is debated, the doing is not.",
            probe: "Where is the gap widest right now between what you profess on Sunday and what you live on Tuesday—and what one small commitment would begin to close it?"
        }
    },
    "A12": {
        eyebrow: "Articles of Interfaith Discipleship · Of Immortality and Eternal Life",
        slides: [
            {
                type: "title",
                number: "Article 12",
                title: "Of Immortality and Eternal Life",
                lead: "We believe this life is not all there is. The grave is not the end. Christ’s resurrection is the promise and the proof."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "This life is not all there is; the grave is not the end.",
                    "Christ’s resurrection is the promise and the proof of every other promise He has made.",
                    "What was sown in sorrow will be raised in glory; what is given to Him is not lost.",
                    "What glories await and what the accounting looks like, we leave to God, who keeps His promises."
                ]
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "But now is Christ risen from the dead, and become the firstfruits of them that slept.", ref: "1 Corinthians 15:20", url: "nt/1-cor/15?id=p20#p20" },
                    { text: "It is sown in corruption; it is raised in incorruption: …It is sown in dishonour; it is raised in glory.", ref: "1 Corinthians 15:42–43", url: "nt/1-cor/15?id=p42#p42" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "What do you most fear about standing before God in naked honesty? What do you most hope for?" },
                    { tag: "Together", text: "Our traditions describe the afterlife with very different details. What can we affirm together about the hope of resurrection without requiring agreement on the geography of heaven?" }
                ]
            }
        ],
        facilitator: {
            intro: "Article 12 is the cluster’s hope chapter. The disagreements here are about the geography of the afterlife. Keep the room close to the proof—the empty tomb—and let the maps remain different.",
            scriptureExamples: [
                "Paul wrote that ‘if Christ be not raised, your faith is vain’—the resurrection is the load-bearing fact (1 Corinthians 15:14–17).",
                "Job, in the ash heap, said ‘I know that my redeemer liveth… and though after my skin worms destroy this body, yet in my flesh shall I see God’ (Job 19:25–26).",
                "Jesus told Martha at Lazarus’s tomb, ‘I am the resurrection, and the life’—and then proved it before her eyes (John 11:25, 43–44)."
            ],
            liveExamples: [
                "Whether the soul sleeps until the resurrection or is conscious in the interim",
                "The number and character of the heavens, kingdoms, mansions",
                "Final judgment: who, when, and on what basis",
                "Universal salvation, eternal conscious punishment, or annihilation",
                "Purgation / purgatory and the state of the dead"
            ],
            frame: "Article 12 will not draw the map of the next world. It confesses the empty tomb and the trustworthy Christ, and leaves the rest in God’s hands. The hope is sure even when the architecture is debated.",
            probe: "Where has detailed certainty about the afterlife replaced—rather than deepened—your trust in the One who promises it?"
        }
    },
    "A13": {
        eyebrow: "Articles of Interfaith Discipleship · Of Our Confidence",
        slides: [
            {
                type: "title",
                number: "Article 13",
                title: "Of Our Confidence",
                lead: "We proclaim that Christ is enough—His gospel for the flawed, the weary, the wounded, and the searching."
            },
            {
                type: "points",
                heading: "The Heart of It",
                items: [
                    "Christ is enough. His gospel is for the flawed, the weary, the wounded, and the searching.",
                    "His invitation reaches every tribe, every tongue, across every tradition.",
                    "We have accepted Him as our Savior with or without perfect doctrinal understanding.",
                    "We build on what we hold in common, with careful restraint and Christ-like patience over what might divide."
                ]
            },
            {
                type: "scripture",
                label: "Anchored in scripture",
                verses: [
                    { text: "For whosoever shall call upon the name of the Lord shall be saved.", ref: "Romans 10:13", url: "nt/rom/10?id=p13#p13" },
                    { text: "…a great multitude… of all nations, and kindreds, and people, and tongues, stood before the throne.", ref: "Revelation 7:9", url: "nt/rev/7?id=p9#p9" }
                ]
            },
            {
                type: "discuss",
                label: "For discussion",
                questions: [
                    { tag: "Personal", text: "Is Christ enough for you — not for others, not in theory, but for you, today, as you are?" },
                    { tag: "Together", text: "If we walk out of this room genuinely persuaded that Christ is enough, what is one thing we would stop doing—and one thing we would start—in how we treat believers of other traditions?" }
                ]
            }
        ],
        facilitator: {
            intro: "Article 13 is the cluster’s benediction—the place where confession becomes posture. There are no live disagreements to surface here; the work is to send the room out as the Articles intend: with Christ central, restraint exercised, and the door held open.",
            scriptureExamples: [
                "Paul’s confidence: ‘I know whom I have believed, and am persuaded that he is able to keep that which I have committed unto him’ (2 Timothy 1:12).",
                "John saw ‘a great multitude, which no man could number, of all nations, and kindreds, and people, and tongues’ before the throne (Revelation 7:9)—the gathering Christ purchased.",
                "Christ’s own prayer: ‘Father, the hour is come; glorify thy Son… that they all may be one’ (John 17:1, 21)—the prayer the cluster ends with."
            ],
            liveExamples: [
                "How active should our welcome be to those of other faiths, or none?",
                "Where does ‘building on common ground’ shade into compromise?",
                "How does this community sustain its center without becoming a new denomination?",
                "What does ‘careful restraint and Christ-like patience’ actually look like in practice?"
            ],
            frame: "Article 13 closes the cluster with a posture, not a policy. Christ is enough; the rest is restraint. The disciple’s confidence is not that we have settled every question, but that we have been received by the One who has.",
            probe: "If ‘Christ is enough’ became your operating posture starting now, which conversation would you stop having? Which one would you finally start?"
        }
    }
};
