import base64
import json
import traceback
from unimodel.backends.base import Serializer
from unimodel import types
from contextlib import contextmanager

class SerializationException(Exception):
    pass

class ReadValidationException(Exception):

    def __init__(self, message, read_context=None, tb=None, data=None):
        Exception.__init__(self, message)
        self.json_path = None
        if read_context:
            self.json_path = read_context.current_path()
        self.tb = tb
        self.data = data

    def __str__(self):
        msg = Exception.__str__(self)
        return "ReadValidationException: %s, json_path: %s" % (
            msg, self.json_path)

class Context(object):

    def __init__(self):
        self.context_stack = []

    @contextmanager
    def context(self, key, type_definition, value):
        self.context_stack.append((key, type_definition, value))
        yield
        self.context_stack.pop()

    def current_path(self):
        return ".".join([s[0] for s in self.context_stack])

class JSONSerializer(Serializer):

    def __init__(self,
            skip_unknown_fields=True,
            **kwargs):
        super(JSONSerializer, self).__init__(**kwargs)
        self.skip_unknown_fields = skip_unknown_fields
        self.context = Context()

    def serialize(self, obj):
        if self.validate_before_write:
            obj.validate()
        with self.context.context("", obj.__class__, obj):
            output = self.writeStruct(obj)
        return json.dumps(output)

    def writeStruct(self, obj):
        output = {}
        for name, value in obj.items():
            if value is not None:
                field_type = obj.get_field_definition(name).field_type
                with self.context.context(name, field_type, value):
                    output[name] = self.writeField(field_type, value)
        return output

    def writeField(self, field_type, value):
        if isinstance(field_type, types.NumberType):
            return self.writeValue(value)
        if isinstance(field_type, types.StringType):
            return self.writeString(field_type, value)
        if isinstance(field_type, types.Bool):
            return self.writeValue(value)
        if isinstance(field_type, types.Struct):
            return self.writeStruct(value)
        if isinstance(field_type, types.List):
            return self.writeList(field_type, value)
        if isinstance(field_type, types.Map):
            return self.writeMap(field_type, value)
        raise Exception("Don't know how to write type %s (value %s)" % (field, value))

    def writeValue(self, value):
        return value

    def writeString(self, field_type, value):
        if isinstance(field_type, types.Binary):
            return base64.b64encode(value)
        return value

    def writeList(self, field_type, collection):
        """ write lists and sets """
        output = []
        element_type = field_type.type_parameters[0]
        ix = 0
        for element in collection:
            with self.context.context(str(ix), element_type, element):
                output.append(self.writeField(element_type, element))
            ix += 1
        return output

    def writeMap(self, type_definition, collection):
        """ write maps """
        output = {}
        map_key_type = type_definition.type_parameters[0]
        map_value_type = type_definition.type_parameters[1]
        for key, value in collection.items():
            with self.context.context(key, map_key_type, key):
                encoded_key = self.writeField(map_key_type, key)
            with self.context.context(key, map_value_type, value):
                encoded_value = self.writeField(map_value_type, value)
            output[encoded_key] = encoded_value
        return output

    def deserialize(self, struct_class, stream):
        parsed_json = json.loads(stream)
        cls = self.get_implementation_class(struct_class)
        return self.readStruct(cls, parsed_json)

    def get_implementation_class(self, cls):
        return self.model_registry.lookup(cls)

    def validation_assert(self, condition, message=""):
        if not condition:
            raise ReadValidationException(message, self.read_context, data=self.read_context.current_json_object())

    def readStruct(self, struct_class, json_obj):
        self.validation_assert(type(json_obj) == dict, "Expecting JSON dictionary, got %s" % type(json_obj))
        target_obj = self.get_implementation_class(struct_class)()
        known_fields = []
        unknown_fields = []
        for key, raw_value in json_obj.iteritems():
            field = target_obj._fields_by_name.get(key, None)
            if field is None:
                unknown_fields.append(key)
                continue
            known_fields.append(key)
            with self.context.context(key, field.field_type, raw_value):
                parsed_value = self.readField(field.field_type, raw_value)
                target_obj._set_value_by_field_id(field.field_id, parsed_value)
        if not self.skip_unknown_fields:
            self.validation_assert(len(unknown_fields) ==  0,
                "unknown fields: %s" % ", ".join(unknown_fields))
        try:
            target_obj.validate()
        except Exception, e:
            tb = traceback.format_exc()
            raise ReadValidationException(str(e), self.read_context, tb=tb)
        return target_obj

    def readField(self, type_definition, value):
        if isinstance(type_definition, types.NumberType):
            return self.readValue(value)
        if isinstance(type_definition, types.StringType):
            return self.readString(type_definition, value)
        if isinstance(type_definition, types.Bool):
            return self.readValue(value)
        if isinstance(type_definition, types.Struct):
            return self.readStruct(type_definition.python_type, value)
        if isinstance(type_definition, types.Map):
            return self.readMap(type_definition, value)
        if isinstance(type_definition, types.List):
            return self.readList(type_definition, value)
        raise Exception("Cannot read type %s (value is %s)" % (str(type_definition), str(value)))

    def readValue(self, value):
        return value

    def readString(self, type_definition, value):
        if isinstance(type_definition, types.Binary):
            return base64.b64decode(value)
        return value

    def readMap(self, type_definition, collection):
        result = {}
        map_key_type = type_definition.type_parameters[0]
        map_type_definition = type_definition.type_parameters[1]
        for encoded_key, encoded_value in collection.items():
            with self.context.context(encoded_key, map_key_type, encoded_value):
                key = self.readField(map_key_type, encoded_key)
            with self.context.context(encoded_value, map_type_definition, encoded_value):
                value = self.readField(map_type_definition, encoded_value)
            result[key] = value
        return result

    def readList(self, type_definition, collection):
        result = []
        element_type = type_definition.type_parameters[0]
        ix = 0
        for encoded_element in collection:
            with self.context.context(str(ix), element_type, encoded_element):
                element = self.readField(element_type, encoded_element)
            result.append(element)
            ix += 1
        return result

