"""
.. A feature structure class, to encapsulate the SemSpec.

.. moduleauthor:: Luca Gilardi <lucag@icsi.berkeley.edu>

"""

from utils import update, Struct
from json.encoder import JSONEncoder
from collections import namedtuple
# import pprint

FeatureDesc = namedtuple('FeatureDesc', ['parent', 'role', 'type', 'index', 'typesystem', 'value'])

class FeatureStruct(Struct):
    def __init__(self, **entries):
        self.__dict__.update(entries)
    
    def __setitem__(self, i, item):
        self.__dict__.__setitem__(i, item)
        
    def __items__(self):
        return self.__dict__.items()
        
class Feature(object): 
    def __init__(self, **entries):
        """Constructor. It needs the __type__, __typesystem__ and __value__ 
        keys be present in **entries.
        """        
        # We want entries passed in to override those in self.
        update(self, **entries)
        
    def type(self):
        t = self.__type__
        return t.replace('-', '_') if t else t

    def index(self):
        return self.__index__
    
    def typesystem(self):
        return self.__typesystem__
    
#    def value(self):
#        return self.__value__

    def __dir__(self):
        d = self.__dict__
        fs = self.__fs__()
        v = self.__dict__['__value__']
        try:
            return [] if v else list(d.keys()) + (list(fs.__dict__.keys()))
        except TypeError:
            print(type(d.keys()), d.keys())
            print(type(fs.__dict__.keys()), fs.__dict__.keys())
            raise
        
    def __getattr__(self, name):
        try:
            return getattr(self.__fs__(), name)
        except KeyError:
            return getattr(self.__dict__['__value__'], name)

    def __fs__(self):
        ff = self.__features__
        return ff[self.__index__]
        
    def __repr__(self):
        d = self.__dict__
        i = self.__index__
        t = d['__type__']
        ts = d['__typesystem__']
        v = d['__value__']
        if not v and self.__index__ in self.__features__:
            fs = self.__fs__()
            return '[%s %s[%s], roles: %s]' % (ts, t, i, ', '.join(fs.__dict__.keys()))
        else:
            return str(self)
        
    def __int__(self):
        return int(self.__value__)
    
    def __float__(self):
        return float(self.__value__)
    
    def __str__(self):
        return str(self.__value__)
    
    def __json__(self):
        return self.__dict__


class StructJSONEncoder(JSONEncoder):
    def default(self, x):
        if isinstance(x, Struct):
            return dict(__JSON_Struct__=x.__json__())
        elif isinstance(x, Feature):
            return dict(__JSON_Feature__=x.__json__())
        else:
            return JSONEncoder.default(self, x)
    
    @staticmethod
    def as_struct(x):
        if '__JSON_Struct__' in x:
            return Struct(x['__JSON_Struct__'])
        elif '__JSON_Feature__' in x:
            return Feature(x['__JSON_Feature__'])
        else:
            return x
            
    
def as_featurestruct(root_desc, seq):
    features = dict()
    for slot_desc in seq:
        slot = FeatureDesc(*slot_desc)
        features.setdefault(slot.parent, FeatureStruct())[slot.role] = Feature(__type__=slot.type,
                                                                               __index__=slot.index,
                                                                               __typesystem__=slot.typesystem,
                                                                               __value__=slot.value,
                                                                               __features__=features) 
    root = FeatureDesc(*root_desc)
    return Feature(__type__=root.type,
                   __index__=root.index,
                   __typesystem__=root.typesystem,
                   __value__=root.value,
                   __features__=features)
        

    
    