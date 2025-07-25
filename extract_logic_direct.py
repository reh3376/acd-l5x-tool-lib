#!/usr/bin/env python3
"""
Extract ladder logic directly from ACD databases
"""

import os
import sqlite3
import json
from pathlib import Path
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract
from acd.record.sbregion import SbRegionRecord

class DirectLogicExtractor:
    def __init__(self, acd_file):
        self.acd_file = Path(acd_file)
        self.output_dir = Path("direct_logic_extraction")
        self.output_dir.mkdir(exist_ok=True)
        
        self.db_dir = self.output_dir / "databases"
        self.rungs = []
        self.programs = {}
        
    def extract(self):
        """Extract logic directly"""
        print(f"\n🔍 Direct extraction from {self.acd_file.name}")
        print("="*60)
        
        # Extract databases
        print("\n📋 Step 1: Extracting databases...")
        ExtractAcdDatabase(str(self.acd_file), str(self.db_dir)).extract()
        
        # Process SbRegion (contains rungs)
        self.process_sbregion()
        
        # Report results
        self.generate_report()
        
    def process_sbregion(self):
        """Process SbRegion.Dat which contains the rungs"""
        print("\n📋 Step 2: Processing SbRegion.Dat for rungs...")
        
        sbregion_file = self.db_dir / "SbRegion.Dat"
        if not sbregion_file.exists():
            print("❌ SbRegion.Dat not found")
            return
            
        try:
            # Create temp database
            temp_db = self.output_dir / "rungs.db"
            if temp_db.exists():
                os.remove(temp_db)
                
            db = sqlite3.connect(str(temp_db))
            cur = db.cursor()
            
            # Create rungs table
            cur.execute("CREATE TABLE rungs(object_id int, rung text, seq_number int)")
            
            # Read SbRegion
            sb_db = DbExtract(str(sbregion_file)).read()
            print(f"  Found {len(sb_db.records.record)} records in SbRegion")
            
            # Process records
            rung_count = 0
            for i, record in enumerate(sb_db.records.record):
                if i % 500 == 0:
                    print(f"    Progress: {i}/{len(sb_db.records.record)}")
                    
                try:
                    # Let SbRegionRecord process it
                    SbRegionRecord(cur, record)
                except:
                    # Skip errors
                    pass
                    
            db.commit()
            
            # Query for rungs
            cur.execute("SELECT COUNT(*) FROM rungs")
            total_rungs = cur.fetchone()[0]
            print(f"\n✅ Found {total_rungs} rungs!")
            
            # Get sample rungs
            cur.execute("SELECT object_id, rung FROM rungs LIMIT 20")
            sample_rungs = cur.fetchall()
            
            if sample_rungs:
                print("\n📄 Sample rungs:")
                for i, (obj_id, rung_text) in enumerate(sample_rungs[:10]):
                    print(f"\n  Rung {i + 1} (Object ID: {obj_id}):")
                    print(f"    {rung_text[:200]}{'...' if len(rung_text) > 200 else ''}")
                    
                    # Save full rung
                    self.rungs.append({
                        'object_id': obj_id,
                        'text': rung_text
                    })
            
            # Get all rungs for output
            cur.execute("SELECT object_id, rung FROM rungs")
            all_rungs = cur.fetchall()
            
            # Save all rungs
            rungs_file = self.output_dir / "extracted_rungs.json"
            with open(rungs_file, 'w') as f:
                json.dump([{'object_id': r[0], 'text': r[1]} for r in all_rungs], f, indent=2)
                
            print(f"\n✅ All {len(all_rungs)} rungs saved to: {rungs_file}")
            
            db.close()
            
        except Exception as e:
            print(f"❌ Error processing SbRegion: {e}")
            import traceback
            traceback.print_exc()
    
    def generate_report(self):
        """Generate extraction report"""
        report = {
            'acd_file': str(self.acd_file),
            'rungs_extracted': len(self.rungs),
            'sample_rungs': self.rungs[:5]
        }
        
        report_file = self.output_dir / "direct_extraction_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\n📊 Report saved to: {report_file}")

def main():
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    extractor = DirectLogicExtractor(acd_file)
    extractor.extract()

if __name__ == "__main__":
    main() 