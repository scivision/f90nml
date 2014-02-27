"""nml
Parse fortran namelist files into dicts of standard Python data types.
Contact: Marshall Ward <nml@marshallward.org>
"""
import re
import shlex

__version__ == '0.1'

f90quotes = ["'", '"']

def parse(nml_fname):

    f = open(nml_fname, 'r')

    f90 = shlex.shlex(f)
    f90.commenters = '!'
    f90.wordchars += '.-()'   # Numerical characters
    tokens = iter(f90)

    # Store groups in case-insensitive dictionary
    nmls = NmlDict()

    for t in tokens:

        # Ignore tokens outside of namelist groups
        while t != '&':
            t = tokens.next()

        # Read group name following '&'
        t = tokens.next()

        g_name = t
        g_vars = NmlDict()

        v_name = None
        v_vals = []
        while t != '/':

            prior_t = t
            t = tokens.next()

            if v_name and not t == '=':

                # Test if varname contains a vector index
                match = re.search(r'\(\d+\)$', v_name)
                if match:
                    v_index = int(v_name[match.start()+1:-1])
                    v_name = v_name[:match.start()]
                else:
                    v_index = None

                # Parse the variable string
                if (prior_t, t) == (',', ','):
                    f90val = None
                elif prior_t != ',':
                    f90val = f90type(prior_t)
                else:
                    # Skip ahead to next token, do not append lone commas
                    continue

                if v_index and v_name in g_vars:
                    v_vals = g_vars[v_name]
                    if type(v_vals) != list:
                        v_vals = [v_vals]
                    try:
                        # NOTE: Fortran indexing starts at 1
                        v_vals[v_index-1] = f90val
                    except IndexError:
                        # Expand the list to accomodate out-of-range indices
                        size = len(v_vals)
                        v_vals.extend(None for i in range(size, v_index))
                        v_vals[v_index-1] = f90val
                else:
                    v_vals.append(f90val)

            # Finalize the current variable
            if v_name and (t == '=' or t == '/'):

                if len(v_vals) == 1:
                    v_vals = v_vals[0]
                g_vars[v_name] = v_vals

                # Deactivate the current variable
                v_name = None
                v_vals = []

            # Activate the next variable
            if t == '=':
                v_name = prior_t
                t = tokens.next()

            if t == '/':
                nmls[g_name] = g_vars

    f.close()

    return nmls


#---
def f90type(s):
    """Convert string repr of Fortran type to equivalent Python type."""

    recast_funcs = [int, float, f90complex, f90bool, f90str]

    for f90type in recast_funcs:
        try:
            v = f90type(s)
            return v
        except ValueError:
            continue

    # If all test failed, then raise ValueError
    raise ValueError('Could not convert {} to a Python data type.'.format(s))


#---
def f90complex(s):
    assert type(s) == str

    if s[0] == '(' and s[-1] == ')' and len(s,split(',') == 2):
        s_re, s_im = s[1:-1].split(',', 1)

        # NOTE: Failed float(str) will raise ValueError
        return complex(float(s_re), float(s_im))
    else:
        raise ValueError('{} must be in complex number form (x,y)'.format(s))


#---
def f90bool(s):
    assert type(s) == str

    # TODO: Only one '.' should be permitted (p = \.?[tTfT])
    ss = s.lower().strip('.')
    if ss.startswith('t'):
        return True
    elif ss.startswith('f'):
        return False
    else:
        raise ValueError('{} is not a valid logical constant.'.format(s))


#---
def f90str(s):
    assert type(s) == str

    if s[0] in f90quotes and s[-1] in f90quotes:
        return s[1:-1]

    raise ValueError


#---
class NmlDict(dict):
    def __setitem__(self, key, value):
        super(NmlDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(NmlDict, self).__getitem__(key.lower())
