import unittest
from py2freezed import Py2Freezed

class TestPy2Freezed(unittest.TestCase):
    def test_enum(self):
        py2freezed = Py2Freezed()
        py2freezed.parse("""
class TestEnum(enum.Enum):
    FOO = enum.auto()
    BAR = enum.auto()
    BAZ = enum.auto()
""")
        self.assertEqual(py2freezed.to_freezed(), """
enum TestEnum {
  FOO,
  BAR,
  BAZ,
}
""")

    def test_basic(self):
        py2freezed = Py2Freezed()
        py2freezed.parse("""
class TestClass:
    boolean: bool
    integer: int
    string: str
    foo: Foo
""")
        self.assertEqual(py2freezed.to_freezed(), """
@freezed
class TestClass with _$TestClass {
  @JsonSerializable(explicitToJson: true, fieldRename: FieldRename.snake)
  const factory TestClass({
    required bool boolean,
    required int integer,
    required String string,
    required Foo foo,
  }) = _TestClass;

  factory TestClass.fromJson(Map<String, dynamic> json) => _$TestClassFromJson(json);
}
""")

    def test_optional(self):
        py2freezed = Py2Freezed()
        py2freezed.parse("""
class TestClass:
    boolean: Optional[bool]
    integer: Optional[int]
    string: Optional[str]
    foo: Optional[Foo]
""")
        self.assertEqual(py2freezed.to_freezed(), """
@freezed
class TestClass with _$TestClass {
  @JsonSerializable(explicitToJson: true, fieldRename: FieldRename.snake)
  const factory TestClass({
    required bool? boolean,
    required int? integer,
    required String? string,
    required Foo? foo,
  }) = _TestClass;

  factory TestClass.fromJson(Map<String, dynamic> json) => _$TestClassFromJson(json);
}
""")

    def test_default(self):
        py2freezed = Py2Freezed()
        py2freezed.parse("""
class TestClass:
    boolean: bool = False
    integer: int = 1
    string: str = "foo"
""")
        self.assertEqual(py2freezed.to_freezed(), """
@freezed
class TestClass with _$TestClass {
  @JsonSerializable(explicitToJson: true, fieldRename: FieldRename.snake)
  const factory TestClass({
    @Default(false) bool boolean,
    @Default(1) int integer,
    @Default('foo') String string,
  }) = _TestClass;

  factory TestClass.fromJson(Map<String, dynamic> json) => _$TestClassFromJson(json);
}
""")

    def test_attr(self):
        py2freezed = Py2Freezed()
        py2freezed.parse("""
@attr.s(auto_attribs=True)
class TestClass:
    foo: int = attr.ib(default=123, repr=False)
    bar: str = attr.ib(default='foo', repr=False)
    baz: List[str] = attr.Factory(list)
    qux: List[str] = attr.ib(default=attr.Factory(list))
""")
        self.assertEqual(py2freezed.to_freezed(), """
@freezed
class TestClass with _$TestClass {
  @JsonSerializable(explicitToJson: true, fieldRename: FieldRename.snake)
  const factory TestClass({
    @Default(123) int foo,
    @Default('foo') String bar,
    @Default([]) List<String> baz,
    @Default([]) List<String> qux,
  }) = _TestClass;

  factory TestClass.fromJson(Map<String, dynamic> json) => _$TestClassFromJson(json);
}
""")

    def test_camel(self):
        py2freezed = Py2Freezed()
        py2freezed.parse("""
class TestClass:
    foo_bar: bool = False
""")
        self.assertEqual(py2freezed.to_freezed(), """
@freezed
class TestClass with _$TestClass {
  @JsonSerializable(explicitToJson: true, fieldRename: FieldRename.snake)
  const factory TestClass({
    @Default(false) @JsonKey(name: 'foo_bar') bool fooBar,
  }) = _TestClass;

  factory TestClass.fromJson(Map<String, dynamic> json) => _$TestClassFromJson(json);
}
""")

if __name__ == '__main__':
    unittest.main()
