"""
CLI Interface for PLC Format Converter

This module provides command-line interface for PLC file format conversion
with comprehensive validation, batch processing, and round-trip testing capabilities.
"""

import sys
import click
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import time
from datetime import datetime
import tempfile
import os

import structlog

# Import core converter and handlers
from .core.converter import PLCConverter, EnhancedPLCConverter
from .formats.acd_handler import ACDHandler
from .formats.l5x_handler import L5XHandler
from .utils.validation import PLCValidator, ValidationResult

# Configure structured logging for CLI
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@click.group()
@click.version_option(version="2.1.1", prog_name="plc-format-converter")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-error output')
def main(verbose: bool, quiet: bool):
    """
    PLC Format Converter - Convert between ACD and L5X formats
    
    This tool provides comprehensive PLC file format conversion with validation,
    round-trip testing, and batch processing capabilities.
    """
    # Configure logging level based on flags
    if quiet:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
    elif verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)


@main.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.argument('output_file', type=click.Path(path_type=Path))
@click.option('--validate', is_flag=True, help='Validate conversion result')
@click.option('--studio5000', is_flag=True, help='Use Studio 5000 for enhanced conversion')
@click.option('--preserve-metadata', is_flag=True, default=True, help='Preserve original metadata')
def acd2l5x(input_file: Path, output_file: Path, validate: bool, 
           studio5000: bool, preserve_metadata: bool):
    """
    Convert ACD file to L5X format
    
    INPUT_FILE: Path to the ACD file to convert
    OUTPUT_FILE: Path for the output L5X file
    """
    click.echo(f"🔄 Converting ACD to L5X: {input_file} → {output_file}")
    
    try:
        start_time = time.time()
        
        # Initialize handlers
        acd_handler = ACDHandler()
        l5x_handler = L5XHandler()
        
        # Check capabilities
        acd_caps = acd_handler.get_capabilities()
        l5x_caps = l5x_handler.get_capabilities()
        
        if not acd_caps['read_support']:
            click.echo("❌ ACD reading not supported", err=True)
            sys.exit(1)
        
        if not l5x_caps['write_support']:
            click.echo("❌ L5X writing not supported", err=True)
            sys.exit(1)
        
        # Load ACD file
        click.echo("📖 Loading ACD file...")
        project = acd_handler.load(input_file)
        
        # Enhance with Studio 5000 if requested
        if studio5000 and acd_caps['dependencies']['studio_5000_available']:
            click.echo("🔧 Using Studio 5000 enhanced parsing...")
        elif studio5000:
            click.echo("⚠️  Studio 5000 not available, using standard parsing")
        
        # Save as L5X
        click.echo("💾 Saving L5X file...")
        l5x_handler.save(project, output_file)
        
        # Validation if requested
        if validate:
            click.echo("✅ Validating conversion...")
            validator = PLCValidator()
            validation_result = validator.validate_project(project)
            
            if validation_result.is_valid:
                click.echo("✅ Validation passed")
            else:
                click.echo("⚠️  Validation warnings:")
                for issue in validation_result.get_errors():
                    click.echo(f"   • {issue.message}")
        
        # Report completion
        elapsed = time.time() - start_time
        click.echo(f"✅ Conversion completed in {elapsed:.2f}s")
        
        # Display project statistics
        _display_project_stats(project)
        
    except Exception as e:
        click.echo(f"❌ Conversion failed: {e}", err=True)
        logger.error("ACD to L5X conversion failed", error=str(e))
        sys.exit(1)


