"""Exercise the supplied VTL Lua source with CE's event contract and native mocks.

Receipt naming is user-verified; ware Detail rendering still needs an in-game test.
"""
from pathlib import Path
import sys
from lxml import etree
from lupa.luajit21 import LuaRuntime

root = Path(__file__).resolve().parents[2] / 'src'
mod = Path(sys.argv[1])
manifest = etree.parse(str(mod / 'content.xml'))
assert manifest.getroot().get('id') == 'VerboseTransactionLog'
trade = etree.parse(str(root / 'md/ce_trade.xml'))
transaction_log = etree.parse(str(root / 'md/ce_transaction_log.xml'))
event, = transaction_log.xpath('//raise_lua_event[contains(@param,"{974201,155}")]')
assert event.get('param') == "$SalesTaxPaid + ';' + {974201,155}.[$R.$Hub.sector.knownname]"
assert event.getparent().get('value') == '$SalesTaxPaid gt 0Cr'
label, = etree.parse(str(root / 't/0001-l044.xml')).xpath('//t[@id="155"]/text()')
delivery_event, = transaction_log.xpath('//raise_lua_event[@name="\'CEVTLDelivery\'"]')
assert delivery_event.get('param') is None
assert delivery_event.xpath('ancestor::library/@name') == ['PublishPayment']
assert trade.xpath('//cue[@name="DeliveryAccountPaid"]/actions/include_actions/@ref') == ['md.CE_TransactionLog.PublishPayment']
assert not transaction_log.xpath('//library[@name="PublishPayment"]//raise_lua_event[@name="\'transfer_money\'"]')
delivery_label, = etree.parse(str(root / 't/0001-l044.xml')).xpath('//t[@id="156"]/text()')

lua = LuaRuntime()
lua.execute('''
nativeffi = require('ffi')
events = {}; callbacks = {}; now = 100; saved = nil
package.loaded.ffi = { C = {
    GetPlayerID = function() return 1 end,
    GetCurrentGameTime = function() return now end,
}}
ConvertStringTo64Bit = tonumber
RegisterEvent = function(name, fn)
    local previous = events[name]
    if name == 'mvtl.onGameLoad' and previous then
        events[name] = function(...) previous(...); fn(...) end
    else events[name] = fn end
end
Helper = {registerCallback = function(name, fn, id)
    if id == 'CEWareDetail' then detailCallback = fn else callbacks[name] = fn end
end}
GetNPCBlackboard = function(_, key)
    assert(key == '$verboseTransactionLog'); return saved
end
SetNPCBlackboard = function(_, key, value)
    assert(key == '$verboseTransactionLog'); saved = value
end
''')
source = (mod / 'ui/verbose_transaction_log.lua').read_text(encoding='utf-8-sig')
lua.execute(source)
lua.globals().ce_label = label.replace('%1', 'Grand Exchange I')
lua.globals().ce_delivery_label = delivery_label.replace('%1', 'Grand Exchange I')
lua.execute('''
events['mvtl.onGameLoad']()
local annotate = callbacks['createTransactionLog_on_before_adding_entry']
local emit = events['transfer_money']
local function entry(id, time, money)
    return {entryid=id, time=time, money=money,
        eventtypename='Mission reward', partnername='original'}
end
emit(nil, '924600;' .. ce_label)
emit(nil, '6164200;' .. ce_delivery_label)
local unrelated = annotate(entry(1, 99, 9246))
assert(unrelated.eventtypename == 'Mission reward')
local different = annotate(entry(2, 100, 42))
assert(different.eventtypename == 'Mission reward')
local delivery = entry(8, 100, 61642)
delivery.eventtypename = 'Incoming Transfer from Trade Order'
delivery.partnername = 'Heron E (SVI-685)'
delivery = annotate(delivery)
assert(delivery.eventtypename == ce_delivery_label and delivery.partnername == '')
local tax = annotate(entry(3, 100, 9246))
assert(tax.eventtypename == ce_label and tax.partnername == '')
assert(#saved.queue == 0 and saved.lookupTable[3].description == ce_label)
assert(annotate(entry(3,100,9246)).eventtypename == ce_label)

-- Distinct amounts at the same time can be visited in either order.
now = 110
emit(nil, '10000;Tax A'); emit(nil, '20000;Tax B')
assert(annotate(entry(5,110,200)).eventtypename == 'Tax B')
assert(annotate(entry(4,110,100)).eventtypename == 'Tax A')

-- The supplied module's blackboard survives its boot callback.
events['mvtl.onGameLoad']()
assert(annotate(entry(3,100,9246)).eventtypename == ce_label)

-- Known upstream limitation: matching cannot identify the source of two
-- equal payments at the same timestamp. Do not claim exact-ID correlation.
now = 120
emit(nil, '30000;Tax A'); emit(nil, '30000;Tax B')
assert(annotate(entry(6,120,300)).eventtypename == 'Tax B')
assert(annotate(entry(7,120,300)).eventtypename == 'Tax A')

-- Slot 4 reproduction: unloading/MD completion and personal-account payment
-- have different native timestamps. Old immediate emission cannot match.
now = 240858.740
emit(nil, '6164200;' .. ce_delivery_label)
local receipt = entry(9, 240859.741, 61642)
receipt.partnername = 'Heron E (SVI-685)'
assert(annotate(receipt).partnername == 'Heron E (SVI-685)')
-- Counterfactual exact-time emission demonstrates VTL's requirement. Actual
-- account notifications arrive late; the receipt-ID bridge below replaces this.
now = 240859.741
emit(nil, '6164200;' .. ce_delivery_label)
assert(annotate(receipt).eventtypename == ce_delivery_label)
assert(receipt.partnername == '')
''')
print(f"VTL {manifest.getroot().get('version')}: installed Lua accepts CE labels; "
      "unmatched entries, repeat reads, distinct simultaneous amounts and boot passed.")
