import json
import jsonschema
from unimodel.schema import *
from unimodel import types
from jsonschema.validators import RefResolver

# Thanks to Randy Abernethy for the list of reserved keywords
RESERVED_NAMES = """BEGIN END __CLASS__ __DIR__ __FILE__ __FUNCTION__ __LINE__
__METHOD__ __NAMESPACE__ abstract alias and args as assert begin break case
catch class clone continue declare def default del delete do dynamic elif else
elseif elsif end enddeclare endfor endforeach endif endswitch endwhile ensure
except exec finally float for foreach function global goto if implements import
in inline instanceof interface is lambda module native new next nil not or pass
public print private protected public raise redo rescue retry register return
self sizeof static super switch synchronized then this throw transient try
undef union unless unsigned until use var virtual volatile when while with xor
yield""".split()
REF_TEMPLATE = "#/definitions/%s"
DEFAULT_ARRAY_ITEMS = {'type': 'string'}


class Reference(object):
    REF_ATTR = '$ref'

    def __init__(self, obj):
        self.ref = obj[Reference.REF_ATTR]

    @classmethod
    def is_ref(cls, obj):
        return isinstance(obj, dict) and Reference.REF_ATTR in obj

    def resolve(self, refresolver):
        with refresolver.resolving(self.ref) as res:
            if self.is_ref(res):
                return Reference(res).resolve(refresolver)
            return res


def relative_name(full_name):
    """ turns #/definitions/X into X """
    return full_name.split("/")[-1]


