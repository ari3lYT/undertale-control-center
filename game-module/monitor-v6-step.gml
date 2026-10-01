// Incremental sweep; small gameplay fields are sampled every frame.
var scan_start=get_timer();
ucc6_frame+=1;
if(ucc6_frame mod 15==0 && file_exists("ucc-settings.ini"))
{
 ini_open("ucc-settings.ini");ucc6_interval=max(100,min(2000,ini_read_real("manager","monitor_interval_ms",1000)));ini_close();
}
if(ucc6_phase==0 && current_time>=ucc6_next_scan){ucc6_next_scan=current_time+ucc6_interval;ucc6_cycle+=1;ucc6_count=0;ucc6_skipped=0;ucc6_max_slice=0;ucc6_names=variable_instance_get_names(global);ucc6_pos=0;ucc6_phase=1;scr_ucc6_value("obj_time.time",time,0);}
var fast=["hp","maxhp","en","maxen","lv","xp","gold","kills","plot","item","phone","weapon","armor","inbattle","interact","choice","shrine"];
for(var n=0;n<array_length_1d(fast);n+=1)
 if(variable_global_exists(fast[n])) scr_ucc6_value("global."+fast[n],variable_global_get(fast[n]),0);
scr_ucc6_value("engine.room",room,0);
scr_ucc6_value("engine.room_speed",room_speed,0);
scr_ucc6_value("engine.instance_count",instance_count,0);
while(get_timer()-scan_start<4000 && ucc6_phase>0 && ucc6_phase<4)
{
 if(ucc6_phase==1)
 {
  if(ucc6_pos<array_length_1d(ucc6_names))
  {
   var name=ucc6_names[ucc6_pos];ucc6_pos+=1;
   if(string_copy(name,1,4)!="ucc_" && variable_global_exists(name))scr_ucc6_value("global."+name,variable_global_get(name),0);
  }
  else
  {
   ucc6_instances=instance_count;
   for(var n=0;n<ucc6_instances;n+=1)ucc6_ids[n]=instance_id[n];
   ucc6_inst_pos=0;ucc6_phase=2;
  }
 }
 else if(ucc6_phase==2)
 {
  if(ucc6_inst_pos>=ucc6_instances)ucc6_phase=4;
  else
  {
   ucc6_inst=ucc6_ids[ucc6_inst_pos];ucc6_inst_pos+=1;
   if(instance_exists(ucc6_inst))
   {
    ucc6_prefix="instance["+string(ucc6_inst)+":"+object_get_name(ucc6_inst.object_index)+"].";
    ucc6_names=variable_instance_get_names(ucc6_inst);ucc6_pos=0;ucc6_phase=3;
   }
  }
 }
 else if(ucc6_phase==3)
 {
  if(!instance_exists(ucc6_inst))ucc6_phase=2;
  else
  {
   var user_count=array_length_1d(ucc6_names);var built_count=array_length_1d(ucc6_builtins);
   if(ucc6_pos<user_count)
   {
    var name=ucc6_names[ucc6_pos];
    if(string_copy(name,1,3)!="ucc" && variable_instance_exists(ucc6_inst,name))scr_ucc6_value(ucc6_prefix+name,variable_instance_get(ucc6_inst,name),0);
   }
   else if(ucc6_pos<user_count+built_count)
   {
    var name=ucc6_builtins[ucc6_pos-user_count];scr_ucc6_value(ucc6_prefix+name,variable_instance_get(ucc6_inst,name),0);
   }
   else if(ucc6_pos<user_count+built_count+12)
   {
    var alarm_n=ucc6_pos-user_count-built_count;scr_ucc6_value(ucc6_prefix+"alarm["+string(alarm_n)+"]",ucc6_inst.alarm[alarm_n],0);
   }
   else ucc6_phase=2;
   ucc6_pos+=1;
  }
 }
}
if(ucc6_phase==4)
{
 var kept=0;
 for(var key_n=0;key_n<ucc6_keycount;key_n+=1)
 {
  var key=ucc6_keys[key_n];var keep=true;
  if(ds_map_find_value(ucc6_seen,key)!=ucc6_cycle && ucc6_skipped==0)
  {
   var escaped=string_replace_all(string_replace_all(string_replace_all(string_replace_all(key,"%","%25"),"|","%7C"),chr(10),"%0A"),chr(13),"%0D");
   ucc6_buffer+="D|"+string(current_time)+"|"+string(time)+"|"+escaped+chr(10);
   ds_map_delete(ucc6_prev,key);ds_map_delete(ucc6_seen,key);ds_map_delete(ucc6_types,key);keep=false;
  }
  if(keep){ucc6_keys[kept]=key;kept+=1;}
 }
 ucc6_keycount=kept;
}
ucc6_scan_us=get_timer()-scan_start;ucc6_max_slice=max(ucc6_max_slice,ucc6_scan_us);
if(ucc6_phase==4)
{
 ucc6_buffer+="T|"+string(current_time)+"|"+string(time)+"|"+string(ucc6_keycount)+"|"+string(ucc6_skipped)+"|"+string(ucc6_max_slice)+"|"+string(ucc6_frame)+chr(10);
 ucc6_phase=0;
}
if((ucc6_frame mod 15==0 || ucc6_phase==0 || string_length(ucc6_buffer)>262144) && string_length(ucc6_buffer)>0)
{
 var h=file_text_open_append("ucc-events.log");file_text_write_string(h,ucc6_buffer);file_text_close(h);ucc6_buffer="";
}
