"""
PLC Format Converter Library

Modern ACD ↔ L5X conversion library with industrial-grade validation 
and motion control support.

Copyright (c) 2025 PLC-GPT Team
Licensed under the MIT License
"""

__version__ = "2.0.0"
__author__ = "PLC-GPT Team"
__email__ = "plc-gpt@example.com"
__license__ = "MIT"
__description__ = "Modern ACD ↔ L5X conversion library with industrial-grade validation and motion control support"

# Main library exports
from .core.models import (
    # Core data models
    PLCProject,
    PLCController,
    PLCProgram,
    PLCRoutine,
    PLCTag,
    PLCDevice,
    PLCAddOnInstruction,
    PLCUserDefinedType,
    PLCMetadata,
    
    # Enums
    DataType,
    RoutineType,
    ConversionStatus,
    PLCComponentType,
    
    # Exceptions
    ConversionError,
    ValidationError,
    FormatError,
    
    # Results
    ConversionResult,
    ConversionIssue
)

from .formats import (
    ACDHandler,
    L5XHandler
)

from .utils import (
    PLCValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity
)

# Convenience imports for common use cases
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
    
    # Core models
    "PLCProject",
    "PLCController", 
    "PLCProgram",
    "PLCRoutine",
    "PLCTag",
    "PLCDevice",
    "PLCAddOnInstruction",
    "PLCUserDefinedType",
    "PLCMetadata",
    
    # Enums
    "DataType",
    "RoutineType", 
    "ConversionStatus",
    "PLCComponentType",
    
    # Format handlers
    "ACDHandler",
    "L5XHandler",
    
    # Validation
    "PLCValidator",
    "ValidationResult",
    "ValidationIssue", 
    "ValidationSeverity",
    
    # Exceptions
    "ConversionError",
    "ValidationError",
    "FormatError",
    
    # Results
    "ConversionResult",
    "ConversionIssue"
]


def get_version() -> str:
    """Get the current version of the library."""
    return __version__


def get_library_info() -> dict:
    """Get comprehensive library information."""
    return {
        "name": "plc-format-converter",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "license": __license__,
        "description": __description__,
        "supported_formats": ["ACD", "L5X"],
        "features": [
            "Format conversion",
            "Validation framework", 
            "Motion control support",
            "Safety system support",
            "Round-trip integrity"
        ]
    }


# Quick usage examples for documentation
def quick_examples():
    """Print quick usage examples."""
    examples = """
PLC Format Converter - Quick Examples
====================================

1. Convert ACD to L5X:
   from plc_format_converter import ACDHandler, L5XHandler
   
   acd_handler = ACDHandler()
   l5x_handler = L5XHandler()
   
   project = acd_handler.load("project.acd")
   l5x_handler.save(project, "project.L5X")

2. Validate a project:
   from plc_format_converter import PLCValidator, L5XHandler
   
   handler = L5XHandler()
   validator = PLCValidator()
   
   project = handler.load("project.L5X") 
   result = validator.validate_project(project)
   print(f"Valid: {result.is_valid}")

3. Check capabilities:
   from plc_format_converter import ACDHandler
   
   handler = ACDHandler()
   caps = handler.get_capabilities()
   print(f"Features: {caps['features']}")

For complete documentation: https://plc-format-converter.readthedocs.io
"""
    print(examples) 