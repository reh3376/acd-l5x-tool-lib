# L5X to ACD: Reversing the Conversion Path

## 🎯 First Principles Analysis

### The Key Insight
If we can successfully convert ACD → L5X with 100% data preservation, then the reverse path L5X → ACD should be achievable by reversing each transformation step.

## 📊 Mapping the Reverse Path

### What We Know from ACD → L5X Conversion:

1. **ACD Structure**
   ```
   ACD File
   ├── Text Header (37KB)
   │   └── Version history, metadata
   └── Binary Section (starts at 0x9307)
       └── GZIP Compressed Blocks
           ├── Comps.Dat (18MB) - Component records
           ├── TagInfo.XML (4MB) - Tags and programs  
           ├── SbRegion.Dat (1.4MB) - Ladder logic
           ├── Comments.Dat (1.1MB) - Comments
           ├── QuickInfo.XML - Controller info
           └── XRefs.Dat (2.1MB) - Cross references
   ```

2. **L5X Structure**
   ```
   L5X File (XML)
   ├── Controller
   │   ├── DataTypes
   │   ├── Modules
   │   ├── Tags
   │   └── Programs
   │       └── Routines
   │           └── Rungs (Ladder Logic)
   └── Comments (embedded in elements)
   ```

## 🔄 Reverse Transformation Map

### Step-by-Step Reversal Process:

#### 1. Text Header Generation
**Forward**: ACD text header → Ignored (metadata only)
**Reverse**: Generate standard header with:
```python
def generate_acd_header(l5x_data):
    # Extract metadata from L5X
    controller_name = l5x_data['controller']['name']
    timestamp = datetime.now()
    
    # Generate standard header format
    header = f"""=~=~=~=~=~=~=~=~=~=~=~= PLC Battery Information =~=~=~=~=~=~=~=~=~=~=~=
 Battery Operated: false

=~=~=~=~=~=~=~=~=~=~=~= Project Information =~=~=~=~=~=~=~=~=~=~=~=
 Project Created: {timestamp}
 Controller: {controller_name}
    """
    return header.ljust(0x9307)  # Pad to exact size
```

#### 2. TagInfo.XML Generation
**Forward**: TagInfo.XML → Programs, Tags extracted
**Reverse**: Programs, Tags → TagInfo.XML
```python
def generate_taginfo_xml(programs, tags):
    # We already did this in the prototype!
    # Just need to match exact format from original
    root = ET.Element("TagInfo")
    # ... populate from L5X data
    return ET.tostring(root, encoding='utf-16le')
```

#### 3. Comps.Dat Binary Generation
**Forward**: Binary records → Component objects
**Reverse**: Component objects → Binary records

This is where we need to reverse engineer the binary format:
```python
def generate_comps_record(component):
    # From our analysis, we know:
    # - object_id (4 bytes)
    # - parent_id (4 bytes)  
    # - record_type (4 bytes)
    # - name (UTF-16LE with length prefix)
    
    record = bytearray()
    record.extend(struct.pack('<I', component['object_id']))
    record.extend(struct.pack('<I', component['parent_id']))
    record.extend(struct.pack('<I', component['record_type']))
    
    name_bytes = component['name'].encode('utf-16le')
    record.extend(struct.pack('<H', len(name_bytes)))
    record.extend(name_bytes)
    
    return bytes(record)
```

#### 4. SbRegion.Dat Generation
**Forward**: UTF-16LE rungs with @ID@ references → Resolved ladder logic
**Reverse**: Resolved ladder logic → UTF-16LE rungs with @ID@ references

```python
def generate_sbregion_record(rung, tag_map):
    # Reverse the tag resolution
    rung_text = rung['text']
    
    # Replace tag names with @ID@ references
    for tag_name, object_id in tag_map.items():
        rung_text = rung_text.replace(tag_name, f'@{object_id:08X}@')
    
    # Encode as UTF-16LE
    return rung_text.encode('utf-16le')
```

#### 5. Comments.Dat Generation
**Forward**: Various encodings → Extracted comments
**Reverse**: Comments → Proper encoding in Comments.Dat

## 🛠️ Implementation Strategy

### Phase 1: Exact Format Matching
1. Use our extracted databases as templates
2. Generate each database with exact binary format
3. Compare byte-by-byte with originals

### Phase 2: Object ID Management
```python
class ObjectIDManager:
    def __init__(self):
        self.next_id = 0x1000  # Start at safe offset
        self.id_map = {}
        
    def get_id(self, name, type):
        key = f"{type}:{name}"
        if key not in self.id_map:
            self.id_map[key] = self.next_id
            self.next_id += 1
        return self.id_map[key]
```

### Phase 3: Binary Assembly
```python
def assemble_acd(databases):
    acd = bytearray()
    
    # Add text header
    acd.extend(generate_header())
    
    # Add each database as GZIP block
    for db_name, db_data in databases.items():
        compressed = gzip.compress(db_data)
        
        # Add database entry
        acd.extend(struct.pack('<I', len(db_name)))
        acd.extend(db_name.encode('utf-8'))
        acd.extend(struct.pack('<I', len(compressed)))
        acd.extend(compressed)
    
    return bytes(acd)
```

## 📋 Validation Strategy

### Binary Comparison Tools
```python
def validate_database(generated, original):
    # Compare structure
    if len(generated) != len(original):
        return False, f"Size mismatch: {len(generated)} vs {len(original)}"
    
    # Find differences
    diffs = []
    for i, (g, o) in enumerate(zip(generated, original)):
        if g != o:
            diffs.append((i, g, o))
    
    return len(diffs) == 0, diffs
```

### Functional Validation
1. Import generated ACD into hutcheb/acd
2. Extract databases
3. Compare with source L5X data
4. Test in Studio 5000 (if available)

## 🚀 Next Steps

### Immediate Actions:
1. **Analyze Binary Formats**: Deep dive into each database's exact binary structure
2. **Build Format Library**: Create binary format definitions for each record type
3. **Implement Generators**: One generator per database type
4. **Test Incrementally**: Start with simple databases (QuickInfo.XML)

### Code Structure:
```python
class L5XToACDConverter:
    def __init__(self, l5x_file):
        self.l5x = self.parse_l5x(l5x_file)
        self.id_manager = ObjectIDManager()
        self.databases = {}
        
    def convert(self):
        # Generate each database
        self.databases['TagInfo.XML'] = self.generate_taginfo()
        self.databases['QuickInfo.XML'] = self.generate_quickinfo()
        self.databases['Comps.Dat'] = self.generate_comps()
        self.databases['SbRegion.Dat'] = self.generate_sbregion()
        self.databases['Comments.Dat'] = self.generate_comments()
        
        # Assemble ACD
        return self.assemble_acd()
```

## 🎯 Why This Will Work

1. **Bijective Mapping**: Our ACD → L5X conversion preserves all data, so the reverse mapping exists
2. **Known Formats**: We've decoded the binary formats during extraction
3. **Reference Implementation**: hutcheb/acd provides parsing logic we can reverse
4. **Incremental Validation**: We can validate each component separately

## 📊 Confidence Level

- **High Confidence**: XML databases (TagInfo.XML, QuickInfo.XML)
- **Medium Confidence**: Binary databases with known structure (Comps.Dat)
- **Low Confidence**: Complex binary formats (checksums, headers)

The path is clear - we just need to reverse each transformation we discovered during ACD → L5X conversion! 