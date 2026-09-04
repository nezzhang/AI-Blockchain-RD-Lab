# MASTER BUILD PROMPT
# AI Blockchain R&D Lab

You are the lead architect, senior software engineer, quantitative researcher, blockchain researcher, economist, security researcher, and AI-agent engineer responsible for building this entire project.

The project name is:

# AI Blockchain R&D Lab

Repository:

`AI-Blockchain-RD-Lab`

---

# 0. Mission

Build an autonomous AI-powered research laboratory for discovering, evaluating, simulating, attacking, and ranking novel blockchain economic mechanisms.

The ultimate objective is NOT:

- creating random crypto tokens
- copying existing blockchains
- generating meme coins
- immediately launching a token
- immediately launching a Layer-1
- producing superficial whitepapers

The objective is:

> Discover genuinely interesting, economically coherent, technically feasible, and potentially novel blockchain economic primitives.

Examples include:

- new token supply mechanisms
- new monetary systems
- stablecoin mechanisms
- stablecoin infrastructure
- payment protocols
- oracle mechanisms
- incentive mechanisms
- decentralized financial primitives
- real-world-data-driven monetary systems
- novel blockchain architectures

The system should systematically search a huge design space and eliminate bad ideas through research, mathematical modeling, simulation, and adversarial testing.

---

# 1. Founder Constraints

The founder is a single individual.

Assume:

- very limited initial capital
- no large engineering team
- no research department
- no dedicated marketing team
- no dedicated legal department
- heavy dependence on LLMs and automation

Therefore:

> AI must provide maximum leverage.

The system should allow one person to operate a serious research laboratory using LLM agents, open-source software, public datasets, simulations, and automation.

---

# 2. Core Principle

Never trust an idea simply because an LLM thinks it is good.

Separate:

## LLM responsibilities

LLMs may:

- generate hypotheses
- research
- summarize literature
- compare protocols
- design mechanisms
- formulate mathematical models
- write simulation code
- criticize ideas
- perform red-team analysis
- write reports

## Deterministic software responsibilities

Code must:

- calculate
- simulate
- backtest
- optimize
- validate
- score
- store results
- reproduce experiments

The fundamental principle is:

> LLM proposes. Code tests. Evidence decides.

---

# 3. Research Loop

The entire system must follow:

```text
DISCOVER
    ↓
RESEARCH
    ↓
PRIOR ART
    ↓
DE-DUPLICATE
    ↓
FORMALIZE
    ↓
SIMULATE
    ↓
RED TEAM
    ↓
IMPROVE
    ↓
RE-SIMULATE
    ↓
SCORE
    ↓
RANK
    ↓
REPORT
    ↓
PUBLIC RESEARCH
```

---

# 4. Important Strategic Principle

Do NOT assume every good idea needs:

- a token
- a blockchain
- a Layer-1
- a Layer-2

The system must first determine:

> What is the economic mechanism?

Only afterward determine:

> What technology is required?

Possible final implementations:

- token
- smart contract
- DeFi protocol
- oracle network
- stablecoin
- payment network
- L1
- L2
- application
- API
- no blockchain at all

---

# 5. Repository Structure

Create:

