#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <zlib.h>

#define BUFFER_SIZE 4096
#define GZIP_MAGIC 0x8b1f

// Structure to hold ACD file info
typedef struct {
    FILE *file;
    long file_size;
    char *header_text;
    long binary_start;
} ACD_File;

// Structure for a compressed block
typedef struct {
    long offset;
    uint32_t compressed_size;
    uint32_t uncompressed_size;
    unsigned char *data;
} CompressedBlock;

// Read the text header
int read_text_header(ACD_File *acd) {
    char buffer[BUFFER_SIZE];
    int header_lines = 0;
    long pos = 0;
    
    printf("📖 Reading ACD text header...\n");
    
    while (fgets(buffer, sizeof(buffer), acd->file)) {
        // Check if we've hit binary data (non-printable characters)
        int is_text = 1;
        for (int i = 0; buffer[i] && buffer[i] != '\n'; i++) {
            if ((unsigned char)buffer[i] < 0x20 && buffer[i] != '\r' && buffer[i] != '\n' && buffer[i] != '\t') {
                is_text = 0;
                break;
            }
        }
        
        if (!is_text) {
            acd->binary_start = pos;
            printf("✅ Found binary data start at offset: 0x%lx (%ld)\n", pos, pos);
            break;
        }
        
        if (header_lines < 5) {
            printf("   %s", buffer);
        }
        
        pos = ftell(acd->file);
        header_lines++;
    }
    
    printf("📊 Header lines: %d\n", header_lines);
    return 0;
}

// Search for GZIP compressed blocks
int find_compressed_blocks(ACD_File *acd) {
    fseek(acd->file, acd->binary_start, SEEK_SET);
    
    unsigned char buffer[BUFFER_SIZE];
    long offset = acd->binary_start;
    int block_count = 0;
    
    printf("\n🔍 Searching for compressed blocks...\n");
    
    while (offset < acd->file_size - 2) {
        fseek(acd->file, offset, SEEK_SET);
        size_t bytes_read = fread(buffer, 1, BUFFER_SIZE, acd->file);
        
        for (size_t i = 0; i < bytes_read - 10; i++) {
            // Check for GZIP magic number (1F 8B)
            if (buffer[i] == 0x1F && buffer[i+1] == 0x8B) {
                long block_offset = offset + i;
                
                // Read GZIP header
                unsigned char method = buffer[i+2];
                unsigned char flags = buffer[i+3];
                
                printf("\n🗜️  Found GZIP block #%d at offset: 0x%lx\n", ++block_count, block_offset);
                printf("   Compression method: %02x\n", method);
                printf("   Flags: %02x\n", flags);
                
                // Try to decompress a small portion to verify
                if (i + 100 < bytes_read) {
                    unsigned char test_decomp[1024];
                    z_stream strm = {0};
                    strm.next_in = buffer + i;
                    strm.avail_in = 100;
                    strm.next_out = test_decomp;
                    strm.avail_out = sizeof(test_decomp);
                    
                    if (inflateInit2(&strm, 16 + MAX_WBITS) == Z_OK) {
                        int ret = inflate(&strm, Z_NO_FLUSH);
                        if (ret == Z_OK || ret == Z_STREAM_END) {
                            printf("   ✅ Valid GZIP data (decompressed %lu bytes)\n", strm.total_out);
                        }
                        inflateEnd(&strm);
                    }
                }
                
                if (block_count >= 10) {
                    printf("\n... (showing first 10 blocks)\n");
                    return block_count;
                }
            }
        }
        
        offset += bytes_read - 10; // Overlap to catch boundaries
    }
    
    return block_count;
}

// Analyze the file structure
void analyze_structure(ACD_File *acd) {
    printf("\n📊 Analyzing ACD file structure...\n");
    
    // Look for specific patterns
    fseek(acd->file, acd->binary_start, SEEK_SET);
    
    unsigned char buffer[4096];
    fread(buffer, 1, sizeof(buffer), acd->file);
    
    // Look for database signatures
    printf("\n🔍 Looking for database signatures...\n");
    
    for (int i = 0; i < sizeof(buffer) - 16; i++) {
        // Check for "Comps" database
        if (memcmp(buffer + i, "Comps", 5) == 0) {
            printf("   Found 'Comps' at offset: 0x%lx\n", acd->binary_start + i);
        }
        // Check for "Controller" 
        if (memcmp(buffer + i, "Controller", 10) == 0) {
            printf("   Found 'Controller' at offset: 0x%lx\n", acd->binary_start + i);
        }
        // Check for XML signatures
        if (memcmp(buffer + i, "<?xml", 5) == 0) {
            printf("   Found XML at offset: 0x%lx\n", acd->binary_start + i);
        }
    }
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <acd_file>\n", argv[0]);
        return 1;
    }
    
    ACD_File acd = {0};
    
    printf("🚀 ACD Binary Parser v1.0\n");
    printf("========================\n\n");
    
    // Open file
    acd.file = fopen(argv[1], "rb");
    if (!acd.file) {
        perror("Failed to open file");
        return 1;
    }
    
    // Get file size
    fseek(acd.file, 0, SEEK_END);
    acd.file_size = ftell(acd.file);
    rewind(acd.file);
    
    printf("📄 File: %s\n", argv[1]);
    printf("📏 Size: %.2f MB (%ld bytes)\n\n", acd.file_size / (1024.0 * 1024.0), acd.file_size);
    
    // Read header
    read_text_header(&acd);
    
    // Find compressed blocks
    int blocks = find_compressed_blocks(&acd);
    printf("\n📦 Total compressed blocks found: %d\n", blocks);
    
    // Analyze structure
    analyze_structure(&acd);
    
    fclose(acd.file);
    
    printf("\n✅ Analysis complete!\n");
    return 0;
} 