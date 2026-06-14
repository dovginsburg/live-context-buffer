"""
Research Executor

Autonomously executes research proposals using Hermes tools.
Orchestrates web search, extraction, and analysis phases.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

# Import proposal generator
from proposal_generator import ProposalGenerator, ResearchProposal, ResearchPhase, ResearchType


@dataclass
class SearchResult:
    query: str
    url: str
    title: str
    snippet: str
    timestamp: str


@dataclass
class ExtractedContent:
    url: str
    title: str
    content: str
    word_count: int
    extraction_time: str
    error: Optional[str] = None


@dataclass
class PhaseResult:
    phase_id: str
    phase_name: str
    search_results: List[SearchResult]
    extracted_content: List[ExtractedContent]
    analysis: str
    insights: List[str]
    sources: List[str]
    duration_seconds: float
    status: str  # completed, partial, failed


@dataclass
class ResearchResult:
    proposal_id: str
    topic: str
    research_type: str
    started_at: str
    completed_at: Optional[str]
    status: str  # running, completed, failed
    phase_results: List[PhaseResult]
    executive_summary: str
    key_findings: List[str]
    recommendations: List[str]
    sources_cited: List[str]
    total_duration_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResearchExecutor:
    """Executes research proposals autonomously."""
    
    def __init__(self, results_dir: str = None):
        if results_dir is None:
            results_dir = Path.home() / "Projects" / "ezra" / "research-system" / "results"
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.proposal_generator = ProposalGenerator()
        
        # Track execution state
        self.current_proposal: Optional[ResearchProposal] = None
        self.current_result: Optional[ResearchResult] = None
    
    def execute_proposal(self, proposal_id: str) -> ResearchResult:
        """Execute a research proposal and return results."""
        
        # Load proposal
        proposal = self.proposal_generator.load_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        self.current_proposal = proposal
        
        # Initialize result
        result = ResearchResult(
            proposal_id=proposal_id,
            topic=proposal.topic,
            research_type=proposal.research_type.value,
            started_at=datetime.now().isoformat(),
            completed_at=None,
            status="running",
            phase_results=[],
            executive_summary="",
            key_findings=[],
            recommendations=[],
            sources_cited=[],
            total_duration_seconds=0,
            metadata={
                "target_audience": proposal.target_audience,
                "depth": proposal.metadata.get("depth", "standard")
            }
        )
        
        self.current_result = result
        
        # Update proposal status
        self.proposal_generator.update_proposal_status(proposal_id, "active")
        
        start_time = time.time()
        
        try:
            # Execute each phase
            for phase in proposal.phases:
                print(f"\n{'='*60}")
                print(f"Executing Phase {phase.id}: {phase.name}")
                print(f"{'='*60}")
                
                phase_result = self._execute_phase(phase)
                result.phase_results.append(phase_result)
                
                print(f"Phase completed in {phase_result.duration_seconds:.1f}s")
                print(f"Status: {phase_result.status}")
                print(f"Sources found: {len(phase_result.extracted_content)}")
            
            # Generate executive summary
            result.executive_summary = self._generate_executive_summary()
            result.key_findings = self._extract_key_findings()
            result.recommendations = self._generate_recommendations()
            result.sources_cited = self._collect_all_sources()
            
            result.status = "completed"
            result.completed_at = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - start_time
            
            # Update proposal status
            self.proposal_generator.update_proposal_status(proposal_id, "completed")
            
            # Save results
            self._save_result(result)
            
            print(f"\n{'='*60}")
            print(f"Research Completed Successfully!")
            print(f"Total Duration: {result.total_duration_seconds:.1f}s")
            print(f"Sources Cited: {len(result.sources_cited)}")
            print(f"{'='*60}")
            
        except Exception as e:
            result.status = "failed"
            result.completed_at = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - start_time
            result.metadata["error"] = str(e)
            
            self.proposal_generator.update_proposal_status(proposal_id, "failed")
            self._save_result(result)
            
            print(f"\n❌ Research failed: {e}")
            raise
        
        return result
    
    def _execute_phase(self, phase: ResearchPhase) -> PhaseResult:
        """Execute a single research phase."""
        
        start_time = time.time()
        search_results = []
        extracted_content = []
        all_insights = []
        all_sources = []
        
        try:
            # Step 1: Execute search queries
            print(f"\nExecuting {len(phase.search_queries)} search queries...")
            for query in phase.search_queries:
                print(f"  Searching: {query}")
                results = self._search(query)
                search_results.extend(results)
                print(f"    Found {len(results)} results")
            
            # Step 2: Extract content from URLs
            print(f"\nExtracting content from {len(phase.extraction_urls)} URLs...")
            urls_to_extract = list(set([r.url for r in search_results[:5]] + phase.extraction_urls[:3]))
            
            for url in urls_to_extract[:5]:  # Limit to 5 extractions
                print(f"  Extracting: {url}")
                content = self._extract_content(url)
                if content:
                    extracted_content.append(content)
                    all_sources.append(url)
                    print(f"    Extracted {content.word_count} words")
            
            # Step 3: Analyze content
            print(f"\nAnalyzing extracted content...")
            analysis = self._analyze_content(
                phase=phase,
                search_results=search_results,
                extracted_content=extracted_content
            )
            
            # Step 4: Extract insights
            insights = self._extract_insights(analysis, extracted_content)
            all_insights.extend(insights)
            
            duration = time.time() - start_time
            
            return PhaseResult(
                phase_id=phase.id,
                phase_name=phase.name,
                search_results=search_results,
                extracted_content=extracted_content,
                analysis=analysis,
                insights=insights,
                sources=all_sources,
                duration_seconds=duration,
                status="completed"
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return PhaseResult(
                phase_id=phase.id,
                phase_name=phase.name,
                search_results=search_results,
                extracted_content=extracted_content,
                analysis=f"Phase failed: {str(e)}",
                insights=[],
                sources=all_sources,
                duration_seconds=duration,
                status="failed"
            )
    
    def _search(self, query: str) -> List[SearchResult]:
        """Execute a web search and return results."""
        # This will be called via execute_code with hermes_tools
        # For now, return placeholder structure
        return []
    
    def _extract_content(self, url: str) -> Optional[ExtractedContent]:
        """Extract content from a URL."""
        # This will be called via execute_code with hermes_tools
        # For now, return placeholder structure
        return None
    
    def _analyze_content(
        self,
        phase: ResearchPhase,
        search_results: List[SearchResult],
        extracted_content: List[ExtractedContent]
    ) -> str:
        """Analyze extracted content and generate insights."""
        # This will use LLM analysis via execute_code
        # For now, return placeholder
        return "Analysis pending..."
    
    def _extract_insights(self, analysis: str, content: List[ExtractedContent]) -> List[str]:
        """Extract key insights from analysis."""
        # This will use LLM extraction via execute_code
        return ["Insight extraction pending..."]
    
    def _generate_executive_summary(self) -> str:
        """Generate executive summary from all phase results."""
        if not self.current_result or not self.current_result.phase_results:
            return "No data to summarize."
        
        summary_parts = []
        summary_parts.append(f"Research on: {self.current_result.topic}")
        summary_parts.append(f"Research Type: {self.current_result.research_type}")
        summary_parts.append(f"Phases Completed: {len(self.current_result.phase_results)}")
        summary_parts.append(f"Total Sources: {len(self.current_result.sources_cited)}")
        
        return "\n".join(summary_parts)
    
    def _extract_key_findings(self) -> List[str]:
        """Extract key findings from all phase results."""
        findings = []
        
        if self.current_result:
            for phase_result in self.current_result.phase_results:
                findings.extend(phase_result.insights)
        
        return findings[:10]  # Limit to top 10 findings
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on findings."""
        # This will use LLM generation via execute_code
        return ["Recommendations pending analysis..."]
    
    def _collect_all_sources(self) -> List[str]:
        """Collect all unique sources cited."""
        sources = set()
        
        if self.current_result:
            for phase_result in self.current_result.phase_results:
                sources.update(phase_result.sources)
        
        return sorted(list(sources))
    
    def _save_result(self, result: ResearchResult):
        """Save research results to disk."""
        result_file = self.results_dir / f"{result.proposal_id}.json"
        
        # Convert to dict for JSON serialization
        data = {
            "proposal_id": result.proposal_id,
            "topic": result.topic,
            "research_type": result.research_type,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "status": result.status,
            "phase_results": [asdict(pr) for pr in result.phase_results],
            "executive_summary": result.executive_summary,
            "key_findings": result.key_findings,
            "recommendations": result.recommendations,
            "sources_cited": result.sources_cited,
            "total_duration_seconds": result.total_duration_seconds,
            "metadata": result.metadata
        }
        
        with open(result_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\nResults saved to: {result_file}")
    
    def load_result(self, proposal_id: str) -> Optional[ResearchResult]:
        """Load research results from disk."""
        result_file = self.results_dir / f"{proposal_id}.json"
        
        if not result_file.exists():
            return None
        
        with open(result_file, 'r') as f:
            data = json.load(f)
        
        # Reconstruct phase results
        phase_results = []
        for pr_data in data.get("phase_results", []):
            phase_results.append(PhaseResult(**pr_data))
        
        return ResearchResult(
            proposal_id=data["proposal_id"],
            topic=data["topic"],
            research_type=data["research_type"],
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            status=data["status"],
            phase_results=phase_results,
            executive_summary=data.get("executive_summary", ""),
            key_findings=data.get("key_findings", []),
            recommendations=data.get("recommendations", []),
            sources_cited=data.get("sources_cited", []),
            total_duration_seconds=data.get("total_duration_seconds", 0),
            metadata=data.get("metadata", {})
        )
    
    def list_results(self) -> List[Dict]:
        """List all completed research results."""
        results = []
        
        for result_file in self.results_dir.glob("*.json"):
            with open(result_file, 'r') as f:
                data = json.load(f)
            
            results.append({
                "proposal_id": data["proposal_id"],
                "topic": data["topic"],
                "type": data["research_type"],
                "status": data["status"],
                "completed_at": data.get("completed_at"),
                "duration": data.get("total_duration_seconds", 0),
                "sources": len(data.get("sources_cited", []))
            })
        
        return sorted(results, key=lambda x: x.get("completed_at", ""), reverse=True)


def execute_proposal_cli(proposal_id: str):
    """CLI wrapper for proposal execution."""
    executor = ResearchExecutor()
    
    print(f"\n🚀 Starting Research Execution")
    print(f"Proposal ID: {proposal_id}")
    
    result = executor.execute_proposal(proposal_id)
    
    print(f"\n📊 Executive Summary:")
    print(result.executive_summary)
    
    print(f"\n🔑 Key Findings:")
    for i, finding in enumerate(result.key_findings, 1):
        print(f"  {i}. {finding}")
    
    print(f"\n📚 Sources Cited ({len(result.sources_cited)}):")
    for source in result.sources_cited[:10]:
        print(f"  • {source}")
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python research_executor.py <proposal_id>")
        sys.exit(1)
    
    proposal_id = sys.argv[1]
    execute_proposal_cli(proposal_id)