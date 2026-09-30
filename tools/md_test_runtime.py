"""Small interpreter for CE calculation actions, NOT an X4 engine emulator.
Only arithmetic/state/list actions are supported; engine actions fail unless explicitly stubbed.
"""
import re
from pathlib import Path
from lxml import etree as E
from md_expressions import compile_expression, normalize_path

class Missing:
    def __deepcopy__(self, memo): return self
    def __bool__(self): return False
    def __getattr__(self, key): return False if key == 'exists' else (0 if key == 'count' else self)
    def __getitem__(self, key): return self
NIL = Missing()

class ActionReturn(Exception):
    def __init__(self,value): self.value=value

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

class PseudoValue:
    """Native property path intermediate; cannot be saved as an MD value."""
    pass


class Angle(float):
    """Degrees in fixtures; preserve angle type for the observed modulo error.

    This narrow arithmetic contract is not a complete native units model.
    """
    def __add__(self, other): return Angle(float(self) + float(other))
    def __radd__(self, other): return Angle(float(other) + float(self))
    def __sub__(self, other): return Angle(float(self) - float(other))
    def __rsub__(self, other): return Angle(float(other) - float(self))
    def __abs__(self): return Angle(abs(float(self)))
    def __mod__(self, other): raise TypeError('Native angles do not support modulo')
    def __rmod__(self, other): raise TypeError('Native angles do not support modulo')


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

class Component(Table):
    __hash__=object.__hash__
    def __eq__(self,other): return self is other
    def __ne__(self,other): return self is not other

class Station(Component):
    """Station component properties are readable, but have no entity blackboard."""
    pass

class List(list):
    @property
    def min(self): return min(self)
    @property
    def max(self): return max(self)
    @property
    def random(self): return self[1] if self else NIL
    @property
    def list(self): return self
    @property
    def count(self): return len(self)
    @property
    def clone(self): return List(self)
    @property
    def indexof(self):
        source=self
        class Index:
            def __getitem__(self, value):
                return next((i for i,x in enumerate(source,1) if x == value),0)
        return Index()
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

class BreakLoop(Exception):
    pass


