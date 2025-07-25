#!/usr/bin/env python3
"""
Parse ACD and compare with L5X exports
"""

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

def parse_taginfo_xml(taginfo_path):
    """Parse TagInfo.XML to extract all program information"""
    
    with open(taginfo_path, 'r', encoding='utf-16', errors='ignore') as f:
        content = f.read()
    
    root = ET.fromstring(content)
    
    controller_info = {
        'name': root.get('Name'),
        'programs': [],
        'tags': [],
        'datatypes': [],
        'modules': []
    }
    
    # Extract Programs
    for program in root.findall('.//Program'):
        prog_info = {
            'name': program.get('Name'),
            'type': program.get('Type', 'Unknown'),
            'routines': []
        }
        
        # Get routines for this program
        for routine in program.findall('.//Routine'):
            prog_info['routines'].append({
                'name': routine.get('Name'),
                'type': routine.get('Type', 'Unknown')
            })
        
        controller_info['programs'].append(prog_info)
    
    # Extract Tags
    for tag in root.findall('.//Tag'):
        controller_info['tags'].append({
            'name': tag.get('Name'),
            'datatype': tag.get('DataType'),
            'scope': tag.get('Scope', 'Controller')
        })
    
    # Extract DataTypes
    for dt in root.findall('.//DataType'):
        controller_info['datatypes'].append({
            'name': dt.get('Name'),
            'family': dt.get('Family', 'Unknown')
        })
    
    return controller_info

def load_l5x_export_info():
    """Load information about our L5X exports"""
    
    analysis_file = "docs/exports/analysis_report.json"
    if Path(analysis_file).exists():
        with open(analysis_file, 'r') as f:
            return json.load(f)
    return {}

def compare_acd_with_exports():
    """Compare ACD extraction with L5X exports"""
    
    print("🔍 Comparing ACD Extraction with L5X Exports")
    print("="*60)
    
    # Parse TagInfo.XML
    taginfo_path = "acd_complete_parse/database_files/TagInfo.XML"
    if not Path(taginfo_path).exists():
        print("❌ TagInfo.XML not found. Run parse_acd_complete.py first.")
        return
    
    print("\n📋 Parsing ACD TagInfo.XML...")
    acd_info = parse_taginfo_xml(taginfo_path)
    
    print(f"✅ Controller: {acd_info['name']}")
    print(f"   Programs: {len(acd_info['programs'])}")
    print(f"   Tags: {len(acd_info['tags'])}")
    print(f"   DataTypes: {len(acd_info['datatypes'])}")
    
    # Load L5X export analysis
    print("\n📋 Loading L5X Export Analysis...")
    l5x_info = load_l5x_export_info()
    
    if l5x_info:
        print(f"✅ L5X Exports Found:")
        print(f"   Programs: {len(l5x_info.get('programs', {}))}")
        print(f"   Modules: {len(l5x_info.get('modules', {}))}")
        print(f"   AOIs: {len(l5x_info.get('aois', {}))}")
        print(f"   DataTypes: {len(l5x_info.get('data_types', {}))}")
    
    # Compare Programs
    print("\n📊 Program Comparison:")
    acd_programs = {p['name'] for p in acd_info['programs']}
    l5x_programs = set()
    
    # Extract program names from L5X analysis
    for prog_key in l5x_info.get('programs', {}):
        prog_name = prog_key.replace('_Program', '')
        l5x_programs.add(prog_name)
    
    print(f"\n  Programs in ACD: {len(acd_programs)}")
    print(f"  Programs in L5X exports: {len(l5x_programs)}")
    
    # Find matches and differences
    matched = acd_programs & l5x_programs
    acd_only = acd_programs - l5x_programs
    l5x_only = l5x_programs - acd_programs
    
    print(f"\n  ✅ Matched Programs: {len(matched)}")
    if matched:
        for prog in sorted(matched)[:10]:
            print(f"     - {prog}")
        if len(matched) > 10:
            print(f"     ... and {len(matched) - 10} more")
    
    if acd_only:
        print(f"\n  ⚠️  In ACD only: {len(acd_only)}")
        for prog in sorted(acd_only)[:5]:
            print(f"     - {prog}")
    
    if l5x_only:
        print(f"\n  ⚠️  In L5X only: {len(l5x_only)}")
        for prog in sorted(l5x_only)[:5]:
            print(f"     - {prog}")
    
    # Detailed program analysis
    print("\n📋 Detailed Program Analysis:")
    for i, program in enumerate(acd_info['programs'][:10]):
        print(f"\n  {i+1}. {program['name']}")
        print(f"     Type: {program['type']}")
        print(f"     Routines: {len(program['routines'])}")
        if program['routines']:
            for r in program['routines'][:3]:
                print(f"       - {r['name']} ({r['type']})")
            if len(program['routines']) > 3:
                print(f"       ... and {len(program['routines']) - 3} more")
    
    # Save comparison results
    comparison = {
        'controller_name': acd_info['name'],
        'acd_stats': {
            'programs': len(acd_info['programs']),
            'tags': len(acd_info['tags']),
            'datatypes': len(acd_info['datatypes'])
        },
        'l5x_stats': {
            'programs': len(l5x_programs),
            'modules': len(l5x_info.get('modules', {})),
            'aois': len(l5x_info.get('aois', {})),
            'datatypes': len(l5x_info.get('data_types', {}))
        },
        'comparison': {
            'matched_programs': len(matched),
            'acd_only_programs': len(acd_only),
            'l5x_only_programs': len(l5x_only),
            'matched_program_names': sorted(list(matched))
        }
    }
    
    output_file = "acd_l5x_comparison.json"
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2)
    
    print(f"\n✅ Comparison saved to {output_file}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY:")
    print(f"  ✅ Successfully parsed ACD file")
    print(f"  ✅ Found all {len(acd_programs)} programs in TagInfo.XML")
    print(f"  ✅ {len(matched)}/{len(acd_programs)} programs match L5X exports")
    print(f"  🎯 Ready for detailed data extraction!")

if __name__ == "__main__":
    compare_acd_with_exports() 