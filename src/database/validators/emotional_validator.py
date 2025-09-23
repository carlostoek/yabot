"""
Emotional data validation utilities for the Diana Emotional System.

This module provides validation for emotional behavioral data,
ensuring data integrity and consistency as required by the emocional specification.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import re
from src.utils.logger import get_logger
from src.database.schemas.emotional import (
    MemoryFragment, 
    EmotionalResponse, 
    ProgressionAssessment,
    PersonalizedResponse,
    ContentVariant,
    MemoryCallback
)

logger = get_logger(__name__)


class ValidationError(Exception):
    """Base exception for emotional data validation errors."""
    pass


class EmotionalDataValidator:
    """Validator for emotional behavioral data integrity."""
    
    # Valid archetype constants
    VALID_ARCHETYPES = [
        "EXPLORADOR_PROFUNDO",
        "DIRECTO_AUTENTICO", 
        "POETA_DESEO",
        "ANALITICO_EMPATICO",
        "PERSISTENTE_PACIENTE"
    ]
    
    # Valid memory types
    VALID_MEMORY_TYPES = [
        "VULNERABILITY_MOMENT",
        "BREAKTHROUGH",
        "RESISTANCE", 
        "AUTHENTIC_SHARING",
        "EMOTIONAL_DEEPENING"
    ]
    
    # Valid Diana levels (1-6)
    MIN_DIANA_LEVEL = 1
    MAX_DIANA_LEVEL = 6
    
    def __init__(self):
        """Initialize emotional data validator."""
        logger.debug("Initialized EmotionalDataValidator")
    
    def validate_emotional_signature(self, signature_data: Dict[str, Any]) -> bool:
        """Validate emotional signature data integrity.
        
        Args:
            signature_data: Emotional signature data to validate
            
        Returns:
            bool: True if data is valid, False otherwise
            
        Raises:
            ValidationError: If data is invalid with specific error details
        """
        if not isinstance(signature_data, dict):
            raise ValidationError("Emotional signature must be a dictionary")
        
        # Validate archetype if present
        archetype = signature_data.get("archetype")
        if archetype is not None:
            if not isinstance(archetype, str):
                raise ValidationError("Archetype must be a string")
            if archetype not in self.VALID_ARCHETYPES:
                raise ValidationError(f"Invalid archetype '{archetype}'. Must be one of: {self.VALID_ARCHETYPES}")
        
        # Validate authenticity_score if present
        auth_score = signature_data.get("authenticity_score")
        if auth_score is not None:
            if not isinstance(auth_score, (int, float)):
                raise ValidationError("Authenticity score must be numeric")
            if not (0.0 <= auth_score <= 1.0):
                raise ValidationError("Authenticity score must be between 0.0 and 1.0")
        
        # Validate vulnerability_level if present
        vuln_level = signature_data.get("vulnerability_level")
        if vuln_level is not None:
            if not isinstance(vuln_level, (int, float)):
                raise ValidationError("Vulnerability level must be numeric")
            if not (0.0 <= vuln_level <= 1.0):
                raise ValidationError("Vulnerability level must be between 0.0 and 1.0")
        
        # Validate signature_strength if present
        sig_strength = signature_data.get("signature_strength")
        if sig_strength is not None:
            if not isinstance(sig_strength, (int, float)):
                raise ValidationError("Signature strength must be numeric")
            if not (0.0 <= sig_strength <= 1.0):
                raise ValidationError("Signature strength must be between 0.0 and 1.0")
        
        logger.debug("Emotional signature data validated successfully")
        return True
    
    def validate_memory_fragment(self, fragment_data: Dict[str, Any]) -> bool:
        """Validate emotional memory fragment data integrity.
        
        Args:
            fragment_data: Memory fragment data to validate
            
        Returns:
            bool: True if data is valid, False otherwise
            
        Raises:
            ValidationError: If data is invalid with specific error details
        """
        if not isinstance(fragment_data, dict):
            raise ValidationError("Memory fragment data must be a dictionary")
        
        # Validate required fields
        required_fields = ["user_id", "interaction_context", "emotional_significance", "memory_type", "content_summary"]
        for field in required_fields:
            if field not in fragment_data:
                raise ValidationError(f"Required field '{field}' missing from memory fragment")
        
        # Validate user_id
        user_id = fragment_data.get("user_id")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValidationError("User ID must be a non-empty string")
        
        # Validate emotional_significance
        emo_sig = fragment_data.get("emotional_significance")
        if not isinstance(emo_sig, (int, float)):
            raise ValidationError("Emotional significance must be numeric")
        if not (0.0 <= emo_sig <= 1.0):
            raise ValidationError("Emotional significance must be between 0.0 and 1.0")
        
        # Validate memory_type
        mem_type = fragment_data.get("memory_type")
        if not isinstance(mem_type, str):
            raise ValidationError("Memory type must be a string")
        if mem_type not in self.VALID_MEMORY_TYPES:
            raise ValidationError(f"Invalid memory type '{mem_type}'. Must be one of: {self.VALID_MEMORY_TYPES}")
        
        # Validate relationship_stage
        rel_stage = fragment_data.get("relationship_stage")
        if rel_stage is not None:
            if not isinstance(rel_stage, int):
                raise ValidationError("Relationship stage must be an integer")
            if not (self.MIN_DIANA_LEVEL <= rel_stage <= self.MAX_DIANA_LEVEL):
                raise ValidationError(f"Relationship stage must be between {self.MIN_DIANA_LEVEL} and {self.MAX_DIANA_LEVEL}")
        
        # Validate content_summary
        content_summary = fragment_data.get("content_summary")
        if not isinstance(content_summary, str) or len(content_summary.strip()) == 0:
            raise ValidationError("Content summary must be a non-empty string")
        
        logger.debug("Memory fragment data validated successfully")
        return True
    
    def validate_emotional_response(self, response_data: Dict[str, Any]) -> bool:
        """Validate emotional response data integrity.
        
        Args:
            response_data: Emotional response data to validate
            
        Returns:
            bool: True if data is valid, False otherwise
            
        Raises:
            ValidationError: If data is invalid with specific error details
        """
        if not isinstance(response_data, dict):
            raise ValidationError("Emotional response data must be a dictionary")
        
        # Try to parse with Pydantic model for comprehensive validation
        try:
            EmotionalResponse(**response_data)
        except Exception as e:
            raise ValidationError(f"Emotional response data validation failed: {str(e)}")
        
        logger.debug("Emotional response data validated successfully")
        return True
    
    def validate_emotional_interaction(self, interaction_data: Dict[str, Any]) -> bool:
        """Validate emotional interaction data integrity.
        
        Args:
            interaction_data: Emotional interaction data to validate
            
        Returns:
            bool: True if data is valid, False otherwise
            
        Raises:
            ValidationError: If data is invalid with specific error details
        """
        if not isinstance(interaction_data, dict):
            raise ValidationError("Emotional interaction data must be a dictionary")
        
        # Validate required fields
        required_fields = ["user_id", "interaction_type"]
        for field in required_fields:
            if field not in interaction_data:
                raise ValidationError(f"Required field '{field}' missing from interaction data")
        
        # Validate user_id
        user_id = interaction_data.get("user_id")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValidationError("User ID must be a non-empty string")
        
        # Validate interaction_type
        interaction_type = interaction_data.get("interaction_type")
        if not isinstance(interaction_type, str) or not interaction_type.strip():
            raise ValidationError("Interaction type must be a non-empty string")
        
        # Validate timestamps if present
        if "timestamp" in interaction_data:
            timestamp = interaction_data["timestamp"]
            if not isinstance(timestamp, datetime):
                raise ValidationError("Timestamp must be a datetime object")
        
        logger.debug("Emotional interaction data validated successfully")
        return True
    
    def validate_diana_level_progression(self, progression_data: Dict[str, Any]) -> bool:
        """Validate Diana level progression data.
        
        Args:
            progression_data: Diana level progression data to validate
            
        Returns:
            bool: True if data is valid, False otherwise
            
        Raises:
            ValidationError: If data is invalid with specific error details
        """
        if not isinstance(progression_data, dict):
            raise ValidationError("Diana level progression data must be a dictionary")
        
        # Validate required fields
        required_fields = ["previous_level", "new_level", "progression_reason"]
        for field in required_fields:
            if field not in progression_data:
                raise ValidationError(f"Required field '{field}' missing from progression data")
        
        # Validate level ranges
        prev_level = progression_data["previous_level"]
        new_level = progression_data["new_level"]
        
        if not isinstance(prev_level, int):
            raise ValidationError("Previous level must be an integer")
        if not (self.MIN_DIANA_LEVEL <= prev_level <= self.MAX_DIANA_LEVEL):
            raise ValidationError(f"Previous level must be between {self.MIN_DIANA_LEVEL} and {self.MAX_DIANA_LEVEL}")
        
        if not isinstance(new_level, int):
            raise ValidationError("New level must be an integer")
        if not (self.MIN_DIANA_LEVEL <= new_level <= self.MAX_DIANA_LEVEL):
            raise ValidationError(f"New level must be between {self.MIN_DIANA_LEVEL} and {self.MAX_DIANA_LEVEL}")
        
        if new_level <= prev_level:
            raise ValidationError("New level must be greater than previous level")
        
        # Validate progression_reason
        reason = progression_data["progression_reason"]
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError("Progression reason must be a non-empty string")
        
        logger.debug("Diana level progression data validated successfully")
        return True
    
    def sanitize_emotional_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize emotional data to remove potentially harmful content.
        
        Args:
            data: Emotional data to sanitize
            
        Returns:
            Dict[str, Any]: Sanitized emotional data
        """
        sanitized_data = data.copy()
        
        # Remove any fields that might contain sensitive information
        sensitive_keywords = ["password", "token", "secret", "key", "credential"]
        
        # Recursively sanitize nested dictionaries
        def sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            result = {}
            for key, value in d.items():
                # Skip sensitive fields
                if any(keyword in key.lower() for keyword in sensitive_keywords):
                    continue
                    
                # Sanitize nested structures
                if isinstance(value, dict):
                    result[key] = sanitize_dict(value)
                elif isinstance(value, list):
                    result[key] = sanitize_list(value)
                elif isinstance(value, str):
                    result[key] = self._sanitize_string(value)
                else:
                    result[key] = value
            return result
        
        def sanitize_list(lst: List[Any]) -> List[Any]:
            result = []
            for item in lst:
                if isinstance(item, dict):
                    result.append(sanitize_dict(item))
                elif isinstance(item, list):
                    result.append(sanitize_list(item))
                elif isinstance(item, str):
                    result.append(self._sanitize_string(item))
                else:
                    result.append(item)
            return result
        
        # Apply sanitization to top-level data
        return sanitize_dict(sanitized_data)
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize string content to prevent injection attacks.
        
        Args:
            text: String to sanitize
            
        Returns:
            str: Sanitized string
        """
        # Remove null bytes and other dangerous characters
        text = text.replace('\x00', '')
        
        # Limit length to prevent resource exhaustion
        max_length = 10000  # Arbitrary limit
        if len(text) > max_length:
            text = text[:max_length]
        
        return text


# Global emotional data validator instance
_emotional_validator = None


def get_emotional_validator() -> EmotionalDataValidator:
    """Get global emotional data validator instance.
    
    Returns:
        EmotionalDataValidator: Global emotional data validator
    """
    global _emotional_validator
    if _emotional_validator is None:
        _emotional_validator = EmotionalDataValidator()
    return _emotional_validator


def validate_emotional_signature(signature_data: Dict[str, Any]) -> bool:
    """Validate emotional signature data using global validator.
    
    Args:
        signature_data: Emotional signature data to validate
        
    Returns:
        bool: True if data is valid
        
    Raises:
        ValidationError: If data is invalid with specific error details
    """
    return get_emotional_validator().validate_emotional_signature(signature_data)


def validate_memory_fragment(fragment_data: Dict[str, Any]) -> bool:
    """Validate emotional memory fragment data using global validator.
    
    Args:
        fragment_data: Memory fragment data to validate
        
    Returns:
        bool: True if data is valid
        
    Raises:
        ValidationError: If data is invalid with specific error details
    """
    return get_emotional_validator().validate_memory_fragment(fragment_data)


def validate_emotional_response(response_data: Dict[str, Any]) -> bool:
    """Validate emotional response data using global validator.
    
    Args:
        response_data: Emotional response data to validate
        
    Returns:
        bool: True if data is valid
        
    Raises:
        ValidationError: If data is invalid with specific error details
    """
    return get_emotional_validator().validate_emotional_response(response_data)


def validate_emotional_interaction(interaction_data: Dict[str, Any]) -> bool:
    """Validate emotional interaction data using global validator.
    
    Args:
        interaction_data: Emotional interaction data to validate
        
    Returns:
        bool: True if data is valid
        
    Raises:
        ValidationError: If data is invalid with specific error details
    """
    return get_emotional_validator().validate_emotional_interaction(interaction_data)


def validate_diana_level_progression(progression_data: Dict[str, Any]) -> bool:
    """Validate Diana level progression data using global validator.
    
    Args:
        progression_data: Diana level progression data to validate
        
    Returns:
        bool: True if data is valid
        
    Raises:
        ValidationError: If data is invalid with specific error details
    """
    return get_emotional_validator().validate_diana_level_progression(progression_data)


def sanitize_emotional_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize emotional data using global validator.
    
    Args:
        data: Emotional data to sanitize
        
    Returns:
        Dict[str, Any]: Sanitized emotional data
    """
    return get_emotional_validator().sanitize_emotional_data(data)


