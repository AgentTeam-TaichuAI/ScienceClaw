from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence


FUNCTION_GROUP_LABELS: Dict[str, str] = {
    "knowledge_literature": "知识与文献",
    "data_resources": "数据与资源",
    "database_api": "数据库与 API",
    "models_prediction": "模型与预测",
    "analysis_workflow": "分析与工作流",
    "clinical_guidelines": "临床与规范",
    "workspace_authoring": "工作区与写作",
}

DISCIPLINE_LABELS: Dict[str, str] = {
    "life_science": "生命科学",
    "chem_drug": "化学与药物",
    "protein_structure": "蛋白与结构生物学",
    "materials_science": "材料科学",
    "clinical_medical": "临床与医学",
    "earth_environment": "地球与环境",
    "general_compute": "跨学科与通用研究",
    "writing_automation": "研究写作与知识管理",
    "other": "其他",
}

# Temporary aliases kept for compatibility while the frontend migrates.
SYSTEM_GROUP_LABELS = FUNCTION_GROUP_LABELS
SYSTEM_SUBGROUP_LABELS = DISCIPLINE_LABELS

_WORD_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class PhraseRule:
    key: str
    phrases: tuple[str, ...]


@dataclass(frozen=True)
class WeightedText:
    source: str
    text: str
    weight: int


_FUNCTION_GROUP_ALIASES: Dict[str, str] = {
    "knowledge_literature": "knowledge_literature",
    "knowledge literature": "knowledge_literature",
    "literature": "knowledge_literature",
    "paper": "knowledge_literature",
    "papers": "knowledge_literature",
    "citation": "knowledge_literature",
    "data_resources": "data_resources",
    "data resources": "data_resources",
    "dataset": "data_resources",
    "datasets": "data_resources",
    "resource": "data_resources",
    "resources": "data_resources",
    "database_api": "database_api",
    "database api": "database_api",
    "database": "database_api",
    "api": "database_api",
    "registry": "database_api",
    "portal": "database_api",
    "models_prediction": "models_prediction",
    "models prediction": "models_prediction",
    "model": "models_prediction",
    "models": "models_prediction",
    "prediction": "models_prediction",
    "analysis_workflow": "analysis_workflow",
    "analysis workflow": "analysis_workflow",
    "analysis": "analysis_workflow",
    "workflow": "analysis_workflow",
    "clinical_guidelines": "clinical_guidelines",
    "clinical guidelines": "clinical_guidelines",
    "guideline": "clinical_guidelines",
    "guidelines": "clinical_guidelines",
    "structured product labeling": "clinical_guidelines",
    "workspace_authoring": "workspace_authoring",
    "workspace authoring": "workspace_authoring",
    "workspace": "workspace_authoring",
    "authoring": "workspace_authoring",
    "obsidian": "workspace_authoring",
    "review bundle": "workspace_authoring",
}

_DISCIPLINE_ALIASES: Dict[str, str] = {
    "life_science": "life_science",
    "life science": "life_science",
    "biology": "life_science",
    "bio": "life_science",
    "chem_drug": "chem_drug",
    "chem drug": "chem_drug",
    "chemistry": "chem_drug",
    "drug": "chem_drug",
    "protein_structure": "protein_structure",
    "protein structure": "protein_structure",
    "structure biology": "protein_structure",
    "materials_science": "materials_science",
    "materials science": "materials_science",
    "material science": "materials_science",
    "mat sci": "materials_science",
    "matsci": "materials_science",
    "clinical_medical": "clinical_medical",
    "clinical medical": "clinical_medical",
    "clinical": "clinical_medical",
    "medical": "clinical_medical",
    "medicine": "clinical_medical",
    "earth_environment": "earth_environment",
    "earth environment": "earth_environment",
    "earth": "earth_environment",
    "environment": "earth_environment",
    "general_compute": "general_compute",
    "general compute": "general_compute",
    "cross domain": "general_compute",
    "cross-domain": "general_compute",
    "general research": "general_compute",
    "writing_automation": "writing_automation",
    "writing automation": "writing_automation",
    "research writing": "writing_automation",
    "knowledge management": "writing_automation",
    "obsidian": "writing_automation",
    "zotero": "writing_automation",
    "review bundle": "writing_automation",
    "other": "other",
}

