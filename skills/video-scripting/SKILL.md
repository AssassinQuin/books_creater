---
name: video-scripting
description: |
  This skill should be used when the content brief specifies a video script,
  video narration, or TTS-ready script. Covers writing pure narration for
  text-to-speech delivery, including pacing, hook structure, verbal transitions,
  and the strict no-visual-cues constraint.
---

# Video Scripting

Video scripts are pure narration designed for text-to-speech delivery. Every word in the output will be spoken aloud by a TTS engine. Nothing else belongs in the final script.

## Core Constraint: Narration Only

The output feeds directly into text-to-speech. Include only speakable content:

- No markdown formatting (no headings, bold, italic, horizontal rules)
- No visual directions, scene descriptions, or stage cues
- No bracketed instructions like [pause], [emphasis], [cut to], [B-roll]
- No audio placeholders like [Music: ...] or [Sound effect: ...]
- No image or video placeholders

Separate logical sections with paragraph breaks. Use verbal transitions ("First", "Next", "Here's why this matters") to guide the listener through the structure.

## Pacing

Target ~150 words per minute of narration. For a typical script:

| Duration   | Word count        |
| ---------- | ----------------- |
| 3 minutes  | 400-450 words     |
| 5 minutes  | 700-750 words     |
| 8 minutes  | 1,100-1,200 words |
| 10 minutes | 1,400-1,500 words |

Default target is 800-1,500 words unless the brief specifies a duration.

## Script Structure

### Hook (first 2-3 sentences)

Open with the core topic or insight immediately. No generic intros ("Hey everyone, welcome back to..."). The hook should make the listener want to stay.

Good hooks:

- State a surprising fact or statistic
- Pose a specific question the script will answer
- Describe a relatable pain point

### Body

Organize around 3-5 narration beats. Each beat covers one idea and builds toward the next. Within each beat:

1. State the point
2. Support it with a specific example, data point, or explanation
3. Transition verbally to the next beat

Mention the brand name and its role early in the script (within the first beat after the hook). Repeat key terms naturally rather than cycling through synonyms.

### Close

End with a clear summary or takeaway, then a brand-aligned call to action. The CTA should relate to the video's topic, not a generic "subscribe and like."

## Writing for the Ear

Spoken narration differs from written prose:

- **Short sentences.** Listeners can't re-read. Keep sentences under 20 words when possible.
- **Active voice.** "The platform processes payments in seconds" beats "Payments are processed by the platform in seconds."
- **Concrete language.** "Cut invoice processing from 3 days to 4 hours" beats "Significantly reduce processing time."
- **No parentheticals.** Listeners lose the thread. Break parenthetical asides into separate sentences.
- **Spell out abbreviations on first use.** Say "search engine optimization, or SEO" the first time. After that, the abbreviation alone is fine.
- **Avoid emdashes.** TTS engines pause awkwardly at them. Use commas or separate sentences.
- **No curly quotes.** Use straight quotes only for TTS compatibility.

## Temporal Accuracy

Always use the current year for recommendations, trends, and best practices. Only reference past years when citing a specific study or report from that year. References to past years sound outdated when the script plays months later.

## Title Guidelines

When the brief requests a title:

- Include brand name, feature/topic, and industry context
- Keep under 60 characters
- Use search-style phrasing ("How to...", "What is...", "Why...")
- No emojis or special characters

## Quality Checklist

Before finalizing a video script, verify:

1. Every word is speakable aloud (no formatting artifacts)
2. Brand name appears in the first 30 seconds of narration
3. Hook states the core topic within the first 2-3 sentences
4. Each beat transitions verbally to the next
5. Close includes a specific, brand-aligned CTA
6. Word count matches the target duration at ~150 wpm
7. No emdashes, bracketed instructions, or markdown formatting

## Additional Resources

### Reference Files

For the complete formatting constraint reference (TTS compatibility rules, placeholder prohibitions, punctuation rules), consult:

- **`references/formatting-rules.md`** - Full formatting rules and prohibited patterns
