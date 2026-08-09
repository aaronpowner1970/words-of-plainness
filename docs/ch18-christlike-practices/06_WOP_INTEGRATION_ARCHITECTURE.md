# Words of Plainness Integration Architecture

## 1. Position inside Volume 1

The current recommendation preserves the existing Volume 1 structure.

```text
WORDS OF PLAINNESS — VOLUME 1

Movement 3: Practical Discipleship Practices / Follow Me

  Chapters 12–17
  Foundations of Practice
        │
        ▼
  CHAPTER 18
  Christlike Virtues in Practice
        │
        ├── explains behavior-first approach
        ├── introduces virtue → practice distinction
        ├── teaches how to use the tool
        └── launches reusable Christlike Practices app
        │
        ▼
  Chapters 19–29
  Daily-life contexts in which these behaviors are practiced
```

Chapter 18 should not require renumbering or rebuilding the remainder of Movement 3.

## 2. Recommended Chapter 18 role

### A. Christlike character becomes visible in behavior
Introduce the distinction between durable virtue and observable practice.

### B. How the practices were identified
Briefly explain the behavior-first, primarily Gospel-narrative methodology and evidence categories.

### C. How to use this resource
Make explicit that this is not a checklist, the reader need not explore every practice, and repeated return is expected.

### D. Enter the practice
Primary CTA launches the app.

Potential CTA:

> **Explore the Practices of Jesus**

## 3. Relationship to Chapters 19–29

Chapter 18 supplies the behavioral vocabulary. Later chapters provide contexts in which practices can be revisited.

### Loving Our Neighbors
Potentially surface Attentive Presence, Dignity & Belonging, Grace & Restoration, Peace & Right Use of Power.

### Building Godly Marriages
Potential practices include Unhurried Presence, Questions That Honor the Soul, Truthfulness in Love, Forgiveness, Non-Retaliation, Repairing Harm, Refusal of Comparison.

### Raising Children
Potential practices include Attentiveness, Patience with Slow Understanding, Specific Affirmation, Development Through Debriefing, Restoring Agency, Capacity-Sensitive Judgment.

### Witnessing of Christ
Potential practices include Respect for Agency, Questions That Honor the Soul, Honest Disclosure of Cost, Non-Gatekeeping, Listening as a Learner.

### Faithful Service
Potential practices include Embodied Care, Privacy-Preserving Care, Follow-through, Stewardship Without Waste, Doing Good Without Requiring Gratitude.

### Trials / Treasure / Endurance
Potentially surface Inner Government, Long-Horizon Fidelity, Trust, Non-Retaliation, Courage, Detachment, Other-Directed Care While Suffering.

## 4. Relationship to Keep My Commandments

```text
KEEP MY COMMANDMENTS
What did Jesus ask disciples to do?
        │
        │ future reciprocal links
        ▼
CHRISTLIKE PRACTICES
How did Jesus Himself behave?
```

Potential cross-link labels:

From Christlike Practices:
> **Jesus Taught This** — Explore related commandments.

From Keep My Commandments:
> **See Christ Model This Teaching** — Explore related Christlike practices.

Do not require complete cross-link coverage for first release.

## 5. Existing design grammar worth reusing

Preserve where appropriate:

- **How We Practice**
- **How It Blesses Lives**
- **How Will You Practice?**

Add:

- **What Jesus Did**
- optional **See This Practice in His Life**

## 6. Technical integration questions for Cowork

Before implementation, audit:

- shared auth/user identity;
- reusable commitments/reflections infrastructure;
- Sanity ownership of editorial practice content;
- Supabase ownership of user practice-cycle state;
- reusable KMC components/packages;
- route vs subdomain vs separate app;
- analytics and consent patterns;
- accessibility conventions;
- mobile/navigation system;
- deployment/environment conventions;
- current RAG/content-generation workflow.

## 7. Architectural posture

Prefer **reuse of infrastructure and design primitives** while preserving **separate product semantics**.

Do not reuse a KMC completion schema merely because it already exists if it forces the wrong formation model.