_SCIENCE_FAMILY_FUNCTION_GROUP_MAP: Dict[str, str] = {
    "ada_aha_nccn": "clinical_guidelines",
    "admetai": "models_prediction",
    "alphafold": "models_prediction",
    "alphamissense": "models_prediction",
    "arxiv": "knowledge_literature",
    "bigg_models": "models_prediction",
    "bioimage_archive": "data_resources",
    "biomodels_tools": "models_prediction",
    "biorxiv": "knowledge_literature",
    "biorxiv_ext": "knowledge_literature",
    "bioportal": "analysis_workflow",
    "biosamples": "data_resources",
    "biostudies": "data_resources",
    "blast": "analysis_workflow",
    "cellxgene_census": "data_resources",
    "cellxgene_discovery": "database_api",
    "clinical_guidelines": "clinical_guidelines",
    "clinical_trials": "clinical_guidelines",
    "clingen": "clinical_guidelines",
    "clingen_ar": "clinical_guidelines",
    "clingen_dosage": "clinical_guidelines",
    "clinvar": "clinical_guidelines",
    "core": "knowledge_literature",
    "cpic": "clinical_guidelines",
    "crossref": "knowledge_literature",
    "datacite": "data_resources",
    "dataset": "data_resources",
    "dataone": "data_resources",
    "dataverse": "data_resources",
    "dailymed": "clinical_guidelines",
    "deepgo": "models_prediction",
    "europepmc": "knowledge_literature",
    "europepmc_annotations": "knowledge_literature",
    "europepmc_citations": "knowledge_literature",
    "fda_drug_adverse_event": "clinical_guidelines",
    "fda_drug_adverse_event_detail": "clinical_guidelines",
    "fda_drug_label": "clinical_guidelines",
    "fda_orange_book": "clinical_guidelines",
    "fda_pharmacogenomic_biomarkers": "clinical_guidelines",
    "figshare": "data_resources",
    "github": "analysis_workflow",
    "guidelines": "clinical_guidelines",
    "huggingface": "models_prediction",
    "icd": "clinical_guidelines",
    "matbench": "data_resources",
    "materials_project": "database_api",
    "medlineplus": "clinical_guidelines",
    "medrxiv": "knowledge_literature",
    "modeldb": "models_prediction",
    "mp_api": "database_api",
    "mydisease": "clinical_guidelines",
    "ncbi_datasets": "data_resources",
    "openalex": "knowledge_literature",
    "openfda": "clinical_guidelines",
    "opencitations": "knowledge_literature",
    "oqmd": "database_api",
    "phonondb": "data_resources",
    "pmc": "knowledge_literature",
    "pubmed": "knowledge_literature",
    "pymatgen": "analysis_workflow",
    "semantic_scholar": "knowledge_literature",
    "semantic_scholar_ext": "knowledge_literature",
    "swissdock": "models_prediction",
    "swissmodel": "models_prediction",
    "uscensus": "data_resources",
    "vasp": "analysis_workflow",
    "zenodo": "data_resources",
}

_SCIENCE_FAMILY_DISCIPLINE_MAP: Dict[str, str] = {
    "ada_aha_nccn": "clinical_medical",
    "admetai": "chem_drug",
    "alphafold": "protein_structure",
    "alphamissense": "protein_structure",
    "arxiv": "general_compute",
    "bigg_models": "life_science",
    "bioimage_archive": "life_science",
    "biomodels_tools": "life_science",
    "biorxiv": "life_science",
    "biorxiv_ext": "life_science",
    "bioportal": "life_science",
    "blast": "life_science",
    "cellxgene_census": "life_science",
    "cellxgene_discovery": "life_science",
    "clinical_guidelines": "clinical_medical",
    "clinical_trials": "clinical_medical",
    "clingen": "clinical_medical",
    "clingen_ar": "clinical_medical",
    "clingen_dosage": "clinical_medical",
    "clinvar": "clinical_medical",
    "core": "general_compute",
    "cpic": "clinical_medical",
    "crossref": "general_compute",
    "dailymed": "clinical_medical",
    "deepgo": "life_science",
    "europepmc": "clinical_medical",
    "fda_drug_adverse_event": "clinical_medical",
    "fda_drug_adverse_event_detail": "clinical_medical",
    "fda_drug_label": "clinical_medical",
    "fda_orange_book": "clinical_medical",
    "fda_pharmacogenomic_biomarkers": "clinical_medical",
    "github": "general_compute",
    "guidelines": "clinical_medical",
    "huggingface": "general_compute",
    "icd": "clinical_medical",
    "matbench": "materials_science",
    "materials_project": "materials_science",
    "medlineplus": "clinical_medical",
    "medrxiv": "clinical_medical",
    "modeldb": "life_science",
    "mp_api": "materials_science",
    "mydisease": "clinical_medical",
    "openalex": "general_compute",
    "openfda": "clinical_medical",
    "oqmd": "materials_science",
    "phonondb": "materials_science",
    "pmc": "clinical_medical",
    "pubmed": "clinical_medical",
    "pymatgen": "materials_science",
    "semantic_scholar": "general_compute",
    "swissdock": "protein_structure",
    "swissmodel": "protein_structure",
    "vasp": "materials_science",
}

