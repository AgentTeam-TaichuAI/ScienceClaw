from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml


class SkillInstallerError(RuntimeError):
    """Raised when a third-party skill cannot be installed safely."""


@dataclass(frozen=True)
class SkillCandidate:
    directory: Path
    folder_name: str
    skill_name: str
    description: str
    metadata: Dict[str, Any]


_SKILLS_SH_RE = re.compile(r"^https?://skills\.sh/([^/]+)/([^/]+)(?:/([^/?#]+))?/?$", re.IGNORECASE)
_GITHUB_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SKIP_SCAN_PARTS = {".git", ".hg", ".svn", "__pycache__", "node_modules", "dist", "build", ".venv", "venv"}
_MANIFEST_NAME = ".scienceclaw-source.json"


def _parse_skill_frontmatter(skill_dir: Path) -> Dict[str, Any]:
    skill_md = skill_dir / "SKILL.md"
    result: Dict[str, Any] = {
        "name": skill_dir.name,
        "description": "",
        "metadata": {},
    }
    if not skill_md.is_file():
        return result

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return result

    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return result
    if not isinstance(data, dict):
        return result

    name = data.get("name")
    if isinstance(name, str) and name.strip():
        result["name"] = name.strip()

    description = data.get("description")
    if isinstance(description, str):
        result["description"] = description.strip()

    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        result["metadata"] = metadata

    return result


def _normalize_install_source(source: str, requested_skill: str = "") -> Dict[str, str]:
    raw_source = (source or "").strip()
    if not raw_source:
        raise SkillInstallerError("Skill source is required")

    explicit_skill = (requested_skill or "").strip()
    implicit_skill = ""
    normalized_source = raw_source

    skills_match = _SKILLS_SH_RE.match(raw_source)
    if skills_match:
        owner, repo, skill = skills_match.groups()
        normalized_source = f"https://github.com/{owner}/{repo}.git"
        implicit_skill = (skill or "").strip()
    else:
        possible_local = Path(raw_source).expanduser()
        if possible_local.exists():
            normalized_source = str(possible_local.resolve())
        else:
            if "@" in raw_source and not raw_source.startswith(("http://", "https://", "git@")):
                repo_part, skill_part = raw_source.rsplit("@", 1)
                if _GITHUB_REPO_RE.match(repo_part.strip()):
                    normalized_source = f"https://github.com/{repo_part.strip()}.git"
                    implicit_skill = skill_part.strip()
            elif _GITHUB_REPO_RE.match(raw_source):
                normalized_source = f"https://github.com/{raw_source}.git"

    return {
        "source": normalized_source,
        "requested_skill": explicit_skill or implicit_skill,
        "display_source": raw_source,
    }


