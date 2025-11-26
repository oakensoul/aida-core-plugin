FROM aida-test-base:latest

WORKDIR /home/tester/projects/nodejs-test-project

# Copy sample Node.js project
COPY --chown=tester:tester sample-project/ .

# Install dependencies
RUN npm install

# Initialize git repository
RUN git init \
    && git add . \
    && git commit -m "Initial commit: Node.js test project"

CMD ["/bin/bash"]
