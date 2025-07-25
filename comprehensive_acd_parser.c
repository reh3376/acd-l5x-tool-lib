#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <zlib.h>
#include <sys/stat.h>

#define MAX_COMPONENTS 10000
#define MAX_STRING_LEN 256

// Component structure based on database fields
typedef struct {
    uint32_t uid;
    char name[MAX_STRING_LEN];
    char ioi[MAX_STRING_LEN];
    uint32_t parent_uid;
    uint32_t ordinal;
    char type[64];
} Component;

// Database header structure
typedef struct {
    char name[64];
    uint32_t record_count;
    uint32_t record_size;
    uint32_t data_offset;
    uint32_t index_offset;
} DatabaseHeader;

// Global storage
Component components[MAX_COMPONENTS];
int component_count = 0;

// Read a null-terminated string from data
char* read_string(unsigned char *data, size_t offset, size_t max_len) {
    static char buffer[MAX_STRING_LEN];
    size_t i = 0;
    
    while (i < MAX_STRING_LEN - 1 && i < max_len && data[offset + i] != 0) {
        buffer[i] = data[offset + i];
        i++;
    }
    buffer[i] = '\0';
    
    return buffer;
}

// Read 32-bit little-endian integer
uint32_t read_uint32_le(unsigned char *data, size_t offset) {
    return data[offset] | 
           (data[offset + 1] << 8) | 
           (data[offset + 2] << 16) | 
           (data[offset + 3] << 24);
}

// Parse the Comps database
int parse_comps_database(unsigned char *data, size_t data_size, size_t start_offset) {
    printf("\n📊 Parsing Comps Database...\n");
    
    size_t offset = start_offset;
    
    // Skip "Comps\0"
    offset += 6;
    
    // Read field names
    printf("   Database fields:\n");
    int field_count = 0;
    char *fields[20];
    
    while (offset < data_size && field_count < 20) {
        char *field = read_string(data, offset, 50);
        if (strlen(field) == 0) break;
        
        fields[field_count] = strdup(field);
        printf("      [%d] %s\n", field_count, field);
        offset += strlen(field) + 1;
        field_count++;
    }
    
    // Look for .dat and .idx markers
    size_t dat_offset = 0, idx_offset = 0;
    
    for (size_t i = offset; i < data_size - 10; i++) {
        if (memcmp(data + i, ".dat", 4) == 0) {
            dat_offset = i + 8;  // Skip ".dat\0\0\0\0"
            printf("   📍 Found .dat section at: 0x%zx\n", dat_offset);
        }
        if (memcmp(data + i, ".idx", 4) == 0) {
            idx_offset = i + 8;  // Skip ".idx\0\0\0\0"
            printf("   📍 Found .idx section at: 0x%zx\n", idx_offset);
            break;
        }
    }
    
    // Parse records between dat_offset and next section
    if (dat_offset > 0) {
        printf("\n   📖 Parsing component records...\n");
        
        // Estimate record size (seems to be around 100-200 bytes)
        size_t record_size = 100;  // Start with estimate
        size_t current = dat_offset;
        
        while (current < data_size - record_size && component_count < MAX_COMPONENTS) {
            // Try to find component pattern
            // Look for reasonable UIDs (32-bit values)
            uint32_t potential_uid = read_uint32_le(data, current);
            
            if (potential_uid > 0 && potential_uid < 0x10000) {
                Component comp = {0};
                comp.uid = potential_uid;
                
                // Try to find name (usually after UID)
                size_t name_offset = current + 4;
                
                // Search for printable string
                for (size_t j = name_offset; j < current + record_size && j < data_size - 50; j++) {
                    if (data[j] >= 'A' && data[j] <= 'z') {
                        char *potential_name = read_string(data, j, 50);
                        if (strlen(potential_name) > 3 && strlen(potential_name) < 40) {
                            strcpy(comp.name, potential_name);
                            
                            components[component_count++] = comp;
                            printf("      Component %d: UID=%u, Name='%s'\n", 
                                   component_count, comp.uid, comp.name);
                            
                            current = j + strlen(potential_name) + 20;  // Skip ahead
                            break;
                        }
                    }
                }
            }
            
            current += 4;  // Move to next potential record
            
            if (component_count >= 50) break;  // Limit for now
        }
    }
    
    printf("   ✅ Found %d components\n", component_count);
    
    // Free field names
    for (int i = 0; i < field_count; i++) {
        free(fields[i]);
    }
    
    return component_count;
}

