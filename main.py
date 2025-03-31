#!/usr/bin/env python3
import os
import sys
import argparse
from pytox86.utils import run_compiler

def main():
    parser = argparse.ArgumentParser(description="Python to x86 Assembly Transpiler")
    
    parser.add_argument("input_file", help="Python source file")
    parser.add_argument("-o", "--output", help="Output assembly file")
    parser.add_argument("-O", "--optimize", type=int, choices=[0, 1, 2, 3], default=1,
                      help="Optimization level (0-3)")
    parser.add_argument("--dump-ast", action="store_true", help="Dump AST")
    parser.add_argument("--dump-tokens", action="store_true", help="Dump tokens")
    parser.add_argument("--dump-ir", action="store_true", help="Dump intermediate representation")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist", file=sys.stderr)
        return 1
    
    # Print which file we're trying to compile
    print(f"Compiling file: {args.input_file}")
    
    with open(args.input_file, 'r') as f:
        print(f"File content:\n{'='*40}")
        print(f.read())
        print(f"{'='*40}\n")
    
    # Always enable debug output to help troubleshoot any issues
    return run_compiler(
        args.input_file,
        args.output,
        args.optimize,
        True,  # Always dump AST
        True,  # Always dump tokens
        True   # Always dump IR
    )

if __name__ == "__main__":
    sys.exit(main())
