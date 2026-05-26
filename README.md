# Topical Map MCP

A complete MCP (Model Context Protocol) server for **Holistic pSEO 2026** — based on Koray Tuğberk GÜBÜR's semantic SEO framework. 18 tools that chain with SE Ranking MCP and Claude as the orchestrator.

---

## How It Works

```
SE Ranking MCP  ──┐
                  ├──→  Claude (orchestrator)  ──→  You
topical-map MCP ──┘
```

Claude uses SE Ranking to fetch keyword data, then passes it to this MCP to build topical maps, content briefs, schema markup, and run quality gates — automatically.

---

## 18 Tools

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

First run downloads the BGE embedding model (~50MB) from HuggingFace automatically.

### Step 3 — Test the pipeline

```bash
uv run python example_workflow.py
```

Expected output ends with: `DONE - full pipeline verified`

### Step 4 — Connect to Claude Desktop

Open your Claude Desktop config:
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add this entry inside `mcpServers`:

```json
{
  "mcpServers": {
    "topical-map": {
      "command": "uv",
      "args": [
        "--directory",
        "/FULL/PATH/TO/topical-map-mcp",
        "run",
        "server.py"
      ]
    }
  }
}
```

> **Windows example path:** `F:\\MCP\\topical-map-mcp`

### Step 5 — Restart Claude Desktop

Fully quit (system tray → Quit) and reopen. The `topical-map` server will appear in the tool list.

---

## No API Keys Required

| Component | How |
|-----------|-----|
| Keyword clustering | Local BGE model (CPU, free) |
| All scoring formulas | Pure math |
| Wikidata lookup | Free public API |
| Competitor sitemap | Public URL fetch |
| Storage | Local SQLite |

---

## Example Workflow

In Claude Desktop, with SE Ranking MCP also connected:

> **You:** "Fetch the top 150 organic keywords for PubCrawls.com from SE Ranking. Then build a topical map — central entity 'bar crawl events', core product 'pub crawl tickets', US market. Save it as 'PubCrawls.com'."

Claude will:
1. Call SE Ranking MCP → fetch keywords
2. Call `build_topical_map` → 8 corner nodes + keyword clusters
3. Call `save_topical_map` → persist to SQLite

---

## Storage

SQLite database is created automatically at `topical_maps.db` next to `server.py`.

Override the path with an environment variable:
```bash
export PSEO_DB_PATH=/path/to/your/maps.db
```

---

## Built for Axis Consulting

Koray's framework © Koray Tuğberk GÜBÜR — this MCP encodes his publicly published methodology.