print('Known limitation reproduced: equal simultaneous amounts are matched in reverse queue order.')

# Run the new bridge with the actual installed VTL, including its private cache.
lua.execute('''
local ffi = package.loaded.ffi
ffi.new = function() return {} end
ffi.string = function(s) return s end
local C = ffi.C
C.GetPlayerID = function() return nativeffi.new('uint64_t', 1) end
local function idnumber(s) return tonumber((tostring(s):gsub('ULL$', ''):gsub('LL$', ''))) end
ConvertStringTo64Bit = idnumber
ConvertStringToLuaID = idnumber
ConvertIDTo64Bit = function(id)
    assert(type(id) == 'number', 'blackboard seller must be a Lua ID')
    return nativeffi.new('uint64_t', id)
end
rows = {}; requests = nil; active = true; reads = 0; boots = 0
GetExtensionList = function() return {{id='VerboseTransactionLog',enabled=active}} end
GetNPCBlackboard = function(player, key)
    assert(type(player) == 'number' and player == 1, 'blackboard requires Lua ID')
    if key == '$ce_vtl_deliveries' then return requests end
    assert(key == '$verboseTransactionLog'); return saved
end
SetNPCBlackboard = function(player, key, data)
    assert(type(player) == 'number' and player == 1, 'blackboard requires Lua ID')
    if key == '$ce_vtl_deliveries' then requests = data; return end
    assert(key == '$verboseTransactionLog'); saved = data
end
CallEventScripts = function(name)
    assert(name == 'mvtl.onGameLoad'); boots = boots + 1; events[name]()
end
ReadText = function(page, id) assert(page == 974201 and id == 156); return 'Civilian hub delivery - %1' end
wareNames = {water='Water',food='Food'}
GetWareData = function(ware, field) assert(field == 'name'); return wareNames[ware] end
diagnostics = {}
DebugError = function(message) diagnostics[#diagnostics + 1] = message end
C.GetNumTransactionLog = function(player, start, finish)
    assert(type(player) == 'cdata' and tonumber(player) == 1, 'ledger requires native UniverseID')
    reads = reads + 1; return #rows
end
C.GetTransactionLog = function(buffer, count, player, start, finish)
    assert(type(player) == 'cdata' and tonumber(player) == 1, 'ledger requires native UniverseID')
    for i, row in ipairs(rows) do buffer[i-1] = row end
    return #rows
end
''')
bridge = (root / 'ui/ce_transaction_log.lua').read_text()
# Negative control: reproduce the old Lua-ID-to-native-query boundary error.
lua.execute(bridge.replace('pcall(receipt, nativePlayer, request)',
                           'pcall(receipt, player, request)'))
