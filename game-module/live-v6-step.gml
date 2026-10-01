// Does not run on startup without an explicit, session-bound user request.
if(!file_exists("ucc-live-request.ini"))exit;
ini_open("ucc-live-request.ini");
var seq=ini_read_real("command","seq",-1);
var expires=ini_read_real("command","expires",-1);
var token=ini_read_string("command","token","");
var load_file=ini_read_string("command","load_file","");
var count=ini_read_real("command","count",-1);
ini_close();
var reason="";
var before=[];var after=[];
if(token!=ucc6_token || current_time>expires || seq<0)reason="expired-session";
if(reason=="" && (!variable_global_exists("inbattle") || !variable_global_exists("interact") || global.inbattle!=0 || global.interact!=0 || !instance_exists(obj_mainchara)))exit;
var names=["file0","file1","file2","file3","file4","file5","file6","file7","file8","file9","undertale.ini","config.ini","system_information_962","system_information_963","undertale.sav"];
var stage="ucc-stage-"+string_format(seq,0,0)+"/";
if(count!=array_length_1d(names) || (load_file!="" && load_file!="file0" && load_file!="file9"))reason="invalid-manifest";
if(reason=="")
{
 ini_open("ucc-live-request.ini");
 for(var n=0;n<count;n+=1)
 {
  var sec=string(n);
  if(ini_read_string(sec,"name","")!=names[n])reason="invalid-name";
  before[n]=ini_read_string(sec,"before","");after[n]=ini_read_string(sec,"after","");
 }
 ini_close();
 for(var n=0;n<count;n+=1)
 {
  if(scr_ucc6_hash(names[n])!=before[n])reason="stale-files";
  if(scr_ucc6_hash(stage+"before-"+names[n])!=before[n] || scr_ucc6_hash(stage+"after-"+names[n])!=after[n])reason="damaged-staging";
 }
}
// All checks precede writes. Other game events cannot interleave this script.
if(reason=="")
{
 for(var n=0;n<count;n+=1)
 {
  if(before[n]!=after[n])
  {
   if(file_exists(names[n]))file_delete(names[n]);
   if(after[n]!="absent")file_copy(stage+"after-"+names[n],names[n]);
  }
 }
 for(var n=0;n<count;n+=1)if(scr_ucc6_hash(names[n])!=after[n])reason="write-failed";
 if(reason!="")
 {
  for(var n=0;n<count;n+=1)
  {
   if(file_exists(names[n]))file_delete(names[n]);
   if(before[n]!="absent")file_copy(stage+"before-"+names[n],names[n]);
  }
  for(var n=0;n<count;n+=1)if(scr_ucc6_hash(names[n])!=before[n])reason="rollback-failed";
 }
}
file_delete("ucc-live-request.ini");
ini_open("ucc-live-result.ini");
ini_write_string("result","seq",string_format(seq,0,0));ini_write_string("result","state",reason==""?"applied":"rejected");ini_write_string("result","reason",reason);ini_close();
if(reason=="")
{
 // Native loading restores HP and normalizes the same flags as Continue.
 // Whole-bundle operations reboot the game state, not the OS process.
 if(load_file!="")
 {
  global.filechoice=0;if(load_file=="file9")global.filechoice=9;
  scr_load();
 }
 else game_restart();
}
