import re

class Token:
    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"Token(type='{self.type}', value={self.value})"

def tokenize(code):
    keywords = {'fn', 'in', 'out', 'gb', 'nor', 'rt'}
    logic_operators = {'and', 'xor', 'or', 'not', 'nand', 'nor', 'xnor'}
    tokens = []

    code = re.sub(r'\/\/.*', '', code)  # Eliminar comentarios
    code = code.replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')

    # Utilizar una expresión regular más robusta para la tokenización
    pattern = re.compile(r'\b(?:' + '|'.join(map(re.escape, keywords)) + r')\b|0x[0-9A-Fa-f]+\b|fx[0-9A-Fa-f]+\b|1x[0-9A-Fa-f]+\b|\d+\b|=\b|\b(?:and|or|xor|not|nand|nor|xnor)\b|;|#|{|}')
    matches = pattern.finditer(code)

    for match in matches:
        token_str = match.group(0)
        if token_str.startswith('0x'):
            tokens.append(Token('hex', token_str))
        elif token_str.startswith('fx'):
            tokens.append(Token('fn', str(token_str)))
        elif token_str.startswith('1x'):
            tokens.append(Token('fncall', str(token_str)))
        elif token_str == 'in':
            tokens.append(Token('input'))
        elif token_str == 'out':
            tokens.append(Token('out'))
        elif token_str == '#':
            tokens.append(Token('end'))
        elif token_str == '0' or token_str == '1':
            tokens.append(Token('bit', token_str))
        elif token_str == ';':
            tokens.append(Token('semicolon'))
        elif token_str == '{':
            tokens.append(Token('openbracket'))
        elif token_str == '}':
            tokens.append(Token('closedbracket'))
        elif token_str in logic_operators:
            tokens.append(Token('logicoperator', token_str))
        else:
            tokens.append(Token(token_str))

    return tokens

def parse_tokens(tokens):
    ast = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        if token.type == 'hex':
            # Asignación de variable
            if tokens[i + 1].type == 'bit' or tokens[i - 1].type == "semicolon" or tokens[i-1].type == "openbracket" or tokens[i + 1].type == 'input':
                variable = token.value
                if tokens[i + 1].type == "input":
                    value = str(input(":"))

                    if value != '0' and value != '1':
                        handle_errors("Value error", f"Unexpected input on: {token.value}. Not binary")
                else:
                    value = tokens[i + 1].value
                ast.append(AssignmentNode(variable, value))
                i += 2
            elif tokens[i - 1].type == 'logicoperator' or tokens[i - 1].type == 'out' or tokens[i - 1].type == "fnCall":
                pass
            else:
                handle_errors("Syntax error", f"Unexpected token: {token.value}", code_segment=str(tokens[i:i+3]))
        elif tokens[i].type == "end":
            break
        elif token.type == 'fn':
            # Definición de función
            name = token.value
            arguments = []

            # Recoger los argumentos de la función
            i += 1
            while i < len(tokens) and tokens[i].type != 'openbracket':
                if tokens[i].type != "hex":
                    handle_errors("Syntax error", f"Unexpected token: {token.value}", code_segment=str(tokens[i:i+3]))
                else:
                    arguments.append(tokens[i].value)
                    i += 1

            # Buscar el índice del token que contiene '}'
            closing_brace_index = find_closing_symbol(tokens, i, 'openbracket', 'closedbracket')

            # Verificar si se encontró el token '}'
            if closing_brace_index is not None:
                # Parsear el cuerpo de la función
                body = parse_function_body(tokens[i:closing_brace_index])
                ast.append(FunctionNode(name, arguments, body))
                i = closing_brace_index + 1  # Saltar '}'
            else:
                handle_errors("Syntax error", "Missing closing brace '}'")
        elif token.type == 'out':
            # Imprimir por pantalla
            out_index = i
            while tokens[out_index + 1].type in {'hex', 'logicoperator', 'bit', 'fncall'}: 
                out_index += 1
            
            arguments = [[tokens[j].type, tokens[j].value] for j in range(i + 1, out_index + 1)]

            ast.append(PrintNode('out', arguments))

            i = out_index + 1
        elif token.type == 'semicolon':
            # Asignación de variable
            if len(tokens) == i+1:
                handle_errors("Syntax error", f"Expected # token at the end line :(")

            if tokens[i + 1].type == "end":
                break

            if tokens[i - 1].type == 'logicoperator' or (tokens[i - 1].type == "semicolon" or tokens[i+1].type == "semicolon"):
                handle_errors("Syntax error", f"Unexpected token: {token.type}", code_segment=str(tokens[i:i+3]))
            i += 1
        else:
            handle_errors("Syntax error", f"Unexpected token: {token.value}", code_segment=str(tokens[i]))

    return ast

def find_closing_symbol(tokens, start_index, open, close):
    count = 1
    i = start_index + 1

    while i < len(tokens) and count > 0:
        if tokens[i].type == open:
            count += 1
        elif tokens[i].type == close:
            count -= 1
        i += 1

    if count == 0:
        return i - 1  # Índice del token que contiene '}'
    else:
        return None  # No se encontró el token '}'

