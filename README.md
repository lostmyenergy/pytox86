# PyToX86 Transpiler

A sophisticated Python to x86 assembly transpiler demonstrating advanced compiler design principles.

## Features

- Converts Python code to optimized x86 assembly
- Multi-stage compilation pipeline
- AST-based parsing with full context sensitivity
- Intermediate representation (IR) for optimization
- Multiple optimization levels
- Register allocation
- Basic control flow structures (if/else, for, while)
- Function definitions and calls
- Arithmetic and logical operations

## Architecture

The transpiler follows a classic compiler architecture with multiple stages:

1. **Lexical Analysis**: Tokenizes the input Python code
2. **Parsing**: Builds an Abstract Syntax Tree (AST) from tokens
3. **Semantic Analysis**: Performs type checking and variable resolution
4. **IR Generation**: Transforms the AST into an Intermediate Representation
5. **Optimization**: Applies various optimization passes to the IR
6. **Code Generation**: Produces the final x86 assembly code


