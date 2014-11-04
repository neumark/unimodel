import sys
import types
import itertools
import inspect
from functools import wraps
from thrift.Thrift import TType, TMessageType, TException, TApplicationException
from thrift.protocol.TBase import TBase, TExceptionBase
from thrift.transport import TTransport

class FieldFactory(object):

    def field_dict_to_field_list(self, field_dict):
        # Then, we process the contents of field_dict
        fields = [(k,v) for k,v in field_dict.iteritems()]
        # set missing field names
        for name, field_data in fields:
            if field_data.field_name is None:
                field_data.field_name = name
        return fields

    def add_fields(self, cls, fields=None):
        thrift_spec_attr = self.get_field_definition(cls, fields)
        for attr_name, attr_value in thrift_spec_attr.items():
            if attr_value:  # do not set empty values
                setattr(cls, attr_name, attr_value)

    def replace_default_field_ids(self, fields):
        # replace -1 field ids with the next available positive integer
        # fields is a list of (python_field_name, field_def) pairs.
        taken_field_ids = set([f[1].field_id for f in fields])
        next_field_id = 1
        # sort fields by creation count
        fields = sorted(fields, key=lambda x:x[1].creation_count)
        for field_name, field in fields:
            if field.field_id < 1:
                while next_field_id in taken_field_ids:
                    next_field_id += 1
                taken_field_ids.add(next_field_id)
                field.field_id = next_field_id
        return fields
 
    def get_field_definition(self, cls, field_dict=None, bases=None):
        """ Returns a dictionary of attributes which will
            be set on the class by the metaclass. These
            attributes are:
            _fields_by_id
            _fields_by_name
        """
        fields = self.field_dict_to_field_list(field_dict or {})
        self.replace_default_field_ids(fields)
        # thrift_spec can be a list or a tuple
        # we only need to set it here in the latter case
        # because a list thrift_spec is already an attr of cls.
        attr_dict = {
            '_fields_by_id': dict([(v.field_id, (k,v)) for k,v in fields]),
            '_fields_by_name': dict([(k,v) for k,v in fields])}
        return attr_dict

class Field(object):
    _field_creation_counter = 0

    def __init__(self,
            field_type,
            field_name=None,
            field_id=-1,
            default=None,
            required=None,
            annotations=None):
        self.creation_count = Field._field_creation_counter
        Field._field_creation_counter += 1
        # If they left off the parenthesis, fix it.
        if type(field_type) == type:
            self.field_type = field_type()
        else:
            self.field_type = field_type
        self.field_id = field_id
        self.field_name = field_name
        self.default = default
        self.required = required
        self.annotations = annotations

    def validate(self, value):
        # first, validate the type of the value
        self.field_type.validate(value)

class UnimodelMetaclass(type):
    def __init__(cls, name, bases, dct):
        super(UnimodelMetaclass, cls).__init__(name, bases, dct)
        fields = dict([(k,v) for k,v in dct.iteritems() if isinstance(v, Field)])
        # Note: we could optionally pass a custom FieldMerger here if needed.
        field_factory = FieldFactory()
        field_factory.add_fields(cls, fields)


class Unimodel(object):

    __metaclass__ = UnimodelMetaclass

    def __init__(self, **kwargs):
        self._model_data = {}

        for field_name, value in kwargs.iteritems():
            setattr(self, field_name, value)

    def __repr__(self):
        L = ['%s=%r' % (self._fields_by_id[field_id][0], value)
            for field_id, value in self._model_data.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def write(self, protocol):
        """ this method is called by the thrift protocols """
        return protocol.serializer.write_to_stream(self, protocol)

    def read(self, protocol):
        """ this method is called by the thrift protocols """
        return protocol.serializer.read_from_stream(self, protocol)

    def iterkeys(self):
        return itertools.imap(
                lambda pair: self._fields_by_id[pair[0]][1].field_name,
                itertools.ifilter(lambda pair: pair[1] is not None, self._model_data.iteritems()))

    def _field_name_to_field_id(self, field_name):
        field = [f[1] for f in self._fields_by_id.values() if f[1].field_name == field_name]
        if len(field) < 1:
            raise KeyError(field_name)
        return field[0].field_id

    def __getitem__(self, field_name):
        return self._model_data[self._field_name_to_field_id(field_name)]

    def __setitem__(self, field_name, value):
        self._model_data[self._field_name_to_field_id(field_name)] = value

    def __delitem__(self, field_name):
        self._model_data.__delitem__(
                self._field_name_to_field_id(field_name))

    def __iter__(self):
        return self.iterkeys()

    def __getattribute__(self, name):
        # check in model_data first
        fields_by_name = object.__getattribute__(self, '_fields_by_name')
        # Note: In a try ... raise block because reading of _model_data
        # raises an AttributeError in Unimodel.__init__, when the
        # attribute is initialized.
        try:
            model_data = object.__getattribute__(self, '_model_data')
            # If a model field name matches, return its value
            if name in fields_by_name:
                return model_data.get(fields_by_name[name].field_id, None)
        except AttributeError:
            pass
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if hasattr(self, '_model_data') and name in self._fields_by_name:
            self._model_data[self._fields_by_name[name].field_id] = value
            return
        super(Unimodel, self).__setattr__(name, value)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

    def _set_value_by_thrift_field_id(self, field_id, value):
        self._model_data[field_id] = value

    def _get_value_by_thrift_field_id(self, field_id):
        return self._model_data.get(field_id, None)

    def validate(self):
        # check to make sure required fields are set
        for k, v in self._fields_by_name.iteritems():
            if v.required and self._model_data.get(v.field_id, None) is None:
                raise ValidationException("Required field %s (id %s) not set" % (k, v.field_id))
            # Run any field validators
            v.field_type.validate(self._model_data.get(v.field_id, None))
        # Run the validator for the model itself (if it is set)
        if hasattr(self, 'validators'):
            for validator in (self.validators or []):
                validator.validate(self)

class ModelRegistry(object):

    def __init__(self):
        self.class_dict = {}

    def register(self, interface_class, implementation_class):
        self.class_dict[interface_class] = implementation_class

    def lookup(self, interface_class):
        return self.class_dict.get(interface_class, interface_class)
