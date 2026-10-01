var filename=argument0;
if(!file_exists(filename))return "absent";
var buf=buffer_load(filename);
if(buf<0)return "unreadable";
var hash=buffer_md5(buf,0,buffer_get_size(buf));
buffer_delete(buf);
return hash;
