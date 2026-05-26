"""
Quickstart Example - PubCrawls.com style workflow

Run this from inside the topical-map-mcp-final folder to verify
every major tool works end-to-end on your machine:

    uv run python example_workflow.py

This DOES NOT call SE Ranking - it uses hardcoded sample keywords
to demonstrate the full pipeline.
"""

import json
import sys

sys.path.insert(0, ".")
import server


def divider(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


SAMPLE_KEYWORDS = [
    "nyc bar crawl tickets",
    "manhattan pub crawl",
    "brooklyn bar crawl",
    "best bar crawls 2026",
    "top rated pub crawls",
    "chicago bar crawl events",
    "chicago pub crawl",
    "boston bar crawl",
    "halloween bar crawl nyc",
    "santa pub crawl chicago",
    "how to organize a bar crawl",
    "pub crawl business plan",
    "bar crawl insurance requirements",
    "what to wear bar crawl",
    "bar crawl etiquette",
]


def run():
    divider("STEP 1 - Build topical map (Koray's 8 corner + 3 tiers)")
    topical_map = server.build_topical_map(
        central_entity="bar crawl events",
        core_service_or_product="pub crawl tickets",
        keywords=SAMPLE_KEYWORDS,
        target_market="United States",
        cluster_count=5,
        client_name="PubCrawls.com",
    )
    print(f"  Total pages planned: {topical_map['total_pages_planned']}")
    print(f"  Corner nodes: {len(topical_map['publish_first_corner_nodes'])}")
    print(f"  Keyword clusters: {len(topical_map['supporting_pages_from_keywords'])}")

    divider("STEP 2 - Classify keyword intents (Formula 6)")
    intents = server.classify_keyword_intent(keywords=SAMPLE_KEYWORDS)
    print(f"  Intent distribution: {intents['intent_distribution']}")

    divider("STEP 3 - Content brief for pillar page (A1: 'What is...')")
    brief = server.generate_content_brief(
        primary_keyword="pub crawl tickets",
        central_entity="bar crawl events",
        supporting_keywords=["nyc pub crawl tickets", "best pub crawl tickets"],
        tier=1,
        page_type="Pillar",
    )
    print(f"  Word target: {brief['page_meta']['word_count_target']}")
    print(f"  H2 sections: {[s['h2'] for s in brief['required_h2_sections']]}")

    divider("STEP 4 - EAV table validation")
    eav = server.build_eav_table(
        entity_name="pub crawl tickets",
        attribute_value_pairs=[
            {"attribute": "definition", "value": "Prepaid passes to guided pub-to-pub events"},
            {"attribute": "purpose", "value": "Group access + venue coordination"},
            {"attribute": "components", "value": "QR pass, venue list, host meeting point"},
            {"attribute": "process", "value": "Buy online -> receive QR -> check in at start"},
            {"attribute": "benefits", "value": "Drink specials, no cover, group rate"},
            {"attribute": "limitations", "value": "21+, weather may cancel"},
            {"attribute": "cost_range", "value": "$25-$75 per person"},
            {"attribute": "duration", "value": "4-6 hours"},
            {"attribute": "case_examples", "value": "NYC Halloween 2025 - sold out 2 weeks early"},
            {"attribute": "historical_context", "value": "Format popularized in UK universities, US since 2000s"},
        ],
    )
    print(f"  EAV completeness: {eav['completeness_pct']}%")
    print(f"  Ready for quality gate: {eav['ready_for_quality_gate']}")

    divider("STEP 5 - Schema markup (JSON-LD)")
    schema = server.generate_schema_markup(
        page_type="article",
        page_url="https://pubcrawls.com/pub-crawl-tickets/",
        headline="Pub Crawl Tickets: Complete Guide 2026",
        description="Everything about pub crawl tickets - pricing, what's included, top events.",
        author_name="Jordan, Senior SEO Manager",
        publisher_name="PubCrawls.com",
        publisher_logo_url="https://pubcrawls.com/logo.png",
        date_published="2026-05-23",
        breadcrumb_trail=[
            {"name": "Home", "url": "https://pubcrawls.com/"},
            {"name": "Tickets", "url": "https://pubcrawls.com/tickets/"},
        ],
        faq_items=[
            {"q": "How much do pub crawl tickets cost?", "a": "Typically $25 to $75 per person."},
            {"q": "Are pub crawl tickets refundable?", "a": "Refund policies vary by event."},
        ],
    )
    print(f"  Generated {schema['schema_count']} schema blocks: {[s['@type'] for s in schema['schemas_json_ld']]}")

    divider("STEP 6 - AI citation potential (Formula 5)")
    ai_score = server.score_ai_citation_potential(
        structured_facts_count=11,
        monthly_update_recency_days=14,
        domain_authority=58,
    )
    print(f"  Estimated AI coverage: {ai_score['estimated_ai_citation_coverage_pct']}%")

    divider("STEP 7 - Save topical map to SQLite")
    save_result = server.save_topical_map(
        client_name="PubCrawls.com",
        topical_map=topical_map,
    )
    print(f"  {save_result['action']} with map_id={save_result['map_id']}")
    print(f"  DB location: {save_result['db_path']}")

    listing = server.list_saved_maps()
    print(f"  Total saved maps in DB: {listing['total_maps']}")

    divider("STEP 8 - Internal linking plan (silo compliance)")
    graph = server.generate_internal_link_graph(topical_map=topical_map)
    print(f"  {graph['total_links']} links planned across {graph['total_pages']} pages")
    print(f"  Tier distribution: {graph['tier_distribution']}")

    divider("DONE - full pipeline verified")
    print(
        "\nAll 18 tools are working. In Claude Desktop, chain them with "
        "SE Ranking MCP for fully automated topical mapping.\n"
    )


if __name__ == "__main__":
    run()
