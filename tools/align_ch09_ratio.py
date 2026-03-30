"""
Ch. 9 ratio-based timestamp alignment.

Uses ElevenLabs transcripts (collected via MCP, baked in below) to
locate each sentence's first word within the chunk transcript, then
calculates its timestamp as:

    global_time = cumulative_offset + (word_position / total_words) * chunk_duration

This is more accurate than interpolation and requires no network calls.
Chunk durations come from ffprobe on the original chunk files.
"""

import re
import json
import subprocess

# ── Paths ─────────────────────────────────────────────────────────────────
CHUNKS_DIR   = r"C:\Users\aaron\Documents\working-folder\ch09-chunks"
CHAPTER_PATH = r"C:\Users\aaron\Documents\words-of-plainness\src\chapters\09-yehoshua-the-man.md"
OUTPUT_PATH  = r"C:\Users\aaron\Documents\words-of-plainness\src\_data\timestamps\chapter-09-yehoshua-the-man.json"

# ── ElevenLabs transcripts (baked in from MCP collection) ─────────────────
TRANSCRIPTS = {
    "tts_By_th_20260313_212610.mp3": "By the time the first sandals scuffed dust into the air above ancient dirt roads, every household is already in motion, each person drawn forward by the same quiet force that still moves us today in our modern age of shoes and pavement: the need to eat, to provide, to compete, to endure another day. The dust and duty of life cannot be ignored, and it can become all-consuming if we allow it. She did not think of herself as distracted. She thought of herself as responsible. The fire needed tending, the guests needed feeding, and no one else seemed to notice. She had no idea that one day the whole world would know her name. Martha, sister to Mary, both sisters of Lazarus of Bethany. Their home in Judea, conveniently near Jerusalem, was a favorite resting place for God who walked among humans. Mary and Martha labored daily within this pressing reality of dust and duty, especially when he visited their home. They had heard the stories, considered the gospel message of the long-awaited Messiah. They had prayed, experimented upon the Word, embraced him and his teachings, and bent their lives to his service. This is the question explored in chapter six: How would you know the truth of him? If he were introduced to you as the Christ, how would you know it's true? This chapter presents a very different question from chapter six: How would you know him personally, not just the truth of his identity? How would you relate to him socially? How would your soul respond to his personality and bearing? Would you be in the right frame of mind to feel his spiritual presence, ready to see him for who he is rather than who you might expect based on 2,000-year-old records, traditions, and creeds? Would you be comfortable in his presence, or would you feel awkward? We know that children ran toward him. Men untrained in theology responded instantly to his call. Crowds listening to him forgot to eat. The powerful among Israel came to speak to him in secret. Desperate souls pressed through walls of people and tore through rooftops to obtain his personal blessing. His enemies were confused by him, and often failed to execute their own orders. A tax collector climbed a tree just to catch a glimpse of him.",

    "tts_If_He_20260313_212701.mp3": "If He walked into a church meeting dressed as a parishioner, but by His will, your eyes were kept from recognizing Him, like the disciples on the road to Emmaus, would we be too distracted by hymns and prayers and wiggling children and the normal business and gossip of congregational life? Would we know Him? How would we know Him? You have a Mary and Martha decision to make. You can be like Mary, recognizing the value of His character and kneeling at His feet to learn from Him. You can be like Martha, honorably busy serving the needs of others but not recognizing the special moment for what it was. This isn't to say that we stop tending to the mortal essentials, but that we must be ready whenever He calls to stop, listen, and obey. We must also learn to be in the firm habit of setting down our cares and concerns regularly to make moments for Him. The Prophet Joshua also presented to the world this same challenge. Choose for yourselves this day whom you will serve. This is not all, not for a disciple. This isn't a one-and-done choice. Choose today, and then tomorrow, choose again. If you ever fail to make the same choice, then get back up, shake the dust off of your sandals, and make the choice once again to serve the Lord. What would it be like for Yahoshua to enter a room today, or walk into a busy marketplace? Would He be noticed or would He blend in? What would it be like to be near Him as just another member of a community? What would His presence say of Him to any that took notice? His attitude? His posture? His behavior? Before He ever opened His mouth, what would you learn of Him? The value of this chapter is in the sincere character study of Jesus Christ, the human personality of the Word made flesh. This topic is the centerpiece of our effort to respond to His command, Learn of me. Let us feast upon the Scriptures to learn of our God-made flesh. Don't delegate this task to others, not even to preachers or teachers. It is as much your responsibility to learn of Jesus Christ as to personally confess Him as your Lord and Savior, or to follow Him as an expression of your love for Him. Our purpose here is contemplative. Sit with Yahoshua the man, study Him honestly. Who is He? What kind of person is He? This chapter asks, What is He like? What manner of man is this? The portrait that follows is organized around a single claim, that grace and truth are the most defining character traits of the Son of God, and that every other attribute, action, and reaction of Yahoshua flows from this foundation. His character is not the absence of human feeling, but the perfection of it. Every impulse governed by love, every response shaped by wisdom, every choice submitted to the Father. He is the mirror we hold up to see ourselves honestly.",

    "tts_Yehos_20260313_212752.mp3": "Yahoshua spent roughly thirty years doing manual labor and only three years in ministry. That ratio itself is a testament to his humility. God in the flesh chose to quietly shape wood and stone in the privacy of an insignificant village before he ever shaped souls and performed miracles publicly. Shortly before his triumphant reception in the city, Yahoshua had left Galilee to walk the road to Jerusalem when a young man came running to meet him along the way, falling to his knees before the master. The young man said, Good teacher, what must I do to inherit eternal life? Of course, Yahoshua knew the answer better than anyone. He had taught the gospel of salvation in many forms to many people. Still, rather than answering directly, Yahoshua reacted with graceful humility. Why do you call me good? No one is good, except God alone. He did then teach the answer, but first redirected glory to the Father. From his early years, he could have enjoyed the same celebrity status that welcomed him to Jerusalem on the day of his triumphal entry when a vast throng of believers accepted him as their messiah and king of the Jews. Even on that glorious day when all seemed to be going well, he rode into the adoring masses riding a humble donkey instead of a war horse. Paul taught us to emulate Yahoshua's humility in his letter to the people of Philippi. In your relationships with one another, have the same mindset as Christ Jesus, who being in very nature God, did not consider equality with God something to be used to his own advantage. Rather, he made himself nothing by taking the very nature of a servant, being made in human likeness. Yahoshua's example is what grace looks like in the form of humility. He did not have to proclaim his mastery of humility. He lived it in his everyday relationships. My mother used to remind me that one does not announce one's own humility. Throughout my life, I have never felt safer than when I am with genuinely humble people. Sensing no competition, no threat, it allows me to let down my guard. Humility in others allows us to see deeper than the facade of ego to real depth of character. This is what it must have felt like to be near Yahoshua. To some, it may have been frightening or suspicious. To disciples, it feels like coming home.",

    "tts_This__20260313_212836.mp3": "This is a good moment to pause. The reflection tabs in the margin invite you to sit with what you just read before we continue. Free registration saves all your reflection work to a personal report you can return to any time from the user menu.",

    "tts_Many__20260313_212912.mp3": "Many Christians identify Christ's ultimate act of obedience to the Father by the words of surrender in Gethsemane. Not my will, but thine, be done. This moment will be studied in another chapter. Here, let us observe his daily examples of obedience as evidence of his character. As a dutiful son, Yahoshua obeyed his mortal parents and respected his elders. Both obedience and discipline were required to learn the artisan skills of carpentry and stonework from Joseph. Mary would have benefited from his obedience in performing chores around the house, and running errands to neighbors and the market. He willingly obeyed the laws and traditions of attending to regular studies and worship at synagogue. The concept of roots before fruits applies to this study of Christ's trait of obedience. Yahoshua's mortal character was not whole and complete from birth. His development was molded by perfect submission to the Father. He received grace from the Father as he learned obedience from suffering, sacrifice, and the day-to-day choices needed to submit to the will of the Father. He grew in wisdom, stature, and favor with both God and man. He learned mortal obedience the same way God teaches from heaven, line upon line, precept upon precept. His obedience was not automatic. It was chosen costly, and deepened through mortal experience. His natural character was developed further by his mortal experience. This informs us about our own capacity to progress. After the miracle of feeding the 5,000 from a single boy's lunch, the crowd was astonished to the point that they were ready to make him ruler of Israel immediately. When Jesus therefore perceived that they would come and take him by force to make him a king, he departed again into a mountain himself alone. He walked away from the easy path to kingship offered freely. The people wanted him for their earthly king, but the Father's plan was not a political throne in Galilee. The Son knew the path and obeyed. He traded the easy crown for Gethsemane, a betrayal, a trial, a cross, and a borrowed tomb in Jerusalem. He did not turn from the path. This is what obedience looks like in its highest form. Not only the refusal of evil, but the refusal of good that is not God's will.",

    "tts_I_rem_20260313_213004.mp3": "I remember sitting with paychecks in hand while watching my young children play around me. For years, as a young father, I worried about how it would affect them each time I chose to pay tithes and make charitable offerings. The widow's mite reminded me that God sees the cost of small obedience, and the Lord's challenge in Malachi sustained my resolve. Prove me now herewith saith the Lord of Hosts if I will not open you the windows of heaven and pour you out a blessing that there shall not be room enough to receive it. I was not perfect in this, but each time I chose obedience, He kept His promise. There are some who stand at the edge of this story and feel something other than inspiration. They hear of obedience, and they hear constraint. They think of the covenant life of discipleship, and they see doors closing, freedom surrendered, individuality submerged, the self handed over to an institution or a set of rules that will define and diminish them. Rebellion is marketed as courage. Submission is marketed as weakness. And somewhere in the noise, the actual invitation of Yahoshua gets buried under the fears about whether it is safe to accept it. It is worth pausing here and saying plainly, that is not what obedience to the Lord is. It is not the surrender of the true self. It is the rescue of the self from everything that was diminishing it. The disciples who followed Him did not become less. They became more than they had imagined they could be. The fishermen became apostles. The tax collector became an evangelist. The greatest persecutor of disciples became the greatest missionary the early church produced. Obedience to the invitation of Yahoshua does not erase the person. It reveals the person, the truest, deepest, most fully realized version of who they were always meant to become. The Lord does not stand at the gate of discipleship as a foreman with a longer list of tasks. He stands there as the one who has already borne the heaviest load in the history of creation, and who is offering, with open hands, to take yours. He is not asking you to carry what He has not already carried. He is asking you to stop carrying it alone. There is a freedom on the other side of that surrender that the world cannot manufacture and cannot explain. The freedom the Savior offers is the freedom of the person who knows what they are and why they are here and to whom they belong, a knowledge that settles in one's heart like ballast in a storm. And then God says within your heart let there be light. The covenant life is lit from within in a way that the life of self-directed striving simply is not. There is a quality of joy available to the obedient disciple, not the surface happiness of favorable circumstances, but something deeper and steadier, a luminosity that persists even when circumstances are hard. The yoke of Yahoshua is miraculously light upon the shoulders, fitting far better than any device or philosophy the world can fashion without God. Come unto me all ye that labor and are heavy laden and I will give you rest. Take my yoke upon you and learn of me for I am meek and lowly in heart and ye shall find rest unto your souls. For my yoke is easy and my burden is light. Easy. Light. These are not the words of a taskmaster. They are the words of the one who designed the yoke so that it will not chafe, who knows exactly what it was made for, and who has been wearing it since before the world was formed. The burden is light because he is pulling at the same beam, and he does not tire. You do not lose yourself in Him. You find yourself lit up, set free, and finally moving in the direction you were built to travel.",

    "tts_Pause_20260313_213102.mp3": "Pause here. What you just read is worth more than a passing thought. The reflection tabs in the margin are waiting for you. Free registration saves everything you write to a personal report in your user menu.",

    "tts_In_th_20260313_213138.mp3": "In the Gospel of Mark, Yahoshua's grace encountered a broken man, a leper, a man whose skin was rotting from a disfiguring disease, a man who searched for the rabbi who could perform miracles. When he found the master, he fell to his knees to confess, If you are willing, you can make me clean. Yahoshua didn't hesitate in disgust. Instead, he was so moved with compassion for the man that he reached out his hand to touch him. The contact made Yahoshua ritually unclean under the law, and then He healed him. This is what grace looks like when it encounters the broken, not pity from a safe distance, but a compassionate savior choosing contact. In the 11th chapter of John, Yahoshua learned of the dire illness of his close personal friend, Lazarus. He didn't depart immediately to heal the friend, though he could have. He waited on purpose until after Lazarus had died. Learning that the master approached their home in Bethany, Martha and Mary both ran to him in turns to fall down at his feet to sob, Lord, if you had been here, my brother would not have died. Surrounded by the mourning sisters and a crowd of grieving Jews, He groaned in the spirit and was troubled. This is not the reaction of a distant and unrelatable deity. He then asked, Where have you laid him? And that question is extraordinary because He already knew what He was about to do. He was about to raise Lazarus. What happened next may be the most revealing moment in all of scripture, Jesus wept. This tender moment of compassion wasn't because Yahoshua felt sad about the death of his friend. Rather, it demonstrates his fully developed compassion in the moment he chose to walk the full distance of human grief with a family in mourning, sharing in their pain. He didn't have to. He could have spoken the command at a distance, as with the Roman centurion's dying servant, but he knew the value of entering the grief of the grieving, touch and presence rather than healing from a distance. Throughout his mortal ministry, the Lord was filled with compassion for souls who fainted and were scattered abroad as sheep having no shepherd.",

    "tts_This__20260313_213228.mp3": "This trait did not lessen or end with his death. In the eastern hemisphere, the resurrected master comforted the weeping Mary at his empty tomb. He reassured the fearful disciples. He removed Peter's shame by allowing him to declare his love three times, once for each time he had previously denied him. He walked with the grieving disciples on the road to Emmaus. He personally made a warm fire at a campsite and hand-cooked a meal for his disciples who were returning from a frustrating day of fishing. The resurrected Yahoshua also gloriously appeared to a multitude of disciples in the western hemisphere, who had been waiting for him. After delivering his gospel message, he cast his eyes roundabout again on the multitude and beheld they were in tears and did look steadfastly upon him as if they would ask him to tarry a little longer with them. Behold, my bowels are filled with compassion towards you. He chose, out of grace, to stay for a while longer, to visit and to heal the sick and afflicted. He blessed their children and prayed for them. The word compassion in the Bible is translated from the Greek splagxnizomai. It signifies a profound gut feeling of love and mercy that motivates actions to save and atone. It describes the visceral upheaval of seeing suffering, being shaken to the core by it, and then moving to act. I have known what it is to be broken and in need of compassion, the instability and isolation of homelessness, the devastation of a broken marriage, and being a single parent to three teenage daughters, the helpless feeling of being on the verge of losing everything, and the dark night of the soul when God seemed distant. But I have also known the healing relief of Christlike compassion of others who reached out to me in those dark days. I can name one pair of hands that reached for me. They belonged to my dear wife, Michelle, who was brave enough to love me, generous enough to be a mother to my three daughters. I also gained a precious new daughter in the blending, and I was healed in the process. When someone is in crisis beyond their own capacity to survive, sympathy is insufficient. The leper didn't need someone to quote Levitical laws, he needed someone to touch him with grace. There is a wide difference between knowing about the suffering of others and entering into it to support them. Grace, at its most Christlike, is compassion combined with the wisdom to know when and how to get involved.",

    "tts_Take__20260313_213339.mp3": "Take a moment here before moving on. Use the reflection tabs in the margin to sit with this. The chapter will wait. Free registration saves all your reflection work to a personal report you can find in the user menu.",

    "tts_A_sol_20260313_213413.mp3": "A solitary Samaritan woman came to draw water at midday, an hour when no one else would be at the well, perhaps avoiding her peers. Yahoshua saw her and waited there. He greeted her with neither doctrine nor authority. He asked her for a drink, which would have seemed inappropriate within that cultural setting. Beginning with that simple request, He led her step by step at exactly the pace she could follow. Water turned to worship. He resolved her past and shaped her future. He led her from natural curiosity to a confession of faith. She recognized the promised Messiah, and what did she do? She left her water pot and ran to tell her village, Come, see a man which told me all things that ever I did. Is not this the Christ? Grace received became grace shared in a matter of minutes, and it transformed her from an isolated soul to student, and then from student to teacher. This is His pattern. How Yahoshua taught reveals who He was. He didn't simply pour out truth, He calibrated it to the hearer. Parables for crowds who needed to discover truth at their own pace. Direct doctrine for disciples ready to receive it. Piercing questions for pharisees hiding behind their authority. Silence as a teaching tool to instruct a Roman governor who had no interest in the answer. Every choice of method was an act of respectful grace for the person standing before Him. Why did He teach it all? Because out of the abundance of the heart, the mouth speaketh. A heart full of grace overflows. Restoration scripture confirms this in an account of Lehi, an elderly prophet. In a vision, he tasted the fruit of the tree of life, and his first impulse was not to analyze it, but to turn to his family. I began to be desirous that my household should partake of it also. The desire to share what is precious is the natural fruit of having received it. This is grace communicated. I remember a moment when a teenage special education student said something so disrespectful in my science laboratory that every instinct told me to respond by matching his energy. Instead, I bit my tongue, threw a desperate prayer heavenward and waited. The spirit softened my heart and opened my eyes, not just to find compassion for the student, but to see how to reach him. The unmet need motivating his behavior became the focus for the teaching moment. I learned that day what the master practiced perfectly. Truth that reaches a soul must first be calibrated to the soul it is reaching. This is not just a teaching technique. It flows from habits of grace that we learn from Yahoshua, the man.",

    "tts_The_s_20260313_213526.mp3": "The same hands that overturned tables in the temple at Jerusalem also washed feet in the prepared upper room. Why? It bears repeating, Yehoshua was full of grace and truth. On the evening before his crucifixion, Yehoshua rose from his place at the last supper table to perform a task that had been neglected by others. He laid aside his outer garment, wrapped a towel around his waist, and poured water into a basin. The master then knelt before his servants. Washing of guests feet was a degrading task assigned to the lowest household slave, work that Jewish law forbade compelling of a Hebrew servant. It was also an act of affectionate personal service that a wife would perform for her husband. The paradox is not that degradation equals affection, but that love can stoop to perform what status would despise. Peter's horrified reaction reveals the depth of meaning in watching his master do this task. Yehoshua washed Peter's feet, who would deny him. He washed the feet of Judas, who already had made plans to betray him. The master was not ignorant of these things, yet he knelt to serve, taking the posture and position of one that no one notices. Earlier that same Passover week, Yehoshua entered the temple and saw that the Court of the Gentiles, the only part of the temple where people of all faiths and nationalities could worship the God of Israel, had been converted into a bustling marketplace filled with vendors, moneychangers, animals, and the chaos, filth, and greed that go with these things. He found a place where he could sit down and make a whip of cords. His reaction was not sudden. It was measured and premeditated. Those gentle hands, those that washed feet, broke bread with the hungry, healed lepers, shaped the world, and gestured to all to come and see, overturned the vendor tables, scattered their wares, cracked his whip in deliberate fury, and his voice thundered quoted scriptures. His anger was not aimed solely at the merchants, but its scope included the corrupt priests that profited from the corruption of the house of prayer. He courageously took a stand to confront an abusive system, not just functionaries. His anger focused on anything that came between souls and the kingdom of heaven, and no one could stop him. The chief priests feared him and could not act. Meekness is not weakness, and courage is not rage. Both are manifestations of the same character trait, one that flows in different directions from the same source, the grace and truth at the core of his personality. The meek serve when dignity says don't bother. The courageous serve when safety says don't dare. Both require the same inner conquest, the surrender of ego before the work of love begins. Yehoshua did not kneel because he was timid. He did not overturn tables because he lost control. He mastered his natural impulses and then acted from what remained, grace directed by truth. When truth called for gentleness, he was gentle without being weak. When truth called for confrontation, he confronted without being cruel. This is what mastery looks like, not the absence of strong emotion, but the governance of it by wisdom and love. I recall several moments of conflict in which I said something I thought sounded righteous, but wound up being self-righteous and hurtful. I repent humbly before God. I ask those I harmed for forgiveness. I pray that I am developing a measure of Christlike character as his grace and truth work upon my spirit. I imitate him imperfectly, but it is my covenant duty to try. There is comfort for me in holding up the character of Christ as a mirror to examine my soul. I remind myself often not to focus on how far I fall short of him, but to hold to my faith that his grace sees me as I hope to be, and that his spirit works tirelessly upon me daily to close the gap.",

    "tts_The_P_20260313_213653.mp3": "The Pharisees and their entourage of scribes dragged her into the temple courts on a morning when Yahoshua sat teaching a gathering of the people. They interrupted his teaching and thrust her in the middle of his gathering. They weren't interested in redeeming her soul at all. They were trying to build a case against Yahoshua. Their challenge, Moses in the law commanded us that such should be stoned, but what sayest thou? She must have been shaking with fear and shame before the crowd. The master stooped to write on the ground with a finger. We don't know what he wrote. We do know that Yahoshua refused to answer on their terms. When they pressed the master, he rose and delivered one sentence that shattered their trap without breaking the law. He that is without sin among you, let him first cast a stone at her. They departed one by one, eldest first, stung by their own conscience. When only the woman remained, he delivered a powerful sermon in divine brevity. Neither do I condemn thee. Go and sin no more. Mercy without justice is indulgence that leaves a sinner unchanged. Justice without mercy is cruelty that crushes the soul of the sinner. In Yahoshua, we find that the grace and truth in him courageously names what must change, while meekly protecting the soul that must make the change. I am the light of the world he that followeth me shall not walk in darkness but shall have the light of life. The context for this verse is Yahoshua's demonstration of the dynamic between justice and mercy, and more importantly, how this affected the life of the woman whom he did not condemn. Again, I hear the voice of my saintly mother, Aaron, you never know what sorrow lies behind a smile. You never know how someone who has mistreated you was personally greeted and then treated in this life. Be like Jesus. Her voice echoes in my heart like that of Yahoshua, teaching me to neither announce my own virtues, nor to assume another's vices. In all our spiritual journeys, when faced with the opportunities to judge one another, let us walk in the grace of his light. Anything else is walking in the dark.",

    "tts_Contr_20260313_213810.mp3": "Contrasting His own lifestyle to that of His cousin who taught in the wilderness, Yahoshua described Himself as eating and drinking with His followers. His enemies claimed He took this to excess as a glutton and a drunkard, a friend of tax collectors and sinners. They meant this as an insult. Read it again. Think. What kind of person draws that accusation? Not a broody stoic. Not the pale, sorrowful figure captured in medieval stained glass. His enemies saw a man who showed up at feasts, who turned water into wine at a wedding. His first recorded miracle was performed to keep a celebration going at the request of His own mother. Yahoshua was the kind of man that people wanted as a friend and companion. His presence made rooms feel different, better. The man, Yahoshua, had joy. This wasn't a shallow happiness. It was the deep kind of gladness that survives grief and sustains inner purpose. Luke named his emotion. In that hour, Jesus rejoiced in spirit. The occasion of such joy had nothing to do with miracles or outsmarting enemies. The seventy had just returned from their missions, and the Father had revealed truth to the hearts of the faithful. Yahoshua's joy was in the Father's work, in the lost sheep's safety, in the return of the prodigal. In one tender account, the resurrected Lord knelt among the children, blessed them one by one, and wept, not from sorrow, but from joy so full it overflowed. This is the nature of grace rejoicing. It is not the absence of sorrow, nor a paradise of pleasure. Joy that comes from Christlike grace cannot be extinguished by opposition. Joy and sorrow live side-by-side in every honest life. The writer of Hebrews understood. Jesus, who for the joy that was set before Him endured the cross. Joy was His motive, not the reward. These things have I spoken unto you, that my joy might remain in you, and that your joy might be full. This is His invitation for you to receive the same grace that fueled His own gladness, and to let it overflow into the lives of others. I remember a full day of shoveling manure with fellow saints for neighborhood gardens. We didn't dare hug or even shake hands, smiling brightly, despite being thoroughly covered in muck. How odd it is that we can be covered in filth while filled with joy in the service of the master and while caring for one another. This truly is the abundant life He promised.",

    "tts_This__20260313_213926.mp3": "This chapter could not possibly detail all the marvelous personality traits that flow from Yahoshua's core of grace and truth. The Apostle John also felt the need to explain, There are also many other things which Jesus did, the which, if they should be written every one, I suppose that even the world itself could not contain the books that should be written. My purpose here is to introduce Yahoshua, the man behind the ministry, as a relatable person that we would be delighted to have as a friend. Better than being introduced by servants, the master of grace and truth shared his own character portrait in the form of the Sermon on the Mount. The Beatitudes are instructions, and they are also something more. The first words of his first recorded sermon were a character sketch of himself. We gain marvelous confirmation of the nature of his own character by assuming that the teacher practiced what he taught. He not only described what his disciples should become, he described what he already was and what his grace makes possible in every willing heart. That same grace that is the living core of his character is a power at work in every willing disciple. Studying his character is not meant to measure the distance between him and us. It is meant to show us what we can become as his grace works its refining purpose in our mortal lives. Beholding the truth of his grace as the mechanism of our own transformation is the whole point of this chapter.",

    "tts_Youv__20260313_214047.mp3": "You've sat with Yehoshua. You have studied the man who is God. You've observed that his great heart, full of grace, beats with his life-giving truth throughout all parts of his character. We hear the phrase, He died for us often, but let us not forget that He also lives for us. He is the Lord of both the dead and the living. His heart still beats for you. Now is an important moment for your own heart. Will it begin to beat for Him as well? John recorded a profound prayer of Jesus, a prayer that is called The Great Intercessor's Prayer. My prayer is not for them alone. I pray also for those who will believe in me through their message. You are inside His prayer. Jesus prayed for the person reading this chapter by name in the eternal sense. This is not a simple metaphor. He saw you. His heart still beats for you. I have given them the glory that you gave me that they may be one as we are one, that they may be brought to complete unity. That same graceful character you just studied, the humility, the compassion, the mastery of every human impulse is not to be held at a distance for admiration. It is a gift that has been freely given. Will it be received? The glory of Christ's character is the gift of grace to the willing disciple. But it must be received through the beholding. His arms are open wide. Christ prayed that we would behold His glory, and we are taught that beholding transforms the beholder into the same image from glory to glory. It has already begun in you. His hands will bless you. Christ prayed that His disciples may become one. As thou, Father, art in me and I in thee, that they also may be one in us, that they may be made perfect in one. The heart of Christ is not just for the individual. It is the bonding agent that makes us one with Him, one with the Father, and one with the heart of every other disciple. His voice calls you home. Christ closed His prayer with His most sincere longing for us. That the love you have for me may be in them and that I myself may be in them. The great intercessor's prayer doesn't end with a desire for nearness. His great heart desires a true oneness with you in spirit and in truth. This oneness does not just happen. It is a journey, an epic story arc. As we learn of Him and follow, His grace transforms us, refines our own character over time. God is calling, Come to Zion. His grace is sufficient for you. The next chapter will show you what it cost Him. We will behold His mastery tested to its absolute limit as we follow Him to Gethsemane and to Golgotha. We testify that the character of the person we have studied here is the Son of God in the highest. Salvation is found in no one else, for there is no other name under heaven given to mankind by which we must be saved. In the name of Jesus Christ, amen.",

    "tts_Befor_20260313_214213.mp3": "Before we close, the reflection tabs in the margin are waiting. What you just read deserves more than a moment; free registration saves all your reflection work to a personal report in your user menu.",
}

