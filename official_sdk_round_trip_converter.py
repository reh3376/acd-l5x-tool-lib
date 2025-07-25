#!/usr/bin/env python3
"""
Official Round-Trip ACD ↔ L5X Converter using Rockwell's Logix Designer SDK
Requires: Studio 5000 + Logix Designer SDK v2.01+
"""

import asyncio
import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List

# Official Rockwell SDK
try:
    from logix_designer_sdk.logix_project import LogixProject
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("⚠️  Warning: Logix Designer SDK not available")
    print("   Install: pip install /path/to/logix_designer_sdk-*.whl")

# For ACD → L5X we still use hutcheb/acd as it's more feature-rich
try:
    from acd.api import ImportProjectFromFile
    HUTCHEB_AVAILABLE = True
except ImportError:
    HUTCHEB_AVAILABLE = False
    print("⚠️  Warning: hutcheb/acd not available for ACD → L5X conversion")

class OfficialRoundTripConverter:
    """
    Production-ready round-trip converter using official Rockwell SDK
    """
    
    def __init__(self):
        self.output_dir = Path("official_round_trip_output")
        self.output_dir.mkdir(exist_ok=True)
        self.conversion_log = []
        
    async def l5x_to_acd_official(self, l5x_path: str, acd_path: str) -> bool:
        """
        Convert L5X to ACD using official Rockwell SDK
        
        This is the OFFICIAL method recommended by Rockwell
        """
        if not SDK_AVAILABLE:
            raise ImportError("Logix Designer SDK not installed")
            
        l5x_file = Path(l5x_path)
        acd_file = Path(acd_path)
        
        if not l5x_file.exists():
            raise FileNotFoundError(f"L5X file not found: {l5x_path}")
        
        print(f"\n🔄 Converting L5X → ACD (Official SDK)")
        print(f"  Source: {l5x_file}")
        print(f"  Target: {acd_file}")
        
        start_time = datetime.now()
        
        try:
            # Official SDK method - import L5X as project in memory
            print("  Importing L5X as project...")
            proj = await LogixProject.import_l5x(str(l5x_file))
            
            # Save it back out as ACD file
            print("  Saving as ACD...")
            await proj.save_as(str(acd_file))
            
            # Close project
            await proj.close()
            
            # Verify output
            if not acd_file.exists():
                raise RuntimeError("ACD file was not created")
            
            # Get file sizes
            l5x_size = l5x_file.stat().st_size
            acd_size = acd_file.stat().st_size
            
            conversion_time = (datetime.now() - start_time).total_seconds()
            
            # Log success
            self.conversion_log.append({
                'operation': 'L5X → ACD (Official SDK)',
                'source': str(l5x_file),
                'target': str(acd_file),
                'source_size': l5x_size,
                'target_size': acd_size,
                'conversion_time': conversion_time,
                'status': 'SUCCESS'
            })
            
            print(f"✅ Conversion successful!")
            print(f"  L5X size: {l5x_size:,} bytes")
            print(f"  ACD size: {acd_size:,} bytes")
            print(f"  Time: {conversion_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            self.conversion_log.append({
                'operation': 'L5X → ACD (Official SDK)',
                'source': str(l5x_file),
                'target': str(acd_file),
                'status': 'FAILED',
                'error': str(e)
            })
            print(f"❌ Conversion failed: {e}")
            return False
    
    async def acd_to_l5x_official(self, acd_path: str, l5x_path: str) -> bool:
        """
        Convert ACD to L5X using official Rockwell SDK
        """
        if not SDK_AVAILABLE:
            raise ImportError("Logix Designer SDK not installed")
            
        acd_file = Path(acd_path)
        l5x_file = Path(l5x_path)
        
        if not acd_file.exists():
            raise FileNotFoundError(f"ACD file not found: {acd_path}")
        
        print(f"\n🔄 Converting ACD → L5X (Official SDK)")
        print(f"  Source: {acd_file}")
        print(f"  Target: {l5x_file}")
        
        start_time = datetime.now()
        
        try:
            # Open ACD project
            print("  Opening ACD project...")
            proj = await LogixProject.open_logix_project(str(acd_file))
            
            # Export to L5X
            print("  Exporting to L5X...")
            await proj.export_l5x(
                str(l5x_file),
                encode_source=False,  # Keep source readable
                export_context=True   # Include all context
            )
            
            # Close project
            await proj.close()
            
            # Verify output
            if not l5x_file.exists():
                raise RuntimeError("L5X file was not created")
            
            # Get file sizes
            acd_size = acd_file.stat().st_size
            l5x_size = l5x_file.stat().st_size
            
            conversion_time = (datetime.now() - start_time).total_seconds()
            
            # Log success
            self.conversion_log.append({
                'operation': 'ACD → L5X (Official SDK)',
                'source': str(acd_file),
                'target': str(l5x_file),
                'source_size': acd_size,
                'target_size': l5x_size,
                'conversion_time': conversion_time,
                'status': 'SUCCESS'
            })
            
            print(f"✅ Conversion successful!")
            print(f"  ACD size: {acd_size:,} bytes")
            print(f"  L5X size: {l5x_size:,} bytes")
            print(f"  Time: {conversion_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            self.conversion_log.append({
                'operation': 'ACD → L5X (Official SDK)',
                'source': str(acd_file),
                'target': str(l5x_file),
                'status': 'FAILED',
                'error': str(e)
            })
            print(f"❌ Conversion failed: {e}")
            return False
    
    def acd_to_l5x_hutcheb(self, acd_path: str, l5x_path: str) -> bool:
        """
        Convert ACD to L5X using hutcheb/acd (alternative method)
        Better for extracting all components including comments
        """
        if not HUTCHEB_AVAILABLE:
            print("⚠️  hutcheb/acd not available, falling back to SDK")
            return asyncio.run(self.acd_to_l5x_official(acd_path, l5x_path))
        
        acd_file = Path(acd_path)
        l5x_file = Path(l5x_path)
        
        print(f"\n🔄 Converting ACD → L5X (hutcheb/acd)")
        print(f"  Source: {acd_file}")
        print(f"  Target: {l5x_file}")
        
        try:
            proj = ImportProjectFromFile(str(acd_file))
            proj.write_to_l5x(str(l5x_file))
            
            print(f"✅ Conversion successful!")
            return True
            
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            return False
    
    async def round_trip_test(self, original_acd: str, method: str = "official") -> bool:
        """
        Perform complete round-trip test
        
        Args:
            original_acd: Path to original ACD file
            method: "official" (SDK both ways) or "hybrid" (hutcheb + SDK)
        """
        print(f"\n🔄 ROUND-TRIP CONVERSION TEST ({method.upper()} METHOD)")
        print("="*60)
        
        original_path = Path(original_acd)
        if not original_path.exists():
            raise FileNotFoundError(f"Original ACD not found: {original_acd}")
        
        # Set paths
        intermediate_l5x = self.output_dir / f"{original_path.stem}_intermediate.L5X"
        final_acd = self.output_dir / f"{original_path.stem}_roundtrip.ACD"
        
        # Step 1: ACD → L5X
        print("\n📋 Step 1: ACD → L5X")
        if method == "official":
            success = await self.acd_to_l5x_official(original_acd, str(intermediate_l5x))
        else:
            success = self.acd_to_l5x_hutcheb(original_acd, str(intermediate_l5x))
        
        if not success:
            print("❌ Round-trip failed at Step 1")
            return False
        
        # Step 2: L5X → ACD
        print("\n📋 Step 2: L5X → ACD")
        success = await self.l5x_to_acd_official(str(intermediate_l5x), str(final_acd))
        
        if not success:
            print("❌ Round-trip failed at Step 2")
            return False
        
        # Step 3: Compare files
        print("\n📋 Step 3: Comparing original and round-trip ACD")
        comparison = self.compare_files(original_path, final_acd)
        
        # Generate report
        self.generate_report(original_path, intermediate_l5x, final_acd, comparison)
        
        return comparison['identical']
    
    def compare_files(self, file1: Path, file2: Path) -> dict:
        """Compare two files"""
        comparison = {
            'file1': str(file1),
            'file2': str(file2),
            'size1': file1.stat().st_size,
            'size2': file2.stat().st_size,
            'size_diff': file2.stat().st_size - file1.stat().st_size,
            'identical': False
        }
        
        # Calculate MD5 hashes
        with open(file1, 'rb') as f:
            md5_1 = hashlib.md5(f.read()).hexdigest()
        
        with open(file2, 'rb') as f:
            md5_2 = hashlib.md5(f.read()).hexdigest()
        
        comparison['md5_1'] = md5_1
        comparison['md5_2'] = md5_2
        comparison['identical'] = (md5_1 == md5_2)
        
        if comparison['identical']:
            print("  ✅ Files are identical!")
        else:
            print("  ⚠️  Files differ")
            print(f"    Size difference: {comparison['size_diff']:+,} bytes")
            print(f"    MD5 mismatch")
        
        return comparison
    
    def generate_report(self, original: Path, intermediate: Path, final: Path, comparison: dict):
        """Generate round-trip report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'method': 'Official Rockwell SDK',
            'paths': {
                'original_acd': str(original),
                'intermediate_l5x': str(intermediate),
                'final_acd': str(final)
            },
            'comparison': comparison,
            'conversion_log': self.conversion_log
        }
        
        report_file = self.output_dir / "official_round_trip_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved: {report_file}")
    
    async def batch_convert(self, input_dir: str, output_dir: str, 
                          direction: str = "l5x_to_acd") -> Tuple[int, List]:
        """
        Batch convert files using official SDK
        
        Args:
            input_dir: Directory containing source files
            output_dir: Directory for output files
            direction: "l5x_to_acd" or "acd_to_l5x"
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Determine file pattern
        if direction == "l5x_to_acd":
            pattern = "*.L5X"
            convert_func = self.l5x_to_acd_official
            output_ext = ".ACD"
        else:
            pattern = "*.ACD"
            convert_func = self.acd_to_l5x_official
            output_ext = ".L5X"
        
        files = list(input_path.glob(pattern))
        print(f"\n📋 Batch converting {len(files)} files ({direction})")
        
        success_count = 0
        failed_files = []
        
        for source_file in files:
            output_file = output_path / f"{source_file.stem}{output_ext}"
            
            try:
                print(f"\nConverting {source_file.name}...")
                success = await convert_func(str(source_file), str(output_file))
                
                if success:
                    success_count += 1
                else:
                    failed_files.append((source_file.name, "Conversion failed"))
                    
            except Exception as e:
                failed_files.append((source_file.name, str(e)))
        
        # Summary
        print(f"\n📊 Batch Conversion Summary:")
        print(f"  Successful: {success_count}/{len(files)}")
        print(f"  Failed: {len(failed_files)}")
        
        if failed_files:
            print("\n❌ Failed conversions:")
            for name, error in failed_files:
                print(f"  - {name}: {error}")
        
        return success_count, failed_files

