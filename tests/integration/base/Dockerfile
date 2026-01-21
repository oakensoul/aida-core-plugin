FROM ubuntu:24.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install base dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    ca-certificates \
    gnupg \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for Claude Code CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for testing
RUN useradd -m -s /bin/bash -G sudo tester \
    && echo "tester:tester" | chpasswd \
    && echo "tester ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to tester user
USER tester
WORKDIR /home/tester

# Install Claude Code CLI
RUN curl -fsSL https://claude.ai/install.sh | bash

# Add Claude CLI to PATH (install.sh typically installs to ~/.local/bin)
ENV PATH="/home/tester/.local/bin:${PATH}"

# Configure git with dummy user (needed for git operations)
RUN git config --global user.email "tester@example.com" \
    && git config --global user.name "AIDA Tester"

# Create project directory
RUN mkdir -p /home/tester/project && \
    cd /home/tester/project && \
    git init

# Set up environment
ENV HOME=/home/tester
ENV USER=tester
WORKDIR /home/tester/project

CMD ["/bin/bash"]
