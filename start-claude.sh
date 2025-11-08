#!/bin/bash

# Claude Code Start Script
# For management container with proper permissions

echo "🤖 Starting Claude Code with continue and skip permissions..."
echo "   --continue: Resume previous session"
echo "   --danger-skip-permissions: Skip permission checks"
echo ""

# Start Claude Code with the requested flags
claude --continue --dangerously-skip-permissions 

echo ""
echo "Claude session ended."