# Convenience validation functions for specific components
def validate_personalized_response(response_data: Dict[str, Any]) -> bool:
    """Validate personalized response data.
    
    Args:
        response_data: Personalized response data to validate
        
    Returns:
        bool: True if data is valid
        
    Raises:
        ValidationError: If data is invalid with specific error details
    """
    try:
        PersonalizedResponse(**response_data)
        return True
    except Exception as e:
        raise ValidationError(f"Personalized response validation failed: {str(e)}")


def validate_content_variant(variant_data: Dict[str, Any]) -> bool:
    """Validate content variant data.
    
    Args:
        variant_data: Content variant data to validate
        
    Returns:
        bool: True if data is valid
        
    Raises:
        ValidationError: If data is invalid with specific error details
    """
    try:
        ContentVariant(**variant_data)
        return True
    except Exception as e:
        raise ValidationError(f"Content variant validation failed: {str(e)}")


def validate_memory_callback(callback_data: Dict[str, Any]) -> bool:
    """Validate memory callback data.
    
    Args:
        callback_data: Memory callback data to validate
        
    Returns:
        bool: True if data is valid
        
    Raises:
        ValidationError: If data is invalid with specific error details
    """
    try:
        MemoryCallback(**callback_data)
        return True
    except Exception as e:
        raise ValidationError(f"Memory callback validation failed: {str(e)}")


