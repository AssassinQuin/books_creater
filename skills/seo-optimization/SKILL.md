---
name: seo-optimization
description: |
  SEO content optimization based on the Periodic Table of SEO Elements.
  Use when writing or reviewing content for search performance. Covers
  on-page factors, E-E-A-T signals, semantic SEO, and GEO optimization.
---

# SEO Content Optimization Skill

This skill codifies SEO best practices for content writers and AI agents. It is based on the **Periodic Table of SEO Elements** (Search Engine Land, 7th Edition, 2024) and current research on content optimization, E-E-A-T, and Generative Engine Optimization (GEO).

**Scope**: Content-level optimization only. This skill does not cover server configuration, crawl budget management, or infrastructure concerns.

---

## How to Use This Skill

This skill supplements your existing writing instructions with SEO-specific knowledge. When writing or reviewing content:

1. **Keyword placement**: Use the Keyword Placement Map (Section 2.4) to verify keywords appear in all required positions
2. **E-E-A-T compliance**: Use Section 3 to verify the content demonstrates experience, expertise, authoritativeness, and trust
3. **Semantic SEO**: Use Section 4 to ensure topic coverage, entity clarity, and internal linking
4. **GEO readiness**: Use Section 5 to ensure content is optimized for AI extraction and citation
5. **Schema markup**: Use Section 6 to select and implement the correct schema type
6. **Pre-publish verification**: Run through the GEO readiness checklist in Section 7 before finalizing

**Precedence**: If this skill conflicts with your system prompt, brand voice instructions, or the content guidelines document, those take precedence. This skill adds SEO knowledge; it does not override existing quality rules.

**Priority levels**: Items marked **[Must]** are required for every piece of content. Items marked **[Should]** improve SEO performance but can be skipped under time or context constraints. Items marked **[Context]** are background knowledge that inform decisions but require no direct action.

---

## Table of Contents

