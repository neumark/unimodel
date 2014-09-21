from thrift.protocol.TProtocol import TType, TProtocolBase, TProtocolException
from thrift.protocol.TJSONProtocol import TSimpleJSONProtocol
import base64
import json
import math
import traceback
from StringIO import StringIO
from thriftmodel.util import replace_tuple_element

__all__ = ['TFlexibleJSONProtocol',
           'TFlexibleJSONProtocolFactory']

DEFAULT_OPTIONS = {
    'base64_encode_string': True,
    'allow_unknown_fields': True}

VERSION = 1

UNBOXED_UNION_ATTR = "is_unboxed_union"

NUMBER_TYPES = [
    TType.BYTE,
    TType.I08,
    TType.DOUBLE,
    TType.I16,
    TType.I32,
    TType.I64]

STRING_TYPES = [
    TType.STRING,
    TType.UTF7,
    TType.UTF8,
    TType.UTF16]

def set_field_value(thrift_obj, field_id, value):
    if hasattr(thrift_obj, "_set_value_by_thrift_field_id"):
        thrift_obj._set_value_by_thrift_field_id(field_id, value)
    else:
        field_spec = [f for f in thrift_obj.thrift_spec[1:] if f[0] == field_id]
        setattr(thrift_obj, field_spec[0][2], value)

def iterate_fields(thrift_obj):
    """ generatord for (field_id, value) pairs. """
    for current_field_spec in thrift_obj.thrift_spec[1:]:
        field_id = current_field_spec[0]
        if hasattr(thrift_obj, '_get_value_by_thrift_field_id'):
            # NOTE: the thrift_field_name may be different than the field name used by
            # the python class, this is why it's better to get it by field id.
            field_value = thrift_obj._get_value_by_thrift_field_id(field_id)
        else:
            field_value = getattr(thrift_obj, current_field_spec[2])
        yield (field_id, current_field_spec, field_value)

def get_unboxed_union_field(thrift_obj):
    if hasattr(thrift_obj, "is_unboxed_union"):
        set_fields = []
        for _fid, spec, v in iterate_fields(thrift_obj):
            if v is not None:
                set_fields.append((spec, v))
        if len(set_fields) == 0:
            return (None, None)
        if len(set_fields) > 1:
            raise SerializationException("UnboxedUnion can have at most one field set!")
        return set_fields[0]

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

class ReadContext(object):

    def __init__(self, root_spec, parsed_json):
        self.context_stack = [] # holds a list of (spec, jq_path, object) tuples
        self.root_spec = root_spec
        self.parsed_json = parsed_json
        self.push_context(root_spec, "", parsed_json)

    def push_context(self, spec, key, obj):
        if len(self.context_stack) > 0:
            current = self.context_stack[-1]
        else:
            current = (None, [], None)
        self.context_stack.append((spec, current[1] + [key], obj))

    def pop_context(self):
        self.context_stack.pop()

    def _ensure_context_initialized(self):
        self.context_stack.append((spec, ["."], self.parsed_json))

    def current_spec(self):
        return self.context_stack[-1][0]

    def current_path(self):
        return ".".join(self.context_stack[-1][1])

    def current_object(self):
        return self.context_stack[-1][2]