class JSONSchemaModelGenerator(object):
    # From:
    # github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
    # Name     type    format    Comments
    # --       --      --        --
    # integer  integer int32     signed 32 bits
    # long     integer int64     signed 64 bits
    # float    number  float
    # double   number  double
    # string   string
    # byte     string  byte
    # boolean  boolean
    # date     string  date      As defined by full-date - RFC3339
    # dateTime string  date-time As defined by date-time - RFC3339

    # Maps (type, format) -> (unimodel type name, type constructor class)
    # based on the table above. Unimodel names take from
    # unimodel.schema.type_id_enum
    JSON_TO_UNIMODEL_TYPE = {
        ('integer', None): 'int64',
        ('integer', 'int32'): 'int32',
        ('integer', 'int64'): 'int64',
        ('number', None): 'double',
        ('number', 'float'): 'double',
        ('number', 'double'): 'double',
        ('string', None): 'utf8',
        ('string', 'byte'): 'binary',
        ('string', 'date'): 'utf8',  # TODO: make this a date UTF8 subclass
        # TODO: make this a date-time UTF8 subclass
        ('string', 'date-time'): 'utf8',
        ('string', 'uri'): 'utf8',  # TODO: make this a URI UTF8 subclass
        ('string', 'email'): 'utf8',  # TODO: make this an email UTF8 subclass
        ('string', 'regex'): 'utf8',  # TODO: make this an email UTF8 subclass
        ('boolean', None): 'bool',
        ('array', None): 'list',
        # 'object' can mean map or struct, but structs are
        # listed directly under 'definitions', everywhere else,
        # they are $ref'd.
        ('object', None): 'map'
        # Enums have the 'string' type in jsonschema. An additional
        # 'enum' property identifies them as such.
    }

    def __init__(self, name, schema):
        self.name = name
        self.schema = schema
        self.definitions = {}
        self.refresolver = RefResolver.from_schema(schema)

    def is_defined(self, name):
        return name in self.definitions

    def generate_type_def(self, definition):
        # TODO: fix anyOf, allOf and not!
        if 'type' not in definition:
            raise Exception(
                "Cannot process type definition %s" %
                json.dumps(definition))
        json_type = definition['type']
        json_format = definition.get('format', None)
        enum = definition.get('enum', None)
        if enum:
            return TypeDef(type_class=TypeClass(
                enum=dict(zip(
                    xrange(0, len(enum)),
                    enum))))
        type_name = self.JSON_TO_UNIMODEL_TYPE[(json_type, json_format)]
        type_id = type_id_enum.name_to_key(type_name)
        # note: type_name will never be "struct" because
        # struct objects are already defined by this point in the code.
        assert not type_name == "struct"
        # note: maps are generated by generate_map
        assert not type_name == "map"
        if type_name == "list":
            # eg: {u'uniqueItems': True, u'items': {u'$ref':
            # u'#/definitions/mimeType'}, u'type': u'array'}
            if definition.get('uniqueItems', False):
                type_id = type_id_enum.name_to_key("set")
            return TypeDef(
                type_class=TypeClass(
                    parametric_type=ParametricType(
                        type_id=type_id,
                        type_parameters=[
                            self.get_field_type(
                                None,
                                definition.get(
                                    'items',
                                    DEFAULT_ARRAY_ITEMS))])))
        # primitive type
        return TypeDef(type_class=TypeClass(primitive_type_id=type_id))

    def generate_map(self, name, definition):
        # TODO: patternProperties places constraints on the keys of the map
        # TODO: right now, we assume it's a Map(UTF8, UTF8)
        return TypeDef(
            type_class=TypeClass(
                parametric_type=ParametricType(
                    type_id=type_id_enum.name_to_key("map"),
                    type_parameters=[
                        self.generate_type_def({"type": "string"}),
                        self.generate_type_def({"type": "string"})])))

    def get_field_type(self, name, definition):
        field_type_obj = self.process_definition(name, definition)
        # if field_type_obj is a StructDef, we need to convert it
        # to a TypeDef object.
        if isinstance(field_type_obj, StructDef):
            # for StructDefs, we need to create the proper TypeDef object.
            field_type_obj = TypeDef(
                type_class=TypeClass(
                    struct_name=field_type_obj.common.name))
        assert isinstance(field_type_obj, TypeDef)
        return field_type_obj

    def generate_field(self, name, definition, required=False):
        field_def = FieldDef(
            field_type=self.get_field_type(name, definition),
            common=SchemaObject(name=relative_name(name)),
            required=required)
        return field_def

    def generate_struct(self, name, definition, struct_def):
        struct_def.common = SchemaObject(name=relative_name(name))
        struct_def.fields = []
        required_fields = definition.get('required', [])
        for field_name, field_definition in definition.get(
                'properties', {}).items():
            # TODO: fix handling of default fields
            if field_name == 'default':
                continue  # ignoring defaults for now
            field_def = self.generate_field(
                field_name,
                field_definition,
                field_name in required_fields)
            struct_def.fields.append(field_def)
        return struct_def

    def generate_composite_struct(self, name, definition):
        """ generates StructDefs for anyOf, allOf and oneOf """
        # TODO TypeParams!!!
        return StructDef(
            common=SchemaObject(name=relative_name(name)),
            fields=[])

    def generate_tuple(self, name, definition):
        """ generates StructDefs for anyOf, allOf and oneOf """
        # TODO TypeParams!!!
        return TypeDef(type_class=TypeClass(parametric_type=ParametricType(
            type_id=type_id_enum.name_to_key("tuple"),
            type_parameters=[])))

    def save_type_def(self, name, value):
        if name is not None:
            self.definitions[name] = value
        return value

    def process_definition(self, name, definition):
        """ reads a json definition of some sort, and creates
            the associated object from unimodel.struct. """
        # check if the value is already cached
        if self.is_defined(name):
            return self.definitions[name]
        # this is sort of a hack for constants
        if definition == {}:
            return self.save_type_def(name, Literal())  # TODO
        # recursively process references
        if Reference.is_ref(definition):
            ref = Reference(definition)
            if self.is_defined(ref.ref):
                return self.definitions[ref.ref]
            else:
                resolved_definition = ref.resolve(self.refresolver)
                result = self.process_definition(ref.ref, resolved_definition)
                return self.save_type_def(ref.ref, result)
        # maps
        if 'patternProperties' in definition:
            return self.save_type_def(
                name,
                self.generate_map(
                    name,
                    definition))
        # composite structs / unions
        for union_type in ['allOf', 'oneOf', 'anyOf']:
            if union_type in definition:
                return self.save_type_def(
                    name,
                    self.generate_composite_struct(
                        name,
                        definition))
        # tuples
        if 'additionalItems' in definition:
            return self.save_type_def(
                name,
                self.generate_tuple(
                    name,
                    definition))
        # unhandled case (we didn't think of something)
        if 'type' not in definition:
            raise Exception(
                "Unexpected jsonschema element in field %s: %s" %
                (name, json.dumps(definition)))
        # structs
        if definition['type'] == 'object':
            # generate_struct save the type definition itself to handle
            # recursive types
            self.definitions[name] = StructDef()
            return self.generate_struct(
                name,
                definition,
                self.definitions[name])
        # all other types, which can be handled in a fairly uniform
        # matter: enums, lists, sets, primitive types
        return self.save_type_def(name, self.generate_type_def(definition))

    def generate_model_schema(self):
        # generate models for structs in definitions
        model_schema = ModelSchema(
            common=SchemaObject(name=self.name),
            description=self.schema.get('description', ''))
        for name, definition in self.schema.get('definitions', {}).items():
            full_name = REF_TEMPLATE % name
            self.process_definition(full_name, definition)
        model_schema.structs = [
            s for s in self.definitions.values() if isinstance(
                s,
                StructDef)]
        return model_schema
