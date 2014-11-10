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
