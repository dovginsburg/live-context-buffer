# Research System

An autonomous research proposal and execution system built on Hermes Agent.

## Features

- **Topic Specification**: Define research topics with customizable parameters
- **Proposal Generation**: Automatically generate structured research plans
- **Autonomous Execution**: Execute research using Hermes tools (web search, extraction, analysis)
- **Results Management**: Store, view, search, and export research results
- **Multiple Research Types**: Literature review, market analysis, technical deep-dive, competitive analysis, trend analysis

## Quick Start

### 1. Create a Research Proposal

```bash
# Basic usage
python research_cli.py create "Impact of AI on healthcare"

# With specific type and depth
python research_cli.py create "Quantum computing applications" technical_deep_dive deep

# List research types
python research_cli.py create --help
```

### 2. View Your Proposals

```bash
python research_cli.py list
```

### 3. Execute Research

```bash
python research_cli.py execute <proposal_id>
```

This will:
- Execute search queries for each phase
- Extract content from relevant sources
- Analyze findings and generate insights
- Save results automatically

### 4. View Results

```bash
# List all results
python research_cli.py results list

# View detailed results
python research_cli.py results detail <proposal_id>

# Export as markdown
python research_cli.py results export <proposal_id> markdown

# Export as HTML
python research_cli.py results export <proposal_id> html

# Search results
python research_cli.py results search "healthcare"
```

### 5. View Statistics

```bash
python research_cli.py stats
```

## Research Types

| Type | Description | Best For |
|------|-------------|----------|
| `literature_review` | Survey academic and industry literature | Understanding existing knowledge |
| `market_analysis` | Analyze market size, trends, players | Business decisions, investments |
| `technical_deep_dive` | Deep technical exploration | Architecture, implementation |
| `competitive_analysis` | Compare competitors and positioning | Strategy, differentiation |
| `trend_analysis` | Identify and validate trends | Future planning, innovation |

## Depth Levels

| Level | Phases | Duration | Use Case |
|-------|--------|----------|----------|
| `light` | 1-2 | 5-10 min | Quick overview |
| `standard` | 2-3 | 10-20 min | Comprehensive |
| `deep` | 3-4 | 20-40 min | Exhaustive |

## System Architecture

```
research-system/
├── research_cli.py          # Main CLI interface
├── scripts/
│   ├── __init__.py
│   ├── proposal_generator.py    # Creates research proposals
│   ├── research_executor.py     # Executes research (base class)
│   ├── hermes_executor.py       # Hermes tools integration
│   └── results_manager.py       # Results viewing and export
├── proposals/              # Stored proposal files (.json)
├── results/                # Stored research results (.json, .md, .html)
└── README.md               # This file
```

## How It Works

1. **Proposal Generation**: When you create a proposal, the system:
   - Analyzes your topic and research type
   - Generates search queries and extraction targets
   - Creates a phased research plan with estimated durations
   - Saves the proposal as JSON

2. **Research Execution**: When you execute a proposal, the system:
   - Loads the proposal and initializes results tracking
   - For each phase:
     - Executes web searches using Hermes `web_search` tool
     - Extracts content from top sources using Hermes `web_extract` tool
     - Analyzes findings and extracts insights
   - Generates executive summary and key findings
   - Saves comprehensive results

3. **Results Management**: Results are stored in JSON format and can be:
   - Viewed in terminal with formatting
   - Exported as Markdown for documentation
   - Exported as HTML for sharing
   - Searched across all past research

## Example Workflow

```bash
# 1. Create a proposal about quantum computing
python research_cli.py create "Quantum computing applications in cryptography" technical_deep_dive

# Note the proposal ID (e.g., a1b2c3d4)

# 2. Execute the research
python research_cli.py execute a1b2c3d4

# 3. View the results
python research_cli.py results detail a1b2c3d4

# 4. Export as markdown
python research_cli.py results export a1b2c3d4 markdown

# 5. Check statistics
python research_cli.py stats
```

## Integration with Hermes Agent

This system is designed to work seamlessly with Hermes Agent:

- Uses Hermes tools (`web_search`, `web_extract`) for content gathering
- Results can be accessed via `execute_code` for programmatic use
- Exports can be shared via WhatsApp or other channels
- Past research can be searched and referenced in future sessions

## File Formats

### Proposal JSON

```json
{
  "id": "a1b2c3d4",
  "topic": "Quantum computing applications",
  "research_type": "technical_deep_dive",
  "status": "completed",
  "phases": [...],
  "created_at": "2024-01-15T10:30:00",
  "estimated_total_minutes": 25
}
```

### Result JSON

```json
{
  "proposal_id": "a1b2c3d4",
  "topic": "Quantum computing applications",
  "status": "completed",
  "executive_summary": "...",
  "key_findings": ["..."],
  "sources_cited": ["..."],
  "phase_results": [...]
}
```

## Troubleshooting

### "Proposal not found"

Make sure you're using the correct proposal ID. List all proposals:
```bash
python research_cli.py list
```

### Research takes too long

- Use `light` depth for quick overviews
- Limit custom URLs and queries
- Check network connectivity

### Results not saving

Ensure the `results/` directory exists and is writable:
```bash
mkdir -p ~/Projects/ezra/research-system/results
```

## Future Enhancements

- [ ] Parallel phase execution
- [ ] Custom analysis templates
- [ ] Integration with academic APIs (arXiv, PubMed)
- [ ] Citation management (BibTeX export)
- [ ] Collaborative research sharing
- [ ] Real-time progress monitoring
- [ ] AI-powered insight extraction
- [ ] Automated report generation

## License

MIT