```text
AI-Blockchain-RD-Lab/

├── README.md
├── MASTER_BUILD_PROMPT.md
├── AGENTS.md
├── CLAUDE.md
├── GEMINI.md
├── LICENSE
├── pyproject.toml
├── Makefile
├── .gitignore
│
├── config/
│   ├── lab.yaml
│   ├── agents.yaml
│   ├── scoring.yaml
│   └── research.yaml
│
├── src/
│   └── blockchain_rd_lab/
│       ├── __init__.py
│       ├── cli.py
│       │
│       ├── orchestrator/
│       ├── agents/
│       ├── discovery/
│       ├── research/
│       ├── prior_art/
│       ├── mechanisms/
│       ├── simulation/
│       ├── redteam/
│       ├── scoring/
│       ├── ranking/
│       ├── database/
│       ├── reports/
│       └── utils/
│
├── agents/
│   ├── orchestrator/
│   ├── discovery/
│   ├── economist/
│   ├── game_theory/
│   ├── quant/
│   ├── blockchain/
│   ├── oracle/
│   ├── security/
│   ├── regulatory/
│   ├── market/
│   └── red_team/
│
├── ideas/
│   ├── active/
│   ├── promising/
│   ├── finalists/
│   └── rejected/
│
├── research/
│   ├── papers/
│   ├── protocols/
│   ├── prior_art/
│   └── competitors/
│
├── mechanisms/
│
├── simulations/
│   ├── models/
│   ├── monte_carlo/
│   ├── agent_based/
│   └── historical/
│
├── redteam/
│   ├── economic/
│   ├── game_theory/
│   ├── security/
│   ├── oracle/
│   ├── governance/
│   └── liquidity/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
│
├── database/
│
├── reports/
│   ├── daily/
│   ├── weekly/
│   └── finalists/
│
├── tests/
│
└── scripts/
```

---

# 6. Technology Stack

Prefer:

### Language

Python 3.12+

### Package management

Use modern Python packaging with `pyproject.toml`.

Prefer `uv` for dependency management if available.

### Core

- Pydantic
- Typer
- Rich
- SQLAlchemy
- SQLite initially
- DuckDB for analytical workloads
- Pandas or Polars
- NumPy
- SciPy
- statsmodels
- NetworkX
- PyYAML

### Simulation

- NumPy
- SciPy
- Monte Carlo
- agent-based simulation where appropriate

### Optimization

- Optuna

### Testing

- pytest
- hypothesis

### Formatting

- Ruff

### Type checking

- mypy or pyright

Do not introduce unnecessary dependencies.

Prefer simple, maintainable architecture.

---

# 7. CLI

Create an executable CLI:

```bash
lab discover
lab research
lab prior-art
lab formalize
lab simulate
lab redteam
lab score
lab rank
lab report
lab pipeline
lab status
lab search
```

Example:

```bash
lab discover --count 100
```

Example:

```bash
lab pipeline --count 100
```

The complete pipeline should eventually support:

```text
100 ideas
↓
prior-art research
↓
20 candidates
↓
mathematical formalization
↓
simulation
↓
red-team
↓
5 finalists
↓
1 recommended candidate
```

---

# 8. Agent Architecture

Implement an agent abstraction.

Every agent should have:

```text
Agent
├── name
├── role
├── system_prompt
├── input_schema
├── output_schema
├── model
├── temperature
├── tools
└── execute()
```

Use structured outputs wherever possible.

Do not allow arbitrary unstructured text to control deterministic parts of the system.

---

# 9. Initial Agents

Implement these agents.

## Discovery Agent

Mission:

Generate novel blockchain mechanisms.

Search across:

- economics
- finance
- demographics
- AI
- energy
- climate
- biology
- mathematics
- game theory
- information theory
- network economics
- insurance
- prediction markets
- commodities
- labor
- global trade
- internet
- distributed systems

Generate mechanisms, not token names.

---

## Economist Agent

Analyze:

- monetary policy
- inflation
- deflation
- incentives
- liquidity
- monetary equilibrium
- economic stability
- reflexivity
- capital flows

---

## Game Theory Agent

Assume participants are rational profit maximizers.

Find:

- arbitrage
- manipulation
- incentive misalignment
- equilibrium failures
- bank runs
- death spirals
- strategic attacks

---

## Quant Agent

Convert ideas into mathematical models and simulations.

Use:

- historical data
- Monte Carlo
- sensitivity analysis
- parameter sweeps
- optimization
- stress testing

---

## Blockchain Architect

Determine:

- whether blockchain is actually required
- consensus requirements
- state model
- token model
- smart contracts
- validator economics
- transaction model
- finality
- scalability
- MEV
- governance

---

## Oracle Agent

For real-world-data mechanisms investigate:

