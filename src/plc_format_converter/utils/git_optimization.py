"""
Git Optimization Utilities for PLC Format Converter - Phase 3.9
==============================================================

Utilities for optimizing L5X files for git version control with meaningful
diffs and merge capabilities.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple
import re
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GitOptimizer:
    """
    Optimizes L5X files for git version control
    
    Features:
    - Consistent formatting for meaningful diffs
    - Stable element ordering
    - Meaningful comments for context
    - Merge-friendly structure
    """
    
    def __init__(self):
        """Initialize git optimizer"""
        self.optimization_rules = {
            'sort_elements': True,
            'add_context_comments': True,
            'normalize_whitespace': True,
            'stable_uuids': True,
            'consistent_formatting': True
        }
    
    def optimize_l5x_for_git(self, l5x_content: str, source_info: Optional[Dict] = None) -> str:
        """
        Optimize L5X content for git version control
        
        Args:
            l5x_content: Raw L5X XML content
            source_info: Optional source file information
            
        Returns:
            Git-optimized L5X content
        """
        try:
            # Parse XML
            root = ET.fromstring(l5x_content)
            
            # Apply optimization rules
            if self.optimization_rules['sort_elements']:
                self._sort_elements_recursively(root)
            
            if self.optimization_rules['add_context_comments']:
                self._add_context_comments(root, source_info)
            
            if self.optimization_rules['stable_uuids']:
                self._stabilize_uuids(root)
            
            # Generate optimized XML
            optimized_content = self._format_xml_for_git(root)
            
            if self.optimization_rules['normalize_whitespace']:
                optimized_content = self._normalize_whitespace(optimized_content)
            
            logger.info("L5X content optimized for git version control")
            return optimized_content
            
        except Exception as e:
            logger.error(f"Git optimization failed: {e}")
            return l5x_content  # Return original on error
    
    def _sort_elements_recursively(self, element: ET.Element):
        """Sort XML elements for consistent ordering"""
        
        # Define sort priority for common PLC elements
        sort_priority = {
            'Controller': 0,
            'Programs': 1,
            'Program': 1,
            'Routines': 2,
            'Routine': 2,
            'Tags': 3,
            'Tag': 3,
            'DataTypes': 4,
            'DataType': 4,
            'Modules': 5,
            'Module': 5
        }
        
        # Sort child elements
        children = list(element)
        children.sort(key=lambda e: (
            sort_priority.get(e.tag, 999),
            e.get('Name', ''),
            e.tag
        ))
        
        # Clear and re-add sorted children
        element.clear()
        for child in children:
            element.append(child)
            self._sort_elements_recursively(child)
    
    def _add_context_comments(self, root: ET.Element, source_info: Optional[Dict]):
        """Add contextual comments for better git understanding"""
        
        # Add header comment
        header_comment = self._create_header_comment(source_info)
        if header_comment:
            root.insert(0, ET.Comment(header_comment))
        
        # Add section comments
        for child in root:
            if child.tag in ['Programs', 'Tags', 'DataTypes', 'Modules']:
                section_comment = f" {child.tag} Section - Contains {len(list(child))} items "
                child.insert(0, ET.Comment(section_comment))
    
    def _create_header_comment(self, source_info: Optional[Dict]) -> Optional[str]:
        """Create header comment with conversion context"""
        
        if not source_info:
            return None
        
        comment_lines = [
            " Enhanced L5X Conversion - Phase 3.9 ",
            f" Source: {source_info.get('source_file', 'Unknown')} ",
            f" Converted: {source_info.get('conversion_date', 'Unknown')} ",
            f" Data Preservation: {source_info.get('preservation_score', 'Unknown')}% "
        ]
        
        return '\n'.join(comment_lines)
    
    def _stabilize_uuids(self, element: ET.Element):
        """Replace random UUIDs with stable, content-based identifiers"""
        
        uuid_pattern = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
        
        for attr_name, attr_value in element.attrib.items():
            if uuid_pattern.match(attr_value):
                # Generate stable UUID based on element content
                stable_id = self._generate_stable_id(element)
                element.set(attr_name, stable_id)
        
        # Process child elements
        for child in element:
            self._stabilize_uuids(child)
    
    def _generate_stable_id(self, element: ET.Element) -> str:
        """Generate stable identifier based on element content"""
        
        # Use element name and type for stable ID
        name = element.get('Name', '')
        tag = element.tag
        
        # Create deterministic hash
        import hashlib
        content = f"{tag}_{name}".encode()
        hash_hex = hashlib.md5(content).hexdigest()
        
        # Format as UUID-like string
        return f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:32]}"
    
    def _format_xml_for_git(self, root: ET.Element) -> str:
        """Format XML with git-friendly structure"""
        
        # Use consistent indentation
        self._indent_xml(root)
        
        # Generate XML string
        xml_str = ET.tostring(root, encoding='unicode', xml_declaration=True)
        
        # Ensure consistent line endings
        xml_str = xml_str.replace('\r\n', '\n').replace('\r', '\n')
        
        return xml_str
    
    def _indent_xml(self, element: ET.Element, level: int = 0):
        """Add consistent indentation to XML elements"""
        
        indent = "\n" + "  " * level
        
        if len(element):
            if not element.text or not element.text.strip():
                element.text = indent + "  "
            
            if not element.tail or not element.tail.strip():
                element.tail = indent
            
            for child in element:
                self._indent_xml(child, level + 1)
            
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not element.tail or not element.tail.strip()):
                element.tail = indent
    
    def _normalize_whitespace(self, xml_content: str) -> str:
        """Normalize whitespace for consistent formatting"""
        
        # Remove trailing whitespace from lines
        lines = xml_content.split('\n')
        normalized_lines = [line.rstrip() for line in lines]
        
        # Ensure file ends with single newline
        while normalized_lines and not normalized_lines[-1]:
            normalized_lines.pop()
        
        normalized_lines.append('')
        
        return '\n'.join(normalized_lines)


class DiffAnalyzer:
    """
    Analyzes differences between L5X files for meaningful change detection
    """
    
    def __init__(self):
        """Initialize diff analyzer"""
        self.change_categories = {
            'logic_changes': [],
            'tag_changes': [],
            'io_changes': [],
            'configuration_changes': []
        }
    
    def analyze_l5x_changes(self, old_l5x: str, new_l5x: str) -> Dict[str, Any]:
        """
        Analyze meaningful changes between L5X versions
        
        Args:
            old_l5x: Original L5X content
            new_l5x: Modified L5X content
            
        Returns:
            Dictionary of categorized changes
        """
        try:
            old_root = ET.fromstring(old_l5x)
            new_root = ET.fromstring(new_l5x)
            
            changes = {
                'logic_changes': self._find_logic_changes(old_root, new_root),
                'tag_changes': self._find_tag_changes(old_root, new_root),
                'io_changes': self._find_io_changes(old_root, new_root),
                'configuration_changes': self._find_config_changes(old_root, new_root),
                'summary': {}
            }
            
            # Generate summary
            changes['summary'] = self._generate_change_summary(changes)
            
            return changes
            
        except Exception as e:
            logger.error(f"Change analysis failed: {e}")
            return {'error': str(e)}
    
    def _find_logic_changes(self, old_root: ET.Element, new_root: ET.Element) -> List[Dict]:
        """Find changes in ladder logic"""
        
        logic_changes = []
        
        # Compare routines
        old_routines = self._extract_routines(old_root)
        new_routines = self._extract_routines(new_root)
        
        # Find added routines
        for name, routine in new_routines.items():
            if name not in old_routines:
                logic_changes.append({
                    'type': 'routine_added',
                    'routine': name,
                    'description': f"Added routine: {name}"
                })
        
        # Find removed routines
        for name, routine in old_routines.items():
            if name not in new_routines:
                logic_changes.append({
                    'type': 'routine_removed',
                    'routine': name,
                    'description': f"Removed routine: {name}"
                })
        
        # Find modified routines
        for name in set(old_routines.keys()) & set(new_routines.keys()):
            if old_routines[name] != new_routines[name]:
                logic_changes.append({
                    'type': 'routine_modified',
                    'routine': name,
                    'description': f"Modified routine: {name}"
                })
        
        return logic_changes
    
    def _find_tag_changes(self, old_root: ET.Element, new_root: ET.Element) -> List[Dict]:
        """Find changes in tag database"""
        
        tag_changes = []
        
        # Extract tag information
        old_tags = self._extract_tags(old_root)
        new_tags = self._extract_tags(new_root)
        
        # Find tag differences
        for name, tag_info in new_tags.items():
            if name not in old_tags:
                tag_changes.append({
                    'type': 'tag_added',
                    'tag': name,
                    'data_type': tag_info.get('data_type', ''),
                    'description': f"Added tag: {name}"
                })
            elif old_tags[name] != tag_info:
                tag_changes.append({
                    'type': 'tag_modified',
                    'tag': name,
                    'description': f"Modified tag: {name}"
                })
        
        for name in old_tags:
            if name not in new_tags:
                tag_changes.append({
                    'type': 'tag_removed',
                    'tag': name,
                    'description': f"Removed tag: {name}"
                })
        
        return tag_changes
    
    def _find_io_changes(self, old_root: ET.Element, new_root: ET.Element) -> List[Dict]:
        """Find changes in I/O configuration"""
        
        io_changes = []
        
        # Extract I/O module information
        old_modules = self._extract_modules(old_root)
        new_modules = self._extract_modules(new_root)
        
        # Find module differences
        for name, module_info in new_modules.items():
            if name not in old_modules:
                io_changes.append({
                    'type': 'module_added',
                    'module': name,
                    'description': f"Added I/O module: {name}"
                })
            elif old_modules[name] != module_info:
                io_changes.append({
                    'type': 'module_modified',
                    'module': name,
                    'description': f"Modified I/O module: {name}"
                })
        
        for name in old_modules:
            if name not in new_modules:
                io_changes.append({
                    'type': 'module_removed',
                    'module': name,
                    'description': f"Removed I/O module: {name}"
                })
        
        return io_changes
    
    def _find_config_changes(self, old_root: ET.Element, new_root: ET.Element) -> List[Dict]:
        """Find changes in controller configuration"""
        
        config_changes = []
        
        # Compare controller properties
        old_controller = old_root.find('.//Controller')
        new_controller = new_root.find('.//Controller')
        
        if old_controller is not None and new_controller is not None:
            # Compare key attributes
            key_attrs = ['Name', 'ProcessorType', 'MajorRev', 'MinorRev']
            
            for attr in key_attrs:
                old_value = old_controller.get(attr, '')
                new_value = new_controller.get(attr, '')
                
                if old_value != new_value:
                    config_changes.append({
                        'type': 'controller_config_changed',
                        'attribute': attr,
                        'old_value': old_value,
                        'new_value': new_value,
                        'description': f"Controller {attr} changed from '{old_value}' to '{new_value}'"
                    })
        
        return config_changes
    
    def _extract_routines(self, root: ET.Element) -> Dict[str, str]:
        """Extract routine information from XML"""
        
        routines = {}
        
        for routine in root.findall('.//Routine'):
            name = routine.get('Name', '')
            if name:
                # Get routine content as string for comparison
                content = ET.tostring(routine, encoding='unicode')
                routines[name] = content
        
        return routines
    
    def _extract_tags(self, root: ET.Element) -> Dict[str, Dict]:
        """Extract tag information from XML"""
        
        tags = {}
        
        for tag in root.findall('.//Tag'):
            name = tag.get('Name', '')
            if name:
                tags[name] = {
                    'data_type': tag.get('DataType', ''),
                    'tag_type': tag.get('TagType', ''),
                    'scope': tag.get('Scope', ''),
                    'content': ET.tostring(tag, encoding='unicode')
                }
        
        return tags
    
    def _extract_modules(self, root: ET.Element) -> Dict[str, Dict]:
        """Extract I/O module information from XML"""
        
        modules = {}
        
        for module in root.findall('.//Module'):
            name = module.get('Name', '')
            if name:
                modules[name] = {
                    'catalog_number': module.get('CatalogNumber', ''),
                    'vendor': module.get('Vendor', ''),
                    'product_type': module.get('ProductType', ''),
                    'content': ET.tostring(module, encoding='unicode')
                }
        
        return modules
    
    def _generate_change_summary(self, changes: Dict[str, List]) -> Dict[str, Any]:
        """Generate summary of all changes"""
        
        summary = {
            'total_changes': 0,
            'by_category': {},
            'impact_level': 'low'
        }
        
        for category, change_list in changes.items():
            if category != 'summary' and isinstance(change_list, list):
                count = len(change_list)
                summary['by_category'][category] = count
                summary['total_changes'] += count
        
        # Determine impact level
        if summary['total_changes'] == 0:
            summary['impact_level'] = 'none'
        elif summary['total_changes'] <= 5:
            summary['impact_level'] = 'low'
        elif summary['total_changes'] <= 20:
            summary['impact_level'] = 'medium'
        else:
            summary['impact_level'] = 'high'
        
        return summary


def optimize_l5x_for_version_control(l5x_content: str, source_info: Optional[Dict] = None) -> str:
    """
    Convenience function to optimize L5X content for git version control
    
    Args:
        l5x_content: Raw L5X XML content
        source_info: Optional source file information
        
    Returns:
        Git-optimized L5X content
    """
    optimizer = GitOptimizer()
    return optimizer.optimize_l5x_for_git(l5x_content, source_info)


def analyze_l5x_diff(old_l5x: str, new_l5x: str) -> Dict[str, Any]:
    """
    Convenience function to analyze differences between L5X files
    
    Args:
        old_l5x: Original L5X content
        new_l5x: Modified L5X content
        
    Returns:
        Dictionary of categorized changes
    """
    analyzer = DiffAnalyzer()
    return analyzer.analyze_l5x_changes(old_l5x, new_l5x) 