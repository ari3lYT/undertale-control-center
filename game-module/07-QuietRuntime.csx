// Keep the bridge's polling cadence (including live command latency), but
// write unchanged settings and heartbeat state much less often.
EnsureDataLoaded();
var context = new UndertaleModLib.Decompiler.GlobalDecompileContext(Data);
var code = Data.Code.ByName("gml_Object_obj_time_Step_1");
var step = new Underanalyzer.Decompiler.DecompileContext(context, code, Data.ToolInfo.DecompilerSettings).DecompileToString();
var lines = new System.Collections.Generic.List<string>(step.Split('\n'));
int q = lines.FindIndex(line => line.Contains("ucc_io +=") && line.Contains("\"Q|\""));
int h = lines.FindIndex(line => line.Contains("ucc_out +=") && line.Contains("\"H|\""));
if (q < 0 || h < 0 || q == h) throw new Exception("Runtime bridge log anchors changed; refusing patch");
var qLine = lines[q].Trim();
lines[q] = @"if (!variable_instance_exists(id, ""ucc_last_q"")) ucc_last_q = """";
var ucc_q_sig = string(global.debug) + ""|"" + string(global.ucc_wasd) + ""|"" + string(global.ucc_zxc) + ""|"" + string(global.ucc_inputlog) + ""|"" + string(global.shrine);
if (ucc_q_sig != ucc_last_q) { ucc_last_q = ucc_q_sig; " + qLine + " }";
var hLine = lines[h].Trim();
lines[h] = @"if (!variable_instance_exists(id, ""ucc_last_h_sig"")) { ucc_last_h_sig = """"; ucc_last_h_wall = -999999; }
var ucc_h_sig = string(room) + ""|"" + string(global.plot) + ""|"" + string(global.inbattle) + ""|"" + string(global.interact);
if (ucc_h_sig != ucc_last_h_sig || current_time - ucc_last_h_wall >= 2000)
{ ucc_last_h_sig = ucc_h_sig; ucc_last_h_wall = current_time; " + hLine + " }";
var group = new UndertaleModLib.Compiler.CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
group.QueueReplace(code, string.Join("\n",lines));
group.Import();
ScriptMessage("Runtime bridge staged: settings only on change; state heartbeat at 2 s or transition; live polling unchanged.");
