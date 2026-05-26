# Topical Map MCP

A complete MCP (Model Context Protocol) server for **Holistic pSEO 2026** — based on Koray Tuğberk GÜBÜR's semantic SEO framework. 18 tools that chain with Claude Desktop and any SEO data source.

---

## The Big Idea — Connect Any SEO Tool to Claude

This repo demonstrates a pattern: **any SEO tool can be added as a custom MCP server in Claude Desktop**, and they all work together automatically with Claude as the orchestrator.

```
SE Ranking MCP   ──┐
Ahrefs MCP       ──┤
SEMrush MCP      ──┼──→  Claude (orchestrator)  ──→  You
GSC MCP          ──┤
topical-map MCP  ──┘
```

Claude sits in the middle. You just tell Claude what you want in plain English — it decides which tool to call, chains the results, and hands you the output. You never have to think about which MCP does what.

### Why this matters

Without MCP:
> You → export CSV from SE Ranking → paste into ChatGPT → copy output → paste into another tool → repeat 10 times

With MCP:
> You → tell Claude once → Claude chains everything automatically

---

## How to Add Any SEO Tool as a Custom MCP

Every MCP server follows the same pattern in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "your-tool-name": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/mcp/folder",
        "run",
        "server.py"
      ]
    }
  }
}
```

You can stack as many as you want — they all run simultaneously and Claude picks the right one based on your request.

### Config file location
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

### Real example with multiple tools connected

```json
{
  "mcpServers": {
    "topical-map": {
      "command": "uv",
      "args": ["--directory", "F:\\MCP\\topical-map-mcp", "run", "server.py"]
    },
    "se-ranking": {
      "command": "uv",
      "args": ["--directory", "F:\\MCP\\se-ranking-mcp", "run", "server.py"]
    },
    "google-search-console": {
      "command": "C:\\Users\\HP\\.local\\bin\\uvx.exe",
      "args": ["mcp-search-console"]
    },
    "google-tag-manager": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://gtm-mcp.stape.ai/mcp"]
    }
  }
}
```

After saving, fully quit Claude Desktop and reopen — all tools appear automatically. No manual steps each time.

### Rules for adding a new MCP
1. The MCP folder must have a `server.py` (or equivalent entry point) and `pyproject.toml`
2. Run `uv sync` inside the folder once to install dependencies
3. Add the entry to `claude_desktop_config.json`
4. Quit and restart Claude Desktop — done

---

## This Repo — Topical Map MCP (18 Tools)

### Topical Map & Clustering
| Tool | Description |
|------|-------------|
| `cluster_keywords` | Semantic clustering using BGE embeddings (local, free) |
| `build_topical_map` | Koray's 8 corner nodes + 3-tier page hierarchy |
| `suggest_8_corner_nodes` | Generate skeleton without keyword data (kick-off planning) |

### Content Briefs
| Tool | Description |
|------|-------------|
| `generate_content_brief` | Full brief with H2s, EAV table, quality gate minimums |

### Koray's Scoring Formulas
| Tool | Formula |
|------|---------|
| `classify_keyword_intent` | Formula 6 — Transactional=10, Commercial=7, Informational=3, Navigational=1 |
| `score_topical_coverage` | Embeddings-based gap analysis |
| `score_topical_authority` | Formula 1 — Coverage × History ÷ Retrieval Cost |
| `score_ai_citation_potential` | Formula 5 — 9+ structured facts = ~78% AI coverage |
| `score_kbt_trust` | Formula 7 — Knowledge-Based Trust |

### Entity & Knowledge Graph
| Tool | Description |
|------|-------------|
| `validate_entity_wikidata` | Wikidata lookup with local SQLite cache |
| `build_eav_table` | 6 mandatory + 2 optional + 2 enhancing attributes |

### Schema Markup
| Tool | Description |
|------|-------------|
| `generate_schema_markup` | JSON-LD stack — Article + BreadcrumbList + FAQPage |

### Quality Gate
| Tool | Description |
|------|-------------|
| `apply_quality_gate` | Koray's 65-point pre-publish checklist (72 actual checks) |

### Competitor Analysis
| Tool | Description |
|------|-------------|
| `import_competitor_sitemap` | Fetch + parse competitor sitemap.xml for gap analysis |

### Persistence
| Tool | Description |
|------|-------------|
| `save_topical_map` | Save map to SQLite by client name |
| `load_topical_map` | Retrieve saved map |
| `list_saved_maps` | List all saved maps |

### Internal Linking
| Tool | Description |
|------|-------------|
| `generate_internal_link_graph` | Silo-compliant link plan (Tier 3 → 2 → 1 → Home) |

---

## Setup

### Requirements
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

### Step 1 — Install uv

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Mac/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2 — Clone and install

```bash
git clone https://github.com/KamrulHassanTuhin/topical-map-mcp.git
cd topical-map-mcp
uv sync
```

First run downloads the BGE embedding model (~50MB) from HuggingFace automatically. Cached after that — no internet needed.

### Step 3 — Test the pipeline

```bash
uv run python example_workflow.py
```

Expected output ends with: `DONE - full pipeline verified`

### Step 4 — Connect to Claude Desktop

Add to your `claude_desktop_config.json` inside `mcpServers`:

```json
"topical-map": {
  "command": "uv",
  "args": [
    "--directory",
    "/FULL/PATH/TO/topical-map-mcp",
    "run",
    "server.py"
  ]
}
```

> **Windows path example:** `F:\\MCP\\topical-map-mcp`  
> **Mac path example:** `/Users/yourname/MCP/topical-map-mcp`

### Step 5 — Restart Claude Desktop

Fully quit (system tray → Quit) and reopen. The `topical-map` server appears automatically every time — no manual steps needed.

---

## No API Keys Required

| Component | How |
|-----------|-----|
| Keyword clustering | Local BGE model (CPU, offline after first download) |
| All scoring formulas | Pure math — no external calls |
| Wikidata lookup | Free public API — no key |
| Competitor sitemap | Public URL fetch — no key |
| Storage | Local SQLite file |

---

## Example Workflows

### With SE Ranking MCP connected

> **You:** "Fetch the top 150 organic keywords for PubCrawls.com from SE Ranking. Build a topical map — central entity 'bar crawl events', core product 'pub crawl tickets', US market. Save it as 'PubCrawls.com'."

Claude will:
1. SE Ranking MCP → fetch keywords
2. `build_topical_map` → 8 corner nodes + keyword clusters
3. `save_topical_map` → saved to SQLite

### With Google Search Console MCP connected

> **You:** "Pull last 90 days of GSC data for our site. Find topics where impressions are high but clicks are low. Build content briefs for those gaps."

Claude will:
1. GSC MCP → fetch impression/click data
2. `score_topical_coverage` → identify gaps
3. `generate_content_brief` → brief for each gap page

### Standalone (no other MCP needed)

> **You:** "I have these 50 keywords. Build a topical map for 'project management software', core product 'task tracker'. Give me the full internal linking plan."

Claude will use topical-map MCP tools only — no other MCP required.

---

## Storage

SQLite database auto-created at `topical_maps.db` next to `server.py`.

Override with environment variable:
```bash
# Mac/Linux
export PSEO_DB_PATH=/path/to/your/maps.db

# Windows PowerShell
$env:PSEO_DB_PATH = "F:\MCP\my-maps.db"
```

---

## Built for Axis Consulting

Koray's framework © Koray Tuğberk GÜBÜR — this MCP encodes his publicly published methodology for agency use.