- data sources
- accuracy
- latency
- revisions
- manipulation
- decentralization
- oracle incentives
- conflicting data

---

## Security Agent

Investigate:

- smart contract attacks
- economic attacks
- oracle attacks
- governance attacks
- validator attacks
- liquidity attacks
- Sybil attacks
- censorship
- collusion

---

## Regulatory Risk Agent

This agent must NOT provide legal advice.

It should identify potential regulatory issues and areas requiring professional legal review.

Investigate:

- securities risk
- stablecoin regulation
- money transmission
- AML/KYC
- sanctions
- jurisdiction
- custody
- financial promotion

---

## Market Agent

Analyze:

- actual customer
- actual problem
- existing alternatives
- market size
- adoption barriers
- network effects
- competitive landscape

---

## Red Team Agent

Mission:

DESTROY THE IDEA.

It should actively attempt to make every promising mechanism fail.

Ask:

```text
How can I manipulate it?

How can I arbitrage it?

How can a whale exploit it?

How can validators exploit it?

How can oracle providers exploit it?

How can governance exploit it?

How can liquidity disappear?

How can the system enter a death spiral?

Can I create a profitable attack?

What happens during a crisis?

What happens if assumptions are wrong?
```

---

# 10. Candidate Schema

Create a structured candidate model.

Example fields:

```text
id
name
category
description
core_mechanism
problem
innovation_claim
inputs
outputs
oracle_required
blockchain_required
token_required
status
novelty_score
economic_score
game_theory_score
technical_score
oracle_score
security_score
market_score
capital_efficiency_score
network_effect_score
communication_score
viral_score
overall_score
fatal_flaw
created_at
updated_at
```

Use Pydantic validation.

---

# 11. Status Machine

Candidates must move through controlled states:

```text
GENERATED
    ↓
RESEARCHING
    ↓
PRIOR_ART_CHECKED
    ↓
FORMALIZED
    ↓
SIMULATING
    ↓
RED_TEAM
    ↓
IMPROVEMENT
    ↓
RETEST
    ↓
SCORED
    ↓
FINALIST
```

Possible terminal states:

```text
REJECTED
FAILED
SUPERSEDED
```

Never allow arbitrary state transitions.

---

# 12. Novelty Classification

Use:

```text
A = clearly existing
B = very similar existing mechanism
C = adjacent mechanism
D = appears substantially novel
E = insufficient evidence
```

IMPORTANT:

Never claim:

> "Nobody has ever done this."

Instead say:

> "No substantially similar implementation was identified in the searched sources."

Record:

- search queries
- sources
- dates
- findings
- similar mechanisms

---

# 13. Mathematical Formalization

Every serious candidate must eventually have equations.

Example:

Population mechanism:

```text
P(t) = global population

B(t) = births

D(t) = deaths

M(t) = migration

ΔP(t) = B(t) - D(t) + M(t)
```

Potential supply rule:

```text
S(t+1) = S(t) × [1 + α × ΔP/P]
```

The system must investigate:

- α
- smoothing
- lag
- caps
- floors
- uncertainty
- oracle frequency
- statistical confidence

Never assume the first equation is correct.

---

# 14. Simulation Framework

Create a generic simulation interface.

Example:

```text
Simulation
├── parameters
├── initial_state
├── transition()
├── observe()
├── metrics()
└── run()
```

Support:

### Monte Carlo

Randomized scenarios.

### Historical simulation

Use real historical data.

### Agent-based simulation

Model:

- users
- whales
- validators
- arbitrageurs
- liquidity providers
- attackers
- governance participants
- oracle providers

---

# 15. Simulation Requirements

Every promising mechanism should test:

```text
Base case
Bull case
Bear case
Extreme inflation
Extreme deflation
Liquidity crisis
Bank run
Oracle failure
Oracle manipulation
Governance attack
Whale attack
Market crash
Black swan
```

Never only show favorable scenarios.

---

# 16. Stablecoin Infrastructure Research Track

Create a dedicated research category:

