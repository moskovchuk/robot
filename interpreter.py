import sys
import re
import copy
from parser import Parser
from syntax_tree import SyntaxTreeNode
from robot import Robot, Square, squares
from errors import Error_Handler
from errors import InterpreterRedeclarationError
from errors import InterpreterUndeclaredError
from errors import InterpreterIndexError
from errors import InterpreterConvertError
from errors import InterpreterSumSizeError
from errors import InterpreterSumTypesError
from errors import InterpreterRecursionError


class Variant:
    def __init__(self, first_size=1, second_size=0):
        self.first_size = first_size
        self.second_size = second_size
        self.value = []
        if second_size == 0:
            for i in range(first_size):
                self.value.append({'int': 0, 'bool': False, 'string': ""})
        else:
            for i in range(first_size):
                buf = []
                for j in range(second_size):
                    buf.append({'int': 0, 'bool': False, 'string': ""})
                self.value.append(buf)


class TypeConverter:
    def __init__(self):
        pass

    def conv(self, val, type_to):
        if type(val) == int:
            if type_to == 'int':
                return val
            elif type_to == 'bool':
                return bool(val)
            elif type_to == 'string':
                return str(val)
        elif type(val) == bool:
            if type_to == 'int':
                return int(val)
            elif type_to == 'bool':
                return val
            elif type_to == 'string':
                return self.bool_to_string(val)
        elif type(val) == str:
            if type_to == 'int':
                return self.string_to_int(val)
            elif type_to == 'bool':
                return self.string_to_bool(val)
            elif type_to == 'string':
                return val

    @staticmethod
    def bool_to_string(val):
        if val:
            return 'TRUE'
        else:
            return 'FALSE'

    @staticmethod
    def string_to_int(val):
        try:
            res = int(val)
            print ('tyt')
            return res
        except:
            raise InterpreterConvertError

    @staticmethod
    def string_to_bool(val):
        reg = r'TRUE|FALSE'
        res = re.findall(reg, val)
        if len(res) != 0:
            if res[0] == 'TRUE':
                return True
            else:
                return False
        else:
            raise InterpreterConvertError


