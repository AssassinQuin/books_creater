# Video Script Formatting Rules

Complete reference for TTS-compatible video script formatting. These rules ensure scripts render correctly when fed to text-to-speech engines.

## Prohibited Elements

### Markdown Formatting

TTS engines read markdown syntax aloud or produce garbled output. None of the following belong in a video script:

| Element          | Example                 | Why prohibited                    |
| ---------------- | ----------------------- | --------------------------------- |
| Headings         | `# Title`, `## Section` | TTS reads the hash characters     |
| Bold/italic      | `**word**`, `*word*`    | TTS reads the asterisks           |
| Horizontal rules | `---`, `***`            | TTS produces silence or artifacts |
| Lists            | `- item`, `1. item`     | TTS reads the markers literally   |
| Links            | `[text](url)`           | TTS reads the URL aloud           |
| Code blocks      | `` `code` ``            | TTS reads the backticks           |

### Visual and Stage Directions

The script is narration only. No visual layer exists in the TTS output:

- No scene descriptions: ~~[Scene: office setting]~~
- No camera directions: ~~[Cut to product demo]~~
- No B-roll cues: ~~[B-roll: team working]~~
- No on-screen text: ~~[Text overlay: "50% faster"]~~
- No visual transitions: ~~[Fade to black]~~

### Audio Placeholders

TTS reads these literally:

- No music cues: ~~[Music: upbeat intro]~~
- No sound effects: ~~[Sound effect: notification chime]~~
- No audio transitions: ~~[Audio fade out]~~

### Delivery Instructions

TTS engines cannot interpret performance notes:

- No pause markers: ~~[pause]~~, ~~[beat]~~
- No emphasis markers: ~~[emphasis]~~, ~~[stressed]~~
- No tone directions: ~~[excitedly]~~, ~~[serious tone]~~

## Punctuation Rules

### Emdashes

Avoid emdashes (`—`). TTS engines produce awkward pauses at emdashes that disrupt narration flow.

Instead of:

> The platform handles everything — from invoicing to reconciliation — in a single dashboard.

Write:

> The platform handles everything from invoicing to reconciliation in a single dashboard.

Or split into separate sentences:

> The platform handles everything in a single dashboard. That includes invoicing, reconciliation, and reporting.

### Curly Quotes

Use straight quotes (`"..."`) only. Curly quotes (`\u201c...\u201d`) cause encoding issues in some TTS systems.

### Ellipses

Avoid trailing ellipses (`...`). They create unpredictable pauses. End sentences with periods.

## Section Separation

Use paragraph breaks (blank lines) to separate logical sections. Verbal transitions at the start of each new section guide the listener:

Good transitions:

- "Now, here's where it gets interesting."
- "So what does this mean in practice?"
- "Let's look at a specific example."
- "The second factor is just as important."

Bad transitions (too mechanical):

- "Moving on to our next point..."
- "In this section, we'll discuss..."
- "Let's transition to..."

## Numbers and Abbreviations

### Numbers

- Spell out numbers one through nine ("three reasons", not "3 reasons")
- Use digits for 10 and above ("15 percent faster")
- Spell out numbers at the start of a sentence ("Forty percent of users...")
- For large numbers, use spoken form: "2.5 million" not "2,500,000"

### Abbreviations

- Spell out on first use: "search engine optimization, or SEO"
- After first use, the abbreviation alone is fine
- For well-known abbreviations (URL, API, CEO), spelling out is optional but preferred for general audiences
- Never assume the audience knows industry-specific abbreviations

### Dates

- Use spoken form: "January twenty-twenty-five" or "early 2025"
- Avoid date formats like "01/25/2025" or "2025-01-25"

## Placeholder Prohibition

Scripts may be fed directly to TTS without human review. Any placeholder text will be read aloud:

- No `[INSERT BRAND NAME]` or `[COMPANY]`
- No `[STATISTIC]` or `[DATA POINT]`
- No `[LINK]` or `[URL]`
- No `[IMAGE]` or `[VISUAL]`

If specific data is unavailable, write around it or flag the gap to the user rather than leaving a placeholder.
