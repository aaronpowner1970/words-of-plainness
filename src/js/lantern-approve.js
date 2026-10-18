/* Lantern Approve page: record or choose a narration, send it, show the receipt.
   Talks only to /api/lantern-narration. The receipt text comes from the server. */
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var dateEl = $('la-date'), pwEl = $('la-pw'), onfile = $('la-onfile'), picked = $('la-picked');
  var player = $('la-player'), sendBtn = $('la-send'), recBtn = $('la-record'), fileEl = $('la-file');
  var receiptEl = $('la-receipt'), errorEl = $('la-error'), approveBtn = $('la-approve');
  var MAX = 4 * 1024 * 1024;
  var current = null;           // { blob, filename } kept until a send succeeds
  var haveReceiptFor = null;    // date string
  var recorder = null, stream = null, chunks = [], timer = null;

  function store(op, k, v) {
    try { return op === 'get' ? localStorage.getItem(k) : localStorage.setItem(k, v); } catch (e) { return null; }
  }
  function nextSunday() {
    var d = new Date();
    d.setDate(d.getDate() + ((7 - d.getDay()) % 7));
    var m = ('0' + (d.getMonth() + 1)).slice(-2), day = ('0' + d.getDate()).slice(-2);
    return d.getFullYear() + '-' + m + '-' + day;
  }
  function refresh() {
    sendBtn.disabled = !current;
    approveBtn.disabled = haveReceiptFor !== dateEl.value;
  }
  function showError(msg) { errorEl.textContent = msg || ''; }
  function setCurrent(blob, filename) {
    current = { blob: blob, filename: filename };
    player.src = URL.createObjectURL(blob);
    player.hidden = false;
    picked.textContent = 'Ready to send: ' + filename + ' (' + (blob.size / 1048576).toFixed(1) + ' MB). Listen first if you like.';
    showError('');
    refresh();
  }
  function headers() { return { 'x-lantern-password': pwEl.value }; }

  async function checkOnFile() {
    haveReceiptFor = null; receiptEl.textContent = ''; refresh();
    if (!pwEl.value) { onfile.textContent = 'Enter the password to see what is on file for this date.'; return; }
    onfile.textContent = 'Checking what is on file…';
    try {
      var res = await fetch('/api/lantern-narration?date=' + encodeURIComponent(dateEl.value), { headers: headers() });
      var j = await res.json();
      if (!res.ok) { onfile.textContent = ''; showError(j.error || 'The check failed.'); return; }
      showError('');
      if (j.onFile) { onfile.textContent = ''; receiptEl.textContent = j.text; haveReceiptFor = dateEl.value; }
      else onfile.textContent = j.text;
    } catch (e) { onfile.textContent = ''; showError('Could not reach the site to check. Check your signal and try again.'); }
    refresh();
  }

  async function send() {
    if (!current) return;
    if (!pwEl.value) { showError('Enter the password first.'); return; }
    if (current.blob.size > MAX) { showError('That file is over 4 MB. Please record in a compressed format (the Record button here, or Voice Memos as m4a).'); return; }
    sendBtn.disabled = true; showError(''); receiptEl.textContent = 'Sending…';
    var sentDate = dateEl.value;
    try {
      var url = '/api/lantern-narration?date=' + encodeURIComponent(sentDate) + '&filename=' + encodeURIComponent(current.filename);
      var h = headers(); h['content-type'] = 'application/octet-stream';
      var res = await fetch(url, { method: 'POST', headers: h, body: current.blob });
      var j = {};
      try { j = await res.json(); } catch (e) { /* non-JSON error page */ }
      if (res.ok && j.ok) {
        store('set', 'wop-lantern-pw', pwEl.value);
        receiptEl.textContent = j.text; haveReceiptFor = sentDate; onfile.textContent = '';
        if (j.warning) showError(j.warning);
        current = null; picked.textContent = ''; player.hidden = true;
      } else {
        receiptEl.textContent = '';
        showError((j.error || ('The send failed (status ' + res.status + ').')) + ' Your recording is still here; press Send to try again.');
      }
    } catch (e) {
      receiptEl.textContent = '';
      showError('The send did not get through (no signal, perhaps). Nothing is confirmed. Your recording is still here; press Send to try again.');
    }
    refresh();
  }

  async function toggleRecord() {
    if (recorder && recorder.state === 'recording') { recorder.stop(); return; }
    if (!window.MediaRecorder || !navigator.mediaDevices) { showError('This browser cannot record here. Use Choose a file instead.'); return; }
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch (e) { showError('The microphone was not allowed. Allow it for this site, or use Choose a file.'); return; }
    var types = ['audio/mp4', 'audio/webm;codecs=opus', 'audio/webm'];
    var type = types.filter(function (t) { return MediaRecorder.isTypeSupported(t); })[0] || '';
    chunks = [];
    recorder = new MediaRecorder(stream, type ? { mimeType: type, audioBitsPerSecond: 48000 } : { audioBitsPerSecond: 48000 });
    recorder.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
    recorder.onstop = function () {
      clearInterval(timer); stream.getTracks().forEach(function (t) { t.stop(); });
      recBtn.classList.remove('recording'); recBtn.textContent = 'Record again';
      var mime = recorder.mimeType || type || 'audio/webm';
      var ext = mime.indexOf('mp4') > -1 ? 'm4a' : (mime.indexOf('ogg') > -1 ? 'ogg' : 'webm');
      setCurrent(new Blob(chunks, { type: mime }), 'narration.' + ext);
    };
    recorder.start(1000);
    recBtn.classList.add('recording');
    var t0 = Date.now();
    timer = setInterval(function () { recBtn.textContent = 'Stop (' + Math.floor((Date.now() - t0) / 1000) + 's)'; }, 500);
    recBtn.textContent = 'Stop (0s)';
    showError('');
  }

  dateEl.value = nextSunday();
  pwEl.value = store('get', 'wop-lantern-pw') || '';
  dateEl.addEventListener('change', function () { checkOnFile(); });
  pwEl.addEventListener('change', function () { store('set', 'wop-lantern-pw', pwEl.value); checkOnFile(); });
  fileEl.addEventListener('change', function () {
    var f = fileEl.files && fileEl.files[0];
    if (f) setCurrent(f, f.name);
  });
  recBtn.addEventListener('click', toggleRecord);
  sendBtn.addEventListener('click', send);
  checkOnFile();
})();
