---
name: prose-craft
description: |
  Use when drafting or revising any document where writing quality matters —
  anything a human will read, review, or act on. Establishes voice (genre,
  audience, register) and selects a styleguide before writing begins, then
  provides word choice corrections and construction techniques that address
  persistent LLM weaknesses. If the output needs to sound like it was written
  by someone specific for someone specific, load this skill.
---

# Prose Craft

Good writing is not the absence of bad patterns. The humanizer removes AI tells;
this skill teaches you to write well.

Before drafting, establish two things: voice (who you sound like) and styleguide
(how sentences are constructed). Then apply the word choice and construction
corrections below. The styleguide handles grammar and usage rules.

## Voice

Before writing, determine who this document sounds like it was written by, and
for whom. If project instructions or the user already establish voice, adopt it.
Otherwise, reason through the following layers internally before drafting.

### Resolution order

1. **Project instructions** — If CLAUDE.md, AGENTS.md, or brand voice documents
   declare voice, tone, audience, or register conventions, adopt them. These
   take precedence.
2. **Explicit user request** — If the user specified voice, audience, or tone
   in this session, adopt it.
3. **Internal reasoning** — Work through the three layers below silently. State
   your resulting voice choice briefly and proceed. The user can override.

### Layer 1 — What does this document do?

Genre is not a format — it is a social action. A design doc does not merely
describe a system; it builds consensus on an approach. A postmortem does not
merely list failures; it prevents recurrence. A tutorial does not merely
explain steps; it transfers a skill.

Before choosing tone or register, identify the action this document performs:

| Action            | The document...                                      | Voice consequence                                      | Common archetypes                                                                                |
| ----------------- | ---------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| Inform            | Delivers facts or analysis for the reader to absorb  | Explanatory, concrete, evidence-forward                | Explainer (concept → why it matters → how it works), data-driven (finding → data → implications) |
| Persuade          | Moves the reader to accept a position or take action | Thesis-driven, fair-minded, evidence over adjectives   | Opinion/argument (position → evidence → counterargument → reaffirmation)                         |
| Build consensus   | Aligns a group around a decision or approach         | Direct, anticipates objections, recommendation-first   | Comparison (criteria → options → recommendation), design doc                                     |
| Transfer a skill  | Enables the reader to do something new               | Patient, sequential, second-person, anticipates errors | How-to guide (problem → steps → result), tutorial                                                |
| Certify or record | Creates a durable record for future reference        | Precise, neutral, structured for retrieval             | Postmortem, specification, changelog                                                             |
| Narrate           | Engages through story and human experience           | Vivid, specific, scene-driven                          | Case study, profile, incident narrative                                                          |

### Layer 2 — Who is the discourse community?

Every document is written for a community with shared goals, communication
channels, genres, vocabulary, and membership norms. The voice that works is the
one that demonstrates membership in (or appropriate respect for) that community.

Reason through these characteristics:

- **Shared goals** — What does this community exist to accomplish? How does this
  document serve those goals?
- **Communication channels** — Through what medium does this community exchange
  ideas? (Slack, journals, PRs, memos, blog posts, conference talks?) The
  channel's conventions set register expectations.
- **Genres the community owns** — What document types does this community
  produce? What are _their specific_ conventions for this type? A "design doc"
  at a startup looks different from a "design doc" at a government contractor.
- **Specialized vocabulary** — What terms carry precise meaning inside the
  community? Which terms would be jargon to outsiders? Is the reader inside
  or outside?
- **Writer's position** — Are you writing as an insider (shared lexis, assumed
  context) or addressing the community from outside (define terms, establish
  credibility)?

### Layer 3 — What conventions does this community expect?

Writing conventions vary by community. What marks a document as "one of ours"
to an expert reader — and what would immediately mark it as foreign?

Assess along these axes:

| Axis          | Range                                                                     |
| ------------- | ------------------------------------------------------------------------- |
| **Person**    | First person ("I argue") ↔ Impersonal ("It was observed")                 |
| **Evidence**  | Data and citations ↔ Anecdotes and examples ↔ Logical argument            |
| **Hedging**   | Strong claims ("This proves") ↔ Heavy qualification ("may suggest")       |
| **Structure** | Rigid template (IMRD, RFC) ↔ Flexible (essay, think piece)                |
| **Register**  | Casual (contractions, fragments) ↔ Formal (no contractions, third person) |
| **Jargon**    | Assumed (expert audience) ↔ Defined on first use (mixed audience)         |

When the session context lacks detailed conventions for the identified genre,
load `references/on-writing-well.md` for per-genre guidance. Skip the reference
if project instructions or brand voice already define the conventions.

When uncertain about register, choose one level more casual than your instinct
suggests. LLMs err toward excessive formality.

### Voice statement

After reasoning through the three layers, synthesize a one-sentence voice
statement and hold it as a reference throughout the session:

> "This is **[action]** writing for **[community]** at **[register]** register.
> Conventions: **[person, evidence type, hedging level, jargon stance]**."

If the prose drifts from this statement, the voice is slipping.

## Styleguide Selection

Determine the governing styleguide in this order:

1. **Explicit user request** — If the user specified a styleguide in this
   session, use it.
2. **Project instructions** — If CLAUDE.md, AGENTS.md, or project instructions
   declare a preferred styleguide, use it.
3. **Best judgment from context** — Assess the document's genre, audience, and
   purpose. Choose the best-fit styleguide, state your choice and reasoning,
   and proceed. The user can override.

Once determined, load the reference file via `read_skill_resource` and use it
as the authoritative source for grammar, usage, and stylistic rulings throughout
the session.

### Styleguides (pick one)

