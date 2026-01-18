#!/bin/bash

# Flowex Ralph Loop Script
# Autonomous AI coding loop for P&ID digitization platform
# Based on Geoff Huntley's Ralph methodology

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_MODEL="opus"
MAX_ITERATIONS=${2:-0}  # 0 = unlimited
ITERATION=0

# Mode selection
MODE=${1:-build}
case $MODE in
    plan|planning)
        PROMPT_FILE="PROMPT_plan.md"
        echo -e "${BLUE}🗺️  PLANNING MODE${NC} - Generating/updating implementation plan"
        ;;
    build|building|"")
        PROMPT_FILE="PROMPT_build.md"
        echo -e "${GREEN}🔨 BUILDING MODE${NC} - Implementing from plan"
        ;;
    *)
        # If first arg is a number, treat as max iterations for build mode
        if [[ $MODE =~ ^[0-9]+$ ]]; then
            MAX_ITERATIONS=$MODE
            PROMPT_FILE="PROMPT_build.md"
            echo -e "${GREEN}🔨 BUILDING MODE${NC} - Max $MAX_ITERATIONS iterations"
        else
            echo -e "${RED}Unknown mode: $MODE${NC}"
            echo "Usage: ./loop.sh [plan|build] [max_iterations]"
            echo "  ./loop.sh           # Build mode, unlimited"
            echo "  ./loop.sh plan      # Planning mode"
            echo "  ./loop.sh build 20  # Build mode, max 20 iterations"
            echo "  ./loop.sh 20        # Build mode, max 20 iterations"
            exit 1
        fi
        ;;
esac

# Check required files exist
if [ ! -f "$PROMPT_FILE" ]; then
    echo -e "${RED}Error: $PROMPT_FILE not found${NC}"
    exit 1
fi

if [ ! -f "AGENTS.md" ]; then
    echo -e "${RED}Error: AGENTS.md not found${NC}"
    exit 1
fi

# Main loop
echo -e "${YELLOW}Starting Ralph loop...${NC}"
echo "Press Ctrl+C to stop"
echo "---"

while true; do
    ITERATION=$((ITERATION + 1))
    
    # Check max iterations
    if [ $MAX_ITERATIONS -gt 0 ] && [ $ITERATION -gt $MAX_ITERATIONS ]; then
        echo -e "${YELLOW}Max iterations ($MAX_ITERATIONS) reached. Stopping.${NC}"
        break
    fi
    
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Iteration $ITERATION${NC} $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    
    # Run Claude with the prompt
    # Options:
    # -p: headless mode (non-interactive)
    # --dangerously-skip-permissions: bypass permission prompts for automation
    # --model: specify model (opus for complex tasks, sonnet for speed)
    
    cat "$PROMPT_FILE" | claude -p \
        --dangerously-skip-permissions \
        --model "$DEFAULT_MODEL" \
        --verbose \
        2>&1 | tee -a "ralph_log_$(date '+%Y%m%d').txt"
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo -e "${RED}Claude exited with code $EXIT_CODE${NC}"
        echo "Continuing to next iteration in 5 seconds..."
        sleep 5
    fi
    
    # Push changes after each iteration (optional - uncomment if desired)
    # if git status --porcelain | grep -q .; then
    #     echo -e "${YELLOW}Pushing changes...${NC}"
    #     git push origin $(git branch --show-current) 2>/dev/null || true
    # fi
    
    echo ""
    echo -e "${GREEN}Iteration $ITERATION complete. Starting fresh context...${NC}"
    echo ""
    
    # Small delay between iterations
    sleep 2
done

echo -e "${GREEN}Ralph loop completed after $ITERATION iterations.${NC}"