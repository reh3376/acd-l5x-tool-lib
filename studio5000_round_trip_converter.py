#!/usr/bin/env python3
"""
Complete Round-Trip ACD ↔ L5X Converter
Using hutcheb/acd for ACD → L5X and Studio5000AutomationClient for L5X → ACD
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

# For ACD → L5X conversion
from acd.api import ImportProjectFromFile

# For L5X → ACD conversion
try:
    from etl.studio5000_integration import Studio5000AutomationClient
    STUDIO5000_AVAILABLE = True
except ImportError:
    STUDIO5000_AVAILABLE = False
    print("⚠️  Warning: Studio5000AutomationClient not available")
    print("   L5X → ACD conversion will not be possible")

class RoundTripConverter:
    """
    Complete round-trip converter for ACD ↔ L5X formats
    """
    
    def __init__(self):
        self.output_dir = Path("round_trip_output")
        self.output_dir.mkdir(exist_ok=True)
        self.conversion_log = []
        
    def acd_to_l5x(self, acd_file, output_l5x=None):
        """
        Convert ACD to L5X using hutcheb/acd
        """
        acd_path = Path(acd_file)
        if not acd_path.exists():
            raise FileNotFoundError(f"ACD file not found: {acd_file}")
        
        # Set output path
        if output_l5x is None:
            output_l5x = self.output_dir / f"{acd_path.stem}.L5X"
        else:
            output_l5x = Path(output_l5x)
        
        print(f"\n🔄 Converting ACD → L5X")
        print(f"  Source: {acd_path}")
        print(f"  Target: {output_l5x}")
        
        start_time = datetime.now()
        
        try:
            # Use hutcheb/acd for conversion
            proj = ImportProjectFromFile(str(acd_path))
            proj.write_to_l5x(str(output_l5x))
            
            # Get file info
            acd_size = acd_path.stat().st_size
            l5x_size = output_l5x.stat().st_size
            
            conversion_time = (datetime.now() - start_time).total_seconds()
            
            # Log conversion
            self.conversion_log.append({
                'operation': 'ACD → L5X',
                'source': str(acd_path),
                'target': str(output_l5x),
                'source_size': acd_size,
                'target_size': l5x_size,
                'conversion_time': conversion_time,
                'status': 'SUCCESS'
            })
            
            print(f"✅ Conversion successful!")
            print(f"  ACD size: {acd_size:,} bytes")
            print(f"  L5X size: {l5x_size:,} bytes")
            print(f"  Time: {conversion_time:.2f} seconds")
            
            return output_l5x
            
        except Exception as e:
            self.conversion_log.append({
                'operation': 'ACD → L5X',
                'source': str(acd_path),
                'target': str(output_l5x),
                'status': 'FAILED',
                'error': str(e)
            })
            raise
    
    def l5x_to_acd(self, l5x_file, output_acd=None):
        """
        Convert L5X to ACD using Studio5000AutomationClient
        """
        if not STUDIO5000_AVAILABLE:
            raise ImportError("Studio5000AutomationClient not available")
        
        l5x_path = Path(l5x_file)
        if not l5x_path.exists():
            raise FileNotFoundError(f"L5X file not found: {l5x_file}")
        
        # Set output path
        if output_acd is None:
            output_acd = self.output_dir / f"{l5x_path.stem}.ACD"
        else:
            output_acd = Path(output_acd)
        
        print(f"\n🔄 Converting L5X → ACD")
        print(f"  Source: {l5x_path}")
        print(f"  Target: {output_acd}")
        
        start_time = datetime.now()
        
        try:
            # Use Studio5000AutomationClient
            client = Studio5000AutomationClient()
            
            print("  Connecting to Studio 5000...")
            client.connect()
            
            print("  Importing L5X...")
            client.import_from_l5x(
                str(l5x_path.absolute()),
                target_acd_path=str(output_acd.absolute())
            )
            
            print("  Disconnecting...")
            client.disconnect()
            
            # Get file info
            l5x_size = l5x_path.stat().st_size
            acd_size = output_acd.stat().st_size if output_acd.exists() else 0
            
            conversion_time = (datetime.now() - start_time).total_seconds()
            
            # Log conversion
            self.conversion_log.append({
                'operation': 'L5X → ACD',
                'source': str(l5x_path),
                'target': str(output_acd),
                'source_size': l5x_size,
                'target_size': acd_size,
                'conversion_time': conversion_time,
                'status': 'SUCCESS'
            })
            
            print(f"✅ Conversion successful!")
            print(f"  L5X size: {l5x_size:,} bytes")
            print(f"  ACD size: {acd_size:,} bytes")
            print(f"  Time: {conversion_time:.2f} seconds")
            
            return output_acd
            
        except Exception as e:
            self.conversion_log.append({
                'operation': 'L5X → ACD',
                'source': str(l5x_path),
                'target': str(output_acd),
                'status': 'FAILED',
                'error': str(e)
            })
            raise
    
    def round_trip_test(self, original_acd):
        """
        Perform complete round-trip conversion and validate
        ACD → L5X → ACD
        """
        print(f"\n🔄 ROUND-TRIP CONVERSION TEST")
        print("="*50)
        
        original_path = Path(original_acd)
        if not original_path.exists():
            raise FileNotFoundError(f"Original ACD not found: {original_acd}")
        
        # Step 1: ACD → L5X
        print("\n📋 Step 1: ACD → L5X")
        intermediate_l5x = self.acd_to_l5x(original_acd)
        
        # Step 2: L5X → ACD
        print("\n📋 Step 2: L5X → ACD")
        final_acd = self.l5x_to_acd(
            intermediate_l5x,
            output_acd=self.output_dir / f"{original_path.stem}_roundtrip.ACD"
        )
        
        # Step 3: Compare original and final ACD
        print("\n📋 Step 3: Comparing original and round-trip ACD")
        comparison = self.compare_acd_files(original_path, final_acd)
        
        # Generate report
        self.generate_round_trip_report(original_path, intermediate_l5x, final_acd, comparison)
        
        return comparison['identical']
    
    def compare_acd_files(self, acd1, acd2):
        """
        Compare two ACD files
        """
        path1 = Path(acd1)
        path2 = Path(acd2)
        
        comparison = {
            'file1': str(path1),
            'file2': str(path2),
            'size1': path1.stat().st_size,
            'size2': path2.stat().st_size,
            'size_diff': path2.stat().st_size - path1.stat().st_size,
            'identical': False,
            'differences': []
        }
        
        # Compare file sizes
        if comparison['size1'] != comparison['size2']:
            comparison['differences'].append(
                f"File size difference: {comparison['size_diff']:+,} bytes"
            )
        
        # Compare MD5 hashes
        md5_1 = self.calculate_md5(path1)
        md5_2 = self.calculate_md5(path2)
        
        comparison['md5_1'] = md5_1
        comparison['md5_2'] = md5_2
        
        if md5_1 == md5_2:
            comparison['identical'] = True
            print("  ✅ Files are identical!")
        else:
            print("  ⚠️  Files differ")
            comparison['differences'].append("MD5 hashes do not match")
            
            # Try to extract and compare databases
            try:
                self.compare_internal_databases(path1, path2, comparison)
            except Exception as e:
                comparison['differences'].append(f"Could not compare databases: {e}")
        
        return comparison
    
    def calculate_md5(self, file_path):
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def compare_internal_databases(self, acd1, acd2, comparison):
        """Compare internal databases of two ACD files"""
        from acd.api import ExtractAcdDatabase
        
        # Extract databases from both files
        db_dir1 = self.output_dir / "compare_db1"
        db_dir2 = self.output_dir / "compare_db2"
        
        ExtractAcdDatabase(str(acd1), str(db_dir1)).extract()
        ExtractAcdDatabase(str(acd2), str(db_dir2)).extract()
        
        # Compare each database
        db_files1 = set(f.name for f in db_dir1.glob("*"))
        db_files2 = set(f.name for f in db_dir2.glob("*"))
        
        # Check for missing databases
        missing_in_2 = db_files1 - db_files2
        extra_in_2 = db_files2 - db_files1
        
        if missing_in_2:
            comparison['differences'].append(f"Missing databases: {missing_in_2}")
        if extra_in_2:
            comparison['differences'].append(f"Extra databases: {extra_in_2}")
        
        # Compare common databases
        common_dbs = db_files1 & db_files2
        for db_name in common_dbs:
            size1 = (db_dir1 / db_name).stat().st_size
            size2 = (db_dir2 / db_name).stat().st_size
            
            if size1 != size2:
                comparison['differences'].append(
                    f"{db_name}: size difference {size2 - size1:+,} bytes"
                )
    
    def generate_round_trip_report(self, original_acd, intermediate_l5x, final_acd, comparison):
        """Generate detailed round-trip conversion report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'round_trip_path': {
                'original_acd': str(original_acd),
                'intermediate_l5x': str(intermediate_l5x),
                'final_acd': str(final_acd)
            },
            'comparison': comparison,
            'conversion_log': self.conversion_log,
            'success': comparison['identical']
        }
        
        report_file = self.output_dir / "round_trip_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Round-trip report saved: {report_file}")
        
        # Print summary
        print("\n📊 ROUND-TRIP SUMMARY")
        print("="*50)
        print(f"Original ACD: {original_acd.name}")
        print(f"Size: {original_acd.stat().st_size:,} bytes")
        print(f"\nFinal ACD: {final_acd.name}")
        print(f"Size: {final_acd.stat().st_size:,} bytes")
        print(f"\nResult: {'✅ IDENTICAL' if comparison['identical'] else '⚠️  DIFFERENT'}")
        
        if not comparison['identical']:
            print("\nDifferences:")
            for diff in comparison['differences']:
                print(f"  - {diff}")

