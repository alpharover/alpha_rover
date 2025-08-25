#!/bin/bash

# Setup script to add 'oak' command to PATH

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BASHRC="$HOME/.bashrc"

# Add to PATH if not already there
if ! grep -q "oak_multi_bringup/scripts" "$BASHRC"; then
    echo "" >> "$BASHRC"
    echo "# OAK Multi Sensor Scripts" >> "$BASHRC"
    echo "export PATH=\"$SCRIPT_DIR:\$PATH\"" >> "$BASHRC"
    echo "Added oak command to PATH in ~/.bashrc"
    echo "Run 'source ~/.bashrc' or open a new terminal to use 'oak' command"
else
    echo "oak command already in PATH"
fi

echo ""
echo "Usage after sourcing:"
echo "  oak           - Launch all sensors"
echo "  oak foxglove  - Launch with Foxglove bridge"
echo "  oak stop      - Stop all processes"