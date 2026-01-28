---
# ===========================================
# CHAPTER TEMPLATE
# Copy this file and rename for new chapters
# ===========================================

layout: layouts/chapter.njk

# Basic Info
title: "Chapter Title Here"
chapter: 1
slug: "chapter-slug"
chapterId: "chapter-01-slug"

# Scripture Epigraph
scripture:
  text: "Scripture quote text here..."
  reference: "Book Chapter:Verse"
  url: "bofm/book/chapter.verse"

# Reading Info
readingTime: 15
sectionCount: 16

# Audio Files
audio:
  narration: "chapter-01-narration.mp3"
  overview: "chapter-01-overview.mp3"
  testimony: "chapter-01-testimony.mp3"

# Resources
pdf: "WoP_Ch01_Title.pdf"
infographic: "chapter-01-infographic.png"
slides:
  count: 10
  path: "chapter-01"

# Navigation
prevChapter:
  url: "/writings/"
  title: "All Chapters"
nextChapter:
  url: "/chapters/02-next-chapter/"
  title: "Chapter 2: Next Title"

# Discord
discordChannelId: "1234567890123456789"

# Table of Contents (auto-generated from h2 headings if omitted)
toc:
  - id: "section-one"
    title: "First Section"
  - id: "section-two"
    title: "Second Section"

# Timestamps loaded from: src/_data/timestamps/chapter-01.json
---

## First Section {#section-one}

{% sentence 0 %}First sentence of the chapter.{% endsentence %}
{% sentence 1 %}Second sentence continues the thought.{% endsentence %}
{% sentence 2 %}Third sentence adds more detail.{% endsentence %}

As taught in {% scripture "Alma 42:8" %}, the plan of redemption was prepared from the foundation of the world.

## Second Section {#section-two}

{% sentence 3 %}Beginning of the second section.{% endsentence %}
{% sentence 4 %}More content here.{% endsentence %}

{# Continue with chapter content... #}