@main.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.argument('output_file', type=click.Path(path_type=Path))
@click.option('--validate', is_flag=True, help='Validate conversion result')
@click.option('--studio5000', is_flag=True, help='Use Studio 5000 for ACD generation')
@click.option('--preserve-metadata', is_flag=True, default=True, help='Preserve original metadata')
def l5x2acd(input_file: Path, output_file: Path, validate: bool,
           studio5000: bool, preserve_metadata: bool):
    """
    Convert L5X file to ACD format
    
    INPUT_FILE: Path to the L5X file to convert
    OUTPUT_FILE: Path for the output ACD file
    """
    click.echo(f"🔄 Converting L5X to ACD: {input_file} → {output_file}")
    
    try:
        start_time = time.time()
        
        # Initialize handlers
        l5x_handler = L5XHandler()
        acd_handler = ACDHandler()
        
        # Check capabilities
        l5x_caps = l5x_handler.get_capabilities()
        acd_caps = acd_handler.get_capabilities()
        
        if not l5x_caps['read_support']:
            click.echo("❌ L5X reading not supported", err=True)
            sys.exit(1)
        
        if not acd_caps['write_support']:
            if studio5000:
                click.echo("⚠️  ACD writing requires Studio 5000")
            else:
                click.echo("❌ ACD writing not supported without Studio 5000", err=True)
                click.echo("💡 Use --studio5000 flag to enable ACD generation")
                sys.exit(1)
        
        # Load L5X file
        click.echo("📖 Loading L5X file...")
        project = l5x_handler.load(input_file)
        
        # Save as ACD using Studio 5000
        click.echo("💾 Saving ACD file using Studio 5000...")
        acd_handler.save(project, output_file)
        
        # Validation if requested
        if validate:
            click.echo("✅ Validating conversion...")
            validator = PLCValidator()
            validation_result = validator.validate_project(project)
            
            if validation_result.is_valid:
                click.echo("✅ Validation passed")
            else:
                click.echo("⚠️  Validation warnings:")
                for issue in validation_result.get_errors():
                    click.echo(f"   • {issue.message}")
        
        # Report completion
        elapsed = time.time() - start_time
        click.echo(f"✅ Conversion completed in {elapsed:.2f}s")
        
        # Display project statistics
        _display_project_stats(project)
        
    except Exception as e:
        click.echo(f"❌ Conversion failed: {e}", err=True)
        logger.error("L5X to ACD conversion failed", error=str(e))
        sys.exit(1)


@main.command()
@click.option('--input', '-i', 'input_file', type=click.Path(exists=True, path_type=Path), 
              help='Input file path')
@click.option('--output', '-o', 'output_file', type=click.Path(path_type=Path),
              help='Output file path')
@click.option('--format', 'output_format', type=click.Choice(['acd', 'l5x'], case_sensitive=False),
              help='Output format (auto-detected if not specified)')
@click.option('--validate', is_flag=True, help='Validate conversion result')
@click.option('--round-trip', is_flag=True, help='Perform round-trip validation')
@click.option('--studio5000', is_flag=True, help='Use Studio 5000 integration')
@click.option('--batch', is_flag=True, help='Enable batch processing mode')
@click.option('--input-dir', type=click.Path(exists=True, path_type=Path),
              help='Input directory for batch processing')
@click.option('--output-dir', type=click.Path(path_type=Path),
              help='Output directory for batch processing')
@click.option('--report', type=click.Path(path_type=Path),
              help='Generate detailed report file')
def convert(input_file: Optional[Path], output_file: Optional[Path], output_format: Optional[str],
           validate: bool, round_trip: bool, studio5000: bool, batch: bool,
           input_dir: Optional[Path], output_dir: Optional[Path], report: Optional[Path]):
    """
    Universal PLC format converter with advanced features
    
    Supports single file conversion, batch processing, and comprehensive validation.
    """
    if batch:
        _handle_batch_conversion(input_dir, output_dir, output_format, validate, 
                               round_trip, studio5000, report)
    else:
        _handle_single_conversion(input_file, output_file, output_format, validate,
                                round_trip, studio5000, report)


