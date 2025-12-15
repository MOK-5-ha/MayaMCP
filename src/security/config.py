from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class ScanConfig:
    prompt_injection_enabled: bool = True
    prompt_injection_threshold: float = 0.5
    toxicity_enabled: bool = True
    toxicity_threshold: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanConfig":
        """
        Create a configuration from a dictionary.
        Ignores unknown keys for forward compatibility.
        """
        valid_keys = {k for k in cls.__annotations__}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)
