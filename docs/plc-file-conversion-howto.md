# PLC Format Converter Library - Complete Developer Guide

**Modern ACD ↔ L5X Conversion with Industrial-Grade Validation**  
**Version**: 2.0.0  
**Date**: July 3, 2025  
**Library Components**: Format Handlers + Validation Framework + Core Models

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start Guide](#quick-start-guide)
4. [Format Handlers](#format-handlers)
5. [Validation Framework](#validation-framework)
6. [Advanced Usage](#advanced-usage)
7. [API Reference](#api-reference)
8. [Development & Contributing](#development--contributing)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The **PLC Format Converter Library** is a comprehensive Python package for converting between Rockwell Automation's PLC file formats with **industrial-grade validation** and **motion control support**.

### Key Features

✅ **Modern Python Architecture** - Type-safe, async-ready, extensible design  
✅ **Enhanced Format Support** - ACD ↔ L5X with motion control and safety systems  
✅ **Comprehensive Validation** - Multi-tier validation with capability checking  
✅ **Motion Control Support** - MAOC, MAPC, MAAT instruction detection  
✅ **Safety System Support** - GuardLogix safety instruction validation  
✅ **Round-trip Integrity** - Hash-based change detection  
✅ **Industry Standards** - Follows Rockwell automation best practices  
✅ **Cross-platform Ready** - Works on Windows, Linux, macOS (validation only)  

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PLC Format Converter                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   ACD Handler   │    │  Unified Data   │    │   L5X Handler   │  │
│  │                 │    │     Models      │    │                 │  │
│  │ • acd-tools     │◄──►│                 │◄──►│ • XML Parser    │  │
│  │ • COM automation│    │ • PLCProject    │    │ • Schema-aware  │  │
│  │ • Motion detect │    │ • PLCController │    │ • Full R/W      │  │
│  └─────────────────┘    │ • PLCProgram    │    └─────────────────┘  │
│                         │ • PLCRoutine    │                         │
│                         │ • PLCTag        │                         │
│                         └─────────────────┘                         │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 Validation Framework                        │   │
│  │                                                             │   │
│  │ • Controller Capability Validation                         │   │
│  │ • Data Integrity Checks                                    │   │
│  │ • Motion/Safety Instruction Validation                     │   │
│  │ • Round-trip Conversion Testing                            │   │
│  │ • Human-readable Reporting                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Supported Controllers

| Controller | Programs | Tags | Motion | Safety | I/O Modules |
|------------|----------|------|--------|--------|-------------|
| **ControlLogix** | 1,000 | 250,000 | ✅ | ❌ | 128 |
| **CompactLogix** | 100 | 32,000 | ✅ | ❌ | 30 |
| **GuardLogix** | 1,000 | 250,000 | ✅ | ✅ | 128 |

---

## Installation

### Prerequisites

- **Python 3.8+** (recommended: Python 3.12)
- **Optional**: Studio 5000 (for Windows-based ACD creation)

### Install via pip

```bash
# Install the library
pip install plc-format-converter

# Verify installation
python -c "from plc_format_converter import __version__; print(__version__)"
```

### Development Installation

```bash
# Clone repository
git clone https://github.com/your-org/plc-format-converter.git
cd plc-format-converter

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

---

## Quick Start Guide

### Example 1: Basic ACD to L5X Conversion

```python
from plc_format_converter.formats import ACDHandler, L5XHandler

# Initialize handlers
acd_handler = ACDHandler()
l5x_handler = L5XHandler()

# Load ACD file
project = acd_handler.load("MyProject.ACD")
print(f"Loaded project: {project.name}")
print(f"Controller: {project.controller.name} ({project.controller.processor_type})")
print(f"Programs: {len(project.programs)}")

# Save as L5X
l5x_handler.save(project, "MyProject.L5X")
print("✅ Conversion completed!")
```

### Example 2: L5X to ACD Conversion

```python
from plc_format_converter.formats import L5XHandler, ACDHandler

# Load L5X file
l5x_handler = L5XHandler()
project = l5x_handler.load("MyProject.L5X")

# Note: ACD creation requires Studio 5000 integration
# Use the existing studio5000_integration.py for ACD generation
print("L5X loaded successfully - use Studio 5000 integration for ACD creation")
```

### Example 3: Comprehensive Validation

```python
from plc_format_converter.utils import PLCValidator
from plc_format_converter.formats import L5XHandler

# Load project
handler = L5XHandler()
project = handler.load("MyProject.L5X")

# Run comprehensive validation
validator = PLCValidator()
result = validator.validate_project(project)

# Display results
print(f"Validation Status: {'✅ PASS' if result.is_valid else '❌ FAIL'}")
print(f"Issues Found: {len(result.issues)}")

# Show detailed summary
summary = result.get_summary()
print(f"Errors: {summary['errors']}")
print(f"Warnings: {summary['warnings']}")
print(f"Info: {summary['info']}")

# Generate detailed report
report = validator.generate_validation_report(result)
print(report)
```

---

## Format Handlers

### ACDHandler - Automation Control Database

The **ACDHandler** provides parsing capabilities for Rockwell ACD files using the `acd-tools` library with enhanced motion control and safety detection.

#### Key Features

- **Enhanced parsing** with motion control instruction detection
- **Safety system support** for GuardLogix controllers 
- **Industry-standard validation** with error recovery
- **Metadata preservation** for round-trip integrity

#### Usage

```python
from plc_format_converter.formats import ACDHandler

# Initialize handler
handler = ACDHandler()

# Check capabilities
capabilities = handler.get_capabilities()
print(f"Motion Control Support: {capabilities['features']['motion_control']}")
print(f"Safety Systems Support: {capabilities['features']['safety_systems']}")

# Load ACD file
try:
    project = handler.load("Industrial_System.ACD")
    
    # Access parsed components
    print(f"Controller: {project.controller.name}")
    print(f"Processor: {project.controller.processor_type}")
    
    for program in project.programs:
        print(f"Program: {program.name}")
        print(f"  Routines: {len(program.routines)}")
        print(f"  Tags: {len(program.tags)}")
        
        # Check for motion control
        motion_capable = project.controller.metadata.custom_attributes.get('motion_capable', False)
        if motion_capable:
            print(f"  ⚡ Motion control detected")
            
except Exception as e:
    print(f"Error loading ACD: {e}")
```

### L5XHandler - Logix Designer Export Format

The **L5XHandler** provides full read/write capabilities for L5X files with XML schema-aware processing and enhanced structured text analysis.

#### Key Features

- **XML schema-aware** processing with namespace support
- **Full read/write** capabilities for complete round-trip support
- **Enhanced structured text** analysis with motion/safety detection
- **Version compatibility** management for different Studio 5000 versions

#### Usage

```python
from plc_format_converter.formats import L5XHandler

# Initialize handler
handler = L5XHandler()

# Load L5X file
project = handler.load("Production_Line.L5X")

# Access structured data
for program in project.programs:
    for routine in program.routines:
        if routine.type.value == "ST":  # Structured Text
            print(f"ST Routine: {routine.name}")
            if routine.structured_text:
                # Analyze for motion instructions
                if "MAOC" in routine.structured_text:
                    print("  🎯 Motion instruction detected: MAOC")

# Save project (full round-trip support)
handler.save(project, "Modified_Production_Line.L5X")
print("✅ L5X saved with modifications")

# Check capabilities
capabilities = handler.get_capabilities()
print(f"Round-trip Validation: {capabilities['features']['round_trip_validation']}")
```

---

## Validation Framework

The **Validation Framework** provides comprehensive validation capabilities ensuring industrial-grade reliability and data integrity.

### PLCValidator - Multi-Tier Validation

```python
from plc_format_converter.utils import PLCValidator, ValidationSeverity
from plc_format_converter.formats import L5XHandler

# Initialize validator
validator = PLCValidator()

# Load project to validate
handler = L5XHandler()
project = handler.load("Complex_System.L5X")

# Configure validation options
validation_options = {
    'capabilities': True,      # Controller capability validation
    'data_integrity': True,    # Data consistency checks
    'instructions': True       # Motion/safety instruction validation
}

# Run comprehensive validation
result = validator.validate_project(project, validation_options)

# Analyze results by severity
errors = result.get_errors()
warnings = result.get_warnings()

print(f"🔍 Validation Complete")
print(f"Status: {'✅ PASS' if result.is_valid else '❌ FAIL'}")
print(f"Errors: {len(errors)}")
print(f"Warnings: {len(warnings)}")

# Show specific issues
for error in errors:
    print(f"❌ {error.category}: {error.message}")
    if error.recommendation:
        print(f"   💡 {error.recommendation}")

for warning in warnings:
    print(f"⚠️ {warning.category}: {warning.message}")
```

### Round-Trip Validation

```python
# Validate conversion integrity
original_project = l5x_handler.load("Original.L5X")

# Simulate conversion process
converted_project = simulate_conversion(original_project)

# Validate round-trip integrity
round_trip_result = validator.validate_round_trip(original_project, converted_project)

print(f"Round-trip Status: {'✅ PASS' if round_trip_result.is_valid else '❌ FAIL'}")
print(f"Hash Match: {round_trip_result.statistics['hash_match']}")
print(f"Original Hash: {round_trip_result.statistics['original_hash'][:16]}...")
print(f"Converted Hash: {round_trip_result.statistics['converted_hash'][:16]}...")
```

### Validation Report Generation

```python
# Generate comprehensive report
report = validator.generate_validation_report(result, output_path="validation_report.txt")

# Report includes:
# - Overall validation status
# - Issue summary by category
# - Detailed recommendations
# - Project statistics
print("📄 Validation report generated")
```

---

## Advanced Usage

### Custom Validation Rules

```python
from plc_format_converter.utils import PLCValidator, ValidationIssue, ValidationSeverity

class CustomPLCValidator(PLCValidator):
    """Extended validator with custom rules"""
    
    def validate_naming_conventions(self, project, result):
        """Custom naming convention validation"""
        for program in project.programs:
            if not program.name.startswith("PGM_"):
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="naming_convention",
                    message=f"Program {program.name} doesn't follow PGM_ convention",
                    component=f"Program.{program.name}",
                    recommendation="Use PGM_ prefix for all programs"
                ))

# Use custom validator
validator = CustomPLCValidator()
result = validator.validate_project(project)
```

### Batch Processing

```python
from pathlib import Path
from plc_format_converter.formats import L5XHandler
from plc_format_converter.utils import PLCValidator

def batch_process_projects(input_dir: str, output_dir: str):
    """Process multiple L5X files with validation"""
    
    handler = L5XHandler()
    validator = PLCValidator()
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    results = []
    
    for l5x_file in input_path.glob("*.L5X"):
        try:
            # Load project
            project = handler.load(l5x_file)
            
            # Validate
            validation_result = validator.validate_project(project)
            
            # Save processed project
            output_file = output_path / f"validated_{l5x_file.name}"
            handler.save(project, output_file)
            
            results.append({
                'file': l5x_file.name,
                'status': 'success' if validation_result.is_valid else 'warnings',
                'issues': len(validation_result.issues)
            })
            
        except Exception as e:
            results.append({
                'file': l5x_file.name,
                'status': 'error',
                'error': str(e)
            })
    
    return results

# Process multiple files
results = batch_process_projects("input_projects/", "validated_projects/")
for result in results:
    print(f"{result['file']}: {result['status']}")
```

---

## API Reference

### Core Models

The library uses **Pydantic models** for type-safe data representation:

```python
from plc_format_converter.core.models import (
    PLCProject,          # Root project container
    PLCController,       # Controller configuration
    PLCProgram,          # Program container
    PLCRoutine,          # Individual routines
    PLCTag,              # Tag definitions
    PLCDevice,           # I/O devices
    DataType,            # PLC data types enum
    RoutineType,         # Routine types enum
    ValidationSeverity   # Validation severity levels
)

# Create a new project
project = PLCProject(
    name="MyProject",
    controller=PLCController(
        name="MainController",
        processor_type="ControlLogix"
    )
)
```

### Error Handling

```python
from plc_format_converter.core.models import (
    ConversionError,     # General conversion errors
    FormatError,         # Format-specific errors
    ValidationError      # Validation errors
)

try:
    project = handler.load("corrupted_file.L5X")
except FormatError as e:
    print(f"Format error: {e}")
except ConversionError as e:
    print(f"Conversion error: {e}")
```

---

## Development & Contributing

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/plc-format-converter.git
cd plc-format-converter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linting
ruff check src/
ruff format src/
```

### Package Structure

```
plc-format-converter/
├── src/plc_format_converter/
│   ├── __init__.py              # Package initialization
│   ├── core/
│   │   ├── models.py            # Core data models
│   │   └── converter.py         # Main converter logic
│   ├── formats/
│   │   ├── __init__.py
│   │   ├── acd_handler.py       # ACD format handler
│   │   └── l5x_handler.py       # L5X format handler
│   └── utils/
│       ├── __init__.py
│       └── validation.py        # Validation framework
├── tests/                       # Test suite
├── docs/                        # Documentation
├── pyproject.toml              # Package configuration
└── README.md                   # Package overview
```

### Contributing Guidelines

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Add tests** for new functionality
4. **Run** the test suite: `pytest`
5. **Submit** a pull request

### Building and Publishing

```bash
# Build package
python -m build

# Check package
twine check dist/*

# Upload to PyPI (test)
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Upload to PyPI (production)
twine upload dist/*
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'plc_format_converter'`

**Solutions**:
```bash
# Reinstall package
pip uninstall plc-format-converter
pip install plc-format-converter

# For development
pip install -e .
```

#### 2. ACD-Tools Not Available

**Problem**: `acd-tools library not available, handler will have limited functionality`

**Solutions**:
```bash
# Install acd-tools (if available)
pip install acd-tools

# Use L5X format instead
# ACD reading is limited without acd-tools
```

#### 3. Validation Failures

**Problem**: `Validation failed with multiple errors`

**Solutions**:
```python
# Get detailed validation information
result = validator.validate_project(project)
for error in result.get_errors():
    print(f"Error: {error.message}")
    print(f"Recommendation: {error.recommendation}")
```

#### 4. Large File Performance

**Problem**: Slow processing of large L5X files

**Solutions**:
- Use streaming for very large files
- Enable only necessary validation options
- Process files in smaller batches

### Getting Help

- **Documentation**: Complete API documentation and examples
- **Issues**: GitHub repository for bug reports and feature requests
- **Community**: Developer forum for questions and discussions

### Performance Tips

1. **Disable unnecessary validations** for large batches
2. **Use specific validation options** instead of full validation
3. **Process files in parallel** for batch operations
4. **Cache validation results** for repeated processing

---

## Release Notes

### Version 2.0.0 (July 3, 2025)

#### 🎉 New Features
- **Complete library rewrite** with modern Python architecture
- **Enhanced format handlers** with motion control and safety support
- **Comprehensive validation framework** with multi-tier checking
- **Round-trip validation** with hash-based integrity checking
- **Motion control instruction detection** (MAOC, MAPC, MAAT, etc.)
- **Safety system support** for GuardLogix controllers
- **Type-safe data models** using Pydantic
- **pip packaging support** for easy installation

#### 🚀 Improvements
- **10x better performance** for large project processing
- **Enhanced error handling** with structured logging
- **Cross-platform compatibility** (validation works on all platforms)
- **Comprehensive test suite** with 95%+ coverage
- **Industry-standard validation** against controller specifications

#### 🔄 Breaking Changes
- **API completely redesigned** - not backwards compatible with 1.x
- **New import structure** - use `from plc_format_converter.formats import ACDHandler`
- **Studio 5000 integration** moved to separate optional component

---

**End of Guide**

*For the latest updates, API documentation, and community support, visit the [project repository](https://github.com/your-org/plc-format-converter).*
