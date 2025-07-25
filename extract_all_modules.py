#!/usr/bin/env python3
"""
Extract ALL module configurations from ACD using L5X exports and comprehensive record analysis
"""

import os
import sqlite3
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract
from acd.record.comps import CompsRecord

class ComprehensiveModuleExtractor:
    def __init__(self, acd_file):
        self.acd_file = Path(acd_file)
        self.output_dir = Path("all_modules_extracted")
        self.output_dir.mkdir(exist_ok=True)
        self.db_dir = self.output_dir / "databases"
        self.exports_dir = Path("docs/exports")
        
    def extract(self):
        """Extract all module configurations comprehensively"""
        print(f"\n🔍 Comprehensive Module Extraction from {self.acd_file.name}")
        print("="*60)
        
        all_modules = {}
        
        # Step 1: Parse L5X module exports
        print("\n📋 Step 1: Parsing L5X module exports...")
        l5x_modules = self.parse_l5x_exports()
        all_modules.update(l5x_modules)
        
        # Step 2: Extract from ACD databases
        print("\n📋 Step 2: Extracting from ACD databases...")
        acd_modules = self.extract_from_acd()
        
        # Merge with L5X data
        for name, module in acd_modules.items():
            if name in all_modules:
                # Merge data
                all_modules[name].update(module)
            else:
                all_modules[name] = module
        
        # Step 3: Analyze and generate complete L5X
        print("\n📋 Step 3: Generating complete L5X with modules...")
        self.create_final_l5x(all_modules)
        
    def parse_l5x_exports(self):
        """Parse all L5X module export files"""
        modules = {}
        
        # Find all module L5X files
        module_files = list(self.exports_dir.glob("*_Module.L5X"))
        print(f"  Found {len(module_files)} module export files")
        
        for module_file in module_files:
            try:
                tree = ET.parse(module_file)
                root = tree.getroot()
                
                # Find the module element
                module_elem = root.find(".//Module[@Use='Target']")
                if module_elem is not None:
                    name = module_elem.get('Name')
                    if name:
                        module_config = {
                            'name': name,
                            'catalog_number': module_elem.get('CatalogNumber'),
                            'vendor': module_elem.get('Vendor'),
                            'product_type': module_elem.get('ProductType'),
                            'product_code': module_elem.get('ProductCode'),
                            'major_rev': module_elem.get('Major'),
                            'minor_rev': module_elem.get('Minor'),
                            'parent_module': module_elem.get('ParentModule'),
                            'parent_port': module_elem.get('ParentModPortId'),
                            'inhibited': module_elem.get('Inhibited'),
                            'major_fault': module_elem.get('MajorFault'),
                            'safety_enabled': module_elem.get('SafetyEnabled'),
                            'source': 'L5X Export',
                            'file': module_file.name
                        }
                        
                        # Parse EKey
                        ekey = module_elem.find('EKey')
                        if ekey is not None:
                            module_config['ekey_state'] = ekey.get('State')
                        
                        # Parse Ports
                        ports = []
                        for port in module_elem.findall('.//Port'):
                            port_info = {
                                'id': port.get('Id'),
                                'address': port.get('Address'),
                                'type': port.get('Type'),
                                'upstream': port.get('Upstream')
                            }
                            ports.append(port_info)
                        
                        if ports:
                            module_config['ports'] = ports
                        
                        # Parse Configuration
                        config_tag = module_elem.find('.//ConfigTag')
                        if config_tag is not None:
                            module_config['config_size'] = config_tag.get('ConfigSize')
                            module_config['external_access'] = config_tag.get('ExternalAccess')
                            
                            # Get configuration data
                            data_elem = config_tag.find('.//Data[@Format="L5K"]')
                            if data_elem is not None and data_elem.text:
                                module_config['config_data'] = data_elem.text.strip()
                        
                        # Parse Connection
                        connection = module_elem.find('.//Connection')
                        if connection is not None:
                            module_config['connection'] = {
                                'name': connection.get('Name'),
                                'rpi': connection.get('RPI'),
                                'type': connection.get('Type'),
                                'input_connection_type': connection.get('InputConnectionType'),
                                'input_size': connection.get('InputSize'),
                                'output_size': connection.get('OutputSize')
                            }
                        
                        modules[name] = module_config
                        print(f"    Parsed module: {name} ({module_config['catalog_number']})")
                
            except Exception as e:
                print(f"    Error parsing {module_file.name}: {e}")
        
        print(f"  Total modules from L5X: {len(modules)}")
        return modules
    
    def extract_from_acd(self):
        """Extract module info from ACD databases"""
        print("  Extracting databases...")
        ExtractAcdDatabase(str(self.acd_file), str(self.db_dir)).extract()
        
        modules = {}
        
        # Create SQLite database
        db_file = self.output_dir / "comprehensive.db"
        if db_file.exists():
            os.remove(db_file)
            
        db = sqlite3.connect(str(db_file))
        cur = db.cursor()
        
        # Create table
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
        
        # Load Comps.Dat
        comps_file = self.db_dir / "Comps.Dat"
        comps_db = DbExtract(str(comps_file)).read()
        
        for record in comps_db.records.record:
            try:
                CompsRecord(cur, record)
            except:
                pass
                
        db.commit()
        
        # Look for modules in various record types
        print("  Searching all record types for modules...")
        
        # Check all record types
        cur.execute("SELECT DISTINCT record_type, COUNT(*) FROM comps GROUP BY record_type ORDER BY record_type")
        record_type_counts = cur.fetchall()
        
        print("    Record type distribution:")
        for record_type, count in record_type_counts:
            print(f"      Type {record_type}: {count} records")
        
        # Look for records that might be modules (not just type 4)
        # Type 4 is definitely modules, but there might be others
        potential_module_types = [4, 16, 32, 64, 128]  # Common module types
        
        all_potential_modules = []
        for module_type in potential_module_types:
            cur.execute("SELECT object_id, comp_name, parent_id FROM comps WHERE record_type = ?", (module_type,))
            records = cur.fetchall()
            if records:
                print(f"    Found {len(records)} potential modules in type {module_type}")
                all_potential_modules.extend([(r[0], r[1], r[2], module_type) for r in records])
        
        # Also look for records with module-like names
        cur.execute("SELECT object_id, comp_name, parent_id, record_type FROM comps WHERE comp_name LIKE '%MODULE%' OR comp_name LIKE '%IO%' OR comp_name LIKE '%DI_%' OR comp_name LIKE '%DO_%' OR comp_name LIKE '%AI_%' OR comp_name LIKE '%AO_%'")
        name_based_modules = cur.fetchall()
        print(f"    Found {len(name_based_modules)} records with module-like names")
        
        # Combine all potential modules
        all_candidates = set(all_potential_modules + name_based_modules)
        
        for obj_id, name, parent_id, record_type in all_candidates:
            if name and name.strip():  # Skip empty names
                modules[name] = {
                    'object_id': obj_id,
                    'name': name,
                    'parent_id': parent_id,
                    'record_type': record_type,
                    'source': 'ACD Database'
                }
        
        print(f"  Total potential modules from ACD: {len(modules)}")
        
        db.close()
        return modules
    
    def create_final_l5x(self, all_modules):
        """Create the final complete L5X file with all components"""
        print(f"\n📋 Creating final complete L5X file...")
        print(f"  Total modules to include: {len(all_modules)}")
        
        # Load rungs
        rungs_file = Path("real_rungs_extracted/extracted_rungs_complete.json")
        rungs_data = []
        if rungs_file.exists():
            with open(rungs_file, 'r') as f:
                rungs_data = json.load(f)
            print(f"  Loaded {len(rungs_data)} rungs")
        
        # Load tags from simple converter
        simple_l5x = Path("simple_l5x_output/PLC100_Mashing.L5X")
        existing_tags = []
        existing_datatypes = []
        existing_programs = []
        
        if simple_l5x.exists():
            try:
                tree = ET.parse(simple_l5x)
                root = tree.getroot()
                
                # Extract existing tags
                for tag in root.findall('.//Tag'):
                    existing_tags.append(tag)
                print(f"  Loaded {len(existing_tags)} existing tags")
                
                # Extract existing data types
                for dt in root.findall('.//DataType'):
                    existing_datatypes.append(dt)
                print(f"  Loaded {len(existing_datatypes)} existing data types")
                
                # Extract existing programs
                for prog in root.findall('.//Program'):
                    existing_programs.append(prog)
                print(f"  Loaded {len(existing_programs)} existing programs")
                
            except Exception as e:
                print(f"  Warning: Could not parse existing L5X: {e}")
        
        # Create comprehensive L5X structure
        root = ET.Element("RSLogix5000Content")
        root.set("SchemaRevision", "1.0")
        root.set("SoftwareRevision", "35.01")
        root.set("TargetName", "PLC100_Mashing")
        root.set("TargetType", "Controller")
        root.set("TargetRevision", "35.01")
        root.set("TargetLastEdited", "2025-01-01T00:00:00.000Z")
        root.set("ContainsContext", "true")
        
        # Controller
        controller = ET.SubElement(root, "Controller")
        controller.set("Use", "Context")
        controller.set("Name", "PLC100_Mashing")
        controller.set("ProcessorType", "1756-L85E")
        controller.set("MajorRev", "35")
        controller.set("MinorRev", "1")
        controller.set("TimeSlice", "20")
        controller.set("ShareUnusedTimeSlice", "1")
        
        # Add standard sections
        self.add_standard_sections(controller)
        
        # DataTypes
        datatypes_elem = ET.SubElement(controller, "DataTypes")
        for dt in existing_datatypes:
            datatypes_elem.append(dt)
        
        # Modules section with full configurations
        modules_elem = ET.SubElement(controller, "Modules")
        
        for name, module in all_modules.items():
            module_elem = ET.SubElement(modules_elem, "Module")
            module_elem.set("Name", name)
            module_elem.set("CatalogNumber", module.get('catalog_number', 'Generic'))
            module_elem.set("Vendor", str(module.get('vendor', '1')))
            module_elem.set("ProductType", str(module.get('product_type', '0')))
            module_elem.set("ProductCode", str(module.get('product_code', '0')))
            module_elem.set("Major", str(module.get('major_rev', '1')))
            module_elem.set("Minor", str(module.get('minor_rev', '0')))
            module_elem.set("ParentModule", module.get('parent_module', 'Local'))
            module_elem.set("ParentModPortId", str(module.get('parent_port', '1')))
            module_elem.set("Inhibited", module.get('inhibited', 'false'))
            module_elem.set("MajorFault", module.get('major_fault', 'false'))
            
            # Add EKey
            ekey = ET.SubElement(module_elem, "EKey")
            ekey.set("State", module.get('ekey_state', 'CompatibleModule'))
            
            # Add Ports if available
            if 'ports' in module:
                ports_elem = ET.SubElement(module_elem, "Ports")
                for port in module['ports']:
                    port_elem = ET.SubElement(ports_elem, "Port")
                    port_elem.set("Id", str(port.get('id', '1')))
                    port_elem.set("Address", str(port.get('address', '0')))
                    port_elem.set("Type", str(port.get('type', 'ICP')))
                    if port.get('upstream'):
                        port_elem.set("Upstream", port.get('upstream'))
            
            # Add Communications if available
            if 'config_size' in module:
                comm_elem = ET.SubElement(module_elem, "Communications")
                config_tag_elem = ET.SubElement(comm_elem, "ConfigTag")
                config_tag_elem.set("ConfigSize", str(module.get('config_size', '0')))
                config_tag_elem.set("ExternalAccess", module.get('external_access', 'Read/Write'))
                
                if 'config_data' in module:
                    data_elem = ET.SubElement(config_tag_elem, "Data")
                    data_elem.set("Format", "L5K")
                    cdata = ET.SubElement(data_elem, "CDATA")
                    cdata.text = module['config_data']
            
            # Add Connection if available
            if 'connection' in module and module['connection']:
                conn_info = module['connection']
                conn_elem = ET.SubElement(module_elem, "Connection")
                for key, value in conn_info.items():
                    if value:
                        conn_elem.set(key.replace('_', ''), str(value))
        
        # AOI Definitions
        aoi_elem = ET.SubElement(controller, "AddOnInstructionDefinitions")
        
        # Tags
        tags_elem = ET.SubElement(controller, "Tags")
        for tag in existing_tags:
            tags_elem.append(tag)
        
        # Programs with rungs
        programs_elem = ET.SubElement(controller, "Programs")
        
        if existing_programs:
            # Use existing program structure
            for prog in existing_programs:
                programs_elem.append(prog)
        else:
            # Create basic program with rungs
            program_elem = ET.SubElement(programs_elem, "Program")
            program_elem.set("Name", "MainProgram")
            program_elem.set("TestEdits", "false")
            program_elem.set("MainRoutineName", "MainRoutine")
            program_elem.set("Disabled", "false")
            program_elem.set("UseAsFolder", "false")
            
            prog_tags = ET.SubElement(program_elem, "Tags")
            routines_elem = ET.SubElement(program_elem, "Routines")
            
            routine_elem = ET.SubElement(routines_elem, "Routine")
            routine_elem.set("Name", "MainRoutine")
            routine_elem.set("Type", "RLL")
            
            rll_elem = ET.SubElement(routine_elem, "RLLContent")
            
            # Add all rungs
            for i, rung_data in enumerate(rungs_data):
                rung_elem = ET.SubElement(rll_elem, "Rung")
                rung_elem.set("Number", str(i))
                rung_elem.set("Type", "N")
                
                text_elem = ET.SubElement(rung_elem, "Text")
                text_elem.text = rung_data['text']
        
        # Tasks
        tasks_elem = ET.SubElement(controller, "Tasks")
        task_elem = ET.SubElement(tasks_elem, "Task")
        task_elem.set("Name", "MainTask")
        task_elem.set("Type", "CONTINUOUS")
        task_elem.set("Priority", "10")
        task_elem.set("Watchdog", "500")
        task_elem.set("DisableUpdateOutputs", "false")
        task_elem.set("InhibitTask", "false")
        
        scheduled_progs = ET.SubElement(task_elem, "ScheduledPrograms")
        sched_prog = ET.SubElement(scheduled_progs, "ScheduledProgram")
        sched_prog.set("Name", "MainProgram")
        
        # Save final L5X
        final_l5x = self.output_dir / "COMPLETE_PLC100_Mashing.L5X"
        
        # Pretty print
        from xml.dom import minidom
        rough_string = ET.tostring(root, 'unicode')
        reparsed = minidom.parseString(rough_string)
        pretty = reparsed.toprettyxml(indent="  ")
        
        with open(final_l5x, 'w') as f:
            f.write(pretty)
        
        print(f"\n🎉 COMPLETE L5X FILE CREATED!")
        print(f"✅ File: {final_l5x}")
        print(f"📊 Contains:")
        print(f"   • {len(all_modules)} Modules with full configurations")
        print(f"   • {len(rungs_data)} Ladder logic rungs")
        print(f"   • {len(existing_tags)} Tags")
        print(f"   • {len(existing_datatypes)} Data types")
        print(f"   • {len(existing_programs)} Programs")
        
        # Save module summary
        summary = {
            'total_modules': len(all_modules),
            'modules_with_config': len([m for m in all_modules.values() if 'config_data' in m]),
            'modules_with_ports': len([m for m in all_modules.values() if 'ports' in m]),
            'modules_by_catalog': {}
        }
        
        for module in all_modules.values():
            catalog = module.get('catalog_number', 'Unknown')
            summary['modules_by_catalog'][catalog] = summary['modules_by_catalog'].get(catalog, 0) + 1
        
        summary_file = self.output_dir / "extraction_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📄 Summary saved to: {summary_file}")
    
    def add_standard_sections(self, controller):
        """Add standard controller sections"""
        # RedundancyInfo
        redundancy = ET.SubElement(controller, "RedundancyInfo")
        redundancy.set("Enabled", "false")
        redundancy.set("KeepTestEditsOnSwitchOver", "false")
        redundancy.set("IOMemoryPadPercentage", "90")
        redundancy.set("DataTablePadPercentage", "50")
        
        # Security
        security = ET.SubElement(controller, "Security")
        security.set("Code", "0")
        security.set("ChangesToDetect", "16#ffff_ffff_ffff_ffff")
        
        # SafetyInfo
        safety = ET.SubElement(controller, "SafetyInfo")
        safety.set("SafetySignature", "16#0000_0000_0000_0000")

def main():
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    extractor = ComprehensiveModuleExtractor(acd_file)
    extractor.extract()

if __name__ == "__main__":
    main() 