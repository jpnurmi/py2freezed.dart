import ast
import sys

class Py2Freezed(ast.NodeVisitor):
    def __init__(self):
        self.nodes = []

    def parse(self, data):
        tree = ast.parse(data)
        return self.visit(tree)

    def visit_ClassDef(self, node):
        if any(base.value.id == 'enum' for base in node.bases):
            self.nodes.append(Py2FreezedEnum(node))

    def to_freezed(self):
        return '\n'.join(str(node) for node in self.nodes)

class Py2FreezedEnum(ast.NodeVisitor):
    def __init__(self, node: ast.ClassDef):
        self.name = node.name
        self.values = []
        self.visit(node)

    def visit_Assign(self, node):
        self.values.append(node.targets[0].id)

    def __str__(self):
        values = ',\n  '.join(self.values)
        return f'''
enum {self.name} {{
  {values},
}}
'''

def main():
    for arg in sys.argv[1:]:
        with open(arg, 'r') as f:
            py2freezed = Py2Freezed()
            py2freezed.parse(f.read())
            print(py2freezed.to_freezed())

if __name__ == "__main__":
    sys.exit(main())