1. [Periodic Table of SEO Elements](#1-periodic-table-of-seo-elements) — Reference framework (context)
2. [On-Page Content Optimization](#2-on-page-content-optimization) — Keyword placement and structure
3. [E-E-A-T Signals](#3-e-e-a-t-signals) — Credibility and trust signals
4. [Semantic SEO and Topic Architecture](#4-semantic-seo-and-topic-architecture) — Entity and cluster strategy
5. [GEO: Generative Engine Optimization](#5-geo-generative-engine-optimization) — AI search optimization
6. [Schema Markup for Content](#6-schema-markup-for-content) — Structured data implementation
7. [Content Freshness](#7-content-freshness) — Keeping content current
8. [AI-Generated Content Guidelines](#8-ai-generated-content-guidelines) — Using AI tools responsibly
9. [Pre-Publish Checklist](#9-pre-publish-checklist) — Final verification

---

## 1. Periodic Table of SEO Elements

The Periodic Table of SEO Elements organizes 44 foundational elements into 7 categories. The 2024 edition removed the Niches and Toxins groups, renamed HTML to "Code" and Reputation to "Credibility," and added a new "Performance" group.

The philosophy: no element has a publicly known weight. Quality content is the foundation, and every other element reinforces it.

Elements below are tagged with priority levels:

- **[Must]** — Required for every piece. Verify before publishing.
- **[Should]** — Improves SEO. Skip only under constraints.
- **[Context]** — Background knowledge. No direct action required from the writer.

### 1.1 Content Elements

These are the elements you directly control when writing.

| Element | Name       | Priority      | What to Do                                                                                                                                                                                                                                                                                                                                                                              |
| ------- | ---------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ck**  | Keywords   | **[Must]**    | Place the primary keyword in the title, H1, first 100 words, and URL. See the Keyword Placement Map (Section 2.4) for full requirements.                                                                                                                                                                                                                                                |
| **Ca**  | Answers    | **[Must]**    | Open each section with a direct answer to the heading's question, then elaborate. Structure for featured snippet extraction (paragraph, list, or table). Avoid preamble ("There are many factors...", "Before we dive in...", "It depends..."). Example — Good: "Most SEO efforts show measurable results in 4-6 months." Bad: "SEO is a complex process that depends on many factors." |
| **Cu**  | Accuracy   | **[Must]**    | Cite primary sources for all statistics and claims. Link to authoritative references. Never fabricate data.                                                                                                                                                                                                                                                                             |
| **Cr**  | Relevance  | **[Must]**    | Match content format and depth to search intent (informational, navigational, transactional, commercial).                                                                                                                                                                                                                                                                               |
| **Cd**  | Depth      | **[Should]**  | For each H2 section, cover: (1) what the subtopic is, (2) why it matters, (3) how to apply it, (4) common mistakes or edge cases. If a heading promises depth, deliver it.                                                                                                                                                                                                              |
| **Cf**  | Freshness  | **[Should]**  | Reference current year for statistics. Include `datePublished` and `dateModified` in schema. Cite sources from within the last 1-2 years for fast-moving topics.                                                                                                                                                                                                                        |
| **Cm**  | Multimedia | **[Should]**  | Include relevant images or diagrams. Every image needs descriptive alt text that includes keywords where natural.                                                                                                                                                                                                                                                                       |
| **Cq**  | Quality    | **[Context]** | Covered by your existing writing instructions. No additional action needed from this skill.                                                                                                                                                                                                                                                                                             |
| **Ce**  | Engagement | **[Context]** | Covered by your existing writing instructions (answer-first, scannable formatting, CTAs).                                                                                                                                                                                                                                                                                               |

### 1.2 Architecture Elements

Most architecture elements are handled by engineering, not the content writer. The writer-relevant items:

| Element                | Name             | Priority      | What to Do                                                                                                                               |
| ---------------------- | ---------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Au**                 | URLs             | **[Must]**    | Use short, keyword-rich URL slugs with hyphens. No parameters, IDs, or unnecessary nesting.                                              |
| **Am**                 | Mobile           | **[Should]**  | Use short paragraphs, clear headings. Avoid wide tables or fixed-width elements.                                                         |
| **Ad**                 | Duplicate        | **[Should]**  | Set a self-referencing canonical tag. Do not publish substantially similar content across multiple URLs.                                 |
| **Ac, Ah, Aj, As, Ax** | (Infrastructure) | **[Context]** | Crawlability, HTTPS, JavaScript rendering, site structure, and sitemaps are engineering concerns. Not directly actionable by the writer. |

### 1.3 Code Elements

HTML/markup signals the writer directly controls.

| Element    | Name                 | Priority     | What to Do                                                                                                                                              |
| ---------- | -------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Hh**     | Headings             | **[Must]**   | One H1 per page with primary keyword. H2s for major sections, H3s for subsections. Sequential hierarchy (no skipping levels). See Section 2.3.          |
| **Hi**     | Image Alt            | **[Must]**   | Every content image needs descriptive alt text. Include keywords where natural. Do not stuff keywords.                                                  |
| **Hs**     | Schema               | **[Must]**   | Implement Article + BreadcrumbList schema at minimum. Add FAQ or HowTo schema when the content format warrants it. See Section 6.                       |
| **Ht, Hd** | Titles, Descriptions | **[Must]**   | Defer to your system prompt's title and meta description rules. This skill's guidance in Section 2.1-2.2 supplements with SEO-specific formatting tips. |
| **Hc**     | Canonical            | **[Should]** | Self-referencing canonical on every page.                                                                                                               |

### 1.4 Credibility Elements

Credibility maps to Google's E-E-A-T framework. See Section 3 for detailed implementation.

| Element | Name              | Priority      | What to Do                                                                                                                    |
| ------- | ----------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Re**  | Experience        | **[Must]**    | Include first-person observations, test results, or case studies. Show the author has done/used/tested what they write about. |
| **Rx**  | Expertise         | **[Must]**    | Include author bio with relevant credentials. Cover nuances and edge cases only an expert would know.                         |
| **Rt**  | Trust             | **[Must]**    | Cite sources for all claims. Be transparent about content creation methodology.                                               |
| **Ra**  | Authoritativeness | **[Context]** | Recognition as a trusted source is built over time through sustained coverage. Not actionable on a single piece.              |
| **Rb**  | Brand             | **[Context]** | Brand reputation is a marketing concern, not a per-article concern.                                                           |
| **Rh**  | History           | **[Context]** | Publishing track record is built over time. Not actionable on a single piece.                                                 |

### 1.5 Links Elements

| Element    | Name               | Priority      | What to Do                                                                                                     |
| ---------- | ------------------ | ------------- | -------------------------------------------------------------------------------------------------------------- |
| **Li**     | Internal           | **[Must]**    | Every new page links out to 2-3 related pages. Use descriptive, keyword-relevant anchor text. See Section 4.3. |
| **La**     | Anchors            | **[Must]**    | Use descriptive anchor text for all links. Never use "click here" or bare URLs.                                |
| **Lr**     | Relevance          | **[Should]**  | Link to topically related content within the same topic cluster.                                               |
| **Ls**     | Sponsored          | **[Should]**  | Mark sponsored links with `rel="sponsored"`, user-generated with `rel="ugc"`.                                  |
| **Lq, Ld** | Quality, Diversity | **[Context]** | Inbound link quality and diversity are earned through content quality, not controlled per-article.             |

### 1.6 User Elements

| Element            | Name           | Priority      | What to Do                                                                                                         |
| ------------------ | -------------- | ------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Ui**             | Intent         | **[Must]**    | Match content format and depth to the search intent type (informational, navigational, transactional, commercial). |
| **Ub**             | Behavior       | **[Should]**  | Deliver on the title's promise in the first paragraph. Structure for scannability.                                 |
| **Uc, Ul, Up, Ux** | (User context) | **[Context]** | Localization, personalization, and UX design are handled by the platform, not the writer.                          |

### 1.7 Performance Elements

| Element                                                  | Priority      | What to Do                                                                                                              |
| -------------------------------------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Ps, Pr, Pv** (Speed, Responsiveness, Visual Stability) | **[Context]** | Core Web Vitals are engineering concerns. Writer's only contribution: optimize image file sizes and specify dimensions. |

---

## 2. On-Page Content Optimization

### 2.1 Title Tag Rules

| Rule               | Details                                                                                      |
| ------------------ | -------------------------------------------------------------------------------------------- |
| Length             | 50-60 characters (Google truncates longer titles)                                            |
| Keyword placement  | Front-load the primary keyword                                                               |
| Uniqueness         | Every page must have a unique title                                                          |
| Format             | `Primary Keyword - Secondary Context \| Brand` or `Primary Keyword: Descriptive Phrase`      |
| Click optimization | Titles with numbers, "how to," and power words ("complete," "guide," "best") earn higher CTR |

**Example**: `Content SEO Checklist: 15 Steps to Rank Higher in 2026 | Yolando`

### 2.2 Meta Description Rules

| Rule    | Details                                                                |
| ------- | ---------------------------------------------------------------------- |
| Length  | 150-160 characters                                                     |
| Content | Value proposition, not a summary. Tell the reader what they will gain. |
| Keyword | Include the primary keyword naturally (Google bolds matching terms)    |
| CTA     | End with an implicit or explicit call to action                        |

**Example**: `Master on-page SEO with this actionable checklist. Covers title tags, heading structure, E-E-A-T signals, and content freshness. Start ranking higher today.`

### 2.3 Heading Structure

```text
H1: Primary keyword + topic framing (one per page)
  H2: Major section headings (include secondary keywords)
    H3: Subsection headings (include related terms / long-tail variations)
      H4: Detail-level headings (use sparingly)
```

Rules:

- One H1 per page, always containing the primary keyword
- H2s should cover the main subtopics a searcher expects to find
- Use question-format H2s/H3s to target "People Also Ask" and featured snippets
- Heading hierarchy must be sequential (do not skip from H2 to H4)
- At least 3-5 H2 sections for substantial content

### 2.4 Keyword Placement Map

| Location                  | Primary Keyword | Secondary Keywords | Semantic/Related Terms |
| ------------------------- | :-------------: | :----------------: | :--------------------: |
| Title tag                 |    Required     |      Optional      |           --           |
| Meta description          |    Required     |         --         |           --           |
| URL slug                  |    Required     |         --         |           --           |
| H1                        |    Required     |         --         |           --           |
| First 100 words           |    Required     |         --         |           --           |
| H2 headings               |    1-2 times    |   Natural usage    |     Natural usage      |
| H3 headings               |       --        |   Natural usage    |     Natural usage      |
| Body text                 |  1-2% density   |     Throughout     |       Throughout       |
| Image alt text            |     1 image     |    Other images    |           --           |
| Internal link anchor text |  When relevant  |   When relevant    |           --           |

### 2.5 Content Length Guidelines

There is no ideal word count. Length should match intent:

| Content Type              | Typical Range     | Guidance                                                      |
| ------------------------- | ----------------- | ------------------------------------------------------------- |
| Quick answer / definition | 300-800 words     | Get to the point. Answer the question in the first paragraph. |
| Blog post / article       | 1,000-2,000 words | Cover the topic thoroughly but concisely.                     |
| Comprehensive guide       | 2,000-4,000 words | Be the definitive resource. Include a table of contents.      |
| Pillar page               | 2,500-5,000 words | Broad coverage with links to cluster pages for depth.         |

The rule: cover the topic completely, then stop. Every sentence should earn its place.

---

## 3. E-E-A-T Signals

E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) is the framework Google's quality raters use to evaluate content. After the December 2025 core update, E-E-A-T requirements extend beyond YMYL (Your Money or Your Life) topics to virtually all competitive queries.

### 3.1 Experience Signals

Show that the author has first-hand, real-world experience with the subject.

| Signal                | How to Implement                                                                   |
| --------------------- | ---------------------------------------------------------------------------------- |
| First-person accounts | "When I tested this approach with 50 clients..."                                   |
| Original media        | Include original photos, screenshots, or recordings from actual experience         |
| Specific details      | Reference particular tools, versions, dates, and outcomes from personal experience |
| Process documentation | Walk through what you actually did, including mistakes and workarounds             |
| Case studies          | Present real results with real numbers (anonymized if necessary)                   |

### 3.2 Expertise Signals

Demonstrate subject-matter knowledge that goes beyond surface-level understanding.

| Signal               | How to Implement                                                                       |
| -------------------- | -------------------------------------------------------------------------------------- |
| Author bio           | Include a detailed author bio with relevant credentials, certifications, or experience |
| Author page          | Link to a dedicated author page that aggregates the author's body of work              |
| Technical depth      | Cover nuances, edge cases, and trade-offs that only an expert would know               |
| Accurate terminology | Use correct domain-specific language (but explain jargon for the audience)             |
| Counter-arguments    | Address common misconceptions and alternative viewpoints                               |
| Methodology          | Explain how conclusions were reached, not just what they are                           |

### 3.3 Authoritativeness Signals

Establish the content source as a recognized authority on the topic.

| Signal              | How to Implement                                                                                   |
| ------------------- | -------------------------------------------------------------------------------------------------- |
| Topical depth       | Publish multiple related pieces that demonstrate sustained coverage of a topic                     |
| External citations  | Cite and link to authoritative sources (academic papers, official documentation, industry leaders) |
| Earn citations      | Create original research, data, or frameworks that others want to reference                        |
| Brand consistency   | Maintain consistent messaging and positioning across all content                                   |
| Contributor network | Feature guest experts or include expert quotes with proper attribution                             |

### 3.4 Trustworthiness Signals

Trust is the foundation of E-E-A-T. Without trust, the other signals carry less weight.

| Signal              | How to Implement                                                                            |
| ------------------- | ------------------------------------------------------------------------------------------- |
| Source attribution  | Cite all statistics, claims, and data with links to primary sources                         |
| Transparency        | Disclose author identity, content creation methodology, and potential conflicts of interest |
| Accuracy            | Fact-check everything. Correct errors promptly. Note corrections publicly.                  |
| Contact information | Provide clear contact information and organizational details                                |
| Editorial standards | Publish and follow an editorial policy. Include a review/fact-check process.                |
| Content dating      | Show publication and last-updated dates prominently                                         |
| AI transparency     | If AI was used in content creation, disclose this in sensitive/YMYL topics                  |

---

## 4. Semantic SEO and Topic Architecture

### 4.1 Topic Clusters

Modern SEO ranks topic ecosystems, not individual pages. Structure content in clusters:

```text
                    +-------------------+
                    |   Pillar Page     |
                    |  (Broad Topic)    |
                    +--------+----------+
              +--------------+--------------+
              v              v              v
       +-----------+  +-----------+  +-----------+
       | Cluster   |  | Cluster   |  | Cluster   |
       | Page A    |  | Page B    |  | Page C    |
       +-----------+  +-----------+  +-----------+
```

**Pillar page**: 2,500-5,000 words covering a broad topic from multiple perspectives. Links to all cluster pages.

**Cluster pages**: 1,000-2,500 words each, diving deep into a specific subtopic. Each links back to the pillar page and cross-links to 1-3 related cluster pages.

### 4.2 Entity-Based Optimization

Search engines now understand topics through entities (people, places, concepts, organizations) rather than just keywords.

Rules for entity optimization:

- Identify the core entities in your content (e.g., for "SEO content optimization": Google, E-E-A-T, schema markup, Core Web Vitals)
- Define entities clearly on first mention
- Use consistent terminology for the same entity throughout
- Connect entities through relationship language ("X is a type of Y," "X is used by Y")
- Cover the entity's attributes and relationships comprehensively

### 4.3 Internal Linking Strategy

| Rule                    | Details                                                                                                    |
| ----------------------- | ---------------------------------------------------------------------------------------------------------- |
| New content             | Every new page must receive 2-5 internal links from existing relevant pages within one week of publication |
| Outbound internal links | Every new page should link to 2-3 existing related pages                                                   |
| Anchor text             | Use descriptive, keyword-rich anchor text. Vary the anchor text across different linking pages.            |
| Contextual placement    | Links should appear naturally within paragraph text, not in isolated "Related articles" sections           |
| Pillar links            | Every cluster page links back to its pillar page. The pillar page links to every cluster page.             |
| Cross-cluster links     | 1-3 horizontal links between related cluster pages                                                         |
| Depth limit             | Key content should be reachable within 3 clicks from the homepage                                          |
| Audit frequency         | Review and update internal links quarterly                                                                 |

### 4.4 Semantic Keyword Expansion

Beyond the primary keyword, content should naturally incorporate:

| Type                     | Description                        | Example (for "SEO content optimization")                 |
| ------------------------ | ---------------------------------- | -------------------------------------------------------- |
| **LSI terms**            | Semantically related terms         | search engine ranking, organic traffic, content strategy |
| **Long-tail variations** | Specific phrasings of the topic    | "how to optimize blog posts for SEO in 2026"             |
| **Question keywords**    | Questions searchers ask            | "what makes content rank on Google?"                     |
| **Entity-related terms** | Terms associated with key entities | E-E-A-T, Core Web Vitals, featured snippets              |
| **Action terms**         | Verbs associated with the topic    | optimize, improve, audit, analyze, implement             |

---

## 5. GEO: Generative Engine Optimization

GEO (Generative Engine Optimization) is the practice of optimizing content for visibility in AI-powered search experiences, including Google AI Overviews, ChatGPT Search, Perplexity, and other LLM-based systems.

### 5.1 Why GEO Matters

- Zero-click searches reached 60% in 2025 (77% on mobile)
- When an AI Overview appears, the #1 traditional result loses 34.5% of its clicks
- AI systems synthesize answers from multiple sources -- they do not simply select the top-ranked page
- Citations in AI Overviews often come from pages that do not rank #1

### 5.2 GEO Optimization Rules

| Strategy                          | How to Implement                                                                 | Why It Works                                                                                             |
| --------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Include verifiable statistics** | Add specific numbers, percentages, and data points with source attribution       | AI systems prefer claims they can verify; statistics with sources are highly citable                     |
| **Use authoritative citations**   | Link to academic papers, official documentation, and recognized industry sources | LLMs grounded in knowledge graphs with citations achieve 300% higher accuracy                            |
| **Structure for extraction**      | Use clear headings, definition lists, tables, and concise paragraphs             | AI systems parse structured content more accurately than long prose                                      |
| **Answer questions directly**     | Open sections with a concise answer, then elaborate                              | AI Overviews extract direct answers from the clearest source                                             |
| **Claim specificity**             | Replace vague statements with specific, verifiable claims                        | "Conversion rates increased 23% over 6 months" vs. "Conversion rates improved significantly"             |
| **Publish original research**     | Create "State of X" reports, benchmark data, surveys, case studies               | Brands producing original research appear in AI citations 10x more than those publishing generic content |
| **Define entities clearly**       | When introducing a concept, provide a clear one-sentence definition              | AI systems use these definitions when synthesizing answers                                               |
| **Build topical authority**       | Publish comprehensive coverage across a topic cluster                            | AI systems prefer citing sources that demonstrate sustained, deep coverage                               |

### 5.3 Content Formatting for AI Extraction

AI systems extract information most reliably from these formats:

| Format                   | Best For               | Example                                                                                                                   |
| ------------------------ | ---------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Definition paragraph** | Concept definitions    | "E-E-A-T stands for Experience, Expertise, Authoritativeness, and Trustworthiness. It is the framework Google uses to..." |
| **Numbered lists**       | Step-by-step processes | "To optimize a title tag: 1. Start with the primary keyword. 2. Keep under 60 characters..."                              |
| **Tables**               | Comparisons and data   | Feature comparison tables, pricing tables, specification tables                                                           |
| **FAQ format**           | Direct Q&A             | `<h3>What is GEO?</h3>` followed by a concise, self-contained answer                                                      |
| **Bold key phrases**     | Key takeaways          | "The most important finding: **pages with structured data receive 20-30% more clicks**"                                   |

### 5.4 Measuring GEO Success

| Metric                    | Description                                                                |
| ------------------------- | -------------------------------------------------------------------------- |
| **Share of Model (SoM)**  | How often your brand appears in AI-generated responses vs. competitors     |
| **AI citation frequency** | Number of times your content is cited in AI Overviews, ChatGPT, Perplexity |
| **Source attribution**    | Whether AI systems name your brand when using your information             |
| **Zero-click visibility** | Presence in AI Overviews and featured snippets                             |

---

## 6. Schema Markup for Content

Schema markup (structured data) helps search engines understand content type, authorship, and relationships. It enables rich results and improves AI comprehension of your content.

### 6.1 Content-Relevant Schema Types

| Schema Type        | When to Use                           | Key Properties                                                                |
| ------------------ | ------------------------------------- | ----------------------------------------------------------------------------- |
| **Article**        | Blog posts, news articles, guides     | `headline`, `author`, `datePublished`, `dateModified`, `image`, `description` |
| **FAQPage**        | Pages with frequently asked questions | `mainEntity` array of `Question` + `acceptedAnswer` pairs                     |
| **HowTo**          | Step-by-step tutorials and guides     | `name`, `step` array with `name`, `text`, `image`                             |
| **BreadcrumbList** | All content pages                     | `itemListElement` array showing page hierarchy                                |
| **Person**         | Author pages                          | `name`, `jobTitle`, `url`, `sameAs` (link to social profiles)                 |
| **Organization**   | About pages, site-wide                | `name`, `url`, `logo`, `sameAs`                                               |
| **WebPage**        | All pages (general)                   | `name`, `description`, `datePublished`, `dateModified`                        |

### 6.2 Schema Implementation Rules

- Use JSON-LD format (Google's preferred format)
- Every content page should have at minimum: `Article` + `BreadcrumbList` schema
- Author information in Article schema should reference a `Person` entity
- Include `datePublished` and `dateModified` -- these are critical freshness signals
- Test all schema with Google's Rich Results Test before publishing
- Do not mark up content that is not visible on the page (schema must reflect actual content)

### 6.3 Example: Article Schema

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "SEO Content Optimization: The Complete Guide",
  "author": {
    "@type": "Person",
    "name": "Jane Smith",
    "url": "https://example.com/authors/jane-smith",
    "jobTitle": "Head of Content Strategy"
  },
  "datePublished": "2026-01-15",
  "dateModified": "2026-02-01",
  "image": "https://example.com/images/seo-guide-hero.webp",
  "description": "A comprehensive guide to optimizing content for search engines and AI systems.",
  "publisher": {
    "@type": "Organization",
    "name": "Example Brand",
    "logo": {
      "@type": "ImageObject",
      "url": "https://example.com/logo.png"
    }
  }
}
```

---

## 7. Content Freshness

### 7.1 Freshness Signals

Google uses multiple signals to assess content freshness:

| Signal                 | What It Measures                                               |
| ---------------------- | -------------------------------------------------------------- |
| Publication date       | When the content was first published                           |
| Modification date      | When the content was last substantively updated                |
| Content changes        | Whether the actual content has changed (not just the date)     |
| New backlinks          | Rate of new links pointing to the content                      |
| Social mentions        | Recent social media activity around the content                |
| Query freshness demand | Whether the search query implies a need for recent information |

### 7.2 Freshness Strategy

| Action                      | Frequency       | Details                                                              |
| --------------------------- | --------------- | -------------------------------------------------------------------- |
| **Publish new content**     | Ongoing         | Maintain a consistent publishing cadence                             |
| **Update existing content** | Quarterly       | Refresh statistics, add new developments, fix broken links           |
| **Content audit**           | Twice yearly    | Identify stale pages to update, consolidate, or remove               |
| **Date management**         | On every update | Only update the "last modified" date when making substantive changes |
| **Ratio**                   | 3:1             | For every 3 new pieces, thoroughly update 1 existing piece           |

### 7.3 What Counts as a Substantive Update

Search engines distinguish between cosmetic changes and real updates:

| Substantive (do update the date)                  | Cosmetic (do not update the date)          |
| ------------------------------------------------- | ------------------------------------------ |
| Adding new sections or paragraphs                 | Fixing typos                               |
| Updating statistics with current data             | Reformatting text                          |
| Adding new examples or case studies               | Changing images without adding information |
| Revising recommendations based on new information | Adding internal links                      |
| Adding new research or source citations           | Minor wording changes                      |

---

## 8. AI-Generated Content Guidelines

### 8.1 Google's Position

Google does not penalize content for being AI-generated. The focus is on content quality and usefulness, regardless of creation method. However, the December 2025 core update is the first to explicitly evaluate AI content authenticity.

### 8.2 Rules for AI-Generated Content That Ranks

| Rule                                  | Details                                                                                                                        |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Add human expertise**               | AI-generated drafts must be enhanced with original insights, personal experience, and expert knowledge                         |
| **Fact-check everything**             | Verify all statistics, claims, and recommendations. AI models hallucinate.                                                     |
| **Include original elements**         | Add original data, screenshots, case studies, or quotes that AI could not generate                                             |
| **Demonstrate experience**            | Include first-person observations, test results, and real-world application details                                            |
| **Avoid generic content**             | If the content could have been written by anyone for anyone, it will not rank. Add specific, contextual value.                 |
| **Edit for voice and style**          | Ensure content matches the brand voice and does not read like generic AI output                                                |
| **Disclose when required**            | For YMYL content (health, finance, legal), disclose AI involvement in creation                                                 |
| **Do not publish unedited AI output** | Content rated as "all or almost all AI-generated lacking effort, originality, and added value" receives Google's Lowest rating |

### 8.3 Quality Differentiation

What separates high-quality AI-assisted content from low-quality AI spam:

| High Quality                                  | Low Quality                               |
| --------------------------------------------- | ----------------------------------------- |
| AI draft + expert editing + original insights | Published raw AI output                   |
| Verified facts with cited sources             | Unverified claims                         |
| Original data, media, or perspectives         | Rehashed information available everywhere |
| Clear author with relevant credentials        | No attribution                            |
| Matches specific search intent precisely      | Covers topic generically                  |
| Updated with current information              | Static, date-unaware content              |
| Structured for both humans and search engines | Unstructured wall of text                 |

---

## 9. Pre-Publish Checklist

Run through this checklist before publishing any content piece.

### Title and Meta

- [ ] Title tag is 50-60 characters
- [ ] Title contains the primary keyword, front-loaded
- [ ] Title is unique (not used on any other page)
- [ ] Meta description is 150-160 characters
- [ ] Meta description includes the primary keyword
- [ ] Meta description is a value proposition, not a summary

### URL

- [ ] URL slug contains the primary keyword
- [ ] URL is short, descriptive, and uses hyphens
- [ ] URL does not contain parameters, IDs, or unnecessary nesting

### Headings

- [ ] One H1 per page containing the primary keyword
- [ ] H2s cover the major subtopics searchers expect
- [ ] H3s include secondary keywords or long-tail variations
- [ ] Heading hierarchy is sequential (no skipped levels)
- [ ] At least one heading is in question format (for featured snippets)

### Content Quality

- [ ] Content directly addresses the search intent for the target keyword
- [ ] Primary keyword appears in the first 100 words
- [ ] Keyword density is 1-2% (not over-optimized)
- [ ] Secondary and semantic keywords are used naturally throughout
- [ ] Content is comprehensive -- no major subtopic is missing
- [ ] All facts, statistics, and claims are verified and sourced
- [ ] Content includes original insights, data, or perspectives
- [ ] No filler paragraphs -- every sentence adds value

### E-E-A-T

- [ ] Author is identified with name and credentials
- [ ] Author bio is included or linked
- [ ] First-hand experience is demonstrated where applicable
- [ ] Sources are cited with links to primary references
- [ ] Publication date and last-updated date are displayed
- [ ] Content creation methodology is transparent (especially for YMYL topics)

### Media and Formatting

- [ ] All images have descriptive alt text
- [ ] Images are optimized for web (WebP/AVIF, compressed, dimensions specified)
- [ ] Content includes at least one relevant image, diagram, or visual
- [ ] Content is formatted for scannability (short paragraphs, bullet points, tables)
- [ ] Mobile rendering has been checked

### Internal Linking

- [ ] Content links to 2-3 relevant existing pages
- [ ] 2-5 existing pages have been updated to link to this new content
- [ ] Anchor text is descriptive and keyword-relevant
- [ ] If part of a topic cluster: links back to pillar page

### Schema and Technical

- [ ] Article schema is implemented with correct `headline`, `author`, `datePublished`, `dateModified`
- [ ] BreadcrumbList schema is present
- [ ] FAQ or HowTo schema is added (if the content format warrants it)
- [ ] Canonical tag is set (self-referencing)
- [ ] Page is accessible (not blocked by robots.txt or noindex)

### GEO Readiness

- [ ] Key definitions are stated clearly in self-contained sentences
- [ ] Statistics include specific numbers with source attribution
- [ ] Content is structured for AI extraction (tables, lists, definition paragraphs)
- [ ] Questions are answered directly before elaboration
- [ ] At least one piece of original data, research, or insight is included

---

## References

- [The 2024 Periodic Table of SEO Elements](https://searchengineland.com/seotable) -- Search Engine Land
- [SEO Guide: Content & Search Engine Success Factors](https://searchengineland.com/guide/seo/content-search-engine-ranking) -- Search Engine Land
- [Google's guidance about AI-generated content](https://developers.google.com/search/blog/2023/02/google-search-and-ai-content) -- Google Search Central
- [What is GEO (Generative Engine Optimization)?](https://searchengineland.com/guide/what-is-geo) -- Search Engine Land
- [E-E-A-T for Google: How to Win SEO Rankings in 2026](https://weventure.de/en/blog/e-e-a-t) -- weventure
- [E-E-A-T Standards in 2026](https://chapters-eg.com/blog/seo-blog/guide-to-e-e-a-t-standards-in-2026/) -- Chapters
- [Schema Markup Guide](https://backlinko.com/schema-markup-guide) -- Backlinko
- [Google December 2025 Core Update](https://thatware.co/google-december-2025-core-update/) -- ThatWare
- [Content SEO in 2026](https://neuronwriter.com/content-seo-in-2026-what-you-need-to-know-about-googles-algorithms/) -- NEURONwriter
- [GEO Guide 2026](https://www.digitalapplied.com/blog/geo-guide-generative-engine-optimization-2026) -- Digital Applied
- [Internal Linking Strategy Guide 2026](https://www.ideamagix.com/blog/internal-linking-strategy-seo-guide-2026/) -- IdeaMagix
- [Semantic SEO Guide 2026](https://niumatrix.com/semantic-seo-guide/) -- NiuMatrix
- [Fresh Content and Google Rankings](https://ahrefs.com/blog/fresh-content/) -- Ahrefs