_EXTERNAL_FAMILY_FUNCTION_GROUP_MAP: Dict[str, str] = {
    "obsidian": "workspace_authoring",
    "zotero": "workspace_authoring",
}

_EXTERNAL_FAMILY_DISCIPLINE_MAP: Dict[str, str] = {
    "obsidian": "writing_automation",
    "zotero": "writing_automation",
}

_SCIENCE_TOOL_OVERRIDES: Dict[str, Dict[str, str]] = {
    "structured product labeling": {
        "function_group": "clinical_guidelines",
        "discipline": "clinical_medical",
    },
}

_EXTERNAL_TOOL_OVERRIDES: Dict[str, Dict[str, str]] = {
    "obsidian_build_zotero_review_bundle": {
        "function_group": "workspace_authoring",
        "discipline": "writing_automation",
    },
    "obsidian_import_zotero_bbt_json": {
        "function_group": "workspace_authoring",
        "discipline": "writing_automation",
    },
    "obsidian_write_materials_note": {
        "function_group": "workspace_authoring",
        "discipline": "writing_automation",
    },
}

_FUNCTION_GROUP_PHRASE_RULES: tuple[PhraseRule, ...] = (
    PhraseRule(
        "workspace_authoring",
        (
            "obsidian",
            "zotero",
            "review bundle",
            "knowledge base",
            "workspace authoring",
            "literature note",
            "vault",
            "note authoring",
        ),
    ),
    PhraseRule(
        "knowledge_literature",
        (
            "paper",
            "papers",
            "literature",
            "citation",
            "crossref",
            "semantic scholar",
            "openalex",
            "arxiv",
            "biorxiv",
            "medrxiv",
            "pubmed",
            "europepmc",
            "preprint",
        ),
    ),
    PhraseRule(
        "clinical_guidelines",
        (
            "guideline",
            "guidelines",
            "clinical trial",
            "structured product labeling",
            "drug label",
            "adverse event",
            "clinvar",
            "clingen",
            "cpic",
            "dailymed",
            "medlineplus",
            "openfda",
            "nccn",
            "icd",
        ),
    ),
    PhraseRule(
        "models_prediction",
        (
            "alphafold",
            "alphamissense",
            "predictive model",
            "prediction",
            "docking",
            "swissmodel",
            "swissdock",
            "toxicity",
            "admet",
            "bioavailability",
            "clearance",
            "missense",
        ),
    ),
    PhraseRule(
        "data_resources",
        (
            "dataset",
            "datasets",
            "archive",
            "archives",
            "biosample",
            "biostudies",
            "census",
            "dataverse",
            "figshare",
            "zenodo",
            "resource catalog",
        ),
    ),
    PhraseRule(
        "analysis_workflow",
        (
            "analysis workflow",
            "workflow",
            "annotation",
            "enrichment",
            "blast",
            "visualize",
            "visualization",
            "compare sequences",
            "optimize",
            "composer",
        ),
    ),
    PhraseRule(
        "database_api",
        (
            "materials project",
            "mp api",
            "ncbi",
            "uniprot",
            "reactome",
            "kegg",
            "brenda",
            "chembl",
            "bindingdb",
            "biotools",
            "query service",
            "database portal",
        ),
    ),
)

