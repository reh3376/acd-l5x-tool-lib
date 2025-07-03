"""
Command Line Interface for PLC Format Converter

Provides command-line tools for converting between ACD and L5X formats
with comprehensive validation and reporting capabilities.
"""

import sys
import click
from pathlib import Path
from typing import Optional

from . import __version__, get_library_info
from .formats import ACDHandler, L5XHandler
from .utils import PLCValidator
from .core.models import ConversionError, FormatError, ValidationError


@click.group()
@click.version_option(version=__version__, prog_name="plc-convert")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def cli(verbose: bool):
    """PLC Format Converter - Convert between ACD and L5X formats with validation."""
    if verbose:
        click.echo(f"PLC Format Converter v{__version__}")


@cli.command()
def info():
    """Display library information and capabilities."""
    info = get_library_info()
    
    click.echo("PLC Format Converter Library Information")
    click.echo("=" * 45)
    click.echo(f"Version: {info['version']}")
    click.echo(f"Author: {info['author']}")
    click.echo(f"License: {info['license']}")
    click.echo(f"Description: {info['description']}")
    click.echo()
    click.echo("Supported Formats:")
    for fmt in info['supported_formats']:
        click.echo(f"  • {fmt}")
    click.echo()
    click.echo("Features:")
    for feature in info['features']:
        click.echo(f"  • {feature}")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.argument('output_file', type=click.Path(path_type=Path))