def _handle_single_conversion(input_file: Optional[Path], output_file: Optional[Path], 
                            output_format: Optional[str], validate: bool, round_trip: bool,
                            studio5000: bool, report: Optional[Path]):
    """Handle single file conversion"""
    if not input_file:
        click.echo("❌ Input file required for single conversion", err=True)
        sys.exit(1)
    
    if not output_file:
        # Auto-generate output filename
        if not output_format:
            # Determine output format from input
            if input_file.suffix.lower() == '.acd':
                output_format = 'l5x'
            elif input_file.suffix.lower() == '.l5x':
                output_format = 'acd'
            else:
                click.echo("❌ Cannot determine output format", err=True)
                sys.exit(1)
        
        output_file = input_file.with_suffix(f'.{output_format.upper()}')
    
    click.echo(f"🔄 Converting {input_file} → {output_file}")
    
    try:
        start_time = time.time()
        conversion_result = {}
        
        # Initialize converter
        converter = PLCConverter()
        
        # Perform conversion
        if input_file.suffix.lower() == '.acd' and output_file.suffix.lower() == '.l5x':
            project = converter.convert_acd_to_l5x(input_file, output_file)
            conversion_result['direction'] = 'ACD → L5X'
        elif input_file.suffix.lower() == '.l5x' and output_file.suffix.lower() == '.acd':
            project = converter.convert_l5x_to_acd(input_file, output_file)
            conversion_result['direction'] = 'L5X → ACD'
        else:
            click.echo("❌ Unsupported conversion direction", err=True)
            sys.exit(1)
        
        # Validation
        if validate:
            click.echo("✅ Validating conversion...")
            validator = PLCValidator()
            validation_result = validator.validate_project(project)
            conversion_result['validation'] = validation_result.get_summary()
            
            if validation_result.is_valid:
                click.echo("✅ Validation passed")
            else:
                click.echo("⚠️  Validation issues found")
        
        # Round-trip validation
        if round_trip:
            click.echo("🔄 Performing round-trip validation...")
            round_trip_result = _perform_round_trip_validation(input_file, output_file)
            conversion_result['round_trip'] = round_trip_result
            
            if round_trip_result['validation_passed']:
                click.echo(f"✅ Round-trip validation passed (score: {round_trip_result.get('round_trip_score', 0):.1f}%)")
            else:
                click.echo(f"⚠️  Round-trip validation issues (score: {round_trip_result.get('round_trip_score', 0):.1f}%)")
        
        # Report completion
        elapsed = time.time() - start_time
        conversion_result['elapsed_time'] = elapsed
        conversion_result['timestamp'] = datetime.now().isoformat()
        
        click.echo(f"✅ Conversion completed in {elapsed:.2f}s")
        
        # Display project statistics
        _display_project_stats(project)
        
        # Generate report if requested
        if report:
            _generate_conversion_report(conversion_result, report)
            click.echo(f"📊 Report saved to {report}")
        
    except Exception as e:
        click.echo(f"❌ Conversion failed: {e}", err=True)
        logger.error("Single file conversion failed", error=str(e))
        sys.exit(1)


