FROM aida-test-base:latest

WORKDIR /home/tester/projects/aida-test-project

# Copy sample AIDA project structure
COPY --chown=tester:tester sample-project/ .

# Initialize git repository
RUN git init \
    && git add . \
    && git commit -m "Initial commit: AIDA test project"

# Create .claude directory structure
RUN mkdir -p .claude/commands .claude/skills .claude/agents .claude/knowledge

WORKDIR /home/tester/projects/aida-test-project

CMD ["/bin/bash"]