# ── Chunk manifest ────────────────────────────────────────────────────────
CHUNKS = [
    ("tts_By_th_20260313_212610.mp3",  0,    27,   False, None),
    ("tts_If_He_20260313_212701.mp3",  28,   61,   False, None),
    ("tts_Yehos_20260313_212752.mp3",  62,   85,   False, None),
    ("tts_This__20260313_212836.mp3",  None, None, True,  385),
    ("tts_Many__20260313_212912.mp3",  86,   111,  False, None),
    ("tts_I_rem_20260313_213004.mp3",  112,  150,  False, None),
    ("tts_Pause_20260313_213102.mp3",  None, None, True,  386),
    ("tts_In_th_20260313_213138.mp3",  151,  175,  False, None),
    ("tts_This__20260313_213228.mp3",  176,  199,  False, None),
    ("tts_Take__20260313_213339.mp3",  None, None, True,  387),
    ("tts_A_sol_20260313_213413.mp3",  200,  235,  False, None),
    ("tts_The_s_20260313_213526.mp3",  236,  277,  False, None),
    ("tts_The_P_20260313_213653.mp3",  278,  300,  False, None),
    ("tts_Contr_20260313_213810.mp3",  301,  330,  False, None),
    ("tts_This__20260313_213926.mp3",  331,  342,  False, None),
    ("tts_Youv__20260313_214047.mp3",  343,  384,  False, None),
    ("tts_Befor_20260313_214213.mp3",  None, None, True,  388),
]