class AssignmentNode:
    def __init__(self, variable, value):
        self.variable = variable
        self.value = value

class AssignmentFunctionNode:
    def __init__(self, variable, name, arguments):
        self.name = name
        self.arguments = arguments
        self.variable = variable

class FunctionNode:
    def __init__(self, name, arguments, body):
        self.name = name
        self.arguments = arguments
        self.body = body

class AssignmentOperationNode:
    def __init__(self, variable, value):
        self.variable = variable
        self.value = value

class OperationNode:
    def __init__(self, operator, operands):
        self.operator = operator
        self.operands = operands

class PrintNode:
    def __init__(self, function_name, arguments):
        self.function_name = function_name
        self.arguments = arguments

class ReturnNode:
    def __init__(self, variable):
        self.variable = variable
    def execute(self, variables, functions):
        return variables.get(self.variable, None)

def parse_function_body(tokens):
    body = []
    i = 1  # Iniciar después de '{'

    while i < len(tokens) and tokens[i].type != 'closedbracket':
        token = tokens[i]

        if token.type == 'hex':
            # Asignación de variable
            if (tokens[i + 1].type == 'bit' or tokens[i - 1].type == "semicolon" or tokens[i + 1].type == 'input') and tokens[i+2].type == 'semicolon':
                variable = token.value
                if tokens[i + 1].type == "input":
                    value = str(input(":"))

                    if value != '0' and value != '1':
                        handle_errors("Value error", f"Unexpected input in function: {token.value}. Not binary")
                else:
                    value = tokens[i + 1].value
                body.append(AssignmentNode(variable, value))
                i += 2
            elif tokens[i+1].type == "fncall":
                i += 2
                arguments = []
                while i < len(tokens) and tokens[i].type != 'semicolon':
                    if tokens[i].type != "hex":
                        handle_errors("Syntax error", f"Unexpected function token: {token.value}", code_segment=str(tokens[i:i+3]))
                    else:
                        arguments.append(tokens[i].value)
                        i += 1
                print(arguments)
                body.append(AssignmentFunctionNode(variable, tokens[i+1].value, arguments))
            
            elif tokens[i + 2].type == 'logicoperator' and (tokens[i + 1].type == "hex" or tokens[i + 1].type == "bit") and (tokens[i + 1].type == "hex" or tokens[i + 1].type == "bit"):
                out_index = i
                variable = token.value
                
                while tokens[out_index + 1].type in {'hex', 'logicoperator', 'bit', 'fncall'}: 
                    out_index += 1
                
                arguments = [[tokens[j].type, tokens[j].value] for j in range(i + 1, out_index + 1)]
                body.append(AssignmentOperationNode(variable, arguments))

                i = out_index + 1
            elif (tokens[i + 2].type == 'hex' or tokens[i + 2].type == 'bit') and tokens[i + 1].type == "logicoperator" and tokens[i+3].type == "semicolon":
                out_index = i
                variable = token.value
                
                while tokens[out_index + 1].type in {'hex', 'logicoperator', 'bit'}: 
                    out_index += 1
                
                arguments = [[tokens[j].type, tokens[j].value] for j in range(i + 1, out_index + 1)]

                body.append(AssignmentOperationNode(variable, arguments))

                i = out_index + 1
            else:
                handle_errors("Syntax error", f"Unexpected token in function body: {token.value}", code_segment=str(tokens[i:i+3]))
        elif token.type == 'gb':
            # Nodo para guardar el valor en una variable
            variable = tokens[i + 1].value
            body.append(AssignmentNode(variable, "gb " + tokens[i + 1].value))
            i += 3
        elif token.type == 'rt':
            # Nodo para un return
            body.append(ReturnNode(tokens[i+1].value))
            break  # No se espera más código después de una operación lógica
        elif token.type == 'semicolon':
            # Asignación de variable
            if len(tokens) == i+1:
                handle_errors("Syntax error", f"Expected # token at the end line :(")

            if tokens[i + 1].type == "end":
                break

            if tokens[i - 1].type == 'logicoperator' or (tokens[i - 1].type == "semicolon" or tokens[i+1].type == "semicolon"):
                handle_errors("Syntax error", f"Unexpected token: {token.type}", code_segment=str(tokens[i:i+3]))
            i += 1
        else:
            handle_errors("Syntax error", f"Unexpected token in function body: {token.value}")

    return body

