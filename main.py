"""Google Photos Discovery Engine — CLI Entry Point.

Usage:
    python main.py collect     Run data collection only (Layer 1)
    python main.py analyze     Run analysis only (Layer 2)
    python main.py report      Generate report only (Layer 3)
    python main.py run         Run full pipeline end-to-end
    python main.py evidence    Search the evidence library
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from core.config import load_config
from core.logger import setup_logger


@click.group()
@click.option("--config", "config_dir", default="./config", help="Path to config directory.")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate without writing outputs.")
@click.option("--verbose", is_flag=True, default=False, help="Enable debug logging.")
@click.pass_context
def cli(ctx: click.Context, config_dir: str, dry_run: bool, verbose: bool) -> None:
    """Google Photos Discovery Engine — AI-powered user feedback analysis."""
    ctx.ensure_object(dict)

    # Load configuration
    app_config = load_config(config_dir)
    if dry_run:
        app_config.dry_run = True
    if verbose:
        app_config.log_level = "DEBUG"

    # Setup logger
    logger = setup_logger(
        log_level=app_config.log_level,
        log_dir=Path(app_config.data_dir) / "logs",
    )

    # Ensure data directories exist
    data_dir = Path(app_config.data_dir)
    for subdir in ["raw", "processed", "outputs", "logs", ".cache"]:
        (data_dir / subdir).mkdir(parents=True, exist_ok=True)

    ctx.obj["config"] = app_config
    ctx.obj["logger"] = logger


@cli.command()
@click.option("--sources", default=None, help="Comma-separated source filter (e.g., reddit,google_play).")
@click.pass_context
def collect(ctx: click.Context, sources: str | None) -> None:
    """Run data collection from configured public sources."""
    config = ctx.obj["config"]
    logger = ctx.obj["logger"]

    # Filter sources if specified
    source_filter = None
    if sources:
        source_filter = [s.strip() for s in sources.split(",")]

    logger.info(
        f"Starting collection (dry_run={config.dry_run})",
        extra={"stage": "collect"},
    )

    from collectors.factory import CollectorFactory
    from collectors.normalizer import DataNormalizer
    from collectors.deduplicator import Deduplicator

    factory = CollectorFactory(config.sources, config)
    normalizer = DataNormalizer()
    deduplicator = Deduplicator(cache_dir=Path(config.data_dir) / ".cache")

    total_collected = 0
    total_duplicates = 0
    sources_used = []

    for source_name, collector in factory.create_collectors(source_filter):
        logger.info(f"Collecting from {source_name}...", extra={"stage": "collect", "source_type": source_name})

        try:
            raw_records = collector.collect()
        except Exception as e:
            logger.error(f"Source {source_name} failed: {e}", extra={"stage": "collect", "source_type": source_name})
            continue

        # Normalize, deduplicate, and write
        output_path = Path(config.data_dir) / "raw" / f"{source_name}_{__import__('datetime').date.today().isoformat()}.jsonl"

        source_count = 0
        source_dupes = 0

        with open(output_path, "w", encoding="utf-8") as f:
            for raw in raw_records:
                try:
                    record = normalizer.normalize(raw, source_name)
                    if deduplicator.is_duplicate(record):
                        source_dupes += 1
                        continue
                    f.write(record.model_dump_json() + "\n")
                    source_count += 1
                except Exception as e:
                    logger.warning(f"Skipping record: {e}", extra={"stage": "normalizer"})

        total_collected += source_count
        total_duplicates += source_dupes
        sources_used.append(source_name)
        logger.info(
            f"Collected {source_count} records from {source_name} ({source_dupes} duplicates skipped)",
            extra={"stage": "collect", "source_type": source_name},
        )

    deduplicator.save_cache()

    click.echo(f"Collected {total_collected} records from {len(sources_used)} sources, {total_duplicates} duplicates skipped")
    logger.info(
        f"Collection complete: {total_collected} records from {len(sources_used)} sources",
        extra={"stage": "collect"},
    )


@cli.command()
@click.option("--limit", default=None, type=int, help="Limit number of records to analyze.")
@click.option("--input-dir", default=None, help="Directory containing raw .jsonl files.")
@click.option("--skip-clustering", is_flag=True, default=False, help="Skip BGE embedding clustering.")
@click.pass_context
def analyze(ctx: click.Context, limit: int | None, input_dir: str | None, skip_clustering: bool) -> None:
    """Run analysis pipeline: relevance filtering, failure categorization, and memory extraction."""
    import json
    from core.schemas import UnifiedRecord
    from core.llm_client import LLMClient
    from analysis.relevance_filter import RelevanceFilter
    from analysis.failure_categorizer import FailureCategorizer
    from analysis.memory_model_extractor import MemoryModelExtractor

    config = ctx.obj["config"]
    logger = ctx.obj["logger"]

    data_dir = Path(config.data_dir)
    raw_dir = Path(input_dir) if input_dir else data_dir / "raw"
    processed_dir = data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    raw_files = list(raw_dir.glob("*.jsonl"))
    if not raw_files:
        click.echo(f"No raw .jsonl files found in {raw_dir}. Run 'python main.py collect' first.")
        return

    # Load records
    all_records: list[UnifiedRecord] = []
    for rf in raw_files:
        with open(rf, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        all_records.append(UnifiedRecord.model_validate_json(line))
                    except Exception as e:
                        logger.warning(f"Failed to parse record in {rf.name}: {e}")

    if limit:
        all_records = all_records[:limit]

    total_records = len(all_records)
    click.echo(f"Loaded {total_records} raw records for analysis from {len(raw_files)} files.")
    logger.info(f"Starting analysis on {total_records} records", extra={"stage": "analyze"})

    llm = LLMClient()
    relevance_filter = RelevanceFilter(config.analysis, llm_client=llm)
    categorizer = FailureCategorizer(config.analysis, llm_client=llm)
    memory_extractor = MemoryModelExtractor(config.analysis, llm_client=llm)

    # -----------------------------------------------------------------------
    # Stage 2A: Relevance Filtering
    # -----------------------------------------------------------------------
    click.echo("\n--- Stage 2A: Relevance Filtering ---")
    relevant_items: list[tuple[UnifiedRecord, Any]] = []
    review_items: list[tuple[UnifiedRecord, Any]] = []
    discarded_items: list[tuple[UnifiedRecord, Any]] = []

    rel_file = open(processed_dir / "relevant.jsonl", "w", encoding="utf-8")
    rev_file = open(processed_dir / "review.jsonl", "w", encoding="utf-8")
    disc_file = open(processed_dir / "discarded.jsonl", "w", encoding="utf-8")

    try:
        with click.progressbar(all_records, label="Filtering relevance") as bar:
            for record in bar:
                res = relevance_filter.classify_record(record)
                decision = relevance_filter.evaluate_decision(res)

                out_dict = {
                    "record": record.model_dump(mode="json"),
                    "relevance": res.model_dump(mode="json"),
                }
                out_line = json.dumps(out_dict) + "\n"

                if decision == "relevant":
                    relevant_items.append((record, res))
                    rel_file.write(out_line)
                elif decision == "review":
                    review_items.append((record, res))
                    rev_file.write(out_line)
                else:
                    discarded_items.append((record, res))
                    disc_file.write(out_line)
    finally:
        rel_file.close()
        rev_file.close()
        disc_file.close()

    click.echo(
        f"Relevance Filtering Complete:\n"
        f"  * Relevant:  {len(relevant_items)} ({len(relevant_items)/total_records*100:.1f}%)\n"
        f"  * Review:    {len(review_items)}\n"
        f"  * Discarded: {len(discarded_items)}"
    )

    if not relevant_items:
        click.echo("No relevant retrieval records found. Analysis halted.")
        return

    # -----------------------------------------------------------------------
    # Stage 2B: Failure Categorization & Clustering
    # -----------------------------------------------------------------------
    click.echo("\n--- Stage 2B: Failure Categorization ---")
    categorized_items: list[tuple[UnifiedRecord, Any, Any]] = []
    cat_file = open(processed_dir / "categorized.jsonl", "w", encoding="utf-8")

    try:
        with click.progressbar(relevant_items, label="Categorizing failures") as bar:
            for record, rel_res in bar:
                cat_res = categorizer.categorize_record(record)
                categorized_items.append((record, rel_res, cat_res))

                out_dict = {
                    "record": record.model_dump(mode="json"),
                    "relevance": rel_res.model_dump(mode="json"),
                    "categorization": cat_res.model_dump(mode="json"),
                }
                cat_file.write(json.dumps(out_dict) + "\n")
    finally:
        cat_file.close()

    click.echo(f"Categorized {len(categorized_items)} relevant records.")

    # BGE Embedding Clustering
    if not skip_clustering and len(categorized_items) >= 3:
        click.echo("Generating BGE embeddings and clustering emergent failure modes...")
        cluster_info = categorizer.cluster_emergent_failures(
            [item[0] for item in categorized_items],
            [item[2] for item in categorized_items],
        )
        with open(processed_dir / "clusters.json", "w", encoding="utf-8") as cf:
            json.dump(cluster_info, cf, indent=2)
        click.echo(f"Discovered {cluster_info.get('num_clusters', 0)} emergent semantic clusters.")

    # -----------------------------------------------------------------------
    # Stage 2C: Memory Model Extraction
    # -----------------------------------------------------------------------
    click.echo("\n--- Stage 2C: Memory Model Extraction ---")
    analyzed_file = open(processed_dir / "analyzed.jsonl", "w", encoding="utf-8")
    enriched_records: list[Any] = []

    from core.schemas import EnrichedRecord

    try:
        with click.progressbar(categorized_items, label="Extracting memory models") as bar:
            for record, rel_res, cat_res in bar:
                mem_model = memory_extractor.extract_record(record)

                enriched = EnrichedRecord(
                    record=record,
                    relevance=rel_res,
                    categorization=cat_res,
                    memory_model=mem_model,
                )
                enriched_records.append(enriched)

                out_dict = {
                    "record": record.model_dump(mode="json"),
                    "relevance": rel_res.model_dump(mode="json"),
                    "categorization": cat_res.model_dump(mode="json"),
                    "memory_model": mem_model.model_dump(mode="json"),
                }
                analyzed_file.write(json.dumps(out_dict) + "\n")
    finally:
        analyzed_file.close()

    llm.close()

    # -----------------------------------------------------------------------
    # Stage 2D: Aggregation & Opportunity Ranking (Phase 3)
    # -----------------------------------------------------------------------
    click.echo("\n--- Stage 2D: Aggregation & Opportunity Ranking ---")
    from analysis.aggregator import Aggregator
    from reports.evidence_library import EvidenceLibrary

    aggregator = Aggregator(config.analysis)
    agg_result = aggregator.aggregate(
        enriched_records,
        total_collected=total_records,
        total_discarded=len(discarded_items),
    )

    # Save aggregation.json
    agg_path = processed_dir / "aggregation.json"
    with open(agg_path, "w", encoding="utf-8") as f:
        f.write(agg_result.model_dump_json(indent=2))

    # Build and export Evidence Library
    outputs_dir = data_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    evidence_lib = EvidenceLibrary()
    evidence_lib.build_from_records(enriched_records, aggregator=aggregator)
    evidence_lib.export_json(outputs_dir / "evidence_library.json")
    evidence_lib.export_csv(outputs_dir / "evidence_library.csv")

    click.echo(f"\nPhase 2 & 3 Complete!")
    click.echo(f"  * Aggregation saved:    {agg_path}")
    click.echo(f"  * Evidence CSV saved:   {outputs_dir / 'evidence_library.csv'}")
    click.echo(f"  * Evidence JSON saved:  {outputs_dir / 'evidence_library.json'}")

    # Display Top Opportunity Rankings
    click.echo("\nTop Opportunity Rankings:")
    for idx, cat in enumerate(agg_result.categories, 1):
        click.echo(
            f"  {idx}. {cat.category:<24} | Opp Score: {cat.opportunity_score:5.1f} "
            f"| Vol: {cat.volume_count:2d} ({cat.volume_percentage:4.1f}%) "
            f"| Sev: {cat.severity_score:4.1f}"
        )


@cli.command()
@click.pass_context
def report(ctx: click.Context) -> None:
    """Generate executive discovery report from analyzed data."""
    config = ctx.obj["config"]
    logger = ctx.obj["logger"]

    agg_path = Path(config.data_dir) / "processed" / "aggregation.json"
    if not agg_path.exists():
        click.echo(f"Aggregation file not found at {agg_path}. Run 'python main.py analyze' first.")
        return

    from reports.report_generator import ReportGenerator

    generator = ReportGenerator(config.report)
    out_file = generator.generate(aggregation_path=agg_path)
    logger.info(f"Generated report at {out_file}", extra={"stage": "report"})
    click.echo(f"\nReport successfully generated at:\n  * {out_file}\n  * {out_file.parent / 'discovery_report.md'}")


@cli.command()
@click.pass_context
def run(ctx: click.Context) -> None:
    """Run full pipeline: collect → analyze → report."""
    ctx.invoke(collect)
    ctx.invoke(analyze)
    ctx.invoke(report)


@cli.command()
@click.argument("query")
@click.option("--category", default=None, help="Filter by category.")
@click.option("--source", default=None, help="Filter by source type.")
@click.option("--min-severity", default=0.0, type=float, help="Minimum severity score (0-100).")
@click.option("--limit", default=5, type=int, help="Maximum quotes to return.")
@click.pass_context
def evidence(
    ctx: click.Context,
    query: str,
    category: str | None,
    source: str | None,
    min_severity: float,
    limit: int,
) -> None:
    """Search the evidence library for matching quotes."""
    from reports.evidence_library import EvidenceLibrary

    config = ctx.obj["config"]
    lib_path = Path(config.data_dir) / "outputs" / "evidence_library.json"

    if not lib_path.exists():
        click.echo(f"Evidence library not found at {lib_path}. Run 'python main.py analyze' first.")
        return

    import json
    with open(lib_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    lib = EvidenceLibrary()
    lib.entries = entries

    results = lib.search(
        query=query,
        category=category,
        source_type=source,
        min_severity=min_severity,
        limit=limit,
    )

    if not results:
        click.echo(f"No matching quotes found for '{query}'.")
        return

    click.echo(f"\nFound {len(results)} matching quotes for '{query}':\n" + "=" * 60)
    for idx, r in enumerate(results, 1):
        click.echo(f"\n[{idx}] Category: {r['category_primary']} | Severity: {r['severity_score']}/100 | Source: {r['source_type']}")
        if r.get("rating") and r["rating"] != "N/A":
            click.echo(f"    Rating: {'★' * int(r['rating'])}{'☆' * (5 - int(r['rating']))}")
        click.echo(f"    Failure: {r['failure_description']}")
        click.echo(f"    Quote:   \"{r['text'][:180]}...\"")
        if r.get("source_url"):
            click.echo(f"    URL:     {r['source_url']}")
        if r.get("remembered_summary"):
            click.echo(f"    Memory:  {r['remembered_summary'][:100]}")


if __name__ == "__main__":
    cli()
