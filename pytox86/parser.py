from dataclasses import dataclass, field
from typing import List as ListType, Dict as DictType, Any, Optional, Union
from .lexer import TokenType, Token

class ASTNode:
    pass

@dataclass
class Program(ASTNode):
    body: ListType[ASTNode]

@dataclass
class FunctionDef(ASTNode):
    name: str
    params: ListType[str]
    body: ListType[ASTNode]
    decorators: ListType[ASTNode] = field(default_factory=list)
    returns: Optional[ASTNode] = None

@dataclass
class Return(ASTNode):
    value: Optional[ASTNode] = None

@dataclass
class Assign(ASTNode):
    targets: ListType[ASTNode]
    value: ASTNode

@dataclass
class AugAssign(ASTNode):
    target: ASTNode
    op: str
    value: ASTNode

@dataclass
class For(ASTNode):
    target: ASTNode
    iter: ASTNode
    body: ListType[ASTNode]
    orelse: ListType[ASTNode] = field(default_factory=list)

@dataclass
class While(ASTNode):
    test: ASTNode
    body: ListType[ASTNode]
    orelse: ListType[ASTNode] = field(default_factory=list)

@dataclass
class If(ASTNode):
    test: ASTNode
    body: ListType[ASTNode]
    orelse: ListType[ASTNode] = field(default_factory=list)

@dataclass
class BinOp(ASTNode):
    left: ASTNode
    op: str
    right: ASTNode

@dataclass
class UnaryOp(ASTNode):
    op: str
    operand: ASTNode

@dataclass
class Call(ASTNode):
    func: ASTNode
    args: ListType[ASTNode]
    keywords: DictType[str, ASTNode] = field(default_factory=dict)

@dataclass
class Constant(ASTNode):
    value: Any
    kind: Optional[str] = None

@dataclass
class Name(ASTNode):
    id: str
    ctx: str = "Load"

@dataclass
class List(ASTNode):
    elts: ListType[ASTNode]
    ctx: str = "Load"

@dataclass
class Dict(ASTNode):
    keys: ListType[ASTNode]
    values: ListType[ASTNode]

@dataclass
class Compare(ASTNode):
    left: ASTNode
    ops: ListType[str]
    comparators: ListType[ASTNode]

@dataclass
class Pass(ASTNode):
    pass

