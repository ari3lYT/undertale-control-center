// Executed before the game's input translation. No system-wide input hook.
ucc_settings_poll += 1;
var ucc_io = "";
if (ucc_settings_poll >= 15 && started == 1)
{
    ucc_settings_poll = 0;
    if (file_exists("ucc-settings.ini"))
    {
        ini_open("ucc-settings.ini");
        global.ucc_wasd = ini_read_real("manager", "wasd", 1) == 1;
        global.ucc_zxc = ini_read_real("manager", "zxc", 1) == 1;
        global.ucc_inputlog = ini_read_real("manager", "input_log", 1) == 1;
        global.debug = ini_read_real("manager", "debug", 0) == 1;
        ini_close();
    }
    ucc_io += "Q|" + string(current_time) + "|" + string(time) + "|" + string(global.debug) + "|" + string(global.ucc_wasd) + "|" + string(global.ucc_zxc) + "|" + string(global.ucc_inputlog) + "|" + string(global.shrine) + chr(10);
}
for (var ucc_key = 8; ucc_key < 256; ucc_key += 1)
{
    var ucc_down = window_has_focus() && keyboard_check_direct(ucc_key);
    if (global.ucc_inputlog && ucc_down != ucc_keys[ucc_key])
        ucc_io += "I|" + string(current_time) + "|" + string(time) + "|" + string(room) + "|" + string(ucc_key) + "|" + string(ucc_down) + chr(10);
    ucc_keys[ucc_key] = ucc_down;
}
for (var ucc_mb = 1; ucc_mb <= 3; ucc_mb += 1)
{
    var ucc_down = window_has_focus() && mouse_check_button(ucc_mb);
    if (global.ucc_inputlog && ucc_down != ucc_mouse[ucc_mb])
        ucc_io += "M|" + string(current_time) + "|" + string(time) + "|" + string(room) + "|" + string(ucc_mb) + "|" + string(ucc_down) + "|" + string(mouse_x) + "|" + string(mouse_y) + chr(10);
    ucc_mouse[ucc_mb] = ucc_down;
}
for (var ucc_pad = 0; ucc_pad < min(16, gamepad_get_device_count()); ucc_pad += 1)
{
    if (gamepad_is_connected(ucc_pad))
    {
        for (var ucc_bt = 0; ucc_bt < 16; ucc_bt += 1)
        {
            var ucc_down = window_has_focus() && gamepad_button_check(ucc_pad, gp_face1 + ucc_bt);
            var ucc_slot = ucc_pad * 16 + ucc_bt;
            if (global.ucc_inputlog && ucc_down != ucc_pads[ucc_slot])
                ucc_io += "G|" + string(current_time) + "|" + string(time) + "|" + string(room) + "|" + string(ucc_bt) + "|" + string(ucc_down) + "|" + string(ucc_pad) + chr(10);
            ucc_pads[ucc_slot] = ucc_down;
        }
    }
}
if (variable_global_exists("choice"))
{
    if (global.ucc_inputlog && global.choice != ucc_lastchoice)
        ucc_io += "C|" + string(current_time) + "|" + string(time) + "|" + string(room) + "|" + string(global.choice) + "|1" + chr(10);
    ucc_lastchoice = global.choice;
}
if (string_length(ucc_io) > 0)
{
    var ucc_handle = file_text_open_append("ucc-events.log");
    file_text_write_string(ucc_handle, ucc_io);
    file_text_close(ucc_handle);
}
