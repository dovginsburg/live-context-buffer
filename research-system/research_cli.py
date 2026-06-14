#!/usr/bin/env python3
"""
Research System CLI

Unified command-line interface for the research proposal system.

Usage:
    python research_cli.py create <topic> [type] [depth]   - Create a research proposal
    python research_cli.py list                             - List all proposals
    python research_cli.py execute <proposal_id>            - Execute a research proposal
    python research_cli.py results list                     - List all results
    python research_cli.py results detail <proposal_id>     - View result details
    python research_cli.py results export <id> [format]     - Export result (markdown/html)
    python research_cli.py results search <query>           - Search results
    python research_cli.py stats                            - View statistics
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1]
    
    if command == "create":
        handle_create()
    elif command == "list":
        handle_list()
    elif command == "execute":
        handle_execute()
    elif command == "results":
        handle_results()
    elif command == "stats":
        handle_stats()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


def handle_create():
    """Create a new research proposal."""
    if len(sys.argv) < 3:
        print("Usage: python research_cli.py create <topic> [research_type] [depth]")
        print("\nResearch Types:")
        print("  literature_review     - Survey academic and industry literature")
        print("  market_analysis       - Analyze market size, trends, players")
        print("  technical_deep_dive   - Deep technical exploration")
        print("  competitive_analysis  - Compare competitors and positioning")
        print("  trend_analysis        - Identify and validate trends")
        print("\nDepth:")
        print("  light    - Quick overview (1-2 phases)")
        print("  standard - Comprehensive (2-3 phases)")
        print("  deep     - Exhaustive (3-4 phases)")
        return
    
    topic = sys.argv[2]
    research_type = sys.argv[3] if len(sys.argv) > 3 else "literature_review"
    depth = sys.argv[4] if len(sys.argv) > 4 else "standard"
    
    from scripts.proposal_generator import generate_proposal_cli
    generate_proposal_cli(topic, research_type, depth)


def handle_list():
    """List all proposals."""
    from scripts.proposal_generator import ProposalGenerator
    
    generator = ProposalGenerator()
    proposals = generator.list_proposals()
    
    if not proposals:
        print("\n📭 No proposals found. Create one with:")
        print("  python research_cli.py create <topic>")
        return
    
    print(f"\n📋 Research Proposals ({len(proposals)} total)")
    print("=" * 70)
    
    for p in proposals:
        status_icon = {"draft": "📝", "active": "🔄", "completed": "✅", "failed": "❌"}.get(p["status"], "❓")
        print(f"{status_icon} {p['id']} | {p['topic'][:40]}")
        print(f"   Type: {p['type']} | Status: {p['status']} | Phases: {p['phases']}")
        print(f"   Created: {p['created_at'][:19]}")
        print()


def handle_execute():
    """Execute a research proposal."""
    if len(sys.argv) < 3:
        print("Usage: python research_cli.py execute <proposal_id>")
        print("\nList proposals with: python research_cli.py list")
        return
    
    proposal_id = sys.argv[2]
    
    print(f"\n🚀 Executing Research Proposal: {proposal_id}")
    print("This will use Hermes tools to search and extract content.")
    print("This may take several minutes...\n")
    
    # Use execute_code via hermes_tools
    from scripts.hermes_executor import run_research
    result = run_research(proposal_id)
    
    if result:
        print(f"\n✅ Research completed successfully!")
        print(f"View results with: python research_cli.py results detail {proposal_id}")


def handle_results():
    """Handle results subcommands."""
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python research_cli.py results list                 - List all results")
        print("  python research_cli.py results detail <proposal_id> - View result details")
        print("  python research_cli.py results export <id> [format] - Export result")
        print("  python research_cli.py results search <query>       - Search results")
        return
    
    subcommand = sys.argv[2]
    
    from scripts.results_manager import (
        ResultsManager, print_results_list, print_result_detail, export_result_to_file
    )
    
    manager = ResultsManager()
    
    if subcommand == "list":
        print_results_list(manager)
    
    elif subcommand == "detail":
        if len(sys.argv) < 4:
            print("Usage: python research_cli.py results detail <proposal_id>")
            return
        print_result_detail(manager, sys.argv[3])
    
    elif subcommand == "export":
        if len(sys.argv) < 4:
            print("Usage: python research_cli.py results export <proposal_id> [markdown|html]")
            return
        fmt = sys.argv[4] if len(sys.argv) > 4 else "markdown"
        export_result_to_file(manager, sys.argv[3], fmt)
    
    elif subcommand == "search":
        if len(sys.argv) < 4:
            print("Usage: python research_cli.py results search <query>")
            return
        results = manager.search_results(sys.argv[3])
        if results:
            print(f"\n🔍 Found {len(results)} matching results:")
            for r in results:
                print(f"  • {r.proposal_id}: {r.topic}")
        else:
            print("\n📭 No matching results found.")
    
    else:
        print(f"Unknown subcommand: {subcommand}")


def handle_stats():
    """Show statistics."""
    from scripts.results_manager import ResultsManager
    
    manager = ResultsManager()
    stats = manager.get_statistics()
    
    print("\n📈 Research Statistics")
    print("=" * 40)
    print(f"Total Research: {stats['total_research']}")
    print(f"Completed: {stats['completed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total Sources: {stats['total_sources']}")
    print(f"Avg Duration: {stats['avg_duration_minutes']:.1f} min")
    
    if stats['by_type']:
        print("\nBy Type:")
        for rtype, count in stats['by_type'].items():
            print(f"  {rtype}: {count}")


if __name__ == "__main__":
    main()