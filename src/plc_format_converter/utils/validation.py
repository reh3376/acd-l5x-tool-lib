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