_DISCIPLINE_PHRASE_RULES: tuple[PhraseRule, ...] = (
    PhraseRule(
        "writing_automation",
        (
            "obsidian",
            "zotero",
            "review bundle",
            "research writing",
            "knowledge management",
            "literature note",
            "vault",
            "note authoring",
        ),
    ),
    PhraseRule(
        "clinical_medical",
        (
            "clinical",
            "medical",
            "medicine",
            "patient",
            "disease",
            "oncology",
            "cancer",
            "therapeutic",
            "pharmacogenomic",
            "structured product labeling",
            "adverse event",
        ),
    ),
    PhraseRule(
        "protein_structure",
        (
            "protein structure",
            "alphafold",
            "alphamissense",
            "swissmodel",
            "swissdock",
            "pdb",
            "residue",
            "ligand binding",
            "fold prediction",
        ),
    ),
    PhraseRule(
        "materials_science",
        (
            "materials project",
            "materials science",
            "matbench",
            "pymatgen",
            "phase diagram",
            "band structure",
            "phonon",
            "poscar",
            "vasp",
            "cif",
            "alloy",
            "crystal structure",
            "perovskite",
            "solid state",
            "formation energy",
            "elastic tensor",
            "defect chemistry",
            "surface energy",
        ),
    ),
    PhraseRule(
        "chem_drug",
        (
            "chemistry",
            "drug",
            "ligand",
            "metabolite",
            "toxicity",
            "admet",
            "pubchem",
            "chembl",
            "bindingdb",
            "pharmacology",
        ),
    ),
    PhraseRule(
        "earth_environment",
        (
            "earth system",
            "earth science",
            "climate",
            "ocean",
            "weather",
            "hydrology",
            "geology",
            "ecology",
            "biodiversity",
            "nasa earth",
        ),
    ),
    PhraseRule(
        "life_science",
        (
            "gene",
            "genome",
            "genomic",
            "rna",
            "dna",
            "cell",
            "pathway",
            "taxonomy",
            "ontology",
            "proteomics",
            "metabolomics",
            "transcriptomics",
            "epigenomics",
            "biosample",
        ),
    ),
    PhraseRule(
        "general_compute",
        (
            "github",
            "python package",
            "general purpose",
            "benchmark",
            "software engineering",
            "cross domain",
            "tooling",
        ),
    ),
)


def _normalize_token(value: Any) -> str:
    normalized = _WORD_RE.sub(" ", str(value or "").strip().lower())
    return " ".join(part for part in normalized.split() if part)


