EnsureDataLoaded();
var ctx = new UndertaleModLib.Decompiler.GlobalDecompileContext(Data);
string Read(string n) => new Underanalyzer.Decompiler.DecompileContext(ctx, Data.Code.ByName(n), Data.ToolInfo.DecompilerSettings).DecompileToString();
var g = new UndertaleModLib.Compiler.CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
var step = Read("gml_Object_obj_time_Step_1");
var begin = step.IndexOf("if (global.ucc_wasd && global.debug == 0 && keyboard_check_direct(ord(\"W\"))");
var end = step.IndexOf("if (variable_global_exists(\"plot\")", begin);
if (begin < 0 || end < begin || step.Contains("ucc_wasd_mapping")) throw new Exception("Expected V4 input block not found");
step = step.Remove(begin, end-begin);
var mapping = @"
// Native key aliases: no synthetic held arrows or Enter/Shift/Ctrl.
var ucc_use_wasd = global.ucc_wasd && global.debug == 0;
if (ucc_use_wasd != ucc_wasd_mapping)
{
    for (var ucc_i = 0; ucc_i < 4; ucc_i += 1)
    {
        keyboard_clear(ucc_wasd_keys[ucc_i]);
        keyboard_clear(ucc_wasd_targets[ucc_i]);
        if (ucc_use_wasd) keyboard_set_map(ucc_wasd_keys[ucc_i], ucc_wasd_targets[ucc_i]);
        else keyboard_set_map(ucc_wasd_keys[ucc_i], ucc_wasd_original[ucc_i]);
    }
    ucc_wasd_mapping = ucc_use_wasd;
}
";
if (!step.Contains("control_update();")) throw new Exception("Missing native input anchor");
step = step.Replace("control_update();", mapping + "\ncontrol_update();");
var create = Read("gml_Object_obj_time_Create_0") + @"
ucc_wasd_mapping = -1;
ucc_wasd_keys[0] = ord(""W""); ucc_wasd_targets[0] = vk_up;
ucc_wasd_keys[1] = ord(""A""); ucc_wasd_targets[1] = vk_left;
ucc_wasd_keys[2] = ord(""S""); ucc_wasd_targets[2] = vk_down;
ucc_wasd_keys[3] = ord(""D""); ucc_wasd_targets[3] = vk_right;
for (var ucc_i = 0; ucc_i < 4; ucc_i += 1)
    ucc_wasd_original[ucc_i] = keyboard_get_map(ucc_wasd_keys[ucc_i]);
";
var controls = Read("gml_Script_control_update");
foreach(var key in new[]{"Z","X","C"}) {
    var match = "keyboard_check(ord(\""+key+"\"))";
    if (!controls.Contains(match)) throw new Exception("Missing native control " + key);
    controls = controls.Replace(match,"(global.ucc_zxc && " + match + ")");
}
g.QueueReplace(Data.Code.ByName("gml_Object_obj_time_Create_0"), create);
g.QueueReplace(Data.Code.ByName("gml_Object_obj_time_Step_1"), step);
g.QueueReplace(Data.Code.ByName("gml_Script_control_update"), controls);
g.Import();
ScriptMessage("V5 native WASD aliases; native ZXC control state; no synthetic key latch.");
