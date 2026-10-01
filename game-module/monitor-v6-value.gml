var key = argument0;
var val = argument1;
var level = argument2;
if (ucc6_count >= 100000 || level > 8)
{
    ucc6_skipped += 1;
    scr_ucc6_emit(key, "unread", "Лимит обхода: 100000 значений / глубина 8");
    exit;
}
if (is_array(val))
{
    var height = array_height_2d(val);
    scr_ucc6_emit(key, "array", string(height));
    for (var row = 0; row < height; row += 1)
    {
        var length = array_length_2d(val, row);
        for (var col = 0; col < length; col += 1)
        {
            var suffix = "[" + string(col) + "]";
            if (height > 1) suffix = "[" + string(row) + "," + string(col) + "]";
            scr_ucc6_value(key + suffix, val[row,col], level + 1);
            if (ucc6_count >= 100000) { ucc6_skipped += 1; break; }
        }
        if (ucc6_count >= 100000) break;
    }
}
else if (is_string(val))
{
    if (string_length(val) > 16384) { ucc6_skipped += 1; scr_ucc6_emit(key,"truncated-string",string_copy(val,1,16384)); }
    else scr_ucc6_emit(key, "string", val);
}
else if (is_real(val) || is_int32(val) || is_int64(val) || is_bool(val)) scr_ucc6_emit(key, "number", val);
else if (is_undefined(val)) scr_ucc6_emit(key, "undefined", "");
else { ucc6_skipped += 1; scr_ucc6_emit(key,"unsupported",string(val)); }
