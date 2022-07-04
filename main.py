import sys, os

import llvmlite.ir as ir
import llvmlite.binding as binding

from ctypes import *

import __main__

def lexer(data):
    pos = 0
    char = data[pos]
    tokens = []

    keywords = [
        "int", "void",
        "return"
    ]

    preproccessors = [
        "include"
    ]

    while pos < len(data):
        while char in ["\t", "\n", " "]:
            pos += 1
            try: char = data[pos]
            except: char = ""
            
        if char.isalpha() or char == "#":
            preproccessor = True if char == "#" else False
            id_str = ""

            if preproccessor:
                pos += 1
                try: char = data[pos]
                except: char = ""

            while char.isalnum():
                id_str += char
                pos += 1
                try: char = data[pos]
                except: char = ""

            if preproccessor:
                if id_str in preproccessors:
                    tokens.append({"type": "PREPROCCESSOR", "value": id_str})

                else:
                    print(f"lexer: error: preproccessor '{id_str}' not defined")
                    sys.exit(-1)

            elif id_str in keywords:
                tokens.append({"type": "KEYWORD", "value": id_str})

            else:
                tokens.append({"type": "IDENTIFIER", "value": id_str})

        elif char.isdigit() or char == ".":
            num_str = ""
            dot_count = 0

            if tokens[len(tokens) - 1] == {"type": "OPERATOR", "value": "-"}:
                if data[pos - 1] == "-":
                    num_str = "-" + num_str
                    del tokens[len(tokens) - 1]

            while char.isdigit() or char == ".":
                if char == ".": dot_count += 1
                num_str += char
                pos += 1
                try: char = data[pos]
                except: char = ""

            if dot_count > 1:
                print(f"lexer: error: unexpected character: '.'")
                sys.exit(-1)

            elif dot_count == 1:
                tokens.append({"type": "FLOAT", "value": num_str})

            else:
                tokens.append({"type": "INT", "value": num_str})

        elif char in ["\"", "'", "<"]:
            if char == "<":
                op = ">"

            else:
                op = char

            value_str = ""
            pos += 1
            try: char = data[pos]
            except: char = ""

            while char != op:
                pos += 1
                value_str += char
                try: char = data[pos]
                except: char = ""

            pos += 1
            try: char = data[pos]
            except: char = ""

            if op == ">":
                tokens.append({"type": "LIBNAME", "value": value_str})

            else:
                tokens.append({"type": "STRING", "value": value_str})

        else:
            tokens.append({"type": "OPERATOR", "value": char})
            pos += 1
            try: char = data[pos]
            except: char = ""

    return tokens

