FROM aida-test-base:latest

USER root

# Install Python for mixed monorepo
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

USER tester
WORKDIR /home/tester/projects/monorepo-test-project

# Copy sample monorepo project
COPY --chown=tester:tester sample-project/ .

# Install root dependencies
RUN npm install

# Install Python package dependencies
RUN cd packages/python-service && \
    python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Initialize git repository
RUN git init \
    && git add . \
    && git commit -m "Initial commit: Monorepo test project"

CMD ["/bin/bash"]