# Stablecoin Infrastructure

Research:

- stablecoin settlement
- cross-border payments
- merchant payments
- stablecoin-native chains
- stablecoin routing
- liquidity
- collateral
- decentralized FX
- payment channels
- account abstraction
- institutional settlement
- merchant APIs
- wallet SDKs
- transaction fee markets
- compliance infrastructure

The system should answer:

> What infrastructure could make stablecoins substantially cheaper, faster, safer, and easier to use?

---

# 17. Token Supply Mechanism Laboratory

Create a dedicated mechanism library.

Explore:

```text
Market-driven
Usage-driven
Economic-driven
Demographic-driven
Productivity-driven
Energy-driven
Climate-driven
Commodity-driven
Insurance-driven
Prediction-driven
Network-driven
AI-driven
Hybrid
```

Search for novel combinations.

---

# 18. Mechanism Combinator

Create an engine that combines mechanisms.

Examples:

```text
Population
+
Stablecoin
```

```text
AI productivity
+
Monetary policy
```

```text
Energy
+
Proof-of-Stake
```

```text
Human development
+
Currency supply
```

Do not generate combinations randomly only.

Use semantic similarity and economic compatibility.

---

# 19. Scoring

Use:

```text
Novelty                 10%
Economic Coherence      15%
Game Theory             10%
Technical Feasibility   10%
Oracle Feasibility      10%
Security                10%
Market Demand           15%
Capital Efficiency       5%
Network Effects          5%
Communication            5%
Viral Potential          5%
```

Create a deterministic scoring engine.

---

# 20. Fatal Flaw System

A candidate must not receive a high ranking if it contains a fatal flaw.

Examples:

```text
Oracle manipulation impossible to prevent
Critical economic death spiral
Unfixable security vulnerability
No identifiable user
Requires impossible data
Requires unrealistic infrastructure
```

If a fatal flaw is confirmed:

```text
REJECTED
```

Do not average away fatal flaws.

---

# 21. Reproducibility

Every experiment must record:

```text
experiment_id
candidate_id
timestamp
git_commit
parameters
dataset
model
seed
simulation_version
results
```

A researcher must be able to reproduce a result.

---

# 22. Database

Start with SQLite.

Use DuckDB for analytical queries.

Store:

```text
candidates
experiments
simulations
agents
agent_runs
sources
prior_art
scores
redteam_results
datasets
reports
```

Do not store huge datasets inside Git.

---

# 23. Reports

Generate:

```text
reports/
├── daily/
├── weekly/
└── finalists/
```

Every finalist should have:

```text
Executive Summary

Problem

Mechanism

Mathematical Model

Economic Analysis

Game Theory

Oracle Design

Security

Simulation

Historical Analysis

Prior Art

Competitors

Market

Technical Architecture

Regulatory Risks

MVP

Risks

Open Questions

Recommendation
```

---

# 24. First 100 Mechanisms

The first research cycle must generate at least:

# 100 mechanisms

across:

1. Monetary economics
2. Stablecoins
3. Payments
4. Demographics
5. AI productivity
6. Energy
7. Climate
8. Commodities
9. Insurance
10. Prediction markets
11. Labor
12. Global trade
13. Internet
14. Biology
15. Ecology
16. Game theory
17. Information theory
18. Network economics
19. Financial markets
20. Distributed systems

Do not prematurely select the Population idea.

It must compete fairly with all other candidates.

---

# 25. Population Money Experiment

Include this as:

```text
Experiment #001
```

Initial hypothesis:

> Token supply is linked to verified changes in global population.

Potential variables:

```text
Births
Deaths
Migration
Population growth
Population uncertainty
```

Do NOT assume this is a good idea.

The lab must attempt to prove or disprove it.

Questions:

```text
Does it have economic meaning?

What does 1 token represent?

Why should the token have value?

Does supply growth create dilution?

Can supply reduction create a death spiral?

Can population data be manipulated?

Can the system be gamed?

What happens during demographic collapse?

What happens if data is revised?

What happens if different sources disagree?
```

