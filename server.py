"""
─────────────────────────────────────────────────────────────────────────────────
  HOLISTIC pSEO 2026 – MCP SERVER (Final Version)
─────────────────────────────────────────────────────────────────────────────────

  Koray Tuğberk GÜBÜR's Semantic pSEO framework, exposed as 18 MCP tools.

  Built for chaining with SE Ranking MCP (keyword data) and Claude as the
  orchestrator. Pure-logic tools – no LLM calls inside the server, since
  Claude is already the LLM in the loop.

  AUTHOR: Built for Jordan @ Axis Consulting
  TARGET: Claude Desktop / Claude.ai MCP integration
  PYTHON: 3.10+
  STORAGE: SQLite (auto-created next to server.py)

  ────────────────────────────────────────────────────────────────────────────
  TOOL INDEX (18 tools)
  ────────────────────────────────────────────────────────────────────────────
    CLUSTERING & MAPS:
      1.  cluster_keywords
      2.  build_topical_map
      3.  suggest_8_corner_nodes

    CONTENT BRIEFS:
      4.  generate_content_brief

    SCORING (Koray's Formulas 1, 5, 6, 7):
      5.  classify_keyword_intent          (Formula 6 – Keyword Prioritization)
      6.  score_topical_coverage
      7.  score_topical_authority          (Formula 1)
      8.  score_ai_citation_potential      (Formula 5 – 9+ structured facts)
      9.  score_kbt_trust                  (Formula 7 – Knowledge-Based Trust)

    ENTITY & KNOWLEDGE GRAPH:
      10. validate_entity_wikidata
      11. build_eav_table

    SCHEMA MARKUP (JSON-LD):
      12. generate_schema_markup

    QUALITY GATE (Chapter 23):
      13. apply_quality_gate                (65-point checklist)

    COMPETITOR ANALYSIS:
      14. import_competitor_sitemap

    PERSISTENCE (SQLite):
      15. save_topical_map
      16. load_topical_map
      17. list_saved_maps

    INTERNAL LINKING:
      18. generate_internal_link_graph
  ────────────────────────────────────────────────────────────────────────────
"""

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: IMPORTS & CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import os
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np
import requests
from fastembed import TextEmbedding
from mcp.server.fastmcp import FastMCP
from sklearn.cluster import AgglomerativeClustering

# Initialise the MCP server
mcp = FastMCP("Holistic pSEO 2026 (Koray Framework)")

# SQLite DB lives next to this file by default – override with env var if needed
DB_PATH = Path(os.getenv("PSEO_DB_PATH", Path(__file__).parent / "topical_maps.db"))

# Embedding model (loaded lazily once, ~50MB)
_EMBEDDER: TextEmbedding | None = None


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: KORAY'S FRAMEWORK CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Intent value mapping (Formula 6)
INTENT_VALUES = {
    "transactional": 10,
    "commercial": 7,
    "informational": 3,
    "navigational": 1,
}

# Intent classification patterns (rule-based – Claude can refine after)
INTENT_PATTERNS = {
    "transactional": [
        r"\b(buy|order|purchase|book|hire|get|download|sign[\s-]?up|subscribe|register|reserve|enroll)\b",
        r"\b(coupon|deal|discount|offer|cheap|free trial|pricing|price|ticket|tickets|pass|passes|entry)\b",
        r"\b(near me|nearby|open now|hours|directions)\b",
        # city/geo + service = local transactional (e.g. "nyc bar crawl", "chicago pub crawl")
        r"\b(nyc|new york|manhattan|brooklyn|queens|bronx|chicago|boston|la|los angeles|miami|dallas|houston|seattle|denver|atlanta|philadelphia|phoenix|san francisco|sf|dc|washington)\b",
        r"\b(in [a-z]+ (city|tx|ca|ny|fl|il|wa|co|ga|pa|az|ma|nc|oh))\b",
    ],
    "commercial": [
        r"\b(best|top|review|reviews|vs|versus|comparison|compare|alternative|alternatives)\b",
        r"\b(which|recommended|rated|ranking|worth it|worth)\b",
        r"\b(agency|service|services|company|companies|provider|providers|platform|tool|tools|software)\b",
        r"\b(affordable|cheap|expensive|premium|budget|cost effective|value)\b",
        # local modifier without immediate city name = commercial research
        r"\b(local|near|around|in my area|in [a-z]+ area)\b",
    ],
    "navigational": [
        r"\b(login|sign in|dashboard|account|portal|logout|my account)\b",
        r"^\s*[A-Z][a-zA-Z]+\s*$",  # brand-name only
    ],
    "informational": [
        r"\b(how|what|why|when|where|who|guide|tutorial|tips|learn|understand)\b",
        r"\b(definition|meaning|explained|example|examples|overview|introduction|beginner)\b",
        r"\b(does|do|can|should|is|are|will|would|could)\b",
        r"\b(history|origin|difference between|types of|list of|ideas)\b",
    ],
}