def _normalize_tokens(values: Iterable[Any]) -> List[str]:
    out: List[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            out.extend(_normalize_tokens(value))
            continue
        text = _normalize_token(value)
        if text:
            out.append(text)
    return out


def _build_text_blob(*parts: Any) -> str:
    return " ".join(_normalize_tokens(parts))


def _derive_tool_family(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    for delimiter in ("_", "-"):
        if delimiter in raw:
            prefix = raw.split(delimiter, 1)[0].strip()
            if prefix:
                return _normalize_token(prefix)
    return _normalize_token(raw)


def _contains_phrase(normalized_text: str, phrase: str) -> bool:
    if not normalized_text or not phrase:
        return False
    return f" {phrase} " in f" {normalized_text} "


def _match_alias(values: Sequence[str], aliases: Mapping[str, str]) -> str:
    for value in values:
        normalized = _normalize_token(value)
        if not normalized:
            continue
        alias = aliases.get(normalized, "")
        if alias:
            return alias
    return ""


def _match_mapping_candidates(values: Sequence[str], mapping: Mapping[str, str]) -> str:
    best_value = ""
    best_length = 0
    for value in values:
        normalized = _normalize_token(value)
        if not normalized:
            continue
        padded = f" {normalized} "
        for key, mapped_value in mapping.items():
            normalized_key = _normalize_token(key)
            if not normalized_key:
                continue
            if normalized == normalized_key:
                return mapped_value
            if (
                normalized.startswith(f"{normalized_key} ")
                or normalized.endswith(f" {normalized_key}")
                or f" {normalized_key} " in padded
            ) and len(normalized_key) > best_length:
                best_value = mapped_value
                best_length = len(normalized_key)
    return best_value


def _score_phrase_rules(texts: Sequence[WeightedText], rules: Sequence[PhraseRule]) -> tuple[str, dict[str, Any]]:
    best_key = ""
    best_score = 0
    best_hits: list[dict[str, Any]] = []

    for rule in rules:
        score = 0
        hits: list[dict[str, Any]] = []
        for phrase in rule.phrases:
            normalized_phrase = _normalize_token(phrase)
            if not normalized_phrase:
                continue
            phrase_weight = max(1, len(normalized_phrase.split()))
            for text in texts:
                if _contains_phrase(text.text, normalized_phrase):
                    increment = text.weight * phrase_weight
                    score += increment
                    hits.append(
                        {
                            "source": text.source,
                            "phrase": normalized_phrase,
                            "score": increment,
                        }
                    )
        if score > best_score:
            best_key = rule.key
            best_score = score
            best_hits = hits
    return best_key, {"score": best_score, "hits": best_hits}


def _taxonomy_payload(function_group: str, discipline: str, debug: dict[str, Any] | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "function_group": function_group,
        "function_group_zh": get_function_group_label(function_group),
        "discipline": discipline,
        "discipline_zh": get_discipline_label(discipline),
        "system_group": function_group,
        "system_group_zh": get_function_group_label(function_group),
        "system_subgroup": discipline,
        "system_subgroup_zh": get_discipline_label(discipline),
    }
    if debug is not None:
        payload["debug"] = debug
    return payload


def _build_weighted_texts(parts: Sequence[tuple[str, Any, int]]) -> List[WeightedText]:
    texts: List[WeightedText] = []
    for source, raw_value, weight in parts:
        for normalized in _normalize_tokens([raw_value]):
            texts.append(WeightedText(source=source, text=normalized, weight=weight))
    return texts


def _classify(
    *,
    name: str,
    raw_category: str = "",
    raw_subcategory: str = "",
    description: str = "",
    tool_type: str = "",
    tags: Iterable[Any] | None = None,
    function_group_overrides: Mapping[str, Dict[str, str]],
    function_group_family_map: Mapping[str, str],
    discipline_family_map: Mapping[str, str],
    fallback_function_group: str,
    fallback_discipline: str,
    include_debug: bool,
) -> Dict[str, Any]:
    normalized_name = _normalize_token(name)
    family = _derive_tool_family(name)
    normalized_tags = _normalize_tokens(tags or [])

    debug: Dict[str, Any] = {
        "normalized_name": normalized_name,
        "family": family,
        "inputs": {
            "raw_category": _normalize_token(raw_category),
            "raw_subcategory": _normalize_token(raw_subcategory),
            "tool_type": _normalize_token(tool_type),
            "tags": normalized_tags,
        },
    }

    override = function_group_overrides.get(normalized_name)
    if override:
        debug["matched_by"] = "tool_override"
        debug["override"] = override
        return _taxonomy_payload(
            override.get("function_group", fallback_function_group),
            override.get("discipline", fallback_discipline),
            debug if include_debug else None,
        )

    alias_candidates = [raw_category, raw_subcategory, tool_type]
    function_group = _match_alias(alias_candidates, _FUNCTION_GROUP_ALIASES)
    discipline = _match_alias(alias_candidates, _DISCIPLINE_ALIASES)
    if function_group or discipline:
        debug["matched_by"] = "raw_alias"
        debug["alias_match"] = {
            "function_group": function_group,
            "discipline": discipline,
        }

    mapping_candidates = [raw_category, raw_subcategory, name, family, tool_type]
    if not function_group:
        function_group = _match_mapping_candidates(mapping_candidates, function_group_family_map)
    if not discipline:
        discipline = _match_mapping_candidates(mapping_candidates, discipline_family_map)
    if (function_group or discipline) and "matched_by" not in debug:
        debug["matched_by"] = "family_or_category_mapping"
        debug["mapping_match"] = {
            "function_group": function_group,
            "discipline": discipline,
        }

    phrase_texts = _build_weighted_texts(
        (
            ("name", name, 6),
            ("raw_category", raw_category, 6),
            ("raw_subcategory", raw_subcategory, 6),
            ("family", family, 5),
            ("tool_type", tool_type, 4),
            ("tags", normalized_tags, 4),
            ("description", description, 1),
        )
    )

    if not function_group:
        function_group, group_debug = _score_phrase_rules(phrase_texts, _FUNCTION_GROUP_PHRASE_RULES)
        if function_group:
            debug["matched_by"] = "phrase_scoring"
            debug["function_group_phrase"] = group_debug
    if not discipline:
        discipline, discipline_debug = _score_phrase_rules(phrase_texts, _DISCIPLINE_PHRASE_RULES)
        if discipline:
            if "matched_by" not in debug:
                debug["matched_by"] = "phrase_scoring"
            debug["discipline_phrase"] = discipline_debug

    if not function_group:
        function_group = fallback_function_group
    if not discipline:
        discipline = fallback_discipline
    if "matched_by" not in debug:
        debug["matched_by"] = "fallback"

    return _taxonomy_payload(
        function_group,
        discipline,
        debug if include_debug else None,
    )


def get_function_group_label(group_id: str) -> str:
    return FUNCTION_GROUP_LABELS.get(group_id, FUNCTION_GROUP_LABELS["analysis_workflow"])


def get_discipline_label(discipline_id: str) -> str:
    return DISCIPLINE_LABELS.get(discipline_id, DISCIPLINE_LABELS["other"])


def get_system_group_label(group_id: str) -> str:
    return get_function_group_label(group_id)


def get_system_subgroup_label(subgroup_id: str) -> str:
    return get_discipline_label(subgroup_id)


def list_function_groups() -> List[Dict[str, str]]:
    return [{"id": key, "label": label} for key, label in FUNCTION_GROUP_LABELS.items()]


def list_disciplines() -> List[Dict[str, str]]:
    return [{"id": key, "label": label} for key, label in DISCIPLINE_LABELS.items()]


def list_system_groups() -> List[Dict[str, str]]:
    return list_function_groups()


def list_system_subgroups() -> List[Dict[str, str]]:
    return list_disciplines()


def classify_science_tool(
    *,
    name: str,
    raw_category: str = "",
    description: str = "",
    tool_type: str = "",
    include_debug: bool = False,
) -> Dict[str, Any]:
    return _classify(
        name=name,
        raw_category=raw_category,
        description=description,
        tool_type=tool_type,
        function_group_overrides=_SCIENCE_TOOL_OVERRIDES,
        function_group_family_map=_SCIENCE_FAMILY_FUNCTION_GROUP_MAP,
        discipline_family_map=_SCIENCE_FAMILY_DISCIPLINE_MAP,
        fallback_function_group="database_api",
        fallback_discipline="general_compute",
        include_debug=include_debug,
    )


def classify_external_tool(
    *,
    name: str,
    raw_category: str = "",
    raw_subcategory: str = "",
    tags: Iterable[Any] | None = None,
    description: str = "",
    include_debug: bool = False,
) -> Dict[str, Any]:
    return _classify(
        name=name,
        raw_category=raw_category,
        raw_subcategory=raw_subcategory,
        description=description,
        tags=tags,
        function_group_overrides=_EXTERNAL_TOOL_OVERRIDES,
        function_group_family_map=_EXTERNAL_FAMILY_FUNCTION_GROUP_MAP,
        discipline_family_map=_EXTERNAL_FAMILY_DISCIPLINE_MAP,
        fallback_function_group="analysis_workflow",
        fallback_discipline="general_compute",
        include_debug=include_debug,
    )


def find_boundary_mismatch_phrases(*parts: Any) -> List[Dict[str, str]]:
    text_blob = _build_text_blob(*parts)
    mismatches: List[Dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for axis, rules in (("function_group", _FUNCTION_GROUP_PHRASE_RULES), ("discipline", _DISCIPLINE_PHRASE_RULES)):
        for rule in rules:
            for phrase in rule.phrases:
                normalized_phrase = _normalize_token(phrase)
                if not normalized_phrase or len(normalized_phrase) < 3:
                    continue
                if normalized_phrase in text_blob and not _contains_phrase(text_blob, normalized_phrase):
                    key = (axis, normalized_phrase)
                    if key in seen:
                        continue
                    seen.add(key)
                    mismatches.append(
                        {
                            "axis": axis,
                            "rule": rule.key,
                            "phrase": normalized_phrase,
                        }
                    )
    return mismatches
