"""
Hermes Research Executor

Actual executor that uses Hermes tools for web search and extraction.
This module is designed to be run via execute_code with hermes_tools.
"""

import json
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))


def run_research(proposal_id: str):
    """Execute research using Hermes tools."""
    from hermes_tools import web_search, web_extract
    from proposal_generator import ProposalGenerator
    from research_executor import ResearchExecutor, SearchResult, ExtractedContent
    
    # Load proposal
    generator = ProposalGenerator()
    proposal = generator.load_proposal(proposal_id)
    
    if not proposal:
        print(f"❌ Proposal {proposal_id} not found")
        return None
    
    print(f"\n🚀 Starting Research: {proposal.topic}")
    print(f"Type: {proposal.research_type.value}")
    print(f"Phases: {len(proposal.phases)}")
    
    all_results = []
    all_sources = []
    
    # Execute each phase
    for phase in proposal.phases:
        print(f"\n{'='*60}")
        print(f"Phase: {phase.name}")
        print(f"{'='*60}")
        
        phase_search_results = []
        phase_extracted_content = []
        
        # Execute search queries
        for query in phase.search_queries:
            print(f"\n🔍 Searching: {query}")
            search_data = web_search(query, limit=5)
            
            if search_data and "data" in search_data and "web" in search_data["data"]:
                for item in search_data["data"]["web"]:
                    result = SearchResult(
                        query=query,
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        snippet=item.get("description", ""),
                        timestamp=""
                    )
                    phase_search_results.append(result)
                    print(f"  ✓ {item.get('title', 'Untitled')[:60]}")
        
        # Extract content from top URLs
        urls_to_extract = list(set([r.url for r in phase_search_results[:3]]))
        
        if urls_to_extract:
            print(f"\n📄 Extracting content from {len(urls_to_extract)} URLs...")
            extraction_data = web_extract(urls_to_extract[:3])
            
            if extraction_data and "results" in extraction_data:
                for result in extraction_data["results"]:
                    if result.get("content") and not result.get("error"):
                        content = ExtractedContent(
                            url=result.get("url", ""),
                            title=result.get("title", "Untitled"),
                            content=result.get("content", "")[:5000],  # Limit content length
                            word_count=len(result.get("content", "").split()),
                            extraction_time=""
                        )
                        phase_extracted_content.append(content)
                        all_sources.append(result.get("url", ""))
                        print(f"  ✓ {content.title[:50]} ({content.word_count} words)")
                    elif result.get("error"):
                        print(f"  ⚠️ Failed to extract {result.get('url', 'URL')}: {result.get('error')}")
        
        # Combine phase results
        phase_result = {
            "phase_id": phase.id,
            "phase_name": phase.name,
            "search_results": [vars(r) for r in phase_search_results],
            "extracted_content": [vars(c) for c in phase_extracted_content],
            "insights": [],  # Will be filled by analysis
            "sources": [c.url for c in phase_extracted_content]
        }
        
        all_results.append(phase_result)
        
        print(f"\n✅ Phase Complete:")
        print(f"   Search Results: {len(phase_search_results)}")
        print(f"   Content Extracted: {len(phase_extracted_content)}")
    
    # Generate summary
    print(f"\n{'='*60}")
    print(f"Research Complete!")
    print(f"{'='*60}")
    print(f"Total Sources: {len(all_sources)}")
    print(f"Total Phases: {len(all_results)}")
    
    # Return structured results
    return {
        "proposal_id": proposal_id,
        "topic": proposal.topic,
        "research_type": proposal.research_type.value,
        "phase_results": all_results,
        "sources": all_sources,
        "summary": f"Completed research on {proposal.topic} with {len(all_sources)} sources."
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hermes_executor.py <proposal_id>")
        sys.exit(1)
    
    result = run_research(sys.argv[1])
    if result:
        print(json.dumps(result, indent=2))