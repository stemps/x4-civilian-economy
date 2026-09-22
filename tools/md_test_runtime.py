"""Small interpreter for CE calculation actions, NOT an X4 engine emulator.
Only arithmetic/state/list actions are supported; engine actions fail unless explicitly stubbed.
"""
import re
from pathlib import Path
from lxml import etree as E

class Missing:
    def __deepcopy__(self, memo): return self
    def __bool__(self): return False
    def __getattr__(self, key): return False if key == 'exists' else (0 if key == 'count' else self)
    def __getitem__(self, key): return self
NIL = Missing()

class DataType(str):
    @property
    def isnumeric(self): return self in ('integer','float')
    @property
    def isstring(self): return self == 'string'

def datatype_of(value):
    if isinstance(value,List):return DataType('list')
    if isinstance(value,Table):return DataType('table')
    if type(value) is int:return DataType('integer')
    if type(value) is float:return DataType('float')
    if type(value) is str:return DataType('string')
    return DataType('other')

class Table(dict):
    # Fixture attribute writes must affect the same table seen by MD paths.
    def __setattr__(self, key, value): self[key] = value
    @property
    def keys(self): return List(list(self))
    def __getattr__(self, key):
        if key.startswith('__'): raise AttributeError(key)
        if key == 'count': return len(self)
        if key == 'keys': return List(list(self))
        return self.get(key, NIL)
    def __getitem__(self, key): return self.get(key, NIL)
    def __bool__(self): return True

class List(list):
    @property
    def list(self): return self
    @property
    def count(self): return len(self)
    def __getitem__(self, key):
        if isinstance(key, slice): return super().__getitem__(key)
        return super().__getitem__(key - 1) if 1 <= key <= len(self) else NIL
    def __setitem__(self, key, value): super().__setitem__(key - 1, value)
    def __delitem__(self, key): super().__delitem__(key - 1)

def wrap(v):
    if isinstance(v, (Table, List, Missing)): return v
    if isinstance(v, dict): return Table({k:wrap(x) for k,x in v.items()})
    if isinstance(v, list): return List([wrap(x) for x in v])
    return v

def split(s):
    start=depth=0
    for i,c in enumerate(s):
        if c in '[({': depth += 1
        elif c in '])}': depth -= 1
        elif c == ',' and depth == 0:
            yield s[start:i]; start=i+1
    if s[start:]: yield s[start:]