class Runner:
    def __init__(self):
        root = Path(__file__).resolve().parents[1] / 'md'
        self.scripts = {}
        for path in sorted(root.glob('*.xml')):
            tree = E.parse(str(path))
            self.scripts[tree.getroot().get('name')] = tree
        self.tree = self.scripts['CE_CivilianHub']
        self.profiles = self.scripts['CE_PopulationProfiles']
        self.construction = self.scripts['CE_Construction']
        self.reserves = self.scripts['CE_Reserves']
        self.trade = self.scripts['CE_Trade']
        self.env={'player':Table(age=0), 'null':NIL, 'true':True, 'false':False}
        self.env['md']=Table({name:Table({cue.get('name'):Table() for cue in tree.xpath('//cue')})
                              for name,tree in self.scripts.items()})
        self.env['datatype']=Table(list=DataType('list'),table=DataType('table'))
        self.stubs={}
        self.native={}
        self.signals=[]
        self.continue_on_invalid_key=False
        self.engine_errors=[]
    def path(self,s):
        return normalize_path(s)
    def expr(self,s):
        s=s.strip()
        if re.search(r'@\$?\w+(?:\.\$?\w+|\.\{[^{}]*\})*\?', s):
            raise ValueError('MD @ cannot be combined with ?')
        if re.search(r'\.keys$', s):
            raise ValueError('MD table keys require .keys.list to obtain a list')
        if s.startswith('table['):
            return Table({k.strip().lstrip('$'):self.expr(v) for k,v in (x.split('=',1) for x in split(s[6:-1]))})
        if s.startswith('if '):
            cond,rest=s[3:].split(' then ',1); a,b=rest.split(' else ',1)
            return self.expr(a if self.expr(cond) else b)
        formatted = re.fullmatch(r"'([^']*)'\.\[(.*)\]", s)
        if formatted:
            args=[self.expr(arg) for arg in split(formatted[2])]
            return re.sub(r'%([1-9]\d*)', lambda m: str(args[int(m[1])-1]), formatted[1])
        # Literal text references are not expressions. Dynamic IDs use readtext.
        for text_id in re.findall(r'\{\d+,([^}]+)\}', s):
            if not text_id.strip().isdigit():
                raise ValueError('Literal text references require constant integer IDs')
        textref = re.fullmatch(r'\{(\d+),(\d+)\}(?:\.\[(.*)\])?', s)
        if textref:
            return (int(textref[1]), self.expr(textref[2]),
                    tuple(self.expr(arg) for arg in split(textref[3] or '')))
        code = compile_expression(s)
        return wrap(eval(code, {'__builtins__':{},'Angle':Angle,'List':List,'min':min,'max':max,'abs':abs,'int':int,'float':float,'datatype_of':datatype_of,'defined':lambda x:x is not NIL},self.env))
    def set(self,path,v,remove=False):
        if isinstance(v, PseudoValue):
            raise ValueError('Native pseudo-values cannot be stored; read a property directly')
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
        if isinstance(obj, Station):
            raise ValueError('Station components cannot store MD blackboard variables')
        if remove: del obj[key]
        else: obj[key]=wrap(v)
    def library(self,name):
        local_name = name.removeprefix('md.CE_CivilianHub.')
        if name in self.stubs: return self.stubs[name]()
        if local_name in self.stubs: return self.stubs[local_name]()
        script = name.split('.')[1] if name.startswith('md.') else 'CE_CivilianHub'
        tree = self.scripts[script]
        nodes=tree.xpath('//library[@name=$n]/actions',n=name.rsplit('.',1)[-1])
        if not nodes: raise ValueError(name)
        self.actions(nodes[0])
    def run_actions(self,name,params):
        script=name.split('.')[1] if name.startswith('md.') else 'CE_CivilianHub'
        node=self.scripts[script].xpath('//library[@name=$name]',name=name.rsplit('.',1)[-1])[0]
        caller=self.env
        self.env=dict(caller)
        try:
            for param in node.findall('params/param'):
                key=param.get('name')
                self.env[key]=params[key] if key in params else self.expr(param.get('default','null'))
            try: self.actions(node.find('actions'))
            except ActionReturn as result: return result.value
            return NIL
        finally: self.env=caller
    def actions(self,nodes):
        branch=False
        for n in nodes:
            tag=n.tag
            if not isinstance(tag,str): continue
            if tag=='set_value':
                val=self.expr(n.get('exact','1'))
                if n.get('min') is not None:
                    low,high=self.expr(n.get('min')),self.expr(n.get('max'))
                    assert low <= high
                    # Deterministic sample; individual tests can exercise both bounds.
                    val=low+(high-low)*getattr(self,'random_fraction',0.5)
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
                for i,item in enumerate(items):
                    self.set(n.get('name'),item)
                    if n.get('counter'):self.set(n.get('counter'),len(items)-i if n.get('reverse')=='true' else i+1)
                    try:self.actions(n)
                    except BreakLoop:break
            elif tag=='do_all':
                for i in range(int(self.expr(n.get('exact')))):
                    if n.get('counter'): self.set(n.get('counter'),i+1)
                    try:self.actions(n)
                    except BreakLoop:break
            elif tag=='do_while':
                count=0
                while self.expr(n.get('value')):
                    self.actions(n);count+=1
                    if count>10000:raise RuntimeError('loop guard')
            elif tag=='include_actions': self.library(n.get('ref'))
            elif tag=='break': raise BreakLoop()
            elif tag=='run_actions':
                params={p.get('name'):self.expr(p.get('value')) for p in n.findall('param')}
                result=self.run_actions(n.get('ref'),params)
                if n.get('result'):self.set(n.get('result'),result)
            elif tag=='return' and tag not in self.native: raise ActionReturn(self.expr(n.get('value','null')))
            elif tag in ('signal_cue','signal_cue_instantly') and tag not in self.native:
                self.signals.append((n.get('cue'),self.expr(n.get('param','null'))))
            elif tag=='append_to_list': self.expr(n.get('name')).append(self.expr(n.get('exact')))
            elif tag=='append_list_elements': self.expr(n.get('name')).extend(self.expr(n.get('other')))
            elif tag=='remove_value': self.set(n.get('name'),None,remove=True)
            elif tag=='clear_table': self.expr(n.get('table')).clear()
            elif tag=='debug_text':
                if tag in self.native: self.native[tag](n)
            elif tag in self.native: self.native[tag](n)
            else: raise NotImplementedError(tag)