# Koray's 65-point Quality Gate (Chapter 23)
QUALITY_GATE_CHECKS = {
    "pre_writing": [
        "source_context_statement_written",
        "contextual_domain_declared",
        "eav_table_complete_6mand_2opt_2enh",
        "8_subqueries_mapped_to_h2s",
        "hook_drafted_3_layers",
        "9plus_structured_facts_planned",
    ],
    "ai_selectability": [
        "9plus_structured_facts_in_content",
        "first_sentence_per_section_is_declarative",
        "every_section_self_contained",
        "all_statistics_dated_current_year",
        "fcp_under_0_4s",
        "reading_mode_check_passed",
    ],
    "bing_chatgpt": [
        "bing_webmaster_sitemap_submitted",
        "oai_searchbot_allowed_in_robots",
        "indexnow_api_enabled",
    ],
    "sxo_anti_pogo": [
        "hook_kills_pogo_in_10s",
        "answer_above_fold",
        "scannable_h2_navigation",
        "no_popups",
        "internal_links_with_bridges",
    ],
    "title_url": [
        "title_50_60_chars_with_year_or_number",
        "primary_entity_first",
        "url_entity_rich_level_2",
        "url_lowercase_hyphens_under_75_chars",
    ],
    "entity_layer": [
        "primary_entity_in_title_h1_first_100w",
        "salience_0_85_plus",
        "entity_home_about_us_linked",
        "brand_spo_triples_present",
        "agency_angle_maintained",
        "no_topical_dilution",
        "wsd_applied_ambiguous_terms_clarified",
        "bold_on_entity_and_key_data_only",
    ],
    "writing_rules": [
        "word_sequence_primary_entity_first",
        "declarative_only_no_hedging",
        "zero_fluff_one_breath_test",
        "numeric_values_throughout",
        "qualify_instances",
        "entailed_acquisition_verbs",
        "examples_after_plurals",
        "declaration_before_condition",
        "active_voice",
        "short_paragraphs_60_100_words",
    ],
    "architecture": [
        "h1_h2_h3_no_skip_levels",
        "heading_vector_consistent",
        "134_167_words_per_h2",
        "self_contained_sections",
        "tldr_box_present",
        "40_word_answers_after_h2s",
        "faq_7_8_questions",
        "structured_information_cards",
        "definition_blocks_at_section_starts",
    ],
    "image": [
        "alt_text_spo_format",
        "entity_rich_file_names",
        "webp_compressed_dimensions_specified",
        "lcp_eager_others_lazy",
    ],
    "technical": [
        "schema_stacked_correctly",
        "all_ai_bots_bingbot_allowed",
        "llms_txt_published",
        "freshness_time_datetime_tag",
        "semantic_html5_structure",
        "cwv_passed_fcp_under_0_4s",
        "schema_validated_rich_results_test",
        "anti_cannibalization_checked",
    ],
    "links": [
        "contextual_bridges_on_internal_links",
        "hub_page_linked",
        "2_3_sibling_pages_linked",
        "comparison_page_linked",
        "about_us_linked",
        "anchors_entity_specific_not_generic",
    ],
    "historical": [
        "publish_date_visible",
        "time_datetime_tag_with_year",
        "quarterly_refresh_calendar_set",
    ],
}

TOTAL_QG_CHECKS = sum(len(v) for v in QUALITY_GATE_CHECKS.values())
QG_PASS_THRESHOLD = int(round(0.954 * TOTAL_QG_CHECKS))
QG_MINIMUM_FLOOR = int(round(0.892 * TOTAL_QG_CHECKS))

# Word count targets by tier
TIER_WORD_COUNTS = {
    1: "2500-4000",  # Pillar
    2: "1500-2500",  # Supporting
    3: "800-1600",   # Atomic
}

TIER_NAMES = {1: "Pillar", 2: "Supporting", 3: "Atomic"}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: SQLITE STORAGE LAYER
# ─────────────────────────────────────────────────────────────────────────────