def _handle_batch_conversion(input_dir: Optional[Path], output_dir: Optional[Path],
                           output_format: Optional[str], validate: bool, round_trip: bool,
                           studio5000: bool, report: Optional[Path]):
    """Handle batch conversion of multiple files"""
    if not input_dir:
        click.echo("❌ Input directory required for batch conversion", err=True)
        sys.exit(1)
    
    if not output_dir:
        output_dir = input_dir / 'converted'
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"🔄 Batch converting files from {input_dir} to {output_dir}")
    
    # Find input files
    input_files = []
    for pattern in ['*.acd', '*.ACD', '*.l5x', '*.L5X']:
        input_files.extend(input_dir.glob(pattern))
    
    if not input_files:
        click.echo("❌ No ACD or L5X files found in input directory", err=True)
        sys.exit(1)
    
    click.echo(f"📁 Found {len(input_files)} files to convert")
    
    # Process files
    results = []
    successful = 0
    failed = 0
    
    for input_file in input_files:
        try:
            click.echo(f"\n🔄 Processing {input_file.name}...")
            
            # Determine output format and filename
            if not output_format:
                if input_file.suffix.lower() == '.acd':
                    target_format = 'l5x'
                elif input_file.suffix.lower() == '.l5x':
                    target_format = 'acd'
                else:
                    continue
            else:
                target_format = output_format.lower()
            
            output_file = output_dir / f"{input_file.stem}.{target_format.upper()}"
            
            # Perform conversion
            start_time = time.time()
            converter = PLCConverter()
            
            if input_file.suffix.lower() == '.acd' and target_format == 'l5x':
                project = converter.convert_acd_to_l5x(input_file, output_file)
            elif input_file.suffix.lower() == '.l5x' and target_format == 'acd':
                project = converter.convert_l5x_to_acd(input_file, output_file)
            else:
                click.echo(f"⚠️  Skipping {input_file.name} - unsupported conversion")
                continue
            
            elapsed = time.time() - start_time
            
            # Validation if requested
            validation_result = None
            if validate:
                validator = PLCValidator()
                validation_result = validator.validate_project(project)
            
            # Round-trip validation if requested
            round_trip_result = None
            if round_trip:
                round_trip_result = _perform_round_trip_validation(input_file, output_file)
            
            # Record result
            file_result = {
                'input_file': str(input_file),
                'output_file': str(output_file),
                'success': True,
                'elapsed_time': elapsed,
                'validation': validation_result.get_summary() if validation_result else None,
                'round_trip': round_trip_result
            }
            results.append(file_result)
            successful += 1
            
            click.echo(f"✅ {input_file.name} converted successfully ({elapsed:.2f}s)")
            
        except Exception as e:
            file_result = {
                'input_file': str(input_file),
                'output_file': None,
                'success': False,
                'error': str(e),
                'elapsed_time': None
            }
            results.append(file_result)
            failed += 1
            
            click.echo(f"❌ {input_file.name} conversion failed: {e}")
            logger.error("Batch file conversion failed", file=str(input_file), error=str(e))
    
    # Summary
    click.echo(f"\n📊 Batch conversion completed:")
    click.echo(f"   ✅ Successful: {successful}")
    click.echo(f"   ❌ Failed: {failed}")
    click.echo(f"   📁 Total: {len(input_files)}")
    
    # Generate batch report
    if report:
        batch_report = {
            'summary': {
                'total_files': len(input_files),
                'successful': successful,
                'failed': failed,
                'success_rate': (successful / len(input_files)) * 100 if input_files else 0
            },
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        _generate_conversion_report(batch_report, report)
        click.echo(f"📊 Batch report saved to {report}")


@main.command()
@click.argument('file_path', type=click.Path(exists=True, path_type=Path))
@click.option('--round-trip', is_flag=True, help='Perform round-trip validation')
@click.option('--detailed', is_flag=True, help='Show detailed validation results')
@click.option('--report', type=click.Path(path_type=Path), help='Save validation report')
def validate(file_path: Path, round_trip: bool, detailed: bool, report: Optional[Path]):
    """
    Validate PLC file format and structure
    
    FILE_PATH: Path to the PLC file to validate
    """
    click.echo(f"✅ Validating {file_path}")
    
    try:
        start_time = time.time()
        
        # Determine file type and load
        if file_path.suffix.lower() == '.acd':
            handler = ACDHandler()
        elif file_path.suffix.lower() == '.l5x':
            handler = L5XHandler()
        else:
            click.echo("❌ Unsupported file format", err=True)
            sys.exit(1)
        
        # Load project
        project = handler.load(file_path)
        
        # Validate project
        validator = PLCValidator()
        validation_result = validator.validate_project(project)
        
        # Display results
        if validation_result.is_valid:
            click.echo("✅ Validation passed")
        else:
            click.echo("⚠️  Validation issues found")
        
        summary = validation_result.get_summary()
        click.echo(f"📊 Issues: {summary['errors']} errors, {summary['warnings']} warnings")
        
        if detailed:
            _display_detailed_validation(validation_result)
        
        # Round-trip validation
        round_trip_result = None
        if round_trip:
            click.echo("\n🔄 Performing round-trip validation...")
            round_trip_result = _perform_round_trip_validation(file_path)
            
            if round_trip_result['validation_passed']:
                click.echo(f"✅ Round-trip validation passed (score: {round_trip_result.get('round_trip_score', 0):.1f}%)")
            else:
                click.echo(f"⚠️  Round-trip validation issues (score: {round_trip_result.get('round_trip_score', 0):.1f}%)")
        
        elapsed = time.time() - start_time
        click.echo(f"⏱️  Validation completed in {elapsed:.2f}s")
        
        # Generate report if requested
        if report:
            validation_report = {
                'file_path': str(file_path),
                'validation_result': validation_result.get_summary(),
                'round_trip_result': round_trip_result,
                'elapsed_time': elapsed,
                'timestamp': datetime.now().isoformat()
            }
            _generate_conversion_report(validation_report, report)
            click.echo(f"📊 Validation report saved to {report}")
        
    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)
        logger.error("File validation failed", error=str(e))
        sys.exit(1)


