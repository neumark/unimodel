import sys

def get_module(module_name):
        __import__(module_name)
        return sys.modules[module_name]

def get_backend_type(backend, type_id):
    backend_module = get_module("unimodel.backends.%s.type_data" % backend)
    return backend_module.type_id_mapping[type_id]