def _init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS topical_maps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                central_entity TEXT NOT NULL,
                core_service_or_product TEXT,
                target_market TEXT,
                map_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_maps_client ON topical_maps(client_name);

            CREATE TABLE IF NOT EXISTS content_briefs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                primary_keyword TEXT NOT NULL,
                tier INTEGER NOT NULL,
                brief_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_briefs_client ON content_briefs(client_name);

            CREATE TABLE IF NOT EXISTS entity_validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_name TEXT NOT NULL UNIQUE,
                wikidata_id TEXT,
                wikidata_url TEXT,
                description TEXT,
                validated_at TEXT NOT NULL
            );
        """)


_init_db()


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: EMBEDDING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_embedder() -> TextEmbedding:
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _EMBEDDER


def _embed(texts: list[str]) -> np.ndarray:
    return np.array(list(_get_embedder().embed(texts)))


def _cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_n = a / np.linalg.norm(a, axis=1, keepdims=True)
    b_n = b / np.linalg.norm(b, axis=1, keepdims=True)
    return a_n @ b_n.T


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: TOOLS – CLUSTERING & MAPS
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def cluster_keywords(keywords: list[str], cluster_count: int = 8) -> dict:
    """
    Semantic clustering of a keyword list using BGE embeddings.

    DATA SOURCE: Keywords typically come from SE Ranking MCP (organic
    keywords, keyword research) or Ahrefs. Pass the raw list here.

    Args:
        keywords: Keyword list to cluster.
        cluster_count: Target clusters (default 8, matches Koray's 8 corner nodes).

    Returns clusters with primary (centroid-closest) keyword per group.
    """
    if len(keywords) < 2:
        return {"error": "Need at least 2 keywords to cluster"}

    warning = None
    if len(keywords) < 100:
        warning = (
            f"Only {len(keywords)} keywords provided. Clusters will be thin and "
            f"topical coverage unreliable. Feed 100-200 keywords minimum for "
            f"accurate tier assignment and gap detection. Use SE Ranking MCP or "
            f"Ahrefs to pull domain organic keywords before clustering."
        )

    cluster_count = min(cluster_count, len(keywords))
    vectors = _embed(keywords)
    labels = AgglomerativeClustering(
        n_clusters=cluster_count, linkage="average", metric="cosine"
    ).fit_predict(vectors)

    grouped: dict[int, list[int]] = {}
    for i, label in enumerate(labels):
        grouped.setdefault(int(label), []).append(i)

    clusters = []
    for label, indices in sorted(grouped.items()):
        cluster_vecs = vectors[indices]
        centroid = cluster_vecs.mean(axis=0, keepdims=True)
        sims = _cosine(cluster_vecs, centroid).flatten()
        primary_idx = indices[int(sims.argmax())]
        cluster_kws = [keywords[i] for i in indices]
        clusters.append({
            "cluster_id": label,
            "primary_keyword": keywords[primary_idx],
            "supporting_keywords": [k for k in cluster_kws if k != keywords[primary_idx]],
            "keyword_count": len(cluster_kws),
        })

    result = {
        "total_keywords": len(keywords),
        "cluster_count": len(clusters),
        "clusters": clusters,
    }
    if warning:
        result["warning"] = warning
    return result


@mcp.tool()
def build_topical_map(
    central_entity: str,
    core_service_or_product: str,
    keywords: list[str],
    target_market: str = "United States",
    cluster_count: int = 8,
    client_name: str | None = None,
) -> dict:
    """
    Build a complete topical map: Koray's 8 corner nodes + 3-tier hierarchy.

    CHAIN HINT: Use AFTER fetching keywords from SE Ranking MCP. Typical flow:
      1. SE Ranking MCP fetches domain organic keywords (top 100-200)
      2. This tool builds the full map
      3. generate_content_brief() called for each cluster
      4. save_topical_map() persists the result

    Args:
        central_entity: Site's central entity (e.g., "bar crawl events").
        core_service_or_product: Core offering (e.g., "pub crawl tickets").
        keywords: All researched keywords for supporting pages.
        target_market: Geographic focus (Koray's WHERE node).
        cluster_count: Target supporting clusters (default 8).
        client_name: Optional – if provided, returned map can be saved directly.
    """
    corner_nodes = [
        {"node": "WHO", "page_id": "A0", "tier": 1, "page_type": "About / Entity Home",
         "title": f"About {central_entity}", "h1": f"About {central_entity}",
         "purpose": "Entity declaration, founder, mission, E-E-A-T signals",
         "word_count": TIER_WORD_COUNTS[1]},
        {"node": "WHAT", "page_id": "A1", "tier": 1, "page_type": "Pillar – Definition",
         "title": f"What is {core_service_or_product}? Definitive Guide 2026",
         "h1": f"What is {core_service_or_product}?",
         "purpose": "Definitive entity definition + EAV attributes table",
         "word_count": TIER_WORD_COUNTS[1]},
        {"node": "HOW", "page_id": "A2", "tier": 2, "page_type": "Supporting – Process",
         "title": f"How {core_service_or_product} Works (Step-by-Step)",
         "h1": f"How {core_service_or_product} works",
         "purpose": "Process/methodology breakdown – sequential SPO triples",
         "word_count": TIER_WORD_COUNTS[2]},
        {"node": "HOW MUCH", "page_id": "A3", "tier": 2, "page_type": "Supporting – Pricing",
         "title": f"{core_service_or_product} Cost & Pricing in 2026",
         "h1": f"{core_service_or_product} cost",
         "purpose": "Cost transparency, pricing tiers, ROI calculation",
         "word_count": TIER_WORD_COUNTS[2]},
        {"node": "WHEN", "page_id": "A4", "tier": 2, "page_type": "Supporting – Timing",
         "title": f"When to Start With {core_service_or_product}",
         "h1": f"When to start with {core_service_or_product}",
         "purpose": "Buyer-stage signals, timing triggers, decision criteria",
         "word_count": TIER_WORD_COUNTS[2]},
        {"node": "WHY", "page_id": "B1", "tier": 1, "page_type": "Pillar – Comparison",
         "title": f"Why {core_service_or_product} vs Alternatives (2026)",
         "h1": f"Why {core_service_or_product} vs alternatives",
         "purpose": "Competitive positioning, differentiation, disambiguation",
         "word_count": TIER_WORD_COUNTS[1]},
        {"node": "WHICH", "page_id": "C0", "tier": 1, "page_type": "Pillar – Use-Case Hub",
         "title": f"{core_service_or_product} for [Use Cases / Industries]",
         "h1": f"{core_service_or_product} use cases",
         "purpose": "Hub linking to all atomic Tier-3 use-case children",
         "word_count": TIER_WORD_COUNTS[1]},
        {"node": "WHERE", "page_id": "D0", "tier": 1, "page_type": "Pillar – Geo Hub",
         "title": f"{core_service_or_product} in {target_market}",
         "h1": f"{core_service_or_product} in {target_market}",
         "purpose": f"Geographic hub for {target_market}, links to city pages",
         "word_count": TIER_WORD_COUNTS[1]},
    ]

    supporting_pages = []
    if keywords:
        clustered = cluster_keywords(keywords, cluster_count=cluster_count)
        for i, c in enumerate(clustered["clusters"]):
            kw_count = c["keyword_count"]
            if kw_count >= 8:
                tier = 1
            elif kw_count >= 4:
                tier = 2
            else:
                tier = 3
            supporting_pages.append({
                "page_id": f"E{i+1}",
                "tier": tier,
                "page_type": TIER_NAMES[tier],
                "primary_keyword": c["primary_keyword"],
                "supporting_keywords": c["supporting_keywords"],
                "keyword_count": kw_count,
                "word_count": TIER_WORD_COUNTS[tier],
                "parent": "C0 (use-case hub)" if tier == 3 else
                          ("Homepage" if tier == 1 else "C0 or D0"),
            })

    result = {
        "framework": "Holistic pSEO 2026 (Koray Tuğberk GÜBÜR)",
        "client_name": client_name,
        "central_entity": central_entity,
        "core_service_or_product": core_service_or_product,
        "target_market": target_market,
        "publish_first_corner_nodes": corner_nodes,
        "supporting_pages_from_keywords": supporting_pages,
        "total_pages_planned": len(corner_nodes) + len(supporting_pages),
        "silo_linking_rule": "Tier 3 → Tier 2 → Tier 1 → Homepage (never skip levels)",
        "80_percent_coverage_rule": (
            "Target competitive head terms only AFTER 87+ pages published "
            "(~Month 9). Before that: long-tail only."
        ),
        "next_actions": [
            "1. Run generate_content_brief() for each corner node (priority order: A1 → A0 → B1 → C0/D0).",
            "2. Run generate_schema_markup() per page type.",
            "3. Run apply_quality_gate() before publish on each page.",
            "4. save_topical_map() to persist this map for the client.",
        ],
    }
    return result


@mcp.tool()
def suggest_8_corner_nodes(
    central_entity: str,
    core_service_or_product: str,
    target_market: str = "United States",
) -> dict:
    """
    Generate the universal 8-corner-node skeleton without keyword data.
    Useful for kick-off planning before keyword research.
    """
    return build_topical_map(
        central_entity=central_entity,
        core_service_or_product=core_service_or_product,
        keywords=[],
        target_market=target_market,
        cluster_count=0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: TOOLS – CONTENT BRIEFS
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def generate_content_brief(
    primary_keyword: str,
    central_entity: str,
    supporting_keywords: list[str] | None = None,
    tier: int = 2,
    page_type: str = "Supporting",
    target_market: str | None = None,
    client_name: str | None = None,
) -> dict:
    """
    Generate a content brief in Koray's structure (Ch 9 + Ch 23).

    Args:
        primary_keyword: Canonical query for this page (1 page = 1 query).
        central_entity: Site's central entity for internal linking.
        supporting_keywords: Secondary keywords for FAQ + body.
        tier: 1 Pillar | 2 Supporting | 3 Atomic.
        page_type: Pillar / Supporting / Atomic / Comparison / Geo / About.
        target_market: For geo pages.
        client_name: Optional – for saving the brief.
    """
    sk = supporting_keywords or []
    word_target = TIER_WORD_COUNTS.get(tier, "1500-2500")

    return {
        "framework": "Holistic pSEO 2026",
        "page_meta": {
            "primary_keyword": primary_keyword,
            "canonical_query": primary_keyword,
            "tier": tier,
            "tier_name": TIER_NAMES.get(tier, "Supporting"),
            "page_type": page_type,
            "central_entity_link": central_entity,
            "target_market": target_market,
            "word_count_target": word_target,
        },
        "title_and_h1": {
            "title_tag": f"{primary_keyword.title()} | 2026 [Value Prop] – 50-60 chars",
            "h1": primary_keyword.title(),
            "rule": "H1 must contain canonical query verbatim or close variant.",
            "url_pattern": f"/{re.sub(r'[^a-z0-9]+', '-', primary_keyword.lower()).strip('-')}/",
        },
        "intro_50_words": [
            f"Define '{primary_keyword}' in the first sentence – declarative, no hedging.",
            f"Connect to central entity: {central_entity}.",
            "State the search-intent satisfaction promise upfront.",
            "Place 1 numeric fact in the first 100 words for AI selectability.",
        ],
        "required_h2_sections": [
            {"h2": f"What is {primary_keyword}?",
             "purpose": "Entity definition + EAV table (attribute-value pairs)",
             "min_spo_triples": 8,
             "answer_first_40_words": True},
            {"h2": f"How {primary_keyword} works",
             "purpose": "Process/methodology – sequential SPO triples",
             "min_spo_triples": 6,
             "answer_first_40_words": True},
            {"h2": f"Types of {primary_keyword}",
             "purpose": "Taxonomic breakdown – same-type entities",
             "min_spo_triples": 5,
             "answer_first_40_words": True},
            {"h2": f"{primary_keyword} vs alternatives",
             "purpose": "Comparative context – disambiguation",
             "min_spo_triples": 4,
             "answer_first_40_words": True},
            {"h2": "FAQ",
             "purpose": "Long-tail query coverage from supporting keywords",
             "min_questions": min(8, max(7, len(sk) or 7)),
             "format": "One-sentence answers for AI snippet extraction"},
        ],
        "eav_mandatory_attributes": [
            "definition", "purpose", "components", "process",
            "benefits", "limitations",
        ],
        "eav_optional_attributes": ["cost_range", "duration"],
        "eav_enhancing_attributes": ["case_examples", "historical_context"],
        "supporting_keywords_to_distribute": sk,
        "internal_linking": {
            "link_up_to_parent": "Tier-1 pillar / Homepage" if tier <= 2 else "Tier-2 supporting parent",
            "sibling_links": "2-4 related cluster pages with contextual bridges",
            "must_link_to": ["Hub page", "Comparison page", "/about-us/"],
            "anchor_text_rule": "Entity-specific anchors, not generic 'click here'",
        },
        "quality_gate_minimums": {
            "unique_entities_named": 15,
            "spo_triples_total": 20,
            "outbound_authoritative_sources": 3,
            "structured_facts_for_AI_coverage": 9,
            "schema_markup_required": ["Article", "BreadcrumbList", "FAQPage"],
            "salience_target": 0.85,
            "fcp_target_seconds": 0.4,
        },
        "ai_citation_optimization": [
            "Front-load definite information in first 100 words.",
            "Answer-first paragraph structure (claim – evidence).",
            "9+ structured facts for ChatGPT / Perplexity / AI Overviews citation.",
            "One-sentence FAQ answers for snippet extraction.",
            "All statistics dated for current year.",
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: TOOLS – SCORING (KORAY'S FORMULAS)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def classify_keyword_intent(keywords: list[str]) -> dict:
    """
    Classify each keyword by search intent (Formula 6):
    Transactional=10 | Commercial=7 | Informational=3 | Navigational=1

    Args:
        keywords: List of keywords to classify.
    """
    results = []
    for kw in keywords:
        kw_lower = kw.lower()
        intent_scores = {}
        for intent, patterns in INTENT_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, kw_lower):
                    intent_scores[intent] = intent_scores.get(intent, 0) + 1

        if not intent_scores:
            intent = "informational"
        else:
            intent = max(intent_scores, key=intent_scores.get)

        results.append({
            "keyword": kw,
            "intent": intent,
            "intent_value": INTENT_VALUES[intent],
            "note": "Rule-based – Claude can refine ambiguous cases" if not intent_scores else None,
        })

    summary = {}
    for r in results:
        summary[r["intent"]] = summary.get(r["intent"], 0) + 1

    return {
        "formula": "Formula 6 – Keyword Prioritization (intent value × volume × relevance ÷ KD × DA gap)",
        "intent_distribution": summary,
        "keywords": results,
    }


@mcp.tool()
def score_topical_coverage(
    existing_page_topics: list[str],
    target_topics: list[str],
    coverage_threshold: float = 0.70,
) -> dict:
    """
    Compare existing pages to target clusters via semantic similarity.

    Args:
        existing_page_topics: Already-published page titles/topics.
        target_topics: Topics to rank for.
        coverage_threshold: Cosine similarity for "covered" (default 0.70).
    """
    if not existing_page_topics or not target_topics:
        return {"error": "Both lists must be non-empty"}

    page_vec = _embed(existing_page_topics)
    target_vec = _embed(target_topics)
    sim = _cosine(page_vec, target_vec)

    covered, gaps = [], []
    for j, target in enumerate(target_topics):
        col = sim[:, j]
        best_idx = int(col.argmax())
        max_sim = float(col.max())
        if max_sim >= coverage_threshold:
            covered.append({
                "target_topic": target,
                "best_matching_page": existing_page_topics[best_idx],
                "similarity": round(max_sim, 3),
            })
        else:
            priority = "HIGH" if max_sim < 0.45 else "MEDIUM"
            gaps.append({
                "target_topic": target,
                "closest_existing_page": existing_page_topics[best_idx],
                "similarity": round(max_sim, 3),
                "priority": priority,
                "action": "Build new page" if max_sim < 0.45 else "Expand existing OR build new",
            })

    coverage_pct = len(covered) / len(target_topics) * 100
    return {
        "coverage_score_percent": round(coverage_pct, 1),
        "target_topics_total": len(target_topics),
        "covered_count": len(covered),
        "gap_count": len(gaps),
        "covered_topics": covered,
        "gap_topics": gaps,
        "recommendation": (
            f"Build {sum(1 for g in gaps if g['priority']=='HIGH')} HIGH-priority "
            f"new pages, then {sum(1 for g in gaps if g['priority']=='MEDIUM')} MEDIUM."
        ),
    }


@mcp.tool()
def score_topical_authority(
    topical_coverage_pct: float,
    historical_data_months: int,
    cost_of_retrieval_seconds: float = 0.4,
) -> dict:
    """
    Formula 1 – Topical Authority = (Coverage × Historical) ÷ Retrieval Cost.

    Args:
        topical_coverage_pct: 0-100 – % of planned topical map published.
        historical_data_months: Domain age + content history in months.
        cost_of_retrieval_seconds: Avg FCP / TTFB for the site (lower better).
    """
    if cost_of_retrieval_seconds <= 0:
        return {"error": "cost_of_retrieval_seconds must be > 0"}

    score = (topical_coverage_pct * historical_data_months) / (cost_of_retrieval_seconds * 100)

    if score >= 50:
        grade, desc = "A", "Strong topical authority – keep refreshing quarterly."
    elif score >= 25:
        grade, desc = "B", "Growing authority – expand to 87+ pages for head-term targeting."
    elif score >= 10:
        grade, desc = "C", "Emerging – focus on coverage expansion and freshness."
    else:
        grade, desc = "D", "Low authority – prioritize coverage + speed optimization."

    return {
        "formula": "Topical Authority = (Coverage × Historical Data) ÷ Cost of Retrieval",
        "inputs": {
            "topical_coverage_pct": topical_coverage_pct,
            "historical_data_months": historical_data_months,
            "cost_of_retrieval_seconds": cost_of_retrieval_seconds,
        },
        "score": round(score, 2),
        "grade": grade,
        "interpretation": desc,
    }


@mcp.tool()
def score_ai_citation_potential(
    structured_facts_count: int,
    monthly_update_recency_days: int,
    domain_authority: int,
) -> dict:
    """
    Formula 5 – AI Coverage = Structured Facts × Updates × DA.
    Key threshold: 9+ structured facts = ~78% AI coverage.

    Args:
        structured_facts_count: Count of dated, numeric, verifiable facts on the page.
        monthly_update_recency_days: Days since last update (lower = better).
        domain_authority: Moz DA, Ahrefs DR, or InLink Rank (0-100).
    """
    if structured_facts_count >= 9:
        baseline_pct = 78
    elif structured_facts_count >= 5:
        baseline_pct = 45
    elif structured_facts_count >= 3:
        baseline_pct = 22
    else:
        baseline_pct = 9

    freshness_mult = 1.0 if monthly_update_recency_days <= 30 else (
        0.85 if monthly_update_recency_days <= 90 else
        0.65 if monthly_update_recency_days <= 180 else 0.4
    )
    da_mult = min(1.2, 0.5 + domain_authority / 100)

    coverage_pct = min(95, baseline_pct * freshness_mult * da_mult)

    recommendations = []
    if structured_facts_count < 9:
        recommendations.append(
            f"Add {9 - structured_facts_count} more structured facts to hit the 78% threshold."
        )
    if monthly_update_recency_days > 30:
        recommendations.append("Refresh the page – recency under 30 days hits max multiplier.")
    if domain_authority < 50:
        recommendations.append("Build topical authority + backlinks to raise DA past 50.")

    return {
        "formula": "AI Citation Coverage = Structured Facts × Monthly Updates × Domain Authority",
        "estimated_ai_citation_coverage_pct": round(coverage_pct, 1),
        "inputs": {
            "structured_facts_count": structured_facts_count,
            "monthly_update_recency_days": monthly_update_recency_days,
            "domain_authority": domain_authority,
        },
        "thresholds": {
            "9+_facts": "~78% coverage",
            "5-8_facts": "~45% coverage",
            "3-4_facts": "~22% coverage",
            "0-2_facts": "~9% coverage",
        },
        "recommendations": recommendations or ["Page is well-optimized for AI citation."],
    }


@mcp.tool()
def score_kbt_trust(
    verified_facts: int,
    source_corroboration_count: int,
    author_credibility_score: int,
    unverified_claims: int = 0,
    false_statements: int = 0,
    contradictions: int = 0,
) -> dict:
    """
    Formula 7 – Knowledge-Based Trust (KBT).

    Args:
        verified_facts: Facts confirmed by external authoritative sources.
        source_corroboration_count: Distinct authoritative sources cited.
        author_credibility_score: 1-10, based on author bio + credentials.
        unverified_claims: Claims with no source backing.
        false_statements: Demonstrably wrong claims.
        contradictions: Internal contradictions within the page or site.
    """
    denominator = max(1, unverified_claims + false_statements + contradictions)
    trust_score = (verified_facts * source_corroboration_count * author_credibility_score) / denominator

    if trust_score >= 100:
        grade = "A – High KBT, strong AI citation candidate"
    elif trust_score >= 40:
        grade = "B – Acceptable KBT, fix unverified claims"
    elif trust_score >= 15:
        grade = "C – Weak KBT, restructure with source-backed facts"
    else:
        grade = "D – KBT failure, rewrite required"

    return {
        "formula": "KBT = (Verified Facts × Source Corroboration × Author Credibility) ÷ (Unverified + False + Contradictions)",
        "trust_score": round(trust_score, 2),
        "grade": grade,
        "inputs": {
            "verified_facts": verified_facts,
            "source_corroboration_count": source_corroboration_count,
            "author_credibility_score": author_credibility_score,
            "unverified_claims": unverified_claims,
            "false_statements": false_statements,
            "contradictions": contradictions,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8: TOOLS – ENTITY & KNOWLEDGE GRAPH
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def validate_entity_wikidata(entity_name: str) -> dict:
    """
    Look up an entity in Wikidata to confirm it's a recognized Knowledge Graph entity.

    Args:
        entity_name: The entity to look up (e.g., "Pub crawl", "Mailchimp").
    """
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT wikidata_id, wikidata_url, description, validated_at "
            "FROM entity_validations WHERE entity_name = ?",
            (entity_name,),
        ).fetchone()
        if row:
            return {
                "entity_name": entity_name,
                "wikidata_id": row[0],
                "wikidata_url": row[1],
                "description": row[2],
                "validated_at": row[3],
                "source": "cached",
            }

    try:
        resp = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "search": entity_name,
                "language": "en",
                "format": "json",
                "limit": 1,
            },
            timeout=10,
            headers={"User-Agent": "HolisticPSEO-MCP/1.0 (SEO research)"},
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("search", [])

        if not results:
            return {
                "entity_name": entity_name,
                "found": False,
                "recommendation": "Entity not in Wikidata. Consider creating a Wikidata page.",
            }

        match = results[0]
        wd_id = match["id"]
        wd_url = f"https://www.wikidata.org/wiki/{wd_id}"
        description = match.get("description", "")

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO entity_validations "
                "(entity_name, wikidata_id, wikidata_url, description, validated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (entity_name, wd_id, wd_url, description, _now()),
            )

        return {
            "entity_name": entity_name,
            "found": True,
            "wikidata_id": wd_id,
            "wikidata_url": wd_url,
            "description": description,
            "validated_at": _now(),
            "source": "wikidata_api",
            "usage_hint": "Reference this Wikidata URL in schema.org 'sameAs' property.",
        }
    except Exception as e:
        return {"entity_name": entity_name, "error": f"Wikidata lookup failed: {e}"}


@mcp.tool()
def build_eav_table(
    entity_name: str,
    attribute_value_pairs: list[dict],
) -> dict:
    """
    Build a structured EAV (Entity-Attribute-Value) table for a topic page.

    Args:
        entity_name: The page's central entity.
        attribute_value_pairs: List of {"attribute": "...", "value": "..."} dicts.
    """
    mandatory_attrs = {"definition", "purpose", "components", "process",
                       "benefits", "limitations"}
    optional_attrs = {"cost_range", "duration", "cost", "pricing"}
    enhancing_attrs = {"case_examples", "historical_context", "examples", "history"}

    provided = {p["attribute"].lower().replace(" ", "_") for p in attribute_value_pairs}

    mandatory_covered = mandatory_attrs & provided
    mandatory_missing = mandatory_attrs - provided
    optional_covered = optional_attrs & provided
    enhancing_covered = enhancing_attrs & provided

    completeness = (
        (len(mandatory_covered) / 6) * 0.6 +
        (min(2, len(optional_covered)) / 2) * 0.2 +
        (min(2, len(enhancing_covered)) / 2) * 0.2
    ) * 100

    eav_table = [
        {"entity": entity_name, "attribute": p["attribute"], "value": p["value"]}
        for p in attribute_value_pairs
    ]

    return {
        "entity": entity_name,
        "eav_table": eav_table,
        "completeness_pct": round(completeness, 1),
        "koray_rule": "6 mandatory + 2 optional + 2 enhancing attributes minimum",
        "mandatory_covered": sorted(mandatory_covered),
        "mandatory_missing": sorted(mandatory_missing),
        "optional_covered": sorted(optional_covered),
        "enhancing_covered": sorted(enhancing_covered),
        "ready_for_quality_gate": (
            len(mandatory_covered) == 6
            and len(optional_covered) >= 2
            and len(enhancing_covered) >= 2
        ),
        "next_action": (
            "EAV complete – pass to quality gate"
            if len(mandatory_missing) == 0
            else f"Add: {', '.join(sorted(mandatory_missing))}"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9: TOOLS – SCHEMA MARKUP (JSON-LD)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def generate_schema_markup(
    page_type: str,
    page_url: str,
    headline: str,
    description: str,
    author_name: str,
    publisher_name: str,
    publisher_logo_url: str,
    date_published: str,
    breadcrumb_trail: list[dict] | None = None,
    faq_items: list[dict] | None = None,
    same_as_urls: list[str] | None = None,
) -> dict:
    """
    Generate stacked JSON-LD schema markup following Koray's Ch 15D rules.

    Args:
        page_type: "article" | "service" | "faq" | "about" | "comparison".
        page_url: Full URL of the page.
        headline: Page H1 / title.
        description: Meta description / page summary.
        author_name: Author byline.
        publisher_name: Publishing org.
        publisher_logo_url: Org logo URL.
        date_published: ISO 8601 (YYYY-MM-DD).
        breadcrumb_trail: [{"name": "Home", "url": "https://..."}, ...].
        faq_items: [{"q": "...", "a": "..."}, ...].
        same_as_urls: Wikidata + social URLs for entity signal.
    """
    schemas = []

    article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": headline,
        "description": description,
        "url": page_url,
        "datePublished": date_published,
        "dateModified": _now()[:10],
        "author": {"@type": "Person", "name": author_name},
        "publisher": {
            "@type": "Organization",
            "name": publisher_name,
            "logo": {"@type": "ImageObject", "url": publisher_logo_url},
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": page_url},
    }
    if same_as_urls:
        article["sameAs"] = same_as_urls
    schemas.append(article)

    if breadcrumb_trail:
        schemas.append({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": crumb["name"],
                    "item": crumb["url"],
                }
                for i, crumb in enumerate(breadcrumb_trail)
            ],
        })

    if faq_items:
        schemas.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item["q"],
                    "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
                }
                for item in faq_items
            ],
        })

    return {
        "page_url": page_url,
        "page_type": page_type,
        "schema_count": len(schemas),
        "schemas_json_ld": schemas,
        "embed_instructions": (
            "Place each schema in a separate <script type=\"application/ld+json\"> "
            "tag inside <head>. Validate with Google Rich Results Test before publish."
        ),
        "validation_url": "https://search.google.com/test/rich-results",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10: TOOLS – QUALITY GATE (CH 23)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def apply_quality_gate(
    checks_passed: list[str],
    page_url: str | None = None,
) -> dict:
    """
    Apply Koray's 65-point quality gate (Chapter 23).

    Args:
        checks_passed: List of check IDs that pass. Call with empty list first to see all IDs.
        page_url: Optional – URL being audited.
    """
    passed_set = set(checks_passed)
    all_check_ids = []
    category_results = {}

    for category, checks in QUALITY_GATE_CHECKS.items():
        cat_passed = [c for c in checks if c in passed_set]
        cat_failed = [c for c in checks if c not in passed_set]
        all_check_ids.extend(checks)
        category_results[category] = {
            "total": len(checks),
            "passed": len(cat_passed),
            "failed_check_ids": cat_failed,
        }

    total_passed = sum(c["passed"] for c in category_results.values())

    if total_passed >= QG_PASS_THRESHOLD:
        verdict = "PASS – ready to publish"
    elif total_passed >= QG_MINIMUM_FLOOR:
        verdict = f"BORDERLINE – fix {QG_PASS_THRESHOLD - total_passed} more checks to PASS"
    else:
        verdict = f"FAIL – at least {QG_MINIMUM_FLOOR - total_passed} more checks needed"

    return {
        "framework": "Koray Quality Gate (Chapter 23)",
        "page_url": page_url,
        "score": f"{total_passed}/{TOTAL_QG_CHECKS}",
        "pass_threshold": f"{QG_PASS_THRESHOLD}/{TOTAL_QG_CHECKS}",
        "minimum_floor": f"{QG_MINIMUM_FLOOR}/{TOTAL_QG_CHECKS}",
        "verdict": verdict,
        "category_breakdown": category_results,
        "all_check_ids_for_reference": all_check_ids,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11: TOOLS – COMPETITOR ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def import_competitor_sitemap(sitemap_url: str, max_urls: int = 500) -> dict:
    """
    Fetch a competitor's sitemap.xml and extract URLs + path-derived topics.

    Args:
        sitemap_url: Full URL to sitemap.xml or sitemap index.
        max_urls: Cap on URLs returned (default 500).
    """
    try:
        resp = requests.get(
            sitemap_url,
            timeout=15,
            headers={"User-Agent": "HolisticPSEO-MCP/1.0 (SEO research)"},
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        return {"error": f"Failed to fetch sitemap: {e}"}

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sub_sitemaps = root.findall(".//sm:sitemap/sm:loc", ns)
    urls = []

    if sub_sitemaps:
        for sm in sub_sitemaps[:10]:
            try:
                sub_resp = requests.get(
                    sm.text, timeout=15,
                    headers={"User-Agent": "HolisticPSEO-MCP/1.0"},
                )
                sub_resp.raise_for_status()
                sub_root = ET.fromstring(sub_resp.content)
                for url_el in sub_root.findall(".//sm:url/sm:loc", ns):
                    urls.append(url_el.text)
                    if len(urls) >= max_urls:
                        break
            except Exception:
                continue
            if len(urls) >= max_urls:
                break
    else:
        for url_el in root.findall(".//sm:url/sm:loc", ns):
            urls.append(url_el.text)
            if len(urls) >= max_urls:
                break

    pages = []
    for u in urls:
        path = urlparse(u).path.strip("/")
        if not path:
            topic = "homepage"
        else:
            slug = path.rstrip("/").split("/")[-1]
            topic = slug.replace("-", " ").replace("_", " ").strip()
        pages.append({"url": u, "derived_topic": topic})

    return {
        "sitemap_url": sitemap_url,
        "urls_imported": len(pages),
        "pages": pages,
        "next_action": "Use derived_topic list as 'existing_page_topics' in score_topical_coverage().",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 12: TOOLS – PERSISTENCE (SQLite)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def save_topical_map(client_name: str, topical_map: dict) -> dict:
    """
    Persist a topical map to SQLite. Overwrites existing map for same client_name.

    Args:
        client_name: Identifier (e.g., "PubCrawls.com").
        topical_map: The full dict returned by build_topical_map().
    """
    central = topical_map.get("central_entity", "")
    core = topical_map.get("core_service_or_product", "")
    market = topical_map.get("target_market", "")

    with sqlite3.connect(DB_PATH) as conn:
        existing = conn.execute(
            "SELECT id FROM topical_maps WHERE client_name = ?", (client_name,)
        ).fetchone()
        now = _now()
        if existing:
            conn.execute(
                "UPDATE topical_maps SET central_entity=?, core_service_or_product=?, "
                "target_market=?, map_json=?, updated_at=? WHERE id=?",
                (central, core, market, json.dumps(topical_map), now, existing[0]),
            )
            map_id = existing[0]
            action = "updated"
        else:
            cursor = conn.execute(
                "INSERT INTO topical_maps (client_name, central_entity, "
                "core_service_or_product, target_market, map_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (client_name, central, core, market, json.dumps(topical_map), now, now),
            )
            map_id = cursor.lastrowid
            action = "created"

    return {"action": action, "map_id": map_id, "client_name": client_name, "saved_at": now, "db_path": str(DB_PATH)}


@mcp.tool()
def load_topical_map(client_name: str) -> dict:
    """
    Retrieve a previously saved topical map by client name.

    Args:
        client_name: Client identifier used when saving.
    """
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, central_entity, core_service_or_product, target_market, "
            "map_json, created_at, updated_at FROM topical_maps WHERE client_name = ?",
            (client_name,),
        ).fetchone()

    if not row:
        return {"error": f"No saved map for client_name='{client_name}'"}

    return {
        "map_id": row[0],
        "client_name": client_name,
        "central_entity": row[1],
        "core_service_or_product": row[2],
        "target_market": row[3],
        "topical_map": json.loads(row[4]),
        "created_at": row[5],
        "updated_at": row[6],
    }


@mcp.tool()
def list_saved_maps() -> dict:
    """List all topical maps saved in the local database."""
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT client_name, central_entity, core_service_or_product, "
            "target_market, created_at, updated_at "
            "FROM topical_maps ORDER BY updated_at DESC"
        ).fetchall()

    maps = [
        {"client_name": r[0], "central_entity": r[1], "core_service_or_product": r[2],
         "target_market": r[3], "created_at": r[4], "updated_at": r[5]}
        for r in rows
    ]
    return {"total_maps": len(maps), "maps": maps, "db_path": str(DB_PATH)}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 13: TOOLS – INTERNAL LINKING
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def generate_internal_link_graph(topical_map: dict) -> dict:
    """
    Generate the internal linking graph from a topical map.
    Silo rule: Tier 3 → Tier 2 → Tier 1 → Homepage (no skipping).

    Args:
        topical_map: Output of build_topical_map() or load_topical_map().topical_map.
    """
    corners = topical_map.get("publish_first_corner_nodes", [])
    supporting = topical_map.get("supporting_pages_from_keywords", [])
    all_pages = corners + supporting

    by_tier = {1: [], 2: [], 3: []}
    for p in all_pages:
        tier = p.get("tier", 2)
        by_tier.setdefault(tier, []).append(p)

    links = []

    for p in by_tier[1]:
        links.append({
            "from": p["page_id"],
            "to": "Homepage",
            "anchor_rule": f"Entity-rich: '{p.get('h1', p.get('title', ''))}'",
            "type": "tier_to_home",
        })

    pillar_ids = [p["page_id"] for p in by_tier[1]]
    for i, p in enumerate(by_tier[2]):
        parent_pillar = pillar_ids[i % len(pillar_ids)] if pillar_ids else "Homepage"
        links.append({
            "from": p["page_id"],
            "to": parent_pillar,
            "anchor_rule": "Contextual bridge – entity-specific anchor",
            "type": "tier2_to_tier1",
        })
        siblings = [s["page_id"] for s in by_tier[2] if s["page_id"] != p["page_id"]][:2]
        for sib in siblings:
            links.append({"from": p["page_id"], "to": sib,
                          "anchor_rule": "Sibling cluster – contextual bridge", "type": "tier2_sibling"})

    supporting_ids = [p["page_id"] for p in by_tier[2]]
    for i, p in enumerate(by_tier[3]):
        parent = supporting_ids[i % len(supporting_ids)] if supporting_ids else (
            pillar_ids[0] if pillar_ids else "Homepage"
        )
        links.append({"from": p["page_id"], "to": parent,
                      "anchor_rule": "Entity-specific anchor – narrow context", "type": "tier3_to_tier2"})

    return {
        "silo_rule": "Tier 3 → Tier 2 → Tier 1 → Homepage (never skip levels)",
        "total_pages": len(all_pages),
        "tier_distribution": {f"tier_{t}": len(by_tier[t]) for t in (1, 2, 3)},
        "total_links": len(links),
        "links": links,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 14: MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
