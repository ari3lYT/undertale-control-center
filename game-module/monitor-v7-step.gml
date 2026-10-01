// Observe only values scr_saveprocess persists. The existing F bridge catches
// every global.flag change each frame; this sampler supplies its baseline and
// checks a small rotating subset as a safety net.
var scan_start = get_timer();
ucc6_frame += 1;
ucc6_count = 0;
if (ucc6_frame == 1)
{
    ucc6_buffer = "E|7" + chr(10);
    ucc6_max_slice = 0;
}

var fields = ["charname","lv","maxhp","maxen","at","wstrength",
              "df","adef","sp","xp","gold","kills","weapon","armor",
              "plot","currentroom","xbox_disconnect_counter",
              "xbox_coins_donated"];
for (var field_n = 0; field_n < array_length_1d(fields); field_n += 1)
{
    var field = fields[field_n];
    if (variable_global_exists(field))
        scr_ucc6_value("global." + field, variable_global_get(field), 0);
}

// The runtime arrays contain extra slots. scr_saveprocess serializes only
// 0..7 for item/phone and 0..2 for menuchoice.
for (var slot_n = 0; slot_n < 8; slot_n += 1)
{
    scr_ucc6_value("global.item[" + string(slot_n) + "]", global.item[slot_n], 0);
    scr_ucc6_value("global.phone[" + string(slot_n) + "]", global.phone[slot_n], 0);
}
for (var menu_n = 0; menu_n < 3; menu_n += 1)
    scr_ucc6_value("global.menuchoice[" + string(menu_n) + "]", global.menuchoice[menu_n], 0);

for (var flag_n = 0; flag_n < 16; flag_n += 1)
{
    var flag_index = ((ucc6_frame - 1) * 16 + flag_n) mod 512;
    scr_ucc6_value("global.flag[" + string(flag_index) + "]", global.flag[flag_index], 0);
}

ucc6_scan_us = get_timer() - scan_start;
ucc6_max_slice = max(ucc6_max_slice, ucc6_scan_us);
if (ucc6_frame >= 32 && ucc6_frame mod 30 == 0)
{
    ucc6_buffer += "T|" + string(current_time) + "|" + string(time) + "|" +
        string(ucc6_keycount) + "|0|" + string(ucc6_max_slice) + "|" +
        string(ucc6_frame) + chr(10);
    ucc6_max_slice = 0;
}
if (string_length(ucc6_buffer) > 0 &&
    (ucc6_frame mod 15 == 0 || string_length(ucc6_buffer) > 16384))
{
    var log_handle = file_text_open_append("ucc-events.log");
    file_text_write_string(log_handle, ucc6_buffer);
    file_text_close(log_handle);
    ucc6_buffer = "";
}
