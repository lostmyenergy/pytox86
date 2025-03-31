import os
import sys
import argparse
from typing import List, Dict, Any, Optional
from .lexer import Lexer, Token, TokenType
from .parser import Parser
from .analyzer import SemanticAnalyzer
from .irgen import IRGenerator
from .optim import Optimizer
from .codegen import X86Generator

def print_ast(node, indent=0):
    prefix = "  " * indent
    if node is None:
        print(f"{prefix}None")
        return
        
    if isinstance(node, list):
        print(f"{prefix}[")
        for item in node:
            print_ast(item, indent + 1)
        print(f"{prefix}]")
        return
        
    class_name = node.__class__.__name__
    print(f"{prefix}{class_name}(")
    
    for key, value in node.__dict__.items():
        if isinstance(value, list) and value and hasattr(value[0], "__dict__"):
            print(f"{prefix}  {key}=[")
            for item in value:
                print_ast(item, indent + 2)
            print(f"{prefix}  ]")
        elif hasattr(value, "__dict__"):
            print(f"{prefix}  {key}=")
            print_ast(value, indent + 2)
        else:
            print(f"{prefix}  {key}={value}")
            
    print(f"{prefix})")

def print_ir(program):
    for func in program.functions:
        print(f"Function {func.name}({', '.join(func.params)}):")
        print(f"  Local vars: {func.local_vars}")
        
        for block in func.blocks:
            print(f"  {block.label}:")
            
            for instr in block.instructions:
                args_str = ", ".join(str(arg) for arg in instr.args)
                result_str = f" -> {instr.result}" if instr.result else ""
                print(f"    {instr.op} {args_str}{result_str}")

def dump_tokens(tokens: List[Token]):
    for token in tokens:
        print(f"{token.type.name:12} '{token.value}' (line {token.line}, col {token.column})")
        
def run_compiler(input_file, output_file=None, optimization_level=1, 
                 dump_ast=False, dump_tokens_flag=False, dump_ir=False):
    from pytox86 import Transpiler
    
    transpiler = Transpiler(optimization_level=optimization_level)
    
    try:
        with open(input_file, 'r') as f:
            source_code = f.read()
            
        if dump_tokens_flag:
            lexer = Lexer()
            tokens = lexer.tokenize(source_code)
            print("=== TOKENS ===")
            dump_tokens(tokens)
            print()
            
        if dump_ast:
            lexer = Lexer()
            parser = Parser()
            tokens = lexer.tokenize(source_code)
            ast = parser.parse(tokens)
            print("=== AST ===")
            print_ast(ast)
            print()
            
        if dump_ir:
            lexer = Lexer()
            parser = Parser()
            analyzer = SemanticAnalyzer()
            irgen = IRGenerator()
            tokens = lexer.tokenize(source_code)
            ast = parser.parse(tokens)
            analyzer.analyze(ast)
            ir = irgen.generate(ast)
            print("=== IR ===")
            print_ir(ir)
            print()
            
        assembly = transpiler.transpile_file(input_file, output_file)
        
        if output_file:
            print(f"Assembly code written to {output_file}")
        else:
            print(assembly)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
        
    return 0
