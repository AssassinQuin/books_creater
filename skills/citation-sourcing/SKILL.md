---
name: citation-sourcing
description: |
  Source tier definitions, citation formatting, verification patterns, and
  hallucination prevention. Load when writing content that requires external
  evidence, statistics, or expert claims. Covers what sources to use, how to
  cite them, and what to avoid.
---

# Citation Sourcing

Every statistic needs a named source. Every claim needs evidence or an explicit opinion label. Content backed by named research gets cited; content backed by "studies show" does not.

## Source Tiers

Use the highest-tier source available for each claim.

| Tier       | Authority    | Examples                                                                                   | Use For                                                |
| ---------- | ------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------ |
| **Tier 1** | Highest      | Academic journals, government data (BLS, Census), Gartner, Forrester, McKinsey             | Key statistics, research findings, industry benchmarks |
| **Tier 2** | High         | HBR, WSJ, major news outlets, respected industry publications                              | Trends, expert opinions, case studies                  |
| **Tier 3** | Acceptable   | Established industry blogs with named authors, company research with methodology disclosed | Definitions, background, general context               |
| **Avoid**  | Insufficient | Anonymous blogs, content farms, undisclosed vendor marketing                               | Should never be primary sources                        |

Wikipedia is useful for discovering primary sources via its references — cite those primary sources directly rather than citing Wikipedia itself.

### Source Selection Rules

- Use Tier 1-2 sources for key claims and statistics
- Tier 3 sources are fine for background context and definitions
- Prefer primary sources over secondary. If a blog post cites a McKinsey report, find and cite the McKinsey report directly. Secondary sources are acceptable only when the primary source is inaccessible.
- Trace statistics to their original source. If Article A cites Article B, which cites a study with no link, the claim is unverifiable — cut it or use `tavily_search` to find the primary source.
- Competitor citations are acceptable when context is neutral — they signal objectivity
- Vendor sources must be explicitly disclosed: "According to Salesforce's customer research..." not "Research shows..."

## Citation Format

Make every reference traceable:

- **Name the study**: "Gartner's 2024 CMO Survey" not "Gartner research"
- **Include the year**: Always for statistics and research findings
- **Name the expert**: "Dr. Jane Smith, Stanford Professor" not "experts say"
- **Link when possible**: Primary source URL preferred
- **Disclose bias**: "According to our internal analysis..." or "Competitor X reports..."

In the markdown output, cite sources inline. When a URL is available, use hyperlinks: "According to [Gartner's 2024 CMO Survey](url), 73% of CMOs...". When no URL is available, use inline attribution: "According to Gartner's 2024 CMO Survey, 73% of CMOs...". Do not use footnotes or endnote-style references.

### Citation Density

Target 2-5 external citations per 1,000 words for substantive content. More is fine for data-heavy pieces. Fewer is acceptable for opinion-focused content where claims are clearly framed as perspective.

## When Citations Aren't Needed

- **Canonical facts**: "Water boils at 100C at sea level" — stable, textbook-level constants
- **Brand-owned data**: When citing proprietary data, provide methodology context: sample size, timeframe, and collection method. "Our survey of 500 customers" is credible; "our research shows" is vague.
- **Opinions clearly framed as such**: "We believe quality trumps quantity"
- **Common knowledge**: "The earth orbits the sun"

## Temporal Requirements

Source recency depends on topic pace:

| Topic Type  | Maximum Age         | Examples                                        |
| ----------- | ------------------- | ----------------------------------------------- |
| Fast-moving | 1-2 years           | AI, social media, tech trends                   |
| Industry    | 2-3 years           | Marketing benchmarks, business strategy         |
| Stable      | 5+ years acceptable | Accounting principles, programming fundamentals |

- "Recent" means within 1-2 years — not 2019
- Statistics from 5+ years ago need explicit context: "As of the 2019 survey..."
- Deprecated practices must not be recommended as current

## Hallucination Prevention

### Red Flags

- **Suspicious precision without source**: "67.3% of companies..." — precise numbers need attribution
- **Non-existent reports**: "According to the 2024 Global AI Adoption Index..." — verify the report exists
- **Unnamed experts**: "Industry experts agree..." — name them or cut the claim
- **Unverifiable case studies**: "TechCorp implemented this and saw 300% growth" — real companies need verifiable details, hypotheticals need labeling
- **Historical errors**: Check dates, sequences, and attributions — LLMs frequently misattribute inventions and discoveries

### Safe Patterns

- Rounded numbers with methodology: "Based on our analysis of 500 websites, roughly half..."
- Named sources with dates: "According to HubSpot's 2024 State of Marketing report, 73%..."
- Clearly labeled hypotheticals: "Imagine a B2B SaaS company launching a new feature..."
- Explicit opinions: "In our experience, this approach works best when..."

### Training Knowledge

When you recall a statistic but cannot name its specific source, use `tavily_search` to find the original. If the source can't be found: round the number and attribute it generally ("industry estimates suggest roughly half..."), or cut the statistic entirely. Never cite a precise number without a named source.

### Conflicting Sources

When credible sources disagree, present both: "Source A reports X, while Source B found Y." Don't silently pick one. Acknowledged disagreement builds trust.

When uncertain about a fact, verify it with `tavily_search`. If verification fails, generalize without a specific number, or cut the claim. An unverified number damages credibility more than a gap.