class Interpreter:
    def __init__(self, parser=Parser(), converter=TypeConverter()):
        self.parser = parser
        self.converter = converter
        self.program = None
        self.symbol_table = [dict()]
        self.tree = None
        self.functions = None
        self.scope = 0
        self.robot = None
        self.exit = False
        self.correct = True
        self.error = Error_Handler()
        self.error_types = {'UnexpectedError': 0,
                            'RedeclarationError': 1,
                            'UndeclaredError': 2,
                            'IndexError': 3,
                            'ConvertError': 4,
                            'SumSizeError': 5,
                            'SumTypesError': 6,
                            'RecursionError': 7,
                            'ReturnError': 8,
                            'CommandError': 9,
                            'RobotError': 10,
                            'FuncStatementsError': 11,
                            'FuncDescriptionError': 12}

    def interpreter(self, program=None, robot=None):
        self.program = program
        self.robot = robot
        self.symbol_table = [dict()]
        self.tree, self.functions, _ok = self.parser.parse(self.program)
        if _ok:
            self.interpreter_tree(self.tree)
            try:
                self.interpreter_node(self.tree)
                return True
            except RecursionError:
                sys.stderr.write(f'RecursionError: function calls itself too many times\n')
                sys.stderr.write("========= Program has finished with fatal error =========\n")
                return False
        else:
            sys.stderr.write(f'Can\'t interpretate this program. Incorrect syntax!\n')

    def interpreter_tree(self, tree):
        print("Program tree:\n")
        tree.print()
        print('\n')

    def interpreter_node(self, node):
        if node is None:
            return ''
        elif node.type == 'program':
            self.interpreter_node(node.children)
        elif node.type == 'statements' or node.type == 'func_body_statements':
            for child in node.children:
                self.interpreter_node(child)
        elif node.type == 'statement' or node.type == 'func_body_statement':
            self.interpreter_node(node.children)
        elif node.type == 'declaration':
            declaration_child = node.children
            if isinstance(declaration_child, list):
                initialization = node.children[1]
                try:
                    self.declare_variant(declaration_child[0], initialization)
                except InterpreterRedeclarationError:
                    self.error.call(self.error_types['RedeclarationError'], node)
                    self.correct = False
                except InterpreterIndexError:
                    self.error.call(self.error_types['IndexError'], node)
                    self.correct = False
            else:
                try:
                    self.declare_variant(declaration_child)
                except InterpreterRedeclarationError:
                    self.error.call(self.error_types['RedeclarationError'], node)
                    self.correct = False
                except InterpreterIndexError:
                    self.error.call(self.error_types['IndexError'], node)
                    self.correct = False
        elif node.type == 'expression':
            res = self.interpreter_node(node.children)
            if res is None:
                self.error.call(self.error_types['ReturnError'], node.children)
                self.correct = False
                res = 0
            return res
        elif node.type == 'variant':
            if node.value not in self.symbol_table[self.scope].keys():
                self.error.call(self.error_types['UndeclaredError'], node)
                self.correct = False
                buf = 0
            else:
                if node.children is not None and node.children.type != 'empty_varsize':
                    index = node.children.children
                    _index = []
                    if isinstance(index, list):
                        _index.append(self.interpreter_node(index[0]))
                        _index.append(self.interpreter_node(index[1]))
                    else:
                        _index.append(self.interpreter_node(index))
                elif node.children is not None and node.children.type == 'empty_varsize':
                    if isinstance(self.symbol_table[self.scope][node.value][0], list):
                        _index = [0, 0]
                    else:
                        _index = [0]
                else:
                    _index = None
                try:
                    buf = self.get_variant_value(node, index=_index)
                except InterpreterIndexError:
                    self.error.call(self.error_types['IndexError'], node)
                    self.correct = False
                    buf = 0
            return buf
        elif node.type == 'func_param':
            if node.value not in self.symbol_table[self.scope].keys():
                self.error.call(self.error_types['UndeclaredError'], node)
                self.correct = False
                buf = 0
            else:
                if node.children is not None and node.children.type != 'empty_varsize':
                    index = node.children.children
                    _index = []
                    if isinstance(index, list):
                        _index.append(self.interpreter_node(index[0]))
                        _index.append(self.interpreter_node(index[1]))
                    else:
                        _index.append(self.interpreter_node(index))
                elif node.children is not None and node.children.type == 'empty_varsize':
                    if isinstance(self.symbol_table[self.scope][node.value][0], list):
                        _index = [0, 0]
                    else:
                        _index = [0]
                else:
                    _index = None
                buf = self.get_variant_value(node, index=_index)
            return buf
        elif node.type == 'const_expressions':
            buf = []
            if isinstance(self.interpreter_node(node.children[0]), list):
                for buf1 in self.interpreter_node(node.children[0]):
                    buf.append(buf1)
            else:
                buf.append(self.interpreter_node(node.children[0]))
            buf.append(self.interpreter_node(node.children[1]))
            return buf
        elif node.type == 'const_expression':
            return self.interpreter_node(node.children)
        elif node.type == 'decimal_const' or node.type == 'bool_const' or node.type == 'string_const':
            return node.value
        elif node.type == 'unar_op':
            return self.unar_minus(node.children)
        elif node.type == 'bin_op':
            value1 = self.interpreter_node(node.children[0])
            value2 = self.interpreter_node(node.children[1])
            try:
                res = self.bin_plus(value1, value2)
            except InterpreterSumSizeError:
                self.error.call(self.error_types['SumSizeError'], node)
                self.correct = False
                res = 0
            except InterpreterSumTypesError:
                self.error.call(self.error_types['SumTypesError'], node)
                self.correct = False
                res = 0
            return res
        elif node.type == 'decimal_expression':
            buf = self.interpreter_node(node.children)
            if isinstance(buf, list) and isinstance(buf[0], dict) and len(buf) == 1:
                return buf[0]['int']
            elif isinstance(buf, dict):
                return buf['int']
            elif type(buf) == int:
                return buf
            else:
                self.error.call(self.error_types['IndexError'], node)
                self.correct = False
                return 0
        elif node.type == 'bool_expression':
            buf = self.interpreter_node(node.children)
            if isinstance(buf, list) and isinstance(buf[0], dict) and len(buf) == 1:
                return buf[0]['bool']
            elif isinstance(buf, dict):
                return buf['bool']
            elif type(buf) == bool:
                return buf
            else:
                self.error.call(self.error_types['IndexError'], node)
                self.correct = False
                return False
        elif node.type == 'string_expression':
            buf = self.interpreter_node(node.children)
            if isinstance(buf, list) and isinstance(buf[0], dict) and len(buf) == 1:
                return buf[0]['string']
            elif isinstance(buf, dict):
                return buf['string']
            elif type(buf) == str:
                return buf
            else:
                self.error.call(self.error_types['IndexError'], node)
                self.correct = False
                return ''
        elif node.type == 'assignment':
            var_name = node.value.value
            if var_name not in self.symbol_table[self.scope].keys():
                self.error.call(self.error_types['UndeclaredError'], node)
                self.correct = False
            else:
                er = 0
                try:
                    expression = self.interpreter_node(node.children)
                except InterpreterUndeclaredError:
                    self.error.call(self.error_types['UndeclaredError'], node.children)
                    self.correct = False
                    er = 1
                except InterpreterIndexError:
                    self.error.call(self.error_types['IndexError'], node.children.children)
                    self.correct = False
                    er = 1
                if node.value.children is not None and node.value.children.type != 'empty_varsize':
                    _index = node.value.children.children
                    index = []
                    if isinstance(_index, list):
                        index.append(self.interpreter_node(_index[0]))
                        index.append(self.interpreter_node(_index[1]))
                        if index[0] < 0 or index[1] < 0:
                            self.error.call(self.error_types['IndexError'], node.children)
                            self.correct = False
                            er = 1
                    else:
                        index.append(self.interpreter_node(_index))
                        if index[0] < 0:
                            self.error.call(self.error_types['IndexError'], node.children)
                            self.correct = False
                            er = 1
                elif node.value.children is not None and node.value.children.type == 'empty_varsize':
                    if isinstance(self.symbol_table[self.scope][var_name][0], list):
                        index = [0, 0]
                    else:
                        index = [0]
                else:
                    index = None
                if er == 0:
                    try:
                        self.assign(var_name, expression, index)
                    except InterpreterIndexError:
                        self.error.call(self.error_types['IndexError'], node)
                        self.correct = False
        elif node.type == 'convert':
            variant = node.children
            er = 0
            if variant.value not in self.symbol_table[self.scope].keys():
                self.error.call(self.error_types['UndeclaredError'], node)
                self.correct = False
                er = 1
            else:
                if node.children.children is not None and node.children.children.type != 'empty_varsize':
                    _index = node.children.children.children
                    index = []
                    if isinstance(_index, list):
                        index.append(self.interpreter_node(_index[0]))
                        index.append(self.interpreter_node(_index[1]))
                        if index[0] < 0 or index[1] < 0:
                            self.error.call(self.error_types['IndexError'], node.children)
                            self.correct = False
                            er = 1
                    else:
                        index.append(self.interpreter_node(_index))
                        if index[0] < 0:
                            self.error.call(self.error_types['IndexError'], node.children)
                            self.correct = False
                            er = 1
                elif node.children.children is not None and node.children.children.type == 'empty_varsize':
                    if isinstance(self.symbol_table[self.scope][variant.value][0], list):
                        index = [0, 0]
                    else:
                        index = [0]
                else:
                    index = None
                type1 = node.value[0]
                type2 = node.value[1]
                if er == 0:
                    try:
                        self.convert(node.children, index, type1, type2)
                    except InterpreterUndeclaredError:
                        self.error.call(self.error_types['UndeclaredError'], node)
                        self.correct = False
                    except InterpreterIndexError:
                        self.error.call(self.error_types['IndexError'], node)
                        self.correct = False
                    except InterpreterConvertError:
                        self.error.call(self.error_types['ConvertationError'], node)
                        self.correct = False
        elif node.type == 'digitize':
            variant = node.children
            er = 0
            if variant.value not in self.symbol_table[self.scope].keys():
                self.error.call(self.error_types['UndeclaredError'], node)
                self.correct = False
                er = 1
            else:
                if node.children.children is not None and node.children.children.type != 'empty_varsize':
                    _index = node.children.children.children
                    index = []
                    if isinstance(_index, list):
                        index.append(self.interpreter_node(_index[0]))
                        index.append(self.interpreter_node(_index[1]))
                        if index[0] < 0 or index[1] < 0:
                            self.error.call(self.error_types['IndexError'], node.children)
                            self.correct = False
                            er = 1
                    else:
                        index.append(self.interpreter_node(_index))
                        if index[0] < 0:
                            self.error.call(self.error_types['IndexError'], node.children)
                            self.correct = False
                            er = 1
                elif node.children.children is not None and node.children.children.type == 'empty_varsize':
                    if isinstance(self.symbol_table[self.scope][variant.value][0], list):
                        index = [0, 0]
                    else:
                        index = [0]
                else:
                    index = None
                type1 = node.value
                if er == 0:
                    try:
                        self.convert(node.children, index, type1, type2='int')
                    except InterpreterUndeclaredError:
                        self.error.call(self.error_types['UndeclaredError'], node)
                        self.correct = False
                    except InterpreterIndexError:
                        self.error.call(self.error_types['IndexError'], node)
                        self.correct = False
                    except InterpreterConvertError:
                        self.error.call(self.error_types['ConvertationError'], node)
                        self.correct = False
        elif node.type == 'while':
            while self.interpreter_node(node.children['condition']):
                self.interpreter_node(node.children['body'])
        elif node.type == 'until':
            while not self.interpreter_node(node.children['condition']):
                self.interpreter_node(node.children['body'])
        elif node.type == 'if':
            if node.children['condition'].value == 'IFZERO':
                if self.interpreter_node(node.children['conditional_expressions'].children) == 0:
                    self.interpreter_node(node.children['body'])
            elif node.children['condition'].value == 'IFNZERO':
                if self.interpreter_node(node.children['conditional_expressions'].children) != 0:
                    self.interpreter_node(node.children['body'])
            elif node.children['condition'].value == 'IFLESS':
                if self.interpreter_node(node.children['conditional_expressions'].children[0]) < self.interpreter_node(
                        node.children['conditional_expressions'].children[1]):
                    self.interpreter_node(node.children['body'])
            elif node.children['condition'].value == 'IFNLESS':
                if self.interpreter_node(node.children['conditional_expressions'].children[0]) >= self.interpreter_node(
                        node.children['conditional_expressions'].children[1]):
                    self.interpreter_node(node.children['body'])
            elif node.children['condition'].value == 'IFHIGH':
                if self.interpreter_node(node.children['conditional_expressions'].children[0]) > self.interpreter_node(
                        node.children['conditional_expressions'].children[1]):
                    self.interpreter_node(node.children['body'])
            elif node.children['condition'].value == 'IFNHIGH':
                if self.interpreter_node(node.children['conditional_expressions'].children[0]) <= self.interpreter_node(
                        node.children['conditional_expressions'].children[1]):
                    self.interpreter_node(node.children['body'])
            elif node.children['condition'].value == 'IFEQUAL':
                if self.interpreter_node(node.children['conditional_expressions'].children[0]) == self.interpreter_node(
                        node.children['conditional_expressions'].children[1]):
                    self.interpreter_node(node.children['body'])
        elif node.type == 'func_descriptor':
            if self.scope != 0:
                self.correct = False
                self.error.call(self.error_types['FuncDescriptionError'], node)
        elif node.type == 'function_call':
            if node.children is not None:
                param = self.interpreter_node(node.children)
                if type(param) == int:
                    param = [{'int': param, 'bool': False, 'string': ''}]
                elif type(param) == bool:
                    param = [{'int': 0, 'bool': param, 'string': ''}]
                elif type(param) == str:
                    param = [{'int': 0, 'bool': False, 'string': param}]
                elif type(param) == dict:
                    param = [param]
            else:
                param = None
            try:
                res = self.func_call(node.value['name'], param)
            except InterpreterRecursionError:
                self.error.call(self.error_types['RecursionError'], node)
                self.correct = False
                res = 0
            return res
        elif node.type == 'return':
            if self.scope == 0:
                self.error.call(self.error_types['FuncStatementsError'], node)
                self.correct = False
            elif '#RETURN' in self.symbol_table[self.scope].keys():
                pass
            else:
                self.symbol_table[self.scope]['#RETURN'] = self.interpreter_node(node.children)
        elif node.type == 'command':
            if self.robot is None:
                self.error.call(self.error_types['RobotError'], node)
                self.correct = False
                return 0
            string_of_commands = self.interpreter_node(node.children)
            commands = string_of_commands.split()
            reg = r'UP|DOWN|LEFT|RIGHT|LOOKUP|LOOKDOWN|LOOKLEFT|LOOKRIGHT'
            res = []
            for cmd in commands:
                if re.fullmatch(reg, cmd) is None:
                    self.error.call(self.error_types['CommandError'], node)
                    self.correct = False
                    return 0
            for cmd in commands:
                if cmd == 'UP' or cmd == 'DOWN' or cmd == 'LEFT' or cmd == 'RIGHT':
                    res.append(self.move(cmd))
                elif cmd == 'LOOKUP' or cmd == 'LOOKDOWN' or cmd == 'LOOKLEFT' or cmd == 'LOOKRIGHT':
                    res.append(self.look(cmd))
            return res

    def declare_variant(self, variant, init=None):
        if variant.children is not None:
            if variant.children.type == 'empty_varsize':
                raise InterpreterIndexError
            size = variant.children.children
            name = variant.value
            if isinstance(size, list):
                first_size = self.interpreter_node(size[0])
                second_size = self.interpreter_node(size[1])
            else:
                first_size = self.interpreter_node(size)
                second_size = 0
            if first_size < 1 or second_size < 0:
                raise InterpreterIndexError
        elif variant.type == 'init' and variant.value.children is not None:
            if variant.value.children.type == 'empty_varsize':
                raise InterpreterIndexError
            size = variant.value.children.children
            name = variant.value.value
            if isinstance(size, list):
                first_size = self.interpreter_node(size[0])
                second_size = self.interpreter_node(size[1])
            else:
                first_size = self.interpreter_node(size)
                second_size = 0
            if first_size < 1 or second_size < 0:
                raise InterpreterIndexError
        elif variant.type == 'init':
            name = variant.value.value
            first_size = 1
            second_size = 0
        else:
            first_size = 1
            second_size = 0
            name = variant.value
        if init is not None:
            initialization, init_size = self.initialize(init, first_size, second_size)
        else:
            initialization = Variant(first_size, second_size)
            initialization = initialization.value
            init_size = [first_size, second_size]
        if name in self.symbol_table[self.scope].keys():
            raise InterpreterRedeclarationError
        if len(init_size) == 2 and init_size[1] == 1:
            init_size[1] = 0
        else:
            self.symbol_table[self.scope][name] = initialization

    def assign(self, variant, expression, index=None):
        if index is not None:
            new_size = []
            if index[0] > 0:
                new_size.append(index[0] + 1)
            else:
                new_size.append(0)
            if len(index) > 1 and index[1] > 0:
                new_size.append(index[1] + 1)
            else:
                if len(index) > 1 and index[1] == 0 and isinstance(expression, list) and len(expression) > 1:
                    raise InterpreterIndexError
                elif isinstance(expression, list) and len(expression) > 1:
                    new_size.append(len(expression))
                else:
                    new_size.append(0)
            #расширить
            self.extend(variant, new_size)
            if len(index) == 2:
                if isinstance(expression, list) and len(expression) == 1 and isinstance(expression[0], dict):
                    self.symbol_table[self.scope][variant][index[0]][index[1]] = expression[0]
                elif type(expression) == int:
                    self.symbol_table[self.scope][variant][index[0]][index[1]]['int'] = expression
                elif type(expression) == bool:
                    self.symbol_table[self.scope][variant][index[0]][index[1]]['bool'] = expression
                elif type(expression) == str:
                    self.symbol_table[self.scope][variant][index[0]][index[1]]['string'] = expression
                else:
                    raise InterpreterIndexError
            else:
                if isinstance(expression, list) and len(expression) == 1 and isinstance(expression[0], dict):
                    self.symbol_table[self.scope][variant][index[0]] = expression[0]
                elif isinstance(expression, dict):
                    self.symbol_table[self.scope][variant][index[0]] = expression
                elif type(expression) == int:
                    self.symbol_table[self.scope][variant][index[0]]['int'] = expression
                elif type(expression) == bool:
                    self.symbol_table[self.scope][variant][index[0]]['bool'] = expression
                elif type(expression) == str:
                    self.symbol_table[self.scope][variant][index[0]]['string'] = expression
        else:
            if isinstance(expression, list):
                self.symbol_table[self.scope][variant] = expression
            elif isinstance(expression, dict):
                self.symbol_table[self.scope][variant] = [expression]
            else:
                if type(expression) == int:
                    expr_type = 'int'
                elif type(expression) == bool:
                    expr_type = 'bool'
                elif type(expression) == str:
                    expr_type = 'string'
                if isinstance(self.symbol_table[self.scope][variant][0], dict):
                    for elem in self.symbol_table[self.scope][variant]:
                        elem[expr_type] = expression
                elif isinstance(self.symbol_table[self.scope][variant][0], list):
                    for elem1 in range(len(self.symbol_table[self.scope][variant])):
                        for elem2 in self.symbol_table[self.scope][variant][elem1]:
                            elem2[expr_type] = expression
    #расширение размера
    def extend(self, variant, new_size):
        if len(self.symbol_table[self.scope][variant]) < new_size[0]:
            buf = Variant(new_size[0] - len(self.symbol_table[self.scope][variant]), 0).value
            if isinstance(self.symbol_table[self.scope][variant][0], dict) and (
                    len(new_size) == 2 and new_size[1] > 0):
                self.symbol_table[self.scope][variant] = [self.symbol_table[self.scope][variant]]
                for elem in buf:
                    self.symbol_table[self.scope][variant].append([elem])
            elif isinstance(self.symbol_table[self.scope][variant][0], list):
                for elem in buf:
                    self.symbol_table[self.scope][variant].append([elem])
            else:
                for elem in buf:
                    self.symbol_table[self.scope][variant].append(elem)
        if len(new_size) == 2:
            for element in self.symbol_table[self.scope][variant]:
                if len(element) > new_size[1]:
                    new_size[1] = len(element)
                sec_size = new_size[1] - len(element)
                if sec_size == 0:
                    sec_size = -1
                if sec_size == 1:
                    sec_size = 0
                if sec_size > -1:
                    buf = Variant(1, sec_size).value
                    if isinstance(buf[0], list):
                        buf = buf[0]
                    for el in buf:
                        element.append(el)

    def get_variant_value(self, variant, index=None):
        if variant.value not in self.symbol_table[self.scope].keys():
            raise InterpreterUndeclaredError
        else:
            if index is not None:
                if index[0] > 0 and len(self.symbol_table[self.scope][variant.value]) - 1 < index[0]:
                    raise InterpreterIndexError
                if len(index) == 1:
                    return copy.deepcopy(self.symbol_table[self.scope][variant.value][index[0]])
                else:
                    if len(self.symbol_table[self.scope][variant.value][index[0]]) <= index[1]:
                        raise InterpreterIndexError
                    else:
                        return copy.deepcopy(self.symbol_table[self.scope][variant.value][index[0]][index[1]])
            else:
                return copy.deepcopy(self.symbol_table[self.scope][variant.value])

    def initialize(self, initialization, first_size=1, sec_size=0):
        _init = self.makeinitializator(initialization)
        init_size = []
        init_size.append(len(_init))
        if init_size[0] > first_size:
            return _init, init_size
        if type(_init[0]) == list:
            sec_size = len(_init[0])
        else:
            sec_size = 0
        init_size.append(sec_size)
        return _init, init_size

    def makeinitializator(self, initialization):
        if initialization.type == 'init_lists':
            init = []
            first = self.makeinitializator(initialization.children[0])
            last = self.makeinitializator(initialization.children[1])
            if type(first[0]) == list or len(first) == 1 or len(last) == 1:
                for first_init in first:
                    init.append(first_init)
            else:
                init.append(first)
            if len(last) == 1:
                init.append(last[0])
            else:
                init.append(last)
            return init
        else:
            if initialization.type == 'empty_init_list':
                init = Variant(1)
                return init
            elif initialization.type == 'init_list':
                initialization = initialization.children
            if initialization.type == 'inits':
                init = []
                first = self.makeinitializator(initialization.children[0])
                for init1 in first:
                    init.append(init1)
                last = self.makeinitializator(initialization.children[1])
                init.append(last[0])
                return init
            elif initialization.type == 'const_expression':
                init = Variant(1)
                init = init.value
                init1 = self.interpreter_node(initialization.children[0])
                if type(init1) == int:
                    init[0]['int'] = init1
                elif type(init1) == bool:
                    init[0]['bool'] = init1
                elif type(init1) == str:
                    init[0]['string'] = init1
                return init
            elif initialization.type == 'const_expressions':
                init = Variant(1)
                init = init.value
                _init = []
                inits = self.interpreter_node(initialization.children[0])
                if isinstance(self.interpreter_node(initialization.children[0]), list):
                    for init1 in inits:
                        _init.append(init1)
                else:
                    _init.append(self.interpreter_node(initialization.children[0]))
                _init.append(self.interpreter_node(initialization.children[1]))
                for i in _init:
                    if type(i) == int:
                        init[0]['int'] = i
                    elif type(i) == bool:
                        init[0]['bool'] = i
                    elif type(i) == str:
                        init[0]['string'] = i
                return init

    def unar_minus(self, _expression):
        value = self.interpreter_node(_expression)
        if type(value) == int:
            value = - value
        elif type(value) == bool:
            value = not value
        elif type(value) == str:
            value = self.string_negation(value)
        elif type(value) == dict:
            value['int'] = -value['int']
            value['bool'] = not value['bool']
        elif type(value) == list:
            for elem in value:
                if isinstance(elem, list):
                    for elem1 in elem:
                        elem1['int'] = -elem1['int']
                        elem1['bool'] = not elem1['bool']
                        elem1['string'] = self.string_negation(elem1['string'])
                else:
                    elem['int'] = -elem['int']
                    elem['bool'] = not elem['bool']
                    elem['string'] = self.string_negation(elem['string'])
        return value

    def string_negation(self, value):
        words = value.split()
        res = ''
        for word in words:
            if word == 'UP':
                newword = 'DOWN'
            elif word == 'DOWN':
                newword = 'UP'
            elif word == 'LEFT':
                newword = 'RIGHT'
            elif word == 'RIGHT':
                newword = 'LEFT'
            elif word == 'LOOKUP':
                newword = 'LOOKDOWN'
            elif word == 'LOOKDOWN':
                newword = 'LOOKUP'
            elif word == 'LOOKLEFT':
                newword = 'LOOKRIGHT'
            elif word == 'LOOKRIGHT':
                newword = 'LOOKLEFT'
            else:
                newword = word
            res += newword + ' '
        res = res[:-1]
        return res

    def bin_plus(self, _expression1, _expression2):
        value1 = _expression1
        value2 = _expression2
        if type(value1) == list and type(value2) == list:
            if len(value1) != len(value2):
                raise InterpreterSumSizeError
            elif type(value1[0]) != type(value2[0]):
                raise InterpreterSumSizeError
            else:
                for i in range(len(value1)):
                    if type(value1[i]) == dict:
                        value1[i] = self.bin_plus(value1[i], value2[i])[0]
                    else:
                        value1[i] = self.bin_plus(value1[i], value2[i])
                return value1
        if type(value1) == int and type(value2) == int:
            return value1 + value2
        elif type(value1) == bool and type(value2) == bool:
            return value1 or value2
        elif type(value1) == str and type(value2) == str:
            return value1 + value2
        elif type(value1) == list and len(value1) == 1:
            value1 = value1[0]
        if type(value1) == dict:
            if type(value2) == int:
                value1['int'] += value2
                return [value1]
            elif type(value2) == bool:
                value1['bool'] = value1['bool'] or value2
                return [value1]
            elif type(value2) == str:
                value1['string'] += value2
                return [value1]
        if type(value2) == list and len(value2) == 1:
            value2 = value2[0]
        if type(value2) == dict:
            if type(value1) == int:
                value2['int'] += value1
                return [value2]
            elif type(value2) == bool:
                value2['bool'] = value2['bool'] or value1
                return [value2]
            elif type(value2) == str:
                value2['string'] += value1
                return [value2]
        if type(value1) == dict and type(value2) == dict:
            value = [{'int': 0, 'bool': False, 'string': ""}]
            value[0]['int'] = value1['int'] + value2['int']
            value[0]['bool'] = value1['bool'] or value2['bool']
            value[0]['string'] = value1['string'] + value2['string']
            return value
        elif type(value1) == list:
            for elem in value1:
                if isinstance(elem, list):
                    for elem1 in elem:
                        if type(value2) == int:
                            elem1['int'] += value2
                        elif type(value2) == bool:
                            elem1['bool'] = elem1['bool'] or value2
                        elif type(value2) == str:
                            elem1['string'] += value2
                else:
                    if type(value2) == int:
                        elem['int'] += value2
                    elif type(value2) == bool:
                        elem['bool'] = elem['bool'] or value2
                    elif type(value2) == str:
                        elem['string'] += value2
            return value1
        raise InterpreterSumTypesError

    def convert(self, variant, index, type1, type2):
        if type1 == 'DIGIT':
            type1 = 'int'
        elif type1 == 'BOOL':
            type1 = 'bool'
        elif type1 == 'STRING':
            type1 = 'string'
        if type2 == 'DIGIT':
            type2 = 'int'
        elif type2 == 'BOOL':
            type2 = 'bool'
        elif type2 == 'STRING':
            type2 = 'string'
        val = self.get_variant_value(variant, index)
        if (len(val) == 1):
            try:
                res = self.converter.conv(val[0][type1], type2)
            except InterpreterConvertError:
                sys.stderr.write(f'ConvertError\n')
                return
            if index is not None and len(index) == 1:
                self.symbol_table[self.scope][variant.value][index[0]][type2] = res
            elif index is not None:
                self.symbol_table[self.scope][variant.value][index[0]][index[1]][type2] = res
        elif (len(val) > 1):
            for i in range(len(val)):
                if isinstance(val[i], list):
                    for j in range(len(val[i])):
                        try:
                            res = self.converter.conv(val[i][j][type1], type2)
                        except InterpreterConvertError:
                            sys.stderr.write(f'ConvertError\n')
                            return
                        self.symbol_table[self.scope][variant.value][i][j][type2] = res

    def func_call(self, name, parametr=None):
        if name not in self.functions.keys():
            raise InterpreterUndeclaredError
        self.scope += 1
        if self.scope > 1000:
            self.scope -= 1
            raise InterpreterRecursionError
        self.symbol_table.append(dict())
        if parametr is not None:
            self.symbol_table[self.scope]['PARAM'] = parametr
        self.interpreter_node(self.functions[name].children['body'])
        if '#RETURN' in self.symbol_table[self.scope].keys():
            result = copy.deepcopy(self.symbol_table[self.scope]['#RETURN'])
        else:
            result = None
        self.symbol_table.pop()
        self.scope -= 1
        return result

    def move(self, command):
        res = self.robot.move(command)
        self.exit = self.robot.exit()
        return {'int': 0, 'bool': res, 'string': ''}

    def look(self, command):
        type, distance = self.robot.look(command)
        return {'int': distance, 'bool': False, 'string': type}

