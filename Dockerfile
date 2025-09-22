FROM debian:bookworm-slim

# Install RawTherapee and dependencies
RUN apt-get update && apt-get install -y \
    rawtherapee \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /workspace

# Set user to avoid permission issues
RUN useradd -m -u 1000 rawuser
USER rawuser

# Default command
CMD ["rawtherapee-cli", "--help"]