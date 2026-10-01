// STAGED ONLY: never point the output at the installed game while it is running.
EnsureDataLoaded();
var group = new UndertaleModLib.Compiler.CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
var root = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), "game-module") + System.IO.Path.DirectorySeparatorChar;
group.QueueReplace("gml_Script_scr_ucc6_emit", System.IO.File.ReadAllText(root + "monitor-v6-emit.gml"));
group.QueueReplace("gml_Script_scr_ucc6_value", System.IO.File.ReadAllText(root + "monitor-v6-value.gml"));
group.QueueReplace("gml_Script_scr_ucc6_step", System.IO.File.ReadAllText(root + "monitor-v6-step.gml"));
group.QueueAppend(Data.Code.ByName("gml_Object_obj_time_Create_0"), @"
ucc6_prev=ds_map_create(); ucc6_seen=ds_map_create(); ucc6_types=ds_map_create(); ucc6_frame=0;
ucc6_keys[0]=""""; ucc6_keycount=0;
ucc6_cycle=0; ucc6_phase=0;
ucc6_interval=1000;ucc6_next_scan=0;
ucc6_builtins=[""x"",""y"",""xprevious"",""yprevious"",""xstart"",""ystart"",""speed"",""hspeed"",""vspeed"",""direction"",""gravity"",""gravity_direction"",""friction"",""sprite_index"",""image_index"",""image_speed"",""image_xscale"",""image_yscale"",""image_angle"",""image_alpha"",""image_blend"",""visible"",""solid"",""persistent"",""depth"",""mask_index"",""path_index"",""path_position"",""path_speed""];
ucc6_buffer=""E|6""+chr(10); ucc6_count=0; ucc6_skipped=0;
");
group.QueueAppend(Data.Code.ByName("gml_Object_obj_time_Step_1"), "scr_ucc6_step();");
group.Import();
ScriptMessage("Staged V6: dynamic globals, instance variables, arrays, built-ins and deletions; no gameplay writes.");
