from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile
from typing import Any, Iterable

VERSION = "1.0.0"
SYSTEM_NAME = "DIKWP COMMONBRIDGE-85"
SYSTEM_NAME_ZH = "共桥 COMMONBRIDGE-85"
ORIGIN = {
    "conceptual_origin": "Yucong Duan / DIKWP",
    "portfolio_profile": "https://github.com/YucongDuan",
    "system": SYSTEM_NAME,
    "version": VERSION,
}

# These are environment envelopes, never person grades. A profile expires and may change by place/time.
CAPABILITY_TIERS: dict[str, dict[str, Any]] = {
    "H0_MANUAL": {
        "rank": 0,
        "label_zh": "纯人工／无AI",
        "label_en": "Human-only / no AI",
        "network": False,
        "model": "none",
    },
    "A1_LOCAL_RULES": {
        "rank": 1,
        "label_zh": "本地规则与轻量工具",
        "label_en": "Local rules and lightweight tools",
        "network": False,
        "model": "rules",
    },
    "A2_SMALL_LOCAL": {
        "rank": 2,
        "label_zh": "小型本地模型",
        "label_en": "Small local model",
        "network": False,
        "model": "small_local",
    },
    "A3_LIMITED_HOSTED": {
        "rank": 3,
        "label_zh": "受限云端模型",
        "label_en": "Limited hosted model",
        "network": True,
        "model": "limited_hosted",
    },
    "A4_ADVANCED_HOSTED": {
        "rank": 4,
        "label_zh": "高级云端模型",
        "label_en": "Advanced hosted model",
        "network": True,
        "model": "advanced_hosted",
    },
    "A5_INSTITUTIONAL_AGENT": {
        "rank": 5,
        "label_zh": "机构级代理与工具",
        "label_en": "Institutional agent and tools",
        "network": True,
        "model": "institutional_agent",
    },
}

TRUE_VALUE_DIMENSIONS: tuple[str, ...] = (
    "truth_access",
    "autonomy",
    "care",
    "repair",
    "recognition",
    "learning",
    "future_options",
    "ecological_continuity",
    "community_trust",
    "time_return",
)

HIGH_STAKES_DOMAINS = {"medical", "legal", "financial", "employment", "public_safety"}

DEFAULT_TASK_TEMPLATES = [
    {
        "task_type": "source_map",
        "title_zh": "建立来源与版本图",
        "title_en": "Map sources and versions",
        "min_tier": "H0_MANUAL",
        "manual_fallback": True,
        "required_skills": ["reading", "source_checking"],
        "sensitivity": "public",
        "true_value": ["truth_access", "recognition"],
    },
    {
        "task_type": "local_context",
        "title_zh": "补充本地语境与缺席世界",
        "title_en": "Add local context and absent worlds",
        "min_tier": "H0_MANUAL",
        "manual_fallback": True,
        "required_skills": ["local_knowledge", "listening"],
        "sensitivity": "community",
        "true_value": ["autonomy", "care", "future_options"],
    },
    {
        "task_type": "translation",
        "title_zh": "翻译并保留语义差异",
        "title_en": "Translate while preserving semantic differences",
        "min_tier": "A1_LOCAL_RULES",
        "manual_fallback": True,
        "required_skills": ["translation"],
        "sensitivity": "public",
        "true_value": ["truth_access", "learning"],
    },
    {
        "task_type": "structured_synthesis",
        "title_zh": "形成D/I/K/W/P协作骨架",
        "title_en": "Build a D/I/K/W/P collaboration scaffold",
        "min_tier": "A2_SMALL_LOCAL",
        "manual_fallback": True,
        "required_skills": ["analysis", "structured_writing"],
        "sensitivity": "public",
        "true_value": ["truth_access", "learning", "time_return"],
    },
    {
        "task_type": "independent_check",
        "title_zh": "独立复核关键主张",
        "title_en": "Independently check decisive claims",
        "min_tier": "A2_SMALL_LOCAL",
        "manual_fallback": True,
        "required_skills": ["verification", "domain_review"],
        "sensitivity": "controlled",
        "true_value": ["truth_access", "community_trust"],
    },
    {
        "task_type": "world_effect",
        "title_zh": "观察现实结果并纠错",
        "title_en": "Observe world effects and correct",
        "min_tier": "H0_MANUAL",
        "manual_fallback": True,
        "required_skills": ["observation", "feedback"],
        "sensitivity": "controlled",
        "true_value": ["repair", "care", "future_options"],
    },
]


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        chunks = re.split(r"[\n,，;；]+", value)
        return [x.strip() for x in chunks if x.strip()]
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.casefold().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _bounded_list(items: Iterable[str], n: int = 12) -> list[str]:
    return _unique(items)[:n]


