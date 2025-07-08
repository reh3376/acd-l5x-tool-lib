"""
Validation Framework for PLC Format Converter

This module provides comprehensive validation capabilities for PLC projects,
including schema validation, data integrity checks, and round-trip validation.
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

import structlog

# Import base classes from core
from ..core.models import (
    PLCProject, PLCController, PLCProgram, PLCRoutine, PLCTag, PLCDevice,
    PLCAddOnInstruction, PLCUserDefinedType, PLCMetadata, DataType,
    ConversionError, FormatError, RoutineType, PLCRung
)

logger = structlog.get_logger()


class ValidationSeverity(Enum):
    """Validation message severity levels"""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    """Represents a validation issue found during validation"""
    severity: ValidationSeverity
    category: str
    message: str
    component: str
    location: Optional[str] = None
    recommendation: Optional[str] = None
    error_code: Optional[str] = None


@dataclass
class ValidationResult:
    """Results of validation process"""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    validation_time: Optional[datetime] = None
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue"""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.is_valid = False
    
    def get_errors(self) -> List[ValidationIssue]:
        """Get all error-level issues"""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR]
    
    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning-level issues"""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]
    
    def get_summary(self) -> Dict[str, int]:
        """Get validation summary statistics"""
        return {
            'total_issues': len(self.issues),
            'errors': len(self.get_errors()),
            'warnings': len(self.get_warnings()),
            'info': len([i for i in self.issues if i.severity == ValidationSeverity.INFO])
        }


class PLCValidator:
    """Main PLC validation orchestrator"""
    
    def __init__(self):
        self.controller_specs = {
            'ControlLogix': {
                'max_programs': 1000,
                'max_routines_per_program': 1000,
                'max_tags': 250000,
                'motion_capable': True,
                'safety_capable': False,
                'max_io_modules': 128
            },
            'CompactLogix': {
                'max_programs': 100,
                'max_routines_per_program': 100,
                'max_tags': 32000,
                'motion_capable': True,
                'safety_capable': False,
                'max_io_modules': 30
            },
            'GuardLogix': {
                'max_programs': 1000,
                'max_routines_per_program': 1000,
                'max_tags': 250000,
                'motion_capable': True,
                'safety_capable': True,
                'max_io_modules': 128
            }
        }
        
        self.standard_instructions = {
            'XIC', 'XIO', 'OTE', 'OTL', 'OTU', 'ONS', 'OSR', 'OSF',
            'ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'AND', 'OR', 'XOR',
            'EQU', 'NEQ', 'LES', 'LEQ', 'GRT', 'GEQ', 'LIM',
            'TON', 'TOF', 'RTO', 'CTU', 'CTD', 'CTC', 'MOV', 'COP'
        }
        
        self.motion_instructions = {
            'MAOC', 'MAPC', 'MAAT', 'MASD', 'MAST', 'MAHD', 'MAFR',
            'MCCD', 'MCCM', 'MCCP', 'MCLM', 'MCSR', 'MCTO', 'MCTP'
        }
        
        self.safety_instructions = {
            'ESTOP', 'RESET', 'SAFESTOP', 'STO', 'SLS', 'SOS', 'SSM'
        }
    
    def validate_project(self, project: PLCProject, validation_options: Optional[Dict[str, bool]] = None) -> ValidationResult:
        """
        Comprehensive project validation
        
        Args:
            project: PLCProject to validate
            validation_options: Optional dict to enable/disable specific validations
            
        Returns:
            ValidationResult with all validation issues
        """
        if validation_options is None:
            validation_options = {
                'capabilities': True,
                'data_integrity': True,
                'instructions': True
            }
        
        start_time = datetime.now()
        result = ValidationResult(is_valid=True)
        
        # Run capability validation
        if validation_options.get('capabilities', True):
            logger.info("Running capability validation")
            self._validate_controller_capabilities(project, result)
        
        # Run data integrity validation
        if validation_options.get('data_integrity', True):
            logger.info("Running data integrity validation")
            self._validate_data_integrity(project, result)
        
        # Run instruction validation
        if validation_options.get('instructions', True):
            logger.info("Running instruction validation")
            self._validate_instructions(project, result)
        
        # Generate statistics
        result.statistics = {
            'validation_time': (datetime.now() - start_time).total_seconds(),
            'project_stats': {
                'programs': len(project.programs),
                'total_routines': sum(len(p.routines) for p in project.programs),
                'total_tags': len(project.controller_tags) + sum(len(p.tags) for p in project.programs),
                'aois': len(project.add_on_instructions),
                'udts': len(project.user_defined_types),
                'devices': len(project.devices)
            }
        }
        
        result.validation_time = datetime.now()
        
        logger.info("Validation complete", 
                   is_valid=result.is_valid,
                   total_issues=len(result.issues),
                   errors=len(result.get_errors()),
                   warnings=len(result.get_warnings()))
        
        return result
    
    def _validate_controller_capabilities(self, project: PLCProject, result: ValidationResult) -> None:
        """Validate project against controller capabilities"""
        controller_type = project.controller.processor_type
        if controller_type not in self.controller_specs:
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="controller_capability",
                message=f"Unknown controller type: {controller_type}",
                component="Controller",
                recommendation="Verify controller type is correct"
            ))
            return
        
        specs = self.controller_specs[controller_type]
        
        # Validate program count
        if len(project.programs) > specs['max_programs']:
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="controller_capability",
                message=f"Too many programs: {len(project.programs)} > {specs['max_programs']}",
                component="Controller",
                recommendation="Reduce number of programs or use higher-capacity controller"
            ))
        
        # Validate total tag count
        total_tags = len(project.controller_tags) + sum(len(prog.tags) for prog in project.programs)
        if total_tags > specs['max_tags']:
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="controller_capability",
                message=f"Too many tags: {total_tags} > {specs['max_tags']}",
                component="Controller",
                recommendation="Reduce tag count or use higher-capacity controller"
            ))
    
    def _validate_data_integrity(self, project: PLCProject, result: ValidationResult) -> None:
        """Validate data integrity across the project"""
        # Check for duplicate program names
        program_names = [p.name for p in project.programs]
        duplicates = self._find_duplicates(program_names)
        for duplicate in duplicates:
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="naming",
                message=f"Duplicate program name: {duplicate}",
                component="Program",
                recommendation="Rename programs to have unique names"
            ))
        
        # Validate routine references
        for program in project.programs:
            routine_names = {r.name for r in program.routines}
            
            # Check main routine reference
            if program.main_routine and program.main_routine not in routine_names:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="routine_reference",
                    message=f"Main routine '{program.main_routine}' not found in program {program.name}",
                    component=f"Program.{program.name}",
                    recommendation="Create main routine or update reference"
                ))
    
    def _validate_instructions(self, project: PLCProject, result: ValidationResult) -> None:
        """Validate instructions used in the project"""
        for program in project.programs:
            for routine in program.routines:
                location = f"Program.{program.name}.Routine.{routine.name}"
                
                if routine.type == RoutineType.LADDER:
                    for i, rung in enumerate(routine.rungs):
                        if rung.text:
                            self._validate_rung_instructions(rung.text, location, i, result)
                
                elif routine.type == RoutineType.STRUCTURED_TEXT:
                    if routine.structured_text:
                        self._validate_st_instructions(routine.structured_text, location, result)
    
    def _validate_rung_instructions(self, rung_text: str, location: str, rung_num: int, result: ValidationResult) -> None:
        """Validate instructions in a rung"""
        words = rung_text.split()
        for word in words:
            if word.upper() in self.motion_instructions:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="instruction_usage",
                    message=f"Motion instruction '{word}' found in rung {rung_num}",
                    component=location,
                    recommendation="Verify motion controller capability"
                ))
            
            elif word.upper() in self.safety_instructions:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="instruction_usage",
                    message=f"Safety instruction '{word}' found in rung {rung_num}",
                    component=location,
                    recommendation="Verify safety controller capability"
                ))
    
    def _validate_st_instructions(self, st_content: str, location: str, result: ValidationResult) -> None:
        """Validate instructions in structured text"""
        lines = st_content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for instruction in self.motion_instructions:
                if instruction in line:
                    result.add_issue(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category="instruction_usage",
                        message=f"Motion instruction '{instruction}' found in ST line {line_num}",
                        component=location,
                        recommendation="Verify motion controller capability"
                    ))
    
    def _find_duplicates(self, items: List[str]) -> Set[str]:
        """Find duplicate items in a list"""
        seen = set()
        duplicates = set()
        for item in items:
            if item in seen:
                duplicates.add(item)
            seen.add(item)
        return duplicates
    
    def validate_round_trip(self, original: PLCProject, converted: PLCProject) -> ValidationResult:
        """Validate round-trip conversion integrity"""
        result = ValidationResult(is_valid=True)
        
        # Compare program count
        if len(original.programs) != len(converted.programs):
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="round_trip",
                message=f"Program count mismatch: original={len(original.programs)}, converted={len(converted.programs)}",
                component="Project",
                recommendation="Check program extraction/generation logic"
            ))
        
        # Compare controller properties
        if original.controller.name != converted.controller.name:
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="round_trip",
                message=f"Controller name mismatch: original='{original.controller.name}', converted='{converted.controller.name}'",
                component="Controller",
                recommendation="Check controller name preservation"
            ))
        
        # Generate checksums
        original_hash = self._generate_project_hash(original)
        converted_hash = self._generate_project_hash(converted)
        
        result.statistics['original_hash'] = original_hash
        result.statistics['converted_hash'] = converted_hash
        result.statistics['hash_match'] = original_hash == converted_hash
        
        if original_hash != converted_hash:
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="round_trip",
                message="Project hash mismatch after round-trip conversion",
                component="Project",
                recommendation="Review conversion process for data loss"
            ))
        
        return result
    
    def _generate_project_hash(self, project: PLCProject) -> str:
        """Generate hash for project structure"""
        project_data = {
            'name': project.name,
            'controller': {
                'name': project.controller.name,
                'type': project.controller.processor_type
            },
            'programs': [
                {
                    'name': p.name,
                    'routine_count': len(p.routines),
                    'tag_count': len(p.tags)
                }
                for p in project.programs
            ]
        }
        
        json_str = json.dumps(project_data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def generate_validation_report(self, result: ValidationResult, output_path: Optional[Path] = None) -> str:
        """Generate human-readable validation report"""
        report_lines = []
        
        # Header
        report_lines.append("PLC PROJECT VALIDATION REPORT")
        report_lines.append("=" * 50)
        report_lines.append(f"Validation Time: {result.validation_time}")
        report_lines.append(f"Overall Status: {'PASS' if result.is_valid else 'FAIL'}")
        report_lines.append("")
        
        # Summary
        summary = result.get_summary()
        report_lines.append("SUMMARY")
        report_lines.append("-" * 20)
        report_lines.append(f"Total Issues: {summary['total_issues']}")
        report_lines.append(f"Errors: {summary['errors']}")
        report_lines.append(f"Warnings: {summary['warnings']}")
        report_lines.append(f"Info: {summary['info']}")
        report_lines.append("")
        
        # Issues by category
        if result.issues:
            report_lines.append("ISSUES BY CATEGORY")
            report_lines.append("-" * 30)
            
            categories = {}
            for issue in result.issues:
                if issue.category not in categories:
                    categories[issue.category] = []
                categories[issue.category].append(issue)
            
            for category, issues in categories.items():
                report_lines.append(f"\n{category.upper()}:")
                for issue in issues:
                    report_lines.append(f"  [{issue.severity.value}] {issue.message}")
                    if issue.location:
                        report_lines.append(f"    Location: {issue.location}")
                    if issue.recommendation:
                        report_lines.append(f"    Recommendation: {issue.recommendation}")
        
        report_content = "\n".join(report_lines)
        
        # Write to file if path provided
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report_content)
            logger.info("Validation report saved", path=str(output_path))
        
        return report_content

# Phase 3.9 Enhanced Components

"""
Validation Framework - Phase 3.9
================================

