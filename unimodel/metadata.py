from unimodel import types


class Metadata(object):

    """ Class for adding metadata to structs, fields, types - anything. """

    def __init__(
            self,
            validators=None,
            annotations=None,
            backend_data=None):
        self.validators = validators or []
        self.annotations = annotations or []
        self.backend_data = backend_data or {}

    def get_backend_data(self, backend, key):
        if backend not in self.backend_data:
            self.backend_data[backend] = {}
        return self.backend_data[backend].get(key, None)

    def set_backend_data(self, backend, key, value):
        if backend not in self.backend_data:
            self.backend_data[backend] = {}
        self.backend_data[backend][key] = value
