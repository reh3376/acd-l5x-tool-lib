#!/usr/bin/env python3
"""
Extract complete ladder logic from ACD Comps.Dat
"""

import os
import sqlite3
import json
from pathlib import Path
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract
from acd.record.comps import CompsRecord

class CompleteLogicExtractor:
    def __init__(self, acd_file):
        self.acd_file = Path(acd_file)
        self.output_dir = Path("complete_logic_extraction")
        self.output_dir.mkdir(exist_ok=True)
        
        self.db_dir = self.output_dir / "databases"
        self.programs = {}
        self.routines = {}
        self.rungs = {}
        self.modules = {}
        
    def extract(self):
        """Extract complete logic from ACD"""
        print(f"\n🔍 Extracting complete logic from {self.acd_file.name}")
        print("="*60)
        
        # Extract databases
        if not self.extract_databases():
            return False
            
        # Process Comps database completely
        if not self.process_comps_complete():
            return False
            
        # Generate report
        self.generate_report()
        
        return True
    
    def extract_databases(self):
        """Extract ACD databases"""
        print("\n📋 Step 1: Extracting databases...")
        try:
            ExtractAcdDatabase(str(self.acd_file), str(self.db_dir)).extract()
            print("✅ Databases extracted")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def process_comps_complete(self):
        """Process entire Comps database"""
        print("\n📋 Step 2: Processing complete Comps database...")
        
        try:
            # Create SQLite database for queries
            temp_db = self.output_dir / "comps_complete.db"
            if temp_db.exists():
                os.remove(temp_db)
                
            db = sqlite3.connect(str(temp_db))
            cur = db.cursor()
            
            # Create tables with proper schema
            cur.execute("""
                CREATE TABLE comps(
                    object_id int PRIMARY KEY,
                    parent_id int,
                    comp_name text,
                    seq_number int,
                    record_type int,
                    record BLOB NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE pointers(
                    object_id int,
                    parent_id int,
                    comp_name text,
                    seq_number int,
                    record_type int,
                    record BLOB NOT NULL
                )
            """)
            
            cur.execute("CREATE TABLE rungs (unk1 INTEGER, unk2 INTEGER, text TEXT);")
            
            # Read Comps.Dat
            comps_file = self.db_dir / "Comps.Dat"
            print(f"  Reading {comps_file.name}...")
            comps_db = DbExtract(str(comps_file)).read()
            
            total_records = len(comps_db.records.record)
            print(f"  Processing {total_records} records...")
            
            # Process ALL records
            processed = 0
            programs_found = 0
            routines_found = 0
            rungs_found = 0
            modules_found = 0
            
            for i, record in enumerate(comps_db.records.record):
                if i % 1000 == 0:
                    print(f"    Progress: {i}/{total_records} ({i*100//total_records}%)")
                
                try:
                    # Let CompsRecord parse it
                    comp = CompsRecord(cur, record)
                    processed += 1
                    
                    # The record is now in the database, query for details
                    if hasattr(record, 'record') and hasattr(record.record, 'comps_record'):
                        comp_rec = record.record.comps_record
                        
                        if hasattr(comp_rec, 'header'):
                            header = comp_rec.header
                            comp_name = header.record_name.value if hasattr(header.record_name, 'value') else None
                            record_type = header.record_type if hasattr(header, 'record_type') else None
                            
                            # Check for different component types
                            if record_type == 89:  # Program
                                programs_found += 1
                                self.programs[header.object_id] = {
                                    'name': comp_name,
                                    'parent_id': header.parent_id
                                }
                            elif record_type == 66:  # Routine
                                routines_found += 1
                                self.routines[header.object_id] = {
                                    'name': comp_name,
                                    'parent_id': header.parent_id
                                }
                            elif record_type == 4:  # Module
                                modules_found += 1
                                self.modules[header.object_id] = {
                                    'name': comp_name,
                                    'parent_id': header.parent_id
                                }
                            
                            # Check for ladder logic
                            if hasattr(comp_rec, 'comps_record_type_specific'):
                                specific = comp_rec.comps_record_type_specific
                                
                                # Look for routine content
                                if hasattr(specific, 'body') and hasattr(specific.body, 'routine_body'):
                                    routine_body = specific.body.routine_body
                                    
                                    # Check for RLL content
                                    if hasattr(routine_body, 'rll_body') and routine_body.rll_body:
                                        rll = routine_body.rll_body
                                        
                                        # Extract rungs
                                        if hasattr(rll, 'body') and hasattr(rll.body, 'rungs'):
                                            for rung in rll.body.rungs:
                                                if hasattr(rung, 'text'):
                                                    rungs_found += 1
                                                    # Store rung text
                                                    cur.execute(
                                                        "INSERT INTO rungs (unk1, unk2, text) VALUES (?, ?, ?)",
                                                        (header.object_id, rungs_found, rung.text)
                                                    )
                
                except Exception as e:
                    # Skip problematic records
                    pass
            
            db.commit()
            
            print(f"\n✅ Processing complete!")
            print(f"   Total records: {total_records}")
            print(f"   Processed: {processed}")
            print(f"   Programs: {programs_found}")
            print(f"   Routines: {routines_found}")
            print(f"   Rungs: {rungs_found}")
            print(f"   Modules: {modules_found}")
            
            # Query for actual content
            print("\n📋 Step 3: Extracting ladder logic...")
            
            # Get programs with their names
            cur.execute("SELECT DISTINCT comp_name FROM comps WHERE record_type = 89")
            program_names = [row[0] for row in cur.fetchall()]
            print(f"  Programs: {', '.join(program_names[:10])}...")
            
            # Get rungs
            cur.execute("SELECT COUNT(*) FROM rungs")
            rung_count = cur.fetchone()[0]
            print(f"  Total rungs in database: {rung_count}")
            
            # Sample some rungs
            cur.execute("SELECT text FROM rungs LIMIT 5")
            sample_rungs = cur.fetchall()
            if sample_rungs:
                print("\n  Sample rungs:")
                for i, (rung_text,) in enumerate(sample_rungs):
                    print(f"    Rung {i}: {rung_text[:100]}...")
            
            # Get modules
            cur.execute("SELECT DISTINCT comp_name FROM comps WHERE record_type = 4")
            module_names = [row[0] for row in cur.fetchall() if row[0]]
            if module_names:
                print(f"\n  Modules: {', '.join(module_names[:10])}...")
            
            db.close()
            return True
            
        except Exception as e:
            print(f"❌ Error processing Comps: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_report(self):
        """Generate extraction report"""
        report = {
            'acd_file': str(self.acd_file),
            'extraction_complete': True,
            'components': {
                'programs': len(self.programs),
                'routines': len(self.routines),
                'rungs': len(self.rungs),
                'modules': len(self.modules)
            },
            'status': 'Complete ladder logic extraction attempted'
        }
        
        report_file = self.output_dir / "complete_extraction_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\n📊 Report saved to: {report_file}")

def main():
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    extractor = CompleteLogicExtractor(acd_file)
    extractor.extract()

if __name__ == "__main__":
    main() 