def _safe_slug(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff_-]+", "-", text.strip())
    return re.sub(r"-+", "-", text).strip("-")[:60] or "capsule"


def _tier_rank(tier: str) -> int:
    return int(CAPABILITY_TIERS.get(tier, CAPABILITY_TIERS["H0_MANUAL"])["rank"])


def _normalize_value_vector(value: Any) -> dict[str, dict[str, Any]]:
    selected = set(_strings(value))
    out: dict[str, dict[str, Any]] = {}
    for dim in TRUE_VALUE_DIMENSIONS:
        out[dim] = {
            "declared": dim in selected,
            "evidence": [],
            "observed": False,
        }
    return out


def _task_from_template(template: dict[str, Any], index: int, capsule_id: str) -> dict[str, Any]:
    task = {
        "task_id": f"task-{index:02d}-{_digest([capsule_id, template['task_type']])[:10]}",
        "task_type": template["task_type"],
        "title_zh": template["title_zh"],
        "title_en": template["title_en"],
        "min_tier": template["min_tier"],
        "manual_fallback": bool(template["manual_fallback"]),
        "required_skills": list(template["required_skills"]),
        "sensitivity": template["sensitivity"],
        "true_value": list(template["true_value"]),
        "status": "OPEN",
        "owner": None,
        "deadline": None,
        "result_required": True,
    }
    return task