def main():
    """Test round-trip conversion"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ACD ↔ L5X Round-Trip Converter')
    parser.add_argument('command', choices=['acd2l5x', 'l5x2acd', 'roundtrip'],
                        help='Conversion command')
    parser.add_argument('input_file', help='Input file (ACD or L5X)')
    parser.add_argument('--output', '-o', help='Output file path')
    
    args = parser.parse_args()
    
    converter = RoundTripConverter()
    
    try:
        if args.command == 'acd2l5x':
            output = converter.acd_to_l5x(args.input_file, args.output)
            print(f"\n✅ Conversion complete: {output}")
            
        elif args.command == 'l5x2acd':
            if not STUDIO5000_AVAILABLE:
                print("❌ Studio5000AutomationClient not available")
                print("   Please ensure Studio 5000 is installed and the automation client is available")
                sys.exit(1)
                
            output = converter.l5x_to_acd(args.input_file, args.output)
            print(f"\n✅ Conversion complete: {output}")
            
        elif args.command == 'roundtrip':
            success = converter.round_trip_test(args.input_file)
            sys.exit(0 if success else 1)
            
    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Run test with our sample file
        print("🔄 Running round-trip test with sample ACD file...")
        
        converter = RoundTripConverter()
        test_acd = "docs/exports/PLC100_Mashing.ACD"
        
        if Path(test_acd).exists():
            if STUDIO5000_AVAILABLE:
                converter.round_trip_test(test_acd)
            else:
                # Just test ACD → L5X
                print("⚠️  Studio 5000 not available, testing ACD → L5X only")
                converter.acd_to_l5x(test_acd)
        else:
            print(f"❌ Test file not found: {test_acd}")
            print("\nUsage: python studio5000_round_trip_converter.py <command> <input_file>")
            print("Commands: acd2l5x, l5x2acd, roundtrip")
    else:
        main() 