@main.command()
def capabilities():
    """
    Display converter capabilities and dependencies
    """
    click.echo("🔧 PLC Format Converter Capabilities\n")
    
    # ACD Handler capabilities
    acd_handler = ACDHandler()
    acd_caps = acd_handler.get_capabilities()
    
    click.echo("📁 ACD Handler:")
    click.echo(f"   Version: {acd_caps['version']}")
    click.echo(f"   Read Support: {'✅' if acd_caps['read_support'] else '❌'}")
    click.echo(f"   Write Support: {'✅' if acd_caps['write_support'] else '❌'}")
    click.echo(f"   Studio 5000 Available: {'✅' if acd_caps['dependencies']['studio_5000_available'] else '❌'}")
    click.echo(f"   ACD Tools Available: {'✅' if acd_caps['dependencies']['acd_tools'] else '❌'}")
    
    # L5X Handler capabilities
    l5x_handler = L5XHandler()
    l5x_caps = l5x_handler.get_capabilities()
    
    click.echo("\n📄 L5X Handler:")
    click.echo(f"   Version: {l5x_caps['version']}")
    click.echo(f"   Read Support: {'✅' if l5x_caps['read_support'] else '❌'}")
    click.echo(f"   Write Support: {'✅' if l5x_caps['write_support'] else '❌'}")
    click.echo(f"   L5X Library Available: {'✅' if l5x_caps['dependencies']['l5x_library'] else '❌'}")
    
    # Features
    click.echo("\n🚀 Features:")
    for feature, supported in acd_caps['features'].items():
        if feature in l5x_caps['features']:
            both_support = supported and l5x_caps['features'][feature]
            click.echo(f"   {feature}: {'✅' if both_support else '⚠️' if supported or l5x_caps['features'][feature] else '❌'}")


# Helper functions
def _display_project_stats(project):
    """Display project statistics"""
    click.echo("\n📊 Project Statistics:")
    click.echo(f"   Controller: {project.controller.name} ({project.controller.processor_type})")
    click.echo(f"   Programs: {len(project.programs)}")
    click.echo(f"   Controller Tags: {len(project.controller_tags)}")
    click.echo(f"   Add-On Instructions: {len(project.add_on_instructions)}")
    click.echo(f"   User Defined Types: {len(project.user_defined_types)}")
    click.echo(f"   Devices: {len(project.devices)}")


def _display_detailed_validation(validation_result: ValidationResult):
    """Display detailed validation results"""
    if validation_result.get_errors():
        click.echo("\n❌ Errors:")
        for error in validation_result.get_errors():
            click.echo(f"   • {error.message}")
            if error.recommendation:
                click.echo(f"     💡 {error.recommendation}")
    
    if validation_result.get_warnings():
        click.echo("\n⚠️  Warnings:")
        for warning in validation_result.get_warnings():
            click.echo(f"   • {warning.message}")
            if warning.recommendation:
                click.echo(f"     💡 {warning.recommendation}")


def _perform_round_trip_validation(original_file: Path, converted_file: Optional[Path] = None) -> Dict[str, Any]:
    """Perform round-trip validation"""
    try:
        if not converted_file:
            # Create temporary converted file
            with tempfile.NamedTemporaryFile(suffix='.L5X' if original_file.suffix.lower() == '.acd' else '.ACD', 
                                           delete=False) as temp_file:
                converted_file = Path(temp_file.name)
        
        # Determine handlers
        if original_file.suffix.lower() == '.acd':
            original_handler = ACDHandler()
            converted_handler = L5XHandler()
            
            # Convert ACD to L5X
            project = original_handler.load(original_file)
            converted_handler.save(project, converted_file)
            
            # Perform round-trip validation
            return original_handler.validate_round_trip(original_file, converted_file)
        
        elif original_file.suffix.lower() == '.l5x':
            original_handler = L5XHandler()
            converted_handler = ACDHandler()
            
            # Convert L5X to ACD (requires Studio 5000)
            project = original_handler.load(original_file)
            converted_handler.save(project, converted_file)
            
            # Perform round-trip validation
            return original_handler.validate_round_trip(original_file, converted_file)
        
        else:
            return {
                'validation_passed': False,
                'error': 'Unsupported file format for round-trip validation'
            }
    
    except Exception as e:
        return {
            'validation_passed': False,
            'error': str(e)
        }
    
    finally:
        # Clean up temporary file if created
        if converted_file and converted_file.exists() and not converted_file.parent.samefile(original_file.parent):
            try:
                os.unlink(converted_file)
            except:
                pass


