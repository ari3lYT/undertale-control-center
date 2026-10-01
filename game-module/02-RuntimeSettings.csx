EnsureDataLoaded();
var root = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), "game-module") + System.IO.Path.DirectorySeparatorChar;
var group = new UndertaleModLib.Compiler.CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
var context = new UndertaleModLib.Decompiler.GlobalDecompileContext(Data);
string Decompile(string name) => new Underanalyzer.Decompiler.DecompileContext(context, Data.Code.ByName(name), Data.ToolInfo.DecompilerSettings).DecompileToString();
var create = Decompile("gml_Object_obj_time_Create_0");
if (create.Contains("ucc_settings_poll")) throw new Exception("V4 is already installed; do not duplicate hooks");
create += @"
ucc_settings_poll = 15;
global.ucc_wasd = 1;
global.ucc_zxc = 1;
global.ucc_inputlog = 1;
ucc_lastchoice = -999;
for (var k = 0; k < 256; k += 1) { ucc_keys[k] = 0; ucc_pads[k] = 0; }
for (var k = 0; k < 4; k += 1) ucc_mouse[k] = 0;
for (var k = 0; k < 7; k += 1) ucc_mapped[k] = 0;
";
var step = Decompile("gml_Object_obj_time_Step_1");
var start = step.IndexOf("if (global.debug == 0)\n{\n    if (keyboard_check(ord(\"W\")))");
var end = step.IndexOf("if (variable_global_exists(\"plot\") && variable_global_exists(\"flag\")", start);
if (start < 0 || end < start) throw new Exception("Input/bridge anchors changed; refusing unsafe patch");
var mapping = "";
var inputs = new[] {"W","A","S","D","Z","X","C"};
var outputs = new[] {"vk_up","vk_left","vk_down","vk_right","vk_enter","vk_shift","vk_control"};
for (int i=0;i<7;i++) {
 var enabled = i<4 ? "global.ucc_wasd && global.debug == 0" : "global.ucc_zxc";
 mapping += $"\nif ({enabled} && keyboard_check_direct(ord(\"{inputs[i]}\")) && window_has_focus()) {{ keyboard_key_press({outputs[i]}); ucc_mapped[{i}] = 1; }}\nelse if (ucc_mapped[{i}] == 1) {{ if (!keyboard_check_direct({outputs[i]})) keyboard_key_release({outputs[i]}); ucc_mapped[{i}] = 0; }}\n";
}
step = System.IO.File.ReadAllText(root+"RuntimeSettings.gml") + "\n" + step.Substring(0,start) + mapping + step.Substring(end);
var ack=step.IndexOf("\"A|\"");
if(ack<0) throw new Exception("Missing acknowledgement anchor");
var ackLine=step.LastIndexOf('\n',ack)+1;
step=step.Insert(ackLine,@"
                if (ucc_kind == 3 && ucc_value >= 0 && ucc_value <= 4)
                {
                    if (room == room_tundra_sanshouse)
                    {
                        global.shrine = ucc_value;
                        ossafe_ini_open(""config.ini"");
                        ini_write_real(""General"", ""ds"", global.shrine);
                        ossafe_ini_close();
                        ossafe_savedata_save();
                        room_restart();
                    }
                    else ucc_kind = -3;
                }
");
group.QueueReplace(Data.Code.ByName("gml_Object_obj_time_Create_0"),create);
group.QueueReplace(Data.Code.ByName("gml_Object_obj_time_Step_1"),step);
group.Import();
ScriptMessage("V4: runtime settings, raw game input transitions, legacy unsafe hot callbacks removed.");
