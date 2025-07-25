#!/usr/bin/env python3
"""
Test the hutcheb/acd library with our ACD file
"""

from acd.api import ImportProjectFromFile, ExtractAcdDatabase, ExtractAcdDatabaseRecordsToFiles, DumpCompsRecordsToFile
import json
from pathlib import Path

def test_acd_parsing():
    """Test parsing ACD file with hutcheb/acd library"""
    
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    output_dir = "hutcheb_acd_output"
    
    print(f"🔍 Testing hutcheb/acd library with: {acd_file}")
    print("="*60)
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    try:
        # Test 1: Import project from ACD file
        print("\n📋 Test 1: Importing project from ACD file...")
        project = ImportProjectFromFile(acd_file).import_project()
        
        if project.controller:
            controller = project.controller
            print(f"✅ Controller Name: {controller.name}")
            print(f"   Processor Type: {controller.processor_type}")
            print(f"   Major Revision: {controller.major_revision}")
            print(f"   Minor Revision: {controller.minor_revision}")
            
            # Count components
            print(f"\n📊 Component Counts:")
            print(f"   Programs: {len(controller.programs) if controller.programs else 0}")
            print(f"   Data Types: {len(controller.data_types) if controller.data_types else 0}")
            print(f"   Modules: {len(controller.modules) if controller.modules else 0}")
            print(f"   Tags: {len(controller.tags) if controller.tags else 0}")
            
            # List programs
            if controller.programs:
                print(f"\n📁 Programs found:")
                for i, program in enumerate(controller.programs[:10]):  # First 10
                    print(f"   {i+1}. {program.name}")
                    if hasattr(program, 'routines') and program.routines:
                        print(f"      - Routines: {len(program.routines)}")
                if len(controller.programs) > 10:
                    print(f"   ... and {len(controller.programs) - 10} more")
            
            # Save controller info
            controller_info = {
                'name': controller.name,
                'processor_type': controller.processor_type,
                'major_revision': controller.major_revision,
                'minor_revision': controller.minor_revision,
                'program_count': len(controller.programs) if controller.programs else 0,
                'programs': [p.name for p in (controller.programs or [])],
                'data_type_count': len(controller.data_types) if controller.data_types else 0,
                'module_count': len(controller.modules) if controller.modules else 0,
                'tag_count': len(controller.tags) if controller.tags else 0
            }
            
            with open(Path(output_dir) / "controller_info.json", 'w') as f:
                json.dump(controller_info, f, indent=2)
            print(f"\n✅ Controller info saved to {output_dir}/controller_info.json")
        else:
            print("❌ No controller found in project")
            
    except Exception as e:
        print(f"❌ Error importing project: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        # Test 2: Extract ACD database files
        print("\n📋 Test 2: Extracting ACD database files...")
        extract_db_dir = Path(output_dir) / "database_files"
        ExtractAcdDatabase(acd_file, extract_db_dir).extract()
        print(f"✅ Database files extracted to {extract_db_dir}")
        
        # List extracted files
        db_files = list(extract_db_dir.glob("*"))
        if db_files:
            print(f"\n📁 Extracted {len(db_files)} database files:")
            for db_file in db_files[:10]:
                print(f"   - {db_file.name} ({db_file.stat().st_size:,} bytes)")
            if len(db_files) > 10:
                print(f"   ... and {len(db_files) - 10} more")
                
    except Exception as e:
        print(f"❌ Error extracting database: {e}")
    
    try:
        # Test 3: Extract database records
        print("\n📋 Test 3: Extracting database records to files...")
        records_dir = Path(output_dir) / "database_records"
        ExtractAcdDatabaseRecordsToFiles(acd_file, records_dir).extract()
        print(f"✅ Database records extracted to {records_dir}")
        
    except Exception as e:
        print(f"❌ Error extracting records: {e}")
    
    try:
        # Test 4: Dump Comps records
        print("\n📋 Test 4: Dumping Comps database records...")
        comps_dir = Path(output_dir) / "comps_dump"
        comps_dir.mkdir(exist_ok=True)
        DumpCompsRecordsToFile(acd_file, comps_dir).extract()
        print(f"✅ Comps records dumped to {comps_dir}")
        
    except Exception as e:
        print(f"❌ Error dumping Comps records: {e}")
    
    print("\n" + "="*60)
    print("✅ Testing complete! Check the output directory for results.")

if __name__ == "__main__":
    test_acd_parsing() 