// Generate detailed L5X from extracted data
void generate_detailed_l5x(const char *output_file) {
    FILE *f = fopen(output_file, "w");
    if (!f) {
        perror("Failed to create L5X file");
        return;
    }
    
    fprintf(f, "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n");
    fprintf(f, "<RSLogix5000Content SchemaRevision=\"1.0\" SoftwareRevision=\"34.01\" ");
    fprintf(f, "TargetName=\"PLC100_Mashing\" TargetType=\"Controller\" ");
    fprintf(f, "ContainsContext=\"true\" Owner=\"ACD Parser\" ");
    fprintf(f, "ExportDate=\"Mon Jan 01 2025 00:00:00\">\n");
    
    fprintf(f, "  <Controller Use=\"Target\" Name=\"PLC100_Mashing\" ");
    fprintf(f, "ProcessorType=\"1756-L85E\" MajorRev=\"34\" MinorRev=\"01\">\n");
    
    // Add components as comments for now
    fprintf(f, "    <!-- Extracted Components from ACD -->\n");
    for (int i = 0; i < component_count && i < 20; i++) {
        fprintf(f, "    <!-- Component %d: UID=%u Name='%s' -->\n", 
                i+1, components[i].uid, components[i].name);
    }
    
    // Basic structure
    fprintf(f, "    <Programs>\n");
    fprintf(f, "      <Program Name=\"MainProgram\">\n");
    fprintf(f, "        <Routines>\n");
    fprintf(f, "          <Routine Name=\"MainRoutine\" Type=\"RLL\">\n");
    fprintf(f, "            <RLLContent>\n");
    
    // Add component info as rungs
    for (int i = 0; i < component_count && i < 5; i++) {
        fprintf(f, "              <Rung Number=\"%d\" Type=\"N\">\n", i);
        fprintf(f, "                <Comment>Component: %s (UID: %u)</Comment>\n", 
                components[i].name, components[i].uid);
        fprintf(f, "                <Text>NOP();</Text>\n");
        fprintf(f, "              </Rung>\n");
    }
    
    fprintf(f, "            </RLLContent>\n");
    fprintf(f, "          </Routine>\n");
    fprintf(f, "        </Routines>\n");
    fprintf(f, "      </Program>\n");
    fprintf(f, "    </Programs>\n");
    
    fprintf(f, "  </Controller>\n");
    fprintf(f, "</RSLogix5000Content>\n");
    
    fclose(f);
    printf("\n✅ Generated detailed L5X: %s\n", output_file);
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <extracted_block.bin> [output.L5X]\n", argv[0]);
        return 1;
    }
    
    printf("🚀 Comprehensive ACD Parser v3.0\n");
    printf("=================================\n\n");
    
    // Load the extracted block
    FILE *f = fopen(argv[1], "rb");
    if (!f) {
        perror("Failed to open block file");
        return 1;
    }
    
    fseek(f, 0, SEEK_END);
    size_t file_size = ftell(f);
    rewind(f);
    
    unsigned char *data = malloc(file_size);
    fread(data, 1, file_size, f);
    fclose(f);
    
    printf("📄 Loaded block: %s\n", argv[1]);
    printf("📏 Size: %.2f MB\n", file_size / (1024.0 * 1024.0));
    
    // Find and parse Comps database
    size_t comps_offset = 0;
    for (size_t i = 0; i < file_size - 5; i++) {
        if (memcmp(data + i, "Comps", 5) == 0) {
            comps_offset = i;
            break;
        }
    }
    
    if (comps_offset > 0) {
        parse_comps_database(data, file_size, comps_offset);
    }
    
    // Generate L5X
    const char *output_file = argc > 2 ? argv[2] : 
        "/Users/reh3376/repos/acd-l5x-tool-lib/docs/l5x-files/PLC100_Mashing_Detailed.L5X";
    generate_detailed_l5x(output_file);
    
    free(data);
    
    printf("\n🎯 Next steps:\n");
    printf("   1. Analyze remaining compressed blocks\n");
    printf("   2. Parse binary record structures\n");
    printf("   3. Extract actual PLC logic\n");
    printf("   4. Implement binary ACD writer for round-trip\n");
    
    return 0;
} 