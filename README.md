---
title: LegalContractReview
emoji: "⚖️"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
---

# LegalContractReview OpenEnv Environment

A real-world AI agent benchmark for legal document auditing and compliance.

The LegalContractReview environment simulates how legal professionals review contracts to identify risks, enforce policy compliance, and detect missing clauses.

## Task Overview

Agents must analyze contracts and identify:

- High-Risk Clauses (e.g., unlimited liability, unfair termination)
- Policy Violations (e.g., unfavorable payment terms)
- Missing Clauses (e.g., confidentiality or indemnity clauses)

## OpenEnv Specification

### Action Space

| Action        | Description          | Required Fields    |
|---------------|----------------------|--------------------|
| flag_risk     | Mark clause as risky | clause_id          |
| mark_safe     | Mark clause as safe  | clause_id          |
| suggest_edit  | Suggest improvement  | clause_id, content |
| add_clause    | Add missing clause   | content            |
| next_clause   | Move to next clause  | -                  |
| finish_review | End review           | -                  |

### Observation Space

- contract_id – Unique contract identifier  
- current_clause – Clause text + ID  
- clause_index – Position in contract  
- issues_found – Detected risks so far  
- metadata:
  - goal – Task objective  
  - score – Current evaluation score  

## Tasks

### Easy — Risk Detection
- Detect high-risk clauses

### Medium — Compliance Audit
- Detect risks and suggest edits

### Hard — Full Audit
- Detect risks, edits, and missing clauses

## Reward Design

- New clause visited: +0.05  
- Correct risk flag: +1.0  
- Correct edit: +1.5  
- Missing clause: +2.0  
- Wrong safe marking: -1.0  
- Final bonus: up to +5.0  

## Setup

### Build Docker Image
docker build -t legalcontractreview-env .

### Run Environment
uv run server

## Validation
openenv validate

## Notes

- Use POST requests for /reset and /step  
- /web is optional  