| Reference                        | File                                         | Best fit for                                                                                                                                                 |
| -------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Elements of Style**            | `references/elements-of-style.md`            | Terse, economical prose. Internal documentation, READMEs, commit messages, technical references. When brevity is the priority.                               |
| **Dreyer's English**             | `references/dreyers-english.md`              | Modern, opinionated prose. Blog posts, articles, proposals, any document that benefits from personality and contemporary usage.                              |
| **Lessons in Clarity and Grace** | `references/lessons-in-clarity-and-grace.md` | Complex or analytical prose. Design documents, research reports, strategic proposals. When the material is dense and clarity requires structural discipline. |

### Supplementary references

These references enrich specific writing situations. Load them only when the
session context lacks the guidance they provide. If project instructions, brand
voice, or CLAUDE.md already cover the same ground, the existing conventions
take precedence — do not load the reference.

| Reference           | File                            | Load when                                                                                                                                                                              | Skip when                                                                                                                                         |
| ------------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **On Writing Well** | `references/on-writing-well.md` | The voice discovery process (above) identified a genre but the session context lacks detailed conventions for that genre — register, structure, evidence norms, audience expectations. | Project instructions or brand voice already define genre conventions for this document. Loading the reference would introduce a competing source. |
| **Microstyle**      | `references/microstyle.md`      | Writing headlines, taglines, subject lines, button text, product names, or other short-form text where every word carries maximum weight.                                              | The task is long-form prose. Short-form techniques do not apply.                                                                                  |

## Styleguide Calibration

After loading a styleguide, assess its signal strength. This determines how
much latitude it earns over the defaults in this skill.

**Strong** — Specific, actionable rules with clear examples. Takes explicit
positions on contested questions (split infinitives, serial comma, singular
"they"). All three styleguides in this skill qualify. Honor the styleguide;
let its rules override the defaults below when they conflict.

**Moderate** — Some rules present but vague or incomplete. Apply the defaults
below in full; let the styleguide shape register and tone.

**No styleguide loaded** — Apply the defaults below at full strength.

Calibration is not a score. You are deciding how much latitude the styleguide
earns. A strong styleguide that says "split infinitives are fine" overrides the
default caution. A weak styleguide that says nothing gives you no reason to
deviate.

## Principles That Always Apply

These hold regardless of genre, styleguide, or audience. They are close enough
to universal that overriding them requires extraordinary justification.

**Consistency.** Apply the same conventions uniformly within a document. If you
use sentence case in headings, use it everywhere. If you use the serial comma,
use it in every list. Inconsistency signals carelessness regardless of which
convention you chose.

**Clarity of intent.** The reader should be able to determine what you mean.
Even in deliberately ambiguous rhetoric, the ambiguity is the intent. Writing
that fails to communicate what it set out to communicate is defective in every
context.

**Progressive development.** Don't require the reader to know something you
haven't told them yet. Each section should provide the context the next section
depends on. The specific ordering (problem before solution, concept before
application) varies by genre. The principle — that an order exists and respects
information dependency — does not.

## Construction Techniques

### Sentence Rhythm

Good prose varies sentence length deliberately. Three sentences of the
same length in a row create a monotonous pattern. Fix it by:

- **Breaking a long sentence into two short ones**
- **Combining two short sentences into one longer one**
- **Starting one sentence with a dependent clause** instead of the subject

Read your paragraph aloud. If it sounds like a metronome, rewrite.

A useful pattern: medium, short, long. Or long, short, medium. The short
sentence after a long one creates emphasis. The long sentence after a
short one provides context. What matters is variation, not any particular
formula.

Approximate sentence length guide:

- Short: under 10 words
- Medium: 10 to 20 words
- Long: 20 to 35 words
- Very long: over 35 words (use sparingly, ensure clarity)

### Paragraph Construction

Each paragraph makes one point. Organize it:

1. **Open with the point** — state what this paragraph is about in the
   first sentence. Don't build up to it.
2. **Develop with evidence** — examples, data, quotations, or reasoning
   that support the opening claim.
3. **Close with implication** — what follows from this point? Why does it
   matter for the next paragraph or the reader's decision?

Short paragraphs (1-2 sentences) can serve as transitions or emphasis. The
principle is: the reader should know what the paragraph is about from its
first sentence.

### The Strong Opening

The first sentence of any section does the most work. It must:

- **Establish the topic** without preamble
- **Signal the angle** — not just what you'll discuss, but your position
- **Earn the next sentence** — give the reader a reason to continue

Weak openings defer the point: "There are many factors to consider when
evaluating..." Strong openings state it: "Evaluation frameworks fail when
they measure effort instead of outcomes."

### The Strong Close

The last sentence of a section resolves it. It should not:

- Repeat the opening in different words
- Trail off into vagueness
- Introduce a new idea

It should:

- State the consequence of what was argued
- Connect to what comes next
- Leave the reader with the strongest version of the point

## How This Skill Composes with Others

**Humanizer** removes AI-generated patterns (significance inflation,
promotional language, synonym cycling). This skill teaches positive
construction — how to write well, not just how to avoid writing badly.
Load this skill first to produce strong initial prose, then load humanizer
to catch remaining artifacts.

**Citation sourcing** handles source quality, attribution formatting, and
hallucination prevention. This skill handles the prose around those
citations — how claims are phrased, how evidence is woven into arguments.

**SEO optimization** handles search-specific structural concerns (answer-first
formatting, FAQ sections, AI citability patterns). This skill handles prose
quality within whatever structure the content requires.

## Credits

The `references/elements-of-style.md` file is taken directly from
[`obra/elements-of-style`](https://github.com/obra/elements-of-style) by
[Jesse Vincent](https://github.com/obra), a Claude Code skill in the
superpowers marketplace. The underlying Strunk text is public domain;
the formatted reference file is the work of that project. Full credit
to the author.
