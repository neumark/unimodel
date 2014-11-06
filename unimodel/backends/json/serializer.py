import base64
import json
import traceback
from unimodel.backends.base import Serializer
from unimodel import types
from contextlib import contextmanager
from unimodel.validation import ValidationException, ValueTypeException

class SerializationException(Exception):
    pass

class JSONValidationException(ValidationException):

    def __init__(self, message, context=None, exc=None):
        Exception.__init__(self, message)
        self.context = context.clone()
        self.exc = None

    def __str__(self):
        msg = Exception.__str__(self)
        return "ReadValidationException: %s, context: %s exc: %s" % (
            msg, str(self.context), str(self.exc))

class Context(object):

    def __init__(self):
        self.context_stack = []

    def __str__(self):
        if self.context_stack:
            return "JSON path: '%s' value: '%s'" % (self.current_path(), self.context_stack[-1][2])

    @contextmanager
    def context(self, key, type_definition, value):
        self.context_stack.append((key, type_definition, value))
        yield
        self.context_stack.pop()

    def current_path(self):
        def fmt(s):
            if type(s) == int:
                return "[%s]" % s
            if len(str(s)) > 0:
                return ".%s" % s
            return str(s)
        return ("".join([fmt(s[0]) for s in self.context_stack if s]))[1:]

    def current_value(self):
        if self.context_stack:
            return self.context_stack[-1][2]
        return None

    def clone(self):
        new_context = Context()
        new_context.context_stack = list(self.context_stack)
        return new_context

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
            return json.dumps(self.writeStruct(obj))

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
            with self.context.context(ix, element_type, element):
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
        with self.context.context("", cls, parsed_json):
            return self.readStruct(cls, parsed_json)

    def get_implementation_class(self, cls):
        return self.model_registry.lookup(cls)

    def assert_type(self, value_type, value):
        if type(value) != value_type:
            raise JSONValidationException(
                "Expecting %s, got %s" % (value_type, value),
                self.context)

    def assert_valid(self, type_definition, value):
        try:
            type_definition.validate(value)
        except ValidationException, e:
            raise JSONValidationException("Error reading '%s' as %s" % (value, type_definition.__class__.__name__), self.context, e)

    def readStruct(self, struct_class, json_obj):
        self.assert_type(dict, json_obj)
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
        if not self.skip_unknown_fields and len(unknown_fields) > 0:
            raise JSONValidationException(
                "unknown fields: %s" % ", ".join(unknown_fields),
                self.context)
        try:
            target_obj.validate()
        except Exception, e:
            raise ReadValidationException("Error validating %s" % struct_class.__name__, self.context, e)
        return target_obj

    def readField(self, type_definition, value):
        if isinstance(type_definition, types.NumberType):
            return self.readValue(type_definition, value)
        if isinstance(type_definition, types.StringType):
            return self.readString(type_definition, value)
        if isinstance(type_definition, types.Bool):
            return self.readValue(type_definition, value)
        if isinstance(type_definition, types.Struct):
            return self.readStruct(type_definition.python_type, value)
        if isinstance(type_definition, types.Map):
            return self.readMap(type_definition, value)
        if isinstance(type_definition, types.List):
            return self.readList(type_definition, value)
        raise Exception("Cannot read type %s (value is %s)" % (str(type_definition), str(value)))

    def readValue(self, type_definition, value):
        self.assert_valid(type_definition, value)
        return value

    def readString(self, type_definition, value):
        self.assert_valid(type_definition, value)
        if isinstance(type_definition, types.Binary):
            return base64.b64decode(value)
        return value

    def readMap(self, type_definition, collection):
        self.assert_type(dict, collection)
        result = {}
        map_key_type = type_definition.type_parameters[0]
        map_type_definition = type_definition.type_parameters[1]
        for encoded_key, encoded_value in collection.items():
            with self.context.context(encoded_key, map_key_type, encoded_value):
                key = self.readField(map_key_type, encoded_key)
            with self.context.context(encoded_value, map_type_definition, encoded_value):
                value = self.readField(map_type_definition, encoded_value)
            result[key] = value
        type_definition.validate(result)
        return result

    def readList(self, type_definition, collection):
        self.assert_type(list, collection)
        result = []
        element_type = type_definition.type_parameters[0]
        ix = 0
        for encoded_element in collection:
            with self.context.context(ix, element_type, encoded_element):
                element = self.readField(element_type, encoded_element)
            result.append(element)
            ix += 1
        type_definition.validate(result)
        return result