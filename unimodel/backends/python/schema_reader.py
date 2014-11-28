from unimodel.backends.base import SchemaReader
from unimodel import types
from unimodel.backends.json.type_data import get_field_name
from unimodel.util import get_backend_type, is_str
from unimodel import ast
from unimodel.model import ModelRegistry
import datetime

class PythonSchemaReader(SchemaReader):
    """ The input for this class is a set of Struct definitions.
    It converts these into a SchemaAST. """

    def __init__(self,
            root_struct_class,
            model_registry=None,
            struct_classes=None,  # additional structures to have in schema
            name=None):
        self.ast = ast.SchemaAST(
            common=ast.SchemaObject(name=name) if name else self.get_model_schema_object(root_struct_class),
            root_struct_name=root_struct_class.get_name())
        self.root_struct_class = root_struct_class
        self.model_registry = model_registry or ModelRegistry()
        self.struct_classes = struct_classes
        if self.struct_classes is None:
            self.struct_classes = set()

    @classmethod
    def get_model_schema_object(cls, model_cls):
        return ast.SchemaObject(
            name=model_cls.get_name(),
            namespace=model_cls.get_namespace(),
            metadata=cls.get_metadata(model_cls)) 

    @classmethod
    def get_metadata(cls, obj):
        if not hasattr(obj, 'metadata'):
            return None
        if obj.metadata is None:
            return None
        if not obj.metadata.backend_data:
            return None
        return ast.SchemaObjectMetadata(
            backend_data=obj.metadata.backend_data)

    def get_ast(self):
        # Collect struct dependencies of root struct (if any).
        struct_dependencies = self.get_dependencies_for_one_struct(
            self.root_struct_class)
        # Collect struct dependencies of manually added struct classes (if
        # any).
        self.get_dependencies_for_one_struct(
                    self.root_struct_class)
        [self.get_dependencies_for_one_struct(
            struct_class,
            struct_dependencies)
            for struct_class in self.struct_classes]
        self.ast.structs = [self.get_struct_definition(struct_class) for struct_class in struct_dependencies]
        self.ast.description = "generated on %s" % datetime.datetime.now()
        return self.ast

    def get_struct_definition(self, struct_class):
        """ returns (name, definition) pairs """
        # Note: maybe we should use the fully-qualified name of
        # the class to avoid name clashes
        struct_def = ast.StructDef(
                common=self.get_model_schema_object(struct_class),
                is_union=struct_class.is_union(),
                fields=[self.get_field_definition(f) for f in struct_class.get_field_definitions()])
        return struct_def

    @classmethod
    def get_default_value(cls, py_default_value):
        if py_default_value is None:
            return None
        if is_str(py_default_value):
            key = 'string'
        elif type(py_default_value) == int:
            key = 'integer'
        elif type(py_default_value) == float:
            key = 'double'
        else:
            raise Exception("value %s of type %s could not be turned into ast.LiteralValue" % (py_default_value, type(py_default_value)))
        return ast.Literal(literal_value=ast.LiteralValue(**{key: py_default_value}))

    def get_field_definition(self, field):
        field_def = ast.FieldDef(
                common=ast.SchemaObject(
                    name=field.field_name,
                    metadata=self.get_metadata(field)),
                default=self.get_default_value(field.default),
                required=field.required,
                field_id=field.field_id,
                field_type=self.get_type_definition(field.field_type))
        return field_def

    def get_type_definition(self, type_definition):
        """ returns field (name, definition) pair """
        if isinstance(type_definition, types.Enum):
            return self.define_enum_type(type_definition)
        if isinstance(type_definition, types.NumberTypeMarker):
            return self.define_primitive_type(type_definition)
        if isinstance(type_definition, types.StringTypeMarker):
            return self.define_primitive_type(type_definition)
        if isinstance(type_definition, types.Bool):
            return self.define_primitive_type(type_definition)
        if isinstance(type_definition, types.JSONData):
            return self.define_primitive_type(type_definition)
        if isinstance(type_definition, types.Struct):
            # Since all the structs were already collected, and are
            # defined in the definitions section, it's enough to refer
            # to the struct here.
            return self.reference_struct(type_definition)
        if isinstance(type_definition, types.Map):
            return self.define_parametric_type(type_definition)
        if isinstance(type_definition, types.List):
            return self.define_parametric_type(type_definition)
        if isinstance(type_definition, types.Tuple):
            return self.define_parametric_type(type_definition)
        raise Exception(
            "Cannot create schema for type %s" %
            str(type_definition))

    def get_typedef_base(self, type_definition):
        return ast.TypeDef(
                metadata=self.get_metadata(type_definition),
                type_class=ast.TypeClass())

    def define_primitive_type(self, type_definition):
        type_def = self.get_typedef_base(type_definition)
        type_def.type_class.primitive_type_id = type_definition.type_id
        return type_def

    def define_enum_type(self, type_definition):
        type_def = self.get_typedef_base(type_definition)
        type_def.type_class.enum = type_definition.keys_to_names
        return type_def

    def reference_struct(self, type_definition):
        type_def = self.get_typedef_base(type_definition)
        type_def.type_class.struct_name = type_definition.struct_class.get_name()
        return type_def

    def define_parametric_type(self, type_definition):
        type_def = self.get_typedef_base(type_definition)
        type_def.type_class.parametric_type = ast.ParametricType(
            type_id=type_definition.type_id,
            type_parameters=[self.get_type_definition(t) for t in type_definition.type_parameters])
        return type_def

    def get_dependencies_for_field_type(self, field_type, struct_dependencies):
        if isinstance(field_type, types.Struct):
            self.get_dependencies_for_one_struct(
                field_type.get_python_type(),
                struct_dependencies)
        if field_type.type_parameters:
            for type_parameter in field_type.type_parameters:
                self.get_dependencies_for_field_type(
                    type_parameter,
                    struct_dependencies)

    def get_dependencies_for_one_struct(self, cls, struct_dependencies=None):
        # It's possible that struct_class is actually an implementation class
        # In this case, we want the interface class
        if struct_dependencies is None:
            struct_dependencies = set()
        struct_class = self.model_registry.lookup_interface(cls)
        if struct_class in struct_dependencies:
            # For recursive types, quit if type has already been encountered
            return struct_dependencies
        # recursively traverse the fields of the struct, looking for new
        # dependencies
        struct_dependencies.add(struct_class)
        if struct_class.get_field_definitions():
            for field in struct_class.get_field_definitions():
                self.get_dependencies_for_field_type(
                    field.field_type,
                    struct_dependencies)
        return struct_dependencies
