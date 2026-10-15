import tomllib
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HarnessType(str, Enum):
    ANTIGRAVITY = "antigravity"          # ~/.gemini/config/skills/ (default active)
    AGENTS_GLOBAL = "agents_global"      # ~/.agents/skills/ (catch-all intake)
    CLAUDE_CODE = "claude_code"          # ~/.claude/skills/ (disabled in MVP)
    CODEX = "codex"                      # ~/.codex/skills/ (disabled in MVP)
    CURSOR = "cursor"                    # ~/.cursor/skills/ (disabled in MVP)


class HarnessConfig(BaseModel):
    enabled: bool = False
    path: Path

    def resolved_path(self) -> Path:
        return self.path.expanduser().resolve()


class IntakeConfig(BaseModel):
    catch_all_path: Path = Path("~/.agents/skills")
    auto_bridge_to_gemini: bool = True
    bridge_prefix: str = ""

    def resolved_catch_all_path(self) -> Path:
        return self.catch_all_path.expanduser().resolve()


class GhoslaConfig(BaseModel):
    active_bundle: str = "baseline"
    harnesses: Dict[HarnessType, HarnessConfig]
    intake: IntakeConfig = Field(default_factory=IntakeConfig)

    @classmethod
    def from_toml_file(cls, path: Path) -> "GhoslaConfig":
        with open(path, "rb") as f:
            raw = tomllib.load(f)

        active_bundle = raw.get("atelier", {}).get("active_bundle", "baseline")
        harnesses_data = raw.get("harnesses", {})
        harnesses: Dict[HarnessType, HarnessConfig] = {}
        for h_key, h_val in harnesses_data.items():
            try:
                ht = HarnessType(h_key)
                harnesses[ht] = HarnessConfig(
                    enabled=h_val.get("enabled", False),
                    path=Path(h_val.get("path", "")),
                )
            except ValueError:
                continue

        intake_data = raw.get("intake", {})
        intake = IntakeConfig(
            catch_all_path=Path(intake_data.get("catch_all_path", "~/.agents/skills")),
            auto_bridge_to_gemini=intake_data.get("auto_bridge_to_gemini", True),
            bridge_prefix=intake_data.get("bridge_prefix", ""),
        )

        return cls(
            active_bundle=active_bundle,
            harnesses=harnesses,
            intake=intake,
        )


class SkillFrontmatter(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    name: str = Field(..., max_length=64, description="Kebab-case skill identifier")
    description: str = Field(..., max_length=1024, description="Trigger and capability summary")
    license: Optional[str] = "MIT"
    allowed_tools: Optional[str] = Field(default=None, alias="allowed-tools")
    disable_model_invocation: Optional[bool] = Field(
        default=None, alias="disable-model-invocation"
    )
    argument_hint: Optional[str] = Field(default=None, alias="argument-hint")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        if not v or not all(c.isalnum() or c == "-" for c in v) or not v.islower():
            raise ValueError("Skill name must be lowercase alphanumeric with hyphens")
        return v

    @property
    def is_fork(self) -> bool:
        if self.metadata.get("fork"):
            return bool(self.metadata.get("fork"))
        extra = getattr(self, "__pydantic_extra__", None) or {}
        return bool(extra.get("fork", False))

    @property
    def upstream_source(self) -> Optional[str]:
        val = self.metadata.get("upstream_source")
        if val is not None:
            return str(val)
        extra = getattr(self, "__pydantic_extra__", None) or {}
        val = extra.get("upstream_source")
        return str(val) if val is not None else None


class SkillSource(str, Enum):
    LOCAL = "local"                      # Owned in skills/
    FORK = "fork"                        # Forked from upstream with local mods
    UPSTREAM = "upstream"                # Direct link from upstream/
    INBOX = "inbox"                      # Imported from web/tweet clipping


class SkillMetadata(BaseModel):
    name: str
    source_type: SkillSource
    path: Path
    frontmatter: SkillFrontmatter
    byte_size: int
    estimated_tokens: int
    has_anti_rationalization: bool
    reference_depth: int
    upstream_repo: Optional[str] = None
    upstream_commit: Optional[str] = None
    upstream_source: Optional[str] = None

    @property
    def is_fork(self) -> bool:
        return self.source_type == SkillSource.FORK or self.frontmatter.is_fork

    @property
    def effective_upstream_source(self) -> Optional[str]:
        return self.upstream_source or self.frontmatter.upstream_source


class SkillBundle(BaseModel):
    name: str
    description: str
    skills: List[str]                   # Names of skills included
    target_harnesses: List[HarnessType] = Field(
        default_factory=lambda: [
            HarnessType.AGENTS_GLOBAL,
            HarnessType.ANTIGRAVITY,
            HarnessType.CLAUDE_CODE,
        ]
    )


class UpstreamDefaults(BaseModel):
    apiVersion: str = "ghosla.io/v1alpha1"
    kind: str = "UpstreamDefaults"
    excludePaths: List[str] = Field(default_factory=list)


class UpstreamSource(BaseModel):
    name: str
    git: Dict[str, str]
    newRootPath: Optional[str] = None
    extraExcludePaths: List[str] = Field(default_factory=list)
