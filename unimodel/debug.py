import sys

class ProtocolDebugger(object):
    def __init__(self, protocol_factory, stream=sys.stdout, log_protocol=True, log_transport=True):
        self.protocol_factory = protocol_factory
        self.log_protocol = log_protocol
        self.log_transport = log_transport
        self.stream = stream
        self.indent_counter = 0
        self.call_counter = 0

    def wrap_method(self, obj, class_name, function_name, func):
        # print call id so we can sort
        # indent_counter a single value, not per obj
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.indent_counter += 1
            current_call_counter = self.call_counter
            self.call_counter += 1
            str_args = ["%s" % str(a) for a in args] + ["%s=%s" % (str(k), str(v)) for k,v in kwargs.iteritems()]
            response = func(*args, **kwargs)
            self.indent_counter -= 1
            self.stream.write("%04d %s%s.%s(%s) -> %s\n" % (current_call_counter, " " * self.indent_counter, class_name, function_name, ", ".join(str_args), response))
            return response
        return wrapper

    def getProtocol(self, transport):
        protocol = self.protocol_factory.getProtocol(transport)
        objects_to_patch = []
        if self.log_protocol:
            objects_to_patch.append(protocol)
        if self.log_transport:
            objects_to_patch.append(transport)
        for obj in objects_to_patch:
            for name in dir(obj):
                fn = getattr(obj, name)
                if hasattr(fn, '__call__'):
                    setattr(obj, name, self.wrap_method(obj, obj.__class__.__name__, name, fn))
        return protocol
