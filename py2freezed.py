import ast
import sys

class Py2Freezed(ast.NodeVisitor):
    def __init__(self):
        self.nodes = []

    def parse(self, data: str):
        tree = ast.parse(data)
        return self.visit(tree)

    def visit_ClassDef(self, node: ast.ClassDef):
        if any(base.value.id == "enum" for base in node.bases):
            self.nodes.append(Py2FreezedEnum(node))
        else:
            self.nodes.append(Py2FreezedClass(node))

    def to_freezed(self):
        return "".join(str(node) for node in self.nodes)

class Py2FreezedClass(ast.NodeVisitor):
    def __init__(self, node: ast.ClassDef):
        self.name = node.name
        self.properties = []
        self.visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        self.properties.append(Py2FreezedProperty(node))

    def __str__(self):
        properties = "\n    ".join(str(property) for property in self.properties)
        return f"""
@freezed
class {self.name} with _${self.name} {{
  @JsonSerializable(explicitToJson: true, fieldRename: FieldRename.snake)
  const factory {self.name}({{
    {properties}
  }}) = _{self.name};

  factory {self.name}.fromJson(Map<String, dynamic> json) => _${self.name}FromJson(json);
}}
"""

def dart_name(name: str):
    words = name.split("_")
    return words[0] + "".join(word.title() for word in words[1:])

def dart_type(node: ast.AST):
    type = ""
    if (isinstance(node, ast.Name)):
        type = node.id
    elif (isinstance(node, ast.Subscript)):
        if node.value.id == "Optional":
            type = f"{dart_type(node.slice)}?"
        elif node.value.id == "List":
            type = f"List<{dart_type(node.slice)}>"
        elif node.value.id == "Dict":
            key = dart_type(node.slice.elts[0])
            value = dart_type(node.slice.elts[1])
            type = f"Map<{key}, {value}>"
    return {
        "str": "String",
    }.get(type, type)

def dart_factory(type):
    return {
        "list": "[]",
    }.get(type, type)

def dart_constant(node: ast.Constant):
    if isinstance(node.value, bool):
        return str(node.value).lower()
    if isinstance(node.value, str):
        return f"'{node.value}'"
    if node.value == None:
        return "null"
    return str(node.value)

def dart_attribute(node: ast.Call):
    if node.func.attr == "ib":
        values = [k.value for k in node.keywords if k.arg == 'default']
        return dart_value(values[0] if len(values) > 0 else None)
    elif node.func.attr == "Factory":
        return dart_factory(node.args[0].id)

def dart_value(node: ast.AST):
    if isinstance(node, ast.Constant):
        return dart_constant(node)
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return dart_attribute(node)
    return None

class Py2FreezedProperty(ast.NodeVisitor):
    def __init__(self, node: ast.AnnAssign):
        self.name = node.target.id
        self.type = dart_type(node.annotation)
        self.value = None
        self.visit(node)

    def visit_AnnAssign(self, node):
        self.value = dart_value(node.value)

    def __str__(self):
        name = dart_name(self.name)
        property = f"{self.type} {name}"
        if self.value == None:
            property = f"required {property}"
        if name != self.name:
            property = f"@JsonKey(name: '{self.name}') {property}"
        if self.value != None and self.value != "null":
            property = f"@Default({self.value}) {property}"
        return f"{property},"

class Py2FreezedEnum(ast.NodeVisitor):
    def __init__(self, node: ast.ClassDef):
        self.name = node.name
        self.values = []
        self.visit(node)

    def visit_Assign(self, node):
        self.values.append(node.targets[0].id)

    def __str__(self):
        values = ",\n  ".join(self.values)
        return f"""
enum {self.name} {{
  {values},
}}
"""

def main():
    for arg in sys.argv[1:]:
        with open(arg, "r") as f:
            py2freezed = Py2Freezed()
            py2freezed.parse(f.read())
            print(py2freezed.to_freezed())

if __name__ == "__main__":
    sys.exit(main())
