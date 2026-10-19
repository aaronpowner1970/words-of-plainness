# AoID reader corrections form (AOID2 step 88): wording and spec, DRAFT v1
Session CHAT-AOID2-46a, 19 Oct 2026. Storage ruled AOID2-CORRECTIONS-STORAGE option 1 (existing Django /contact/ endpoint), topic-only.
Status: APPROVED by Aaron 19 Oct 2026, 08:17 ET ("Approve the wording"): Part 1 wording and Part 2 spec. BUILD TEXT.

## Part 1: reader-facing wording

Page title: Help Us Read Your Tradition Rightly

Intro:
These Articles measure what Christ-believing traditions confess by reading each church's own adopted texts: its creeds, confessions, catechisms, rites and official statements. If we have misread your church's text, or missed one it has adopted, please tell us. We would rather be corrected than be wrong.

What happens next:
Every submission is read. No submission changes a count by itself. If it points to an adopted text we have not weighed, that text is read and verified, and any change to a count is decided openly and recorded with its date and reason.

What we can weigh:
We can count only texts a church has officially adopted. Sermons, personal writings and unofficial statements are welcome as background, but they cannot change a count.

Fields (label / helper text):
1. Your tradition (required; list of the sixteen families, plus "Another tradition") / Choose the family your church belongs to.
2. Your church or denomination (optional) / For example, "Lutheran Church–Missouri Synod" or "Greek Orthodox Archdiocese of America."
3. The teaching you are writing about (optional; filled in automatically when you arrive from an Article) / The Article, and the teaching if you know it.
4. The adopted text and its citation (required) / For example, "Augsburg Confession, Article VII" or "Book of Discipline 2024, ¶161.D."
5. A link to the text, if it is online (optional)
6. What we misread or missed (required) / Tell us what the text says and how our reading should change.
7. Your name (optional)
8. Your email, if you would like a reply (optional) / We will not share it or add you to any list.

Privacy line (above the button): Submissions are private. Nothing you send is published unless you give us permission.

Button: Send correction

Success message: Thank you. Your correction has been received and will be read. If you left an email, you may hear back.

Failure message: Something went wrong, and nothing was sent. Please try again later, or write to us through the contact page.

Link text used on the Disclosure and Record tabs and the disclosure pages: "Has your church's text been misread or missed? Tell us."

## Part 2: build spec (for the Code prompt)

- A page at /aoid/corrections/, built only with the Second Edition switch ON; with the switch OFF the page and every link to it are absent and the public output is byte-identical to HEAD's.
- Links: the Disclosure and Record tabs of every Article, and both disclosure pages (/aoid/disclosures/father-of-spirits/, /aoid/disclosures/sexual-holiness/). Each link carries the Article (and, on a Record tab, the floor item where one is in view) as a query parameter that pre-fills field 3.
- Submission: through the site's existing API client (src/js/api.js, the same /contact/ call the contact form uses) to the Django API at site.api.baseUrl. Name and email go in their own fields; tradition, church, teaching, citation, link and note go into the message in a fixed, labelled layout, one per line, so Aaron can read and copy them. Subject: "AoID correction: <tradition>".
- submission_type: Code first determines, without sending a real submission, which values the API accepts (from the API's own description or source if reachable). If a new type cannot be confirmed as accepted, use the contact form's general type and rely on the subject prefix. Do not change the Django service in this run.
- Bot protection: the same honeypot field and loaded_at timing check the safety and newsletter forms use, with the same minimum time.
- No relative fallback URL: if the API client is unavailable, show the failure message. (The safety form's fallback posts to /api/v1/contact/ on the site's own domain, which has no such route; reported separately, not changed here.)
- Accessible labels for every field, required fields marked in words, keyboard order, phone-width layout, the site's palette.
- No submission is stored in the repository or anywhere public. Nothing in the run reads, counts or displays submissions.
- Tests: switch-OFF byte identity; switch-ON page renders with every field; pre-fill from the query parameter; honeypot blocks a filled honeypot; the request body's layout, checked against a stubbed API (no real submission sent).
