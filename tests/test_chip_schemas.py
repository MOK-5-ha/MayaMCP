"""
Property-based and unit tests for suggestion chip Pydantic schemas.

Uses Hypothesis for property-based testing. Each test is annotated
with the property or requirement it validates.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from src.schemas.chips import (
    ActionID,
    ChipGenerationContext,
    ChipType,
    SuggestionChip,
    SuggestionChipSet,
)

# =============================================================================
# Test Configuration
# =============================================================================

# Minimum 100 iterations per property test
TEST_SETTINGS = settings(max_examples=100, deadline=60000)


# =============================================================================
# Strategies (Generators)
# =============================================================================

# Text strategy for valid chip text (2-40 characters)
valid_chip_text_strategy = st.text(min_size=2, max_size=40, alphabet=st.characters(
    whitelist_categories=('Lu', 'Ll', 'Nd', 'P'),
    min_codepoint=32,
    max_codepoint=126
))

# ChipType strategy
chip_type_strategy = st.sampled_from([ChipType.DIALOGUE, ChipType.ACTION])

# ActionID strategy
action_id_strategy = st.sampled_from([
    ActionID.PAYMENT,
    ActionID.TIP,
    ActionID.MENU,
    ActionID.CANCEL,
    ActionID.ORDER_ANOTHER
])

# Valid dialogue chip strategy
dialogue_chip_strategy = st.builds(
    SuggestionChip,
    text=valid_chip_text_strategy,
    type=st.just(ChipType.DIALOGUE),
    action_id=st.just(None)
)

# Valid action chip strategy
action_chip_strategy = st.builds(
    SuggestionChip,
    text=valid_chip_text_strategy,
    type=st.just(ChipType.ACTION),
    action_id=action_id_strategy
)

# Mixed chip strategy
valid_chip_strategy = st.one_of(dialogue_chip_strategy, action_chip_strategy)


# =============================================================================
# Property Tests
# =============================================================================

class TestChipTextUniquenessProperty:
    """
    **Feature: suggestion-chips, Property 1: Chip text uniqueness within sets**
    
    *For any* SuggestionChipSet with N chips, no two chips SHALL have identical
    text (case-insensitive comparison). The uniqueness check SHALL be enforced
    during validation, not after instantiation.
    
    **Validates: Requirements 2.3, 2.5**
    """

    @TEST_SETTINGS
    @given(
        chips=st.lists(
            valid_chip_strategy,
            min_size=3,
            max_size=6,
            unique_by=lambda chip: chip.text.lower()
        )
    )
    def test_chip_text_uniqueness_valid(self, chips):
        """
        Property 1: Chip text uniqueness (valid case)
        
        Preconditions: List of 3-6 chips with unique texts (case-insensitive)
        Invariant: SuggestionChipSet validates successfully
        """
        # Act: Create chip set
        chip_set = SuggestionChipSet(chips=chips)
        
        # Assert: Validation succeeds
        assert len(chip_set.chips) == len(chips)
        
        # Verify uniqueness at runtime
        texts_lower = [chip.text.lower() for chip in chip_set.chips]
        assert len(texts_lower) == len(set(texts_lower)), "Texts should be unique"

    @TEST_SETTINGS
    @given(
        base_text=valid_chip_text_strategy,
        chip_count=st.integers(min_value=3, max_value=6)
    )
    def test_chip_text_uniqueness_violation(self, base_text, chip_count):
        """
        Property 1: Chip text uniqueness (violation case)
        
        Preconditions: List of chips with duplicate text (case-insensitive)
        Invariant: SuggestionChipSet validation raises ValueError
        """
        # Create chips with duplicate text (same case)
        chips = [
            SuggestionChip(text=base_text, type=ChipType.DIALOGUE)
            for _ in range(chip_count)
        ]
        
        # Assert: Validation fails
        with pytest.raises(ValidationError) as exc_info:
            SuggestionChipSet(chips=chips)
        
        assert "Chip texts must be unique" in str(exc_info.value)

    def test_chip_text_case_insensitive_uniqueness(self):
        """Edge case: case variations should be detected as duplicates"""
        chips = [
            SuggestionChip(text="Tell me more", type=ChipType.DIALOGUE),
            SuggestionChip(text="TELL ME MORE", type=ChipType.DIALOGUE),
            SuggestionChip(text="See menu", type=ChipType.ACTION, action_id=ActionID.MENU),
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            SuggestionChipSet(chips=chips)
        
        assert "Chip texts must be unique" in str(exc_info.value)

    def test_chip_text_uniqueness_minimum_set(self):
        """Edge case: minimum set size (3 chips) with unique texts"""
        chips = [
            SuggestionChip(text="Yes", type=ChipType.DIALOGUE),
            SuggestionChip(text="No", type=ChipType.DIALOGUE),
            SuggestionChip(text="Maybe", type=ChipType.DIALOGUE),
        ]
        
        chip_set = SuggestionChipSet(chips=chips)
        assert len(chip_set.chips) == 3

    def test_chip_text_uniqueness_maximum_set(self):
        """Edge case: maximum set size (6 chips) with unique texts"""
        chips = [
            SuggestionChip(text=f"Chip {i}", type=ChipType.DIALOGUE)
            for i in range(6)
        ]
        
        chip_set = SuggestionChipSet(chips=chips)
        assert len(chip_set.chips) == 6


# =============================================================================
# Unit Tests for Schema Validators
# =============================================================================

class TestSuggestionChipValidation:
    """Unit tests for SuggestionChip field validation."""

    def test_valid_dialogue_chip(self):
        """Valid dialogue chip without action_id"""
        chip = SuggestionChip(
            text="Tell me more",
            type=ChipType.DIALOGUE
        )
        
        assert chip.text == "Tell me more"
        assert chip.type == ChipType.DIALOGUE
        assert chip.action_id is None

    def test_valid_action_chip(self):
        """Valid action chip with action_id"""
        chip = SuggestionChip(
            text="Complete payment",
            type=ChipType.ACTION,
            action_id=ActionID.PAYMENT
        )
        
        assert chip.text == "Complete payment"
        assert chip.type == ChipType.ACTION
        assert chip.action_id == ActionID.PAYMENT

    def test_action_chip_missing_action_id(self):
        """Action chip without action_id should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            SuggestionChip(
                text="Complete payment",
                type=ChipType.ACTION
            )
        
        assert "action_id required for action chips" in str(exc_info.value)

    def test_dialogue_chip_with_action_id(self):
        """Dialogue chip with action_id should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            SuggestionChip(
                text="Tell me more",
                type=ChipType.DIALOGUE,
                action_id=ActionID.PAYMENT
            )
        
        assert "action_id not allowed for dialogue chips" in str(exc_info.value)

    def test_text_too_short(self):
        """Text with less than 2 characters should fail"""
        with pytest.raises(ValidationError) as exc_info:
            SuggestionChip(
                text="A",
                type=ChipType.DIALOGUE
            )
        
        assert "String should have at least 2 characters" in str(exc_info.value)

    def test_text_too_long(self):
        """Text with more than 40 characters should fail"""
        with pytest.raises(ValidationError) as exc_info:
            SuggestionChip(
                text="A" * 41,
                type=ChipType.DIALOGUE
            )
        
        assert "String should have at most 40 characters" in str(exc_info.value)

    def test_text_minimum_length(self):
        """Text with exactly 2 characters should be valid"""
        chip = SuggestionChip(text="No", type=ChipType.DIALOGUE)
        assert chip.text == "No"

    def test_text_maximum_length(self):
        """Text with exactly 40 characters should be valid"""
        text = "A" * 40
        chip = SuggestionChip(text=text, type=ChipType.DIALOGUE)
        assert len(chip.text) == 40

    def test_all_action_ids(self):
        """Test all valid action IDs"""
        for action_id in ActionID:
            chip = SuggestionChip(
                text=f"Action {action_id.value}",
                type=ChipType.ACTION,
                action_id=action_id
            )
            assert chip.action_id == action_id

    def test_invalid_action_id(self):
        """Invalid action_id string should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            SuggestionChip(
                text="Invalid action",
                type=ChipType.ACTION,
                action_id="invalid_action"
            )
        
        assert "Input should be" in str(exc_info.value)


