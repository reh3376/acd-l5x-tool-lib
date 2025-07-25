#!/usr/bin/env python3
"""
Complete ACD parser using hutcheb/acd library
"""

import os
import json
from pathlib import Path
from collections import defaultdict
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract

def parse_acd_complete():
    """Parse ACD file completely using hutcheb/acd"""
    
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    output_dir = "acd_complete_parse"
    
    print(f"🔍 Complete ACD Parsing: {acd_file}")
    print("="*60)
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Step 1: Extract database files
    print("\n📋 Step 1: Extracting database files...")
    db_dir = Path(output_dir) / "database_files"
    try:
        ExtractAcdDatabase(acd_file, db_dir).extract()
        print(f"✅ Database files extracted to {db_dir}")
    except Exception as e:
        print(f"❌ Error extracting: {e}")
        return
    
    # Step 2: Parse each database file
    results = {
        'databases': {},
        'programs': [],
        'modules': [],
        'tags': [],
        'data_types': [],
        'routines': []
    }
    
    # Parse Comps.Dat
    print("\n📋 Step 2: Parsing Comps.Dat...")
    comps_file = db_dir / "Comps.Dat"
    if comps_file.exists():
        try:
            db = DbExtract(str(comps_file)).read()
            print(f"  Total records: {len(db.records)}")
            
            # Analyze records
            record_types = defaultdict(int)
            
            for i, record in enumerate(db.records):
                try:
                    # Get record data
                    data = record.record.record_buffer
                    
                    # Try to identify record type by looking for known patterns
                    if b'Program' in data[:100]:
                        record_types['Program'] += 1
                        # Extract program info
                        results['programs'].append({
                            'record_id': i,
                            'size': len(data)
                        })
                    elif b'Module' in data[:100]:
                        record_types['Module'] += 1
                        results['modules'].append({
                            'record_id': i,
                            'size': len(data)
                        })
                    elif b'DataType' in data[:100]:
                        record_types['DataType'] += 1
                        results['data_types'].append({
                            'record_id': i,
                            'size': len(data)
                        })
                    elif b'Routine' in data[:100]:
                        record_types['Routine'] += 1
                        results['routines'].append({
                            'record_id': i,
                            'size': len(data)
                        })
                    elif b'Tag' in data[:100]:
                        record_types['Tag'] += 1
                        results['tags'].append({
                            'record_id': i,
                            'size': len(data)
                        })
                    else:
                        record_types['Other'] += 1
                except:
                    record_types['Error'] += 1
            
            print("\n  Record type analysis:")
            for rtype, count in sorted(record_types.items()):
                print(f"    {rtype}: {count}")
            
            results['databases']['Comps'] = {
                'total_records': len(db.records),
                'record_types': dict(record_types)
            }
            
        except Exception as e:
            print(f"❌ Error parsing Comps.Dat: {e}")
    
    # Parse TagInfo.XML
    print("\n📋 Step 3: Parsing TagInfo.XML...")
    taginfo_file = db_dir / "TagInfo.XML"
    if taginfo_file.exists():
        try:
            # It's UTF-16 encoded
            with open(taginfo_file, 'r', encoding='utf-16', errors='ignore') as f:
                content = f.read()
            
            # Basic XML parsing
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)
            
            controller_name = root.get('Name', 'Unknown')
            print(f"  Controller: {controller_name}")
            
            # Count elements
            datatypes = root.findall('.//DataType')
            modules = root.findall('.//Module')
            tags = root.findall('.//Tag')
            programs = root.findall('.//Program')
            
            print(f"  DataTypes: {len(datatypes)}")
            print(f"  Modules: {len(modules)}")
            print(f"  Tags: {len(tags)}")
            print(f"  Programs: {len(programs)}")
            
            results['taginfo'] = {
                'controller_name': controller_name,
                'datatype_count': len(datatypes),
                'module_count': len(modules),
                'tag_count': len(tags),
                'program_count': len(programs)
            }
            
        except Exception as e:
            print(f"❌ Error parsing TagInfo.XML: {e}")
    
    # Check other databases
    print("\n📋 Step 4: Checking other databases...")
    for db_file in ['SbRegion.Dat', 'Comments.Dat', 'Nameless.Dat']:
        db_path = db_dir / db_file
        if db_path.exists():
            try:
                db = DbExtract(str(db_path)).read()
                print(f"  {db_file}: {len(db.records)} records")
                results['databases'][db_file] = {
                    'total_records': len(db.records)
                }
            except Exception as e:
                print(f"  {db_file}: Error - {e}")
    
    # Save complete results
    output_file = Path(output_dir) / "complete_parse_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Complete results saved to {output_file}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 PARSING SUMMARY:")
    print(f"  Programs found: {len(results['programs'])}")
    print(f"  Modules found: {len(results['modules'])}")
    print(f"  Data Types found: {len(results['data_types'])}")
    print(f"  Routines found: {len(results['routines'])}")
    print(f"  Tags found: {len(results['tags'])}")
    
    return results

if __name__ == "__main__":
    parse_acd_complete() 