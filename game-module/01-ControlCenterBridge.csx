// Additive bridge; never replaces the game's save/load or input scripts.
EnsureDataLoaded();
var group = new UndertaleModLib.Compiler.CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
var decompileContext = new UndertaleModLib.Decompiler.GlobalDecompileContext(Data);
string Decompile(string name) => new Underanalyzer.Decompiler.DecompileContext(decompileContext, Data.Code.ByName(name), Data.ToolInfo.DecompilerSettings).DecompileToString();
group.QueueAppend(Data.Code.ByName("gml_Object_obj_time_Create_0"), @"
ucc_ready = 0;
ucc_poll = 0;
ucc_seq = -1;
global.ucc_force_fun = -1;
");
group.QueueAppend(Data.Code.ByName("gml_Object_obj_time_Step_1"), @"
if (variable_global_exists(""plot"") && variable_global_exists(""flag"") && started == 1 && (instance_exists(obj_mainchara) || ucc_ready == 1))
{
    var ucc_out = """";
    if (ucc_ready == 0)
    {
        ucc_ready = 1;
        ucc_plot = global.plot;
        ucc_ticks = time;
        ucc_room = room;
        for (var ucc_i = 0; ucc_i < 512; ucc_i += 1) ucc_flags[ucc_i] = global.flag[ucc_i];
        ucc_out += ""S|"" + string(current_time) + ""|"" + string(time) + ""|"" + string(room) + ""|"" + string(global.plot) + chr(10);
    }
    if (global.plot != ucc_plot || time < ucc_ticks)
    {
        ucc_out += ""P|"" + string(current_time) + ""|"" + string(time) + ""|"" + string(room) + ""|"" + string(global.plot) + ""|"" + string(ucc_plot) + chr(10);
        ucc_plot = global.plot;
    }
    ucc_ticks = time;
    for (var ucc_i = 0; ucc_i < 512; ucc_i += 1)
    {
        if (ucc_flags[ucc_i] != global.flag[ucc_i])
        {
            ucc_out += ""F|"" + string(current_time) + ""|"" + string(time) + ""|"" + string(ucc_i) + ""|"" + string(ucc_flags[ucc_i]) + ""|"" + string(global.flag[ucc_i]) + chr(10);
            ucc_flags[ucc_i] = global.flag[ucc_i];
        }
    }
    ucc_poll += 1;
    if (ucc_poll >= 15)
    {
        ucc_poll = 0;
        ucc_out += ""H|"" + string(current_time) + ""|"" + string(time) + ""|"" + string(room) + ""|"" + string(global.plot) + ""|"" + string(global.inbattle) + ""|"" + string(global.interact) + chr(10);
        if (file_exists(""ucc-command.ini"") && global.inbattle == 0 && global.interact == 0 && instance_exists(obj_mainchara))
        {
            ini_open(""ucc-command.ini"");
            var ucc_newseq = ini_read_real(""command"", ""seq"", -1);
            var ucc_kind = ini_read_real(""command"", ""kind"", 0);
            var ucc_index = ini_read_real(""command"", ""index"", -1);
            var ucc_value = ini_read_real(""command"", ""value"", 0);
            ini_close();
            if (ucc_newseq != ucc_seq && ucc_newseq >= 0)
            {
                ucc_seq = ucc_newseq;
                file_delete(""ucc-command.ini"");
                if (ucc_kind == 1 && ucc_index >= 0 && ucc_index < 512)
                {
                    global.flag[ucc_index] = ucc_value;
                    if (ucc_index == 5)
                    {
                        ossafe_ini_open(""undertale.ini"");
                        ini_write_real(""General"", ""fun"", ucc_value);
                        ossafe_ini_close();
                    }
                    room_restart();
                }
                if (ucc_kind == 2)
                {
                    global.ucc_force_fun = ucc_value;
                    global.flag[5] = ucc_value;
                    ossafe_ini_open(""undertale.ini"");
                    ini_write_real(""General"", ""fun"", ucc_value);
                    ossafe_ini_close();
                    room_restart();
                }
                ucc_out += ""A|"" + string(current_time) + ""|"" + string(time) + ""|"" + string(ucc_seq) + ""|"" + string(ucc_kind) + ""|"" + string(ucc_value) + chr(10);
            }
        }
    }
    if (string_length(ucc_out) > 0)
    {
        var ucc_file = file_text_open_append(""ucc-events.log"");
        file_text_write_string(ucc_file, ucc_out);
        file_text_close(ucc_file);
    }
}
");
// Override ONLY the random roll. Story/route prerequisites stay intact.
foreach (var pair in new[] { ("a",61,"choose(0, 1, 2, 3, 4)","4"), ("b",62,"choose(0, 1)","1"), ("c",63,"choose(0, 1)","1") })
{
    var name = "gml_Object_obj_gaster_follower_" + pair.Item1 + "_Create_0";
    var source = Decompile(name);
    source = source.Replace("choos = " + pair.Item3 + ";", "choos = " + pair.Item3 + ";\nif (variable_global_exists(\"ucc_force_fun\") && global.ucc_force_fun == " + pair.Item2 + " && gox == 1) { choos = " + pair.Item4 + "; global.ucc_force_fun = -1; }");
    group.QueueReplace(Data.Code.ByName(name), source);
}
var fishing = Decompile("gml_Object_obj_ladiesfishingrod_Create_0");
fishing = fishing.Replace("orx = choose(0, 1);", "orx = choose(0, 1); if (variable_global_exists(\"ucc_force_fun\") && global.ucc_force_fun == 65) { orx = 1; global.ucc_force_fun = -1; }");
group.QueueReplace(Data.Code.ByName("gml_Object_obj_ladiesfishingrod_Create_0"), fishing);
var door = Decompile("gml_Object_obj_greydoor_Create_0");
door = door.Replace("ch = choose(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);", "ch = choose(0, 1, 2, 3, 4, 5, 6, 7, 8, 9); if (variable_global_exists(\"ucc_force_fun\") && global.ucc_force_fun == 66) { ch = 4; global.ucc_force_fun = -1; }");
group.QueueReplace(Data.Code.ByName("gml_Object_obj_greydoor_Create_0"), door);
group.Import();
ScriptMessage("Control Center runtime bridge installed: plot splits, flag diffs, acknowledged safe live commands.");
