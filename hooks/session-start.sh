#!/bin/bash

# AIDA Session Start Hook
# Loads the active personality at the start of each session

PERSONALITY_FILE="$HOME/.claude/config/personality.txt"

# Check if user has configured a personality
if [ -f "$PERSONALITY_FILE" ]; then
    PERSONALITY=$(cat "$PERSONALITY_FILE" | tr -d '[:space:]')

    if [ -n "$PERSONALITY" ]; then
        # Find the personality agent file in plugins cache
        AGENT_FILE="$HOME/.claude/plugins/cache/aida-personality-$PERSONALITY/agents/$PERSONALITY.md"

        if [ -f "$AGENT_FILE" ]; then
            echo "<session-start-hook>"
            echo "# AIDA Personality: $PERSONALITY"
            echo ""
            cat "$AGENT_FILE"
            echo ""
            echo "</session-start-hook>"
        else
            echo "<!-- AIDA: Personality '$PERSONALITY' configured but agent file not found at $AGENT_FILE -->" >&2
        fi
    fi
fi