class TestSuggestionChipSetValidation:
    """Unit tests for SuggestionChipSet field validation."""

    def test_valid_chip_set_minimum(self):
        """Valid chip set with minimum 3 chips"""
        chips = [
            SuggestionChip(text="Yes", type=ChipType.DIALOGUE),
            SuggestionChip(text="No", type=ChipType.DIALOGUE),
            SuggestionChip(text="Maybe", type=ChipType.DIALOGUE),
        ]
        
        chip_set = SuggestionChipSet(chips=chips)
        assert len(chip_set.chips) == 3

    def test_valid_chip_set_maximum(self):
        """Valid chip set with maximum 6 chips"""
        chips = [
            SuggestionChip(text=f"Chip {i}", type=ChipType.DIALOGUE)
            for i in range(6)
        ]
        
        chip_set = SuggestionChipSet(chips=chips)
        assert len(chip_set.chips) == 6

    def test_chip_set_too_few(self):
        """Chip set with less than 3 chips should fail"""
        chips = [
            SuggestionChip(text="Yes", type=ChipType.DIALOGUE),
            SuggestionChip(text="No", type=ChipType.DIALOGUE),
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            SuggestionChipSet(chips=chips)
        
        assert "List should have at least 3 items" in str(exc_info.value)

    def test_chip_set_too_many(self):
        """Chip set with more than 6 chips should fail"""
        chips = [
            SuggestionChip(text=f"Chip {i}", type=ChipType.DIALOGUE)
            for i in range(7)
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            SuggestionChipSet(chips=chips)
        
        assert "List should have at most 6 items" in str(exc_info.value)

    def test_chip_set_mixed_types(self):
        """Chip set with mixed dialogue and action chips"""
        chips = [
            SuggestionChip(text="Tell me more", type=ChipType.DIALOGUE),
            SuggestionChip(text="Make it stronger", type=ChipType.DIALOGUE),
            SuggestionChip(text="Complete payment", type=ChipType.ACTION, action_id=ActionID.PAYMENT),
            SuggestionChip(text="See menu", type=ChipType.ACTION, action_id=ActionID.MENU),
        ]
        
        chip_set = SuggestionChipSet(chips=chips)
        assert len(chip_set.chips) == 4
        
        dialogue_count = sum(1 for chip in chip_set.chips if chip.type == ChipType.DIALOGUE)
        action_count = sum(1 for chip in chip_set.chips if chip.type == ChipType.ACTION)
        
        assert dialogue_count == 2
        assert action_count == 2

    def test_chip_set_all_dialogue(self):
        """Chip set with all dialogue chips"""
        chips = [
            SuggestionChip(text=f"Dialogue {i}", type=ChipType.DIALOGUE)
            for i in range(4)
        ]
        
        chip_set = SuggestionChipSet(chips=chips)
        assert all(chip.type == ChipType.DIALOGUE for chip in chip_set.chips)

    def test_chip_set_all_action(self):
        """Chip set with all action chips"""
        action_ids = [ActionID.PAYMENT, ActionID.TIP, ActionID.MENU, ActionID.CANCEL]
        chips = [
            SuggestionChip(text=f"Action {i}", type=ChipType.ACTION, action_id=action_id)
            for i, action_id in enumerate(action_ids)
        ]
        
        chip_set = SuggestionChipSet(chips=chips)
        assert all(chip.type == ChipType.ACTION for chip in chip_set.chips)

    def test_chip_set_empty_list(self):
        """Empty chip list should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            SuggestionChipSet(chips=[])
        
        assert "List should have at least 3 items" in str(exc_info.value)


class TestChipGenerationContextValidation:
    """Unit tests for ChipGenerationContext field validation."""

    def test_valid_context_full(self):
        """Valid context with all fields populated"""
        context = ChipGenerationContext(
            conversation_turns=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello! How can I help?"},
                {"role": "user", "content": "I'd like a drink"},
                {"role": "assistant", "content": "What would you like?"},
            ],
            payment_status="pending",
            conversation_phase="ordering",
            recent_user_messages=["Hi", "I'd like a drink"]
        )
        
        assert len(context.conversation_turns) == 4
        assert context.payment_status == "pending"
        assert context.conversation_phase == "ordering"
        assert len(context.recent_user_messages) == 2

    def test_valid_context_minimal(self):
        """Valid context with minimal required fields"""
        context = ChipGenerationContext(
            conversation_turns=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
                {"role": "user", "content": "Drink please"},
            ],
            conversation_phase="ordering"
        )
        
        assert len(context.conversation_turns) == 3
        assert context.payment_status is None
        assert context.recent_user_messages == []

    def test_conversation_turns_too_many(self):
        """More than 4 conversation turns should fail"""
        with pytest.raises(ValidationError) as exc_info:
            ChipGenerationContext(
                conversation_turns=[
                    {"role": "user", "content": f"Message {i}"}
                    for i in range(5)
                ],
                conversation_phase="ordering"
            )
        
        assert "List should have at most 4 items" in str(exc_info.value)

    def test_conversation_turns_maximum(self):
        """Exactly 4 conversation turns should be valid"""
        context = ChipGenerationContext(
            conversation_turns=[
                {"role": "user", "content": f"Message {i}"}
                for i in range(4)
            ],
            conversation_phase="ordering"
        )
        
        assert len(context.conversation_turns) == 4

    def test_recent_user_messages_too_many(self):
        """More than 2 recent user messages should fail"""
        with pytest.raises(ValidationError) as exc_info:
            ChipGenerationContext(
                conversation_turns=[{"role": "user", "content": "Hi"}],
                conversation_phase="ordering",
                recent_user_messages=["Message 1", "Message 2", "Message 3"]
            )
        
        assert "List should have at most 2 items" in str(exc_info.value)

    def test_recent_user_messages_maximum(self):
        """Exactly 2 recent user messages should be valid"""
        context = ChipGenerationContext(
            conversation_turns=[{"role": "user", "content": "Hi"}],
            conversation_phase="ordering",
            recent_user_messages=["Message 1", "Message 2"]
        )
        
        assert len(context.recent_user_messages) == 2

    def test_conversation_turns_empty(self):
        """Empty conversation turns should be valid (edge case)"""
        context = ChipGenerationContext(
            conversation_turns=[],
            conversation_phase="greeting"
        )
        
        assert len(context.conversation_turns) == 0

    def test_payment_status_values(self):
        """Test various payment status values"""
        valid_statuses = ["pending", "completed", "failed", "none", None]
        
        for status in valid_statuses:
            context = ChipGenerationContext(
                conversation_turns=[{"role": "user", "content": "Hi"}],
                payment_status=status,
                conversation_phase="payment"
            )
            assert context.payment_status == status

    def test_conversation_phase_values(self):
        """Test various conversation phase values"""
        valid_phases = ["greeting", "ordering", "describing", "payment", "complete"]
        
        for phase in valid_phases:
            context = ChipGenerationContext(
                conversation_turns=[{"role": "user", "content": "Hi"}],
                conversation_phase=phase
            )
            assert context.conversation_phase == phase


class TestEnumValidation:
    """Unit tests for enum validation."""

    def test_chip_type_enum_values(self):
        """Test ChipType enum values"""
        assert ChipType.DIALOGUE.value == "dialogue"
        assert ChipType.ACTION.value == "action"
        assert len(ChipType) == 2

    def test_action_id_enum_values(self):
        """Test ActionID enum values"""
        assert ActionID.PAYMENT.value == "payment"
        assert ActionID.TIP.value == "tip"
        assert ActionID.MENU.value == "menu"
        assert ActionID.CANCEL.value == "cancel"
        assert ActionID.ORDER_ANOTHER.value == "order_another"
        assert len(ActionID) == 5

    def test_invalid_chip_type(self):
        """Invalid chip type string should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            SuggestionChip(
                text="Test",
                type="invalid_type"
            )
        
        assert "Input should be 'dialogue' or 'action'" in str(exc_info.value)

    def test_invalid_action_id_enum(self):
        """Invalid action_id value should fail validation"""
        with pytest.raises(ValidationError):
            SuggestionChip(
                text="Test",
                type=ChipType.ACTION,
                action_id="invalid_action"
            )


class TestModelSerialization:
    """Unit tests for model_dump() serialization."""

    def test_suggestion_chip_model_dump(self):
        """Test SuggestionChip serialization"""
        chip = SuggestionChip(
            text="Tell me more",
            type=ChipType.DIALOGUE
        )
        
        data = chip.model_dump()
        
        assert data == {
            "text": "Tell me more",
            "type": "dialogue",
            "action_id": None
        }

    def test_action_chip_model_dump(self):
        """Test action chip serialization"""
        chip = SuggestionChip(
            text="Complete payment",
            type=ChipType.ACTION,
            action_id=ActionID.PAYMENT
        )
        
        data = chip.model_dump()
        
        assert data == {
            "text": "Complete payment",
            "type": "action",
            "action_id": "payment"
        }

    def test_suggestion_chip_set_model_dump(self):
        """Test SuggestionChipSet serialization"""
        chips = [
            SuggestionChip(text="Yes", type=ChipType.DIALOGUE),
            SuggestionChip(text="No", type=ChipType.DIALOGUE),
            SuggestionChip(text="Pay", type=ChipType.ACTION, action_id=ActionID.PAYMENT),
        ]
        
        chip_set = SuggestionChipSet(chips=chips)
        data = chip_set.model_dump()
        
        assert "chips" in data
        assert len(data["chips"]) == 3
        assert data["chips"][0]["text"] == "Yes"
        assert data["chips"][2]["action_id"] == "payment"

    def test_chip_generation_context_model_dump(self):
        """Test ChipGenerationContext serialization"""
        context = ChipGenerationContext(
            conversation_turns=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"}
            ],
            payment_status="pending",
            conversation_phase="ordering",
            recent_user_messages=["Hi"]
        )
        
        data = context.model_dump()
        
        assert len(data["conversation_turns"]) == 2
        assert data["payment_status"] == "pending"
        assert data["conversation_phase"] == "ordering"
        assert data["recent_user_messages"] == ["Hi"]

    def test_model_dump_with_exclude(self):
        """Test model_dump with field exclusion"""
        chip = SuggestionChip(
            text="Test",
            type=ChipType.DIALOGUE
        )
        
        data = chip.model_dump(exclude={"action_id"})
        
        assert "text" in data
        assert "type" in data
        assert "action_id" not in data

    def test_model_dump_json(self):
        """Test JSON serialization"""
        chip = SuggestionChip(
            text="Test",
            type=ChipType.DIALOGUE
        )
        
        json_str = chip.model_dump_json()
        
        assert isinstance(json_str, str)
        assert "Test" in json_str
        assert "dialogue" in json_str