# ── Helpers ───────────────────────────────────────────────────────────────

def get_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def get_words(text):
    return normalize(text).split()

def find_sentence_word_position(sentence_text, transcript_words, search_from=0):
    """
    Find the position of a sentence's first words within the transcript word list.
    Returns (position, found) where position is the index into transcript_words.
    """
    sent_words = get_words(sentence_text)
    if not sent_words:
        return search_from, False

    first = sent_words[0]
    check_len = min(3, len(sent_words))
    search_limit = min(search_from + 100, len(transcript_words))

    for i in range(search_from, search_limit):
        if transcript_words[i] == first:
            match_count = sum(
                1 for k in range(check_len)
                if i + k < len(transcript_words) and
                   k < len(sent_words) and
                   transcript_words[i + k] == sent_words[k]
            )
            if match_count >= min(2, check_len):
                return i, True

    return search_from, False

# ── Step 1: Extract sentences ─────────────────────────────────────────────
print("=== Step 1: Extracting sentences from markdown ===")
with open(CHAPTER_PATH, "r", encoding="utf-8") as f:
    content = f.read()

pattern = r'\{%\s*sentence\s+(\d+)\s*%\}(.*?)\{%\s*endsentence\s*%\}'
sentences = {}
for idx_str, raw_text in re.findall(pattern, content, re.DOTALL):
    clean = re.sub(r'\{%.*?%\}', '', raw_text)
    clean = re.sub(r'\{\{.*?\}\}', '', clean)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = re.sub(r'&[a-zA-Z]+;', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = re.sub(r'[\*_]', '', clean)
    sentences[int(idx_str)] = clean

print(f"  Extracted {len(sentences)} sentences")

# ── Step 2: Get chunk durations ───────────────────────────────────────────
print("\n=== Step 2: Getting chunk durations via ffprobe ===")
chunk_durations = []
for filename, *_ in CHUNKS:
    dur = get_duration(f"{CHUNKS_DIR}\\{filename}")
    chunk_durations.append(dur)
    print(f"  {filename}: {dur:.3f}s")

# ── Step 3: Ratio-based alignment ─────────────────────────────────────────
print("\n=== Step 3: Ratio-based alignment ===")
timestamps = {}
cumulative_offset = 0.0

for chunk_idx, (filename, first_sent, last_sent, is_cue, cue_idx) in enumerate(CHUNKS):
    dur = chunk_durations[chunk_idx]
    chunk_num = chunk_idx + 1

    print(f"\n  Chunk {chunk_num:02d}: {filename}")
    print(f"    Offset: {cumulative_offset:.3f}s | Duration: {dur:.3f}s")

    if is_cue:
        cue_time = round(cumulative_offset + 0.5, 2)
        timestamps[str(cue_idx)] = cue_time
        print(f"    CUE {cue_idx} -> {cue_time}s")
    else:
        transcript = TRANSCRIPTS[filename]
        transcript_words = get_words(transcript)
        total_words = len(transcript_words)
        print(f"    Transcript words: {total_words}")

        word_ptr = 0
        for sent_idx in range(first_sent, last_sent + 1):
            sent_text = sentences.get(sent_idx, "")
            pos, found = find_sentence_word_position(sent_text, transcript_words, word_ptr)

            ratio = pos / total_words if total_words > 0 else 0.0
            global_time = round(cumulative_offset + ratio * dur, 2)
            timestamps[str(sent_idx)] = global_time

            if found:
                sent_word_count = len(get_words(sent_text))
                word_ptr = pos + max(sent_word_count - 1, 1)

        first_t = timestamps.get(str(first_sent), "?")
        last_t  = timestamps.get(str(last_sent), "?")
        print(f"    s{first_sent}: {first_t}s  |  s{last_sent}: {last_t}s")

    cumulative_offset = round(cumulative_offset + dur, 3)

# ── Step 4: Save ──────────────────────────────────────────────────────────
print("\n=== Step 4: Saving ===")
ts_sorted = {str(k): timestamps[str(k)] for k in sorted(int(k) for k in timestamps.keys())}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(ts_sorted, f, indent=2)

print(f"  Saved {len(ts_sorted)} timestamps to {OUTPUT_PATH}")

# ── Step 5: Sanity check ──────────────────────────────────────────────────
print("\n=== Sanity Check ===")
checks = [0, 1, 27, 28, 61, 62, 85, 385, 86, 111, 112, 150,
          386, 151, 175, 176, 199, 387, 200, 235, 236, 277,
          278, 300, 301, 330, 331, 342, 343, 384, 388]

for i in checks:
    key = str(i)
    if key in ts_sorted:
        t = float(ts_sorted[key])
        mins = int(t // 60)
        secs = t % 60
        preview = sentences.get(i, f"[CUE {i}]")[:45]
        print(f"  [{key:>3}] {t:>8.2f}s  ({mins}:{secs:05.2f})  {preview}")