def parser(tokens):
    ast = []
    pos = 0

    def get_op(index):
        if tokens[index]["type"] == "OPERATOR":
            return tokens[index]["value"]

        print(f"parser: error: expected an operator")
        sys.exit(-1)

    def get_func_tokens(index):
        temp_tokens = []
        ignore = 0

        while True:
            if tokens[index]["type"] == "OPERATOR" and get_op(index) == "{":
                ignore += 1
                index += 1

            elif tokens[index]["type"] == "OPERATOR" and get_op(index) == "}":
                ignore -= 1

                if ignore < 0:
                    print("parser: error: unexpected character: '}'")
                    sys.exit(-1)

                elif ignore == 0:
                    temp_tokens.append(tokens[index])
                    break

                index += 1

            else:
                temp_tokens.append(tokens[index])
                index += 1

        return index, temp_tokens

    def get_call_args(index):
        call_args = []
        ignore = 0

        while True:
            if tokens[index]["type"] == "OPERATOR" and get_op(index) == "(":
                ignore += 1
                index += 1

            elif tokens[index]["type"] == "OPERATOR" and get_op(index) == ")":
                ignore -= 1

                if ignore < 0:
                    print("parser: error: unexpected character: ')'")
                    sys.exit(-1)

                elif ignore == 0:
                    break

                index += 1

            elif tokens[index]["type"] in ["INT", "FLOAT", "IDENTIFIER"]:
                call_args.append(tokens[index])
                index += 1

            else:
                print("parser: error: unexpected token")
                sys.exit(-1)

        return index, call_args

    def get_args(index):
        args = []
        ignore = 0
        temp_type, temp_value = None, None

        while True:
            if tokens[index]["type"] == "OPERATOR" and get_op(index) == "(":
                ignore += 1
                index += 1

            elif tokens[index]["type"] == "OPERATOR" and get_op(index) == ")":
                ignore -= 1

                if ignore < 0:
                    print("parser: error: unexpected character: ')'")
                    sys.exit(-1)

                elif ignore == 0:
                    if temp_type != None and temp_value != None:
                        args.append({"type": temp_type, "value": temp_value})
                        temp_value, temp_type = None, None

                    break

                index += 1

            elif tokens[index]["type"] == "OPERATOR" and get_op(index) == ",":
                if temp_type != None and temp_value != None:
                    args.append({"type": temp_type, "value": temp_value})
                    temp_value, temp_type = None, None

                index += 1

            elif tokens[index]["type"] == "KEYWORD" and tokens[index]["value"] in ["int", "void"]:
                if temp_value != None or temp_type != None:
                    print("parser: error: unexpected keyword: '" + tokens[index]["value"] + "'")
                    sys.exit(-1)

                if tokens[index]["value"] == "void":
                    args.append({"type": "void"})

                else:
                    temp_type = tokens[index]["value"]

                index += 1

            elif tokens[index]["type"] == "IDENTIFIER":
                if temp_value != None or temp_type == None:
                    print("parser: error: unexpected identifier: '" + tokens[index]["value"] + "'")
                    sys.exit(-1)
                    
                temp_value = tokens[index]["value"]
                index += 1

            else:
                print("parser: error: unexpected token")
                sys.exit(-1)

        return index, args

    while pos < len(tokens):
        if tokens[pos]["type"] == "PREPROCCESSOR":
            if tokens[pos]["value"] == "include":
                if tokens[pos + 1]["type"] == "LIBNAME":
                    ast.append({"type": "include", "value": tokens[pos + 1]["value"]})
                    pos += 2

                else:
                    print("parser: error: expected library name after 'include'")
                    sys.exit(-1)

        elif tokens[pos]["type"] == "IDENTIFIER":
            if get_op(pos + 1) == "(":
                name = tokens[pos]["value"]
                pos, temp_call_args = get_call_args(pos + 1)

                if get_op(pos) == ")":
                    if get_op(pos + 1) == ";":
                        ast.append({"type": "call", "name": name, "args": temp_call_args})
                        pos += 2

                    else:
                        print("parser: error: expected ';'")
                        sys.exit(-1)


        elif tokens[pos]["type"] == "KEYWORD":
            if tokens[pos]["value"] in ["int", "void"]:
                if tokens[pos + 1]["type"] == "IDENTIFIER":
                    if get_op(pos + 2) == "(":
                        name = tokens[pos + 1]["value"]
                        return_type = tokens[pos]["value"]
                        pos, temp_args = get_args(pos + 2)

                        if get_op(pos) == ")":
                            if get_op(pos + 1) == ";":
                                ast.append({"type": "func", "return_type": return_type, "name": name, "args": temp_args, "ast": None})
                                pos += 2

                            elif get_op(pos + 1) == "{":
                                pos, temp_tokens = get_func_tokens(pos + 1)
                                ast.append({"type": "func", "return_type": return_type, "name": name, "args": temp_args, "ast": parser(temp_tokens)})
                                pos += 1

                            else:
                                print(f"parser: error: unexpected character: '{get_op(pos + 1)}'")
                                sys.exit(-1)

                else:
                    print("parser: error: expected an identifier")
                    sys.exit(-1)

            elif tokens[pos]["value"] == "return":
                if tokens[pos + 1]["type"] == "INT":
                    if get_op(pos + 2) == ";":
                        ast.append({"type": "return", "value": tokens[pos + 1]})
                        pos += 3

                    else:
                        print("parser: error: expected ';'")
                        sys.exit(-1)

                else:
                    print("parser: error: expected value after 'return'")
                    sys.exit(-1)

        else:
            pos += 1

    return ast

class iostream:
    def __init__(self, module):
        self.module = module
        self.functions = {"print": {"args": [{"type": "INT"}], "func": self.printf}}
        printf_ty = ir.FunctionType(ir.IntType(32), [ir.IntType(8).as_pointer()], var_arg = True)
        self.printf_func = ir.Function(self.module, printf_ty, name = "printf")

    def in_main(self, builder):
        self.builder = builder
        fmt = "%i\n\0"
        c_fmt = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt)), bytearray(fmt.encode("utf8")))
        global_fmt = ir.GlobalVariable(self.module, c_fmt.type, name = "fstr")
        global_fmt.linkage = "internal"
        global_fmt.global_constant = False
        global_fmt.initializer = c_fmt
        self.fmt_arg = builder.bitcast(global_fmt, ir.IntType(8).as_pointer())

    def printf(self, args):
        self.builder.call(self.printf_func, [self.fmt_arg, args[0]])

