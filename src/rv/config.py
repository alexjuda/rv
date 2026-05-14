import os
from dataclasses import dataclass, field
from pathlib import Path
import tomllib

DEFAULT_STALE_THRESHOLD_MINUTES = 5


def get_config_path() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME")
    if config_home is None:
        config_home = Path.home() / ".config"
    return Path(config_home) / "rv" / "config.toml"


@dataclass
class Config:
    stale_threshold_minutes: int = DEFAULT_STALE_THRESHOLD_MINUTES
    canned_replies: dict[str, str] = field(default_factory=dict)


def load_config(config_path: Path | None = None) -> Config:
    if config_path is None:
        config_path = get_config_path()

    if not config_path.exists():
        return Config()

    with config_path.open("rb") as f:
        data = tomllib.load(f)

    stale = data.get("sync", {}).get(
        "stale_threshold_minutes", DEFAULT_STALE_THRESHOLD_MINUTES
    )
    canned = data.get("canned_replies", {})

    return Config(stale_threshold_minutes=stale, canned_replies=canned)
