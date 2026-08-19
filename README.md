# DIKWP COMMONBRIDGE-85

**Any person. Any lawful AI tier. One verifiable contribution.**

COMMONBRIDGE-85 is an offline-first, capability-neutral cooperation protocol for an era in which AI access may be fragmented by jurisdiction, institutional role, platform policy, export controls, cost, language and network conditions.

It does **not** bypass law, platform controls, model access restrictions, identity rules, sanctions or export controls. It keeps cooperation possible by compiling the same DIKWP project into lawful paths that can be completed:

- manually, without AI;
- with local rules and lightweight tools;
- with a small local model;
- with a limited hosted model;
- with advanced hosted tools;
- or inside an authorized institutional environment.

The system grades **tasks and current environments, never persons**. Environment profiles expire and may change. No global reputation score, ideology score, capability caste, financial token or social-credit object exists.

## What the public tool does

1. Creates a source-grounded D/I/K/W/P cooperation capsule.
2. Splits the project into capability-neutral task shards.
3. Routes each shard through the current lawful environment.
4. Preserves manual and local fallback paths.
5. Exports a content-addressed offline exchange bundle.
6. Records scope-limited contributions and attribution.
7. Issues non-transferable, non-financial true-value receipts only after world effects are observed.
8. Proactively publishes open calls for missing contributions.

## Five-minute run

Requires Python 3.10+ and no third-party runtime dependency.

```bash
python start_showcase.py
```

Open:

```text
http://127.0.0.1:8784
```

Or double-click `index.html` for an offline browser-only experience.

## CLI walkthrough

```bash
python run.py create-capsule \
  examples/cross_border_local_knowledge.json \
  --out outputs/capsule.json

python run.py route \
  outputs/capsule.json \
  examples/profile_manual_only.json \
  --out outputs/route.json

python run.py bundle \
  outputs/capsule.json \
  outputs/route.json \
  --out outputs/cooperation_bundle.zip

python run.py verify-bundle outputs/cooperation_bundle.zip
```

## Core invariants

- `person_grade_absent = true`
- `social_credit = false`
- `financial_asset = false`
- `controls_bypassed = false`
- `manual_path_required = true`
- `world_effect_required = true`
- `correction_required = true`
- `non_core_semantic_authority = 0`

## Why this exists

The public `YucongDuan` GitHub profile displayed 363 repositories on 18 August 2026. The portfolio contains a large and recent stream of closely related truth, responsibility, artificial-consciousness, medicine, justice and MESH systems. Repository count is not a quality score, but it creates a navigation and cooperation bottleneck. COMMONBRIDGE-85 is designed as a single public cooperation protocol and entry point rather than another theory-only endpoint.

The system also responds to a wider global pattern:

- the EU AI Act uses a risk-based framework and prohibits certain social-scoring uses;
- China requires registration of certain public generative-AI services and has binding AI-generated-content labelling rules;
- US export controls restrict defined advanced-computing items, end uses and end users;
- UNESCO's AI ethics recommendation calls for human rights, dignity, inclusion, transparency, accountability and environmental sustainability.

Regulation is necessary in many settings, but capability fragmentation must not silently become a permanent ranking of human beings. COMMONBRIDGE-85 keeps lawful cooperation, local knowledge, manual participation, provenance and appeal available.

## Explicit non-goals

This project does not provide:

- VPN, proxy, Tor, tunnelling or censorship-evasion functions;
- credential theft, account sharing or access-control bypass;
- export-control or sanctions evasion;
- removal or falsification of AI-generated-content labels;
- legal advice about any jurisdiction;
- automatic medical, legal, financial, employment or public-safety decisions;
- persistent person scoring or ideological profiling;
- a cryptocurrency, tradeable reputation token or social-credit score.

## Governance

The public core is Apache-2.0. Contributions must preserve provenance, non-person-ranking, no-circumvention and non-financial true-value boundaries. High-impact domain adapters require separate qualified review and institutional authorization.

Conceptual origin: **Yucong Duan / DIKWP**.


## Engineering verification

The current release passed:

- unit tests: 27/27;
- static structure and safety-boundary checks: 34/34;
- HTTP end-to-end acceptance: 7/7;
- JavaScript syntax check: passed;
- total: 68/68.

These results establish engineering consistency in synthetic conditions. They are not regulatory certification, proof of real-world value, or production-browser certification.
