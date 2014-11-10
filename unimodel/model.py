import sys
import copy
from unimodel.metadata import Metadata
from unimodel.validation import ValidationException


class FieldFactory(object):

    def field_dict_to_field_list(self, field_dict):
        # Then, we process the contents of field_dict
        field_list = []
        for field_name, field in field_dict.iteritems():
            # A copy of the field is made so that changes to the field
            # like replacing default field ids and field names are
            # not reflected in the original field definition.
            field_copy = copy.copy(field)
            # set missing field names
            if field_copy.field_name is None:
                field_copy.field_name = field_name
            field_list.append(field_copy)
        return field_list

    def add_fields(self, cls, fields=None):
        attrs = self.get_field_definition(cls, fields)
        for attr_name, attr_value in attrs.items():
            if attr_value:  # do not set empty values
                setattr(cls, attr_name, attr_value)

    def replace_default_field_ids(self, fields):
        # replace -1 field ids with the next available positive integer
        # fields is a list of (python_field_name, field_def) pairs.
        taken_field_ids = set([f.field_id for f in fields])
        next_field_id = 1
        # sort fields by creation count
        fields = sorted(fields, key=lambda f: f.creation_count)
        for field in fields:
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
        attr_dict = {
            '_fields_by_id': dict(
                [(field.field_id, field) for field in fields]),
            '_fields_by_name': dict(
                [(field.field_name, field) for field in fields])}
        return attr_dict


class Field(object):
    _field_creation_counter = 0

    def __init__(self,
                 field_type,
                 field_name=None,
                 field_id=-1,
                 default=None,
                 required=False,
                 metadata=None):
        self.creation_count = Field._field_creation_counter
        Field._field_creation_counter += 1
        # If they left off the parenthesis, fix it.
        if isinstance(field_type, type):
            self.field_type = field_type()
        else:
            self.field_type = field_type
        self.field_id = field_id
        self.field_name = field_name
        self.default = default
        self.required = required
        self.metadata = metadata or Metadata()

    def validate(self, value):
        # first, validate the type of the value
        self.field_type.validate(value)
        # then run any potential custom validators on the field
        if self.metadata.validators:
            for validator in self.metadata.validators:
                validator.validate(value)


class UnimodelMetaclass(type):

    def __init__(cls, name, bases, dct):
        super(UnimodelMetaclass, cls).__init__(name, bases, dct)
        field_dict = dict([(k, v)
                           for k, v in dct.iteritems() if isinstance(
                               v, Field)])
        setattr(cls, "_field_dict", field_dict)
        fields = {}
        # for each base class, add it's _field_dict to fields
        for base in bases:
            if hasattr(base, "_field_dict"):
                fields.update(base._field_dict)
        fields.update(field_dict)
        field_factory = FieldFactory()
        field_factory.add_fields(cls, fields)


class Unimodel(object):

    __metaclass__ = UnimodelMetaclass

    def __init__(self, **kwargs):
        self._model_data = {}

        for field_name, value in kwargs.iteritems():
            setattr(self, field_name, value)

    def __repr__(self):
        L = ['%s=%r' % (self._fields_by_id[field_id].field_name, value)
             for field_id, value in self._model_data.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def write(self, protocol):
        """ this method is called by the thrift protocols """
        return protocol.serializer.write_to_stream(self, protocol)

    def read(self, protocol):
        """ this method is called by the thrift protocols """
        return protocol.serializer.read_from_stream(self, protocol)

    def iterkeys(self):
        return self._fields_by_name.keys()

    def _field_name_to_field_id(self, field_name):
        return self.get_field_definition(field_name).field_id

    @classmethod
    def get_field_definition(cls, field_name):
        return cls._fields_by_name[field_name]

    @classmethod
    def get_field_definitions(cls):
        return cls._fields_by_name.values()

    def __getitem__(self, field_name):
        return self._model_data.get(
            self._field_name_to_field_id(field_name),
            None)

    def __setitem__(self, field_name, value):
        self._model_data[self._field_name_to_field_id(field_name)] = value

    def __delitem__(self, field_name):
        self._model_data.__delitem__(
            self._field_name_to_field_id(field_name))

    def __iter__(self):
        return self.iterkeys()

    def items(self):
        return iter([(self._fields_by_id[i[0]].field_name, i[1])
                     for i in self._model_data.items()])

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
        return isinstance(
            other,
            self.__class__) and self._model_data == other._model_data

    def __ne__(self, other):
        return not (self == other)

    def _set_value_by_field_id(self, field_id, value):
        self._model_data[field_id] = value

    def _get_value_by_field_id(self, field_id):
        return self._model_data.get(field_id, None)

    def validate(self):
        # check to make sure required fields are set
        for k, v in self._fields_by_name.iteritems():
            if self._model_data.get(v.field_id, None) is None:
                if v.required:
                    raise ValidationException(
                        "Required field %s (id %s) not set" %
                        (k, v.field_id))
            else:
                # Run any field validators
                v.field_type.validate(self._model_data.get(v.field_id, None))
        # Run the validator for the model itself (if it is set)
        if hasattr(self, 'metadata') and hasattr(self.metadata, 'validators'):
            for validator in (self.metadata.validators or []):
                validator.validate(self)

    @classmethod
    def get_name(cls):
        return cls.__name__


class UnimodelUnion(Unimodel):

    # TODO: validate that 0 or 1 fields are set!
    # Perhaps setattr should unset the formerly active field

    def current_field(self):
        set_fields = []
        for f in self.get_field_definitions():
            value = self._get_value_by_field_id(current_field.field_id)
            if value is not None:
                set_fields.append(f.field_name, value)
        if not set_fields:
            return None
        if len(set_fields) > 1:
            raise Exception(
                "Union has too many set fields: %s" %
                str(set_fields))
        return set_fields[0]

    def current_value(self):
        current_field_name = self.current_field()
        if not current_field:
            return None
        return self[current_field_name]


class ModelRegistry(object):

    def __init__(self):
        self.class_dict = {}

    def register(self, interface_class, implementation_class):
        self.class_dict[interface_class] = implementation_class

    def lookup(self, interface_class):
        return self.class_dict.get(interface_class, interface_class)

    def lookup_interface(self, implementation_class):
        for iface_candidate, impl_candidate in self.class_dict.items():
            if issubclass(impl_candidate, implementation_class):
                return iface_candidate
        return implementation_class
