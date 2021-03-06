# Copyright 2017 Giovanni Campagna <gcampagn@cs.stanford.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>. 
'''
Created on Aug 2, 2017

@author: gcampagn
'''

import itertools

from grammar.thingtalk import UNITS
ALL_UNITS = set(itertools.chain(*UNITS.values()))

def _read_value(decoded, off, values):
    token = decoded[off]
    value = dict()
    consumed = 1
    if token == 'true':
        value['type'] = 'Bool'
        value['value'] = dict(value=True)
    elif token == 'false':
        value['type'] = 'Bool'
        value['value'] = dict(value=False)
    elif token == 'rel_home' or token == 'rel_work' or token == 'rel_current_location':
        value['type'] = 'Location'
        value['value'] = dict(relativeTag=token, latitude=-1., longitude=-1.)
    elif token.startswith('LOCATION_'):
        value['type'] = 'Location'
        value['value'] = values[token]
    elif token.startswith('tt-param:'):
        value['type'] = 'VarRef'
        value['value'] = dict(id=token)
    elif token.startswith('QUOTED_STRING_'):
        value['type'] = 'String'
        value['value'] = values[token]
    elif token.startswith('DATE_'):
        value['type'] = 'Date'
        value['value'] = values[token]
    elif token.startswith('TIME_'):
        value['type'] = 'Time'
        value['value'] = values[token]
    elif token.startswith('USERNAME_'):
        value['type'] = 'Entity(tt:username)'
        value['value'] = values[token]
    elif token.startswith('HASHTAG_'):
        value['type'] = 'Entity(tt:hashtag)'
        value['value'] = values[token]
    elif token.startswith('PHONE_NUMBER_'):
        value['type'] = 'Entity(tt:phone_number)'
        value['value'] = values[token]
    elif token.startswith('EMAIL_ADDRESS_'):
        value['type'] = 'Entity(tt:email_address)'
        value['value'] = values[token]
    elif token.startswith('URL_'):
        value['type'] = 'Entity(tt:url)'
        value['value'] = values[token]
    elif token.startswith('DURATION_') or token.startswith('SET_'):
        value['type'] = 'Measure'
        value['value'] = values[token]
    elif token.startswith('NUMBER_'):
        if len(decoded) > off + 1 and decoded[off+1] in ALL_UNITS:
            value['type'] = 'Measure'
            value['value']['unit'] = decoded[off+1]
            consumed = 2
        else:
            value['type'] = 'Number'
        value['value'] = values[token]
    elif token.startswith('GENERIC_ENTITY_'):
        entity_type = token[len('GENERIC_ENTITY_'):]
        value['type'] = 'Entity(' + entity_type + ')'
        value['value'] = values[token]
    else:
        # assume an enum, and hope for the best
        value['type'] = 'Enum'
        value['value'] = dict(value=token)

    return value, consumed

def _read_prim(decoded, off, values):
    fn = decoded[off]
    prim = dict(name=dict(id=fn), args=[])
    args = prim['args']
    consumed = 1
    if off + consumed < len(decoded) and decoded[off+consumed].startswith('USERNAME_'):
        prim['person'] = values[decoded[off+consumed]]['value']
        consumed += 1
    while off + consumed < len(decoded) and decoded[off+consumed].startswith('tt-param:'):
        pname = decoded[off+consumed]
        op = decoded[off+consumed+1]
        value, consumed_arg = _read_value(decoded, off+consumed+2, values)
        value['name'] = dict(id=pname)
        value['operator'] = op
        args.append(value)
        consumed += 2+consumed_arg
    return prim, consumed

def to_json(decoded, grammar, values):
    type = decoded[0]
    if type == 'special':
        return dict(special=dict(id=decoded[1]))
    elif type == 'answer':
        value, _ = _read_value(decoded, 1, values)
        return dict(answer=value)
    elif type == 'command':
        if decoded[1] != 'type':
            raise ValueError('Invalid command type ' + decoded[1])
        if decoded[2] == 'generic':
            return dict(command=dict(type='help', value=dict(value='generic')))
        else:
            return dict(command=dict(type='help', value=dict(value=values[decoded[2]])))
    else:
        # rule
        rule = dict()
        off = 1
        trigger, consumed = _read_prim(decoded, off, values)
        if trigger['name']['id'] != 'tt:$builtin.now':
            rule['trigger'] = trigger
        off += consumed
        query, consumed = _read_prim(decoded, off, values)
        off += consumed
        if query['name']['id'] != 'tt:$builtin.noop':
            rule['query'] = query
        action, consumed = _read_prim(decoded, off, values)
        off += consumed
        if query['name']['id'] != 'tt:$builtin.notify':
            rule['action'] = action
        return dict(rule=rule)
