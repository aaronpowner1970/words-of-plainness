# UX and Replayability Architecture

## Core experience loop

```text
CHAPTER 18 / APP ENTRY
        │
        ├── Help Me Choose
        ├── Choose a Domain
        ├── Life Situation
        ├── Browse All
        └── For Today
                 │
                 ▼
          SELECT PRACTICE
                 │
                 ▼
          WHAT JESUS DID
                 │
                 ▼
          HOW WE PRACTICE
                 │
                 ▼
       HOW IT BLESSES LIVES
                 │
                 ▼
       HOW WILL YOU PRACTICE?
                 │
                 ▼
          PRACTICE CYCLE
                 │
          [ordinary life]
                 │
                 ▼
              REFLECT
             /       \
     PRACTICE AGAIN   EXPLORE ANOTHER
             \       /
               RETURN
```

There is deliberately **no FINISH node**.

## Home screen

### Returning user
Lead with **Continue Your Practice** if an open cycle exists, then allow new exploration.

### New or uncommitted user
Lead with **Where would you like to begin?**

Routes:

1. Help Me Choose
2. Choose a Domain
3. Life Situations
4. Browse All
5. For Today

## Domain presentation

Do not expose all ~70 practices immediately.

Each domain card should contain a concise name, one-sentence description, optional encounter cue, descriptive practice count, and Explore action.

Avoid progress bars such as `5/9 complete`.

## Domain page

Users do not need to study practices in order. Allow lightweight marking such as **Consider for Practice** or **This Speaks to Me**, separate from actual commitment.

## Practice detail

Recommended order:

1. Practice title and descriptor
2. Key New Testament references
3. **What Jesus Did**
4. Optional **See This Practice in His Life**
5. **How We Practice**
6. **How It Blesses Lives**
7. **How Will You Practice?**

Suggested actions should be observable and small enough to attempt.

## Commitment builder

Ask:

1. **Who or what situation comes to mind?**
2. **What will you actually do differently?**
3. **When might you practice this?**

Generate/display a first-person intention and allow editing.

## Behavioral self-assessment

Recommended initial shape:

- approximately 24 items;
- three situational items per domain;
- four-point scale: Rarely / Sometimes / Often / Usually;
- Not applicable / unsure where necessary;
- hide domain labels while responding;
- do not claim psychometric validation.

Recommend **two domains**, not one, and always allow **Choose another domain**.

## Practice cycle lifecycle

Suggested states:

- `planned`
- `active`
- `reflected`
- `closed`

Repeating a practice creates another cycle rather than reopening a terminal virtue state.

## Return loop

On return, invite reflection on a prior/current practice before pushing new material.

Prompts:

- What happened?
- What did you notice?
- What was difficult?
- What would you try differently?
- Continue this practice or explore another?

## My Practice Journey

Prefer journey language over progress language.

Potential sections:

- Current Practice
- Recent Reflections
- Practices I Keep Returning To
- Domains Explored
- Practice Timeline

Potential metrics are descriptive only: practice cycles, reflections, unique practices visited, domains explored.

## Life Situations

Use lived circumstances as a secondary discovery system, analogous to curated paths/topics in Keep My Commandments.

Initial examples:

- When I am angry
- When someone has hurt me
- When someone keeps failing
- When I am leading others
- When I disagree with someone
- When I feel overlooked
- When I am helping someone
- When my help does not seem to work
- When I am exhausted
- When I have power in a conflict
- When someone outside my group does good
- When I am grieving with someone
- When I am anxious
- When I am being praised
- When I need to receive help
- When I am parenting
- When a close relationship is strained
- When I am sharing my faith

## For Today

Surface one practice without implying divine selection or algorithmic diagnosis.

Possible actions:

- Explore this practice
- Show another
- Save for later

## Replayability tests

Verify that the experience works when a user:

1. returns tomorrow and chooses another domain;
2. returns six months later to the same domain;
3. repeats one practice four times;
4. never takes the assessment;
5. retakes assessment over years;
6. browses without saving;
7. accumulates multiple reflections on one practice;
8. enters through Life Situations;
9. leaves a cycle unfinished without shame;
10. never attempts to “cover” all 70.
