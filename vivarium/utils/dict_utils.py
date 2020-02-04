from __future__ import absolute_import, division, print_function


tuple_separator = '___'

def merge_dicts(dicts):
    merge = {}
    for d in dicts:
        merge.update(d)
    return merge

def flatten_role_dicts(dicts):
    '''
    Input:
        dicts (dict): embedded state dictionaries with the {'role_id': {'state_id': state_value}}
    Return:
        merge (dict): flattened dictionary with {'state_id_role_id': value}
    '''
    merge = {}
    for role, states_dict in dicts.items():
        for state, value in states_dict.items():
            merge.update({state + '_' + role: value})
    return merge

def tuplify_role_dicts(dicts):
    '''
    Input:
        dicts (dict): embedded state dictionaries with the {'role_id': {'state_id': state_value}}
    Return:
        merge (dict): tuplified dictionary with {(role_id','state_id'): value}
    '''
    merge = {}
    for role, states_dict in dicts.items():
        for state, value in states_dict.items():
            merge.update({(role, state): value})
    return merge

def tuple_key_to_string(dictionary):

    # get down to the leaves first
    for k, v in dictionary.items():
        if isinstance(v, dict):
            tuple_key_to_string(v)

        # convert tuples in lists
        if isinstance(v, list):
            for idx, var in enumerate(v):
                if isinstance(var, tuple):
                    v[idx] = tuple_separator.join(var)
                if isinstance(var, dict):
                    tuple_key_to_string(var)

    # which keys are tuples?
    tuple_ks = [k for k in dictionary.keys() if isinstance(k, tuple)]
    for tuple_k in tuple_ks:
        str_k = tuple_separator.join(tuple_k)
        dictionary[str_k] = dictionary[tuple_k]
        del dictionary[tuple_k]

    return dictionary