class Runner:
    def __init__(self):
        self.tree=E.parse(str(Path(__file__).resolve().parents[1]/'md/ce_ownerless_hub.xml'))
        self.profiles=E.parse(str(Path(__file__).resolve().parents[1]/'md/ce_population_profiles.xml'))
        self.reserves=E.parse(str(Path(__file__).resolve().parents[1]/'md/ce_reserves.xml'))
        self.env={'player':Table(age=0), 'null':NIL, 'true':True, 'false':False}
        self.env['datatype']=Table(list=DataType('list'),table=DataType('table'))
        self.stubs={}
        self.native={}
        self.continue_on_invalid_key=False
        self.engine_errors=[]
    def path(self,s):
        # Variable sigils are syntax; sigils inside string keys are data.
        s=''.join(part if i % 2 else part.replace('$','').replace('@','')
                  for i,part in enumerate(re.split(r"('(?:[^'\\]|\\.)*')",s)))
        while '.{' in s: s=re.sub(r'\.\{([^{}]+)\}',r'[\1]',s)
        return s
    def expr(self,s):
        s=s.strip()
        if re.search(r'\.keys$', s):
            raise ValueError('MD table keys require .keys.list to obtain a list')
        if s.startswith('table['):
            return Table({k.strip().lstrip('$'):self.expr(v) for k,v in (x.split('=',1) for x in split(s[6:-1]))})
        if s.startswith('if '):
            cond,rest=s[3:].split(' then ',1); a,b=rest.split(' else ',1)
            return self.expr(a if self.expr(cond) else b)
        s=self.path(s)
        s=re.sub(r'typeof (\w+(?:\.[\w]+|\[[^\]]+\])*)',r'datatype_of(\1)',s)
        s=re.sub(r'(\w+(?:\.[\w]+|\[[^\]]+\])*)\?',r'defined(\1)',s)
        s=re.sub(r'\(([^()]*)\)i',r'int(\1)',s)
        s=re.sub(r'(\d+(?:\.\d+)?)f\b',r'\1',s)
        for unit,scale in [('min',60),('km',1000),('m',1),('Cr',100),('h',3600),('s',1)]:
            s=re.sub(r'(\d+(?:\.\d+)?)'+unit+r'\b',lambda m:str(float(m[1])*scale),s)
        for md,py in [(' ge ',' >= '),(' le ',' <= '),(' gt ',' > '),(' lt ',' < ')]: s=s.replace(md,py)
        while re.search(r'\[([^\[\]]+)\]\.(min|max)',s):
            s=re.sub(r'\[([^\[\]]+)\]\.(min|max)',r'\2(\1)',s)
        return wrap(eval(s, {'__builtins__':{},'min':min,'max':max,'int':int,'datatype_of':datatype_of,'defined':lambda x:x is not NIL},self.env))
    def set(self,path,v,remove=False):
        path=self.path(path)
        # Last field/index is the target; everything before it is an expression.
        if path.endswith(']'):
            base,key=path.rsplit('[',1); obj=self.expr(base); key=self.expr(key[:-1])
            if base.startswith('Profile') and type(key) is str and not key.startswith('$'):
                if self.continue_on_invalid_key:
                    self.engine_errors.append('invalid string key: '+key)
                    return
                raise ValueError('MD string table keys require a $ prefix: '+key)
        elif '.' in path:
            base,key=path.rsplit('.',1); obj=self.expr(base)
        else: obj=self.env; key=path
        if remove: del obj[key]
        else: obj[key]=wrap(v)
    def library(self,name):
        if name in self.stubs: return self.stubs[name]()
        tree = self.reserves if name.startswith('md.CE_Reserves.') else self.profiles if name.startswith('md.CE_PopulationProfiles.') else self.tree
        nodes=tree.xpath('//library[@name=$n]/actions',n=name.rsplit('.',1)[-1])
        if not nodes: raise ValueError(name)
        self.actions(nodes[0])
    def actions(self,nodes):
        branch=False
        for n in nodes:
            tag=n.tag
            if not isinstance(tag,str): continue
            if tag=='set_value':
                val=self.expr(n.get('exact','1'))
                if n.get('operation')=='add': val=self.expr(n.get('name'))+val
                self.set(n.get('name'),val)
            elif tag=='do_if':
                branch=bool(self.expr(n.get('value')))
                if branch:self.actions(n)
            elif tag=='do_elseif':
                if not branch:
                    branch=bool(self.expr(n.get('value')))
                    if branch:self.actions(n)
            elif tag=='do_else':
                if not branch:self.actions(n)
                branch=True
            elif tag=='do_for_each':
                items=list(self.expr(n.get('in')))
                if n.get('reverse')=='true':items.reverse()
                for item in items:self.set(n.get('name'),item);self.actions(n)
            elif tag=='do_all':
                for i in range(int(self.expr(n.get('exact')))):
                    if n.get('counter'): self.set(n.get('counter'),i+1)
                    self.actions(n)
            elif tag=='do_while':
                count=0
                while self.expr(n.get('value')):
                    self.actions(n);count+=1
                    if count>10000:raise RuntimeError('loop guard')
            elif tag=='include_actions': self.library(n.get('ref'))
            elif tag=='append_to_list': self.expr(n.get('name')).append(self.expr(n.get('exact')))
            elif tag=='remove_value': self.set(n.get('name'),None,remove=True)
            elif tag=='clear_table': self.expr(n.get('table')).clear()
            elif tag=='debug_text': pass
            elif tag in self.native: self.native[tag](n)
            else: raise NotImplementedError(tag)
