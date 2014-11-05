
# Ingenious pyhton 2/3 ugliness from http://stackoverflow.com/a/11301781
try:
    basestring  # attempt to evaluate basestring
    def is_str(s):
        return isinstance(s, basestring)
except NameError:
    def is_str(s):
        return isinstance(s, str)

class ValidationException(Exception):
    pass

class ValueTypeException(ValidationException):
    pass

