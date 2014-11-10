def append_key(prefix, postfix):
    return "%s.%s" % (prefix, postfix)


def flatten(obj):
    return sorted(_flatten(obj), key=lambda x: x[0])


def _flatten(obj, key="", acc=None):
    acc = acc if acc is not None else []
    if isinstance(obj, dict):
        for k, v in obj.iteritems():
            _flatten(v, append_key(key, str(k)), acc)
    elif isinstance(obj, list):
        for i in xrange(0, len(obj)):
            _flatten(obj[i], append_key(key, str(i)), acc)
    elif hasattr(obj, 'thrift_spec'):
        keys = [f[2] for f in obj.thrift_spec[1:]]
        for k in keys:
            value = getattr(obj, k)
            if value is not None:
                _flatten(value, append_key(key, k), acc)
    else:
        acc.append((key, obj))
    return acc
