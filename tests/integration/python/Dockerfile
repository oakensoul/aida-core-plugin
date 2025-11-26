FROM aida-test-base:latest

USER root

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

USER tester
WORKDIR /home/tester/projects/python-test-project

# Copy sample Python project
COPY --chown=tester:tester sample-project/ .

# Create virtual environment and install dependencies
RUN python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --no-cache-dir -r requirements.txt

# Initialize git repository
RUN git init \
    && git add . \
    && git commit -m "Initial commit: Python test project"

CMD ["/bin/bash"]