---

# 26. Public Research Philosophy

Eventually make the repository suitable for public release.

Public artifacts should include:

```text
README
Research reports
Simulation results
Mathematical models
Rejected ideas
Assumptions
Known limitations
```

Do not hide failed experiments.

The `rejected/` directory is a research asset.

---

# 27. Build-in-Public Strategy

Do not immediately launch a token.

Recommended progression:

```text
Idea
↓
Research
↓
Simulation
↓
Open-source publication
↓
Community criticism
↓
Prototype
↓
Testnet
↓
Developer adoption
↓
Only then consider token/mainnet
```

---

# 28. No Token Before Evidence

The system must NEVER automatically deploy or issue a real cryptocurrency.

The lab is a research system.

Any real-world token issuance requires explicit human approval.

---

# 29. External Research

When performing current research, use authoritative sources where possible.

Preferred sources:

- academic papers
- official protocol documentation
- official repositories
- government datasets
- international organizations
- established research institutions

For blockchain projects, inspect:

- GitHub
- official documentation
- technical papers
- governance documentation
- tokenomics documentation

Always distinguish:

```text
FACT
INFERENCE
HYPOTHESIS
```

---

# 30. LLM Provider Abstraction

Do not hard-code one LLM provider.

Create an interface:

```text
LLMProvider
├── OpenAI
├── Anthropic
├── Gemini
├── Local
└── Mock
```

Provider configuration must come from YAML/environment variables.

Never hard-code API keys.

---

# 31. Cost Control

Because the founder has limited capital:

Implement:

- caching
- deduplication
- retry logic
- token budgets
- model routing
- cheap model for simple tasks
- stronger model for finalists
- deterministic local calculations
- batch research
- configurable concurrency

Do NOT use the most expensive model for everything.

Recommended routing:

```text
Simple classification
→ cheap model

Idea generation
→ medium model

Research synthesis
→ strong model

Final mechanism analysis
→ strongest available model

Simulation
→ Python
```

---

# 32. Agent Memory

Agents should not repeatedly rediscover the same information.

Persist:

- prior-art findings
- research sources
- rejected ideas
- failed attacks
- successful attacks
- simulation results
- assumptions

The lab should become smarter over time.

---

# 33. Research Knowledge Graph

Eventually maintain relationships:

```text
Idea
 ↕
Paper
 ↕
Protocol
 ↕
Mechanism
 ↕
Simulation
 ↕
Attack
 ↕
Improvement
```

This allows future agents to reuse previous discoveries.

---

# 34. Automated Pipeline

Implement:

```bash
lab pipeline --count 100
```

Pipeline:

```text
Generate
↓
Normalize
↓
Deduplicate
↓
Prior Art
↓
Filter
↓
Formalize
↓
Simulate
↓
Red Team
↓
Improve
↓
Re-simulate
↓
Score
↓
Rank
↓
Report
```

The pipeline must support interruption and resumption.

Never lose progress because one LLM call fails.

---

# 35. Error Handling

LLM calls can fail.

Implement:

- retries
- exponential backoff
- timeout
- validation
- structured output validation
- fallback model
- failed-run recording
- resumable jobs

Never crash the entire research pipeline because one agent failed.

---

# 36. Testing

Write tests before considering Phase 0 complete.

Minimum:

```text
unit tests
schema tests
scoring tests
database tests
simulation tests
CLI tests
pipeline tests
mock LLM tests
```

Use synthetic data for deterministic tests.

---

# 37. Security

Never allow an LLM to:

- execute arbitrary shell commands without explicit controls
- access private credentials
- deploy contracts automatically
- transfer funds
- modify system files outside the repository

All external actions must go through explicit tools/interfaces.

---

# 38. Phase Structure

Build incrementally.

## PHASE 0

Foundation.

Implement:

- repository
- configuration
- Pydantic schemas
- database
- CLI
- agent interface
- mock LLM provider
- scoring engine
- tests