def _generate_conversion_report(data: Dict[str, Any], report_path: Path):
    """Generate detailed conversion report"""
    try:
        with open(report_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.warning("Failed to generate report", error=str(e))


# Individual command entry points for standalone executables
@click.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.argument('output_file', type=click.Path(path_type=Path))
@click.option('--validate', '-v', is_flag=True, help='Run validation before conversion')
@click.option('--force', '-f', is_flag=True, help='Force conversion even if validation fails')
def acd2l5x(input_file: Path, output_file: Path, validate: bool, force: bool):
    """Convert ACD files to L5X format.
    
    INPUT_FILE: Source ACD file
    OUTPUT_FILE: Target L5X file
    """
    try:
        # Validate input format
        if input_file.suffix.lower() != '.acd':
            click.echo(f"❌ Expected ACD file, got: {input_file.suffix}")
            sys.exit(1)
        
        # Set output format if not specified
        if output_file.suffix.lower() != '.l5x':
            output_file = output_file.with_suffix('.l5x')
        
        click.echo(f"Converting ACD → L5X")
        click.echo(f"Input: {input_file}")
        click.echo(f"Output: {output_file}")
        
        # Load ACD project
        handler = ACDHandler()
        click.echo("Loading ACD project...")
        project = handler.load(input_file)
        click.echo(f"✅ Loaded: {project.name}")
        
        # Validate if requested
        if validate:
            click.echo("Running validation...")
            validator = PLCValidator()
            result = validator.validate_project(project)
            
            if not result.is_valid:
                click.echo("❌ Validation failed")
                for error in result.get_errors()[:5]:  # Show first 5 errors
                    click.echo(f"  • {error.message}")
                if not force:
                    click.echo("Use --force to continue anyway")
                    sys.exit(1)
            else:
                click.echo("✅ Validation passed")
        
        # Save as L5X
        click.echo("Saving L5X file...")
        output_handler = L5XHandler()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_handler.save(project, output_file)
        click.echo(f"✅ Conversion completed: {output_file}")
        
    except Exception as e:
        click.echo(f"❌ Conversion failed: {e}")
        sys.exit(1)


@click.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.argument('output_file', type=click.Path(path_type=Path))
@click.option('--validate', '-v', is_flag=True, help='Run validation before conversion')
@click.option('--force', '-f', is_flag=True, help='Force conversion even if validation fails')
def l5x2acd(input_file: Path, output_file: Path, validate: bool, force: bool):
    """Convert L5X files to ACD format.
    
    INPUT_FILE: Source L5X file
    OUTPUT_FILE: Target ACD file
    """
    try:
        # Validate input format
        if input_file.suffix.lower() != '.l5x':
            click.echo(f"❌ Expected L5X file, got: {input_file.suffix}")
            sys.exit(1)
        
        click.echo(f"Converting L5X → ACD")
        click.echo(f"Input: {input_file}")
        click.echo(f"Output: {output_file}")
        
        # Load L5X project
        handler = L5XHandler()
        click.echo("Loading L5X project...")
        project = handler.load(input_file)
        click.echo(f"✅ Loaded: {project.name}")
        
        # Validate if requested
        if validate:
            click.echo("Running validation...")
            validator = PLCValidator()
            result = validator.validate_project(project)
            
            if not result.is_valid:
                click.echo("❌ Validation failed")
                for error in result.get_errors()[:5]:  # Show first 5 errors
                    click.echo(f"  • {error.message}")
                if not force:
                    click.echo("Use --force to continue anyway")
                    sys.exit(1)
            else:
                click.echo("✅ Validation passed")
        
        # ACD generation note
        click.echo("❌ Direct ACD generation not supported.")
        click.echo("💡 Use Studio 5000 integration or import the L5X file manually.")
        sys.exit(1)
        
    except Exception as e:
        click.echo(f"❌ Conversion failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 