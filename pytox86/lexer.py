import re
from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    IDENTIFIER = auto()
    KEYWORD = auto()
    OPERATOR = auto()
    PUNCTUATION = auto()
    INDENT = auto()
    DEDENT = auto()
    NEWLINE = auto()
    EOF = auto()

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

class Lexer:
    def __init__(self):
        self.keywords = {
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
            'elif', 'else', 'except', 'False', 'finally', 'for', 'from', 'global',
            'if', 'import', 'in', 'is', 'lambda', 'None', 'nonlocal', 'not', 'or',
            'pass', 'raise', 'return', 'True', 'try', 'while', 'with', 'yield'
        }
        
        self.operators = {
            '+', '-', '*', '/', '%', '**', '//', '==', '!=', '<', '>', '<=', '>=',
            '=', '+=', '-=', '*=', '/=', '%=', '**=', '//=', '&=', '|=', '^=',
            '>>=', '<<=', '&', '|', '^', '~', '<<', '>>'
        }
        
        self.punctuation = {
            '(', ')', '[', ']', '{', '}', ',', ':', '.', ';', '@', '='
        }
        
        self.token_patterns = [
            (r'[ \t]+', None),
            (r'#.*', None),
            (r'\n+', TokenType.NEWLINE),
            (r'[0-9]+\.[0-9]*', TokenType.FLOAT),
            (r'[0-9]+', TokenType.INTEGER),
            (r'"([^"\\]|\\.)*"', TokenType.STRING),
            (r"'([^'\\]|\\.)*'", TokenType.STRING),
            (r'[a-zA-Z_][a-zA-Z0-9_]*', self._identify_name),
            (r'[+\-*/%=<>!&|^~]+', self._identify_operator),
            (r'[(){}\[\],.;:@]', self._identify_punctuation),
        ]
        
        self.patterns = [(re.compile(pattern), handler) for pattern, handler in self.token_patterns]
        
    def _identify_name(self, value, line, column):
        if value in self.keywords:
            return Token(TokenType.KEYWORD, value, line, column)
        return Token(TokenType.IDENTIFIER, value, line, column)
    
    def _identify_operator(self, value, line, column):
        if value in self.operators:
            return Token(TokenType.OPERATOR, value, line, column)
        return None
    
    def _identify_punctuation(self, value, line, column):
        if value in self.punctuation:
            return Token(TokenType.PUNCTUATION, value, line, column)
        return None
    
    def tokenize(self, source_code):
        tokens = []
        
        # Handle empty file case
        if not source_code.strip():
            tokens.append(Token(TokenType.EOF, '', 1, 0))
            return tokens
            
        # Normalize line endings
        source_code = source_code.replace('\r\n', '\n')
        
        # Process the code line by line
        lines = source_code.split('\n')
        indent_stack = [0]
        line_num = 0
        
        for line_num, line in enumerate(lines, 1):
            # Skip empty or comment-only lines
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            line_stripped = line.rstrip()
            indent = len(line_stripped) - len(line_stripped.lstrip())
            
            # Process indentation
            if indent > indent_stack[-1]:
                tokens.append(Token(TokenType.INDENT, '', line_num, 0))
                indent_stack.append(indent)
            else:
                while indent < indent_stack[-1]:
                    indent_stack.pop()
                    tokens.append(Token(TokenType.DEDENT, '', line_num, 0))
                    
                if indent != indent_stack[-1]:
                    raise SyntaxError(f"Inconsistent indentation at line {line_num}")
            
            # Process tokens in the line
            col = indent
            remaining = line_stripped.lstrip()
            
            while remaining:
                match = None
                for pattern, handler in self.patterns:
                    match = pattern.match(remaining)
                    if match:
                        value = match.group(0)
                        if handler:
                            if callable(handler):
                                token = handler(value, line_num, col)
                            else:
                                token = Token(handler, value, line_num, col)
                                
                            if token:
                                tokens.append(token)
                        
                        col += len(value)
                        remaining = remaining[len(value):]
                        break
                
                if not match:
                    raise SyntaxError(f"Invalid syntax at line {line_num}, column {col}: {remaining[0]}")
            
            # Add newline token at the end of each line with content
            tokens.append(Token(TokenType.NEWLINE, '\n', line_num, col))
        
        # Add dedents at the end of the file
        while len(indent_stack) > 1:
            indent_stack.pop()
            tokens.append(Token(TokenType.DEDENT, '', line_num, 0))
        
        # Add EOF token
        tokens.append(Token(TokenType.EOF, '', line_num, 0))
        
        return tokens
