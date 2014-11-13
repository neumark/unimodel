"""
JSONSchema to Unimodel model_schema (basically Unimodel AST) converter.
This class will create a ModelSchema object from a jsonschema definition.
ModelSchema object can then be used to compile python code or thift IDL.

There's actually a fundamental mismatch here between encoding-oriented
IDLs like thrift or Unimodel and validation languages like jsonschema.
The latter is perfectly happy saying "there may be additional fields here
which I know nothing about", while the former isn't.

So something like this has no Thrift equivalent:
    {
        "type": "object",
        "properties": {},
        "additionalProperties": true
    }

Unimodel has the JSONData field for these cases.

Other mismatches:

anyOf, allOf, oneOf
---
These keywords combine several types. They are represented in Unimodel
as a struct where each field has one of these values. The JSON metadata
for the struct indicates that it should be "unpacked", so allOf or oneOf
results in the fields of the referenced types being present in the JSON
directly (without the parent type).
anyOf is also represented as a struct (a union), but the json reader has
to try to match all the fields in the struct individually and move on
to the next candidate if the current field does not match. Only of the
fields should match the incoming data.

tuples
---
Thrift and Unimodel considers a list a collection of elements each
with one type. Jsonschema offer tuples:
{
    "type": "array",
    "items": [
        {
            "type": "boolean"
        },
        {
            "type": "integer"
        },
        {
            "type": "string"
        }
    ],
}

Unimodel also has tuples (a struct is generated with a field names
derived from the tuple element types). It is also possible to have
additional elements in the tuple with the "additionalItems" keyword:

    "additionalItems": {
        "type": "boolean",
        "default": false
    }

In Unimodel, this becomes an unboxed struct where the first field is the tuple,
and the second field is a list of elements of the type declared in the 
"additionalItems" definition.

Reserved field names
---
Field names which are reserved words, or simply invalid fieldnames in python
(eg: $ref, /path/, public) are renamed to something that python can deal with,
but the field's metadata contains the original field name so read-writing
JSON still works.

Root struct
---
Jsonschema describes a DAG, Unimodel describes a set of structs. In order
to reproduce the json structure, a Root struct is created (typically named
Root unless that collides with something).
"""

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
REF_TEMPLATE = "%(base_uri)s/definitions/%(name)s"  # base_uri ends in '#'
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
            real_base_uri = base_uri
            if real_base_uri.endswith('#'):
                real_base_uri = base_uri[:-1]
            return "%s%s" % (real_base_uri, ref)
        return ref

    @classmethod
    def replace_relative_references(cls, base_uri, json_value):
        # TODO
        for _path, value in walk_json(json_value):
            if isinstance(value, dict) and Reference.REF_ATTR in value:
                value[Reference.REF_ATTR] = cls.make_absolute(
                    base_uri, value[Reference.REF_ATTR])
        return json_value

    def resolve(self, refresolver):
        with refresolver.resolving(self.ref) as res:
            if self.is_ref(res):
                ref = Reference(res)
                return ref.resolve(refresolver)
            # It's not enough to call replace_relative_references when
            # the schema is loaded, because resolve() may be pulling in
            # fragments from other JSON documents, thus it may contain
            # relative references.
            return self.replace_relative_references(refresolver.base_uri, res)


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
    #   type        format       unimodel type
        ('integer', None):       'int64',
        ('integer', 'int32'):    'int32',
        ('integer', 'int64'):    'int64',
        ('number', None):        'double',
        ('number', 'float'):     'double',
        ('number', 'double'):    'double',
        ('string', None):        'utf8',
        ('string', 'byte'):      'binary',
        ('string', 'date'):      'utf8', # TODO: make this a date UTF8 subclass
        ('string', 'date-time'): 'utf8', # TODO: make this a date-time UTF8 subclass
        ('string', 'uri'):       'utf8', # TODO: make this a URI UTF8 subclass
        ('string', 'email'):     'utf8', # TODO: make this an email UTF8 subclass
        ('string', 'regex'):     'utf8', # TODO: make this an email UTF8 subclass
        ('boolean', None):       'bool',
        ('array', None):         'list',
        # 'object' can mean map or struct, but structs are
        # listed directly under 'definitions', everywhere else,
        # they are $ref'd.
        ('object', None):        'map'
        # Enums have the 'string' type in jsonschema. An additional
        # 'enum' property identifies them as such.
    }

    def __init__(self, name, schema):
        self.name = name
        self.base_uri = schema.get('id', '')
        # replace all relative references with absolute refs to avoid
        # clashes in self.definitions
        self.schema = Reference.replace_relative_references(self.base_uri, schema)
        # maps full jsonschema fragment path to internal structure,
        # for example a StructDef or a TypeDef.
        self.definitions = {}
        self.refresolver = RefResolver.from_schema(schema)

    def is_defined(self, name):
        return name in self.definitions

    def generate_enum(self, definition):
        enum = definition['enum']
        return TypeDef(type_class=TypeClass(
            enum=dict(zip(
                xrange(0, len(enum)),
                enum))))

    def generate_type_def(self, definition):
        """ Generates a TypeDef object based on a 
            JSONSchema definition. """
        # we should always be getting a dict
        assert isinstance(definition, dict)
        if 'enum' in definition:
            return self.generate_enum(definition)
        if 'type' not in definition:
            raise Exception(
                "Cannot process type definition %s" %
                json.dumps(definition))
        json_type = definition['type']
        json_format = definition.get('format', None)
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
                                definition.get(
                                    'items',
                                    DEFAULT_ARRAY_ITEMS))])))
        # primitive type
        return TypeDef(type_class=TypeClass(primitive_type_id=type_id))

    def generate_map(self, name, definition):
        # There are 4 different thing we could return:
        # 1: A Map. This is what we return if
        #    additionalProperties or patternProperties
        #    gives a type, and there is no 'properties' field
        # 2: A Struct (unbox) composed of a Map and a Struct.
        #    additionalProperties or patternProperties
        #    gives a type, and there is a 'properties' field.


        return TypeDef(
            type_class=TypeClass(
                parametric_type=ParametricType(
                    type_id=type_id_enum.name_to_key("map"),
                    type_parameters=[
                        self.generate_type_def({"type": "string"}),
                        self.generate_type_def({"type": "string"})])))

    def get_field_type(self, definition):
        field_type_obj = self.process_definition(None, definition)
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
            field_type=self.get_field_type(definition),
            common=SchemaObject(name=self.relative_name(name)),
            required=required)
        return field_def

    def generate_struct(self, name, definition, struct_def):
        struct_def.common = SchemaObject(name=self.relative_name(name))
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

    @classmethod
    def ensure_nonexisting(cls, original_name, existing_names=None):
        existing_names = [] if existing_names is None else existing_names
        name = original_name
        counter = 0
        while name in existing_names or name in RESERVED_NAMES:
            name = "%s%s" % (original_name, counter)
            counter += 1
        existing_names.append(name)
        return name

    @classmethod
    def relative_name(cls, full_name):
        """ turns #/definitions/X into X """
        if full_name is None:
            import pdb;pdb.set_trace()
        return full_name.split("/")[-1]

    def field_name_from_type(self, field_type, existing_names=None):
        # primitive types
        if field_type.type_class.primitive_type_id is not None:
            return self.ensure_nonexisting(type_id_enum.key_to_name(
                field_type.type_class.primitive_type_id), existing_names)
        if field_type.type_class.enum is not None:
            return self.ensure_nonexisting('enum', existing_names)
        if field_type.type_class.struct_name is not None:
            return self.ensure_nonexisting(field_type.type_class.struct_name, existing_names)
        # parametric types
        name_parts = [type_id_enum.key_to_name(
            field_type.type_class.parametric_type.type_id)]
        for t in field_type.type_class.parametric_type.type_parameters:
            name_parts.append(self.field_name_from_type(t))
        return self.ensure_nonexisting("_".join(name_parts), existing_names)

    def get_composite_struct_name(self, composite_struct):
        # TODO: we may have to populate 'existing_names' with short names
        # of currently defined structs.
        return  self.ensure_nonexisting("_".join(["struct"] +
            [self.field_name_from_type(f.field_type) for f in composite_struct.fields]), [])


    def generate_composite_struct(self, definition, composition_type):
        """ generates StructDefs for anyOf, allOf and oneOf """
        # TODO: differentiate based on composition_type:
        # oneOf: type union (formerly called unboxed union)
        # allOf, anyOf: unboxed struct
        field_types_all = [self.get_field_type(d)
                       for d in definition[composition_type]]
        # default value definitions like {'default': 0}
        # result in extra Literal types. get_field_type
        # returns None for them. We can ignore them
        # as long as we don't claim to do jsonschema validation.
        field_types = [f for f in field_types_all if f is not None]
        # if there is only a single field type, there is no need
        # to create a composite struct
        if len(field_types) == 1:
            return field_types[0]
        # generate a name for each field based on its type
        composite_struct = StructDef(fields=[])
        existing_field_names = []
        for field_type in field_types:
            field_name = self.field_name_from_type(
                field_type,
                existing_field_names)
            composite_struct.fields.append(
                FieldDef(
                    common=SchemaObject(name=field_name),
                    required=False,
                    field_type=field_type))
        # name the newly created composite field type
        composite_struct.common=SchemaObject(name=self.relative_name(
            self.get_composite_struct_name(composite_struct)))
        return composite_struct

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
                        name=self.relative_name(name)),
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
        # Maps and Structs are pretty similar in jsonschema (they're both 'object'
        # values in JSON).
        # Both definitions with additionalProperties and patternProperties
        # could be either a map or the unboxed union of a struct and a map
        if 'patternProperties' in definition or 'additionalProperties' in definition:
            return self.save_type_def(
                name,
                self.generate_map(
                    name,
                    definition))
        # composite structs / unions
        for composition_type in ['allOf', 'oneOf', 'anyOf']:
            if composition_type in definition:
                composite_struct_def = self.generate_composite_struct(
                    definition,
                    composition_type)
                # generate_composite_struct will give a regular TypeDef
                # if only a single field is defined in the composite
                # struct. So despite the name, composite_struct_def
                # isn't always a StructDef.
                if isinstance(composite_struct_def, StructDef):
                    self.save_type_def(
                        self.full_name(composite_struct_def.common.name),
                        composite_struct_def)
                return composite_struct_def
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
            struct_name = self.relative_name(name)
            self.definitions[name] = StructDef()
            return self.generate_struct(
                struct_name,
                definition,
                self.definitions[name])
        # all other types, which can be handled in a fairly uniform
        # matter: enums, lists, sets, primitive types
        return self.save_type_def(name, self.generate_type_def(definition))

    def full_name(self, name):
        return REF_TEMPLATE % {'base_uri': self.base_uri, 'name': name}

    def generate_model_schema(self):
        # generate models for structs in definitions
        model_schema = ModelSchema(
            common=SchemaObject(name=self.name),
            description=self.schema.get('description', ''))
        # process schema definitions
        for name, definition in self.schema.get('definitions', {}).items():
            self.process_definition(self.full_name(name), definition)
        # process schema root object
        root_name = self.ensure_nonexisting(self.full_name("Root"), self.schema.get('definitions', {}).keys())
        self.process_definition(root_name, self.schema)
        model_schema.root_struct_name = root_name
        model_schema.structs = [
            s for s in self.definitions.values() if isinstance(
                s,
                StructDef)]
        return model_schema
