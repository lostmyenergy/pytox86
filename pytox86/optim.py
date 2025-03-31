from .irgen import IRProgram, IRFunction, BasicBlock, IRInstruction

class Optimizer:
    def __init__(self, optimization_level=1):
        self.optimization_level = optimization_level
        self.optimizations = [
            self.eliminate_dead_code,
            self.constant_folding,
            self.constant_propagation,
            self.eliminate_unreachable_code,
            self.merge_blocks,
        ]
        
    def optimize(self, program):
        if self.optimization_level <= 0:
            return program
            
        changed = True
        
        while changed:
            changed = False
            
            for optimization in self.optimizations[:self.optimization_level]:
                if optimization(program):
                    changed = True
                    
        return program
        
    def eliminate_dead_code(self, program):
        changed = False
        
        for function in program.functions:
            used_vars = set()
            
            for block in function.blocks:
                for instr in block.instructions:
                    if instr.op in ["load", "binop", "unop", "compare", "call", "getitem"]:
                        for arg in instr.args:
                            if isinstance(arg, str) and arg.startswith("%"):
                                used_vars.add(arg)
                    elif instr.op == "ret" and instr.args:
                        for arg in instr.args:
                            if isinstance(arg, str) and arg.startswith("%"):
                                used_vars.add(arg)
                    elif instr.op == "branch" and len(instr.args) > 0:
                        arg = instr.args[0]
                        if isinstance(arg, str) and arg.startswith("%"):
                            used_vars.add(arg)
                            
            for block in function.blocks:
                new_instructions = []
                
                for instr in block.instructions:
                    if instr.result and instr.result.startswith("%") and instr.result not in used_vars:
                        if instr.op not in ["store", "jump", "branch", "ret"]:
                            changed = True
                            continue
                            
                    new_instructions.append(instr)
                    
                if len(new_instructions) != len(block.instructions):
                    changed = True
                    block.instructions = new_instructions
                    
        return changed
        
    def constant_folding(self, program):
        changed = False
        
        for function in program.functions:
            for block in function.blocks:
                for i, instr in enumerate(block.instructions):
                    if instr.op == "binop" and len(instr.args) == 3:
                        op, left, right = instr.args
                        
                        left_const = self.is_constant_value(left)
                        right_const = self.is_constant_value(right)
                        
                        if left_const is not None and right_const is not None:
                            result = None
                            
                            if op == "+":
                                result = left_const + right_const
                            elif op == "-":
                                result = left_const - right_const
                            elif op == "*":
                                result = left_const * right_const
                            elif op == "/" and right_const != 0:
                                result = left_const / right_const
                            elif op == "//" and right_const != 0:
                                result = left_const // right_const
                            elif op == "%":
                                result = left_const % right_const
                                
                            if result is not None:
                                block.instructions[i] = IRInstruction("const", [result], instr.result)
                                changed = True
                                
                    elif instr.op == "unop" and len(instr.args) == 2:
                        op, operand = instr.args
                        
                        operand_const = self.is_constant_value(operand)
                        
                        if operand_const is not None:
                            result = None
                            
                            if op == "-":
                                result = -operand_const
                            elif op == "+":
                                result = +operand_const
                                
                            if result is not None:
                                block.instructions[i] = IRInstruction("const", [result], instr.result)
                                changed = True
                                
                    elif instr.op == "compare" and len(instr.args) == 3:
                        op, left, right = instr.args
                        
                        left_const = self.is_constant_value(left)
                        right_const = self.is_constant_value(right)
                        
                        if left_const is not None and right_const is not None:
                            result = None
                            
                            if op == "==":
                                result = left_const == right_const
                            elif op == "!=":
                                result = left_const != right_const
                            elif op == "<":
                                result = left_const < right_const
                            elif op == ">":
                                result = left_const > right_const
                            elif op == "<=":
                                result = left_const <= right_const
                            elif op == ">=":
                                result = left_const >= right_const
                                
                            if result is not None:
                                block.instructions[i] = IRInstruction("const", [result], instr.result)
                                changed = True
                        
        return changed
        
    def constant_propagation(self, program):
        changed = False
        
        for function in program.functions:
            for block in function.blocks:
                constants = {}
                
                for i, instr in enumerate(block.instructions):
                    if instr.op == "const" and instr.result:
                        constants[instr.result] = instr.args[0]
                        
                    if instr.op in ["binop", "unop", "compare", "load", "getitem"]:
                        new_args = []
                        arg_changed = False
                        
                        for arg in instr.args:
                            if isinstance(arg, str) and arg in constants:
                                new_args.append(constants[arg])
                                arg_changed = True
                            else:
                                new_args.append(arg)
                                
                        if arg_changed:
                            block.instructions[i] = IRInstruction(instr.op, new_args, instr.result)
                            changed = True
                            
                    elif instr.op in ["store", "branch", "ret"]:
                        new_args = []
                        arg_changed = False
                        
                        for arg in instr.args:
                            if isinstance(arg, str) and arg in constants:
                                new_args.append(constants[arg])
                                arg_changed = True
                            else:
                                new_args.append(arg)
                                
                        if arg_changed:
                            block.instructions[i] = IRInstruction(instr.op, new_args, instr.result)
                            changed = True
                        
        return changed
        
    def eliminate_unreachable_code(self, program):
        changed = False
        
        for function in program.functions:
            reachable_blocks = set()
            worklist = [function.entry_block]
            
            while worklist:
                block = worklist.pop()
                
                if block.label in reachable_blocks:
                    continue
                    
                reachable_blocks.add(block.label)
                
                for instr in block.instructions:
                    if instr.op == "jump" and instr.args:
                        target_label = instr.args[0]
                        target_block = next((b for b in function.blocks if b.label == target_label), None)
                        
                        if target_block and target_block.label not in reachable_blocks:
                            worklist.append(target_block)
                            
                    elif instr.op == "branch" and len(instr.args) > 2:
                        true_label = instr.args[1]
                        false_label = instr.args[2]
                        
                        true_block = next((b for b in function.blocks if b.label == true_label), None)
                        false_block = next((b for b in function.blocks if b.label == false_label), None)
                        
                        if true_block and true_block.label not in reachable_blocks:
                            worklist.append(true_block)
                            
                        if false_block and false_block.label not in reachable_blocks:
                            worklist.append(false_block)
                            
                if block.next_block and block.next_block.label not in reachable_blocks:
                    worklist.append(block.next_block)
                    
                if block.branch_target and block.branch_target.label not in reachable_blocks:
                    worklist.append(block.branch_target)
                    
            unreachable_blocks = [b for b in function.blocks if b.label not in reachable_blocks]
            
            if unreachable_blocks:
                changed = True
                function.blocks = [b for b in function.blocks if b.label in reachable_blocks]
                
        return changed
        
    def merge_blocks(self, program):
        changed = False
        
        for function in program.functions:
            i = 0
            
            while i < len(function.blocks):
                block = function.blocks[i]
                
                if not block.instructions:
                    i += 1
                    continue
                    
                last_instr = block.instructions[-1]
                
                if last_instr.op == "jump" and len(last_instr.args) == 1:
                    target_label = last_instr.args[0]
                    target_block = next((b for b in function.blocks if b.label == target_label), None)
                    
                    if target_block and len([b for b in function.blocks if b.next_block == target_block or b.branch_target == target_block]) == 1:
                        block.instructions.pop()
                        block.instructions.extend(target_block.instructions)
                        
                        for other_block in function.blocks:
                            if other_block.next_block == target_block:
                                other_block.next_block = block
                                
                            if other_block.branch_target == target_block:
                                other_block.branch_target = block
                                
                        function.blocks.remove(target_block)
                        changed = True
                        continue
                        
                i += 1
                
        return changed
        
    def is_constant_value(self, value):
        if isinstance(value, (int, float, bool)):
            return value
            
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    if value == "True":
                        return True
                    elif value == "False":
                        return False
                        
        return None
