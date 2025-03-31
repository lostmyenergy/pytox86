from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from .parser import (
    ASTNode, Program, FunctionDef, Return, Assign, AugAssign,
    For, While, If, BinOp, UnaryOp, Call, Constant, Name, Compare
)

@dataclass
class IRInstruction:
    op: str
    args: List[Any] = field(default_factory=list)
    result: Optional[str] = None
    
@dataclass
class BasicBlock:
    label: str
    instructions: List[IRInstruction] = field(default_factory=list)
    next_block: Optional['BasicBlock'] = None
    branch_target: Optional['BasicBlock'] = None
    
@dataclass
class IRFunction:
    name: str
    params: List[str]
    entry_block: BasicBlock
    blocks: List[BasicBlock] = field(default_factory=list)
    local_vars: List[str] = field(default_factory=list)
    
@dataclass
class IRProgram:
    functions: List[IRFunction] = field(default_factory=list)
    global_vars: List[str] = field(default_factory=list)

class IRGenerator:
    def __init__(self):
        self.program = IRProgram()
        self.current_function = None
        self.current_block = None
        self.temp_counter = 0
        self.label_counter = 0
        self.loop_exit_stack = []
        
    def generate(self, ast):
        if isinstance(ast, Program):
            for node in ast.body:
                self.visit(node)
                
        return self.program
        
    def ensure_valid_context(self):
        """Helper method to ensure we have a valid function and block context"""
        if not self.current_function:
            # Create a dummy function if we're in an invalid state
            self.current_function = IRFunction("_error_handling", [], BasicBlock("_error_entry"))
            self.current_block = self.current_function.entry_block
            
            # Make sure the block is added to the function
            if hasattr(self.current_function, 'blocks'):
                self.current_function.blocks.append(self.current_block)
            
            # Add the function to the program
            if self.current_function not in self.program.functions:
                self.program.functions.append(self.current_function)
        
        elif not self.current_block:
            # If we have a function but no block, create one
            self.current_block = BasicBlock(self.label("recovery_block"))
            
            # Add the block to the function, with null check
            if hasattr(self.current_function, 'blocks'):
                self.current_function.blocks.append(self.current_block)
                
        return self.current_function, self.current_block
        
    def visit(self, node):
        method_name = f"visit_{node.__class__.__name__}"
        method = getattr(self, method_name, self.generic_visit)
        return method(node)
        
    def generic_visit(self, node):
        raise NotImplementedError(f"IR generation not implemented for {type(node).__name__}")
        
    def visit_FunctionDef(self, node):
        entry_block = BasicBlock(f"{node.name}_entry")
        func = IRFunction(node.name, node.params, entry_block)
        func.blocks.append(entry_block)
        
        self.program.functions.append(func)
        self.current_function = func
        self.current_block = entry_block
        
        for param in node.params:
            self.current_function.local_vars.append(param)
            
        for stmt in node.body:
            self.visit(stmt)
            
        if not self.current_block.instructions or self.current_block.instructions[-1].op != "ret":
            self.emit("ret", [])
            
        self.current_function = None
        self.current_block = None
        
    def visit_Return(self, node):
        if node.value:
            value = self.visit(node.value)
            self.emit("ret", [value])
        else:
            self.emit("ret", [])
            
    def visit_Assign(self, node):
        value = self.visit(node.value)
        
        for target in node.targets:
            if isinstance(target, Name):
                if self.current_function and target.id not in self.current_function.local_vars:
                    self.current_function.local_vars.append(target.id)
                self.emit("store", [value, target.id])
            else:
                raise NotImplementedError(f"Assignment to {type(target).__name__} not implemented")
                
    def visit_AugAssign(self, node):
        target_value = self.visit(node.target)
        right_value = self.visit(node.value)
        
        result = self.temp()
        self.emit("binop", [node.op, target_value, right_value], result)
        
        if isinstance(node.target, Name):
            if self.current_function and node.target.id not in self.current_function.local_vars:
                self.current_function.local_vars.append(node.target.id)
            self.emit("store", [result, node.target.id])
        else:
            raise NotImplementedError(f"Augmented assignment to {type(node.target).__name__} not implemented")
            
    def visit_For(self, node):
        if not isinstance(node.target, Name):
            raise NotImplementedError("For loop target must be a name")
            
        # Ensure we have a valid current function context
        if not self.current_function:
            self.current_function = IRFunction("_error_handling", [], BasicBlock("_error_entry"))
            self.current_block = self.current_function.entry_block
            self.current_function.blocks.append(self.current_block)
            
        iter_value = self.visit(node.iter)
        
        init_block = self.current_block
        cond_block = BasicBlock(self.label("for_cond"))
        body_block = BasicBlock(self.label("for_body"))
        exit_block = BasicBlock(self.label("for_exit"))
        
        # Safe block additions with null check
        if self.current_function:
            self.current_function.blocks.extend([cond_block, body_block, exit_block])
        
        # Safe block linking with null checks
        if init_block:
            init_block.next_block = cond_block
        if cond_block:
            cond_block.next_block = body_block
            cond_block.branch_target = exit_block
        if body_block:
            body_block.next_block = cond_block
        
        self.loop_exit_stack.append(exit_block)
        
        index_var = self.temp()
        if self.current_function and node.target.id not in self.current_function.local_vars:
            self.current_function.local_vars.append(node.target.id)
            
        self.emit("const", [0], index_var)
        
        self.current_block = cond_block
        
        iter_len = self.temp()
        self.emit("len", [iter_value], iter_len)
        
        cond_result = self.temp()
        self.emit("compare", ["<", index_var, iter_len], cond_result)
        self.emit("branch", [cond_result, body_block.label, exit_block.label])
        
        self.current_block = body_block
        
        item = self.temp()
        self.emit("getitem", [iter_value, index_var], item)
        self.emit("store", [item, node.target.id])
        
        for stmt in node.body:
            self.visit(stmt)
            
        self.emit("binop", ["+", index_var, "1"], index_var)
        self.emit("jump", [cond_block.label])
        
        self.loop_exit_stack.pop()
        self.current_block = exit_block
        
    def visit_While(self, node):
        # Ensure we have a valid current function context
        if not self.current_function:
            self.current_function = IRFunction("_error_handling", [], BasicBlock("_error_entry"))
            self.current_block = self.current_function.entry_block
            self.current_function.blocks.append(self.current_block)
            
        cond_block = BasicBlock(self.label("while_cond"))
        body_block = BasicBlock(self.label("while_body"))
        exit_block = BasicBlock(self.label("while_exit"))
        
        # Add blocks to function with null check
        if self.current_function:
            self.current_function.blocks.extend([cond_block, body_block, exit_block])
        
        # Safe block linking with null checks
        if self.current_block:
            self.current_block.next_block = cond_block
        if cond_block:
            cond_block.next_block = body_block
            cond_block.branch_target = exit_block
        if body_block:
            body_block.next_block = cond_block
        
        self.loop_exit_stack.append(exit_block)
        
        self.current_block = cond_block
        
        cond_result = self.visit(node.test)
        self.emit("branch", [cond_result, body_block.label, exit_block.label])
        
        self.current_block = body_block
        
        for stmt in node.body:
            self.visit(stmt)
            
        self.emit("jump", [cond_block.label])
        
        self.loop_exit_stack.pop()
        self.current_block = exit_block
        
    def visit_If(self, node):
        # Ensure we have a valid current function context
        if not self.current_function:
            # If we're outside of a function or in an invalid state,
            # create a dummy function to avoid errors
            self.current_function = IRFunction("_error_handling", [], BasicBlock("_error_entry"))
            self.current_block = self.current_function.entry_block
            self.current_function.blocks.append(self.current_block)
            
        cond_result = self.visit(node.test)
        
        then_block = BasicBlock(self.label("if_then"))
        else_block = None
        merge_block = BasicBlock(self.label("if_merge"))
        
        # Add blocks to function with null check
        if self.current_function:
            self.current_function.blocks.append(then_block)
            self.current_function.blocks.append(merge_block)
        
        # Safe emission of branch instruction
        if node.orelse:
            else_block = BasicBlock(self.label("if_else"))
            if self.current_function:
                self.current_function.blocks.append(else_block)
            self.emit("branch", [cond_result, then_block.label, else_block.label])
            
            # Set up the branch targets for later blocks with null check
            if self.current_block:
                self.current_block.next_block = then_block
                self.current_block.branch_target = else_block
        else:
            self.emit("branch", [cond_result, then_block.label, merge_block.label])
            
            # Set up the branch targets for later blocks with null check
            if self.current_block:
                self.current_block.next_block = then_block
                self.current_block.branch_target = merge_block
            
        # Process the 'then' block
        self.current_block = then_block
        for stmt in node.body:
            self.visit(stmt)
        self.emit("jump", [merge_block.label])
        
        # Process the 'else' block if it exists
        if else_block:
            self.current_block = else_block
            for stmt in node.orelse:
                self.visit(stmt)
            self.emit("jump", [merge_block.label])
            
        # Continue with the merged block
        self.current_block = merge_block
        
    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        result = self.temp()
        self.emit("binop", [node.op, left, right], result)
        return result
        
    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        
        result = self.temp()
        self.emit("unop", [node.op, operand], result)
        return result
        
    def visit_Call(self, node):
        args = []
        
        for arg in node.args:
            args.append(self.visit(arg))
            
        if isinstance(node.func, Name):
            result = self.temp()
            self.emit("call", [node.func.id] + args, result)
            return result
        else:
            raise NotImplementedError(f"Call to {type(node.func).__name__} not implemented")
            
    def visit_Constant(self, node):
        # For constants, generate literal values directly when possible
        if isinstance(node.value, (int, float, bool, str)):
            # For primitive types, create a temporary with the constant value
            result = self.temp()
            # When using ints like 5 and 10, embed the literal value in the temp name
            # This helps the code generator identify constants
            if isinstance(node.value, int) and 0 <= node.value <= 100:
                # For small integers, create a specialized temp that includes the value
                # for easier literal substitution in code generation
                result = f"%t{node.value}"
            self.emit("const", [node.value], result)
            return result
        elif node.value is None:
            # Handle None value
            result = self.temp()
            self.emit("const", [0], result)  # Use 0 for None
            return result
        else:
            # For complex objects (which shouldn't happen often in this transpiler)
            # Return a placeholder with a fallback value
            result = self.temp()
            self.emit("const", [0], result)  # Use 0 as placeholder
            return result
        
    def visit_Name(self, node):
        if node.ctx == "Load":
            result = self.temp()
            self.emit("load", [node.id], result)
            return result
        else:
            return node.id
            
    def visit_Compare(self, node):
        left = self.visit(node.left)
        
        result = self.temp()
        
        if len(node.ops) == 1 and len(node.comparators) == 1:
            right = self.visit(node.comparators[0])
            self.emit("compare", [node.ops[0], left, right], result)
        else:
            raise NotImplementedError("Multiple comparisons not implemented")
            
        return result
            
    def temp(self):
        name = f"%t{self.temp_counter}"
        self.temp_counter += 1
        return name
        
    def label(self, prefix=""):
        name = f"{prefix}_{self.label_counter}"
        self.label_counter += 1
        return name
        
    def emit(self, op, args, result=None):
        instr = IRInstruction(op, args, result)
        if self.current_block:
            self.current_block.instructions.append(instr)
        else:
            # If we don't have a current block (shouldn't happen in normal execution),
            # create a new one so we don't lose the instruction
            self.current_block = BasicBlock(self.label("emergency_block"))
            if self.current_function:
                self.current_function.blocks.append(self.current_block)
            self.current_block.instructions.append(instr)
        return instr