async def main():
    """Main entry point with CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Official ACD ↔ L5X Converter using Rockwell SDK'
    )
    parser.add_argument('command', 
                       choices=['acd2l5x', 'l5x2acd', 'roundtrip', 'batch'],
                       help='Conversion command')
    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('--output', '-o', help='Output file or directory')
    parser.add_argument('--method', '-m', 
                       choices=['official', 'hybrid'],
                       default='official',
                       help='Conversion method (roundtrip only)')
    
    args = parser.parse_args()
    
    converter = OfficialRoundTripConverter()
    
    try:
        if args.command == 'acd2l5x':
            output = args.output or str(converter.output_dir / f"{Path(args.input).stem}.L5X")
            await converter.acd_to_l5x_official(args.input, output)
            
        elif args.command == 'l5x2acd':
            output = args.output or str(converter.output_dir / f"{Path(args.input).stem}.ACD")
            await converter.l5x_to_acd_official(args.input, output)
            
        elif args.command == 'roundtrip':
            success = await converter.round_trip_test(args.input, args.method)
            sys.exit(0 if success else 1)
            
        elif args.command == 'batch':
            if not args.output:
                print("❌ Output directory required for batch conversion")
                sys.exit(1)
            
            # Detect direction from input files
            input_path = Path(args.input)
            if list(input_path.glob("*.L5X")):
                direction = "l5x_to_acd"
            else:
                direction = "acd_to_l5x"
            
            await converter.batch_convert(args.input, args.output, direction)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

def install_sdk_instructions():
    """Print SDK installation instructions"""
    print("""
