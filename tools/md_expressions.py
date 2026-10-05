"""Pure, bounded compilation caches for the test MD interpreter.

Only strings and Python code objects are shared. Evaluation and mutable MD values
belong to each Runner; this module never sees a runner or its environment.
"""
import ast
from functools import lru_cache
import re


@lru_cache(maxsize=8192)
def normalize_path(expression):
    # Variable sigils are syntax; sigils inside string keys are data.
    expression = ''.join(
        part if i % 2 else part.replace('$', '').replace('@', '')
        for i, part in enumerate(re.split(r"('(?:[^'\\]|\\.)*')", expression))
    )
    while '.{' in expression:
        expression = re.sub(r'\.\{([^{}]+)\}', r'[\1]', expression)
    return expression


class NativeLists(ast.NodeTransformer):
    def visit_List(self, node):
        self.generic_visit(node)
        return ast.copy_location(
            ast.Call(func=ast.Name(id='List', ctx=ast.Load()), args=[node], keywords=[]), node
        )


@lru_cache(maxsize=8192)
def compile_expression(expression):
    """Compile an ordinary expression, keyed by its original MD source text."""
    s = normalize_path(expression)
    s = re.sub(r'typeof (\w+(?:\.[\w]+|\[[^\]]+\])*)', r'datatype_of(\1)', s)
    s = re.sub(r'(\w+(?:\.[\w]+|\[[^\]]+\])*)\?', r'defined(\1)', s)
    s = re.sub(r'\(([^()]*)\)(LF|f|L|i)\b',
               lambda m: {'LF': 'float', 'f': 'float', 'L': 'int', 'i': 'Int32'}[m[2]] + '(' + m[1] + ')', s)
    s = re.sub(r'(\d+(?:\.\d+)?)(?:LF|f|L)\b', r'\1', s)
    s = re.sub(r'(\d+(?:\.\d+)?)deg\b', r'Angle(\1)', s)
    for unit, scale in [('min', 60), ('km', 1000), ('m', 1), ('Cr', 100), ('h', 3600), ('s', 1)]:
        s = re.sub(r'(\d+(?:\.\d+)?)' + unit + r'\b', lambda m: str(float(m[1]) * scale), s)
    for md, py in [(' ge ', ' >= '), (' le ', ' <= '), (' gt ', ' > '), (' lt ', ' < ')]:
        s = s.replace(md, py)
    while re.search(r'\[([^\[\]]+)\]\.(min|max)', s):
        s = re.sub(r'\[([^\[\]]+)\]\.(min|max)', r'\2(\1)', s)
    tree = NativeLists().visit(ast.parse(s, mode='eval'))
    return compile(ast.fix_missing_locations(tree), '<md expression>', 'eval')
