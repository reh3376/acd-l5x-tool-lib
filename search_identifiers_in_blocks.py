#!/usr/bin/env python3
"""
Search for L5X identifiers in extracted ACD blocks
"""

import os
import json
from pathlib import Path

def search_identifiers_in_blocks(blocks_dir, mapping_file):
    """Search for identifiers in extracted blocks"""
    
    # Load the mapping data
    with open(mapping_file, 'r') as f:
        mapping_data = json.load(f)
    
    # Get list of identifiers to search for
    identifiers = set()
    
    # Add program names
    for prog_data in mapping_data['mappings']['programs'].values():
        if 'name' in prog_data:
            identifiers.add(prog_data['name'])
    
    # Add routine names  
    for routine_data in mapping_data['mappings']['routines'].values():
        if 'name' in routine_data:
            identifiers.add(routine_data['name'])
            
    # Add module names
    for module_data in mapping_data['mappings']['modules'].values():
        if 'name' in module_data:
            identifiers.add(module_data['name'])
    
    # Get identifiers from the original extraction
    # Since the mapping is empty, let's get them from the analysis report
    analysis_file = Path("docs/exports/analysis_report.json")
    if analysis_file.exists():
        with open(analysis_file, 'r') as f:
            analysis_data = json.load(f)
            
        # Extract program names
        for prog_key in analysis_data.get('programs', {}):
            prog_name = prog_key.replace('_Program', '').replace('_', ' ')
            identifiers.add(prog_name)
            
            # Also add the original key
            identifiers.add(prog_key.replace('_Program', ''))
            
        # Extract module names
        for module_key in analysis_data.get('modules', {}):
            module_name = module_key.replace('_Module', '')
            identifiers.add(module_name)
    
    print(f"🔍 Searching for {len(identifiers)} identifiers in blocks...")
    
    results = {}
    
    # Search each block
    for block_file in Path(blocks_dir).glob("*.bin"):
        print(f"\n📦 Searching in {block_file.name}...")
        
        with open(block_file, 'rb') as f:
            block_data = f.read()
        
        block_results = {}
        
        # Search for each identifier
        for identifier in sorted(identifiers):
            if not identifier:
                continue
                
            # Try different encodings
            found = False
            
            # UTF-8
            try:
                search_bytes = identifier.encode('utf-8')
                if search_bytes in block_data:
                    count = block_data.count(search_bytes)
                    block_results[identifier] = {
                        'encoding': 'utf-8',
                        'count': count
                    }
                    found = True
                    print(f"  ✅ Found '{identifier}' ({count} times)")
            except:
                pass
            
            # UTF-16LE
            if not found:
                try:
                    search_bytes = identifier.encode('utf-16le')
                    if search_bytes in block_data:
                        count = block_data.count(search_bytes)
                        block_results[identifier] = {
                            'encoding': 'utf-16le',
                            'count': count
                        }
                        found = True
                        print(f"  ✅ Found '{identifier}' in UTF-16LE ({count} times)")
                except:
                    pass
        
        if block_results:
            results[block_file.name] = block_results
    
    # Save results
    output_file = Path("identifier_search_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to {output_file}")
    
    # Summary
    total_found = sum(len(block_results) for block_results in results.values())
    print(f"\n📊 Summary: Found {total_found} identifiers across {len(results)} blocks")

def main():
    blocks_dir = "extracted_blocks"
    mapping_file = "docs/exports/acd_l5x_mapping.json"
    
    search_identifiers_in_blocks(blocks_dir, mapping_file)

if __name__ == "__main__":
    main() 