Do NOT implement the full autonomous pipeline yet.

---

## PHASE 1

Discovery.

Implement:

- Discovery Agent
- idea generation
- normalization
- deduplication
- candidate storage

Target:

```text
100 ideas
```

---

## PHASE 2

Research.

Implement:

- Prior-Art Agent
- Economist Agent
- Market Agent
- research source storage

---

## PHASE 3

Formalization.

Implement:

- mathematical model schema
- Mechanism Designer
- equation storage
- assumptions

---

## PHASE 4

Simulation.

Implement:

- simulation framework
- Monte Carlo
- historical simulation
- parameter sweeps
- Optuna

---

## PHASE 5

Adversarial Testing.

Implement:

- Game Theory Agent
- Security Agent
- Oracle Agent
- Red Team

---

## PHASE 6

Ranking.

Implement:

- deterministic scoring
- fatal flaw gate
- ranking
- finalist selection

---

## PHASE 7

Reporting.

Implement:

- automated research reports
- Markdown
- charts
- experiment summaries

---

## PHASE 8

Public Research.

Prepare:

- README
- methodology
- reproducibility
- research archive
- rejected mechanisms
- public release structure

---

# 39. Development Rules

IMPORTANT:

Do NOT attempt to build the entire system in one huge step.

Work phase by phase.

After each phase:

```text
1. Implement
2. Run tests
3. Fix failures
4. Run lint
5. Run type checking
6. Review architecture
7. Update documentation
8. Commit changes
9. Only then proceed
```

Never skip tests.

---

# 40. Git Commit Strategy

Use meaningful commits:

```text
feat: initialize research lab
feat: add candidate schemas
feat: add database layer
feat: add CLI
feat: add agent abstraction
feat: add discovery pipeline
feat: add prior art research
feat: add simulation engine
feat: add red team engine
feat: add scoring engine
feat: add reporting
```

Do not create meaningless commits.

---

# 41. Human Approval Gates

The following actions require explicit human approval:

```text
Deploying contracts
Launching testnet
Issuing real tokens
Spending significant API budget
Connecting wallets
Moving funds
Publishing official claims of novelty
Entering legal agreements
```

The autonomous lab may recommend.

It must not independently execute these actions.

---

# 42. Definition of Success

The project is successful when one person can execute:

```bash
lab pipeline --count 100
```

and obtain:

```text
100 generated mechanisms

↓
prior-art analysis

↓
20 serious candidates

↓
mathematical models

↓
simulation results

↓
adversarial attacks

↓
5 finalists

↓
1 recommended mechanism
```

with reproducible research reports.

---

# 43. Ultimate Objective

Do not optimize for:

> number of tokens created.

Optimize for:

> discovery of a genuinely valuable new economic primitive.

The strongest outcome may eventually become:

```text
A new token
```

or:

```text
A stablecoin protocol
```

or:

```text
A payment network
```

or:

```text
A blockchain
```

or:

```text
A completely new financial primitive
```

We do not know in advance.

That uncertainty is the reason this research lab exists.

---

# 44. FIRST TASK

You are now inside the empty:

`AI-Blockchain-RD-Lab`

directory.

Start with:

# PHASE 0

Do NOT jump to Phase 1.

First:

1. Inspect the directory.
2. Create the repository structure.
3. Create `pyproject.toml`.
4. Create configuration.
5. Create Pydantic schemas.
6. Create database layer.
7. Create CLI.
8. Create agent abstraction.
9. Create mock LLM provider.
10. Create scoring engine.
11. Create tests.
12. Create documentation.
13. Run all tests.
14. Run linting.
15. Run type checking.
16. Fix all issues.
17. Produce a Phase 0 completion report.

At the end, clearly report:

```text
PHASE 0 STATUS

Implemented:
...

Tests:
...

Lint:
...

Type checking:
...

Known limitations:
...

Next phase:
PHASE 1 — DISCOVERY
```

Do not proceed to Phase 1 until Phase 0 is stable.