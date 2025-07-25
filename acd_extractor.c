#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <zlib.h>
#include <sys/stat.h>

#define CHUNK_SIZE 16384
#define MAX_DECOMP_SIZE (10 * 1024 * 1024) // 10MB max per block

// Extract and decompress a GZIP block
int extract_gzip_block(FILE *file, long offset, int block_num) {
    fseek(file, offset, SEEK_SET);
    
    // Read GZIP header
    unsigned char header[10];
    if (fread(header, 1, 10, file) != 10) {
        return -1;
    }
    
    // Verify GZIP magic
    if (header[0] != 0x1F || header[1] != 0x8B) {
        return -1;
    }
    
    // Create output directory
    mkdir("extracted_blocks", 0755);
    
    // Read compressed data (we'll read up to 1MB for each block)
    unsigned char *compressed = malloc(1024 * 1024);
    fseek(file, offset, SEEK_SET);
    size_t comp_size = fread(compressed, 1, 1024 * 1024, file);
    
    // Setup decompression
    z_stream strm = {0};
    strm.next_in = compressed;
    strm.avail_in = comp_size;
    
    unsigned char *decompressed = malloc(MAX_DECOMP_SIZE);
    strm.next_out = decompressed;
    strm.avail_out = MAX_DECOMP_SIZE;
    
    // Initialize with automatic header detection
    int ret = inflateInit2(&strm, 16 + MAX_WBITS);
    if (ret != Z_OK) {
        free(compressed);
        free(decompressed);
        return -1;
    }
    
    // Decompress
    ret = inflate(&strm, Z_FINISH);
    size_t decomp_size = strm.total_out;
    inflateEnd(&strm);
    
    if (ret == Z_STREAM_END || ret == Z_OK) {
        // Save decompressed data
        char filename[256];
        sprintf(filename, "extracted_blocks/block_%03d_offset_0x%lx.bin", block_num, offset);
        
        FILE *out = fopen(filename, "wb");
        if (out) {
            fwrite(decompressed, 1, decomp_size, out);
            fclose(out);
            
            printf("✅ Block %d: Decompressed %zu bytes → %zu bytes\n", 
                   block_num, strm.total_in, decomp_size);
            printf("   Saved to: %s\n", filename);
            
            // Analyze content
            printf("   Content preview: ");
            int printable = 1;
            for (int i = 0; i < 50 && i < decomp_size; i++) {
                if (decompressed[i] < 0x20 || decompressed[i] > 0x7E) {
                    if (decompressed[i] != '\n' && decompressed[i] != '\r' && decompressed[i] != '\t') {
                        printable = 0;
                        break;
                    }
                }
            }
            
            if (printable && decomp_size > 0) {
                printf("\"");
                for (int i = 0; i < 50 && i < decomp_size; i++) {
                    if (decompressed[i] >= 0x20 && decompressed[i] <= 0x7E) {
                        printf("%c", decompressed[i]);
                    }
                }
                printf("...\"\n");
            } else {
                printf("[Binary data]\n");
            }
            
            // Check for XML
            if (decomp_size > 5 && memcmp(decompressed, "<?xml", 5) == 0) {
                printf("   🔍 XML content detected!\n");
                
                // Save as XML
                sprintf(filename, "extracted_blocks/block_%03d_offset_0x%lx.xml", block_num, offset);
                out = fopen(filename, "w");
                if (out) {
                    fwrite(decompressed, 1, decomp_size, out);
                    fclose(out);
                    printf("   💾 Also saved as: %s\n", filename);
                }
            }
        }
    } else {
        printf("❌ Block %d: Decompression failed (code %d)\n", block_num, ret);
    }
    
    free(compressed);
    free(decompressed);
    return decomp_size > 0 ? 0 : -1;
}

// Search for database files
void find_database_files(FILE *file, long start_offset) {
    printf("\n🔍 Searching for database file structures...\n");
    
    fseek(file, start_offset, SEEK_SET);
    unsigned char buffer[8192];
    long offset = start_offset;
    
    while (fread(buffer, 1, sizeof(buffer), file) > 0) {
        for (int i = 0; i < sizeof(buffer) - 100; i++) {
            // Look for "Controller" with length prefix (common in binary formats)
            if (buffer[i] == 0x0A && buffer[i+1] == 0x00 && 
                memcmp(buffer + i + 2, "Controller", 10) == 0) {
                printf("   Found 'Controller' structure at: 0x%lx\n", offset + i);
            }
            
            // Look for "Program" 
            if (memcmp(buffer + i, "Program", 7) == 0) {
                printf("   Found 'Program' at: 0x%lx\n", offset + i);
            }
            
            // Look for "Routine"
            if (memcmp(buffer + i, "Routine", 7) == 0) {
                printf("   Found 'Routine' at: 0x%lx\n", offset + i);
            }
            
            // Look for "DataType"
            if (memcmp(buffer + i, "DataType", 8) == 0) {
                printf("   Found 'DataType' at: 0x%lx\n", offset + i);
            }
        }
        offset += sizeof(buffer);
        
        // Just scan first 100KB
        if (offset - start_offset > 100000) break;
    }
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <acd_file>\n", argv[0]);
        return 1;
    }
    
    printf("🚀 ACD Extractor v2.0\n");
    printf("====================\n\n");
    
    FILE *file = fopen(argv[1], "rb");
    if (!file) {
        perror("Failed to open file");
        return 1;
    }
    
    // Get file size
    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    rewind(file);
    
    printf("📄 File: %s\n", argv[1]);
    printf("📏 Size: %.2f MB\n\n", file_size / (1024.0 * 1024.0));
    
    // Find binary start (skip text header)
    char line[1024];
    long binary_start = 0;
    while (fgets(line, sizeof(line), file)) {
        int is_binary = 0;
        for (int i = 0; line[i]; i++) {
            if ((unsigned char)line[i] < 0x20 && line[i] != '\r' && line[i] != '\n' && line[i] != '\t') {
                is_binary = 1;
                break;
            }
        }
        if (is_binary) {
            binary_start = ftell(file) - strlen(line);
            break;
        }
    }
    
    printf("📍 Binary data starts at: 0x%lx\n\n", binary_start);
    
    // Extract GZIP blocks
    printf("🗜️  Extracting compressed blocks...\n\n");
    
    fseek(file, binary_start, SEEK_SET);
    unsigned char buffer[4096];
    long offset = binary_start;
    int block_count = 0;
    
    while (offset < file_size - 10) {
        fseek(file, offset, SEEK_SET);
        size_t bytes_read = fread(buffer, 1, sizeof(buffer), file);
        
        for (size_t i = 0; i < bytes_read - 10; i++) {
            if (buffer[i] == 0x1F && buffer[i+1] == 0x8B) {
                extract_gzip_block(file, offset + i, ++block_count);
                if (block_count >= 20) goto done; // Extract first 20 blocks
            }
        }
        offset += bytes_read - 10;
    }
    
done:
    printf("\n📊 Extracted %d compressed blocks\n", block_count);
    
    // Search for database structures
    find_database_files(file, binary_start);
    
    fclose(file);
    
    printf("\n✅ Extraction complete! Check 'extracted_blocks' directory\n");
    return 0;
} 