# Round-Trip ACD ↔ L5X Conversion Solution

## 🎯 Goal
Achieve perfect round-trip conversion: ACD → L5X → ACD where the final ACD is byte-for-byte identical to the original.

## 🔍 Current Understanding

### ACD File Structure
1. **Text Header** (~37KB)
   - Version history and timestamps
   - Human-readable metadata
   
2. **Binary Section** (Compressed)
   - Multiple GZIP blocks containing:
     - Component database ("Comps")
     - Controller configuration
     - Programs, routines, and logic
     - Tags and data types

### Key Discoveries
- Project name: PLC100_Mashing
- Controller type: 1756-L85E
- Software version: V34.01.00
- Database fields: CompUId, CompName, CompIOI, AlternateParentUId, Ordinal

## 📋 Implementation Plan

### Phase 1: Complete ACD Parsing ✅ (Partially Complete)
- [x] Extract GZIP blocks
- [x] Find database structures
- [ ] Parse binary records correctly
- [ ] Extract all components with proper names
- [ ] Extract PLC logic (ladder, structured text)
- [ ] Extract tags and data types

### Phase 2: Generate Complete L5X
- [ ] Create full XML structure with all components
- [ ] Include all programs and routines
- [ ] Include all tags with proper data types
- [ ] Include module configuration
- [ ] Include add-on instructions

### Phase 3: L5X to ACD Conversion
- [ ] Create ACD binary writer
- [ ] Implement GZIP compression
- [ ] Generate proper database structures
- [ ] Recreate exact binary format

### Phase 4: Validation
- [ ] Compare generated ACD with original (byte-by-byte)
- [ ] Test with Studio 5000 software
- [ ] Verify all functionality preserved

## 🛠️ Technical Approach

### For ACD Parsing:
1. **Binary Structure Analysis**
   ```c
   typedef struct {
       uint16_t length;      // Length-prefixed strings
       char data[];          // Actual string data
   } StringRecord;
   
   typedef struct {
       uint32_t record_size; // Total record size
       uint32_t uid;         // Component UID
       StringRecord name;    // Component name
       // ... other fields
   } ComponentRecord;
   ```

2. **Proper String Extraction**
   - Read length prefix (2 bytes)
   - Read exact number of bytes
   - Handle Unicode/ASCII encoding

### For L5X Generation:
- Use extracted data to build complete XML
- Preserve all attributes and relationships
- Include all metadata

### For ACD Generation:
1. **Binary Writer Implementation**
   - Create exact binary structures
   - Implement proper alignment
   - Generate correct checksums

2. **GZIP Compression**
   - Compress blocks with same parameters
   - Maintain exact block boundaries
   - Preserve compression ratios

## 🚀 Next Immediate Steps

1. **Fix Binary Parser**
   - Implement proper length-prefixed string reading
   - Parse record boundaries correctly
   - Extract clean component names

2. **Extract More Data**
   - Parse remaining compressed blocks
   - Find program logic sections
   - Extract tag definitions

3. **Build Comprehensive L5X**
   - Include all extracted components
   - Add proper relationships
   - Generate valid RSLogix structure

## 📊 Success Criteria

✅ Round-trip success when:
```bash
# Original and regenerated files are identical
diff original.ACD regenerated.ACD
# No differences found

# SHA256 hashes match
sha256sum original.ACD regenerated.ACD
# Same hash for both files
```

## 🔧 Tools Needed

1. **Enhanced C Parser** - For binary extraction
2. **Python XML Generator** - For L5X creation
3. **Binary Writer** - For ACD generation
4. **Validation Suite** - For verification

## 💡 Key Insights

The challenge isn't just parsing - it's understanding the exact binary format and relationships between components. The ACD format uses:
- Database-like structures with indexes
- Cross-references between components
- Compressed blocks with specific ordering
- Proprietary encoding for certain fields

With persistence and the right approach, we can achieve perfect round-trip conversion! 