lua.execute('''
rows = {{entryid=900,partnerid=nativeffi.new('uint64_t',55),
         time=241001.752,money=6164200,eventtype='orderqueue_remove'}}
requests = {{55,61642,241000.736,241001.769,'Grand Exchange I'}}
events.CEVTLDelivery()
assert(saved.lookupTable[900] == nil)
''')
lua.execute(bridge)
lua.execute('''
local annotate = callbacks['createTransactionLog_on_before_adding_entry']
local function row(id, ship, time, money, kind)
    return {entryid=id, partnerid=nativeffi.new('uint64_t',ship), time=time, money=money, eventtype=kind or 'orderqueue_remove'}
end
local function request(ship, sector)
    return {ship,61642,240999.243,241000.271,sector or 'Grand Exchange I','water'}
end
local function display(id)
    return annotate({entryid=id,money=61642,time=241000.254,
        partnername='Heron E (SVI-685)',eventtypename='Incoming Transfer'})
end
-- Measured 17ms mismatch: store the native ID, then real VTL renders it.
rows = {row(100,55,241000.254,6164200)}; requests = {request(55)}
events.CEVTLDelivery()
assert(requests == nil and boots == 1)
assert(display(100).partnername == '' and display(100).eventtypename == ce_delivery_label)
events['mvtl.onGameLoad'](); assert(display(100).eventtypename == ce_delivery_label)
local function detail(id, kind, existing)
    return detailCallback({entryid=id,eventtype=kind or 'orderqueue_remove',
        ware='',warename=existing or ''})
end
assert(detail(100).warename == 'Water' and detail(100).ware == '')
assert(detail(100,'trade').warename == '')
assert(detail(100,nil,'Existing ware').warename == 'Existing ware')
assert(detail(999).warename == '')
wareNames.water = 'Wasser'; events['mvtl.onGameLoad']()
assert(detail(100).warename == 'Wasser'); wareNames.water = 'Water'
-- Both UIX callback orders preserve the name and Detail column.
for _, reverse in ipairs({false,true}) do
    local e = {entryid=100,eventtype='orderqueue_remove',money=61642,time=241000.254,
        partnername='Heron',eventtypename='Incoming Transfer',ware='',warename=''}
    if reverse then e=annotate(detailCallback(e)) else e=detailCallback(annotate(e)) end
    assert(e.eventtypename == ce_delivery_label and e.warename == 'Water' and e.ware == '')
end
-- Native trace: MD 51800 cents was incorrectly exported as 5.18 credits after
-- pre-division. Passing the untouched money value exports 518 credits instead.
rows = {row(110,35421905,241142.564408799,51800)}
requests = {{35421905,5.18,241141.547408399,241142.582986899,'Grand Exchange I'}}
events.CEVTLDelivery(); assert(saved.lookupTable[110] == nil)
requests = {{35421905,518,241141.547408399,241142.582986899,'Grand Exchange I'}}
events.CEVTLDelivery(); assert(display(110).eventtypename == ce_delivery_label)
-- Absent/disabled integration leaves both the native label and VTL data alone.
active = false; requests = {request(55)}; rows = {row(101,55,241000.254,6164200)}
events['mvtl.onGameLoad'](); assert(detail(100).warename == '')
local before = reads; events.CEVTLDelivery()
assert(reads == before and saved.lookupTable[101] == nil and requests == nil)
active = true
events['mvtl.onGameLoad']()
-- Equal amounts on different ships, including simultaneous deliveries, remain distinct.
rows = {row(102,55,241000.254,6164200), row(103,56,241000.254,6164200)}
requests = {request(55,'Sector A'),request(56,'Sector B')}; events.CEVTLDelivery()
assert(display(102).eventtypename == 'Civilian hub delivery - Sector A')
assert(display(103).eventtypename == 'Civilian hub delivery - Sector B')
-- Ambiguity, wrong ship/type/amount, partial receipts, stale requests all fail closed.
for _, bad in ipairs({
    {row(104,55,241000.254,6164200),row(105,55,241000.260,6164200)},
    {row(104,56,241000.254,6164200)},
    {row(104,55,241000.254,6164200,'script_add')},
    {row(104,55,241000.254,6164199)},
    {row(104,55,240998,6164200)},
    {row(104,55,241001,6164200)},
    {},
}) do
    rows = bad; requests = {request(55)}; events.CEVTLDelivery()
    assert(saved.lookupTable[104] == nil and saved.lookupTable[105] == nil)
end
rows = {row(104,55,241000.254,6164200)}
requests = {{55,61642,240900,241000.271,'Old sector'}}; events.CEVTLDelivery()
assert(saved.lookupTable[104] == nil)
saved.lookupTable[104] = {description='Another mod'}
requests = {request(55)}; events.CEVTLDelivery()
assert(saved.lookupTable[104].description == 'Another mod')
-- Native API failure remains a quiet no-op after troubleshooting cleanup.
local getnum = package.loaded.ffi.C.GetNumTransactionLog
package.loaded.ffi.C.GetNumTransactionLog = function() error('native query failed') end
requests = {request(55)}; events.CEVTLDelivery()
assert(#diagnostics == 0)
package.loaded.ffi.C.GetNumTransactionLog = getnum
-- Unsupported future saved-data formats are untouched.
saved = {unknown=true}; requests = {request(55)}; events.CEVTLDelivery()
assert(saved.unknown and saved.lookupTable == nil)
''')
print('CE receipt bridge + installed VTL: 17ms delay, persistence, optional fallback, ship identity, ambiguity and collision checks passed.')

