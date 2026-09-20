"""Execute the live-population Lua adapter against native API mocks."""
from pathlib import Path
from lupa.luajit21 import LuaRuntime
lua=LuaRuntime()
lua.execute('''
request={7,{10,11,12,13,14}}
populations={[10]=8524100000,[11]=0,[12]=10000,[13]=18000000000}
events=0; errors=0
package.loaded.ffi={cdef=function() end,C={
 GetPlayerID=function() return 1 end,
 IsValidComponent=function(id) return id~=14 end,
 GetSectorPopulation=function(id) return populations[id] end}}
ConvertStringTo64Bit=tonumber
GetNPCBlackboard=function(_,key) assert(key=='$ce_population_request');return request end
SetNPCBlackboard=function(_,key,data) assert(key=='$ce_population_response');response=data end
AddUITriggeredEvent=function(screen,control) assert(screen=='CEPopulation' and control=='ready');events=events+1 end
DebugError=function() errors=errors+1 end
RegisterEvent=function(name,callback) assert(name=='CEPopulationRequest');run=callback end
''')
lua.execute((Path(__file__).parents[1]/'ui/ce_population.lua').read_text())
lua.execute('''
run();assert(response[1]==7 and #response[2]==4 and events==1 and errors==1)
assert(response[2][2][2]==0 and response[2][4][2]==18000000000)
request={8,{12}};populations[12]=20000;run();assert(response[1]==8 and response[2][1][2]==20000)
request={9,{12}};populations[12]=nil;run();assert(#response[2]==0)
request=nil;run();assert(events==3)
''')
print('Population bridge: zero, small, large, changing and failed readings passed')
