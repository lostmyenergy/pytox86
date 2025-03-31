from typing import Dict, Set, List
from .parser import ASTNode, Program, FunctionDef, Return, Assign, AugAssign
from .parser import For, While, If, BinOp, UnaryOp, Call, Constant, Name, Compare

class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent
        
    def define(self, name, type_info=None):
        self.symbols[name] = type_info
        
    def resolve(self, name):
        if name in self.symbols:
            return self.symbols[name]
        
        if self.parent:
            return self.parent.resolve(name)
            
        return None
        
    def contains(self, name, local_only=False):
        if name in self.symbols:
            return True
            
        if not local_only and self.parent:
            return self.parent.contains(name)
            
        return False

class SemanticAnalyzer:
    def __init__(self):
        self.global_scope = SymbolTable()
        self.current_scope = self.global_scope
        self.errors = []
        
    def analyze(self, ast):
        self.visit(ast)
        
        if self.errors:
            error_message = "\n".join(self.errors)
            raise Exception(f"Semantic analysis failed:\n{error_message}")
            
        return ast
        
    def visit(self, node):
        method_name = f"visit_{node.__class__.__name__}"
        method = getattr(self, method_name, self.generic_visit)
        return method(node)
        
    def generic_visit(self, node):
        if isinstance(node, list):
            for item in node:
                self.visit(item)
        elif hasattr(node, "__dict__"):
            for value in node.__dict__.values():
                if isinstance(value, (ASTNode, list)):
                    self.visit(value)
        
    def visit_Program(self, node):
        for stmt in node.body:
            self.visit(stmt)
            
    def visit_FunctionDef(self, node):
        self.global_scope.define(node.name, "function")
        previous_scope = self.current_scope
        self.current_scope = SymbolTable(previous_scope)
        
        for param in node.params:
            self.current_scope.define(param, "parameter")
            
        for stmt in node.body:
            self.visit(stmt)
            
        self.current_scope = previous_scope
        
    def visit_Return(self, node):
        if node.value:
            self.visit(node.value)
            
    def visit_Assign(self, node):
        self.visit(node.value)
        
        for target in node.targets:
            if isinstance(target, Name):
                if not self.current_scope.contains(target.id):
                    self.current_scope.define(target.id, "variable")
            else:
                self.visit(target)
                
    def visit_AugAssign(self, node):
        self.visit(node.value)
        
        if isinstance(node.target, Name):
            if not self.current_scope.contains(node.target.id):
                self.errors.append(f"Variable '{node.target.id}' used before assignment")
        else:
            self.visit(node.target)
            
    def visit_For(self, node):
        self.visit(node.iter)
        
        previous_scope = self.current_scope
        self.current_scope = SymbolTable(previous_scope)
        
        if isinstance(node.target, Name):
            self.current_scope.define(node.target.id, "variable")
        else:
            self.visit(node.target)
            
        for stmt in node.body:
            self.visit(stmt)
            
        self.current_scope = previous_scope
        
    def visit_While(self, node):
        self.visit(node.test)
        
        previous_scope = self.current_scope
        self.current_scope = SymbolTable(previous_scope)
        
        for stmt in node.body:
            self.visit(stmt)
            
        self.current_scope = previous_scope
        
    def visit_If(self, node):
        self.visit(node.test)
        
        previous_scope = self.current_scope
        self.current_scope = SymbolTable(previous_scope)
        
        for stmt in node.body:
            self.visit(stmt)
            
        self.current_scope = previous_scope
        
        if node.orelse:
            previous_scope = self.current_scope
            self.current_scope = SymbolTable(previous_scope)
            
            for stmt in node.orelse:
                self.visit(stmt)
                
            self.current_scope = previous_scope
            
    def visit_BinOp(self, node):
        self.visit(node.left)
        self.visit(node.right)
        
    def visit_UnaryOp(self, node):
        self.visit(node.operand)
        
    def visit_Call(self, node):
        if isinstance(node.func, Name):
            if not self.global_scope.contains(node.func.id) and not self.current_scope.contains(node.func.id):
                builtin_functions = {"print", "len", "int", "float", "str", "range", "input"}
                
                if node.func.id not in builtin_functions:
                    self.errors.append(f"Function '{node.func.id}' is not defined")
                    
        else:
            self.visit(node.func)
            
        for arg in node.args:
            self.visit(arg)
            
    def visit_Constant(self, node):
        pass
        
    def visit_Name(self, node):
        if node.ctx == "Load" and not self.current_scope.contains(node.id):
            builtin_constants = {"True", "False", "None"}
            
            if node.id not in builtin_constants:
                self.errors.append(f"Variable '{node.id}' used before assignment")
                
    def visit_Compare(self, node):
        self.visit(node.left)
        
        for comparator in node.comparators:
            self.visit(comparator)
