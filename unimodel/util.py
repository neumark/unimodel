import sys
import json

# Ingenious python 2/3 ugliness from http://stackoverflow.com/a/11301781
try:
    basestring  # attempt to evaluate basestring

    def is_str(s):
        return isinstance(s, basestring)
except NameError:
    def is_str(s):
        return isinstance(s, str)

def instantiate_if_class(t):
    # If the user left off the parenthesis (eg: Field(Int)),
    # instantiate the type class.
    if isinstance(t, type):
        return t()
    return t

def get_module(module_name):
        __import__(module_name)
        return sys.modules[module_name]

def get_backend_type(backend, type_id):
    backend_module = get_module("unimodel.backends.%s.type_data" % backend)
    return backend_module.type_id_mapping[type_id]

def pprint_json(json_data):
    return json.dumps(
        json_data,
        sort_keys=True,
        indent=4,
        separators=(',', ': '))
