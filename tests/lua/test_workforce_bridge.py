"""Exercise the shipped native workforce reader with real LuaJIT FFI structures."""
from pathlib import Path
from lupa.luajit21 import LuaRuntime

ROOT=Path(__file__).resolve().parents[2]/'src'
lua=LuaRuntime()
lua.execute(r'''
local ffi=require('ffi')
ffi.cdef[[
typedef struct {const char* type;const char* name;float value;bool active;} UIWorkforceInfluence;
typedef struct {uint32_t numcapacityinfluences;uint32_t numgrowthinfluences;} WorkforceInfluenceCounts;
typedef struct {
uint32_t numcapacityinfluences;uint32_t numgrowthinfluences;
UIWorkforceInfluence* capacityinfluences;UIWorkforceInfluence* growthinfluences;
float basegrowth;uint32_t capacity;uint32_t current;uint32_t sustainable;uint32_t target;int32_t change;
} WorkforceInfluenceInfo;
]]
fill,invalid,fail,badcounts=false,false,false,false
request={7,{{42,{{1,'argon'},{2,'boron'}},9,60,90}}}
local C={
GetPlayerID=function() return 1 end,
IsValidComponent=function(id) return not invalid and id==42 end,
GetNumContainerWorkforceInfluence=function(id,race,force)
 assert(id==42 and force)
 return {numcapacityinfluences=badcounts and 5000 or 1,numgrowthinfluences=0}
end,
GetContainerWorkforceInfluence=function(buf,id,race)
 if fail then error('native unavailable') end
 assert(buf.numcapacityinfluences==1 and buf.numgrowthinfluences==0)
 buf.capacity=1000;buf.sustainable=800;buf.target=600;buf.change=race=='argon' and 20 or -10
end,
ShouldContainerFillWorkforceCapacity=function() return fill end,
}
package.loaded.ffi={C=C,new=ffi.new,cdef=ffi.cdef}
ConvertStringTo64Bit=tonumber
GetNPCBlackboard=function(id,key) assert(id==1 and key=='$ce_workforce_request');return request end
SetNPCBlackboard=function(id,key,value) assert(id==1 and key=='$ce_workforce_response');response=value end
AddUITriggeredEvent=function(screen,control) assert(screen=='CEWorkforce' and control=='ready');signals=(signals or 0)+1 end
RegisterEvent=function(event,fn) assert(event=='CEWorkforceRequest');callback=fn end
''')
lua.execute((ROOT/'ui/ce_workforce.lua').read_text())
lua.execute('''
callback();assert(response[1]==7 and #response[2]==1 and #response[2][1][2]==2)
local rows=response[2][1][2]
assert(rows[1][1]==1 and rows[1][2]==1000 and rows[1][3]==800 and rows[1][4]==600 and rows[1][5]==20)
assert(rows[2][5]==-10)
fill=true;callback();assert(response[2][1][2][1][4]==1000)
fail=true;callback();assert(#response[2][1][2]==0);fail=false
badcounts=true;callback();assert(#response[2][1][2]==0);badcounts=false
invalid=true;callback();assert(#response[2]==0);invalid=false
request=nil;local before=signals;callback();assert(signals==before)
''')
print('Workforce bridge: native limits, races, fill target, failed reads and bounds passed')
