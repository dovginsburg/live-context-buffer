"""
Research Proposal Generator

Generates structured research proposals from topic specifications.
Supports multiple research types: literature review, market analysis,
technical deep-dive, competitive analysis, trend analysis.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class ResearchType(Enum):
    LITERATURE_REVIEW = "literature_review"
    MARKET_ANALYSIS = "market_analysis"
    TECHNICAL_DEEP_DIVE = "technical_deep_dive"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    TREND_ANALYSIS = "trend_analysis"
    CUSTOM = "custom"


@dataclass
class ResearchPhase:
    id: str
    name: str
    description: str
    search_queries: List[str]
    extraction_urls: List[str]
    analysis_tasks: List[str]
    estimated_duration_minutes: int
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class ResearchProposal:
    id: str
    topic: str
    research_type: ResearchType
    created_at: str
    status: str  # draft, active, completed, failed
    phases: List[ResearchPhase]
    metadata: Dict[str, Any]
    estimated_total_minutes: int
    target_audience: str = "general"
    key_questions: List[str] = None
    success_criteria: List[str] = None
    
    def __post_init__(self):
        if self.key_questions is None:
            self.key_questions = []
        if self.success_criteria is None:
            self.success_criteria = []


class ProposalGenerator:
    """Generates research proposals from topic specifications."""
    
    def __init__(self, proposals_dir: str = None):
        if proposals_dir is None:
            proposals_dir = Path.home() / "Projects" / "ezra" / "research-system" / "proposals"
        self.proposals_dir = Path(proposals_dir)
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        
        # Load template library
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict]:
        """Load research phase templates for different research types."""
        return {
            ResearchType.LITERATURE_REVIEW.value: {
                "phases": [
                    {
                        "name": "Initial Survey",
                        "description": "Broad search to understand the landscape",
                        "query_pattern": "{topic} overview review",
                        "url_patterns": ["scholar.google.com", "arxiv.org", "pubmed.ncbi.nlm.nih.gov"],
                        "analysis": ["Identify key themes", "Map major contributors", "Find seminal papers"]
                    },
                    {
                        "name": "Deep Dive",
                        "description": "Targeted search on specific subtopics",
                        "query_pattern": "{topic} detailed analysis research",
                        "url_patterns": ["semanticscholar.org", "researchgate.net"],
                        "analysis": ["Extract methodologies", "Compare findings", "Identify gaps"]
                    },
                    {
                        "name": "Synthesis",
                        "description": "Integrate findings into coherent narrative",
                        "query_pattern": "{topic} meta-analysis systematic review",
                        "url_patterns": [],
                        "analysis": ["Create evidence matrix", "Identify consensus", "Highlight debates"]
                    }
                ],
                "key_questions": [
                    "What is the current state of research on {topic}?",
                    "What are the major findings and methodologies?",
                    "What gaps exist in the literature?",
                    "What are the promising future directions?"
                ]
            },
            ResearchType.MARKET_ANALYSIS.value: {
                "phases": [
                    {
                        "name": "Market Overview",
                        "description": "Understand market size, growth, and key players",
                        "query_pattern": "{topic} market size growth 2024 2025",
                        "url_patterns": ["statista.com", "grandviewresearch.com", "marketsandmarkets.com"],
                        "analysis": ["Estimate market size", "Identify growth drivers", "Map competitive landscape"]
                    },
                    {
                        "name": "Competitive Intelligence",
                        "description": "Deep dive into competitors and positioning",
                        "query_pattern": "{topic} competitors market share top companies",
                        "url_patterns": ["crunchbase.com", "cbinsights.com", "g2.com"],
                        "analysis": ["Profile top 5-10 players", "Compare offerings", "Identify differentiators"]
                    },
                    {
                        "name": "Trend Analysis",
                        "description": "Identify emerging trends and opportunities",
                        "query_pattern": "{topic} trends future predictions 2025 2026",
                        "url_patterns": ["mckinsey.com", "bcg.com", "deloitte.com"],
                        "analysis": ["Map technology trends", "Identify adoption patterns", "Spot white spaces"]
                    }
                ],
                "key_questions": [
                    "What is the current market size and growth trajectory?",
                    "Who are the key players and what are their positions?",
                    "What trends are shaping the market?",
                    "Where are the opportunities for new entrants?"
                ]
            },
            ResearchType.TECHNICAL_DEEP_DIVE.value: {
                "phases": [
                    {
                        "name": "Technical Landscape",
                        "description": "Map the technical architecture and components",
                        "query_pattern": "{topic} architecture system design technical",
                        "url_patterns": ["github.com", "stackoverflow.com", "docs.*.com"],
                        "analysis": ["Map system components", "Identify technologies", "Understand data flow"]
                    },
                    {
                        "name": "Implementation Details",
                        "description": "Deep dive into implementation specifics",
                        "query_pattern": "{topic} implementation tutorial guide",
                        "url_patterns": ["dev.to", "medium.com", "hackernoon.com"],
                        "analysis": ["Extract code patterns", "Identify best practices", "Note pitfalls"]
                    },
                    {
                        "name": "Performance & Scale",
                        "description": "Analyze performance characteristics and scaling",
                        "query_pattern": "{topic} performance benchmark scale optimization",
                        "url_patterns": ["infoq.com", "highscalability.com"],
                        "analysis": ["Benchmark data", "Scaling strategies", "Optimization techniques"]
                    }
                ],
                "key_questions": [
                    "How does the technology work at a technical level?",
                    "What are the key implementation considerations?",
                    "How does it perform at scale?",
                    "What are the known limitations and workarounds?"
                ]
            },
            ResearchType.COMPETITIVE_ANALYSIS.value: {
                "phases": [
                    {
                        "name": "Competitor Mapping",
                        "description": "Identify and profile all major competitors",
                        "query_pattern": "{topic} alternatives competitors comparison",
                        "url_patterns": ["g2.com", "capterra.com", "producthunt.com"],
                        "analysis": ["List all competitors", "Categorize by approach", "Size the field"]
                    },
                    {
                        "name": "Feature Comparison",
                        "description": "Detailed feature-by-feature comparison",
                        "query_pattern": "{topic} features pricing plans comparison",
                        "url_patterns": ["*.com/pricing", "docs.*.com"],
                        "analysis": ["Create feature matrix", "Identify gaps", "Compare pricing"]
                    },
                    {
                        "name": "Strategic Analysis",
                        "description": "Analyze competitive positioning and strategy",
                        "query_pattern": "{topic} strategy funding acquisition",
                        "url_patterns": ["techcrunch.com", "pitchbook.com"],
                        "analysis": ["Map funding history", "Identify strategies", "Predict moves"]
                    }
                ],
                "key_questions": [
                    "Who are the direct and indirect competitors?",
                    "How do their features and pricing compare?",
                    "What are their strategic strengths and weaknesses?",
                    "What opportunities exist for differentiation?"
                ]
            },
            ResearchType.TREND_ANALYSIS.value: {
                "phases": [
                    {
                        "name": "Current State",
                        "description": "Document the current state of the field",
                        "query_pattern": "{topic} current state 2024 2025",
                        "url_patterns": ["wired.com", "techcrunch.com", "theverge.com"],
                        "analysis": ["Document current capabilities", "Map adoption rates", "Identify leaders"]
                    },
                    {
                        "name": "Emerging Trends",
                        "description": "Identify and validate emerging trends",
                        "query_pattern": "{topic} emerging trends future predictions",
                        "url_patterns": ["gartner.com", "forrester.com", "mckinsey.com"],
                        "analysis": ["List emerging trends", "Validate with data", "Assess impact"]
                    },
                    {
                        "name": "Future Outlook",
                        "description": "Project future developments and implications",
                        "query_pattern": "{topic} future roadmap vision 2026 2030",
                        "url_patterns": ["nature.com", "science.org", "arxiv.org"],
                        "analysis": ["Create timeline", "Identify inflection points", "Assess readiness"]
                    }
                ],
                "key_questions": [
                    "What is the current state of the field?",
                    "What trends are emerging?",
                    "How might the field evolve in the next 3-5 years?",
                    "What should organizations prepare for?"
                ]
            }
        }
    
    def generate_proposal(
        self,
        topic: str,
        research_type: ResearchType = ResearchType.LITERATURE_REVIEW,
        custom_queries: List[str] = None,
        custom_urls: List[str] = None,
        target_audience: str = "general",
        depth: str = "standard"  # light, standard, deep
    ) -> ResearchProposal:
        """Generate a research proposal from a topic."""
        
        proposal_id = str(uuid.uuid4())[:8]
        template = self.templates.get(research_type.value)
        
        # Fallback to literature review if type not found
        if template is None:
            template = self.templates[ResearchType.LITERATURE_REVIEW.value]
        
        # Generate phases based on template and depth
        phases = self._generate_phases(
            topic=topic,
            template=template,
            custom_queries=custom_queries,
            custom_urls=custom_urls,
            depth=depth
        )
        
        # Generate key questions
        key_questions = [
            q.format(topic=topic) for q in template.get("key_questions", [])
        ]
        
        # Calculate estimated duration
        total_minutes = sum(phase.estimated_duration_minutes for phase in phases)
        
        # Create proposal
        proposal = ResearchProposal(
            id=proposal_id,
            topic=topic,
            research_type=research_type,
            created_at=datetime.now().isoformat(),
            status="draft",
            phases=phases,
            metadata={
                "depth": depth,
                "custom_queries": custom_queries or [],
                "custom_urls": custom_urls or [],
                "template_used": research_type.value
            },
            estimated_total_minutes=total_minutes,
            target_audience=target_audience,
            key_questions=key_questions,
            success_criteria=[
                "Comprehensive coverage of topic",
                "Multiple authoritative sources cited",
                "Clear synthesis and actionable insights",
                "Gaps and limitations identified"
            ]
        )
        
        # Save proposal
        self._save_proposal(proposal)
        
        return proposal
    
    def _generate_phases(
        self,
        topic: str,
        template: Dict,
        custom_queries: List[str],
        custom_urls: List[str],
        depth: str
    ) -> List[ResearchPhase]:
        """Generate research phases based on template and depth."""
        
        phases = []
        template_phases = template.get("phases", [])
        
        # Adjust phase count based on depth
        if depth == "light":
            phase_count = max(1, len(template_phases) - 1)
        elif depth == "deep":
            phase_count = len(template_phases) + 1
        else:
            phase_count = len(template_phases)
        
        for i, phase_template in enumerate(template_phases[:phase_count]):
            # Generate search queries
            query_pattern = phase_template.get("query_pattern", "{topic}")
            queries = [query_pattern.format(topic=topic)]
            
            if custom_queries:
                queries.extend(custom_queries[:2])
            
            # Generate extraction URLs
            urls = []
            url_patterns = phase_template.get("url_patterns", [])
            for pattern in url_patterns:
                if "*" in pattern:
                    # Convert glob to example URL
                    example = pattern.replace("*", "example")
                    if not example.startswith("http"):
                        example = f"https://{example}"
                    urls.append(example)
                else:
                    if not pattern.startswith("http"):
                        pattern = f"https://{pattern}"
                    urls.append(pattern)
            
            if custom_urls:
                urls.extend(custom_urls[:3])
            
            # Generate analysis tasks
            analysis_tasks = phase_template.get("analysis", [])
            
            # Estimate duration based on complexity
            base_duration = 5
            if depth == "deep":
                base_duration = 8
            elif depth == "light":
                base_duration = 3
            
            duration = base_duration + (len(queries) * 2) + (len(urls) * 3)
            
            phase = ResearchPhase(
                id=f"phase_{i+1}",
                name=phase_template["name"],
                description=phase_template["description"],
                search_queries=queries,
                extraction_urls=urls[:5],  # Limit to 5 URLs per phase
                analysis_tasks=analysis_tasks,
                estimated_duration_minutes=duration,
                dependencies=[f"phase_{i}"] if i > 0 else []
            )
            
            phases.append(phase)
        
        return phases
    
    def _save_proposal(self, proposal: ResearchProposal):
        """Save proposal to disk."""
        proposal_file = self.proposals_dir / f"{proposal.id}.json"
        
        # Convert to dict for JSON serialization
        data = asdict(proposal)
        data["research_type"] = proposal.research_type.value
        
        with open(proposal_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_proposal(self, proposal_id: str) -> Optional[ResearchProposal]:
        """Load a proposal from disk."""
        proposal_file = self.proposals_dir / f"{proposal_id}.json"
        
        if not proposal_file.exists():
            return None
        
        with open(proposal_file, 'r') as f:
            data = json.load(f)
        
        # Convert research_type back to enum
        data["research_type"] = ResearchType(data["research_type"])
        
        # Reconstruct ResearchPhase objects
        phases = []
        for phase_data in data["phases"]:
            phases.append(ResearchPhase(**phase_data))
        data["phases"] = phases
        
        return ResearchProposal(**data)
    
    def list_proposals(self, status: str = None) -> List[Dict]:
        """List all proposals, optionally filtered by status."""
        proposals = []
        
        for proposal_file in self.proposals_dir.glob("*.json"):
            with open(proposal_file, 'r') as f:
                data = json.load(f)
            
            if status and data.get("status") != status:
                continue
            
            proposals.append({
                "id": data["id"],
                "topic": data["topic"],
                "type": data["research_type"],
                "status": data["status"],
                "created_at": data["created_at"],
                "phases": len(data["phases"]),
                "estimated_minutes": data["estimated_total_minutes"]
            })
        
        return sorted(proposals, key=lambda x: x["created_at"], reverse=True)
    
    def update_proposal_status(self, proposal_id: str, status: str):
        """Update proposal status."""
        proposal = self.load_proposal(proposal_id)
        if proposal:
            proposal.status = status
            self._save_proposal(proposal)


def generate_proposal_cli(topic: str, research_type: str = "literature_review", depth: str = "standard"):
    """CLI wrapper for proposal generation."""
    generator = ProposalGenerator()
    
    type_enum = ResearchType(research_type)
    proposal = generator.generate_proposal(topic=topic, research_type=type_enum, depth=depth)
    
    print(f"\n✅ Research Proposal Generated")
    print(f"{'='*60}")
    print(f"ID: {proposal.id}")
    print(f"Topic: {proposal.topic}")
    print(f"Type: {proposal.research_type.value}")
    print(f"Status: {proposal.status}")
    print(f"Estimated Duration: {proposal.estimated_total_minutes} minutes")
    print(f"\nKey Questions:")
    for q in proposal.key_questions:
        print(f"  • {q}")
    print(f"\nPhases:")
    for phase in proposal.phases:
        print(f"\n  Phase {phase.id}: {phase.name}")
        print(f"    Description: {phase.description}")
        print(f"    Duration: ~{phase.estimated_duration_minutes} minutes")
        print(f"    Search Queries:")
        for q in phase.search_queries:
            print(f"      - {q}")
        print(f"    Analysis Tasks:")
        for task in phase.analysis_tasks:
            print(f"      - {task}")
    
    print(f"\n{'='*60}")
    print(f"Proposal saved to: proposals/{proposal.id}.json")
    print(f"\nTo execute: python research_executor.py {proposal.id}")
    
    return proposal


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python proposal_generator.py <topic> [research_type] [depth]")
        print("Research types: literature_review, market_analysis, technical_deep_dive,")
        print("                competitive_analysis, trend_analysis")
        print("Depth: light, standard, deep")
        sys.exit(1)
    
    topic = sys.argv[1]
    research_type = sys.argv[2] if len(sys.argv) > 2 else "literature_review"
    depth = sys.argv[3] if len(sys.argv) > 3 else "standard"
    
    generate_proposal_cli(topic, research_type, depth)