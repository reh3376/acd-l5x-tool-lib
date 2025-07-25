#!/usr/bin/env python3
"""
Extract real ladder logic rungs from ACD using proper hutcheb/acd approach
"""

import os
import re
import sqlite3
import json
from pathlib import Path
from acd.api import ExtractAcdDatabase, ImportProjectFromFile
from acd.database.dbextract import DbExtract
from acd.record.sbregion import SbRegionRecord
from acd.record.comps import CompsRecord

class RealRungExtractor:
    def __init__(self, acd_file):
        self.acd_file = Path(acd_file)
        self.output_dir = Path("real_rungs_extracted")
        self.output_dir.mkdir(exist_ok=True)
        self.db_dir = self.output_dir / "databases"
        
    def extract(self):
        """Extract real rungs using hutcheb/acd approach"""
        print(f"\n🔍 Extracting real ladder logic rungs from {self.acd_file.name}")
        print("="*60)
        
        # Method 1: Try using ImportProjectFromFile with patch
        self.try_import_method()
        
        # Method 2: Manual extraction
        self.manual_extraction()
        
    def try_import_method(self):
        """Try using the hutcheb/acd import with our patch"""
        print("\n📋 Method 1: Using ImportProjectFromFile...")
        
        try:
            # Apply patch
            from patch_hutcheb_acd import patch_acd_library
            patch_acd_library()
            
            # Import project
            project = ImportProjectFromFile(str(self.acd_file)).import_project()
            
            if project and project.controller:
                controller = project.controller
                print(f"✅ Controller: {controller.name}")
                
                # Check for rungs
                total_rungs = 0
                sample_rungs = []
                
                if controller.programs:
                    for program in controller.programs:
                        if hasattr(program, 'routines') and program.routines:
                            for routine in program.routines:
                                if hasattr(routine, 'rungs') and routine.rungs:
                                    total_rungs += len(routine.rungs)
                                    
                                    # Save sample rungs
                                    for rung_idx, rung in enumerate(routine.rungs[:3]):
                                        sample_rungs.append({
                                            'program': program.name,
                                            'routine': routine.name,
                                            'index': rung_idx,
                                            'text': str(rung)
                                        })
                
                print(f"  Total rungs found: {total_rungs}")
                
                if sample_rungs:
                    print("\n  Sample rungs:")
                    for sample in sample_rungs[:5]:
                        print(f"    {sample['program']}.{sample['routine']}[{sample['index']}]: {sample['text']}")
                        
        except Exception as e:
            print(f"❌ Import method failed: {e}")
    
    def manual_extraction(self):
        """Manually extract rungs like hutcheb/acd does internally"""
        print("\n📋 Method 2: Manual extraction...")
        
        # Extract databases
        print("  Extracting databases...")
        ExtractAcdDatabase(str(self.acd_file), str(self.db_dir)).extract()
        
        # Create SQLite database
        db_file = self.output_dir / "extraction.db"
        if db_file.exists():
            os.remove(db_file)
            
        db = sqlite3.connect(str(db_file))
        cur = db.cursor()
        
        # Create tables
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
            CREATE TABLE rungs(
                object_id int,
                rung text,
                seq_number int
            )
        """)
        
        # Process Comps.Dat first (needed for tag resolution)
        print("  Processing Comps.Dat...")
        comps_file = self.db_dir / "Comps.Dat"
        comps_db = DbExtract(str(comps_file)).read()
        
        comps_count = 0
        for record in comps_db.records.record:
            try:
                CompsRecord(cur, record)
                comps_count += 1
            except:
                pass
                
        db.commit()
        print(f"    Loaded {comps_count} component records")
        
        # Process SbRegion.Dat for rungs
        print("  Processing SbRegion.Dat for rungs...")
        sbregion_file = self.db_dir / "SbRegion.Dat"
        sb_db = DbExtract(str(sbregion_file)).read()
        
        rungs_count = 0
        for record in sb_db.records.record:
            try:
                SbRegionRecord(cur, record)
                rungs_count += 1
            except:
                pass
                
        db.commit()
        
        # Query rungs
        cur.execute("SELECT COUNT(*) FROM rungs")
        total_rungs = cur.fetchone()[0]
        print(f"    Found {total_rungs} rungs!")
        
        # Get all rungs
        cur.execute("SELECT object_id, rung FROM rungs ORDER BY object_id")
        all_rungs = cur.fetchall()
        
        # Process and save rungs
        processed_rungs = []
        unique_rungs = set()
        
        for obj_id, rung_text in all_rungs:
            if rung_text and rung_text != "NOP();":
                unique_rungs.add(rung_text)
                processed_rungs.append({
                    'object_id': obj_id,
                    'text': rung_text,
                    'length': len(rung_text)
                })
        
        print(f"\n✅ Extracted {len(processed_rungs)} non-NOP rungs")
        print(f"   Unique rungs: {len(unique_rungs)}")
        
        # Show sample rungs
        if processed_rungs:
            print("\n📄 Sample rungs:")
            for i, rung in enumerate(processed_rungs[:10]):
                print(f"\n  Rung {i + 1} (ID: {rung['object_id']}):")
                # Show first 200 chars
                text = rung['text'][:200]
                if len(rung['text']) > 200:
                    text += "..."
                print(f"    {text}")
        
        # Save all rungs
        rungs_file = self.output_dir / "extracted_rungs_complete.json"
        with open(rungs_file, 'w') as f:
            json.dump(processed_rungs, f, indent=2)
        print(f"\n✅ All rungs saved to: {rungs_file}")
        
        # Analyze rung patterns
        self.analyze_rung_patterns(processed_rungs)
        
        db.close()
    
    def analyze_rung_patterns(self, rungs):
        """Analyze the extracted rungs"""
        print("\n📊 Analyzing rung patterns...")
        
        # Instruction frequency
        instruction_count = {}
        instructions = ['XIC', 'XIO', 'OTE', 'OTL', 'OTU', 'TON', 'TOF', 
                       'CTU', 'CTD', 'MOV', 'ADD', 'SUB', 'MUL', 'DIV',
                       'EQU', 'NEQ', 'LES', 'GRT', 'JSR', 'RET', 'MSG']
        
        for rung in rungs:
            text = rung['text']
            for inst in instructions:
                count = text.count(inst + '(')
                if count > 0:
                    instruction_count[inst] = instruction_count.get(inst, 0) + count
        
        if instruction_count:
            print("\n  Instruction usage:")
            for inst, count in sorted(instruction_count.items(), key=lambda x: x[1], reverse=True):
                print(f"    {inst}: {count} times")
        
        # Find complex rungs (multiple instructions)
        complex_rungs = []
        for rung in rungs:
            text = rung['text']
            # Count instructions
            inst_count = sum(1 for inst in instructions if inst + '(' in text)
            if inst_count > 1:
                complex_rungs.append({
                    'text': text,
                    'instruction_count': inst_count
                })
        
        print(f"\n  Complex rungs (multiple instructions): {len(complex_rungs)}")
        if complex_rungs:
            # Show most complex
            complex_rungs.sort(key=lambda x: x['instruction_count'], reverse=True)
            print(f"  Most complex rung has {complex_rungs[0]['instruction_count']} instructions")
            print(f"    Preview: {complex_rungs[0]['text'][:150]}...")

def main():
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    extractor = RealRungExtractor(acd_file)
    extractor.extract()

if __name__ == "__main__":
    main() 