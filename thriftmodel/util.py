def replace_tuple_element(orig_tuple, ix, new_element):
    return orig_tuple[:ix] + (new_element,) + orig_tuple[(ix + 1):]


