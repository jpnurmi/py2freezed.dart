import ast
import sys
from typing import Any, List
from unicodedata import name

class EnumDef(ast.stmt):
    name: str
    values: List[ast.expr]

class UnionDef(ast.stmt):
    if sys.version_info >= (3, 10):
        __match_args__ = ("name", "classes")
    name: str
    classes: List[ast.ClassDef]

class Py2Freezed(ast.NodeVisitor):
    def __init__(self):
        self.nodes = []

    def parse(self, data: str):
        node = ast.parse(data)

        node = Factory2Constant().visit(node)
        ast.fix_missing_locations(node)

        node = Default2Constant().visit(node)
        ast.fix_missing_locations(node)

        node = Union2Class().visit(node)
        ast.fix_missing_locations(node)

        node = Class2Enum().visit(node)
        ast.fix_missing_locations(node)

        return self.visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.nodes.append(Py2FreezedClass(node))

    def visit_EnumDef(self, node: EnumDef):
        self.nodes.append(Py2FreezedEnum(node))

    def visit_UnionDef(self, node: UnionDef):
        self.nodes.append(Py2FreezedUnion(node))

    def to_freezed(self):
        return "".join(str(node) for node in self.nodes)

class Class2Enum(ast.NodeTransformer):
    class EnumScanner(ast.NodeVisitor):
        values: List[ast.expr] = []
        def visit_Assign(self, node: ast.Assign):
            self.values.extend(node.targets)

    def visit_ClassDef(self, node: ast.ClassDef):
        scanner = self.EnumScanner()
        scanner.visit(node)
        if any(base.value.id == "enum" for base in node.bases):
            return EnumDef(name=node.name, values=scanner.values)
        return self.generic_visit(node)

# Call(
#   func=Attribute(
#     value=Name(id='attr', ctx=Load()),
#     attr='Factory',
#     ctx=Load()
#   ),
#   args=[Name(id='list', ctx=Load())],
#   keywords=[]
# )
class Factory2Constant(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "Factory" and \
            isinstance(node.func.value, ast.Name) and node.func.value.id == "attr" and \
            isinstance(node.args[0], ast.Name) and node.args[0].id == "list":
            return ast.Constant(value=[])
        return self.generic_visit(node)

# Call(
#   func=Attribute(
#     value=Name(id='attr', ctx=Load()),
#     attr='ib',
#     ctx=Load()
#   ),
#   args=[],
#   keywords=[keyword(arg='default', value=Constant(value=False))]
# )
class Default2Constant(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "ib" and \
            isinstance(node.func.value, ast.Name) and node.func.value.id == "attr":
                values = [k.value for k in node.keywords if k.arg == 'default']
                if len(values) == 1 and isinstance(values[0], ast.Constant):
                    return values[0].value
        return self.generic_visit(node)

# Assign(
#   targets=[Name(id='AnyStep', ctx=Store())],
#   value=Subscript(
#     value=Name(id='Union', ctx=Load()),
#     slice=Tuple(elts=[
#         Name(id='StepPressKey', ctx=Load()),
#         Name(id='StepKeyPresent', ctx=Load()),
#         Name(id='StepResult', ctx=Load())
#       ],
#       ctx=Load()
#     ),
#     ctx=Load()
#   )
# )
class Union2Class(ast.NodeTransformer):
    class UnionScanner(ast.NodeTransformer):
        def __init__(self):
            self.named = {}
            self.unnamed = []

        def visit_Assign(self, node: ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and \
                isinstance(node.value, ast.Subscript) and \
                isinstance(node.value.value, ast.Name) and node.value.value.id == "Union":
                names = [e.id for e in node.value.slice.elts if isinstance(e, ast.Name)]
                self.named[node.targets[0].id] = names
                return None
            return self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == "Union":
                names = [e.id for e in node.slice.elts if isinstance(e, ast.Name)]
                self.unnamed.append(names)
                return ast.Name('Or'.join(names))
            return self.generic_visit(node)

    def __init__(self):
        self.scanner = self.UnionScanner()
        self.unions = {}

    def visit_ClassDef(self, node: ast.ClassDef):
        for k, v in self.scanner.named.items():
            if node.name in v:
                if k in self.unions:
                    self.unions[k].classes.append(node)
                    return None
                union = UnionDef(name=k, classes=[node])
                self.unions[k] = union
                return union
        for v in self.scanner.unnamed:
            if node.name in v:
                k = 'Or'.join(v)
                if k in self.unions:
                    self.unions[k].classes.append(node)
                    return None
                union = UnionDef(name=k, classes=[node])
                self.unions[k] = union
                return union
        return self.generic_visit(node)

    def visit_Module(self, node: ast.Module):
        node = self.scanner.visit(node)
        return self.generic_visit(node)

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
    return words[0][:1].lower() + words[0][1:] + "".join(word.title() for word in words[1:])

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

def dart_value(node: ast.AST):
    if not isinstance(node, ast.Constant):
        return None
    if isinstance(node.value, bool):
        return str(node.value).lower()
    if isinstance(node.value, str):
        return f"'{node.value}'"
    if node.value == None:
        return "null"
    return str(node.value)

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

class Py2FreezedUnion(ast.NodeVisitor):
    def __init__(self, node: UnionDef):
        self.name = node.name
        self.classes = [Py2FreezedClass(c) for c in node.classes]

    def _format(self, cls: Py2FreezedClass):
        properties = "\n    ".join(str(property) for property in cls.properties)
        return f"""
  @FreezedUnionValue('{cls.name}')
  @JsonSerializable(explicitToJson: true, fieldRename: FieldRename.snake)
  const factory {self.name}.{dart_name(cls.name)}({{
    {properties}
  }}) = {cls.name};
"""

    def __str__(self):
        classes = "\n".join(self._format(c) for c in self.classes)
        return f"""
@Freezed(unionKey: '\\$type', unionValueCase: FreezedUnionCase.pascal)
class {self.name} with _${self.name} {{
{classes}

  factory {self.name}.fromJson(Map<String, dynamic> json) => _${self.name}FromJson(json);
}}
"""

class Py2FreezedEnum(ast.NodeVisitor):
    def __init__(self, node: EnumDef):
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