# Bulk validation functions
def validate_multiple_memory_fragments(fragments: List[Dict[str, Any]]) -> List[bool]:
    """Validate multiple memory fragments at once.
    
    Args:
        fragments: List of memory fragment data to validate
        
    Returns:
        List[bool]: List of validation results for each fragment
    """
    results = []
    validator = get_emotional_validator()
    for fragment in fragments:
        try:
            results.append(validator.validate_memory_fragment(fragment))
        except ValidationError:
            results.append(False)
        except Exception:
            results.append(False)
    return results


def validate_emotional_journey_state(state_data: Dict[str, Any]) -> bool:
    """Validate emotional journey state data.
    
    Args:
        state_data: Emotional journey state data to validate
        
    Returns:
        bool: True if data is valid
        
    Raises:
        ValidationError: If data is invalid with specific error details
    """
    if not isinstance(state_data, dict):
        raise ValidationError("Emotional journey state must be a dictionary")
    
    # Validate current level if present
    current_level = state_data.get("current_level")
    if current_level is not None:
        if not isinstance(current_level, int):
            raise ValidationError("Current level must be an integer")
        if not (1 <= current_level <= 6):
            raise ValidationError("Current level must be between 1 and 6")
    
    # Validate level entry date if present
    level_entry_date = state_data.get("level_entry_date")
    if level_entry_date is not None and not isinstance(level_entry_date, datetime):
        raise ValidationError("Level entry date must be a datetime object")
    
    logger.debug("Emotional journey state data validated successfully")
    return True