def _materialize_source(source: str, temp_root: Path) -> Path:
    possible_local = Path(source).expanduser()
    if possible_local.exists():
        return possible_local.resolve()

    checkout_dir = temp_root / "repo"
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", source, str(checkout_dir)],
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
    except FileNotFoundError as exc:
        raise SkillInstallerError(
            "ScienceClaw skill installation requires git in the backend container. "
            "Rebuild the backend image after adding git."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SkillInstallerError(f"Timed out while cloning skill source: {source}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise SkillInstallerError(stderr or f"Failed to clone skill source: {source}")

    return checkout_dir


def _discover_skill_candidates(repo_root: Path) -> List[SkillCandidate]:
    candidates: List[SkillCandidate] = []
    for skill_md in sorted(repo_root.rglob("SKILL.md")):
        if any(part in _SKIP_SCAN_PARTS for part in skill_md.parts):
            continue

        skill_dir = skill_md.parent
        frontmatter = _parse_skill_frontmatter(skill_dir)
        candidates.append(
            SkillCandidate(
                directory=skill_dir,
                folder_name=skill_dir.name,
                skill_name=str(frontmatter.get("name") or skill_dir.name).strip() or skill_dir.name,
                description=str(frontmatter.get("description") or "").strip(),
                metadata=frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {},
            )
        )

    deduped: List[SkillCandidate] = []
    seen_dirs: set[str] = set()
    for candidate in candidates:
        key = str(candidate.directory.resolve()).lower()
        if key in seen_dirs:
            continue
        seen_dirs.add(key)
        deduped.append(candidate)
    return deduped


def _candidate_aliases(candidate: SkillCandidate) -> set[str]:
    aliases = {
        candidate.folder_name.strip().lower(),
        candidate.skill_name.strip().lower(),
    }
    aliases.discard("")
    return aliases


def _select_candidate(candidates: List[SkillCandidate], requested_skill: str) -> SkillCandidate:
    if not candidates:
        raise SkillInstallerError("No SKILL.md entries were found in the provided source")

    if requested_skill:
        needle = requested_skill.strip().lower()
        matches = [candidate for candidate in candidates if needle in _candidate_aliases(candidate)]
        if not matches:
            available = ", ".join(sorted(candidate.skill_name for candidate in candidates))
            raise SkillInstallerError(
                f"Skill '{requested_skill}' was not found in the source. Available skills: {available}"
            )
        if len(matches) > 1:
            available = ", ".join(sorted(candidate.skill_name for candidate in matches))
            raise SkillInstallerError(
                f"Skill name '{requested_skill}' matched multiple candidates. Please be more specific: {available}"
            )
        return matches[0]

    if len(candidates) == 1:
        return candidates[0]

    available = ", ".join(sorted(candidate.skill_name for candidate in candidates))
    raise SkillInstallerError(
        "This source contains multiple skills. Provide skill_name explicitly. "
        f"Available skills: {available}"
    )


def _safe_destination_name(candidate: SkillCandidate) -> str:
    base = candidate.skill_name or candidate.folder_name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip(".-_")
    if not cleaned:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate.folder_name).strip(".-_")
    if not cleaned:
        raise SkillInstallerError(f"Unable to derive a safe destination name for skill '{base}'")
    return cleaned


def _write_install_manifest(skill_dir: Path, manifest: Dict[str, Any]) -> None:
    manifest_path = skill_dir / _MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def install_skill_into_directory(
    *,
    external_skills_dir: str,
    source: str,
    skill_name: str = "",
    overwrite: bool = False,
) -> Dict[str, Any]:
    normalized = _normalize_install_source(source, skill_name)
    target_root = Path(external_skills_dir).expanduser().resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="scienceclaw-skill-install-") as temp_dir:
        repo_root = _materialize_source(normalized["source"], Path(temp_dir))
        candidates = _discover_skill_candidates(repo_root)
        selected = _select_candidate(candidates, normalized["requested_skill"])
        destination_name = _safe_destination_name(selected)
        destination_dir = target_root / destination_name

        if destination_dir.exists():
            if not overwrite:
                raise SkillInstallerError(
                    f"Skill '{destination_name}' already exists in ScienceClaw. "
                    "Enable overwrite to replace it."
                )
            shutil.rmtree(destination_dir)

        shutil.copytree(selected.directory, destination_dir)
        _write_install_manifest(
            destination_dir,
            {
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "display_source": normalized["display_source"],
                "normalized_source": normalized["source"],
                "requested_skill": normalized["requested_skill"],
                "selected_skill": selected.skill_name,
                "selected_folder": selected.folder_name,
            },
        )

    frontmatter = _parse_skill_frontmatter(destination_dir)
    files = [
        str(path.relative_to(destination_dir))
        for path in sorted(destination_dir.rglob("*"))
        if path.is_file()
    ]

    return {
        "installed": True,
        "skill_name": str(frontmatter.get("name") or destination_name),
        "description": str(frontmatter.get("description") or ""),
        "files": files,
        "metadata": frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {},
        "source": normalized["display_source"],
        "normalized_source": normalized["source"],
        "requested_skill": normalized["requested_skill"],
        "installed_directory": destination_name,
        "available_skills": [candidate.skill_name for candidate in candidates],
        "manifest_file": _MANIFEST_NAME,
    }
