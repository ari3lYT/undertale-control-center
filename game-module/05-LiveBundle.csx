EnsureDataLoaded();
var g=new UndertaleModLib.Compiler.CodeImportGroup(Data) { MainThreadAction=MainThreadAction };
var root=System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), "game-module") + System.IO.Path.DirectorySeparatorChar;
g.QueueReplace("gml_Script_scr_ucc6_hash",System.IO.File.ReadAllText(root+"live-v6-hash.gml"));
g.QueueReplace("gml_Script_scr_ucc6_live",System.IO.File.ReadAllText(root+"live-v6-step.gml"));
g.QueueAppend(Data.Code.ByName("gml_Object_obj_time_Create_0"),@"
ucc6_token=string(get_timer());
var h=file_text_open_append(""ucc-events.log"");file_text_write_string(h,""K|""+ucc6_token+chr(10));file_text_close(h);
");
g.QueueAppend(Data.Code.ByName("gml_Object_obj_time_Step_1"),"if(ucc6_frame mod 15==0) scr_ucc6_live();");
g.Import();
