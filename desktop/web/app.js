import {parseTime, formatTime, rangeError, clamp, initialStart} from './core.mjs';
import {createScrubPreview} from './scrub.mjs';

const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="clipper-token"]')?.content || '';
const state = {video:null, start:0, end:10, position:0, viewStart:0, viewSpan:10, player:null, ready:false, previewing:false, previewArmed:false, drag:null, loading:false, jobs:[], jobSignature:'', submitting:false, deleteAvailable:true, cloudWorker:false};
let ytPromise;
let scrubPreview;

async function api(path, body, timeout = 15000, method = body === undefined ? 'GET' : 'POST') {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(path, {method, headers:{'Content-Type':'application/json', 'X-Clipper-Token':token}, body:body === undefined ? undefined : JSON.stringify(body), signal:controller.signal});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Sprawdź link i podane czasy.');
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('Operacja trwa zbyt długo. Spróbuj ponownie.');
    if (error instanceof TypeError) throw new Error('Brak połączenia z aplikacją. Uruchom ją ponownie.');
    throw error;
  } finally { clearTimeout(timer); }
}
function showError(message) { $('global-error').textContent=message; $('global-error').hidden=!message; }
function playerProblem(message) { scrubPreview?.cancel();state.ready=false;state.previewing=false; $('preview-error').textContent=message; $('preview-error').hidden=false; updatePlayerControls(); }
function loadYouTubeAPI() {
  if (window.YT?.Player) return Promise.resolve();
  if (ytPromise) return ytPromise;
  ytPromise = new Promise((resolve,reject) => {
    const timer=setTimeout(() => {ytPromise=null;reject(new Error('Nie można uruchomić podglądu YouTube. Możesz nadal wpisać czasy i zapisać klip.'));},15000);
    window.onYouTubeIframeAPIReady=()=>{clearTimeout(timer);resolve();};
    const script=document.createElement('script');script.src='https://www.youtube.com/iframe_api';script.onerror=()=>{clearTimeout(timer);ytPromise=null;reject(new Error('Podgląd YouTube jest zablokowany. Możesz nadal wyciąć klip, wpisując czasy.'));};document.head.append(script);
  });
  return ytPromise;
}
async function mountPlayer(video) {
  scrubPreview?.cancel();scrubPreview=null;
  state.ready=false;state.previewing=false;updatePlayerControls();$('preview-error').hidden=true;
  try {
    await loadYouTubeAPI();
    if (state.video?.id !== video.id) return;
    if (state.player) state.player.destroy();
    $('empty-stage').hidden=true;$('youtube-player').hidden=false;
    state.player=new YT.Player('youtube-player',{videoId:video.id, width:'100%',height:'100%',playerVars:{origin:location.origin,playsinline:1,rel:0,start:Math.floor(state.start)},events:{
      onReady:event=>{if(event.target!==state.player)return;state.ready=true;scrubPreview=createScrubPreview(event.target,{onBlocked:()=>{$('preview-error').textContent='YouTube nie przygotował podglądu. Spróbuj ponownie przesunąć uchwyt na osi czasu lub odtwórz film.';$('preview-error').hidden=false;}});updatePlayerControls();state.player.cueVideoById({videoId:video.id,startSeconds:state.start});},
      onStateChange:event=>{if(event.target!==state.player)return;scrubPreview?.onStateChange(event.data);if (event.data===YT.PlayerState.ENDED) {state.previewing=false;updatePlayerControls();}},
      onError:()=>playerProblem('YouTube nie pozwala odtworzyć tego filmu w osadzonym podglądzie. Możesz nadal ustawić czasy i zapisać fragment.')
    }});
  } catch(error) { playerProblem(error.message); }
}
function updatePlayerControls() {
  for (const id of ['mark-start','mark-end','preview-selection']) $(id).disabled=!state.ready || state.loading;
  $('preview-selection').lastChild.textContent=state.previewing?' Zatrzymaj podgląd':'Odtwórz fragment';
}
function seek(time, final=true) {
  state.position=clamp(time,0,state.video?.duration||0);
  if(state.ready) scrubPreview?.seek(state.position,final);
  renderPosition();
}
function renderPosition() {
  $('current-time').textContent=formatTime(state.position);
  const p=(state.position-state.viewStart)/state.viewSpan*100;
  $('playhead').style.left=`${clamp(p,0,100)}%`;$('playhead').hidden=p<0||p>100||!state.video;
}
function renderTimeline() {
  const duration=state.video?.duration||10;
  state.viewSpan=clamp(state.viewSpan,Math.min(2,duration),duration);
  state.viewStart=clamp(state.viewStart,0,duration-state.viewSpan);
  const x=t=>clamp((t-state.viewStart)/state.viewSpan*100,0,100);
  $('selection').style.left=`${x(state.start)}%`;$('selection').style.width=`${x(state.end)-x(state.start)}%`;
  for (const boundary of ['start','end']) {
    const handle=$(boundary+'-handle');handle.style.left=`${x(state[boundary])}%`;
    handle.setAttribute('aria-valuenow',state[boundary].toFixed(2));handle.setAttribute('aria-valuetext',formatTime(state[boundary]));
    handle.setAttribute('aria-valuemin',boundary==='start'?0:(state.start+.1).toFixed(2));
    handle.setAttribute('aria-valuemax',boundary==='start'?(state.end-.1).toFixed(2):duration);
    handle.hidden=state[boundary]<state.viewStart-.001||state[boundary]>state.viewStart+state.viewSpan+.001;
  }
  $('ticks').replaceChildren();
  const tickCount=$('timeline').clientWidth<420?4:6;
  for(let i=0;i<=tickCount;i++) { const tick=document.createElement('div');tick.className='tick';tick.style.left=`${i/tickCount*100}%`;if(i===tickCount)tick.style.left='calc(100% - 1px)';const text=document.createElement('span');text.textContent=formatTime(state.viewStart+state.viewSpan*i/tickCount,state.viewSpan<10);tick.append(text);$('ticks').append(tick); }
  renderPosition();
}
function renderRange(updateFields=true) {
  if(updateFields){$('start-time').value=formatTime(state.start);$('end-time').value=formatTime(state.end);for(const id of ['start-time','end-time'])$(id).removeAttribute('aria-invalid');}
  const message=state.video?rangeError(state.start,state.end,state.video.duration):'';
  $('range-error').textContent=message;$('range-error').hidden=!message;
  $('clip-duration').textContent=`${(state.end-state.start).toLocaleString('pl-PL',{minimumFractionDigits:2,maximumFractionDigits:2})} s`;
  $('export-button').disabled=!!message||!state.video||state.submitting;
  renderTimeline();
}
function inputRange() {
  const start=parseTime($('start-time').value),end=parseTime($('end-time').value);
  const message=rangeError(start,end,state.video?.duration||0);
  $('range-error').textContent=message;$('range-error').hidden=!message;$('export-button').disabled=!!message||state.submitting;
  for(const id of ['start-time','end-time'])$(id).setAttribute('aria-invalid',String(!!message));
  if(message)return false;
  state.start=start;state.end=end;renderRange(false);return true;
}
function moveBoundary(boundary,value,final=true) {
  if(!state.video||state.loading)return;
  state[boundary]=Math.round(clamp(value,boundary==='start'?0:state.start+.1,boundary==='start'?state.end-.1:state.video.duration)*100)/100;
  state.previewing=false;renderRange();seek(state[boundary],final);updatePlayerControls();
}
function setZoom(span) {
  const center=(state.start+state.end)/2;state.viewSpan=span;state.viewStart=center-span/2;renderTimeline();
}
$('source-form').addEventListener('submit',async event=>{
  event.preventDefault();if(state.loading)return;showError('');state.loading=true;document.body.classList.add('loading');$('load-button').disabled=true;$('load-button').querySelector('span').textContent='Wczytuję…';$('source-message').textContent='Sprawdzam film i dostępne strumienie…';$('cut-controls').disabled=true;$('timeline-controls').disabled=true;updatePlayerControls();
  const original=$('source-url').value;
  try {
    const video=await api('/api/video',{url:original},115000);
    state.video=video;state.start=initialStart(original,video.duration);state.end=Math.min(video.duration,state.start+10);state.viewStart=0;state.viewSpan=video.duration;state.position=state.start;
    $('video-title').textContent=video.title;$('video-title').title=video.title;$('video-meta').textContent=formatTime(video.duration,false);$('source-message').textContent=`${video.channel} · Ustaw zakres i zapisz fragment.`;
    try{localStorage.setItem('clipper-last-url',original);}catch{}renderRange();void mountPlayer(video);
  } catch(error) {showError(error.message);$('source-message').textContent=state.video?'Poprzednio wczytany film pozostaje w edytorze.':'Wklej link do publicznego filmu na YouTube.';}
  finally {state.loading=false;document.body.classList.remove('loading');$('load-button').disabled=false;$('load-button').querySelector('span').textContent='Wczytaj film';$('cut-controls').disabled=!state.video;$('timeline-controls').disabled=!state.video;updatePlayerControls();}
});
for(const id of ['start-time','end-time']) {$(id).addEventListener('input',inputRange);$(id).addEventListener('change',()=>{if(inputRange()){state.previewing=false;updatePlayerControls();renderRange();setZoom(state.viewSpan);seek(state[id==='start-time'?'start':'end']);}});}
document.querySelectorAll('.nudge').forEach(button=>button.addEventListener('click',()=>moveBoundary(button.dataset.boundary,state[button.dataset.boundary]+Number(button.dataset.delta))));
$('mark-start').addEventListener('click',()=>moveBoundary('start',state.player.getCurrentTime()));$('mark-end').addEventListener('click',()=>moveBoundary('end',state.player.getCurrentTime()));
$('zoom-in').addEventListener('click',()=>setZoom(state.viewSpan/2));$('zoom-out').addEventListener('click',()=>setZoom(state.viewSpan*2));$('zoom-selection').addEventListener('click',()=>setZoom(Math.max(2,(state.end-state.start)*1.7)));
function pointerTime(event) {const box=$('timeline').getBoundingClientRect();return state.viewStart+clamp((event.clientX-box.left)/box.width,0,1)*state.viewSpan;}
$('timeline').addEventListener('pointerdown',event=>{
  if(!state.video||state.loading||event.button!==0)return;
  const handle=event.target.closest('.handle');state.drag=handle?(handle.id==='start-handle'?'start':'end'):'seek';
  $('timeline').setPointerCapture(event.pointerId);if(handle)handle.focus();
  if(state.drag==='seek'){state.previewing=false;updatePlayerControls();seek(pointerTime(event),false);}else moveBoundary(state.drag,pointerTime(event),false);
});
$('timeline').addEventListener('pointermove',event=>{if(!state.drag)return;if(state.drag==='seek')seek(pointerTime(event),false);else moveBoundary(state.drag,pointerTime(event),false);});
function endDrag(event){if(!state.drag)return;seek(state.drag==='seek'?state.position:state[state.drag],true);state.drag=null;if($('timeline').hasPointerCapture(event.pointerId))$('timeline').releasePointerCapture(event.pointerId);}
$('timeline').addEventListener('pointerup',endDrag);$('timeline').addEventListener('pointercancel',endDrag);
for(const boundary of ['start','end'])$(boundary+'-handle').addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const delta=(event.shiftKey?1:.1)*(event.key==='ArrowLeft'?-1:1);moveBoundary(boundary,event.key==='Home'?0:event.key==='End'?state.video.duration:state[boundary]+delta);}});
$('preview-selection').addEventListener('click',()=>{
  if(!state.ready||!inputRange())return;
  scrubPreview?.cancel();
  if(state.previewing){state.player.pauseVideo();state.previewing=false;}else{state.previewing=true;state.previewArmed=false;state.position=state.start;renderPosition();state.player.loadVideoById({videoId:state.video.id,startSeconds:state.start,endSeconds:state.end});}updatePlayerControls();
});
setInterval(()=>{if(!state.ready||state.drag||scrubPreview?.pending)return;state.position=state.player.getCurrentTime()||0;if(state.previewing&&state.position>=state.start-.15&&state.position<state.end)state.previewArmed=true;if(state.previewing&&state.previewArmed&&state.position>=state.end){state.player.pauseVideo();state.previewing=false;seek(state.end);updatePlayerControls();}renderPosition();},80);

