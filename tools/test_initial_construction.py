"""Initial completion requires fresh MD membership and an owned native build."""
from pathlib import Path
from lupa.luajit21 import LuaRuntime
lua=LuaRuntime()
lua.execute('''
calls, valid, owner, progress, waiting, allowed = 0, true, 'civilian', 0, false, {}
local C={GetPlayerID=function() return 1 end, IsValidComponent=function() return valid end,
 GetCurrentBuildProgress=function() return progress end,
 IsBuildWaitingForSecondaryComponentResources=function() return waiting end,
 ForceBuildCompletion=function(id) assert(id==42); calls=calls+1 end}
package.loaded.ffi={C=C,cdef=function() end}
CEHubStatus={id=tonumber}
ConvertStringToLuaID=tonumber
GetComponentData=function() return owner end
GetNPCBlackboard=function(id,key) assert(id==1 and key=='$ce_initial_build_hubs'); return allowed end
RegisterEvent=function(name,fn) assert(name=='CEInitialHubBuildReady'); callback=fn end
''')
lua.execute((Path(__file__).resolve().parents[1]/'ui/ce_initial_construction.lua').read_text())
lua.execute('''
callback(nil,42);assert(calls==0)
allowed={42};callback(nil,42);assert(calls==1)
callback(nil,43);assert(calls==1)
owner='player';callback(nil,42);assert(calls==1)
owner='civilian';valid=false;callback(nil,42);assert(calls==1)
valid=true;progress=-1;callback(nil,42);assert(calls==1)
waiting=true;callback(nil,42);assert(calls==2)
allowed={};callback(nil,42);assert(calls==2)
allowed=nil;callback(nil,42);assert(calls==2)
''')
print('Initial construction: fresh membership, owner, native readiness and revoked callbacks passed')
