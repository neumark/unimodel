from unimodel.backends.base import SchemaWriter
import copy

""" Example from http://json-schema.org/example2.html

{
    "id": "http://some.site.somewhere/entry-schema#",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "description": "schema for an fstab entry",
    "type": "object",
    "required": [ "storage" ],
    "properties": {
        "storage": {
            "type": "object",
            "oneOf": [
                { "$ref": "#/definitions/diskDevice" },
                { "$ref": "#/definitions/diskUUID" },
                { "$ref": "#/definitions/nfs" },
                { "$ref": "#/definitions/tmpfs" }
            ]
        },
        "fstype": {
            "enum": [ "ext3", "ext4", "btrfs" ]
        },
        "options": {
            "type": "array",
            "minItems": 1,
            "items": { "type": "string" },
            "uniqueItems": true
        },
        "readonly": { "type": "boolean" }
    },
    "definitions": {
        "diskDevice": {
            "properties": {
                "type": { "enum": [ "disk" ] },
                "device": {
                    "type": "string",
                    "pattern": "^/dev/[^/]+(/[^/]+)*$"
                }
            },
            "required": [ "type", "device" ],
            "additionalProperties": false
        },
        "diskUUID": {
            "properties": {
                "type": { "enum": [ "disk" ] },
                "label": {
                    "type": "string",
                    "pattern": "^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$"
                }
            },
            "required": [ "type", "label" ],
            "additionalProperties": false
        },
        "nfs": {
            "properties": {
                "type": { "enum": [ "nfs" ] },
                "remotePath": {
                    "type": "string",
                    "pattern": "^(/[^/]+)+$"
                },
                "server": {
                    "type": "string",
                    "oneOf": [
                        { "format": "host-name" },
                        { "format": "ipv4" },
                        { "format": "ipv6" }
                    ]
                }
            },
            "required": [ "type", "server", "remotePath" ],
            "additionalProperties": false
        },
        "tmpfs": {
            "properties": {
                "type": { "enum": [ "tmpfs" ] },
                "sizeInMB": {
                    "type": "integer",
                    "minimum": 16,
                    "maximum": 512
                }
            },
            "required": [ "type", "sizeInMB" ],
            "additionalProperties": false
        }
    }
}
"""

STRUCT_MAP_DEFINITION_TEMPLATE = {
    "properties": { },  # Fill with field definitions
    "additionalProperties": True,
    "required": [ ],  # Fill with required field names
}

SCHEMA_TEMPLATE = copy.deepcopy(STRUCT_MAP_DEFINITION_TEMPLATE).update({
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "description": None,  # Replace with schema description
    "properties": { },  # Fill with field definitions
    "additionalProperties": True,
    "required": [ ],  # Fill with required field names
    "definitions": {}  # Fill struct and map type definitions
})

BASIC_FIELD_TEMPLATE = {
    "type": None  # Replace with basic type name, eg: "string"
} 

LIST_TEMPLATE =  {
    "type": "array",
    "items": {
        "type": None  # Replace with type reference to definition of elements
    },
    "uniqueItems": False  # set to True for sets
}

class JSONSchemaWriter(SchemaWriter):
    pass

