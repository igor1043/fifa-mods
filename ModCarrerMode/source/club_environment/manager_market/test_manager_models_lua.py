"""Exercise the installed resolver using an actual Lua 5.1 shared library.
Set LUA51_DLL to an independently built unmodified Lua 5.1 x64 DLL.
"""
from pathlib import Path
import ctypes,os,unittest

@unittest.skipUnless(os.environ.get('LUA51_DLL'),'Set LUA51_DLL for real Lua 5.1 tests')
class ManagerLuaTest(unittest.TestCase):
 def test_model_texture_weather_pair_and_noncareer_delegation(self):
  d=ctypes.CDLL(os.environ['LUA51_DLL']);d.luaL_newstate.restype=ctypes.c_void_p;d.luaL_openlibs.argtypes=[ctypes.c_void_p];d.luaL_loadstring.argtypes=[ctypes.c_void_p,ctypes.c_char_p];d.lua_pcall.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int];d.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)];d.lua_tolstring.restype=ctypes.c_char_p;d.lua_close.argtypes=[ctypes.c_void_p];L=d.luaL_newstate();d.luaL_openlibs(L)
  def run(code):
   error=d.luaL_loadstring(L,code.encode()) or d.lua_pcall(L,0,0,0)
   if error:self.fail(d.lua_tolstring(L,-1,None).decode())
  try:
   run("db={sle={[1]={sletype=10,teamid=1629,cold=0},[2]={sletype=11,teamid=383,cold=1},[3]={sletype=14,teamid=1629},[4]={sletype=1,teamid=1629}}};function GetRMSle(i,m) return 'original:'..i..':'..m end")
   helper=Path(__file__).with_name('manager_models.lua').read_text();run(helper)
   run("assert(GetRMSle(1,0)=='original:1:0');mode=-1;function FIFA16_Career_Manager_Asset(club) return mode end;assert(GetRMSle(1,0)=='original:1:0');mode=0;assert(GetRMSle(1,0)=='');assert(GetRMSle(1,1)=='');mode=14;assert(GetRMSle(1,0)=='data/sceneassets/manager_market/14/model_0.rx3;');assert(GetRMSle(1,1)=='data/sceneassets/manager_market/14/model_0_textures.rx3;');assert(GetRMSle(2,0)=='data/sceneassets/manager_market/14/model_1.rx3;');assert(GetRMSle(2,1)=='data/sceneassets/manager_market/14/model_1_textures.rx3;');assert(GetRMSle(3,0)=='original:3:0');assert(GetRMSle(4,1)=='original:4:1');mode=-1;assert(GetRMSle(2,0)=='original:2:0')")
   embedded=Path(__file__).resolve().parents[4]/'data/fifarna/lua/assets/sle.lua';self.assertTrue(embedded.read_text(encoding='utf8').rstrip().endswith(helper.rstrip()))
  finally:d.lua_close(L)

if __name__=='__main__':unittest.main()
