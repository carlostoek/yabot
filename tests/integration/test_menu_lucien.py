"""
Lucien Voice Integration Tests for Menu System.

Tests Lucien's sophisticated personality integration throughout menu interactions
to ensure compliance with REQ-MENU-005.1 and REQ-MENU-005.4.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from src.ui.menu_factory import MenuFactory, Menu, MenuItem
from src.ui.lucien_voice_generator import LucienVoiceProfile, RelationshipLevel, generate_lucien_response
from src.handlers.menu_system import MenuSystemCoordinator
from src.services.user import UserService
from src.events.bus import EventBus


# Test relationship contexts for Lucien voice testing
RELATIONSHIP_CONTEXTS = {
    "new_acquaintance": {
        "user_id": "new_user_001",
        "relationship_level": RelationshipLevel.ACQUAINTANCE,
        "narrative_level": 1,
        "worthiness_score": 0.3,
        "interaction_count": 5,
        "trust_level": 0.2,
        "emotional_signature": {"vulnerability": 0.1, "authenticity": 0.3}
    },
    "developing_trust": {
        "user_id": "developing_user_001",
        "relationship_level": RelationshipLevel.DEVELOPING_TRUST,
        "narrative_level": 3,
        "worthiness_score": 0.6,
        "interaction_count": 25,
        "trust_level": 0.6,
        "emotional_signature": {"vulnerability": 0.5, "authenticity": 0.7}
    },
    "intimate_connection": {
        "user_id": "intimate_user_001",
        "relationship_level": RelationshipLevel.INTIMATE_CONNECTION,
        "narrative_level": 5,
        "worthiness_score": 0.9,
        "interaction_count": 100,
        "trust_level": 0.9,
        "emotional_signature": {"vulnerability": 0.8, "authenticity": 0.9}
    },
    "low_worthiness": {
        "user_id": "low_worth_user_001",
        "relationship_level": RelationshipLevel.ACQUAINTANCE,
        "narrative_level": 1,
        "worthiness_score": 0.1,
        "interaction_count": 3,
        "trust_level": 0.1,
        "emotional_signature": {"vulnerability": 0.0, "authenticity": 0.1}
    }
}


class TestLucienMenuVoiceIntegration:
    """Test Lucien's voice integration in menu system."""

    @pytest.fixture
    async def menu_factory_with_lucien(self):
        """Create menu factory with Lucien voice integration."""
        factory = MenuFactory()
        yield factory

    @pytest.fixture
    async def lucien_voice_profile(self):
        """Create Lucien voice profile for testing."""
        profile = LucienVoiceProfile()
        yield profile

    @pytest.mark.asyncio
    @pytest.mark.parametrize("relationship_context", [
        "new_acquaintance",
        "developing_trust",
        "intimate_connection",
        "low_worthiness"
    ])
    async def test_lucien_voice_in_menu_headers(self, menu_factory_with_lucien, relationship_context):
        """Test Lucien's voice presence in menu headers and descriptions.

        REQ-MENU-005.1: Any menu displayed THEN Lucien's voice SHALL be present
        in headers, descriptions, and explanations.
        """
        user_context = RELATIONSHIP_CONTEXTS[relationship_context]

        # Test different menu types
        menu_types = ["main_menu", "narrative_menu", "vip_menu", "restriction_menu"]

        for menu_type in menu_types:
            try:
                menu = await menu_factory_with_lucien.generate_menu(menu_type, user_context)

                if menu:
                    # Verify Lucien's voice in menu title
                    await self._verify_lucien_voice_characteristics(menu.title, user_context)

                    # Verify Lucien's voice in menu description
                    if menu.description:
                        await self._verify_lucien_voice_characteristics(menu.description, user_context)

                    # Verify Lucien's voice in menu item descriptions
                    for item in menu.items:
                        if item.description:
                            await self._verify_lucien_voice_characteristics(item.description, user_context)

                        # Check restriction explanations
                        if not item.is_enabled and item.restriction_reason:
                            await self._verify_lucien_restriction_voice(item.restriction_reason, user_context)

            except Exception as e:
                # Some menus might not exist, which is acceptable
                if "not found" not in str(e).lower():
                    raise

    async def _verify_lucien_voice_characteristics(self, text: str, user_context: Dict[str, Any]) -> None:
        """Verify text contains Lucien's sophisticated voice characteristics."""
        text_lower = text.lower()
        relationship_level = user_context.get("relationship_level", RelationshipLevel.ACQUAINTANCE)
        worthiness_score = user_context.get("worthiness_score", 0.0)

        # Lucien's sophisticated vocabulary indicators
        sophisticated_indicators = [
            "exquisite", "refined", "elegant", "sophisticated", "discerning",
            "contemplative", "profound", "authentic", "worthy", "deserving",
            "cultivation", "appreciation", "understanding", "depth", "nuance"
        ]

        # Should contain at least some sophisticated language
        has_sophisticated_language = any(indicator in text_lower for indicator in sophisticated_indicators)

        # Relationship-specific language adaptations
        if relationship_level == RelationshipLevel.INTIMATE_CONNECTION:
            intimate_indicators = ["beloved", "cherished", "treasured", "intimately", "deeply"]
            has_intimate_language = any(indicator in text_lower for indicator in intimate_indicators)
            assert has_sophisticated_language or has_intimate_language, \
                f"Intimate relationship should use sophisticated or intimate language: {text}"

        elif relationship_level == RelationshipLevel.ACQUAINTANCE:
            formal_indicators = ["sir", "madam", "please", "kindly", "respectfully", "proper"]
            has_formal_language = any(indicator in text_lower for indicator in formal_indicators)
            assert has_sophisticated_language or has_formal_language, \
                f"New acquaintance should use sophisticated or formal language: {text}"

        # Worthiness-based adaptations
        if worthiness_score < 0.3:
            # Lower worthiness should still be sophisticated but more guarded
            guarded_indicators = ["perhaps", "consideration", "reflection", "patience", "understanding"]
            has_guarded_language = any(indicator in text_lower for indicator in guarded_indicators)
            assert has_sophisticated_language or has_guarded_language, \
                f"Low worthiness should use sophisticated but guarded language: {text}"

    async def _verify_lucien_restriction_voice(self, restriction_text: str, user_context: Dict[str, Any]) -> None:
        """Verify restriction explanations use Lucien's elegant guidance style."""
        restriction_lower = restriction_text.lower()
        worthiness_score = user_context.get("worthiness_score", 0.0)

        # Lucien should never be harsh or blunt about restrictions
        harsh_language = ["no", "can't", "forbidden", "denied", "blocked", "error"]
        has_harsh_language = any(harsh in restriction_lower for harsh in harsh_language)
        assert not has_harsh_language, \
            f"Lucien should not use harsh language in restrictions: {restriction_text}"

        # Should use elegant explanation patterns
        elegant_patterns = [
            "this requires", "to unlock", "awaits your", "when you have",
            "your journey", "progression", "worthiness", "cultivation",
            "understanding", "deeper appreciation", "exclusive", "reserved"
        ]

        has_elegant_explanation = any(pattern in restriction_lower for pattern in elegant_patterns)
        assert has_elegant_explanation, \
            f"Restriction should use elegant Lucien explanation: {restriction_text}"

        # Worthiness-specific guidance
        if worthiness_score < 0.5:
            guidance_indicators = [
                "develop", "grow", "learn", "explore", "deepen", "cultivate",
                "authentic", "genuine", "meaningful", "patience", "reflection"
            ]
            has_guidance = any(indicator in restriction_lower for indicator in guidance_indicators)
            assert has_guidance, \
                f"Low worthiness restriction should include guidance: {restriction_text}"

    @pytest.mark.asyncio
    async def test_lucien_voice_consistency_across_menus(self, menu_factory_with_lucien):
        """Test that Lucien's voice remains consistent across different menus for same user."""
        user_context = RELATIONSHIP_CONTEXTS["developing_trust"]

        menus = []
        menu_types = ["main_menu", "narrative_menu", "gamification_menu"]

        # Generate multiple menus for same user
        for menu_type in menu_types:
            try:
                menu = await menu_factory_with_lucien.generate_menu(menu_type, user_context)
                if menu:
                    menus.append((menu_type, menu))
            except Exception:
                pass

        # Verify voice consistency
        assert len(menus) >= 2, "Need at least 2 menus to test consistency"

        # Extract voice characteristics from all menus
        all_menu_texts = []
        for menu_type, menu in menus:
            all_menu_texts.append(menu.title)
            if menu.description:
                all_menu_texts.append(menu.description)

        # Check for consistent sophisticated tone
        sophisticated_count = 0
        for text in all_menu_texts:
            try:
                await self._verify_lucien_voice_characteristics(text, user_context)
                sophisticated_count += 1
            except AssertionError:
                pass

        # Should maintain sophisticated voice in majority of texts
        consistency_ratio = sophisticated_count / len(all_menu_texts)
        assert consistency_ratio >= 0.7, \
            f"Lucien voice consistency too low: {consistency_ratio:.2f} (need >= 0.7)"

    @pytest.mark.asyncio
    async def test_lucien_relationship_adaptation(self, menu_factory_with_lucien):
        """Test Lucien's voice adapts based on relationship level.

        REQ-MENU-005.4: When user progression is acknowledged THEN Lucien SHALL
        adapt his tone based on relationship level.
        """
        menu_type = "main_menu"

        # Test voice evolution across relationship levels
        relationship_levels = ["new_acquaintance", "developing_trust", "intimate_connection"]
        menu_texts_by_level = {}

        for level in relationship_levels:
            user_context = RELATIONSHIP_CONTEXTS[level]
            menu = await menu_factory_with_lucien.generate_menu(menu_type, user_context)

            if menu:
                menu_texts_by_level[level] = {
                    "title": menu.title,
                    "description": menu.description or "",
                    "items": [item.description or item.text for item in menu.items[:3]]
                }

        # Verify progression in intimacy and tone
        if len(menu_texts_by_level) >= 2:
            await self._verify_relationship_progression(menu_texts_by_level)

    async def _verify_relationship_progression(self, menu_texts_by_level: Dict[str, Dict[str, Any]]) -> None:
        """Verify that Lucien's tone progresses appropriately with relationship level."""

        # Formal language indicators (early relationship)
        formal_indicators = ["sir", "madam", "please", "kindly", "respectfully", "proper", "allow me"]

        # Intimate language indicators (advanced relationship)
        intimate_indicators = ["beloved", "dear", "cherished", "my", "our", "together", "intimately"]

        # Personal language indicators (developing relationship)
        personal_indicators = ["you", "your journey", "your growth", "understand you", "see in you"]

        # Check progression
        for level, texts in menu_texts_by_level.items():
            all_text = " ".join([texts["title"], texts["description"]] + texts["items"]).lower()

            if level == "new_acquaintance":
                formal_count = sum(1 for indicator in formal_indicators if indicator in all_text)
                assert formal_count > 0, f"New acquaintance should use formal language: {all_text[:200]}"

            elif level == "developing_trust":
                personal_count = sum(1 for indicator in personal_indicators if indicator in all_text)
                assert personal_count > 0, f"Developing trust should use personal language: {all_text[:200]}"

            elif level == "intimate_connection":
                intimate_count = sum(1 for indicator in intimate_indicators if indicator in all_text)
                # Note: Intimate language might be more subtle, so we also check for reduced formality
                formal_count = sum(1 for indicator in formal_indicators if indicator in all_text)

                assert intimate_count > 0 or formal_count == 0, \
                    f"Intimate connection should use intimate language or avoid formal language: {all_text[:200]}"

    @pytest.mark.asyncio
    async def test_lucien_error_handling_voice(self, menu_factory_with_lucien):
        """Test Lucien's voice in error scenarios."""
        user_context = RELATIONSHIP_CONTEXTS["developing_trust"]

        # Test with invalid menu request (should trigger error handling)
        try:
            menu = await menu_factory_with_lucien.generate_menu("nonexistent_menu", user_context)

            # If an error menu is returned instead of exception
            if menu and "error" in menu.menu_id.lower():
                # Verify error is presented with Lucien's sophistication
                error_text = menu.title + " " + (menu.description or "")

                # Should not contain harsh technical errors
                harsh_terms = ["error", "failed", "exception", "invalid", "not found"]
                has_harsh_terms = any(term in error_text.lower() for term in harsh_terms)

                if has_harsh_terms:
                    # If technical terms are present, they should be softened with Lucien's language
                    sophisticated_softening = [
                        "appears", "seems", "perhaps", "momentarily", "temporarily",
                        "experiencing", "encountering", "difficulty", "challenge"
                    ]
                    has_softening = any(term in error_text.lower() for term in sophisticated_softening)
                    assert has_softening, f"Error message should be softened with Lucien's voice: {error_text}"

        except Exception:
            # Exceptions are acceptable for invalid requests
            pass

    @pytest.mark.asyncio
    async def test_lucien_worthiness_assessment_voice(self, menu_factory_with_lucien):
        """Test Lucien's voice when communicating worthiness assessments."""
        # Test with low worthiness user
        low_worthiness_context = RELATIONSHIP_CONTEXTS["low_worthiness"]

        menu = await menu_factory_with_lucien.generate_menu("vip_menu", low_worthiness_context)

        if menu:
            # Find restricted items (should be most or all items)
            restricted_items = [item for item in menu.items if not item.is_enabled and item.restriction_reason]

            assert len(restricted_items) > 0, "Low worthiness user should see restrictions"

            for item in restricted_items:
                restriction_text = item.restriction_reason.lower()

                # Should provide constructive guidance, not judgment
                constructive_language = [
                    "develop", "grow", "cultivate", "authentic", "genuine",
                    "meaningful", "deeper", "understanding", "journey", "exploration"
                ]

                has_constructive_guidance = any(term in restriction_text for term in constructive_language)
                assert has_constructive_guidance, \
                    f"Low worthiness restriction should be constructive: {item.restriction_reason}"

                # Should avoid judgmental language
                judgmental_language = ["unworthy", "insufficient", "inadequate", "lacking", "poor"]
                has_judgmental_language = any(term in restriction_text for term in judgmental_language)
                assert not has_judgmental_language, \
                    f"Lucien should not use judgmental language: {item.restriction_reason}"

    @pytest.mark.asyncio
    async def test_lucien_voice_performance_under_load(self, menu_factory_with_lucien):
        """Test that Lucien's voice quality is maintained under system load."""
        # Create multiple concurrent menu generation requests
        tasks = []
        contexts = list(RELATIONSHIP_CONTEXTS.values()) * 5  # 20 total requests

        for i, context in enumerate(contexts):
            # Modify context to create unique users
            test_context = context.copy()
            test_context["user_id"] = f"load_test_user_{i}"

            task = menu_factory_with_lucien.generate_menu("main_menu", test_context)
            tasks.append((task, test_context))

        # Execute concurrently
        results = await asyncio.gather(*[task[0] for task in tasks], return_exceptions=True)

        # Verify voice quality is maintained
        successful_results = []
        for i, result in enumerate(results):
            if not isinstance(result, Exception) and result:
                context = tasks[i][1]
                successful_results.append((result, context))

        assert len(successful_results) >= len(contexts) * 0.8, "Too many failures under load"

        # Check voice quality in successful results
        voice_quality_count = 0
        for menu, context in successful_results[:10]:  # Check first 10 for performance
            try:
                await self._verify_lucien_voice_characteristics(menu.title, context)
                voice_quality_count += 1
            except AssertionError:
                pass

        voice_quality_ratio = voice_quality_count / min(10, len(successful_results))
        assert voice_quality_ratio >= 0.8, \
            f"Voice quality degraded under load: {voice_quality_ratio:.2f} (need >= 0.8)"


