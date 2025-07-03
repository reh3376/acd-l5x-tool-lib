"""
Core converter class for PLC format conversion.

This module provides the main PLCConverter class that orchestrates
bidirectional conversion between ACD and L5X formats.
"""

import time
from pathlib import Path
from typing import Optional, Union

import structlog

from ..formats.acd_handler import ACDHandler
from ..formats.l5x_handler import L5XHandler
from ..utils.validation import PLCValidator
from .models import (
    ConversionError,
    ConversionResult,
    ConversionStatus,
    PLCProject,
    FormatError,
)

logger = structlog.get_logger()


class PLCConverter:
    """
    Main converter class for bidirectional PLC format conversion.
    
    Supports conversion between Rockwell .ACD and .L5X formats with
    comprehensive validation and error reporting.
    """
    
    def __init__(self, validate_round_trip: bool = True, strict_mode: bool = False):
        """
        Initialize the PLC converter.
        
        Args:
            validate_round_trip: Whether to perform round-trip validation
            strict_mode: Whether to fail on warnings (not just errors)
        """
        self.validate_round_trip = validate_round_trip
        self.strict_mode = strict_mode
        self.acd_handler = ACDHandler()
        self.l5x_handler = L5XHandler()
        self.validator = PLCValidator()
        
        logger.info(
            "PLCConverter initialized",
            validate_round_trip=validate_round_trip,
            strict_mode=strict_mode
        )
    
    def convert_file(
        self, 
        source_file: Union[str, Path], 
        target_file: Optional[Union[str, Path]] = None,
        target_format: Optional[str] = None
    ) -> ConversionResult:
        """
        Convert a PLC file from one format to another.
        
        Args:
            source_file: Path to the source file (.acd or .l5x)
            target_file: Path to the target file (optional, will auto-generate if not provided)
            target_format: Target format ("ACD" or "L5X", auto-detected if not provided)
            
        Returns:
            ConversionResult with conversion status and details
            
        Raises:
            ConversionError: If conversion fails
            FileNotFoundError: If source file doesn't exist
        """
        start_time = time.time()
        source_path = Path(source_file)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Detect source format
        source_format = self._detect_format(source_path)
        
        # Determine target format and path
        if target_format is None:
            target_format = "L5X" if source_format == "ACD" else "ACD"
        
        if target_file is None:
            target_file = self._generate_target_path(source_path, target_format)
        else:
            target_file = Path(target_file)
        
        logger.info(
            "Starting conversion",
            source_file=str(source_path),
            target_file=str(target_file),
            source_format=source_format,
            target_format=target_format
        )
        
        try:
            # Load source project
            project = self._load_project(source_path, source_format)
            
            # Validate project before conversion
            validation_result = self.validator.validate_project(project)
            
            # Convert project
            result = self._convert_project(
                project=project,
                source_file=str(source_path),
                target_file=str(target_file),
                source_format=source_format,
                target_format=target_format,
                conversion_time=time.time() - start_time
            )
            
            # Add validation issues to result
            result.issues.extend(validation_result.issues)
            
            # Save converted project
            self._save_project(project, target_file, target_format)
            
            # Perform round-trip validation if enabled
            if self.validate_round_trip:
                self._perform_round_trip_validation(result, source_path, target_file)
            
            # Update final status
            result.conversion_time = time.time() - start_time
            
            # Check validation result for errors/warnings
            errors = [issue for issue in result.issues if hasattr(issue, 'severity') and issue.severity.value == 'ERROR']
            warnings = [issue for issue in result.issues if hasattr(issue, 'severity') and issue.severity.value == 'WARNING']
            
            result.success = len(errors) == 0
            
            if errors:
                result.status = ConversionStatus.ERROR
            elif warnings:
                result.status = ConversionStatus.WARNING
            else:
                result.status = ConversionStatus.SUCCESS
            
            logger.info(
                "Conversion completed",
                success=result.success,
                status=result.status,
                conversion_time=result.conversion_time,
                issues_count=len(result.issues)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Conversion failed",
                error=str(e),
                source_file=str(source_path),
                target_format=target_format
            )
            
            return ConversionResult(
                success=False,
                status=ConversionStatus.ERROR,
                source_format=source_format,
                target_format=target_format,
                source_file=str(source_path),
                target_file=str(target_file) if target_file else None,
                conversion_time=time.time() - start_time,
                issues=[{
                    "severity": ConversionStatus.ERROR,
                    "component_type": "converter",
                    "message": f"Conversion failed: {str(e)}",
                    "details": str(e)
                }]
            )
    
    def acd_to_l5x(
        self, 
        acd_file: Union[str, Path], 
        l5x_file: Optional[Union[str, Path]] = None
    ) -> ConversionResult:
        """
        Convert ACD file to L5X format.
        
        Args:
            acd_file: Path to the source .acd file
            l5x_file: Path to the target .l5x file (optional)
            
        Returns:
            ConversionResult with conversion status and details
        """
        return self.convert_file(acd_file, l5x_file, "L5X")
    
    def l5x_to_acd(
        self, 
        l5x_file: Union[str, Path], 
        acd_file: Optional[Union[str, Path]] = None
    ) -> ConversionResult:
        """
        Convert L5X file to ACD format.
        
        Args:
            l5x_file: Path to the source .l5x file
            acd_file: Path to the target .acd file (optional)
            
        Returns:
            ConversionResult with conversion status and details
        """
        return self.convert_file(l5x_file, acd_file, "ACD")
    
    def validate_file(self, file_path: Union[str, Path]) -> ConversionResult:
        """
        Validate a PLC file without conversion.
        
        Args:
            file_path: Path to the PLC file to validate
            
        Returns:
            ConversionResult with validation status and issues
        """
        start_time = time.time()
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        source_format = self._detect_format(file_path)
        
        try:
            project = self._load_project(file_path, source_format)
            validation_result = self.validator.validate_project(project)
            
            return ConversionResult(
                success=validation_result.is_valid,
                status=ConversionStatus.SUCCESS if validation_result.is_valid else ConversionStatus.ERROR,
                source_format=source_format,
                target_format=source_format,
                source_file=str(file_path),
                conversion_time=time.time() - start_time,
                project=project,
                issues=validation_result.issues
            )
            
        except Exception as e:
            return ConversionResult(
                success=False,
                status=ConversionStatus.ERROR,
                source_format=source_format,
                target_format=source_format,
                source_file=str(file_path),
                conversion_time=time.time() - start_time,
                issues=[{
                    "severity": ConversionStatus.ERROR,
                    "component_type": "validator",
                    "message": f"Validation failed: {str(e)}",
                    "details": str(e)
                }]
            )
    
    def _detect_format(self, file_path: Path) -> str:
        """Detect the format of a PLC file based on its extension."""
        suffix = file_path.suffix.lower()
        
        if suffix == ".acd":
            return "ACD"
        elif suffix == ".l5x":
            return "L5X"
        else:
            raise FormatError(f"Unsupported file format: {suffix}")
    
    def _generate_target_path(self, source_path: Path, target_format: str) -> Path:
        """Generate a target file path based on source path and target format."""
        if target_format.upper() == "ACD":
            return source_path.with_suffix(".ACD")
        elif target_format.upper() == "L5X":
            return source_path.with_suffix(".L5X")
        else:
            raise FormatError(f"Unsupported target format: {target_format}")
    
    def _load_project(self, file_path: Path, format_type: str) -> PLCProject:
        """Load a PLC project from file."""
        if format_type == "ACD":
            return self.acd_handler.load(file_path)
        elif format_type == "L5X":
            return self.l5x_handler.load(file_path)
        else:
            raise FormatError(f"Unsupported format: {format_type}")
    
    def _save_project(self, project: PLCProject, file_path: Path, format_type: str) -> None:
        """Save a PLC project to file."""
        if format_type == "ACD":
            self.acd_handler.save(project, file_path)
        elif format_type == "L5X":
            self.l5x_handler.save(project, file_path)
        else:
            raise FormatError(f"Unsupported format: {format_type}")
    
    def _convert_project(
        self,
        project: PLCProject,
        source_file: str,
        target_file: str,
        source_format: str,
        target_format: str,
        conversion_time: float
    ) -> ConversionResult:
        """Create a conversion result for the project."""
        
        # Update project metadata
        project.source_format = source_format
        project.modified_at = time.time()
        
        # Calculate statistics
        stats = {
            "programs": len(project.programs),
            "routines": sum(len(p.routines) for p in project.programs),
            "aois": len(project.add_on_instructions),
            "udts": len(project.user_defined_types),
            "controller_tags": len(project.controller_tags),
            "devices": len(project.devices),
            "total_tags": len(project.controller_tags) + sum(len(p.tags) for p in project.programs)
        }
        
        return ConversionResult(
            success=True,
            status=ConversionStatus.SUCCESS,
            source_format=source_format,
            target_format=target_format,
            source_file=source_file,
            target_file=target_file,
            conversion_time=conversion_time,
            project=project,
            statistics=stats
        )
    
    def _perform_round_trip_validation(
        self, 
        result: ConversionResult, 
        original_file: Path, 
        converted_file: Path
    ) -> None:
        """Perform round-trip validation to ensure data integrity."""
        try:
            logger.info("Performing round-trip validation")
            
            # Load both projects
            original_project = self._load_project(original_file, result.source_format)
            converted_project = self._load_project(converted_file, result.target_format)
            
            # Validate round-trip
            validation_result = self.validator.validate_round_trip(original_project, converted_project)
            result.issues.extend(validation_result.issues)
            
            if not validation_result.is_valid:
                errors = validation_result.get_errors()
                if errors:
                    logger.warning("Round-trip validation found errors")
                else:
                    logger.info("Round-trip validation found warnings")
            else:
                logger.info("Round-trip validation passed")
                
        except Exception as e:
            logger.error("Round-trip validation failed", error=str(e))
            result.issues.append({
                "severity": ConversionStatus.ERROR,
                "component_type": "validator",
                "message": f"Round-trip validation failed: {str(e)}",
                "details": str(e)
            }) 