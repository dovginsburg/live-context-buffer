"""
Results Manager

Provides interfaces for viewing, searching, and managing research results.
Supports multiple output formats: terminal, markdown, HTML.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from research_executor import ResearchExecutor, ResearchResult


@dataclass
class ResultSummary:
    proposal_id: str
    topic: str
    research_type: str
    status: str
    completed_at: Optional[str]
    duration_minutes: float
    sources_count: int
    key_findings_count: int
    has_executive_summary: bool


class ResultsManager:
    """Manages and displays research results."""
    
    def __init__(self, results_dir: str = None):
        if results_dir is None:
            results_dir = Path.home() / "Projects" / "ezra" / "research-system" / "results"
        self.results_dir = Path(results_dir)
        self.executor = ResearchExecutor(results_dir)
    
    def list_results(self, status: str = None) -> List[ResultSummary]:
        """List all results with summary info."""
        summaries = []
        
        for result_file in self.results_dir.glob("*.json"):
            with open(result_file, 'r') as f:
                data = json.load(f)
            
            if status and data.get("status") != status:
                continue
            
            summaries.append(ResultSummary(
                proposal_id=data["proposal_id"],
                topic=data["topic"],
                research_type=data["research_type"],
                status=data["status"],
                completed_at=data.get("completed_at"),
                duration_minutes=data.get("total_duration_seconds", 0) / 60,
                sources_count=len(data.get("sources_cited", [])),
                key_findings_count=len(data.get("key_findings", [])),
                has_executive_summary=bool(data.get("executive_summary"))
            ))
        
        return sorted(summaries, key=lambda x: x.completed_at or "", reverse=True)
    
    def get_result(self, proposal_id: str) -> Optional[ResearchResult]:
        """Get full result details."""
        return self.executor.load_result(proposal_id)
    
    def format_terminal(self, result: ResearchResult) -> str:
        """Format result for terminal display."""
        lines = []
        
        lines.append("=" * 70)
        lines.append(f"RESEARCH RESULTS: {result.topic}")
        lines.append("=" * 70)
        lines.append("")
        
        # Basic info
        lines.append(f"Proposal ID: {result.proposal_id}")
        lines.append(f"Research Type: {result.research_type}")
        lines.append(f"Status: {result.status}")
        lines.append(f"Duration: {result.total_duration_seconds / 60:.1f} minutes")
        lines.append(f"Sources Cited: {len(result.sources_cited)}")
        lines.append("")
        
        # Executive Summary
        if result.executive_summary:
            lines.append("-" * 70)
            lines.append("EXECUTIVE SUMMARY")
            lines.append("-" * 70)
            lines.append(result.executive_summary)
            lines.append("")
        
        # Key Findings
        if result.key_findings:
            lines.append("-" * 70)
            lines.append("KEY FINDINGS")
            lines.append("-" * 70)
            for i, finding in enumerate(result.key_findings, 1):
                lines.append(f"{i}. {finding}")
            lines.append("")
        
        # Phase Results
        lines.append("-" * 70)
        lines.append("PHASE BREAKDOWN")
        lines.append("-" * 70)
        for phase in result.phase_results:
            lines.append(f"\n  Phase: {phase.phase_name}")
            lines.append(f"  Status: {phase.status}")
            lines.append(f"  Duration: {phase.duration_seconds:.1f}s")
            lines.append(f"  Sources: {len(phase.extracted_content)}")
            if phase.insights:
                lines.append(f"  Insights:")
                for insight in phase.insights[:3]:
                    lines.append(f"    • {insight}")
        
        # Sources
        if result.sources_cited:
            lines.append("")
            lines.append("-" * 70)
            lines.append("SOURCES CITED")
            lines.append("-" * 70)
            for source in result.sources_cited:
                lines.append(f"• {source}")
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def format_markdown(self, result: ResearchResult) -> str:
        """Format result as markdown."""
        lines = []
        
        lines.append(f"# Research Results: {result.topic}")
        lines.append("")
        lines.append(f"**Proposal ID:** {result.proposal_id}")
        lines.append(f"**Research Type:** {result.research_type}")
        lines.append(f"**Status:** {result.status}")
        lines.append(f"**Duration:** {result.total_duration_seconds / 60:.1f} minutes")
        lines.append(f"**Sources Cited:** {len(result.sources_cited)}")
        lines.append("")
        
        if result.executive_summary:
            lines.append("## Executive Summary")
            lines.append("")
            lines.append(result.executive_summary)
            lines.append("")
        
        if result.key_findings:
            lines.append("## Key Findings")
            lines.append("")
            for i, finding in enumerate(result.key_findings, 1):
                lines.append(f"{i}. {finding}")
            lines.append("")
        
        if result.recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for rec in result.recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        lines.append("## Phase Breakdown")
        lines.append("")
        for phase in result.phase_results:
            lines.append(f"### {phase.phase_name}")
            lines.append(f"- **Status:** {phase.status}")
            lines.append(f"- **Duration:** {phase.duration_seconds:.1f}s")
            lines.append(f"- **Sources:** {len(phase.extracted_content)}")
            if phase.analysis:
                lines.append(f"- **Analysis:** {phase.analysis[:200]}...")
            lines.append("")
        
        if result.sources_cited:
            lines.append("## Sources")
            lines.append("")
            for source in result.sources_cited:
                lines.append(f"- [{source}]({source})")
            lines.append("")
        
        return "\n".join(lines)
    
    def format_html(self, result: ResearchResult) -> str:
        """Format result as HTML."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Results: {result.topic}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .container {{ background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #007AFF; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .meta {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        .meta span {{ margin-right: 20px; }}
        .finding {{ background: #f0f7ff; padding: 10px 15px; border-left: 3px solid #007AFF; margin: 10px 0; border-radius: 0 4px 4px 0; }}
        .phase {{ background: #fafafa; padding: 15px; border-radius: 6px; margin: 10px 0; }}
        .phase h3 {{ margin-top: 0; color: #333; }}
        .sources {{ font-size: 12px; color: #888; }}
        .sources a {{ color: #007AFF; text-decoration: none; }}
        .sources a:hover {{ text-decoration: underline; }}
        .status {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
        .status.completed {{ background: #d4edda; color: #155724; }}
        .status.failed {{ background: #f8d7da; color: #721c24; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Research Results: {result.topic}</h1>
        
        <div class="meta">
            <span><strong>Proposal ID:</strong> {result.proposal_id}</span>
            <span><strong>Type:</strong> {result.research_type}</span>
            <span><strong>Status:</strong> <span class="status {result.status}">{result.status}</span></span>
            <span><strong>Duration:</strong> {result.total_duration_seconds / 60:.1f} min</span>
        </div>
        
        <div class="meta">
            <span><strong>Sources Cited:</strong> {len(result.sources_cited)}</span>
        </div>
"""
        
        if result.executive_summary:
            html += f"""
        <h2>Executive Summary</h2>
        <p>{result.executive_summary}</p>
"""
        
        if result.key_findings:
            html += """
        <h2>Key Findings</h2>
"""
            for i, finding in enumerate(result.key_findings, 1):
                html += f'        <div class="finding"><strong>{i}.</strong> {finding}</div>\n'
        
        if result.recommendations:
            html += """
        <h2>Recommendations</h2>
        <ul>
"""
            for rec in result.recommendations:
                html += f"            <li>{rec}</li>\n"
            html += "        </ul>\n"
        
        html += """
        <h2>Phase Breakdown</h2>
"""
        for phase in result.phase_results:
            html += f"""
        <div class="phase">
            <h3>{phase.phase_name}</h3>
            <p><strong>Status:</strong> {phase.status} | <strong>Duration:</strong> {phase.duration_seconds:.1f}s | <strong>Sources:</strong> {len(phase.extracted_content)}</p>
        </div>
"""
        
        if result.sources_cited:
            html += """
        <h2>Sources</h2>
        <div class="sources">
"""
            for source in result.sources_cited:
                html += f'            <div>• <a href="{source}" target="_blank">{source}</a></div>\n'
            html += "        </div>\n"
        
        html += """
    </div>
</body>
</html>
"""
        return html
    
    def export_result(self, proposal_id: str, format: str = "markdown") -> str:
        """Export result in specified format."""
        result = self.get_result(proposal_id)
        if not result:
            raise ValueError(f"Result {proposal_id} not found")
        
        if format == "markdown":
            return self.format_markdown(result)
        elif format == "html":
            return self.format_html(result)
        elif format == "terminal":
            return self.format_terminal(result)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def save_export(self, proposal_id: str, format: str = "markdown") -> Path:
        """Export and save result to file."""
        content = self.export_result(proposal_id, format)
        
        # Determine file extension
        ext_map = {"markdown": ".md", "html": ".html", "terminal": ".txt"}
        ext = ext_map.get(format, ".txt")
        
        # Get topic for filename
        result = self.get_result(proposal_id)
        topic_slug = result.topic.lower().replace(" ", "_")[:30]
        filename = f"{proposal_id}_{topic_slug}{ext}"
        
        # Save to results directory
        filepath = self.results_dir / filename
        with open(filepath, 'w') as f:
            f.write(content)
        
        return filepath
    
    def search_results(self, query: str) -> List[ResultSummary]:
        """Search results by topic or content."""
        all_results = self.list_results()
        matching = []
        
        query_lower = query.lower()
        for result in all_results:
            if query_lower in result.topic.lower():
                matching.append(result)
                continue
            
            # Also search in key findings if available
            full_result = self.get_result(result.proposal_id)
            if full_result:
                for finding in full_result.key_findings:
                    if query_lower in finding.lower():
                        matching.append(result)
                        break
        
        return matching
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregate statistics across all results."""
        results = self.list_results()
        
        stats = {
            "total_research": len(results),
            "completed": len([r for r in results if r.status == "completed"]),
            "failed": len([r for r in results if r.status == "failed"]),
            "total_sources": sum(r.sources_count for r in results),
            "total_duration_minutes": sum(r.duration_minutes for r in results),
            "avg_duration_minutes": 0,
            "by_type": {}
        }
        
        if results:
            stats["avg_duration_minutes"] = stats["total_duration_minutes"] / len(results)
        
        # Group by type
        for result in results:
            if result.research_type not in stats["by_type"]:
                stats["by_type"][result.research_type] = 0
            stats["by_type"][result.research_type] += 1
        
        return stats


def print_results_list(manager: ResultsManager):
    """Print formatted list of all results."""
    results = manager.list_results()
    
    if not results:
        print("\n📭 No research results found.")
        return
    
    print(f"\n📊 Research Results ({len(results)} total)")
    print("=" * 70)
    
    for r in results:
        status_icon = "✅" if r.status == "completed" else "❌"
        print(f"{status_icon} {r.proposal_id} | {r.topic[:40]}")
        print(f"   Type: {r.research_type} | Duration: {r.duration_minutes:.1f}min | Sources: {r.sources_count}")
        if r.completed_at:
            print(f"   Completed: {r.completed_at[:19]}")
        print()
    
    print("=" * 70)


def print_result_detail(manager: ResultsManager, proposal_id: str):
    """Print detailed result view."""
    result = manager.get_result(proposal_id)
    if not result:
        print(f"\n❌ Result {proposal_id} not found.")
        return
    
    print(manager.format_terminal(result))


def export_result_to_file(manager: ResultsManager, proposal_id: str, format: str = "markdown"):
    """Export result to file and print path."""
    try:
        filepath = manager.save_export(proposal_id, format)
        print(f"\n✅ Exported to: {filepath}")
        return filepath
    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        return None


if __name__ == "__main__":
    import sys
    
    manager = ResultsManager()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python results_manager.py list                    - List all results")
        print("  python results_manager.py detail <proposal_id>   - Show result details")
        print("  python results_manager.py export <proposal_id> [format] - Export result")
        print("  python results_manager.py search <query>         - Search results")
        print("  python results_manager.py stats                  - Show statistics")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        print_results_list(manager)
    
    elif command == "detail":
        if len(sys.argv) < 3:
            print("Usage: python results_manager.py detail <proposal_id>")
            sys.exit(1)
        print_result_detail(manager, sys.argv[2])
    
    elif command == "export":
        if len(sys.argv) < 3:
            print("Usage: python results_manager.py export <proposal_id> [markdown|html|terminal]")
            sys.exit(1)
        fmt = sys.argv[3] if len(sys.argv) > 3 else "markdown"
        export_result_to_file(manager, sys.argv[2], fmt)
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python results_manager.py search <query>")
            sys.exit(1)
        results = manager.search_results(sys.argv[2])
        if results:
            print(f"\n🔍 Found {len(results)} matching results:")
            for r in results:
                print(f"  • {r.proposal_id}: {r.topic}")
        else:
            print("\n📭 No matching results found.")
    
    elif command == "stats":
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
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)