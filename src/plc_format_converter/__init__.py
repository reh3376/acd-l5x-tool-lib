"""
PLC Format Converter - Enhanced Phase 3.9
==========================================

Modern ACD ↔ L5X conversion library with 95%+ data preservation capability.
"""

__version__ = "2.1.0"
__author__ = "PLC-GPT Team"

# Enhanced Phase 3.9 Exports
from .core.models import (
    PLCProject, PLCController, PLCProgram, PLCRoutine, PLCTag,
    ConversionResult, ConversionStatus, DataIntegrityScore
)
from .core.converter import EnhancedPLCConverter
from .utils.validation import DataIntegrityValidator, RoundTripValidator
from .utils.git_optimization import GitOptimizer

# Backward compatibility
PLCConverter = EnhancedPLCConverter

__all__ = [
    "PLCProject", "PLCController", "PLCProgram", "PLCRoutine", "PLCTag",
    "ConversionResult", "ConversionStatus", "DataIntegrityScore",
    "EnhancedPLCConverter", "PLCConverter",
    "DataIntegrityValidator", "RoundTripValidator", "GitOptimizer"
]