class TestLucienVoiceGeneration:
    """Test direct Lucien voice generation functionality."""

    @pytest.mark.asyncio
    async def test_lucien_menu_specific_responses(self):
        """Test Lucien's responses for menu-specific scenarios."""
        voice_profile = LucienVoiceProfile()

        # Test different menu scenarios
        scenarios = [
            {
                "context": "menu_welcome",
                "user_context": RELATIONSHIP_CONTEXTS["new_acquaintance"],
                "expected_elements": ["welcome", "pleasure", "honor"]
            },
            {
                "context": "menu_restriction",
                "user_context": RELATIONSHIP_CONTEXTS["low_worthiness"],
                "expected_elements": ["patience", "understanding", "journey"]
            },
            {
                "context": "menu_unlock",
                "user_context": RELATIONSHIP_CONTEXTS["intimate_connection"],
                "expected_elements": ["celebration", "achievement", "worthy"]
            }
        ]

        for scenario in scenarios:
            response = await generate_lucien_response(
                scenario["context"],
                scenario["user_context"],
                voice_profile
            )

            # Verify response contains expected elements
            response_lower = response.lower()
            has_expected_elements = any(
                element in response_lower for element in scenario["expected_elements"]
            )

            assert has_expected_elements, \
                f"Response should contain expected elements for {scenario['context']}: {response}"

            # Verify sophisticated language
            await self._verify_response_sophistication(response)

    async def _verify_response_sophistication(self, response: str) -> None:
        """Verify response maintains Lucien's sophisticated standards."""
        response_lower = response.lower()

        # Should avoid casual/informal language
        casual_language = ["yeah", "yep", "okay", "sure thing", "no problem", "cool"]
        has_casual_language = any(term in response_lower for term in casual_language)
        assert not has_casual_language, f"Response should avoid casual language: {response}"

        # Should maintain proper grammar and structure
        assert len(response.split()) >= 3, "Response should be substantive"
        assert response[0].isupper(), "Response should start with capital letter"


# Test configuration
@pytest.mark.integration
class TestLucienMenuIntegration:
    """Integration tests for Lucien voice in complete menu system."""

    @pytest.mark.asyncio
    async def test_end_to_end_lucien_integration(self):
        """Test Lucien voice integration in complete menu interaction flow."""
        # This would test complete integration with actual menu system
        # Implementation depends on full system setup
        pass


def pytest_configure(config):
    """Configure pytest for Lucien integration tests."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )

def pytest_collection_modifyitems(config, items):
    """Add integration marker to integration tests."""
    for item in items:
        if "integration" in item.nodeid or "test_menu_lucien" in item.nodeid:
            item.add_marker(pytest.mark.integration)