# Fresh runtimes without loading VTL at all, with and without UI Extensions.
for has_uix in (False, True):
    absent = LuaRuntime()
    absent.globals().has_uix = has_uix
    absent.execute('''
local ffi = require('ffi')
package.loaded.ffi = {C = {
    GetPlayerID = function() return ffi.new('uint64_t',1) end,
    GetNumTransactionLog = function() error('must not query without VTL') end,
}}
ConvertStringToLuaID = function() return 1 end
GetExtensionList = function() return {{id='some_other_mod',enabled=true}} end
events = {}; request = {{55,518,100,101,'Grand Exchange I','water'}}
RegisterEvent = function(name, fn) events[name] = fn end
Helper = {}
if has_uix then Helper.registerCallback = function(_, fn) detail = fn end end
GetNPCBlackboard = function(player, key)
    assert(player == 1 and key == '$ce_vtl_deliveries', 'must not read VTL data')
    return request
end
SetNPCBlackboard = function(player, key, value)
    assert(player == 1 and key == '$ce_vtl_deliveries' and value == nil)
    request = nil
end
CallEventScripts = function() error('must not call VTL') end
DebugError = function() error('unexpected diagnostic') end
''')
    absent.execute(bridge)
    absent.execute('''
events.CEVTLDelivery(); assert(request == nil)
events.CEVTLDelivery() -- no pending request is also harmless
if has_uix then
    local entry = {entryid=1,eventtype='orderqueue_remove',partnername='Heron',warename='',ware=''}
    assert(detail(entry) == entry and entry.partnername == 'Heron' and entry.warename == '')
else assert(detail == nil) end
''')
print('VTL fully absent: fresh-runtime loading and delivery passed with and without UI Extensions; native labels preserved.')
