#!/usr/bin/env python3
"""
Test script for the research system.
Creates a sample proposal and shows the workflow.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from proposal_generator import ProposalGenerator, ResearchType
from results_manager import ResultsManager, print_results_list

def main():
    print("=" * 60)
    print("RESEARCH SYSTEM TEST")
    print("=" * 60)
    
    # 1. Create a proposal
    print("\n1. Creating research proposal...")
    generator = ProposalGenerator()
    
    proposal = generator.generate_proposal(
        topic="Rust programming language adoption in systems programming",
        research_type=ResearchType.TECHNICAL_DEEP_DIVE,
        depth="standard"
    )
    
    print(f"✅ Proposal created: {proposal.id}")
    print(f"   Topic: {proposal.topic}")
    print(f"   Type: {proposal.research_type.value}")
    print(f"   Phases: {len(proposal.phases)}")
    print(f"   Estimated: {proposal.estimated_total_minutes} minutes")
    
    # 2. List proposals
    print("\n2. Listing all proposals...")
    proposals = generator.list_proposals()
    print(f"   Found {len(proposals)} proposal(s)")
    for p in proposals:
        print(f"   - {p['id']}: {p['topic'][:40]} ({p['status']})")
    
    # 3. Show results manager
    print("\n3. Results manager status...")
    manager = ResultsManager()
    results = manager.list_results()
    print(f"   Found {len(results)} result(s)")
    
    stats = manager.get_statistics()
    print(f"   Statistics: {stats['total_research']} total, {stats['completed']} completed")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nTo execute research, use:")
    print(f"  python research_cli.py execute {proposal.id}")
    print("\nTo view this proposal's details:")
    print(f"  python research_cli.py list")

if __name__ == "__main__":
    main()