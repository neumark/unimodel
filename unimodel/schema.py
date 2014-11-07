""" Schema for unimodel objects.
    This allow us to do several things:
    - Encode the schema of the message along with the message itself
    - Build ASTs for generators which take eg. jsonschema as input
    - Create classes at runtime based on a schema (jsonschema or thrift)
    etc.
"""

from unimodel.model import Unimodel, Field
from unimodel import types

class SchemaObjectMetadata(Unimodel):
    annotations = Field(List(UTF8, UTF8))
    # TODO: validators
    backend_data = Field(
                    Map(
                        UTF8,  # Key is the name of the backend, eg: 'thrift'
                        # data for each backend should be represented as a simple dict
                        Map(UTF8, UTF8)))

class SchemaObject(Unimodel):
    name = Field(UTF8, required=True)
    metadata = Field(Struct(SchemaObjectMetadata))

class StructDef(Unimodel):