async function submitClip(){
  if(!state.video||state.loading||state.submitting||!inputRange())return;
  state.submitting=true;$('export-button').disabled=true;showError('');
  try{const job=await api('/api/clips',{url:state.video.url,start:state.start,end:state.end,mute_audio:$('mute-audio').checked,quality:Number($('quality').value)});$('job-announcement').textContent='Dodano fragment do eksportu.';await refreshJobs();document.querySelector(`[data-job-id="${job.id}"]`)?.scrollIntoView({block:'nearest',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
  catch(error){showError(error.message);}finally{state.submitting=false;inputRange();}
}
$('export-button').addEventListener('click',submitClip);
$('mute-audio').addEventListener('change',()=>{$('audio-summary').textContent=$('mute-audio').checked?'Sam obraz, bez dźwięku':'Obraz i dźwięk';});
$('quality').addEventListener('change',()=>{$('quality-summary').textContent=`do ${$('quality').value}p`;});
document.addEventListener('keydown',event=>{
  if(event.ctrlKey&&event.key==='Enter'){event.preventDefault();void submitClip();return;}
  if(!state.ready||state.loading||event.ctrlKey||event.metaKey||event.altKey||event.target.matches('input,textarea,select,[contenteditable="true"]'))return;
  if(event.key.toLowerCase()==='i'){event.preventDefault();$('mark-start').click();}if(event.key.toLowerCase()==='o'){event.preventDefault();$('mark-end').click();}
});
async function openFolder(){try{await api('/api/folder',{});}catch(error){showError(error.message);}}
$('open-folder')?.addEventListener('click',openFolder);$('panel-folder')?.addEventListener('click',openFolder);
function showOutputFolder(path){
  $('output-folder').textContent=`Folder zapisu: ${path}`;
  $('output-folder').title=path;
  $('panel-folder').title=path;
  $('panel-folder').textContent=path.split(/[\\/]/).filter(Boolean).at(-1)||path;
}
$('choose-folder')?.addEventListener('click',async()=>{
  const button=$('choose-folder');button.disabled=true;showError('');
  try{
    if(!window.pywebview?.api?.choose_output_folder)throw new Error('Wybór folderu jest dostępny w zainstalowanej aplikacji Windows.');
    const result=await window.pywebview.api.choose_output_folder();
    showOutputFolder(result.path);
    if(result.changed){state.jobSignature='';await refreshJobs();$('job-announcement').textContent=`Folder zapisu zmieniony na ${result.path}`;}
  }catch(error){showError(error.message||'Nie udało się zmienić folderu zapisu.');}
  finally{button.disabled=false;}
});
function element(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
function renderJobs(jobs){
  const signature=JSON.stringify(jobs);if(signature===state.jobSignature)return;state.jobSignature=signature;state.jobs=jobs;$('jobs').replaceChildren();$('clip-count').textContent=jobs.filter(j=>j.status==='done').length;
  if(!jobs.length){$('jobs').append(element('div','jobs-empty','Pierwszy zapisany fragment pojawi się tutaj.'));return;}
  for(const job of jobs){
    const row=element('article','job');row.dataset.status=job.status;row.dataset.jobId=job.id;row.append(element('div','job-icon','MP4'));
    const details=element('div','job-details');details.append(element('h3','',job.title),element('p','',`${formatTime(job.start)} — ${formatTime(job.end)} · ${job.duration.toLocaleString('pl-PL')} s · do ${job.quality||1080}p${job.mute_audio?' · bez dźwięku':''}${job.size?' · '+(job.size/1048576).toFixed(1)+' MB':''}`));
    details.append(element('p','job-message',job.message));
    const actions=element('div','job-actions');
    if(['queued','resolving','exporting'].includes(job.status)){const progress=element('progress');progress.max=100;progress.setAttribute('aria-label','Postęp eksportu');if(job.progress>0)progress.value=job.progress;details.append(progress);const cancel=element('button','button secondary','Anuluj');cancel.type='button';cancel.addEventListener('click',async()=>{try{await api(`/api/clips/${job.id}/cancel`,{});await refreshJobs();}catch(error){showError(error.message);}});actions.append(cancel);}
    if(job.status==='done'){
      if(state.cloudWorker){const link=element('a','button secondary','Pobierz MP4');link.href=`/api/clips/${job.id}/file`;link.download=job.filename;actions.append(link);}
      else{const folder=element('button','button secondary','Otwórz folder');folder.type='button';folder.setAttribute('aria-label',`Otwórz folder z klipem ${job.title}`);folder.addEventListener('click',openFolder);actions.append(folder);}
      const remove=element('button','button secondary delete-clip','Usuń');remove.type='button';remove.disabled=!state.deleteAvailable;remove.setAttribute('aria-label',`Usuń klip ${job.title} z dysku`);
      remove.addEventListener('click',async()=>{
        if(!confirm(`Usunąć „${job.title}” z listy i z folderu zapisu? Tej operacji nie można cofnąć.`))return;
        remove.disabled=true;showError('');
        try{await api(`/api/clips/${job.id}`,undefined,15000,'DELETE');$('job-announcement').textContent=`Usunięto klip ${job.title} z dysku.`;state.jobSignature='';await refreshJobs();}
        catch(error){remove.disabled=false;showError(error.message);}
      });
      actions.append(remove);
    }
    if(['error','cancelled'].includes(job.status)){const retry=element('button','button secondary','Ponów');retry.type='button';retry.addEventListener('click',async()=>{retry.disabled=true;try{await api('/api/clips',{url:job.url,start:job.start,end:job.end,mute_audio:job.mute_audio===true,quality:job.quality||1080});await refreshJobs();}catch(error){showError(error.message);}finally{retry.disabled=false;}});actions.append(retry);}
    row.append(details,actions);$('jobs').append(row);
  }
}
let polling=false,connectionFailed=false;
async function refreshJobs(){if(polling)return;polling=true;try{const jobs=await api('/api/clips');for(const job of jobs){const previous=state.jobs.find(j=>j.id===job.id);if(previous&&previous.status!==job.status&&['done','error'].includes(job.status))$('job-announcement').textContent=`${job.title}: ${job.message}`;}renderJobs(jobs);if(connectionFailed){connectionFailed=false;showError('');}}catch(error){connectionFailed=true;showError(error.message);}finally{polling=false;}}
setInterval(()=>{if(!document.hidden)void refreshJobs();},1500);
window.addEventListener('resize',renderTimeline);
try{$('source-url').value=localStorage.getItem('clipper-last-url')||'';}catch{}
renderRange();void refreshJobs();
api('/api/health').then(health=>{
  if(!health.ready)showError(`Brak zależności: ${[!health.ffmpeg?'FFmpeg':null,!health.node?'Node.js':null].filter(Boolean).join(', ')}. Uruchom Instaluj.cmd.`);
  state.cloudWorker=health.features?.cloud_worker===true;
  if($('output-folder'))showOutputFolder(health.output_dir);
  if($('choose-folder'))$('choose-folder').hidden=health.features?.choose_folder!==true;
  state.deleteAvailable=health.features?.delete_clip===true;
  $('exports-warning').textContent=state.deleteAvailable?'':'Działa starsza wersja serwera. Zamknij działającą aplikację i uruchom ponownie Uruchom.cmd, aby usuwać klipy.';
  $('exports-warning').hidden=state.deleteAvailable;
  state.jobSignature='';renderJobs(state.jobs);
}).catch(error=>showError(error.message));
