import base64
import json
import traceback
from unimodel.backends.base import Serializer
from unimodel import types
from contextlib import contextmanager
from unimodel.validation import ValidationException, ValueTypeException
from unimodel.backends.json.type_data import (get_field_name,
                                              get_field_by_name,
                                              is_unboxed_struct_field)


class SerializationException(Exception):
    pass


class JSONValidationException(ValidationException):

    def __init__(self, message, context=None, exc=None):
        Exception.__init__(self, message)
        self.context = context.clone()
        self.exc = None

    def __str__(self):
        msg = Exception.__str__(self)
        return "%s, context: %s exc: %s" % (
            msg, str(self.context), str(self.exc))


class Context(object):

    def __init__(self):
        self.context_stack = []

    def __str__(self):
        if self.context_stack:
            return "JSON path: '%s' value: '%s'" % (
                self.current_path(), self.context_stack[-1][2])

    @contextmanager
    def context(self, key, type_definition, value):
        self.context_stack.append((key, type_definition, value))
        yield
        self.context_stack.pop()

    def current_path(self):
        def fmt(s):
            if isinstance(s, int):
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

    def writeStruct(self, obj, output=None):
        output = {} if output is None else output
        unboxed_struct_fields = self.get_unboxed_struct_fields(
            obj.get_field_definitions())
        for name, value in obj.items():
            if value is not None:
                field = obj.get_field_definition(name)
                with self.context.context(name, field.field_type, value):
                    if field in unboxed_struct_fields:
                        self.writeStruct(value, output)
                    else:
                        output[
                            get_field_name(field)] = self.writeField(
                            field.field_type,
                            value)
        return output

    def writeField(self, field_type, value):
        if isinstance(field_type, types.Enum):
            return self.writeEnum(field_type, value)
        if isinstance(field_type, types.NumberTypeMarker):
            return self.writeValue(value)
        if isinstance(field_type, types.StringTypeMarker):
            return self.writeString(field_type, value)
        if isinstance(field_type, types.Bool):
            return self.writeValue(value)
        if isinstance(field_type, types.Struct):
            return self.writeStruct(value)
        if isinstance(field_type, types.List):
            return self.writeList(field_type, value)
        if isinstance(field_type, types.Map):
            return self.writeMap(field_type, value)
        if isinstance(field_type, types.JSONData):
            return value
        if isinstance(field_type, types.Tuple):
            return self.writeTuple(field_type, value)
        raise Exception(
            "Don't know how to write type %s (value %s)" %
            (field_type, value))

    def writeValue(self, value):
        return value

    def writeEnum(self, field_type, value):
        return field_type.key_to_name(value)

    def writeString(self, field_type, value):
        if isinstance(field_type, types.Binary):
            return base64.b64encode(value)
        return value

    def writeTuple(self, field_type, value):
        output = []
        ix = 0
        for element in value:
            element_type = field_type.type_parameters[ix]
            with self.context.context(ix, element_type, element):
                output.append(self.writeField(element_type, element))
            ix += 1
        return output

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
        self.assert_map_key_type(map_key_type)
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
        if not isinstance(value, value_type):
            raise JSONValidationException(
                "Expecting %s, got %s" % (value_type, value),
                self.context)

    def assert_valid(self, type_definition, value):
        try:
            type_definition.validate(value)
        except ValidationException as e:
            raise JSONValidationException(
                "Error reading '%s' as %s" %
                (value, type_definition.__class__.__name__), self.context, e)

    def assert_map_key_type(self, map_key_type):
        if isinstance(map_key_type, types.Int):
            return
        if isinstance(map_key_type, types.StringTypeMarker):
            return
        raise SerializationException(
            "JSON serializer cannot use type '%s' map keys" %
            str(map_key_type))

    def get_unboxed_struct_fields(self, field_definitions):
        unboxed_struct_fields = []
        for field in field_definitions:
            if is_unboxed_struct_field(field):
                unboxed_struct_fields.append(field)
        return sorted(unboxed_struct_fields, key=lambda f: f.field_id)

    def readStruct(self, struct_class, json_obj, target_obj=None):
        self.assert_type(dict, json_obj)
        if target_obj is None:
            target_obj = self.get_implementation_class(struct_class)()
        read_fields = []
        unknown_fields = []
        unboxed_struct_fields = self.get_unboxed_struct_fields(
            struct_class.get_field_definitions())
        for key, raw_value in json_obj.iteritems():
            field = get_field_by_name(target_obj, key)
            # unboxed_struct_fields should not be read as regular values
            if field is None or field in unboxed_struct_fields:
                unknown_fields.append(key)
                continue
            read_fields.append(key)
            with self.context.context(key, field.field_type, raw_value):
                parsed_value = self.readField(field.field_type, raw_value)
                target_obj._set_value_by_field_id(field.field_id, parsed_value)
        # Read the subfields of unboxed fields
        for unboxed_struct_field in unboxed_struct_fields:
            target_obj._set_value_by_field_id(
                unboxed_struct_field.field_id,
                self.readStruct(unboxed_struct_field.field_type.get_python_type(),
                                dict([(k, v) for k, v in json_obj.items()
                                      if k not in read_fields])))
        if not self.skip_unknown_fields and len(unknown_fields) > 0:
            raise JSONValidationException(
                "unknown fields: %s" % ", ".join(unknown_fields),
                self.context)
        try:
            target_obj.validate()
        except Exception as e:
            raise JSONValidationException(
                "Error validating %s: %s" %
                (struct_class.__name__, str(e)), self.context, e)
        return target_obj

    def readField(self, type_definition, value):
        if isinstance(type_definition, types.Enum):
            return self.readEnum(type_definition, value)
        if isinstance(type_definition, types.NumberTypeMarker):
            return self.readValue(type_definition, value)
        if isinstance(type_definition, types.StringTypeMarker):
            return self.readString(type_definition, value)
        if isinstance(type_definition, types.Bool):
            return self.readValue(type_definition, value)
        if isinstance(type_definition, types.Struct):
            return self.readStruct(type_definition.get_python_type(), value)
        if isinstance(type_definition, types.Map):
            return self.readMap(type_definition, value)
        if isinstance(type_definition, types.List):
            return self.readList(type_definition, value)
        if isinstance(type_definition, types.JSONData):
            return value
        if isinstance(type_definition, types.Tuple):
            return self.readTuple(type_definition, value)
        raise Exception(
            "Cannot read type %s (value is %s)" %
            (str(type_definition), str(value)))

    def readEnum(self, type_definition, name):
        enum_key = type_definition.name_to_key(name)
        self.assert_valid(type_definition, enum_key)
        return enum_key

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
        self.assert_map_key_type(map_key_type)
        map_type_definition = type_definition.type_parameters[1]
        for encoded_key, encoded_value in collection.items():
            if isinstance(
                    map_key_type,
                    types.Int) and not isinstance(
                    map_key_type,
                    types.Enum):
                encoded_key = int(encoded_key)
            with self.context.context(encoded_key, map_key_type, encoded_key):
                key = self.readField(map_key_type, encoded_key)
            with self.context.context(
                    encoded_key,
                    map_type_definition,
                    encoded_value):
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
        result = type_definition.get_python_type()(result)
        type_definition.validate(result)
        return result

    def readTuple(self, type_definition, collection):
        self.assert_type(list, collection)
        result = []
        ix = 0
        for encoded_element in collection:
            element_type = type_definition.type_parameters[ix]
            with self.context.context(ix, element_type, encoded_element):
                element = self.readField(element_type, encoded_element)
            result.append(element)
            ix += 1
        result = tuple(result)
        type_definition.validate(result)
        return result
