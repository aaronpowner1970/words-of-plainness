# Data Model Recommendations

This document is conceptual. Claude Cowork should map it onto existing Words of Plainness / Keep My Commandments infrastructure rather than assuming a greenfield database.

## 1. Domain

```ts
interface PracticeDomain {
  id: string;
  title: string;
  shortTitle?: string;
  description: string;
  behavioralCenter: string;
  primaryQuestion: string;
  sortOrder: number;
  status: 'draft' | 'published' | 'archived';
}
```

Domains organize discovery. They are not progress stages.

## 2. Christlike Discipleship Practice

```ts
interface ChristlikePractice {
  id: string;                 // stable CDP-###
  slug: string;
  title: string;
  descriptor: string;

  primaryDomainId: string;
  secondaryDomainIds?: string[];

  evidence: PracticeEvidence[];
  evidenceStrength: 'enacted' | 'taught_and_enacted' | 'strongly_inferred';

  whatJesusDid: string;
  howWePractice: string;
  howItBlessesLives: string;
  suggestedActions: string[];
  reflectionPrompts: string[];

  lifeSituationIds: string[];
  relatedPracticeIds: string[];
  relatedCommandmentIds?: string[];
  relatedVolume1ChapterIds?: string[];

  textualNote?: string;
  editorialNote?: string;

  status: 'candidate' | 'reviewed' | 'published' | 'archived';
  version: number;
}
```

## 3. Practice evidence

```ts
interface PracticeEvidence {
  reference: string;
  type: 'enacted' | 'teaching' | 'retrospective_nt_summary';
  weight?: 'primary' | 'supporting';
  encounterLabel?: string;
  observation?: string;
  textualVariantFlag?: boolean;
}
```

## 4. Life Situation

```ts
interface LifeSituation {
  id: string;
  title: string;
  description?: string;
  practiceIds: string[];
  sortOrder?: number;
  status: 'draft' | 'published' | 'archived';
}
```

Life Situations are many-to-many discovery tags, not the primary taxonomy.

## 5. Practice Cycle

This is the most important user-state object.

```ts
interface PracticeCycle {
  id: string;
  userId: string;
  practiceId: string;
  domainIdAtStart: string;

  startedAt: string;
  status: 'planned' | 'active' | 'reflected' | 'closed';

  personOrSituation?: string;
  intendedBehavior: string;
  timingOrTrigger?: string;
  privateNote?: string;

  reflectedAt?: string;
  whatHappened?: string;
  whatINoticed?: string;
  whatWasDifficult?: string;
  whatIWouldTryDifferently?: string;
  nextAction?: 'repeat_same' | 'same_domain' | 'new_domain' | 'pause';

  sourceEntryRoute?: 'assessment' | 'domain' | 'life_situation' | 'browse' | 'today' | 'related';
  sourceAssessmentId?: string;
}
```

### Critical rule

**Do not store a permanent completion status on a Christlike practice for a user.**

The same user may create unlimited cycles for the same practice.

## 6. Assessment session

```ts
interface AssessmentSession {
  id: string;
  userId?: string;
  startedAt: string;
  completedAt?: string;
  frameworkVersion: string;
  responses: AssessmentResponse[];
  suggestedDomainIds: string[];
  selectedDomainId?: string;
}
```

```ts
interface AssessmentResponse {
  itemId: string;
  response: 'rarely' | 'sometimes' | 'often' | 'usually' | 'na_unsure';
}
```

Do not represent results as validated psychological or spiritual scores.

## 7. Assessment item

```ts
interface AssessmentItem {
  id: string;
  prompt: string;
  domainId: string;        // hidden from user during assessment
  direction: 'positive' | 'reverse';
  version: string;
  active: boolean;
}
```

## 8. Gospel Encounter

Optional separate object if encounter summaries are shared across practices.

```ts
interface GospelEncounter {
  id: string;
  title: string;
  references: string[];
  summary: string;
  practiceIds: string[];
}
```

This can power **See This Practice in His Life** while preventing duplicated narrative copy.

## 9. Saved / Considered Practice

If the UX includes “This speaks to me” or “Consider for Practice,” model it separately from a cycle.

```ts
interface SavedPractice {
  userId: string;
  practiceId: string;
  savedAt: string;
  sourceEntryRoute?: string;
}
```

Saving is not a commitment.

## 10. Reflection history

Reflection may live on PracticeCycle or as linked journal entries, depending on existing infrastructure. The user-facing requirement is chronological history for repeated cycles on the same practice.

## 11. Cross-app relationships

Future optional field:

```ts
relatedCommandmentIds: string[]
```

This supports:

**Jesus Modeled This** ↔ **Jesus Taught This**

Do not block v1 on exhaustive cross-linking.

## 12. Content versioning

Preserve:

- stable `CDP-*` ID;
- content version;
- status;
- updated timestamp;
- optional evidence-review status.

Possible editorial lifecycle:

`candidate → evidence_reviewed → editorial_reviewed → published`

Use established Sanity workflow if equivalent mechanisms already exist.

## 13. Structured seed data

See:

- `data/domains.v0.1.yaml`
- `data/practices.v0.1.yaml`
- `data/life-situations.v0.1.yaml`
- `data/assessment-framework.v0.1.yaml`

These are **developmental seed data**, not production-ready copy.
