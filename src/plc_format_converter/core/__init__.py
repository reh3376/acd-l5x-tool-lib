# Package initialization

# Phase 3.9 Enhanced Components

"""
Core Components for Enhanced PLC Format Converter
================================================

This module contains the core converter logic and data models for Phase 3.9
enhanced data preservation capabilities.
"""

from .converter import EnhancedPLCConverter
from .models import (
    PLCProject, PLCController, PLCProgram, PLCRoutine, PLCTag, PLCDevice,
    ConversionResult, ConversionStatus, DataIntegrityScore,
    # Enhanced models for Phase 3.9
    EnhancedPLCComponent, BinaryDataBlock, ComponentExtraction
)

__all__ = [
    "EnhancedPLCConverter",
    "PLCProject",
    "PLCController", 
    "PLCProgram",
    "PLCRoutine",
    "PLCTag",
    "PLCDevice",
    "ConversionResult",
    "ConversionStatus",
    "DataIntegrityScore",
    "EnhancedPLCComponent",
    "BinaryDataBlock",
    "ComponentExtraction"
] 