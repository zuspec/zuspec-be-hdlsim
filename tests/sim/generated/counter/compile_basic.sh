#!/bin/bash
# Phase 1: Basic Verilator compilation WITHOUT Python integration
# This validates the generated SystemVerilog structure

set -e

echo "================================"
echo "BASIC COMPILATION TEST"
echo "================================"
echo ""
echo "Testing generated SV structure (no Python yet)"
echo ""

# Just the HDL modules, no testbench wrapper with Python
SOURCES="
    counter.sv
    CounterControlXtor.sv
    CounterTB.sv
"

echo "Sources:"
for src in $SOURCES; do
    echo "  - $src"
done
echo ""

# Verilator lint/syntax check
echo "Running Verilator lint..."
verilator --lint-only -Wall $SOURCES

echo ""
echo "✅ Basic SV structure is valid!"
echo ""
echo "Next: Try compilation with testbench wrapper (but skip Python)"

