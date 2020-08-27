import sys
import ply.lex as lex

reserved = {
    'VARIANT': 'VARIANT',
    'TRUE': 'TRUE', 'FALSE': 'FALSE',
    'CONVERT': 'CONVERT', 'BOOL': 'BOOL', 'DIGIT': 'DIGIT', 'STRING': 'STRING', 'TO': 'TO', 'DIGITIZE': 'DIGITIZE',
    'WHILE': 'WHILE', 'ENDW': 'ENDW', 'UNTIL': 'UNTIL', 'ENDU': 'ENDU',
    'IFLESS': 'IFLESS', 'IFNLESS': 'IFNLESS', 'IFZERO': 'IFZERO', 'IFNZERO': 'IFNZERO', 'IFHIGH': 'IFHIGH', 'IFNHIGH': 'IFNHIGH',
    'IFEQUAL': 'IFEQUAL', 'ENDIF': 'ENDIF',
    'COMMAND': 'COMMAND',
    'FUNC': 'FUNC', 'RETURN': 'RETURN', 'PARAM': 'PARAM', 'ENDFUNC': 'ENDFUNC', 'CALL': 'CALL',
}


class Lexer:
    def __init__(self):
        self.lexer = lex.lex(module=self)

    tokens = ['DECIMAL', 'LETTERS', 'NAME', 'NEWLINE',
              'ASSIGNMENT', 'PLUS', 'MINUS',
              'OFBRACKET', 'CFBRACKET',
              'OSQBRACKET', 'CSQBRACKET',
              'COMMA', 'SEMICOLON'] + list(reserved.values())

    t_ASSIGNMENT = r'\='
    t_PLUS = r'\+'
    t_MINUS = r'\-'
    t_OFBRACKET = r'\{'
    t_CFBRACKET = r'\}'
    t_OSQBRACKET = r'\['
    t_CSQBRACKET = r'\]'
    t_COMMA = r'\,'
    t_SEMICOLON = r'\;'
    t_ignore =' \t'

    def t_DECIMAL(self, t):
        r'\d+'
        t.value = int(t.value)
        return t

    def t_LETTERS(self, t):
        r'\"[^\"\n]*\"'
        t.type = reserved.get(t.value, 'LETTERS')
        t.value = str(t.value).strip('\"')
        return t

    def t_NAME(self, t):
        r'[a-zA-Z_][a-zA-Z_0-9]*'
        t.type = reserved.get(t.value, 'NAME')
        return t

    def t_NEWLINE(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)
        return t

    def input(self, data):
        return self.lexer.input(data)

    def token(self):
        return self.lexer.token()

    def t_error(self, t):
        sys.stderr.write(f'Illegal character: {t.value[0]} at line {t.lexer.lineno}\n')
        t.lexer.skip(1)

