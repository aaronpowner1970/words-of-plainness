# Shared method account (Phase C6; not yet written)

`src/_data/aoidArticleTabs.js` reads `method-account.md` from this folder.
When that file exists and has text, every Article's Disclosure tab ends with it
(rendered from Markdown, whole file, so it carries its own heading) and the generated line
on Articles with no disclosure gains its second sentence. While it is absent, the tab shows
only "This Article has no disclosure of its own." and no method section.

Do not put anything else named `method-account.md` here. Only the Second Edition
build (`WOP_AOID2_SECOND_EDITION=1`) shows the tabs at all.
