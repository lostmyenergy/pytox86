from .irgen import IRProgram, IRFunction, BasicBlock, IRInstruction

class X86Generator:
    def __init__(self):
        self.output = []
        self.indentation = 0
        self.label_counter = 0
        self.str_literals = {}
        self.str_counter = 0
        self.current_function = None
        self.stack_vars = {}
        self.stack_size = 0
        
    def generate(self, ir_program):
        self.output = []
        self.indentation = 0
        self.label_counter = 0
        self.str_literals = {}
        self.str_counter = 0
        
        self.emit_header()
        
        for func in ir_program.functions:
            self.generate_function(func)
            
        self.emit_footer()
        
        return "\n".join(self.output)
        
    def emit_header(self):
        self.emit_line(".intel_syntax noprefix")
        self.emit_line(".global main")
        self.emit_line(".text")
        
    def emit_footer(self):
        if self.str_literals:
            self.emit_line(".section .rodata")
            
            for label, value in self.str_literals.items():
                escaped_value = ""
                
                for c in value:
                    if c == '"':
                        escaped_value += '\\"'
                    elif c == '\\':
                        escaped_value += '\\\\'
                    elif c == '\n':
                        escaped_value += '\\n'
                    elif c == '\t':
                        escaped_value += '\\t'
                    elif c == '\r':
                        escaped_value += '\\r'
                    else:
                        escaped_value += c
                        
                self.emit_line(f"{label}:")
                self.emit_line(f'    .string "{escaped_value}"')
                
    def generate_function(self, func):
        self.current_function = func
        self.stack_vars = {}
        self.stack_size = 0
        
        local_vars = set(func.local_vars)
        
        temp_vars = set()
        for block in func.blocks:
            for instr in block.instructions:
                if instr.result and instr.result.startswith("%"):
                    temp_vars.add(instr.result)
                    
        all_vars = list(local_vars) + list(temp_vars)
        self.stack_size = len(all_vars) * 8
        
        if self.stack_size % 16 != 0:
            self.stack_size += 8
            
        for i, var in enumerate(all_vars):
            self.stack_vars[var] = i * 8
            
        self.emit_line("")
        self.emit_line(f"{func.name}:")
        self.indentation += 1
        
        self.emit_line("push rbp")
        self.emit_line("mov rbp, rsp")
        
        if self.stack_size > 0:
            self.emit_line(f"sub rsp, {self.stack_size}")
            
        for i, param in enumerate(func.params):
            if i < 6:
                reg = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"][i]
                self.emit_line(f"mov QWORD PTR [rbp-{self.stack_vars[param]+8}], {reg}")
            else:
                self.emit_line(f"mov rax, QWORD PTR [rbp+{(i-6+2)*8}]")
                self.emit_line(f"mov QWORD PTR [rbp-{self.stack_vars[param]+8}], rax")
                
        for block in func.blocks:
            self.emit_line("")
            self.emit_line(f"{block.label}:")
            
            for instr in block.instructions:
                self.generate_instruction(instr)
                
        self.indentation -= 1
        
    def generate_instruction(self, instr):
        if not self.current_function:
            # Critical error - we need a function context to generate instructions
            return
            
        if instr.op == "const":
            value = instr.args[0]
            
            if isinstance(value, bool):
                value = 1 if value else 0
                
            if isinstance(value, str):
                label = self.add_string_literal(value)
                self.emit_line(f"lea rax, [{label}]")
            else:
                # Use immediate value directly
                self.emit_line(f"mov rax, {value}")
                
            if instr.result:
                self.store_var(instr.result, "rax")
                
        elif instr.op == "load":
            var_name = instr.args[0]
            self.load_var(var_name, "rax")
            
            if instr.result:
                self.store_var(instr.result, "rax")
                
        elif instr.op == "store":
            source = instr.args[0]
            dest = instr.args[1]
            
            self.load_value(source, "rax")
            self.store_var(dest, "rax")
            
        elif instr.op == "binop":
            op, left, right = instr.args
            
            # Load operands
            self.load_value(left, "rax")
            self.load_value(right, "rcx")
            
            # Perform operation
            if op == "+":
                self.emit_line("add rax, rcx")
            elif op == "-":
                self.emit_line("sub rax, rcx")
            elif op == "*":
                self.emit_line("imul rax, rcx")
            elif op == "/":
                # Division requires special handling
                self.emit_line("cqo")  # Sign-extend RAX into RDX:RAX
                self.emit_line("idiv rcx")  # RDX:RAX / RCX, result in RAX
            elif op == "%":
                # Modulo
                self.emit_line("cqo")
                self.emit_line("idiv rcx")  # Remainder goes to RDX
                self.emit_line("mov rax, rdx")
            elif op == "<<":
                self.emit_line("mov rdx, rcx")  # Save rcx
                self.emit_line("shl rax, cl")  # Shift uses CL register (low 8 bits of RCX)
            elif op == ">>":
                self.emit_line("mov rdx, rcx")
                self.emit_line("shr rax, cl")
            elif op == "&":
                self.emit_line("and rax, rcx")
            elif op == "|":
                self.emit_line("or rax, rcx")
            elif op == "^":
                self.emit_line("xor rax, rcx")
                
            # Store result
            if instr.result:
                self.store_var(instr.result, "rax")
                
        elif instr.op == "unop":
            op, operand = instr.args
            
            self.load_value(operand, "rax")
            
            if op == "-":
                self.emit_line("neg rax")
            elif op == "~":
                self.emit_line("not rax")
                
            if instr.result:
                self.store_var(instr.result, "rax")
                
        elif instr.op == "compare":
            op, left, right = instr.args
            
            # Load operands
            self.load_value(left, "rax")
            self.load_value(right, "rcx")
            
            # Compare
            self.emit_line("cmp rax, rcx")
            
            # Set result based on comparison type
            if op == "==":
                self.emit_line("sete al")
            elif op == "!=":
                self.emit_line("setne al")
            elif op == "<":
                self.emit_line("setl al")
            elif op == ">":
                self.emit_line("setg al")
            elif op == "<=":
                self.emit_line("setle al")
            elif op == ">=":
                self.emit_line("setge al")
                
            # Zero-extend AL to RAX
            self.emit_line("movzx rax, al")
            
            if instr.result:
                self.store_var(instr.result, "rax")
                
        elif instr.op == "branch":
            cond, true_label, false_label = instr.args
            
            # Load condition
            self.load_value(cond, "rax")
            
            # Compare with zero
            self.emit_line("cmp rax, 0")
            
            # Conditional jump
            self.emit_line(f"je {false_label}")
            self.emit_line(f"jmp {true_label}")
            
        elif instr.op == "jump":
            label = instr.args[0]
            self.emit_line(f"jmp {label}")
            
        elif instr.op == "call":
            func_name = instr.args[0]
            args = instr.args[1:]
            
            # Prepare function arguments according to x86-64 calling convention
            # First 6 args go in registers, rest on stack
            for i, arg in enumerate(args):
                if i < 6:
                    reg = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"][i]
                    self.load_value(arg, reg)
                else:
                    # Put remaining args on stack
                    self.load_value(arg, "rax")
                    self.emit_line("push rax")
            
            # Ensure 16-byte stack alignment before call
            # If odd number of arguments on stack, add padding
            if len(args) % 2 == 1:
                self.emit_line("sub rsp, 8")
                
            # Call the function
            self.emit_line(f"call {func_name}")
            
            # Clean up the stack if necessary
            if len(args) > 6:
                stack_cleanup = (len(args) - 6) * 8
                if len(args) % 2 == 1:
                    stack_cleanup += 8
                self.emit_line(f"add rsp, {stack_cleanup}")
                
            # Store return value if needed
            if instr.result:
                self.store_var(instr.result, "rax")
                
        elif instr.op == "len":
            value = instr.args[0]
            
            self.load_value(value, "rdi")
            self.emit_line("call _py_len")
            
            if instr.result:
                self.store_var(instr.result, "rax")
                
        elif instr.op == "getitem":
            value, index = instr.args
            
            self.load_value(value, "rdi")
            self.load_value(index, "rsi")
            self.emit_line("call _py_getitem")
            
            if instr.result:
                self.store_var(instr.result, "rax")
                
        elif instr.op == "ret":
            # Function return
            if instr.args:
                # Return with value
                self.load_value(instr.args[0], "rax")
            else:
                # Return void (0)
                self.emit_line("xor rax, rax")
                
            # Epilogue
            self.emit_line("leave")
            self.emit_line("ret")
            
    def load_var(self, var_name, dest_reg):
        if var_name in self.stack_vars:
            self.emit_line(f"mov {dest_reg}, QWORD PTR [rbp-{self.stack_vars[var_name]+8}]")
        else:
            self.emit_line(f"mov {dest_reg}, QWORD PTR [{var_name}]")
            
    def store_var(self, var_name, src_reg):
        if var_name in self.stack_vars:
            self.emit_line(f"mov QWORD PTR [rbp-{self.stack_vars[var_name]+8}], {src_reg}")
        else:
            self.emit_line(f"mov QWORD PTR [{var_name}], {src_reg}")
            
    def load_value(self, value, dest_reg):
        if isinstance(value, (int, float, bool)):
            # Handle primitive literals directly
            if isinstance(value, bool):
                value = 1 if value else 0
            self.emit_line(f"mov {dest_reg}, {value}")
        elif isinstance(value, str):
            # Special case for temps with embedded literals (e.g., %t5 representing the number 5)
            if value.startswith("%t") and value[2:].isdigit() and value not in self.stack_vars:
                # Extract the number directly from the temp name
                # These are created in visit_Constant for small integers
                num_value = int(value[2:])  # Skip '%t' prefix
                self.emit_line(f"mov {dest_reg}, {num_value}")
                return
                
            # Case 1: Variable references (local vars, params, regular temp vars)
            if value.startswith("%") or (self.current_function and 
                  (value in self.current_function.local_vars or value in self.current_function.params)):
                if value.startswith("%") and value not in self.stack_vars:
                    # This is a compiler-generated temporary variable reference
                    # If not in stack_vars, try the embedded literal pattern again
                    var_name = value[2:] if value.startswith("%t") else ""
                    try:
                        # Try to convert to a number (should rarely happen since we check above)
                        immediate_value = int(var_name)
                        self.emit_line(f"mov {dest_reg}, {immediate_value}")
                    except ValueError:
                        # If conversion fails, emit a warning and use 0
                        self.emit_line(f"mov {dest_reg}, 0")
                        self.emit_line(f"# Warning: Unresolved temp variable {value}")
                else:
                    # Normal variable load
                    self.load_var(value, dest_reg)
            # Case 2: Numeric literals (numbers as strings)
            else:
                try:
                    num_value = int(value)
                    self.emit_line(f"mov {dest_reg}, {num_value}")
                except ValueError:
                    try:
                        num_value = float(value)
                        label = self.add_float_literal(num_value)
                        self.emit_line(f"movsd {dest_reg}, [{label}]")
                    except ValueError:
                        # Case 3: Boolean literals
                        if value == "True":
                            self.emit_line(f"mov {dest_reg}, 1")
                        elif value == "False":
                            self.emit_line(f"mov {dest_reg}, 0")
                        # Case 4: String literals (anything else)
                        else:
                            label = self.add_string_literal(value)
                            self.emit_line(f"lea {dest_reg}, [{label}]")
                            
    def add_string_literal(self, value):
        for label, existing_value in self.str_literals.items():
            if existing_value == value:
                return label
                
        label = f".LC{self.str_counter}"
        self.str_counter += 1
        self.str_literals[label] = value
        return label
        
    def add_float_literal(self, value):
        str_value = str(value)
        
        for label, existing_value in self.str_literals.items():
            if existing_value == str_value:
                return label
                
        label = f".LC{self.str_counter}"
        self.str_counter += 1
        self.str_literals[label] = str_value
        return label
        
    def emit_line(self, line):
        indent = "    " * self.indentation
        self.output.append(f"{indent}{line}")
