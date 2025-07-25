#!/usr/bin/env python3
"""
Explore hutcheb/acd capabilities
"""

import os
import json
from pathlib import Path
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract
from acd.generated.dat import Dat

def explore_acd_databases():
    """Explore what we can extract from ACD databases"""
    
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    output_dir = "hutcheb_exploration"
    
    print(f"🔍 Exploring ACD: {acd_file}")
    print("="*60)
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    db_dir = Path(output_dir) / "databases"
    
    # Extract database files
    print("\n📋 Step 1: Extracting database files...")
    try:
        ExtractAcdDatabase(acd_file, str(db_dir)).extract()
        print("✅ Database files extracted")
        
        # List extracted files
        db_files = list(db_dir.glob("*"))
        print(f"\n📁 Extracted {len(db_files)} files:")
        for db_file in sorted(db_files):
            size_mb = db_file.stat().st_size / 1024 / 1024
            print(f"   - {db_file.name} ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"❌ Error extracting: {e}")
        return
    
    # Try to read each database individually
    print("\n📋 Step 2: Attempting to read databases...")
    results = {}
    
    for db_file in sorted(db_dir.glob("*.Dat")):
        print(f"\n🔍 {db_file.name}:")
        
        try:
            # Try to read as Dat file
            db = DbExtract(str(db_file)).read()
            
            # Count records
            record_count = len(db.records.record) if hasattr(db.records, 'record') else 0
            print(f"   ✅ Records: {record_count}")
            
            # Sample first few records
            if record_count > 0 and hasattr(db.records, 'record'):
                print(f"   📊 Sample records:")
                for i, record in enumerate(db.records.record[:3]):
                    record_info = {
                        'identifier': hex(record.identifier) if hasattr(record, 'identifier') else 'Unknown',
                        'len_record': record.len_record if hasattr(record, 'len_record') else 'Unknown',
                        'has_record': hasattr(record, 'record')
                    }
                    print(f"      Record {i}: {record_info}")
                    
                    # Try to extract some text
                    if hasattr(record, 'record') and hasattr(record.record, 'record_buffer'):
                        buffer = record.record.record_buffer
                        # Look for readable strings
                        text_parts = []
                        for j in range(0, min(100, len(buffer))):
                            if 32 <= buffer[j] <= 126:  # Printable ASCII
                                text_parts.append(chr(buffer[j]))
                            else:
                                if text_parts and len(text_parts) > 4:
                                    print(f"         Text: {''.join(text_parts)}")
                                text_parts = []
            
            results[db_file.name] = {
                'status': 'success',
                'records': record_count
            }
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")
            results[db_file.name] = {
                'status': 'error',
                'error': str(e)[:200]
            }
    
    # Check XML files
    print("\n📋 Step 3: Checking XML files...")
    for xml_file in sorted(db_dir.glob("*.XML")):
        print(f"\n🔍 {xml_file.name}:")
        
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'utf-16le', 'utf-16be']
            content = None
            
            for encoding in encodings:
                try:
                    with open(xml_file, 'r', encoding=encoding) as f:
                        content = f.read(1000)  # First 1KB
                    print(f"   ✅ Encoding: {encoding}")
                    break
                except:
                    continue
            
            if content:
                lines = content.split('\n')[:5]
                print("   📄 First few lines:")
                for line in lines:
                    print(f"      {line[:100]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Save results
    results_file = Path(output_dir) / "exploration_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Exploration complete! Results saved to {results_file}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY:")
    successful = sum(1 for r in results.values() if r['status'] == 'success')
    failed = sum(1 for r in results.values() if r['status'] == 'error')
    print(f"  Successful reads: {successful}")
    print(f"  Failed reads: {failed}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if 'Comps.Dat' in results and results['Comps.Dat']['status'] == 'success':
        print("  ✅ Comps.Dat readable - contains PLC components")
    if 'Region Map.Dat' in results and results['Region Map.Dat']['status'] == 'error':
        print("  ⚠️  Region Map.Dat has issues - may need custom parser")
    print("  ✅ TagInfo.XML contains complete program structure")

if __name__ == "__main__":
    explore_acd_databases() 