def ir_generator(ast, module = ir.Module(), builder = None, libs = {}, functions = {}, user_functions = {}):
    for i in ast:
        if i["type"] == "include":
            if i["value"] == "iostream":
                libs[i["value"]] = getattr(__main__, i["value"])(module)
                functions.update(libs[i["value"]].functions)
            
            else:
                print("ir generator: error: no library named: '" + i["name"] + "'")
                sys.exit(-1)

        elif i["type"] == "func":
            temp_args = []

            for j in i["args"]:
                temp_args.append(ir_generator([{"type": j["type"]}]))

            func_type = ir.FunctionType(ir_generator([{"type": i["return_type"]}]), temp_args)
            func = ir.Function(module, func_type, name = i["name"])
            block = func.append_basic_block(name = "entry")
            builder = ir.IRBuilder(block)

            if i["name"] in ["WinMain", "main"]:
                for j in libs:
                    libs[j].in_main(builder)

            ir_generator(i["ast"], builder = builder, libs = libs, functions = functions, user_functions = user_functions)
            user_functions[i["name"]] = {"return_type": i["return_type"], "args": i["args"], "func": func}

        elif i["type"].lower() in ["void", "int"]:
            if i["type"].lower() == "int":
                if "value" in i:
                    return ir.IntType(32)(int(i["value"]))

                else:
                    return ir.IntType(32)

            elif i["type"].lower() == "void":
                return ir.VoidType()

        elif i["type"] == "return":
            builder.ret(ir_generator([i["value"]]))

        elif i["type"] == "call":
            if i["name"] in functions:
                temp_args = []

                if len(functions[i["name"]]["args"]) != len(i["args"]):
                    print("ir generator: error: arguments doesn't match for: '" + i["name"] + "'")
                    sys.exit(-1)

                for index, j in enumerate(i["args"]):
                    if functions[i["name"]]["args"][index]["type"] != j["type"]:
                        print("ir generator: error: arguments doesn't match for: '" + i["name"] + "'")
                        sys.exit(-1)

                    temp_args.append(ir_generator([j]))

                functions[i["name"]]["func"](temp_args)

            elif i["name"] in user_functions:
                print("ir generator: error: not implemented")

            else:
                print("ir generator: error: function '" + i["name"] + "' was not declared in this scope")
                sys.exit(-1)

    return module

def main(argv):
    libs = {}
    module = ir_generator(parser(lexer(open(argv[2], "r").read())), libs = libs)

    binding.initialize()
    binding.initialize_native_target()
    binding.initialize_native_asmprinter()

    target = binding.Target.from_default_triple()
    target_machine = target.create_target_machine()
    module.triple = target_machine.triple

    llvm_ir = str(module)

    if argv[1] == "build":
        with open("temp.llvm", "w") as file:
            file.write(llvm_ir)

        linker = "ld"

        if "iostream" in libs:
            linker = "gcc"

        os.system("llc -filetype=obj temp.llvm")
        os.system(f"{linker} temp.llvm.obj -o main.exe")
        os.remove("temp.llvm.obj")
        os.remove("temp.llvm")

    elif argv[1] == "run":
        def create_execution_engine():
            backing_mod = binding.parse_assembly("")
            engine = binding.create_mcjit_compiler(backing_mod, target_machine)
            return engine

        def compile_ir(engine, llvm_ir):
            mod = binding.parse_assembly(llvm_ir)
            mod.verify()
            engine.add_module(mod)
            engine.finalize_object()
            engine.run_static_constructors()
            return mod

        engine = create_execution_engine()
        mod = compile_ir(engine, llvm_ir)
        func_ptr = engine.get_function_address("main")

        if not func_ptr:
            func_ptr = engine.get_function_address("WinMain")

            if not func_ptr:
                print("main: error: no entry point")
                sys.exit(-1)

        res = CFUNCTYPE(c_int32)(func_ptr)()

        if res != 0:
            print("program exit with code:", res)

    else:
        print("main: error: operation not found")
        sys.exit(-1)
        
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))