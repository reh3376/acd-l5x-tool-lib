# Use Python slim image for smaller size
FROM python:3.12-slim

# Set metadata labels as per OCI specification
LABEL org.opencontainers.image.source=https://github.com/reh3376/acd-l5x-tool-lib
LABEL org.opencontainers.image.description="PLC Format Converter - Convert between ACD and L5X formats"
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.title="PLC Format Converter"
LABEL org.opencontainers.image.vendor="reh3376"

# Set working directory
WORKDIR /app

# Copy package files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir -e .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash plcuser
USER plcuser

# Set up volume for file operations
VOLUME ["/data"]
WORKDIR /data

# Default command shows help
CMD ["plc-convert", "--help"] 