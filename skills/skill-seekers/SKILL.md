---
name: skill-seekers
description: Automatically detect source types and build AI skills using Skill Seekers. Use when the user wants to create skills from documentation, repos, PDFs, videos, or other knowledge sources.
---

# Skill Seekers

You have access to the Skill Seekers MCP server which provides 35 tools for converting knowledge sources into AI-ready skills.

## When to Use This Skill

Use this skill when the user:
- Wants to create an AI skill from a documentation site, GitHub repo, PDF, video, or other source
- Needs to convert documentation into a format suitable for LLM consumption
- Wants to update or sync existing skills with their source documentation
- Needs to export skills to vector databases (Weaviate, Chroma, FAISS, Qdrant)
- Asks about scraping, converting, or packaging documentation for AI

## Source Type Detection

Automatically detect the source type from user input:

| Input Pattern | Source Type | Tool to Use |
|---------------|-------------|-------------|
| `https://...` (not GitHub/YouTube) | Documentation | `scrape_docs` |
| `owner/repo` or `github.com/...` | GitHub | `scrape_github` |
| `*.pdf` | PDF | `scrape_pdf` |
| YouTube/Vimeo URL or video file | Video | `scrape_video` |
| Local directory path | Codebase | `scrape_codebase` |
| `*.ipynb`, `*.html`, `*.yaml` (OpenAPI), `*.adoc`, `*.pptx`, `*.rss`, `*.1`-`.8` | Various | `scrape_generic` |
| JSON config file | Unified | Use config with `scrape_docs` |

## Recommended Workflow

1. **Detect source type** from the user's input
2. **Generate or fetch config** using `generate_config` or `fetch_config` if needed
3. **Estimate scope** with `estimate_pages` for documentation sites
4. **Scrape the source** using the appropriate scraping tool
5. **Enhance** with `enhance_skill` if the user wants AI-powered improvements
6. **Package** with `package_skill` for the target platform
7. **Export to vector DB** if requested using `export_to_*` tools

## Available MCP Tools

### Config Management
- `generate_config` — Generate a scraping config from a URL
- `list_configs` — List available preset configs
- `validate_config` — Validate a config file

### Scraping (use based on source type)
- `scrape_docs` — Documentation sites
- `scrape_github` — GitHub repositories
- `scrape_pdf` — PDF files
- `scrape_video` — Video transcripts
- `scrape_codebase` — Local code analysis
- `scrape_generic` — Jupyter, HTML, OpenAPI, AsciiDoc, PPTX, RSS, manpage, Confluence, Notion, chat

### Post-processing
- `enhance_skill` — AI-powered skill enhancement
- `package_skill` — Package for target platform
- `upload_skill` — Upload to platform API
- `install_skill` — End-to-end install workflow

### Advanced
- `detect_patterns` — Design pattern detection in code
- `extract_test_examples` — Extract usage examples from tests
- `build_how_to_guides` — Generate how-to guides from tests
- `split_config` — Split large configs into focused skills
- `export_to_weaviate`, `export_to_chroma`, `export_to_faiss`, `export_to_qdrant` — Vector DB export

## Key Tool Parameters

### `scrape_docs`
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | ✅ | Root URL of the documentation site |
| `output_path` | string | ❌ | Output directory for scraped content |
| `config_path` | string | ❌ | Path to JSON config file |
| `max_depth` | number | ❌ | Max crawl depth (default: 3) |
| `max_pages` | number | ❌ | Max pages to scrape (default: 100) |

### `scrape_github`
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_url` | string | ✅ | GitHub repository URL or `owner/repo` |
| `branch` | string | ❌ | Branch to scrape (default: main) |
| `include_patterns` | string[] | ❌ | Glob patterns for files to include |
| `exclude_patterns` | string[] | ❌ | Glob patterns for files to exclude |
| `max_file_size` | number | ❌ | Max file size in bytes (default: 100KB) |

### `scrape_pdf`
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | ✅ | Path to PDF file |
| `pages` | string | ❌ | Page range (e.g., "1-10,15,20-30") |
| `extract_tables` | boolean | ❌ | Extract tables as structured data (default: false) |

### `enhance_skill`
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `skill_path` | string | ✅ | Path to the skill file to enhance |
| `focus_areas` | string[] | ❌ | Areas to improve: structure, examples, edge_cases, completeness |
| `target_platform` | string | ❌ | Target: claude, opencode, cursor (default: claude) |

### `package_skill`
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `skill_path` | string | ✅ | Path to the skill file |
| `format` | string | ✅ | Output format: markdown, json, yaml |
| `include_metadata` | boolean | ❌ | Include frontmatter metadata (default: true) |

### `generate_config`
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | ✅ | URL to generate config for |
| `preset` | string | ❌ | Config preset: minimal, standard, comprehensive |
| `output_path` | string | ❌ | Where to save the config file |

## Error Handling

- **Large sites**: Use `estimate_pages` first, then set `max_pages` to control scope
- **Rate limiting**: Config file supports `delay_ms` between requests
- **Authentication**: Use config file for sites requiring login (set `headers` or `cookies`)
- **Broken links**: Set `continue_on_error: true` in config to skip failures
