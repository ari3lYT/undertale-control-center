const liveReasons={'expired-session':'Команда истекла или относится к другой сессии','invalid-manifest':'Некорректный план файлов','invalid-name':'Некорректное имя файла','stale-files':'Игра успела изменить файлы. Нужен новый план','damaged-staging':'Повреждены подготовленные файлы','write-failed':'Ошибка записи; исходные файлы восстановлены','rollback-failed':'Ошибка записи и восстановления. Не сохраняй игру; восстанови защитный слот после закрытия'};
setInterval(async()=>{
 if(!app.liveBundleSeq)return;
 try{
  const result=await api('/api/live-status');
  if(String(result.seq)!==app.liveBundleSeq)return;
  app.liveBundleSeq=null;
  toast(result.state==='applied'?'Игра подтвердила применение файлов и запрос загрузки состояния':(liveReasons[result.reason]||result.reason||'Команда отклонена'),result.state!=='applied');
  await refreshAll();if(typeof refreshExtras==='function')await refreshExtras();
 }catch(e){/* keep awaiting; never equate transport error with success */}
},1000);