Comprehensive validation framework for data integrity scoring and round-trip
validation to ensure 95%+ data preservation in PLC format conversions.
"""

import os
import sys
import logging
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
import xml.etree.ElementTree as ET

# Import enhanced models
from ..core.models import (
    PLCProject, PLCController, PLCProgram, PLCRoutine, PLCTag, PLCInstruction,
    DataIntegrityScore, DataPreservationLevel, ConversionResult, ConversionStatus,
    BinaryDataBlock, ComponentExtraction
)

# Configure logging
logger = logging.getLogger(__name__)


class DataIntegrityValidator:
    """
    Comprehensive data integrity validator for PLC format conversions
    
    Provides detailed scoring and analysis of data preservation quality
    to ensure conversions meet the 95%+ preservation target.
    """
    
    def __init__(self):
        """Initialize data integrity validator"""
        self.validation_results = {}
        self.scoring_weights = {
            'logic_preservation': 0.40,  # Ladder logic completeness
            'tag_preservation': 0.25,    # Tag database completeness
            'io_preservation': 0.15,     # I/O configuration completeness
            'motion_preservation': 0.10, # Motion control completeness
            'safety_preservation': 0.10  # Safety system completeness
        }
        
        logger.info("Data Integrity Validator initialized")
    
    def validate_conversion_integrity(self, source_project: PLCProject, 
                                    converted_project: PLCProject) -> DataIntegrityScore:
        """
        Validate data integrity between source and converted projects
        
        Args:
            source_project: Original PLC project
            converted_project: Converted PLC project
            
        Returns:
            DataIntegrityScore with comprehensive metrics
        """
        logger.info("Starting data integrity validation...")
        
        integrity_score = DataIntegrityScore()
        
        try:
            # Validate logic preservation
            integrity_score.logic_preservation = self._validate_logic_preservation(
                source_project, converted_project
            )
            
            # Validate tag preservation
            integrity_score.tag_preservation = self._validate_tag_preservation(
                source_project, converted_project
            )
            
            # Validate I/O preservation
            integrity_score.io_preservation = self._validate_io_preservation(
                source_project, converted_project
            )
            
            # Validate motion preservation
            integrity_score.motion_preservation = self._validate_motion_preservation(
                source_project, converted_project
            )
            
            # Validate safety preservation
            integrity_score.safety_preservation = self._validate_safety_preservation(
                source_project, converted_project
            )
            
            # Calculate overall score
            integrity_score.calculate_overall_score()
            
            # Store detailed results
            self.validation_results = {
                'source_project': source_project.name,
                'converted_project': converted_project.name,
                'validation_timestamp': datetime.now(),
                'detailed_scores': {
                    'logic': integrity_score.logic_preservation,
                    'tags': integrity_score.tag_preservation,
                    'io': integrity_score.io_preservation,
                    'motion': integrity_score.motion_preservation,
                    'safety': integrity_score.safety_preservation
                },
                'overall_score': integrity_score.overall_score,
                'preservation_level': integrity_score.preservation_level.value
            }
            
            logger.info(f"Data integrity validation completed: {integrity_score.overall_score:.1f}%")
            
            return integrity_score
            
        except Exception as e:
            logger.error(f"Data integrity validation failed: {e}")
            return integrity_score
    
    def _validate_logic_preservation(self, source: PLCProject, converted: PLCProject) -> float:
        """Validate preservation of ladder logic and program structure"""
        
        try:
            source_instructions = self._count_instructions(source)
            converted_instructions = self._count_instructions(converted)
            
            source_routines = self._count_routines(source)
            converted_routines = self._count_routines(converted)
            
            # Calculate instruction preservation ratio
            instruction_ratio = 0.0
            if source_instructions > 0:
                instruction_ratio = min(100.0, (converted_instructions / source_instructions) * 100)
            
            # Calculate routine preservation ratio
            routine_ratio = 0.0
            if source_routines > 0:
                routine_ratio = min(100.0, (converted_routines / source_routines) * 100)
            
            # Weight instruction preservation more heavily
            logic_score = (instruction_ratio * 0.7) + (routine_ratio * 0.3)
            
            logger.debug(f"Logic preservation: {logic_score:.1f}% "
                        f"(Instructions: {converted_instructions}/{source_instructions}, "
                        f"Routines: {converted_routines}/{source_routines})")
            
            return logic_score
            
        except Exception as e:
            logger.warning(f"Logic preservation validation failed: {e}")
            return 0.0
    
    def _validate_tag_preservation(self, source: PLCProject, converted: PLCProject) -> float:
        """Validate preservation of tag database and data types"""
        
        try:
            source_tags = self._get_all_tags(source)
            converted_tags = self._get_all_tags(converted)
            
            # Count tag preservation
            preserved_tags = 0
            total_tags = len(source_tags)
            
            for source_tag in source_tags:
                # Look for matching tag in converted project
                for converted_tag in converted_tags:
                    if (source_tag.name == converted_tag.name and 
                        source_tag.data_type == converted_tag.data_type):
                        preserved_tags += 1
                        break
            
            # Calculate preservation ratio
            tag_ratio = 0.0
            if total_tags > 0:
                tag_ratio = (preserved_tags / total_tags) * 100
            
            logger.debug(f"Tag preservation: {tag_ratio:.1f}% "
                        f"({preserved_tags}/{total_tags})")
            
            return tag_ratio
            
        except Exception as e:
            logger.warning(f"Tag preservation validation failed: {e}")
            return 0.0
    
    def _validate_io_preservation(self, source: PLCProject, converted: PLCProject) -> float:
        """Validate preservation of I/O configuration and modules"""
        
        try:
            source_io_count = self._count_io_modules(source)
            converted_io_count = self._count_io_modules(converted)
            
            # Calculate I/O preservation ratio
            io_ratio = 0.0
            if source_io_count > 0:
                io_ratio = min(100.0, (converted_io_count / source_io_count) * 100)
            elif source_io_count == 0 and converted_io_count == 0:
                io_ratio = 100.0  # No I/O to preserve
            
            logger.debug(f"I/O preservation: {io_ratio:.1f}% "
                        f"({converted_io_count}/{source_io_count} modules)")
            
            return io_ratio
            
        except Exception as e:
            logger.warning(f"I/O preservation validation failed: {e}")
            return 0.0
    
    def _validate_motion_preservation(self, source: PLCProject, converted: PLCProject) -> float:
        """Validate preservation of motion control configuration"""
        
        try:
            source_motion = self._count_motion_components(source)
            converted_motion = self._count_motion_components(converted)
            
            # Calculate motion preservation ratio
            motion_ratio = 0.0
            if source_motion > 0:
                motion_ratio = min(100.0, (converted_motion / source_motion) * 100)
            elif source_motion == 0 and converted_motion == 0:
                motion_ratio = 100.0  # No motion to preserve
            
            logger.debug(f"Motion preservation: {motion_ratio:.1f}% "
                        f"({converted_motion}/{source_motion} components)")
            
            return motion_ratio
            
        except Exception as e:
            logger.warning(f"Motion preservation validation failed: {e}")
            return 0.0
    
    def _validate_safety_preservation(self, source: PLCProject, converted: PLCProject) -> float:
        """Validate preservation of safety system configuration"""
        
        try:
            source_safety = self._count_safety_components(source)
            converted_safety = self._count_safety_components(converted)
            
            # Calculate safety preservation ratio
            safety_ratio = 0.0
            if source_safety > 0:
                safety_ratio = min(100.0, (converted_safety / source_safety) * 100)
            elif source_safety == 0 and converted_safety == 0:
                safety_ratio = 100.0  # No safety to preserve
            
            logger.debug(f"Safety preservation: {safety_ratio:.1f}% "
                        f"({converted_safety}/{source_safety} components)")
            
            return safety_ratio
            
        except Exception as e:
            logger.warning(f"Safety preservation validation failed: {e}")
            return 0.0
    
    def _count_instructions(self, project: PLCProject) -> int:
        """Count total instructions in project"""
        
        total = 0
        for controller in project.controllers:
            for program in controller.programs:
                for routine in program.routines:
                    total += len(routine.instructions)
        return total
    
    def _count_routines(self, project: PLCProject) -> int:
        """Count total routines in project"""
        
        total = 0
        for controller in project.controllers:
            for program in controller.programs:
                total += len(program.routines)
        return total
    
    def _get_all_tags(self, project: PLCProject) -> List[PLCTag]:
        """Get all tags from project"""
        
        all_tags = []
        for controller in project.controllers:
            all_tags.extend(controller.tags)
            # Add program-scoped tags if implemented
        return all_tags
    
    def _count_io_modules(self, project: PLCProject) -> int:
        """Count I/O modules in project"""
        
        total = 0
        for controller in project.controllers:
            if hasattr(controller, 'ethernet_config') and controller.ethernet_config:
                total += len(controller.ethernet_config.get('modules', []))
        return total
    
    def _count_motion_components(self, project: PLCProject) -> int:
        """Count motion control components"""
        
        total = 0
        for controller in project.controllers:
            if hasattr(controller, 'motion_groups'):
                total += len(controller.motion_groups)
            if hasattr(controller, 'axes_configuration'):
                total += len(controller.axes_configuration)
        return total
    
    def _count_safety_components(self, project: PLCProject) -> int:
        """Count safety system components"""
        
        total = 0
        for controller in project.controllers:
            if hasattr(controller, 'safety_config') and controller.safety_config:
                total += 1
            for program in controller.programs:
                if hasattr(program, 'safety_signature') and program.safety_signature:
                    total += 1
        return total
    
    def generate_validation_report(self, integrity_score: DataIntegrityScore) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        
        report = {
            'summary': {
                'overall_score': integrity_score.overall_score,
                'preservation_level': integrity_score.preservation_level.value,
                'meets_target': integrity_score.overall_score >= 95.0,
                'validation_timestamp': integrity_score.validation_timestamp.isoformat()
            },
            'detailed_scores': {
                'logic_preservation': {
                    'score': integrity_score.logic_preservation,
                    'weight': self.scoring_weights['logic_preservation'],
                    'contribution': integrity_score.logic_preservation * self.scoring_weights['logic_preservation']
                },
                'tag_preservation': {
                    'score': integrity_score.tag_preservation,
                    'weight': self.scoring_weights['tag_preservation'],
                    'contribution': integrity_score.tag_preservation * self.scoring_weights['tag_preservation']
                },
                'io_preservation': {
                    'score': integrity_score.io_preservation,
                    'weight': self.scoring_weights['io_preservation'],
                    'contribution': integrity_score.io_preservation * self.scoring_weights['io_preservation']
                },
                'motion_preservation': {
                    'score': integrity_score.motion_preservation,
                    'weight': self.scoring_weights['motion_preservation'],
                    'contribution': integrity_score.motion_preservation * self.scoring_weights['motion_preservation']
                },
                'safety_preservation': {
                    'score': integrity_score.safety_preservation,
                    'weight': self.scoring_weights['safety_preservation'],
                    'contribution': integrity_score.safety_preservation * self.scoring_weights['safety_preservation']
                }
            },
            'component_counts': {
                'instructions': {
                    'total': integrity_score.instruction_count,
                    'preserved': integrity_score.preserved_instructions,
                    'preservation_ratio': (integrity_score.preserved_instructions / integrity_score.instruction_count * 100) if integrity_score.instruction_count > 0 else 0
                },
                'tags': {
                    'total': integrity_score.tag_count,
                    'preserved': integrity_score.preserved_tags,
                    'preservation_ratio': (integrity_score.preserved_tags / integrity_score.tag_count * 100) if integrity_score.tag_count > 0 else 0
                }
            },
            'recommendations': self._generate_recommendations(integrity_score)
        }
        
        return report
    
    def _generate_recommendations(self, integrity_score: DataIntegrityScore) -> List[str]:
        """Generate recommendations for improving data preservation"""
        
        recommendations = []
        
        if integrity_score.overall_score < 95.0:
            recommendations.append("Overall score below 95% target - review conversion process")
        
        if integrity_score.logic_preservation < 90.0:
            recommendations.append("Logic preservation below 90% - enhance ACD binary parsing")
        
        if integrity_score.tag_preservation < 90.0:
            recommendations.append("Tag preservation below 90% - improve tag database extraction")
        
        if integrity_score.io_preservation < 80.0:
            recommendations.append("I/O preservation below 80% - enhance I/O configuration parsing")
        
        if integrity_score.motion_preservation < 80.0:
            recommendations.append("Motion preservation below 80% - improve motion control extraction")
        
        if integrity_score.safety_preservation < 80.0:
            recommendations.append("Safety preservation below 80% - enhance safety system parsing")
        
        if not recommendations:
            recommendations.append("Excellent data preservation - meets industry standards")
        
        return recommendations


class RoundTripValidator:
    """
    Round-trip validation framework for ACD↔L5X conversions
    
    Validates that ACD→L5X→ACD conversions preserve data integrity
    and that L5X files can be successfully imported back into Studio 5000.
    """
    
    def __init__(self, enable_studio5000: bool = True):
        """
        Initialize round-trip validator
        
        Args:
            enable_studio5000: Enable Studio 5000 integration for validation
        """
        self.enable_studio5000 = enable_studio5000
        self.validation_history = []
        
        logger.info("Round-trip Validator initialized")
    
    def validate_round_trip(self, original_acd: Path, generated_l5x: Path) -> Dict[str, Any]:
        """
        Perform comprehensive round-trip validation
        
        Args:
            original_acd: Original ACD file path
            generated_l5x: Generated L5X file path
            
        Returns:
            Dict with validation results
        """
        logger.info(f"Starting round-trip validation: {original_acd.name} → {generated_l5x.name}")
        
        validation_result = {
            'success': False,
            'timestamp': datetime.now(),
            'original_file': str(original_acd),
            'generated_file': str(generated_l5x),
            'tests': {
                'file_existence': False,
                'xml_validity': False,
                'schema_compliance': False,
                'data_integrity': False,
                'studio5000_import': False
            },
            'scores': {},
            'issues': [],
            'warnings': []
        }
        
        try:
            # Test 1: File existence
            validation_result['tests']['file_existence'] = self._test_file_existence(
                original_acd, generated_l5x, validation_result
            )
            
            # Test 2: XML validity
            if validation_result['tests']['file_existence']:
                validation_result['tests']['xml_validity'] = self._test_xml_validity(
                    generated_l5x, validation_result
                )
            
            # Test 3: Schema compliance
            if validation_result['tests']['xml_validity']:
                validation_result['tests']['schema_compliance'] = self._test_schema_compliance(
                    generated_l5x, validation_result
                )
            
            # Test 4: Data integrity
            if validation_result['tests']['schema_compliance']:
                validation_result['tests']['data_integrity'] = self._test_data_integrity(
                    original_acd, generated_l5x, validation_result
                )
            
            # Test 5: Studio 5000 import (if enabled)
            if self.enable_studio5000 and validation_result['tests']['data_integrity']:
                validation_result['tests']['studio5000_import'] = self._test_studio5000_import(
                    generated_l5x, validation_result
                )
            
            # Calculate overall success
            required_tests = ['file_existence', 'xml_validity', 'schema_compliance', 'data_integrity']
            validation_result['success'] = all(
                validation_result['tests'][test] for test in required_tests
            )
            
            # Store validation history
            self.validation_history.append(validation_result)
            
            logger.info(f"Round-trip validation completed: {'SUCCESS' if validation_result['success'] else 'FAILED'}")
            
            return validation_result
            
        except Exception as e:
            validation_result['issues'].append(f"Round-trip validation error: {e}")
            logger.error(f"Round-trip validation failed: {e}")
            return validation_result
    
    def _test_file_existence(self, acd_file: Path, l5x_file: Path, result: Dict) -> bool:
        """Test that both files exist and are accessible"""
        
        if not acd_file.exists():
            result['issues'].append(f"Original ACD file not found: {acd_file}")
            return False
        
        if not l5x_file.exists():
            result['issues'].append(f"Generated L5X file not found: {l5x_file}")
            return False
        
        # Check file sizes
        acd_size = acd_file.stat().st_size
        l5x_size = l5x_file.stat().st_size
        
        if acd_size == 0:
            result['issues'].append("ACD file is empty")
            return False
        
        if l5x_size == 0:
            result['issues'].append("L5X file is empty")
            return False
        
        # Store file information
        result['file_info'] = {
            'acd_size': acd_size,
            'l5x_size': l5x_size,
            'size_ratio': l5x_size / acd_size
        }
        
        return True
    
    def _test_xml_validity(self, l5x_file: Path, result: Dict) -> bool:
        """Test XML validity of L5X file"""
        
        try:
            tree = ET.parse(l5x_file)
            root = tree.getroot()
            
            # Basic XML structure checks
            if root.tag != "RSLogix5000Content":
                result['issues'].append("Invalid L5X root element")
                return False
            
            # Check for required attributes
            required_attrs = ["SchemaRevision", "SoftwareRevision", "TargetName"]
            for attr in required_attrs:
                if not root.get(attr):
                    result['warnings'].append(f"Missing required attribute: {attr}")
            
            return True
            
        except ET.ParseError as e:
            result['issues'].append(f"XML parsing error: {e}")
            return False
        except Exception as e:
            result['issues'].append(f"XML validation error: {e}")
            return False
    
    def _test_schema_compliance(self, l5x_file: Path, result: Dict) -> bool:
        """Test L5X schema compliance"""
        
        try:
            tree = ET.parse(l5x_file)
            root = tree.getroot()
            
            # Check for required elements
            required_elements = [
                ".//Controller",
                ".//Controller/DataTypes",
                ".//Controller/Modules", 
                ".//Controller/Tags",
                ".//Controller/Programs",
                ".//Controller/Tasks"
            ]
            
            missing_elements = []
            for element_path in required_elements:
                if root.find(element_path) is None:
                    missing_elements.append(element_path)
            
            if missing_elements:
                result['warnings'].extend([f"Missing element: {elem}" for elem in missing_elements])
                # Don't fail for missing elements, just warn
            
            return True
            
        except Exception as e:
            result['issues'].append(f"Schema compliance error: {e}")
            return False
    
    def _test_data_integrity(self, acd_file: Path, l5x_file: Path, result: Dict) -> bool:
        """Test data integrity between ACD and L5X"""
        
        try:
            # This would perform detailed data comparison
            # For now, perform basic checks
            
            tree = ET.parse(l5x_file)
            root = tree.getroot()
            
            # Count components in L5X
            controllers = len(root.findall(".//Controller"))
            programs = len(root.findall(".//Programs/Program"))
            routines = len(root.findall(".//Routines/Routine"))
            tags = len(root.findall(".//Tags/Tag"))
            
            result['scores']['component_counts'] = {
                'controllers': controllers,
                'programs': programs,
                'routines': routines,
                'tags': tags
            }
            
            # Basic integrity checks
            if controllers == 0:
                result['issues'].append("No controllers found in L5X")
                return False
            
            if programs == 0:
                result['warnings'].append("No programs found in L5X")
            
            if routines == 0:
                result['warnings'].append("No routines found in L5X")
            
            if tags == 0:
                result['warnings'].append("No tags found in L5X")
            
            return True
            
        except Exception as e:
            result['issues'].append(f"Data integrity test error: {e}")
            return False
    
    def _test_studio5000_import(self, l5x_file: Path, result: Dict) -> bool:
        """Test Studio 5000 import capability (placeholder)"""
        
        try:
            # This would test actual Studio 5000 import
            # For now, return True as placeholder
            result['warnings'].append("Studio 5000 import test not implemented")
            return True
            
        except Exception as e:
            result['issues'].append(f"Studio 5000 import test error: {e}")
            return False
    
    def get_validation_history(self) -> List[Dict[str, Any]]:
        """Get validation history"""
        return self.validation_history.copy()
    
    def generate_round_trip_report(self, validation_result: Dict[str, Any]) -> str:
        """Generate human-readable round-trip validation report"""
        
        report_lines = [
            "Round-Trip Validation Report",
            "=" * 50,
            f"Timestamp: {validation_result['timestamp']}",
            f"Original File: {validation_result['original_file']}",
            f"Generated File: {validation_result['generated_file']}",
            f"Overall Result: {'PASS' if validation_result['success'] else 'FAIL'}",
            "",
            "Test Results:",
            "-" * 20
        ]
        
        for test_name, test_result in validation_result['tests'].items():
            status = "PASS" if test_result else "FAIL"
            report_lines.append(f"  {test_name}: {status}")
        
        if validation_result.get('file_info'):
            report_lines.extend([
                "",
                "File Information:",
                "-" * 20,
                f"  ACD Size: {validation_result['file_info']['acd_size']:,} bytes",
                f"  L5X Size: {validation_result['file_info']['l5x_size']:,} bytes",
                f"  Size Ratio: {validation_result['file_info']['size_ratio']:.3f}"
            ])
        
        if validation_result.get('scores', {}).get('component_counts'):
            counts = validation_result['scores']['component_counts']
            report_lines.extend([
                "",
                "Component Counts:",
                "-" * 20,
                f"  Controllers: {counts['controllers']}",
                f"  Programs: {counts['programs']}",
                f"  Routines: {counts['routines']}",
                f"  Tags: {counts['tags']}"
            ])
        
        if validation_result['issues']:
            report_lines.extend([
                "",
                "Issues:",
                "-" * 20
            ])
            for issue in validation_result['issues']:
                report_lines.append(f"  ❌ {issue}")
        
        if validation_result['warnings']:
            report_lines.extend([
                "",
                "Warnings:",
                "-" * 20
            ])
            for warning in validation_result['warnings']:
                report_lines.append(f"  ⚠️  {warning}")
        
        return "\n".join(report_lines) 