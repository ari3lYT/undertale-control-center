// Called in obj_time context. Only manager-owned caches are written.
var k = argument0;
var typ = argument1;
var val = argument2;
ucc6_count += 1;
ds_map_replace(ucc6_seen, k, ucc6_cycle);
if (!ds_map_exists(ucc6_prev, k) || ds_map_find_value(ucc6_prev, k) != val || ds_map_find_value(ucc6_types,k) != typ)
{
    if (!ds_map_exists(ucc6_prev,k)) { ucc6_keys[ucc6_keycount]=k; ucc6_keycount+=1; }
    ds_map_replace(ucc6_prev, k, val);
    ds_map_replace(ucc6_types,k,typ);
    var text = string(val);
    if (typ == "number") text = string_format(val,0,12);
    var wire = typ + "|" + string_replace_all(string_replace_all(string_replace_all(string_replace_all(text, "%", "%25"), "|", "%7C"), chr(10), "%0A"), chr(13), "%0D");
    var escaped = string_replace_all(string_replace_all(string_replace_all(string_replace_all(k, "%", "%25"), "|", "%7C"), chr(10), "%0A"), chr(13), "%0D");
    ucc6_buffer += "V|" + string(current_time) + "|" + string(time) + "|" + escaped + "|" + wire + chr(10);
}