📋 Logix Designer SDK Installation Instructions:

1. Download SDK:
   - Open FactoryTalk Hub
   - Downloads → Studio 5000 → Utilities
   - Download "Logix Designer SDK" (v2.x)

2. Install SDK:
   - Run installer
   - Check "Python client" option
   - Default location: C:\\Users\\Public\\Documents\\Studio 5000\\Logix Designer SDK

3. Install Python Package:
   cd "%PUBLIC%\\Documents\\Studio 5000\\Logix Designer SDK\\python\\Examples"
   python -m venv .venv
   .venv\\Scripts\\activate
   pip install "..\\dist\\logix_designer_sdk-*.whl"

4. Verify Installation:
   python -c "from logix_designer_sdk.logix_project import LogixProject; print('SDK Ready!')"
""")

if __name__ == "__main__":
    if not SDK_AVAILABLE:
        print("\n❌ Logix Designer SDK not found!")
        install_sdk_instructions()
        sys.exit(1)
    
    if len(sys.argv) == 1:
        # No arguments - run test
        print("🔄 Running round-trip test with official SDK...")
        
        test_acd = "docs/exports/PLC100_Mashing.ACD"
        if Path(test_acd).exists():
            converter = OfficialRoundTripConverter()
            asyncio.run(converter.round_trip_test(test_acd))
        else:
            print(f"❌ Test file not found: {test_acd}")
            print("\nUsage: python official_sdk_round_trip_converter.py <command> <input>")
            print("Commands: acd2l5x, l5x2acd, roundtrip, batch")
    else:
        asyncio.run(main()) 