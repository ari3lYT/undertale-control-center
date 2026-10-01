// Replace only the v6 monitor script; keep save, input and live-load hooks.
EnsureDataLoaded();
var group = new UndertaleModLib.Compiler.CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
var path = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), "game-module", "monitor-v7-step.gml");
group.QueueReplace("gml_Script_scr_ucc6_step", System.IO.File.ReadAllText(path));
group.Import();
ScriptMessage("V7 monitor staged: save fields and saved room only; ticks annotate changes, not per-frame diffs.");
