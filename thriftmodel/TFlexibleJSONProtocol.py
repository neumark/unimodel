from thrift.protocol.TProtocol import TType, TProtocolBase, TProtocolException
from thrift.protocol.TJSONProtocol import TSimpleJSONProtocol
import base64
import json
import math
import traceback
from StringIO import StringIO

__all__ = ['TFlexibleJSONProtocol',
           'TFlexibleJSONProtocolFactory']

VERSION = 1

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

class ReadValidationException(Exception):

    def __init__(self, message, read_context=None, tb=None):
        Exception.__init__(self, message)
        self.read_context = read_context
        self.tb = tb

    def __str__(self):
        msg = Exception.__str__(self)
        json_path = "?" if self.read_context is None else self.read_context.current_path()
        return "ReadValidationException: %s, json_path: %s" % (
            msg, json_path)

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
        return self.context_stack[-1][1]

    def current_object(self):
        return self.context_stack[-1][2]


class TFlexibleJSONProtocol(TSimpleJSONProtocol):
    def __init__(self, trans):
        TSimpleJSONProtocol.__init__(self, trans)
        self.allow_unknown_fields = True
        self.trans = trans
        self.read_context = None
        self.CONTAINER_CONSTRUCTORS = {
            TType.STRUCT: self.readFieldStruct,
            TType.MAP: self.readFieldMap,
            TType.SET: self.readFieldSet,
            TType.LIST: self.readFieldList}

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
            raise ReadValidationException(message, self.read_context)

    def readMessageEnd(self):
        self.readJSONArrayEnd()

    def readStruct(self, target_obj, thrift_spec):
        # if target_obj isa ThriftModel, we have access to
        # validators and the required field.
        if self.read_context is None:
           self.parse_json(thrift_spec)
        json_obj = self.read_context.current_object()
        # (un)known_fields contain thrift field names
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
            if hasattr(target_obj, '_set_value_by_thrift_field_id'):
                # NOTE: the thrift_field_name may be different than the field name used by
                # the python class, this is why it's better to set it by field id.
                target_obj._set_value_by_thrift_field_id(field_id, parsed_value)
            else:
                setattr(target_obj, thrift_field_name, parsed_value)
        if self.allow_unknown_fields:
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
        reader = self.CONTAINER_CONSTRUCTORS[field_type]
        result = reader(key, spec, raw_value)
        self.read_context.pop_context()
        return result

    def readField(self, thrift_field_name, field_type, type_parameters, raw_value):
        if field_type in self.CONTAINER_CONSTRUCTORS:
            return self.readContainer(field_type, thrift_field_name, type_parameters, raw_value)
        if field_type in (NUMBER_TYPES + STRING_TYPES):
            # TODO type checking eg: float vs int, value ranges
            return raw_value
    
 
class TFlexibleJSONProtocolFactory(object):

    def getProtocol(self, trans):
        return TFlexibleJSONProtocol(trans)
