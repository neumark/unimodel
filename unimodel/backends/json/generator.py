import json
import jsonschema
from unimodel.schema import *
from unimodel import types
from jsonschema.validators import RefResolver
from unimodel.validation import is_str

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
REF_TEMPLATE = "%(base_uri)s#/definitions/%(name)s"
DEFAULT_ARRAY_ITEMS = {'type': 'string'}

def walk_json(json_obj, key=""):
    def append_key(prefix, postfix):
        return "%s.%s" % (prefix, postfix)
    if isinstance(json_obj, dict):
        for k, v in json_obj.items():
            for pair in walk_json(v, append_key(key, str(k))):
                yield pair
    elif isinstance(json_obj, list):
        for i in xrange(0, len(json_obj)):
            for pair in walk_json(json_obj[i], append_key(key, str(i))):
                yield pair
    yield (key, json_obj)

class Reference(object):
    REF_ATTR = '$ref'

    def __init__(self, obj):
        self.ref = obj[Reference.REF_ATTR]

    @classmethod
    def is_ref(cls, obj):
        return isinstance(obj, dict) and Reference.REF_ATTR in obj

    @classmethod
    def make_absolute(cls, base_uri, ref):
        if is_str(ref) and ref.startswith('#'):
            return "%s%s" % (base_uri, ref)
        return ref

    def replace_relative_references(self, base_uri, json_value):
        # TODO
        for _path, value in walk_json(json_value):
            if isinstance(value, dict) and Reference.REF_ATTR in value:
                value[Reference.REF_ATTR] = self.make_absolute(
                    base_uri, value[Reference.REF_ATTR])
        return json_value

    def resolve(self, refresolver):
        with refresolver.resolving(self.ref) as res:
            if self.is_ref(res):
                # note that for relative references the resolver's
                # resolution scope should be prepended, this way
                # when one jsonschema doc refers to another
                # which then refers to itself, we keep up and
                # 'switch docs'.
                ref = Reference(res)
                return ref.resolve(refresolver)
            return self.replace_relative_references(refresolver.base_uri, res)


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
        self.base_uri = schema.get('id', '')
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
        if isinstance(field_type_obj, Literal):
            # default values result in Literals being returned by
            # process_definition. In such cases we just return None
            return None
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
            field_def = self.generate_field(
                field_name,
                field_definition,
                field_name in required_fields)
            struct_def.fields.append(field_def)
        return struct_def

    def field_name_from_type(self, field_type, existing_names=None):
        existing_names = [] if existing_names is None else existing_names
        def ensure_nonexisting(original_name):
            name = original_name
            counter = 0
            while name in existing_names:
                name = "%s%s" % (original_name, counter)
                counter += 1
            existing_names.append(name)
            return name
        # primitive types
        if field_type.type_class.primitive_type_id is not None:
            return ensure_nonexisting(type_id_enum.key_to_name(
                field_type.type_class.primitive_type_id))
        if field_type.type_class.enum is not None:
            return ensure_nonexisting('enum')
        if field_type.type_class.struct_name is not None:
            return ensure_nonexisting(field_type.type_class.struct_name)
        # parametric types
        name_parts = [type_id_enum.key_to_name(
            field_type.type_class.parametric_type.type_id)]
        for t in field_type.type_class.parametric_type.type_parameters:
            name_parts.append(self.field_name_from_type(t))
        return ensure_nonexisting("_".join(name_parts))

    def generate_composite_struct(self, name, definition, composition_type):
        """ generates StructDefs for anyOf, allOf and oneOf """
        # TODO: differentiate based on composition_type:
        # oneOf: type union (formerly called unboxed union)
        # allOf, anyOf: unboxed struct
        field_types = [self.get_field_type(None, d)
                       for d in definition[composition_type]]
        field_list = []
        existing_field_names = []
        for field_type in field_types:
            # default value definitions like {'default': 0}
            # result in extra Literal types. get_field_type
            # returns None for them. We can ignore them
            # as long as we don't claim to do jsonschema validation.
            if field_type is None:
                continue
            field_name = self.field_name_from_type(
                field_type,
                existing_field_names)
            field_list.append(
                FieldDef(
                    common=SchemaObject(name=field_name),
                    required=False,
                    field_type=field_type))
        # if field_list only has a single field, we don't need
        # a composite struct.
        if len(field_list) == 1:
            return field_list[0].field_type
        return StructDef(
            common=SchemaObject(name=relative_name(name)),
            fields=field_list)

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
        # default values:
        if definition.keys() == ['default']:
            # TODO: make the 'real' kind of literal
            return Literal(literal_value=LiteralValue(integer=0))
        # empty objects
        if definition == {}:
            return self.save_type_def(
                name,
                StructDef(
                    common=SchemaObject(
                        name=relative_name(name)),
                    fields=[]))
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
        for composition_type in ['allOf', 'oneOf', 'anyOf']:
            if composition_type in definition:
                return self.save_type_def(
                    name,
                    self.generate_composite_struct(
                        name,
                        definition,
                        composition_type))
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

    def make_unique_name(self, name):
        while name in self.definitions:
            name += "_"
        return name                

    def generate_model_schema(self):
        # generate models for structs in definitions
        model_schema = ModelSchema(
            common=SchemaObject(name=self.name),
            description=self.schema.get('description', ''))
        # process schema definitions
        for name, definition in self.schema.get('definitions', {}).items():
            full_name = REF_TEMPLATE % {'base_uri': self.base_uri, 'name': name}
            self.process_definition(full_name, definition)
        # process schema root object
        root_name = self.make_unique_name("Root")
        self.process_definition(root_name, self.schema)
        model_schema.root_struct_name = root_name
        model_schema.structs = [
            s for s in self.definitions.values() if isinstance(
                s,
                StructDef)]
        return model_schema