def compile_capsule(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile a cooperation request into a capability-neutral DIKWP capsule.

    The capsule never ranks persons. It describes a current environment and decomposes work
    into tasks that can be performed manually or with lawful tools.
    """
    title = str(payload.get("title") or payload.get("goal") or "Untitled cooperation").strip()
    purpose = str(payload.get("purpose") or payload.get("goal") or "").strip()
    problem = str(payload.get("problem") or payload.get("context") or "").strip()
    sources = _bounded_list(_strings(payload.get("sources")))
    differences = _bounded_list(_strings(payload.get("differences") or payload.get("uncertainties")))
    understanding = str(payload.get("understanding") or "").strip()
    affected = _bounded_list(_strings(payload.get("affected")))
    constraints = _bounded_list(_strings(payload.get("constraints")))
    local_needs = _bounded_list(_strings(payload.get("local_needs")))
    languages = _bounded_list(_strings(payload.get("languages") or ["zh-CN", "en"]))
    domain = str(payload.get("domain") or "general").strip().lower()
    deadline = str(payload.get("deadline") or "").strip() or None
    values = _normalize_value_vector(payload.get("true_values") or ["truth_access", "autonomy", "recognition"])

    provisional = {
        "schema": "dikwp-commonbridge.capsule/1.0",
        "version": VERSION,
        "created_at": _now(),
        "title": title,
        "purpose": purpose,
        "domain": domain,
        "language_set": languages,
        "identity_policy": {
            "person_grade_absent": True,
            "pseudonym_allowed": True,
            "identity_disclosure_minimized": True,
            "right_to_correct_attribution": True,
            "right_to_withdraw_private_identity": True,
        },
        "lawful_resilience": {
            "bypass_controls": False,
            "credential_evasion": False,
            "network_circumvention": False,
            "policy_adaptation_only": True,
            "manual_path_required": True,
        },
        "dikwp": {
            "D": {
                "problem_statement": problem,
                "sources": sources,
                "local_needs": local_needs,
            },
            "I": {
                "differences_and_uncertainties": differences,
                "constraints": constraints,
                "absent_worlds": _bounded_list(_strings(payload.get("absent_worlds"))),
            },
            "K": {
                "current_understanding": understanding or "OPEN_UNDERSTANDING",
                "scope": str(payload.get("scope") or "bounded to this capsule"),
            },
            "W": {
                "affected_parties": affected,
                "true_value_vector": values,
                "non_money_value_required": True,
            },
            "P": {
                "purpose": purpose or "OPEN_PURPOSE",
                "primary_action": str(payload.get("primary_action") or "Create the first verifiable contribution shard."),
                "deadline": deadline,
                "world_effect_required": True,
                "correction_required": True,
            },
        },
        "tasks": [],
        "mesh85": {
            "semantic_11111": True,
            "active_responsibility": "OPEN_UNTIL_ROUTED",
            "substantive_protection": "IDENTITY_AND_ACCESS_PROTECTED",
            "truth_preserving_disclosure": "SOURCE_BOUND",
            "authority_chain": "NO_HIGH_IMPACT_AUTHORITY_CLAIMED",
            "world_effect_and_correction": "OPEN",
        },
        "origin": ORIGIN,
    }
    provisional["capsule_id"] = "bridge-" + _digest(provisional)[:16]

    explicit_tasks = payload.get("tasks")
    if isinstance(explicit_tasks, list) and explicit_tasks:
        tasks: list[dict[str, Any]] = []
        for index, raw in enumerate(explicit_tasks, start=1):
            if not isinstance(raw, dict):
                continue
            min_tier = str(raw.get("min_tier") or "H0_MANUAL")
            if min_tier not in CAPABILITY_TIERS:
                min_tier = "H0_MANUAL"
            tasks.append({
                "task_id": str(raw.get("task_id") or f"task-{index:02d}-{_digest(raw)[:10]}"),
                "task_type": str(raw.get("task_type") or "custom"),
                "title_zh": str(raw.get("title_zh") or raw.get("title") or f"任务 {index}"),
                "title_en": str(raw.get("title_en") or raw.get("title") or f"Task {index}"),
                "min_tier": min_tier,
                "manual_fallback": bool(raw.get("manual_fallback", True)),
                "required_skills": _strings(raw.get("required_skills")),
                "sensitivity": str(raw.get("sensitivity") or "public"),
                "true_value": _strings(raw.get("true_value")) or ["truth_access"],
                "status": "OPEN",
                "owner": raw.get("owner"),
                "deadline": raw.get("deadline") or deadline,
                "result_required": True,
            })
        provisional["tasks"] = tasks
    else:
        provisional["tasks"] = [
            _task_from_template(t, i, provisional["capsule_id"])
            for i, t in enumerate(DEFAULT_TASK_TEMPLATES, start=1)
        ]
        for task in provisional["tasks"]:
            task["deadline"] = deadline

    provisional["sha256"] = _digest(provisional)
    return provisional


def normalize_environment_profile(profile: dict[str, Any]) -> dict[str, Any]:
    tier = str(profile.get("tier") or "H0_MANUAL")
    if tier not in CAPABILITY_TIERS:
        tier = "H0_MANUAL"
    normalized = {
        "schema": "dikwp-commonbridge.environment-profile/1.0",
        "profile_id": str(profile.get("profile_id") or f"profile-{_digest(profile)[:12]}"),
        "declared_at": str(profile.get("declared_at") or _now()),
        "expires_at": profile.get("expires_at"),
        "tier": tier,
        "tier_is_person_grade": False,
        "jurisdiction_label": str(profile.get("jurisdiction_label") or "USER_DECLARED"),
        "network_available": bool(profile.get("network_available", CAPABILITY_TIERS[tier]["network"])),
        "cloud_ai_allowed": bool(profile.get("cloud_ai_allowed", tier in {"A3_LIMITED_HOSTED", "A4_ADVANCED_HOSTED", "A5_INSTITUTIONAL_AGENT"})),
        "local_ai_allowed": bool(profile.get("local_ai_allowed", tier in {"A2_SMALL_LOCAL", "A3_LIMITED_HOSTED", "A4_ADVANCED_HOSTED", "A5_INSTITUTIONAL_AGENT"})),
        "data_export": str(profile.get("data_export") or "public_only"),
        "identity_disclosure": str(profile.get("identity_disclosure") or "pseudonymous"),
        "generated_content_label_required": bool(profile.get("generated_content_label_required", True)),
        "qualified_review_available": bool(profile.get("qualified_review_available", False)),
        "languages": _strings(profile.get("languages") or ["zh-CN"]),
        "skills": _strings(profile.get("skills")),
        "constraints": _strings(profile.get("constraints")),
        "source": "user_declared_not_legal_advice",
    }
    normalized["sha256"] = _digest(normalized)
    return normalized


def _policy_allows_task(task: dict[str, Any], capsule: dict[str, Any], profile: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    domain = str(capsule.get("domain") or "general")
    if domain in HIGH_STAKES_DOMAINS and task.get("task_type") in {"structured_synthesis", "independent_check"}:
        if not profile.get("qualified_review_available"):
            reasons.append("qualified_review_missing_for_high_stakes_domain")
    if task.get("sensitivity") == "private" and profile.get("data_export") not in {"none", "local_only"}:
        reasons.append("private_data_must_remain_local")
    return (not reasons, reasons)


def _fallback_for_task(task: dict[str, Any], profile: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    if "qualified_review_missing_for_high_stakes_domain" in reasons:
        return {
            "route": "HOLD_AND_PREPARE_REVIEW_PACKET",
            "instructions": [
                "Prepare sources, differences and a bounded question without issuing a high-impact conclusion.",
                "Request a qualified reviewer only for the decisive step.",
            ],
        }
    if "private_data_must_remain_local" in reasons:
        return {
            "route": "LOCAL_EXECUTION_EXPORT_HASH_AND_SUMMARY",
            "instructions": [
                "Keep raw data local.",
                "Export only a schema, aggregate, redacted summary or content hash when lawful.",
            ],
        }
    if task.get("manual_fallback"):
        return {
            "route": "MANUAL_FALLBACK",
            "instructions": [
                "Use the task checklist without an AI model.",
                "Record sources and the result hash in the same capsule format.",
            ],
        }
    return {"route": "NO_LAWFUL_PATH_YET", "instructions": ["Keep the task open; do not bypass controls."]}


def route_capsule(capsule: dict[str, Any], raw_profile: dict[str, Any]) -> dict[str, Any]:
    profile = normalize_environment_profile(raw_profile)
    tier = profile["tier"]
    current_rank = _tier_rank(tier)
    routed_tasks: list[dict[str, Any]] = []

    for task in capsule.get("tasks", []):
        min_rank = _tier_rank(str(task.get("min_tier") or "H0_MANUAL"))
        allowed, reasons = _policy_allows_task(task, capsule, profile)
        if not allowed:
            fallback = _fallback_for_task(task, profile, reasons)
            status = "HOLD_POLICY_OR_REVIEW"
        elif min_rank <= current_rank:
            if task.get("min_tier") in {"A3_LIMITED_HOSTED", "A4_ADVANCED_HOSTED", "A5_INSTITUTIONAL_AGENT"} and not profile.get("cloud_ai_allowed"):
                fallback = _fallback_for_task(task, profile, ["cloud_ai_not_allowed"])
                status = "READY_WITH_FALLBACK" if fallback["route"] != "NO_LAWFUL_PATH_YET" else "OPEN"
            else:
                fallback = {
                    "route": "DIRECT_WITHIN_DECLARED_ENVELOPE",
                    "instructions": [
                        "Use only declared tools and data.",
                        "Label generated content when required.",
                        "Return sources, output hash and unresolved differences.",
                    ],
                }
                status = "READY"
        elif task.get("manual_fallback"):
            fallback = _fallback_for_task(task, profile, [])
            status = "READY_MANUAL"
        else:
            fallback = _fallback_for_task(task, profile, ["tier_insufficient"])
            status = "OPEN"

        routed = {
            "task_id": task.get("task_id"),
            "task_type": task.get("task_type"),
            "title_zh": task.get("title_zh"),
            "title_en": task.get("title_en"),
            "required_tier": task.get("min_tier"),
            "current_environment_tier": tier,
            "status": status,
            "route": fallback["route"],
            "instructions": fallback["instructions"],
            "policy_reasons": reasons,
            "required_skills": task.get("required_skills", []),
            "true_value": task.get("true_value", []),
            "person_grade_absent": True,
        }
        routed_tasks.append(routed)

    ready = [t for t in routed_tasks if t["status"] in {"READY", "READY_MANUAL", "READY_WITH_FALLBACK"}]
    primary = ready[0] if ready else (routed_tasks[0] if routed_tasks else None)
    route = {
        "schema": "dikwp-commonbridge.route-plan/1.0",
        "version": VERSION,
        "created_at": _now(),
        "capsule_id": capsule.get("capsule_id"),
        "capsule_sha256": capsule.get("sha256"),
        "profile": profile,
        "primary_action": {
            "task_id": primary.get("task_id") if primary else None,
            "title_zh": primary.get("title_zh") if primary else "没有可执行任务",
            "title_en": primary.get("title_en") if primary else "No executable task",
            "route": primary.get("route") if primary else "OPEN",
        },
        "tasks": routed_tasks,
        "inclusion": {
            "manual_path_count": sum(1 for t in routed_tasks if t["status"] == "READY_MANUAL" or t["route"] == "MANUAL_FALLBACK"),
            "ready_count": len(ready),
            "blocked_count": sum(1 for t in routed_tasks if t["status"] == "HOLD_POLICY_OR_REVIEW"),
            "no_person_ranking": True,
        },
        "lawful_resilience": {
            "controls_bypassed": False,
            "tasks_transformed_not_evaded": True,
            "manual_or_local_fallback_preferred": True,
        },
        "mesh85": {
            "semantic_11111": True,
            "active_responsibility": "PRIMARY_ACTION_SELECTED" if primary else "OPEN",
            "substantive_protection": "ACCESS_AND_IDENTITY_PROTECTED",
            "truth_preserving_disclosure": "PROFILE_AND_ROUTE_EXPLICIT",
            "authority_chain": "NO_EXTERNAL_EXECUTION_AUTHORITY",
            "world_effect_and_correction": "OPEN",
        },
        "origin": ORIGIN,
    }
    route["route_id"] = "route-" + _digest(route)[:16]
    route["sha256"] = _digest(route)
    return route


def record_contribution(capsule: dict[str, Any], route: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    raw_task_id = str(payload.get("task_id") or "").strip()
    if not raw_task_id or raw_task_id.upper().startswith("REPLACE_"):
        raw_task_id = str(route.get("primary_action", {}).get("task_id") or "").strip()
    task_id = raw_task_id
    task = next((t for t in route.get("tasks", []) if t.get("task_id") == task_id), None)
    if task is None and payload.get("task_type"):
        requested_type = str(payload.get("task_type")).strip()
        task = next((t for t in route.get("tasks", []) if str(t.get("task_type")) == requested_type), None)
        task_id = str(task.get("task_id")) if task else task_id
    if task is None:
        raise ValueError("task_id is not present in route plan")
    contributor = str(payload.get("contributor") or "anonymous-contributor").strip()
    summary = str(payload.get("summary") or "").strip()
    artifacts = _strings(payload.get("artifacts"))
    sources = _strings(payload.get("sources"))
    unresolved = _strings(payload.get("unresolved"))
    review = str(payload.get("review_status") or "PENDING_PEER_REVIEW")

    contribution = {
        "schema": "dikwp-commonbridge.contribution/1.0",
        "version": VERSION,
        "created_at": _now(),
        "capsule_id": capsule.get("capsule_id"),
        "route_id": route.get("route_id"),
        "task": {
            "task_id": task_id,
            "task_type": task.get("task_type"),
            "route": task.get("route"),
        },
        "contributor": {
            "display_id": contributor,
            "pseudonymous_allowed": True,
            "identity_not_ranked": True,
            "person_score_absent": True,
        },
        "result": {
            "summary": summary,
            "artifacts": artifacts,
            "artifact_hashes": [hashlib.sha256(a.encode("utf-8")).hexdigest() for a in artifacts],
            "sources": sources,
            "unresolved": unresolved,
            "review_status": review,
        },
        "rights": {
            "attribution_required": True,
            "right_to_correct": True,
            "right_to_dispute_use": True,
            "private_identity_withdrawal_supported": True,
        },
        "origin": ORIGIN,
    }
    contribution["contribution_id"] = "contrib-" + _digest(contribution)[:16]
    contribution["sha256"] = _digest(contribution)
    return contribution


def issue_true_value_receipt(contribution: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    observed = bool(outcome.get("observed", False))
    categories = _strings(outcome.get("categories"))
    invalid_categories = [x for x in categories if x not in TRUE_VALUE_DIMENSIONS]
    if invalid_categories:
        raise ValueError(f"unsupported true-value categories: {', '.join(invalid_categories)}")
    evidence = _strings(outcome.get("evidence"))
    benefited = _strings(outcome.get("benefited"))
    burdened = _strings(outcome.get("burdened"))
    correction = str(outcome.get("correction") or "").strip()
    status = "OBSERVED_SCOPE_LIMITED" if observed and evidence else "PROVISIONAL_NOT_YET_OBSERVED"
    if correction or burdened:
        status = "REOPENED_FOR_CORRECTION"

    vector = {}
    for dim in TRUE_VALUE_DIMENSIONS:
        vector[dim] = {
            "claimed": dim in categories,
            "observed": bool(observed and dim in categories and evidence),
            "evidence": evidence if dim in categories else [],
        }

    receipt = {
        "schema": "dikwp-commonbridge.true-value-receipt/1.0",
        "version": VERSION,
        "created_at": _now(),
        "status": status,
        "contribution_id": contribution.get("contribution_id"),
        "contribution_sha256": contribution.get("sha256"),
        "scope": {
            "capsule_id": contribution.get("capsule_id"),
            "task_id": contribution.get("task", {}).get("task_id"),
            "not_a_person_grade": True,
        },
        "true_value_vector": vector,
        "world_effect": {
            "observed": observed,
            "summary": str(outcome.get("summary") or "").strip(),
            "evidence": evidence,
            "benefited": benefited,
            "burdened": burdened,
            "affected_feedback": _strings(outcome.get("affected_feedback")),
            "correction": correction or None,
            "review_date": outcome.get("review_date"),
        },
        "currency_boundary": {
            "financial_asset": False,
            "transferable": False,
            "tradeable": False,
            "convertible_to_person_rank": False,
            "social_credit": False,
            "scope_limited": True,
            "revocable_on_new_evidence": True,
        },
        "origin": ORIGIN,
    }
    receipt["receipt_id"] = "value-" + _digest(receipt)[:16]
    receipt["sha256"] = _digest(receipt)
    return receipt


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_exchange_bundle(
    capsule: dict[str, Any],
    route: dict[str, Any],
    output_path: str | Path,
    contributions: list[dict[str, Any]] | None = None,
    receipts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a content-addressed, delay-tolerant collaboration bundle.

    This is for lawful offline exchange through user-controlled channels. It contains no network,
    proxy, credential or execution bypass capability.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    files: dict[str, bytes] = {
        "capsule.json": (json.dumps(capsule, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        "route.json": (json.dumps(route, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        "README.txt": (
            "DIKWP COMMONBRIDGE-85 exchange bundle\n"
            "This bundle adapts cooperation to declared capability and policy envelopes.\n"
            "It does not bypass network, identity, export-control or platform restrictions.\n"
            "Verify MANIFEST.json before use.\n"
        ).encode("utf-8"),
    }
    for i, item in enumerate(contributions or [], start=1):
        files[f"contributions/{i:03d}-{item.get('contribution_id','unknown')}.json"] = (
            json.dumps(item, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
    for i, item in enumerate(receipts or [], start=1):
        files[f"receipts/{i:03d}-{item.get('receipt_id','unknown')}.json"] = (
            json.dumps(item, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")

    manifest = {
        "schema": "dikwp-commonbridge.bundle-manifest/1.0",
        "created_at": _now(),
        "system": SYSTEM_NAME,
        "version": VERSION,
        "files": {
            name: {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
            for name, data in sorted(files.items())
        },
        "safety": {
            "contains_proxy_or_vpn": False,
            "contains_credentials": False,
            "contains_external_execution": False,
            "lawful_user_controlled_exchange_only": True,
        },
        "origin": ORIGIN,
    }
    manifest_data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    # Fixed timestamps make repeated builds stable enough for verification workflows.
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.flag_bits |= 0x800
            zf.writestr(info, data)
        info = zipfile.ZipInfo("MANIFEST.json", date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        info.flag_bits |= 0x800
        zf.writestr(info, manifest_data)

    result = {
        "path": str(output_path),
        "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "size": output_path.stat().st_size,
        "file_count": len(files) + 1,
        "manifest": manifest,
    }
    return result


def verify_exchange_bundle(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    errors: list[str] = []
    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        unsafe = [n for n in names if n.startswith("/") or ".." in Path(n).parts]
        if unsafe:
            errors.append(f"unsafe paths: {unsafe}")
        if "MANIFEST.json" not in names:
            errors.append("MANIFEST.json missing")
            return {"valid": False, "errors": errors}
        manifest = json.loads(zf.read("MANIFEST.json"))
        for name, meta in manifest.get("files", {}).items():
            if name not in names:
                errors.append(f"missing file: {name}")
                continue
            data = zf.read(name)
            if hashlib.sha256(data).hexdigest() != meta.get("sha256"):
                errors.append(f"hash mismatch: {name}")
            if len(data) != meta.get("size"):
                errors.append(f"size mismatch: {name}")
    return {
        "valid": not errors,
        "errors": errors,
        "bundle_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "file_count": len(names),
    }


def generate_open_calls(capsules: list[dict[str, Any]], routes: list[dict[str, Any]], contributions: list[dict[str, Any]]) -> dict[str, Any]:
    completed = {c.get("task", {}).get("task_id") for c in contributions}
    route_by_capsule = {r.get("capsule_id"): r for r in routes}
    calls: list[dict[str, Any]] = []
    for capsule in capsules:
        route = route_by_capsule.get(capsule.get("capsule_id"))
        route_tasks = {t.get("task_id"): t for t in (route or {}).get("tasks", [])}
        for task in capsule.get("tasks", []):
            if task.get("task_id") in completed:
                continue
            routed = route_tasks.get(task.get("task_id"), {})
            # Inclusion-first priority: manual tasks and local knowledge come first.
            inclusion_bonus = 3 if task.get("min_tier") == "H0_MANUAL" else 2 if task.get("manual_fallback") else 0
            value_bonus = len(task.get("true_value", []))
            calls.append({
                "call_id": "call-" + _digest([capsule.get("capsule_id"), task.get("task_id")])[:14],
                "capsule_id": capsule.get("capsule_id"),
                "project": capsule.get("title"),
                "task_id": task.get("task_id"),
                "title_zh": task.get("title_zh"),
                "title_en": task.get("title_en"),
                "available_route": routed.get("route") or "UNROUTED",
                "min_tier": task.get("min_tier"),
                "manual_fallback": bool(task.get("manual_fallback")),
                "required_skills": task.get("required_skills", []),
                "true_value": task.get("true_value", []),
                "priority": inclusion_bonus + value_bonus,
                "money_required": False,
                "person_rank_required": False,
            })
    calls.sort(key=lambda x: (-x["priority"], x["project"], x["task_id"]))
    result = {
        "schema": "dikwp-commonbridge.open-calls/1.0",
        "generated_at": _now(),
        "count": len(calls),
        "calls": calls,
        "primary_action": calls[0] if calls else None,
        "origin": ORIGIN,
    }
    result["sha256"] = _digest(result)
    return result


def portfolio_snapshot() -> dict[str, Any]:
    return {
        "snapshot_date": "2026-08-18",
        "public_repositories": 363,
        "account_projects": 0,
        "account_packages": 0,
        "stars_tab": 583,
        "followers": 663,
        "interpretation": [
            "Repository count is a portfolio-navigation fact, not a quality score.",
            "The recent stream contains many closely related responsibility, truth, medicine and artificial-consciousness systems.",
            "COMMONBRIDGE-85 is designed as a cooperation protocol and public entry point, not another theory-only endpoint.",
        ],
        "source": "https://github.com/YucongDuan?tab=repositories",
    }


def summary() -> dict[str, Any]:
    return {
        "status": "ok",
        "system": SYSTEM_NAME,
        "system_zh": SYSTEM_NAME_ZH,
        "version": VERSION,
        "tagline": "Any person. Any lawful AI tier. One verifiable contribution.",
        "capability_tiers": CAPABILITY_TIERS,
        "true_value_dimensions": list(TRUE_VALUE_DIMENSIONS),
        "invariants": {
            "no_person_grading": True,
            "no_social_credit": True,
            "no_financial_token": True,
            "no_control_circumvention": True,
            "manual_fallback": True,
            "offline_exchange": True,
            "world_effect_required": True,
        },
        "portfolio_snapshot": portfolio_snapshot(),
        "origin": ORIGIN,
    }
