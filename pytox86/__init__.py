import os
import sys

from .lexer import Lexer
from .parser import Parser
from .analyzer import SemanticAnalyzer
from .irgen import IRGenerator
from .optim import Optimizer
from .codegen import X86Generator

class Transpiler:
    def __init__(self, optimization_level=1):
        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = SemanticAnalyzer()
        self.irgen = IRGenerator()
        self.optimizer = Optimizer(optimization_level)
        self.codegen = X86Generator()
        
    def transpile(self, source_code, filename="<unknown>"):
        tokens = self.lexer.tokenize(source_code)
        ast = self.parser.parse(tokens)
        self.analyzer.analyze(ast)
        ir = self.irgen.generate(ast)
        optimized_ir = self.optimizer.optimize(ir)
        assembly = self.codegen.generate(optimized_ir)
        return assembly

    def transpile_file(self, input_file, output_file=None):
        with open(input_file, 'r') as f:
            source_code = f.read()
            
        assembly = self.transpile(source_code, input_file)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(assembly)
            return f"Assembly written to {output_file}"
        else:
            return assembly