def make_robot(descriptor):
    with open(descriptor) as file:
        info = file.read()
    info = info.split('\n')
    map_size = info.pop(0).split()
    robot_coordinates = info.pop(0).split()
    x = int(robot_coordinates[0])
    y = int(robot_coordinates[1])
    map = [0] * int(map_size[0])
    for i in range(int(map_size[0])):
        map[i] = [0] * int(map_size[1])
    for i in range(int(map_size[0])):
        for j in range(int(map_size[1])):
            map[i][j] = Square("EMPTY")
    buf = 0
    while len(info) > 0:
        ln = list(info.pop(0))
        ln = [Square(squares[i]) for i in ln]
        map[buf] = ln
        buf += 1
    return Robot(x, y, map)


if __name__ == '__main__':
    tests = ['sum.txt', 'func.txt', 'sort.txt', 'syntax_errors.txt', 'interpreter_errors.txt', 'recursion.txt']
    maps = ['no_island.txt', 'map_without_exit.txt', 'empty_map.txt',
            'one_island.txt', 'two_islands.txt', 'ring_in_center.txt']
    algo = ['pledge_algorithm.txt']
    print("Make your choice: 1 - test, 2 - robot")
    n = int(input())
    if n == 1:
        i = Interpreter()
        print(
            'Which test do you want to run?\n0 - Simple addition\n1 - Simple function\n2 - Sort\n3 - Syntax errors\n4 - Interpreter errors\n5 - Recursion error')
        num = int(input())
        if num not in range(len(tests)):
            print('Wrong choice')
        else:
            prog = open(tests[num], 'r').read()
            res = i.interpreter(program=prog)
            if res:
                print('Result symbol table:')
                for key, value in i.symbol_table[0].items():
                    print(key, '=', value)
    elif n == 2:
        print(
            "Which map do you want to use?\n0 - Simple map\n1 - Map without exit\n2 - Empty map\n3 - One island\n4 - Two islands\n5 - Ring in center")
        num = int(input())
        if num not in range(len(maps)):
            print('Wrong choice')
        else:
            robot = make_robot(maps[num])
            i = Interpreter()
            prog = open(algo[0], 'r').read()
            res = i.interpreter(robot=robot, program=prog)
            if res:
                print('Result symbol table:')
                for key, value in i.symbol_table[0].items():
                    print(key, '=', value)
            if i.exit:
                print('\n###### Exit has been found!!! ######\n')
            else:
                print('\n###### Exit hasn\'t been found :( ######\n')
            print('Robot:', i.robot)
            print('Map:')
            i.robot.show()
    else:
        print('Wrong choice!\n')