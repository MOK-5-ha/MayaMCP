import pytest
from hypothesis import given, strategies as st
from src.security.config import ScanConfig

@given(
    st.booleans(),
    st.floats(min_value=0.0, max_value=1.0),
    st.booleans(),
    st.floats(min_value=0.0, max_value=1.0)
)
def test_config_roundway_consistency(pi_enabled, pi_threshold, tox_enabled, tox_threshold):
    """
    Property 4: Configuration round-trip consistency
    Validates: Requirements 5.2
    """
    config = ScanConfig(
        prompt_injection_enabled=pi_enabled,
        prompt_injection_threshold=pi_threshold,
        toxicity_enabled=tox_enabled,
        toxicity_threshold=tox_threshold
    )
    
    serialized = config.to_dict()
    deserialized = ScanConfig.from_dict(serialized)
    
    assert deserialized == config
