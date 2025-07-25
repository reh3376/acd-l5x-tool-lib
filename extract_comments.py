#!/usr/bin/env python3
"""
Extract comments from ACD Comments.Dat handling Unicode issues
"""

import os
import sqlite3
import json
import struct
from pathlib import Path
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract

class CommentExtractor:
    def __init__(self, acd_file):
        self.acd_file = Path(acd_file)
        self.output_dir = Path("comments_extracted")
        self.output_dir.mkdir(exist_ok=True)
        self.db_dir = self.output_dir / "databases"
        
    def extract(self):
        """Extract comments from ACD"""
        print(f"\n🔍 Extracting comments from {self.acd_file.name}")
        print("="*60)
        
        # Extract databases
        print("\n📋 Step 1: Extracting databases...")
        ExtractAcdDatabase(str(self.acd_file), str(self.db_dir)).extract()
        
        # Parse Comments.Dat manually
        print("\n📋 Step 2: Parsing Comments.Dat...")
        comments = self.parse_comments_dat()
        
        # Parse from L5X exports for comparison
        print("\n📋 Step 3: Looking for comments in L5X exports...")
        l5x_comments = self.find_l5x_comments()
        
        # Merge and analyze
        all_comments = self.merge_comments(comments, l5x_comments)
        
        # Generate summary
        self.generate_summary(all_comments)
        
        return all_comments
    
    def parse_comments_dat(self):
        """Parse Comments.Dat handling Unicode issues"""
        comments_file = self.db_dir / "Comments.Dat"
        if not comments_file.exists():
            print("  Comments.Dat not found")
            return {}
            
        comments = {}
        
        try:
            # Read the raw binary data
            with open(comments_file, 'rb') as f:
                data = f.read()
            
            print(f"  Comments.Dat size: {len(data)} bytes")
            
            # Try different approaches to extract comments
            
            # Method 1: Look for text patterns
            print("  Method 1: Searching for text patterns...")
            text_comments = self.extract_text_patterns(data)
            comments.update(text_comments)
            
            # Method 2: Use DbExtract but handle errors
            print("  Method 2: Using DbExtract with error handling...")
            db_comments = self.extract_with_dbextract()
            comments.update(db_comments)
            
            # Method 3: Manual binary parsing
            print("  Method 3: Manual binary parsing...")
            binary_comments = self.manual_binary_parse(data)
            comments.update(binary_comments)
            
        except Exception as e:
            print(f"  Error parsing Comments.Dat: {e}")
            
        print(f"  Total comments found: {len(comments)}")
        return comments
    
    def extract_text_patterns(self, data):
        """Extract text patterns that look like comments"""
        comments = {}
        
        # Look for ASCII text sequences
        current_text = []
        comment_id = 0
        
        for i in range(len(data)):
            byte_val = data[i]
            
            # Check if it's printable ASCII
            if 32 <= byte_val <= 126:
                current_text.append(chr(byte_val))
            else:
                # End of text sequence
                if len(current_text) > 10:  # Minimum comment length
                    text = ''.join(current_text)
                    # Filter out non-comment text
                    if self.looks_like_comment(text):
                        comments[f"ascii_{comment_id}"] = {
                            'text': text,
                            'position': i - len(current_text),
                            'method': 'ascii_pattern'
                        }
                        comment_id += 1
                current_text = []
        
        # Check for UTF-16 text
        utf16_comments = self.extract_utf16_text(data)
        comments.update(utf16_comments)
        
        print(f"    Found {len(comments)} text patterns")
        return comments
    
    def extract_utf16_text(self, data):
        """Extract UTF-16 encoded text"""
        comments = {}
        comment_id = 0
        
        # Try UTF-16LE
        for i in range(0, len(data) - 20, 2):
            try:
                # Try to decode 20+ bytes as UTF-16LE
                for length in [20, 50, 100, 200]:
                    if i + length >= len(data):
                        continue
                        
                    text_bytes = data[i:i+length]
                    if len(text_bytes) % 2 != 0:
                        text_bytes = text_bytes[:-1]
                    
                    try:
                        text = text_bytes.decode('utf-16le')
                        # Check if it's meaningful text
                        if self.looks_like_comment(text):
                            comments[f"utf16_{comment_id}"] = {
                                'text': text.strip('\x00'),
                                'position': i,
                                'method': 'utf16_pattern'
                            }
                            comment_id += 1
                            break
                    except:
                        continue
            except:
                continue
        
        return comments
    
    def looks_like_comment(self, text):
        """Check if text looks like a meaningful comment"""
        # Filter criteria
        if len(text) < 5:
            return False
            
        # Must contain mostly printable characters
        printable_ratio = sum(1 for c in text if c.isprintable()) / len(text)
        if printable_ratio < 0.8:
            return False
            
        # Common comment indicators
        comment_indicators = [
            'description', 'comment', 'note', 'alarm', 'fault',
            'input', 'output', 'control', 'system', 'operation',
            'valve', 'pump', 'motor', 'sensor', 'temperature',
            'pressure', 'flow', 'level', 'speed', 'position'
        ]
        
        text_lower = text.lower()
        has_indicators = any(indicator in text_lower for indicator in comment_indicators)
        
        # Has reasonable word structure
        has_spaces = ' ' in text
        has_letters = any(c.isalpha() for c in text)
        
        return has_indicators or (has_spaces and has_letters and len(text) > 15)
    
    def extract_with_dbextract(self):
        """Try to use DbExtract with error handling"""
        comments = {}
        
        try:
            comments_file = self.db_dir / "Comments.Dat"
            db = DbExtract(str(comments_file)).read()
            
            for i, record in enumerate(db.records.record):
                try:
                    if hasattr(record, 'record') and hasattr(record.record, 'record_buffer'):
                        buffer = record.record.record_buffer
                        
                        # Try different encodings
                        for encoding in ['utf-8', 'utf-16le', 'latin1']:
                            try:
                                text = buffer.decode(encoding).strip('\x00')
                                if self.looks_like_comment(text):
                                    comments[f"db_record_{i}"] = {
                                        'text': text,
                                        'encoding': encoding,
                                        'method': 'dbextract'
                                    }
                                    break
                            except:
                                continue
                                
                except Exception as e:
                    # Skip problematic records
                    continue
                    
        except Exception as e:
            print(f"    DbExtract failed: {e}")
            
        return comments
    
    def manual_binary_parse(self, data):
        """Manually parse binary structure for comments"""
        comments = {}
        comment_id = 0
        
        # Look for length-prefixed strings
        for i in range(len(data) - 8):
            try:
                # Try 2-byte length prefix (little endian)
                length = struct.unpack('<H', data[i:i+2])[0]
                if 5 <= length <= 500:  # Reasonable comment length
                    text_start = i + 2
                    text_end = text_start + length
                    
                    if text_end <= len(data):
                        text_bytes = data[text_start:text_end]
                        
                        # Try different encodings
                        for encoding in ['utf-8', 'utf-16le', 'latin1']:
                            try:
                                text = text_bytes.decode(encoding)
                                if self.looks_like_comment(text):
                                    comments[f"manual_{comment_id}"] = {
                                        'text': text.strip('\x00'),
                                        'length_prefix': length,
                                        'position': i,
                                        'encoding': encoding,
                                        'method': 'manual_parse'
                                    }
                                    comment_id += 1
                                    break
                            except:
                                continue
                
                # Try 4-byte length prefix
                length = struct.unpack('<I', data[i:i+4])[0]
                if 5 <= length <= 1000:
                    text_start = i + 4
                    text_end = text_start + length
                    
                    if text_end <= len(data):
                        text_bytes = data[text_start:text_end]
                        
                        for encoding in ['utf-8', 'utf-16le', 'latin1']:
                            try:
                                text = text_bytes.decode(encoding)
                                if self.looks_like_comment(text):
                                    comments[f"manual4_{comment_id}"] = {
                                        'text': text.strip('\x00'),
                                        'length_prefix': length,
                                        'position': i,
                                        'encoding': encoding,
                                        'method': 'manual_parse_4byte'
                                    }
                                    comment_id += 1
                                    break
                            except:
                                continue
                                
            except:
                continue
                
        return comments
    
    def find_l5x_comments(self):
        """Look for comments in L5X export files"""
        comments = {}
        exports_dir = Path("docs/exports")
        
        if not exports_dir.exists():
            return comments
            
        l5x_files = list(exports_dir.glob("*.L5X"))
        print(f"  Checking {len(l5x_files)} L5X files for comments...")
        
        comment_count = 0
        
        for l5x_file in l5x_files[:20]:  # Check first 20 files
            try:
                with open(l5x_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for comment patterns in L5X
                import re
                
                # Look for description attributes
                desc_pattern = r'Description="([^"]+)"'
                descriptions = re.findall(desc_pattern, content)
                
                for desc in descriptions:
                    if len(desc) > 5:  # Meaningful description
                        comments[f"l5x_desc_{comment_count}"] = {
                            'text': desc,
                            'file': l5x_file.name,
                            'method': 'l5x_description'
                        }
                        comment_count += 1
                
                # Look for comment elements
                comment_pattern = r'<Comment>([^<]+)</Comment>'
                comment_elements = re.findall(comment_pattern, content)
                
                for comment in comment_elements:
                    comments[f"l5x_comment_{comment_count}"] = {
                        'text': comment,
                        'file': l5x_file.name,
                        'method': 'l5x_comment_element'
                    }
                    comment_count += 1
                    
            except Exception as e:
                continue
                
        print(f"    Found {len(comments)} comments in L5X files")
        return comments
    
    def merge_comments(self, acd_comments, l5x_comments):
        """Merge and deduplicate comments"""
        all_comments = {}
        all_comments.update(acd_comments)
        all_comments.update(l5x_comments)
        
        # Remove duplicates based on text similarity
        unique_comments = {}
        for comment_id, comment_data in all_comments.items():
            text = comment_data['text'].lower().strip()
            
            # Check if similar comment already exists
            is_duplicate = False
            for existing_id, existing_data in unique_comments.items():
                existing_text = existing_data['text'].lower().strip()
                
                # Simple similarity check
                if text == existing_text or (len(text) > 20 and text in existing_text) or (len(existing_text) > 20 and existing_text in text):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_comments[comment_id] = comment_data
        
        print(f"\n📊 Comment Deduplication:")
        print(f"  Total found: {len(all_comments)}")
        print(f"  Unique: {len(unique_comments)}")
        
        return unique_comments
    
    def generate_summary(self, comments):
        """Generate comment extraction summary"""
        print(f"\n📄 Comment Extraction Summary:")
        
        # Group by method
        by_method = {}
        for comment_data in comments.values():
            method = comment_data['method']
            if method not in by_method:
                by_method[method] = []
            by_method[method].append(comment_data)
        
        for method, method_comments in by_method.items():
            print(f"  {method}: {len(method_comments)} comments")
        
        # Show sample comments
        print(f"\n📝 Sample Comments:")
        for i, (comment_id, comment_data) in enumerate(list(comments.items())[:10]):
            text = comment_data['text'][:100]
            if len(comment_data['text']) > 100:
                text += "..."
            print(f"\n  Comment {i + 1} ({comment_data['method']}):")
            print(f"    {text}")
        
        # Save comments
        comments_file = self.output_dir / "extracted_comments.json"
        with open(comments_file, 'w') as f:
            json.dump(comments, f, indent=2, default=str)
        
        print(f"\n✅ Comments saved to: {comments_file}")
        
        return comments

def main():
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    extractor = CommentExtractor(acd_file)
    comments = extractor.extract()
    
    print(f"\n🎯 Extraction Complete: {len(comments)} comments found")

if __name__ == "__main__":
    main() 