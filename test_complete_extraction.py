#!/usr/bin/env python3
"""
Test complete extraction using hutcheb/acd ImportProjectFromFile
"""

from pathlib import Path
from acd.api import ImportProjectFromFile
import json

def test_extraction():
    """Test if hutcheb/acd extracts ladder logic"""
    
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    print(f"\n🔍 Testing complete extraction of {acd_file}")
    print("="*60)
    
    # Apply patch to skip Comments
    from patch_hutcheb_acd import patch_acd_library
    patch_acd_library()
    
    try:
        print("\n📋 Importing project...")
        project = ImportProjectFromFile(acd_file).import_project()
        
        if not project or not project.controller:
            print("❌ Failed to import project")
            return
            
        controller = project.controller
        print(f"✅ Controller: {controller.name}")
        
        # Check what we actually got
        total_rungs = 0
        programs_with_logic = []
        sample_rungs = []
        
        if controller.programs:
            print(f"\n📊 Analyzing {len(controller.programs)} programs...")
            
            for prog_idx, program in enumerate(controller.programs):
                print(f"\n  Program {prog_idx + 1}: {program.name}")
                
                if hasattr(program, 'routines') and program.routines:
                    print(f"    Routines: {len(program.routines)}")
                    
                    for routine_idx, routine in enumerate(program.routines):
                        print(f"      Routine: {routine.name} (Type: {getattr(routine, 'type', 'Unknown')})")
                        
                        # Check for rungs
                        if hasattr(routine, 'rungs') and routine.rungs:
                            rung_count = len(routine.rungs)
                            total_rungs += rung_count
                            print(f"        ✅ Rungs: {rung_count}")
                            programs_with_logic.append(program.name)
                            
                            # Sample first rung
                            if sample_rungs < 5 and routine.rungs:
                                for rung_idx, rung in enumerate(routine.rungs[:2]):
                                    sample_rungs.append({
                                        'program': program.name,
                                        'routine': routine.name,
                                        'rung_index': rung_idx,
                                        'content': str(rung)[:200]  # First 200 chars
                                    })
                                    print(f"        Sample rung {rung_idx}: {str(rung)[:100]}...")
                        else:
                            print(f"        ❌ No rungs found")
                else:
                    print(f"    No routines found")
        
        # Summary
        print("\n" + "="*60)
        print("📊 EXTRACTION SUMMARY:")
        print(f"  Total rungs found: {total_rungs}")
        print(f"  Programs with logic: {len(set(programs_with_logic))}")
        
        if sample_rungs:
            print("\n📄 Sample Rungs:")
            for i, sample in enumerate(sample_rungs[:5]):
                print(f"\n  Sample {i + 1}:")
                print(f"    Program: {sample['program']}")
                print(f"    Routine: {sample['routine']}")
                print(f"    Content: {sample['content']}")
        
        # Save results
        results = {
            'controller': controller.name,
            'total_programs': len(controller.programs) if controller.programs else 0,
            'total_rungs': total_rungs,
            'programs_with_logic': list(set(programs_with_logic)),
            'sample_rungs': sample_rungs
        }
        
        with open('complete_extraction_test.json', 'w') as f:
            json.dump(results, f, indent=2)
            
        print(f"\n✅ Results saved to complete_extraction_test.json")
        
        return total_rungs > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = test_extraction()
    
    if success:
        print("\n🎉 SUCCESS: Ladder logic found!")
    else:
        print("\n❌ FAILED: No ladder logic extracted")

if __name__ == "__main__":
    main() 