def execute_print_node(node, variables, functions):
    if node.function_name == 'out':
        for arg_type, arg_value in node.arguments:
            if arg_type == 'fncall':
                # Llamada a función
                if arg_value in functions:
                    function_result = execute_function(arg_value, functions[arg_value].arguments, variables, functions)
                    print(function_result)
                else:
                    handle_errors("FunctionError", f"Function '{arg_value}' not defined")
            elif arg_type in {'hex', 'bit'}:
                # Imprimir el valor de la variable
                if arg_value in variables:
                    print(variables[arg_value])
                else:
                    handle_errors("VariableError", f"Variable '{arg_value}' not defined")
            elif arg_type == 'logicoperator':
                # Ejecutar la operación lógica y imprimir el resultado
                result = int(execute_operation(arg_value, [node.arguments[i + 1][1] for i in range(len(node.arguments) - 1)], variables))
                print(result)
            else:
                handle_errors("SyntaxError", f"Unexpected argument type in 'out': {arg_type}")

def execute_function(function_name, arguments, variables, functions):
    if function_name in functions:
        if len(arguments) == len(functions[function_name].arguments):
            # Asigna los valores de los argumentos a las variables locales de la función
            local_variables = dict(zip(functions[function_name].arguments, arguments))
            # Ejecuta el cuerpo de la función
            result = execute_ast(functions[function_name].body, local_variables, functions, variables)
            # Si la función no tiene una declaración de retorno, devuelve un valor por defecto (puede ser modificado según tus necesidades)
            return result if result is not None else print("No return")
        else:
            handle_errors("ArgumentError", f"Function '{function_name}' expects {len(functions[function_name].arguments)} arguments, but {len(arguments)} provided")
    else:
        handle_errors("FunctionError", f"Function '{function_name}' not defined")

def execute_ast(ast, variables=None, functions=None, externalVariables=None):
    if variables is None:
        variables = {}

    if functions is None:
        functions = {}

    for node in ast:
        if isinstance(node, AssignmentNode) and node.value.startswith("gb "):
            # Acceder al valor de la variable externa indicada por "gb" y asignarlo a la variable interna
            external_variable_name = node.value[3:]
            if external_variable_name in externalVariables:
                variables[node.variable] = externalVariables[external_variable_name]
            else:
                handle_errors("VariableError", f"Global variable '{external_variable_name}' not defined")
        
        elif isinstance(node, AssignmentNode):
            variables[node.variable] = node.value
        elif isinstance(node, AssignmentFunctionNode):
            variables[node.variable] = execute_function(node.name, node.arguments, variables, functions)
        elif isinstance(node, AssignmentOperationNode):
            for arg_type, arg_value in node.value:
                if arg_type == 'fncall':
                    # Llamada a función
                    if arg_value in functions:
                        function_result = execute_function(arg_value, functions[arg_value].arguments, variables, functions)
                        variables[node.variable] = function_result
                    else:
                        handle_errors("FunctionError", f"Function '{arg_value}' not defined")
                elif arg_type in {'hex', 'bit'}:
                    # Imprimir el valor de la variable
                    if arg_value in variables:
                        variables[node.variable] = variables[arg_value]
                    else:
                        handle_errors("VariableError", f"Variable '{arg_value}' not defined")
                elif arg_type == 'logicoperator':
                    # Ejecutar la operación lógica y imprimir el resultado
                    result = int(execute_operation(arg_value, [node.value[i][1] for i in range(0, len(node.value)) if node.value[i][0] in ["hex", "bit"]], variables))
                    variables[node.variable] = result
                    break
                else:
                    handle_errors("SyntaxError", f"Unexpected argument type in 'out': {arg_type}")

        elif isinstance(node, FunctionNode):
            node.name = '1x' + node.name[2:]
            functions[node.name] = node
        elif isinstance(node, OperationNode):
            result = execute_operation(node.operator, node.operands, variables)
            return result
        elif isinstance(node, PrintNode):
            execute_print_node(node, variables, functions)
        elif isinstance(node, ReturnNode):
            return_value = node.execute(variables, functions)
            return return_value
        else:
            handle_errors("TypeError", f"Unexpected node type: {type(node)}")

def execute_operation(operator, operands, variables):
    values = [int(str(variables.get(operand, operand)), 2) for operand in operands]

    if operator == 'and':
        return all(values)
    elif operator == 'or':
        return any(values)
    elif operator == 'xor':
        return sum(values) % 2 == 1
    elif operator == 'nor':
        return not any(values)
    elif operator == 'nand':
        return not all(values)
    elif operator == 'xnor':
        return sum(values) % 2 == 0
    elif operator == 'not':
        if len(values) == 1:
            return not values[0]
        else:
            handle_errors("Invalid operand count", "The 'not' operator should have one operand")
    else:
        handle_errors("Unknown operator", f"Unsupported logical operator: {operator}")


def parse_file(file_path):
    with open(file_path, "r") as file:
        code = file.read()

    return code

def handle_errors(error_type, details, code_segment=None):
    # Implementar la lógica de manejo de errores aquí
    # Mostrar mensajes de error informativos

    print(f"Error: {error_type} - {details}")

    if code_segment is not None:
        print(code_segment)

    exit()

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python interpreter.py <file.bpl> or <file.thon>")
        sys.exit(1)

    file_path = sys.argv[1]
    code = parse_file(file_path)
    tokens = tokenize(code)
    ast = parse_tokens(tokens)
    execute_ast(ast)