class Parser:
    def __init__(self):
        self.tokens = []
        self.current = 0
        
    def parse(self, tokens):
        self.tokens = tokens
        self.current = 0
        return self.parse_program()
        
    def parse_program(self):
        statements = []
        
        # Use is_at_end() instead of match() to avoid advancing the token pointer
        while not self.is_at_end():
            stmt = self.parse_statement()
            if stmt is not None:
                statements.append(stmt)
                
            # Safety check to prevent infinite loop
            if self.current >= len(self.tokens) - 1:
                break
            
        return Program(statements)
    
    def parse_statement(self):
        # Check for EOF or trailing newlines at the end of file
        if self.check(TokenType.EOF):
            return None
        elif self.check(TokenType.NEWLINE):
            self.advance()  # Skip newlines
            return None
            
        # Parse statements
        if self.check(TokenType.KEYWORD, "def"):
            return self.parse_function_def()
        elif self.check(TokenType.KEYWORD, "return"):
            return self.parse_return()
        elif self.check(TokenType.KEYWORD, "if"):
            return self.parse_if()
        elif self.check(TokenType.KEYWORD, "while"):
            return self.parse_while()
        elif self.check(TokenType.KEYWORD, "for"):
            return self.parse_for()
        elif self.check(TokenType.KEYWORD, "pass"):
            self.advance()
            if self.check(TokenType.NEWLINE):
                self.advance()
            return Pass()
        else:
            # Try parsing an expression statement, but handle errors gracefully
            try:
                return self.parse_expression_statement()
            except SyntaxError as e:
                if self.check(TokenType.EOF) or self.check(TokenType.NEWLINE):
                    return None  # Safely exit at EOF
                else:
                    raise  # Re-raise the exception if it's not at EOF
    
    def parse_function_def(self):
        self.consume(TokenType.KEYWORD, "Expected 'def'")
        name = self.consume(TokenType.IDENTIFIER, "Expected function name").value
        self.consume(TokenType.PUNCTUATION, "Expected '('")
        
        params = []
        if not self.check(TokenType.PUNCTUATION, ")"):
            params.append(self.consume(TokenType.IDENTIFIER, "Expected parameter name").value)
            
            while self.match(TokenType.PUNCTUATION, ","):
                params.append(self.consume(TokenType.IDENTIFIER, "Expected parameter name").value)
                
        self.consume(TokenType.PUNCTUATION, "Expected ')'")
        self.consume(TokenType.PUNCTUATION, "Expected ':'")
        self.consume(TokenType.NEWLINE, "Expected newline")
        self.consume(TokenType.INDENT, "Expected indented block")
        
        body = []
        while not self.check(TokenType.DEDENT) and not self.check(TokenType.EOF):
            stmt = self.parse_statement()
            if stmt is not None:
                body.append(stmt)
            
        if self.check(TokenType.DEDENT):
            self.advance()
            
        return FunctionDef(name, params, body)
    
    def parse_return(self):
        self.consume(TokenType.KEYWORD, "Expected 'return'")
        
        if self.check(TokenType.NEWLINE):
            self.consume(TokenType.NEWLINE, "Expected newline")
            return Return()
            
        value = self.parse_expression()
        self.consume(TokenType.NEWLINE, "Expected newline")
        return Return(value)
    
    def parse_if(self):
        self.consume(TokenType.KEYWORD, "Expected 'if'")
        test = self.parse_expression()
        self.consume(TokenType.PUNCTUATION, "Expected ':'")
        self.consume(TokenType.NEWLINE, "Expected newline")
        self.consume(TokenType.INDENT, "Expected indented block")
        
        body = []
        while not self.check(TokenType.DEDENT) and not self.check(TokenType.EOF):
            stmt = self.parse_statement()
            if stmt is not None:
                body.append(stmt)
            
        if self.check(TokenType.DEDENT):
            self.advance()
            
        orelse = []
        if self.check(TokenType.KEYWORD, "else"):
            self.advance()
            self.consume(TokenType.PUNCTUATION, "Expected ':'")
            self.consume(TokenType.NEWLINE, "Expected newline")
            self.consume(TokenType.INDENT, "Expected indented block")
            
            while not self.check(TokenType.DEDENT) and not self.check(TokenType.EOF):
                stmt = self.parse_statement()
                if stmt is not None:
                    orelse.append(stmt)
                
            if self.check(TokenType.DEDENT):
                self.advance()
                
        return If(test, body, orelse)
    
    def parse_while(self):
        self.consume(TokenType.KEYWORD, "Expected 'while'")
        test = self.parse_expression()
        self.consume(TokenType.PUNCTUATION, "Expected ':'")
        self.consume(TokenType.NEWLINE, "Expected newline")
        self.consume(TokenType.INDENT, "Expected indented block")
        
        body = []
        while not self.check(TokenType.DEDENT) and not self.check(TokenType.EOF):
            stmt = self.parse_statement()
            if stmt is not None:
                body.append(stmt)
            
        if self.check(TokenType.DEDENT):
            self.advance()
            
        return While(test, body)
    
    def parse_for(self):
        self.consume(TokenType.KEYWORD, "Expected 'for'")
        target = self.parse_expression()
        self.consume(TokenType.KEYWORD, "Expected 'in'")
        iterator = self.parse_expression()
        self.consume(TokenType.PUNCTUATION, "Expected ':'")
        self.consume(TokenType.NEWLINE, "Expected newline")
        self.consume(TokenType.INDENT, "Expected indented block")
        
        body = []
        while not self.check(TokenType.DEDENT) and not self.check(TokenType.EOF):
            stmt = self.parse_statement()
            if stmt is not None:
                body.append(stmt)
            
        if self.check(TokenType.DEDENT):
            self.advance()
            
        return For(target, iterator, body)
    
    def parse_expression_statement(self):
        # Handle EOF and newlines as early termination
        if self.check(TokenType.EOF) or self.check(TokenType.NEWLINE):
            if self.check(TokenType.NEWLINE):
                self.advance()  # Skip newline token
            return None
            
        # Try to parse an expression
        try:
            expr = self.parse_expression()
        except SyntaxError:
            # Error in expression, try to skip to the next newline
            while not self.check(TokenType.NEWLINE) and not self.check(TokenType.EOF):
                self.advance()
            if self.check(TokenType.NEWLINE):
                self.advance()
            return None
        
        # Handle assignments
        if self.check(TokenType.OPERATOR, "="):
            self.advance()
            try:
                value = self.parse_expression()
                # Consume newline or handle EOF
                if self.check(TokenType.NEWLINE):
                    self.advance()
                elif not self.check(TokenType.EOF):
                    self.consume(TokenType.NEWLINE, "Expected newline")
                return Assign([expr], value)
            except SyntaxError:
                # Handle error in the right side of assignment
                while not self.check(TokenType.NEWLINE) and not self.check(TokenType.EOF):
                    self.advance()
                if self.check(TokenType.NEWLINE):
                    self.advance()
                return None
                
        # Handle augmented assignments (+=, -=, etc.)
        elif self.check(TokenType.OPERATOR) and self.peek().value.endswith("=") and len(self.peek().value) > 1:
            op = self.advance().value[:-1]
            try:
                value = self.parse_expression()
                # Consume newline or handle EOF
                if self.check(TokenType.NEWLINE):
                    self.advance()
                elif not self.check(TokenType.EOF):
                    self.consume(TokenType.NEWLINE, "Expected newline")
                return AugAssign(expr, op, value)
            except SyntaxError:
                # Handle error in the right side of augmented assignment
                while not self.check(TokenType.NEWLINE) and not self.check(TokenType.EOF):
                    self.advance()
                if self.check(TokenType.NEWLINE):
                    self.advance()
                return None
        
        # For a plain expression, just consume the newline if present
        if self.check(TokenType.NEWLINE):
            self.advance()
        elif not self.check(TokenType.EOF):
            # If we're not at EOF, we expect a newline
            try:
                self.consume(TokenType.NEWLINE, "Expected newline")
            except SyntaxError:
                # If no newline, try to recover by skipping to the next statement
                while not self.check(TokenType.NEWLINE) and not self.check(TokenType.EOF):
                    self.advance()
                if self.check(TokenType.NEWLINE):
                    self.advance()
        
        return expr
    
    def parse_expression(self):
        return self.parse_comparison()
    
    def parse_comparison(self):
        expr = self.parse_term()
        
        if self.check(TokenType.OPERATOR) and self.peek().value in ["==", "!=", "<", ">", "<=", ">="]:
            ops = []
            comparators = []
            
            while self.check(TokenType.OPERATOR) and self.peek().value in ["==", "!=", "<", ">", "<=", ">="]:
                ops.append(self.advance().value)
                comparators.append(self.parse_term())
                
            return Compare(expr, ops, comparators)
            
        return expr
    
    def parse_term(self):
        expr = self.parse_factor()
        
        while self.check(TokenType.OPERATOR) and self.peek().value in ["+", "-"]:
            op = self.advance().value
            right = self.parse_factor()
            expr = BinOp(expr, op, right)
            
        return expr
    
    def parse_factor(self):
        expr = self.parse_unary()
        
        while self.check(TokenType.OPERATOR) and self.peek().value in ["*", "/", "%"]:
            op = self.advance().value
            right = self.parse_unary()
            expr = BinOp(expr, op, right)
            
        return expr
    
    def parse_unary(self):
        if self.check(TokenType.OPERATOR) and self.peek().value in ["-", "+"]:
            op = self.advance().value
            right = self.parse_unary()
            return UnaryOp(op, right)
            
        return self.parse_primary()
    
    def parse_primary(self):
        if self.check(TokenType.EOF) or self.check(TokenType.NEWLINE):
            # Create a placeholder for EOF or unexpected newline
            return Constant(None)
        
        if self.check(TokenType.INTEGER):
            value = int(self.advance().value)
            return Constant(value)
        elif self.check(TokenType.FLOAT):
            value = float(self.advance().value)
            return Constant(value)
        elif self.check(TokenType.STRING):
            value = self.advance().value
            return Constant(value[1:-1])
        elif self.check(TokenType.IDENTIFIER):
            name = self.advance().value
            
            if self.check(TokenType.PUNCTUATION, "("):
                return self.parse_call(name)
                
            return Name(name)
        elif self.check(TokenType.PUNCTUATION, "("):
            self.advance()
            expr = self.parse_expression()
            self.consume(TokenType.PUNCTUATION, "Expected ')'")
            return expr
        else:
            token = self.peek()
            # More informative error message
            raise SyntaxError(f"Unexpected token: {token.type} '{token.value}' at line {token.line}, column {token.column}")
    
    def parse_call(self, name):
        self.consume(TokenType.PUNCTUATION, "Expected '('")
        args = []
        
        if not self.check(TokenType.PUNCTUATION, ")"):
            args.append(self.parse_expression())
            
            while self.match(TokenType.PUNCTUATION, ","):
                args.append(self.parse_expression())
                
        self.consume(TokenType.PUNCTUATION, "Expected ')'")
        return Call(Name(name), args)
    
    def consume(self, type, message):
        if self.check(type):
            return self.advance()
        
        token = self.peek()
        raise SyntaxError(f"{message} at line {token.line}, column {token.column}, got {token.type} '{token.value}'")
    
    def match(self, type, value=None):
        if self.check(type, value):
            self.advance()
            return True
        return False
    
    def check(self, type, value=None):
        if self.is_at_end():
            return False
        
        if self.peek().type != type:
            return False
            
        if value is not None and self.peek().value != value:
            return False
            
        return True
    
    def advance(self):
        if not self.is_at_end():
            self.current += 1
        return self.previous()
    
    def is_at_end(self):
        return self.peek().type == TokenType.EOF
    
    def peek(self):
        return self.tokens[self.current]
    
    def previous(self):
        return self.tokens[self.current - 1]