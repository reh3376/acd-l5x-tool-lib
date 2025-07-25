#!/usr/bin/env python3
"""
L5X Export Analyzer
Analyzes the complete set of L5X exports to understand structure and content
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
import json
from collections import defaultdict

class L5XExportAnalyzer:
    def __init__(self, export_dir):
        self.export_dir = Path(export_dir)
        self.analysis_results = {
            'modules': {},
            'programs': {},
            'data_types': {},
            'aois': {},
            'statistics': {
                'total_files': 0,
                'total_size_mb': 0,
                'file_types': defaultdict(int)
            }
        }
    
    def analyze_all_exports(self):
        """Analyze all L5X files in the export directory"""
        print(f"🔍 Analyzing exports in: {self.export_dir}")
        
        for l5x_file in self.export_dir.glob("*.L5X"):
            self.analysis_results['statistics']['total_files'] += 1
            self.analysis_results['statistics']['total_size_mb'] += l5x_file.stat().st_size / 1024 / 1024
            
            # Categorize file type
            if '_Module.L5X' in l5x_file.name:
                self.analyze_module(l5x_file)
            elif '_Program.L5X' in l5x_file.name:
                self.analyze_program(l5x_file)
            elif '_DataType' in l5x_file.name:
                self.analyze_datatype(l5x_file)
            elif '_AOI.L5X' in l5x_file.name:
                self.analyze_aoi(l5x_file)
    
    def analyze_module(self, file_path):
        """Analyze a module export file"""
        print(f"  📦 Module: {file_path.name}")
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            module_info = {
                'file_name': file_path.name,
                'size_kb': file_path.stat().st_size / 1024,
                'schema_revision': root.get('SchemaRevision'),
                'software_revision': root.get('SoftwareRevision'),
                'modules': []
            }
            
            # Extract module details
            for module in root.findall('.//Module'):
                module_data = {
                    'name': module.get('Name'),
                    'catalog_number': module.get('CatalogNumber'),
                    'vendor': module.get('Vendor'),
                    'product_type': module.get('ProductType'),
                    'product_code': module.get('ProductCode'),
                    'major': module.get('Major'),
                    'minor': module.get('Minor')
                }
                module_info['modules'].append(module_data)
            
            self.analysis_results['modules'][file_path.stem] = module_info
            self.analysis_results['statistics']['file_types']['module'] += 1
            
        except Exception as e:
            print(f"    ⚠️  Error analyzing {file_path.name}: {e}")
    
    def analyze_program(self, file_path):
        """Analyze a program export file"""
        print(f"  📋 Program: {file_path.name}")
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            program_info = {
                'file_name': file_path.name,
                'size_mb': file_path.stat().st_size / 1024 / 1024,
                'target_name': root.get('TargetName'),
                'routines': [],
                'tags': 0,
                'data_types': []
            }
            
            # Count routines
            for routine in root.findall('.//Routine'):
                routine_data = {
                    'name': routine.get('Name'),
                    'type': routine.get('Type', 'Unknown')
                }
                program_info['routines'].append(routine_data)
            
            # Count tags
            program_info['tags'] = len(root.findall('.//Tag'))
            
            # Find data types used
            for dt in root.findall('.//DataType'):
                program_info['data_types'].append(dt.get('Name'))
            
            self.analysis_results['programs'][file_path.stem] = program_info
            self.analysis_results['statistics']['file_types']['program'] += 1
            
        except Exception as e:
            print(f"    ⚠️  Error analyzing {file_path.name}: {e}")
    
    def analyze_datatype(self, file_path):
        """Analyze a data type export file"""
        print(f"  📊 DataType: {file_path.name}")
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            dt_info = {
                'file_name': file_path.name,
                'size_kb': file_path.stat().st_size / 1024,
                'data_types': []
            }
            
            for dt in root.findall('.//DataType'):
                dt_data = {
                    'name': dt.get('Name'),
                    'family': dt.get('Family'),
                    'class': dt.get('Class'),
                    'members': []
                }
                
                for member in dt.findall('.//Member'):
                    dt_data['members'].append({
                        'name': member.get('Name'),
                        'data_type': member.get('DataType'),
                        'dimension': member.get('Dimension', '0')
                    })
                
                dt_info['data_types'].append(dt_data)
            
            self.analysis_results['data_types'][file_path.stem] = dt_info
            self.analysis_results['statistics']['file_types']['datatype'] += 1
            
        except Exception as e:
            print(f"    ⚠️  Error analyzing {file_path.name}: {e}")
    
    def analyze_aoi(self, file_path):
        """Analyze an Add-On Instruction export file"""
        print(f"  🔧 AOI: {file_path.name}")
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            aoi_info = {
                'file_name': file_path.name,
                'size_kb': file_path.stat().st_size / 1024,
                'aois': []
            }
            
            for aoi in root.findall('.//AddOnInstructionDefinition'):
                aoi_data = {
                    'name': aoi.get('Name'),
                    'revision': aoi.get('Revision'),
                    'vendor': aoi.get('Vendor'),
                    'parameters': [],
                    'local_tags': []
                }
                
                # Get parameters
                for param in aoi.findall('.//Parameter'):
                    aoi_data['parameters'].append({
                        'name': param.get('Name'),
                        'tag_type': param.get('TagType'),
                        'data_type': param.get('DataType')
                    })
                
                # Get local tags
                for tag in aoi.findall('.//LocalTag'):
                    aoi_data['local_tags'].append({
                        'name': tag.get('Name'),
                        'data_type': tag.get('DataType')
                    })
                
                aoi_info['aois'].append(aoi_data)
            
            self.analysis_results['aois'][file_path.stem] = aoi_info
            self.analysis_results['statistics']['file_types']['aoi'] += 1
            
        except Exception as e:
            print(f"    ⚠️  Error analyzing {file_path.name}: {e}")
    
    def generate_report(self):
        """Generate analysis report"""
        print("\n📊 Analysis Summary:")
        print(f"Total files: {self.analysis_results['statistics']['total_files']}")
        print(f"Total size: {self.analysis_results['statistics']['total_size_mb']:.2f} MB")
        print("\nFile types:")
        for file_type, count in self.analysis_results['statistics']['file_types'].items():
            print(f"  - {file_type}: {count}")
        
        # Program statistics
        total_routines = 0
        total_tags = 0
        for prog_name, prog_info in self.analysis_results['programs'].items():
            total_routines += len(prog_info['routines'])
            total_tags += prog_info['tags']
        
        print(f"\nProgram statistics:")
        print(f"  - Total programs: {len(self.analysis_results['programs'])}")
        print(f"  - Total routines: {total_routines}")
        print(f"  - Total tags: {total_tags}")
        
        # Save detailed report
        report_file = self.export_dir / "analysis_report.json"
        with open(report_file, 'w') as f:
            json.dump(self.analysis_results, f, indent=2)
        print(f"\n✅ Detailed report saved to: {report_file}")

def main():
    export_dir = "docs/exports"
    analyzer = L5XExportAnalyzer(export_dir)
    analyzer.analyze_all_exports()
    analyzer.generate_report()

if __name__ == "__main__":
    main() 