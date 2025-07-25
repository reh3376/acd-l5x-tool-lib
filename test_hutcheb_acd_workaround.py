#!/usr/bin/env python3
"""
Test hutcheb/acd with workaround for Unicode errors
"""

import os
import sys
import json
from pathlib import Path
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract
import sqlite3

def extract_and_parse_acd():
    """Extract ACD and parse it manually to avoid Unicode errors"""
    
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    output_dir = "hutcheb_acd_parsed"
    
    print(f"🔍 Parsing ACD file with workaround: {acd_file}")
    print("="*60)
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Step 1: Extract database files
    print("\n📋 Step 1: Extracting database files...")
    db_dir = Path(output_dir) / "database_files"
    ExtractAcdDatabase(acd_file, db_dir).extract()
    print(f"✅ Database files extracted to {db_dir}")
    
    # Step 2: Parse Comps.Dat directly
    print("\n📋 Step 2: Parsing Comps.Dat database...")
    comps_file = db_dir / "Comps.Dat"
    comps_idx = db_dir / "Comps.Idx"
    
    if comps_file.exists() and comps_idx.exists():
        try:
            # Create SQLite database
            db_path = Path(output_dir) / "parsed_acd.db"
            if db_path.exists():
                os.remove(db_path)
            
            db = sqlite3.connect(db_path)
            cur = db.cursor()
            
            # Create tables
            cur.execute("""CREATE TABLE IF NOT EXISTS comps 
                          (record_id INTEGER PRIMARY KEY, 
                           offset INTEGER, 
                           length INTEGER, 
                           data BLOB)""")
            
            # Extract records from Comps database
            extract = DbExtract(str(comps_file))
            records = list(extract.records)
            
            print(f"  Found {len(records)} records in Comps database")
            
            # Parse records and look for programs
            programs_found = []
            modules_found = []
            tags_found = []
            
            for i, record in enumerate(records[:1000]):  # First 1000 records
                try:
                    # Store raw record
                    cur.execute("INSERT INTO comps (record_id, offset, length, data) VALUES (?, ?, ?, ?)",
                              (i, record.offset, record.length, record.record_buffer))
                    
                    # Try to extract text from record
                    data = record.record_buffer
                    
                    # Look for UTF-16LE strings
                    text_parts = []
                    for j in range(0, len(data) - 1, 2):
                        try:
                            char = data[j:j+2].decode('utf-16le')
                            if char.isprintable():
                                text_parts.append(char)
                            else:
                                if text_parts and len(''.join(text_parts)) > 3:
                                    text = ''.join(text_parts)
                                    
                                    # Check if it's a program name
                                    if any(prog in text for prog in ['Main', 'Milling', 'Cooker', 'MashWater', 'DropTub']):
                                        programs_found.append((i, text))
                                    
                                    # Check if it's a module name
                                    if any(mod in text for mod in ['ENET', 'DI_', 'DO_', 'AI_', 'AO_']):
                                        modules_found.append((i, text))
                                
                                text_parts = []
                        except:
                            if text_parts:
                                text_parts = []
                    
                except Exception as e:
                    pass
            
            db.commit()
            
            print(f"\n📊 Parsing Results:")
            print(f"  Programs found: {len(programs_found)}")
            if programs_found:
                for idx, (rec_id, name) in enumerate(programs_found[:10]):
                    print(f"    {idx+1}. Record {rec_id}: {name[:50]}...")
            
            print(f"  Modules found: {len(modules_found)}")
            if modules_found:
                for idx, (rec_id, name) in enumerate(modules_found[:10]):
                    print(f"    {idx+1}. Record {rec_id}: {name[:50]}...")
            
            # Save results
            results = {
                'total_records': len(records),
                'programs_found': len(programs_found),
                'modules_found': len(modules_found),
                'sample_programs': [(rec_id, name) for rec_id, name in programs_found[:20]],
                'sample_modules': [(rec_id, name) for rec_id, name in modules_found[:20]]
            }
            
            with open(Path(output_dir) / "parsing_results.json", 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n✅ Results saved to {output_dir}/parsing_results.json")
            
        except Exception as e:
            print(f"❌ Error parsing Comps.Dat: {e}")
            import traceback
            traceback.print_exc()
    
    # Step 3: Check TagInfo.XML
    print("\n📋 Step 3: Checking TagInfo.XML...")
    taginfo_file = db_dir / "TagInfo.XML"
    if taginfo_file.exists():
        # Read first part of TagInfo.XML
        with open(taginfo_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(5000)  # First 5KB
            
        print("  Sample of TagInfo.XML:")
        lines = content.split('\n')[:10]
        for line in lines:
            print(f"    {line[:100]}...")
        
        # Count tags
        with open(taginfo_file, 'rb') as f:
            content = f.read()
            tag_count = content.count(b'<Tag ')
            print(f"\n  Total tags found: {tag_count}")
    
    print("\n" + "="*60)
    print("✅ Parsing complete with workaround!")

if __name__ == "__main__":
    extract_and_parse_acd() 