@click.option('--validate', '-v', is_flag=True, help='Run validation before conversion')
@click.option('--report', '-r', type=click.Path(path_type=Path), help='Save validation report to file')
@click.option('--force', '-f', is_flag=True, help='Force conversion even if validation fails')
def convert(
    input_file: Path, 
    output_file: Path, 
    validate: bool, 
    report: Optional[Path],
    force: bool
):
    """Convert between ACD and L5X formats.
    
    INPUT_FILE: Source file (ACD or L5X)
    OUTPUT_FILE: Target file (L5X or ACD)
    """
    try:
        # Determine input and output formats
        input_format = input_file.suffix.lower()
        output_format = output_file.suffix.lower()
        
        click.echo(f"Converting {input_format.upper()} → {output_format.upper()}")
        click.echo(f"Input: {input_file}")
        click.echo(f"Output: {output_file}")
        
        # Load the project
        if input_format == '.acd':
            handler = ACDHandler()
        elif input_format == '.l5x':
            handler = L5XHandler()
        else:
            raise ValueError(f"Unsupported input format: {input_format}")
        
        click.echo("Loading project...")
        project = handler.load(input_file)
        click.echo(f"✅ Loaded: {project.name}")
        click.echo(f"   Controller: {project.controller.name} ({project.controller.processor_type})")
        click.echo(f"   Programs: {len(project.programs)}")
        
        # Run validation if requested
        validation_passed = True
        if validate:
            click.echo("\nRunning validation...")
            validator = PLCValidator()
            result = validator.validate_project(project)
            
            click.echo(f"Validation: {'✅ PASS' if result.is_valid else '❌ FAIL'}")
            
            summary = result.get_summary()
            if summary['errors'] > 0:
                click.echo(f"  Errors: {summary['errors']}")
                validation_passed = False
            if summary['warnings'] > 0:
                click.echo(f"  Warnings: {summary['warnings']}")
            if summary['info'] > 0:
                click.echo(f"  Info: {summary['info']}")
            
            # Show errors
            for error in result.get_errors():
                click.echo(f"  ❌ {error.category}: {error.message}")
            
            # Save validation report if requested
            if report:
                report_content = validator.generate_validation_report(result)
                with open(report, 'w') as f:
                    f.write(report_content)
                click.echo(f"📄 Validation report saved: {report}")
            
            # Check if we should continue
            if not validation_passed and not force:
                click.echo("\n❌ Validation failed. Use --force to continue anyway.")
                sys.exit(1)
        
        # Save the project
        click.echo("\nSaving project...")
        if output_format == '.acd':
            click.echo("❌ Direct ACD generation not supported. Use Studio 5000 integration.")
            sys.exit(1)
        elif output_format == '.l5x':
            output_handler = L5XHandler()
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        output_handler.save(project, output_file)
        click.echo(f"✅ Conversion completed: {output_file}")
        
    except (ConversionError, FormatError, ValidationError) as e:
        click.echo(f"❌ Conversion failed: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output report file')
@click.option('--capabilities', is_flag=True, help='Include controller capability validation')
@click.option('--data-integrity', is_flag=True, help='Include data integrity validation')
@click.option('--instructions', is_flag=True, help='Include instruction validation')
def validate(
    input_file: Path, 
    output: Optional[Path],
    capabilities: bool,
    data_integrity: bool,
    instructions: bool
):
    """Validate a PLC project file.
    
    INPUT_FILE: PLC file to validate (ACD or L5X)
    """
    try:
        # Determine file format
        file_format = input_file.suffix.lower()
        
        # Load the project
        if file_format == '.acd':
            handler = ACDHandler()
        elif file_format == '.l5x':
            handler = L5XHandler()
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
        
        click.echo(f"Loading {file_format.upper()} file: {input_file}")
        project = handler.load(input_file)
        click.echo(f"✅ Loaded: {project.name}")
        
        # Configure validation options
        validation_options = {}
        if capabilities or data_integrity or instructions:
            # Use specific options if any are specified
            validation_options = {
                'capabilities': capabilities,
                'data_integrity': data_integrity,
                'instructions': instructions
            }
        else:
            # Use all validations by default
            validation_options = {
                'capabilities': True,
                'data_integrity': True,
                'instructions': True
            }
        
        # Run validation
        click.echo("\nRunning comprehensive validation...")
        validator = PLCValidator()
        result = validator.validate_project(project, validation_options)
        
        # Display results
        click.echo(f"\nValidation Status: {'✅ PASS' if result.is_valid else '❌ FAIL'}")
        
        summary = result.get_summary()
        click.echo(f"Issues Found: {summary['total_issues']}")
        click.echo(f"  Errors: {summary['errors']}")
        click.echo(f"  Warnings: {summary['warnings']}")
        click.echo(f"  Info: {summary['info']}")
        
        # Show detailed issues
        if result.issues:
            click.echo("\nDetailed Issues:")
            for issue in result.issues:
                severity_emoji = "❌" if issue.severity.value == "ERROR" else "⚠️" if issue.severity.value == "WARNING" else "ℹ️"
                click.echo(f"  {severity_emoji} [{issue.category}] {issue.message}")
                if issue.recommendation:
                    click.echo(f"     💡 {issue.recommendation}")
        
        # Show statistics
        if result.statistics:
            click.echo(f"\nProject Statistics:")
            stats = result.statistics.get('project_stats', {})
            click.echo(f"  Programs: {stats.get('programs', 0)}")
            click.echo(f"  Routines: {stats.get('total_routines', 0)}")
            click.echo(f"  Tags: {stats.get('total_tags', 0)}")
            click.echo(f"  AOIs: {stats.get('aois', 0)}")
            click.echo(f"  UDTs: {stats.get('udts', 0)}")
            click.echo(f"  Devices: {stats.get('devices', 0)}")
            
            validation_time = result.statistics.get('validation_time', 0)
            click.echo(f"  Validation Time: {validation_time:.2f}s")
        
        # Generate report if requested
        if output:
            report_content = validator.generate_validation_report(result)
            with open(output, 'w') as f:
                f.write(report_content)
            click.echo(f"\n📄 Detailed report saved: {output}")
        
        # Exit with error code if validation failed
        if not result.is_valid:
            sys.exit(1)
        
    except (ConversionError, FormatError, ValidationError) as e:
        click.echo(f"❌ Validation failed: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")
        sys.exit(1)


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument('output_dir', type=click.Path(path_type=Path))
@click.option('--pattern', '-p', default='*.L5X', help='File pattern to match (default: *.L5X)')
@click.option('--validate', '-v', is_flag=True, help='Validate each file before processing')
@click.option('--continue-on-error', is_flag=True, help='Continue processing other files if one fails')
def batch(
    input_dir: Path, 
    output_dir: Path, 
    pattern: str,
    validate: bool,
    continue_on_error: bool
):
    """Batch process multiple PLC files.
    
    INPUT_DIR: Directory containing PLC files
    OUTPUT_DIR: Directory for processed files
    """
    try:
        # Find matching files
        files = list(input_dir.glob(pattern))
        if not files:
            click.echo(f"No files found matching pattern: {pattern}")
            return
        
        click.echo(f"Found {len(files)} files matching pattern: {pattern}")
        click.echo(f"Output directory: {output_dir}")
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each file
        processed = 0
        failed = 0
        
        for file_path in files:
            try:
                click.echo(f"\nProcessing: {file_path.name}")
                
                # Determine handler
                file_format = file_path.suffix.lower()
                if file_format == '.acd':
                    handler = ACDHandler()
                elif file_format == '.l5x':
                    handler = L5XHandler()
                else:
                    click.echo(f"  ⚠️ Skipping unsupported format: {file_format}")
                    continue
                
                # Load project
                project = handler.load(file_path)
                
                # Validate if requested
                if validate:
                    validator = PLCValidator()
                    result = validator.validate_project(project)
                    click.echo(f"  Validation: {'✅ PASS' if result.is_valid else '❌ FAIL'}")
                    
                    if not result.is_valid and not continue_on_error:
                        click.echo(f"  ❌ Validation failed, skipping file")
                        failed += 1
                        continue
                
                # Save processed file
                output_file = output_dir / f"processed_{file_path.name}"
                if file_format == '.l5x':
                    output_handler = L5XHandler()
                    output_handler.save(project, output_file)
                    click.echo(f"  ✅ Saved: {output_file.name}")
                    processed += 1
                else:
                    click.echo(f"  ⚠️ Cannot save ACD format, skipping")
                
            except Exception as e:
                click.echo(f"  ❌ Error processing {file_path.name}: {e}")
                failed += 1
                if not continue_on_error:
                    break
        
        # Summary
        click.echo(f"\nBatch processing complete:")
        click.echo(f"  Processed: {processed}")
        click.echo(f"  Failed: {failed}")
        click.echo(f"  Total: {len(files)}")
        
    except Exception as e:
        click.echo(f"❌ Batch processing failed: {e}")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main() 