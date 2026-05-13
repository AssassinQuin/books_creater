# Style: Lessons in Clarity and Grace

_An original distillation of the diagnostic revision approach taught by
Joseph M. Williams and Joseph Bizup. This is not excerpted text — it is a
reference guide inspired by their methodology for identifying and fixing
unclear prose._

## Contents

- [I. The Core Principle: Actions and Agents](#i-the-core-principle-actions-and-agents)
- [II. Diagnosing Unclear Prose](#ii-diagnosing-unclear-prose)
- [III. Managing Information Flow](#iii-managing-information-flow)
- [IV. Cohesion and Coherence](#iv-cohesion-and-coherence)
- [V. Emphasis and Shape](#v-emphasis-and-shape)
- [VI. Concision](#vi-concision)
- [VII. Elegance](#vii-elegance)

---

## I. The Core Principle: Actions and Agents

Most unclear writing has a single root cause: the important actions are
buried in nouns, and the agents performing those actions are missing or
hidden. The revision method is mechanical:

1. **Find the action.** What is actually happening in this sentence?
2. **Make the action a verb.** If the action is hiding in a noun
   (a nominalization), convert it back to a verb.
3. **Find the agent.** Who or what is performing that action?
4. **Make the agent the subject.** If the agent is buried in a
   prepositional phrase or missing entirely, promote it to subject
   position.

This single transformation fixes the majority of unclear sentences.

### Nominalizations: The Primary Culprit

A nominalization is a verb or adjective turned into a noun:

| Verb/Adjective | Nominalization |
| --- | --- |
| discover | discovery |
| analyze | analysis |
| fail | failure |
| decide | decision |
| move | movement |
| react | reaction |
| resist | resistance |
| propose | proposal |
| evaluate | evaluation |
| accurate | accuracy |
| precise | precision |
| careless | carelessness |
| different | difference |
| difficult | difficulty |
| important | importance |
| able | ability |
| stable | stability |

Nominalizations are not inherently bad. Some are necessary:

- When the nominalization is a familiar, concrete concept: "The
  **decision** was unanimous." (You could say "They decided unanimously,"
  but "the decision" is now the topic being discussed.)
- When the nominalization is the subject of a sentence and refers back
  to a prior sentence: "This **analysis** revealed a flaw." (The
  analysis was established in the prior sentence.)
- When the nominalization names something that has no verb form:
  "Entropy increases." (Entropy is not derived from a verb.)

Nominalizations are harmful when they bury the action:

**Buried:**

> There was a **discovery** by the researchers of a **connection** between
> the **failure** of the system and the **instability** of the power supply.

**Revised:**

> The researchers discovered that the system failed because the power
> supply was unstable.

The buried version has four nominalizations, no clear agent as subject,
and uses "there was" as a placeholder. The revised version has clear agents
(researchers, system, power supply) performing clear actions (discovered,
failed, was unstable).

### The Diagnostic Process

For any sentence that feels unclear, heavy, or bureaucratic:

1. **Underline the first seven or eight words.** If they contain no
   agent performing an action, the sentence probably buries its meaning.
2. **Circle the nominalizations.** Each one is a potential buried action.
3. **Ask: who is doing what?** If you cannot immediately answer, the
   sentence needs revision.
4. **Rebuild:** Make the agent the subject, make the action a verb,
   arrange the rest as needed.

---

## II. Diagnosing Unclear Prose

Beyond nominalizations, several patterns produce unclear writing. Each has
a diagnostic question and a mechanical fix.

### Pattern: Vague Subjects

When sentences begin with vague subjects ("it," "there," "this," "that,"
"these," "those") followed by a form of "be," the sentence usually delays
its real subject.

**Vague:**

> There is a tendency among developers to avoid writing tests until
> the end of a sprint.

**Clear:**

> Developers tend to avoid writing tests until the end of a sprint.

**Diagnostic:** Does the sentence begin with "There is/are," "It is,"
or a demonstrative pronoun + "be"? If so, find the real subject and
promote it.

**When vague subjects are acceptable:**

- When introducing a new topic: "There are three factors to consider."
  (The real subject — the factors — hasn't been established yet. The
  "there are" construction sets it up.)
- When the "it" has a clear antecedent: "The test failed. It threw an
  exception on line 42." (Clear reference.)

### Pattern: Excessive Prepositional Phrases

Strings of prepositional phrases ("of the," "in the," "for the," "by
the") create a chain that the reader must parse one link at a time.

**Chained:**

> The cause of the failure of the connection of the service to the
> database in the production environment was a misconfiguration of
> the connection pool settings.

**Clear:**

> The service failed to connect to the production database because
> the connection pool was misconfigured.

**Diagnostic:** Count prepositional phrases. More than three in a row
signals a sentence that needs restructuring. Convert some phrases into
verbs, adjectives, or separate sentences.

### Pattern: Passive Concealment

Passive voice is not inherently wrong, but it is a problem when it hides
the agent to avoid accountability or specificity.

**Concealed:**

> It was determined that the requirements had been misunderstood, and
> as a result, the deadline was missed.

**Clear:**

> The team misunderstood the requirements and missed the deadline.

**Diagnostic:** Can you add "by ___" to the passive verb and the agent
is either unknown, obvious, or deliberately hidden? If unknown or obvious,
passive may be fine. If deliberately hidden, make the agent explicit.

### Pattern: Metadiscourse Overload

Metadiscourse is writing about the writing — telling the reader what you
are about to say, what you just said, or how the document is organized.

**Overloaded:**

> In this section, we will examine three approaches to solving this
> problem. First, we will look at the caching approach. Then, we will
> consider the indexing approach. Finally, we will evaluate the
> denormalization approach.

**Direct:**

> Three approaches solve this problem: caching, indexing, and
> denormalization.

Some metadiscourse is useful — topic sentences that orient the reader,
transitions that signal a turn. The problem is excess: telling the reader
you are about to tell them something, instead of just telling them.

**Diagnostic:** Does the sentence describe the document's structure rather
than its content? If so, cut it or convert it to a topic sentence that
simultaneously orients and delivers information.

---

## III. Managing Information Flow

Clear prose manages what the reader knows at each point in a sentence.
The principle: **begin sentences with familiar information, end them
with new information.**

### Old Before New

Readers process sentences by anchoring on what they already know (the
topic, the "old" information) and then absorbing what is new. When new
information comes first, the reader has nothing to anchor it to.

**New first (disorienting):**

> A race condition in the message queue caused the duplicate records.
> Implementing idempotency keys at the consumer level would prevent
> this class of bugs. A retry mechanism with deduplication was what
> the team ultimately chose.

**Old first (oriented):**

> The duplicate records were caused by a race condition in the message
> queue. This class of bugs can be prevented by implementing idempotency
> keys at the consumer level. The team ultimately chose a retry mechanism
> with deduplication.

Each sentence begins with something the reader already knows (from the
previous sentence or from context) and ends with the new information
that the sentence contributes.

### Topic Strings

A sequence of sentences is cohesive when the reader can identify a
consistent topic — typically the grammatical subject — across sentences.
When the topic shifts unpredictably, the reader feels lost.

**Shifting topics:**

> The API validates tokens. Rate limiting is enforced at the gateway.
> Logging captures every request. The dashboard shows error rates.

**Consistent topic:**

> The API validates tokens, enforces rate limits at the gateway, logs
> every request, and reports error rates on the dashboard.

Or, if separate sentences are needed:

> The API validates tokens on every request. It enforces rate limits
> at the gateway. It logs each request for audit. It surfaces error
> rates on the dashboard.

**Diagnostic:** Underline the subject of each sentence in a paragraph.
If the subjects are all different, the paragraph lacks cohesion. Either
unify the subjects or add explicit transitions that explain the shift.

### Stress Position

The end of a sentence is its stress position — the place where readers
naturally expect the most important new information. Place the new,
important, complex, or emphatic material at the end.

**Stress misplaced:**

> The performance improvements were, after six months of optimization
> work by the infrastructure team, significant.

**Stress at end:**

> After six months of optimization work, the infrastructure team
> achieved significant performance improvements.

This principle works at every level: the end of a clause, the end of a
sentence, the end of a paragraph, the end of a section.

---

## IV. Cohesion and Coherence

Cohesion is sentence-to-sentence connection. Coherence is the overall
sense that a passage adds up to something. A passage can be cohesive
(each sentence follows from the last) but incoherent (it doesn't go
anywhere). Good writing needs both.

### Cohesion: Linking Sentences

Sentences link through:

- **Repetition**: Repeat a key term from the end of one sentence at the
  beginning of the next.
- **Pronouns**: Use "it," "they," "this" to refer back to established
  topics.
- **Consistent topic**: Keep the same subject across sentences (topic
  strings).
- **Transitional logic**: Use words that signal the relationship ("but,"
  "so," "therefore," "however," "because").

**Uncohesive:**

> The cache reduces latency. Database queries are the primary bottleneck.
> Users expect sub-second responses. CDN configuration affects perceived
> performance.

**Cohesive:**

> The primary bottleneck is database queries. The cache reduces this
> latency by serving repeated requests from memory. Users expect
> sub-second responses, and the CDN further reduces perceived latency
> for static assets.

### Coherence: The Passage Has a Point

A coherent passage has:

1. **A clear point** — stated or strongly implied early
2. **A consistent string of topics** — the subjects of sentences relate
   to the point
3. **A thematic thread** — key terms recur throughout
4. **A trajectory** — the passage moves toward a conclusion, not in
   circles

**Diagnostic:** After reading a paragraph, can you state its point in
one sentence? If not, the paragraph lacks coherence. Either it makes
multiple points (split it) or no point (cut it or give it one).

---

## V. Emphasis and Shape

### Sentence Shape

A well-shaped sentence moves from the simple to the complex, from the
short to the long, from the familiar to the new. This creates a sense
of momentum and resolution.

**Flat:**

> The system handles authentication and authorization and session
> management and rate limiting and logging.

**Shaped:**

> The system handles authentication, manages sessions, enforces rate
> limits, and logs every request for audit.

The shaped version varies the verb, creates rhythm through parallel
structure, and ends with the most specific item.

### Short Sentences for Emphasis

After a sequence of longer, complex sentences, a short sentence creates
emphasis through contrast. The reader pauses. The point lands.

Use this deliberately. Too many short sentences in a row create a
choppy, breathless quality. One short sentence after two or three longer
ones is the sweet spot.

### Long Sentences for Nuance

Long sentences are not unclear sentences. A long sentence that manages
its information flow — old before new, agent as subject, action as
verb — can be perfectly clear. Length becomes a problem only when the
sentence loses control of its structure: when the reader cannot hold
the subject long enough to reach the verb, or when subordinate clauses
nest so deeply that the reader loses track of the main clause.

**Test for a long sentence:** Can you read it aloud in one breath without
losing the thread? If not, it is too long — not because of word count,
but because of structural complexity.

---

## VI. Concision

Concision is not brevity. Brevity means using few words. Concision means
using no unnecessary words. A long sentence can be concise if every word
does work.

### Categories of Verbal Clutter

**Redundant pairs:**

| Redundant | Concise |
| --- | --- |
| full and complete | complete |
| each and every | every |
| first and foremost | first |
| true and accurate | accurate |
| various and sundry | various |
| any and all | all |
| basic and fundamental | fundamental |
| hopes and desires | hopes |
| past experience | experience |
| future plans | plans |
| final outcome | outcome |
| end result | result |
| free gift | gift |
| unexpected surprise | surprise |

**Redundant modifiers:**

| Redundant | Concise |
| --- | --- |
| absolutely essential | essential |
| completely finished | finished |
| basic fundamentals | fundamentals |
| important essentials | essentials |
| future plans | plans |
| past history | history |
| terrible tragedy | tragedy |
| completely unanimous | unanimous |

**Redundant categories:**

| Redundant | Concise |
| --- | --- |
| period of time | period |
| area of concern | concern |
| type of situation | situation |
| kind of problem | problem |
| process of elimination | elimination |
| state of confusion | confusion |
| large in size | large |
| round in shape | round |
| green in color | green |
| heavy in weight | heavy |

### Meaningless Hedges

These hedges add no precision — they signal uncertainty without
specifying degree:

- somewhat, to some extent, in some ways
- perhaps, possibly, maybe (when not genuinely uncertain)
- tends to, seems to, appears to (when the writer knows the answer)
- it could be argued that (then argue it)
- more or less, for the most part, in a sense

Hedges are appropriate when the uncertainty is real: "The results
suggest a correlation" (if the evidence is preliminary). They are
clutter when the writer is hedging for comfort: "It seems that the
tests are failing" (either they are or they aren't).

---

## VII. Elegance

Elegance in prose comes from balance, rhythm, and the unexpected.

### Balance and Symmetry

Balanced constructions create a sense of completeness:

> "Ask not what your country can do for you — ask what you can do
> for your country."

The balance works because the two halves mirror each other in structure
while reversing the meaning. Look for opportunities to create balance
when making contrasts or comparisons.

### Climactic Order

When listing items, order them from least to most important, from
shortest to longest, from simplest to most complex. The list should
build to a climax, not trail off.

**Trailing off:**

> The system provides real-time analytics, comprehensive reporting,
> dashboards, and charts.

**Climactic:**

> The system provides charts, dashboards, comprehensive reporting,
> and real-time analytics.

### The Well-Turned Sentence

Occasionally, invest extra craft in a sentence that carries significant
weight — the thesis statement, the concluding sentence, the key insight.
These sentences benefit from:

- **Parallel structure** at a level beyond basic correctness
- **Rhythmic variation** — a long clause followed by a short punch
- **Precise word choice** — the single right word rather than an
  approximate phrase
- **Strategic repetition** — echoing a word or structure for emphasis

This is not a technique for every sentence. Reserve it for moments
that deserve the reader's full attention.