class TFlexibleJSONProtocol(TSimpleJSONProtocol):
    def __init__(self, trans):
        TSimpleJSONProtocol.__init__(self, trans)
        self.options = dict(DEFAULT_OPTIONS)
        self.read_context = None
        self.CONTAINER_CONSTRUCTORS = {
            TType.STRUCT: self.readFieldStruct,
            TType.MAP: self.readFieldMap,
            TType.SET: self.readFieldSet,
            TType.LIST: self.readFieldList}
        self._TTYPE_HANDLERS = replace_tuple_element(self._TTYPE_HANDLERS,
            TType.UTF8,
            (None, 'writeUTF8String', False))


    def set_options(self, options_dict):
        self.options.update(options_dict)

    def readFieldStruct(self, key, spec, raw_value):
        cls, type_parameters = spec
        obj = cls()
        self.readStruct(obj, type_parameters)
        return obj

    def readFieldMap(self, key, spec, raw_value):
        key_field_type, key_type_parameter, value_field_type, value_type_parameter = spec
        self.validation_assert(type(raw_value) == dict, "Thrift Map field expects JSON dict")
        obj = {}
        for raw_key, raw_value in raw_value.iteritems():
            parsed_key = self.readField(raw_key, key_field_type, key_type_parameter, raw_key)
            parsed_value = self.readField(raw_key, value_field_type, value_type_parameter, raw_value)
            # TODO: validate key, value types!
            obj[parsed_key] = parsed_value
        return obj

    def readFieldSet(self, key, spec, raw_value):
        return set(readFieldList(self, key, spec, raw_value))

    def readFieldList(self, key, spec, raw_value):
        self.validation_assert(type(raw_value) == list, "Thrift Set/List field expects JSON list")
        # TODO: validate type parameter!
        result = [self.readField(str(ix), spec[0], spec[1], raw_value[ix]) for ix in xrange(0, len(raw_value))]
        return result

    def parse_json(self, spec):
        json_str = StringIO()
        try:
            while True:
                json_str.write(self.trans.readAll(1))
        except EOFError:
            pass
        json_str.seek(0)
        self.read_context = ReadContext(spec, json.loads(json_str.getvalue()))

    def readMessageBegin(self):
        self.resetReadContext()
        self.readJSONArrayStart()
        if self.readJSONInteger() != VERSION:
          raise TProtocolException(TProtocolException.BAD_VERSION,
                                   "Message contained bad version.")
        name = self.readJSONString(False)
        typen = self.readJSONInteger()
        seqid = self.readJSONInteger()
        return (name, typen, seqid)

    def validation_assert(self, condition, message=""):
        if not condition:
            raise ReadValidationException(message, self.read_context, data=self.read_context.current_object())

    def readMessageEnd(self):
        self.readJSONArrayEnd()

    def readUnboxedUnion(self, target_obj, json_obj):
        # Try to read fields in the declared order for ThriftModels
        # (otherwise, use thrift_spec field order)
        if hasattr(target_obj, "_fields_by_name"):
            field_id_list = [f.field_id for f in 
                    sorted(target_obj._fields_by_name.values(), key=lambda x: x.creation_count)]
        else:
            field_id_list = [f[0] for f in target_obj.thrift_spec[1:]]
        spec_dict = dict([(f[0], f) for f in target_obj.thrift_spec[1:]])
        failed_field_reads = {}
        for field_id in field_id_list:
            spec = spec_dict[field_id]
            try:
                read_value = self.readField(spec[2], spec[1], spec[3], json_obj)
                # TODO: maybe check if the read_field is empty (this could be an
                # indication that the read failed even if no exception was raised.
                set_field_value(target_obj, field_id, read_value)
                return target_obj
            except ReadValidationException, e:
                failed_field_reads[spec[2]] = str(e)
        # If we reach this point, no field matched:
        raise ReadValidationException(
                "UnboxedUnion read error: no field matched value",
                read_context=self.read_context,
                data=failed_field_reads)


    def readStruct(self, target_obj, thrift_spec):
        if self.read_context is None:
           self.parse_json(thrift_spec)
        json_obj = self.read_context.current_object()
        if hasattr(target_obj, UNBOXED_UNION_ATTR):
            return self.readUnboxedUnion(target_obj, json_obj)
        # (un)known_fields contain thrift field names
        self.validation_assert(type(json_obj) == dict, "Expecting JSON dictionary, got %s" % type(json_obj))
        known_fields = []
        unknown_fields = []
        for key, raw_value in json_obj.iteritems():
            field_spec = [f for f in thrift_spec[1:] if f[2] == key]
            if len(field_spec) == 0:
                unknown_fields.append(key)
                continue
            known_fields.append(key)
            field_id, field_type, thrift_field_name, type_parameters, default_value = field_spec[0]
            parsed_value = self.readField(thrift_field_name, field_type, type_parameters, raw_value)
            set_field_value(target_obj, field_id, parsed_value)
        if not self.options['allow_unknown_fields']:
            self.validation_assert(len(unknown_fields) ==  0,
                "unknown fields: %s" % ", ".join(unknown_fields))
        if hasattr(target_obj, 'validate'):
            try:
                target_obj.validate()
            except Exception, e:
                tb = traceback.format_exc()
                raise ReadValidationException(str(e), self.read_context, tb=tb)

    def readContainer(self, field_type, key, spec, raw_value):
        self.read_context.push_context(spec, key, raw_value)
        try:
            reader = self.CONTAINER_CONSTRUCTORS[field_type]
            return reader(key, spec, raw_value)
        finally:
            self.read_context.pop_context()

    def readField(self, thrift_field_name, field_type, type_parameters, raw_value):
        if field_type in self.CONTAINER_CONSTRUCTORS:
            return self.readContainer(field_type, thrift_field_name, type_parameters, raw_value)
        if field_type in NUMBER_TYPES:
            return self.readNumber(field_type, thrift_field_name, raw_value)
        if field_type in STRING_TYPES:
            return self.readString(field_type, thrift_field_name, raw_value)
        if field_type == TType.BOOL:
            return raw_value

    def readNumber(self, field_type, thrift_field_name, raw_value):
        if field_type == TType.DOUBLE:
            self.validation_assert(type(raw_value) == float, "Expecting floating point number, got %s" % str(raw_value))
        else:
            self.validation_assert(type(raw_value) == int, "Expecting integer number, got %s" % str(raw_value))
            # TODO: verify range
        return raw_value

    def readString(self, field_type, thrift_field_name, raw_value):
        if field_type == TType.STRING and self.options['base64_encode_string']:
            return base64.b64decode(raw_value)
        if field_type == TType.STRING:
            self.validation_assert(type(raw_value) in [str, unicode],
                    "Expecting unicode string, got %s" % type(raw_value))
        if field_type == TType.UTF8:
            self.validation_assert(type(raw_value) == unicode,
                    "Expecting unicode string, got %s" % type(raw_value))
        return raw_value

    def writeString(self, val):
        # NOTE: by this point, we know that the thrift type is STRING
        if self.options['base64_encode_string']:
            val = base64.b64encode(val)
        TSimpleJSONProtocol.writeString(self, val)

    def writeUTF8String(self, val):
        self.context.write()
        self.trans.write(json.dumps(val))

    def writeStruct(self, obj, thrift_spec):
        # If obj is an UnboxedUnion type, write the active field if it is set.
        if hasattr(obj, UNBOXED_UNION_ATTR):
            field_spec, field_value = get_unboxed_union_field(obj)
            # note, it's possible that the unboxed union is empty
            # if they call deserialize on it directly, they they should get '{}'
            if field_spec is not None:
                return TSimpleJSONProtocol.writeFieldByTType(
                        self,
                        field_spec[1],
                        field_value,
                        field_spec[3])
        # UnboxedUnion fields must be set to None
        # if none of the fields are set.
        for field_id, _spec, value in iterate_fields(obj):
            if hasattr(value, UNBOXED_UNION_ATTR):
                field_id, field_value = get_unboxed_union_field(value)
                if field_value is None:
                    set_field_value(obj, field_id, None)
        else:
            TSimpleJSONProtocol.writeStruct(self, obj, thrift_spec)
    
 
class TFlexibleJSONProtocolFactory(object):

    def getProtocol(self, trans):
        return TFlexibleJSONProtocol(trans)
