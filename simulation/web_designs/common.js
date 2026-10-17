// Shared by design1 and design2: data helpers, the demo calendar and the booking state.
// Patients and staff never receive risk, threshold or overbooking information from these helpers;
// only the management screens read `risk`, `kind` and the rule settings.
const D = DATA, S = D.session, R = D.rules, AB = D.ab, REM = D.reminder;
const $ = (s) => document.querySelector(s);
const fmt = (n) => Math.round(n).toLocaleString('tr-TR');
const f1 = (n) => n.toLocaleString('tr-TR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const pcs = (n) => '%' + f1(n * 100);
const pv = (p) => (p < 0.001 ? '< 0,001' : p.toLocaleString('tr-TR', { maximumFractionDigits: 3 }));
Object.values(R).forEach((r) => { r.util = r.utilization * 100; });

const MONTHS = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
const DOW = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];
const TODAY = '2016-06-09', REAL = '2016-06-07', THR = 30, LIM = 4; // REAL: a day with real records (the past); today is empty
const pad = (n) => String(n).padStart(2, '0');
const isoOf = (y, m, d) => y + '-' + pad(m + 1) + '-' + pad(d); // m is 0-based
const dowOf = (i) => (new Date(i + 'T00:00:00').getDay() + 6) % 7; // 0 = Monday
const longDate = (i) => new Date(i + 'T00:00:00').toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric', weekday: 'long' });
const addDays = (i, n) => { const d = new Date(i + 'T00:00:00'); d.setDate(d.getDate() + n); return isoOf(d.getFullYear(), d.getMonth(), d.getDate()); };
const isOpenDay = (i) => i >= TODAY && dowOf(i) < 5;
const MON = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6 };
const DATA_DAYS = new Set(D.per_day.map((d) => { const [dd, mm, yy] = d.date.split(' '); return isoOf(+yy, MON[mm], +dd); }));
// Management: the clinic-room session shown on the decision screens can be chosen per record day.
const sessionOf = (i) => (D.sessions && D.sessions[i]) || D.session;
let ADAY = REAL, AS = sessionOf(REAL);
const setAday = (i) => { ADAY = i; AS = sessionOf(i); };
const adayPicker = () => `<select id="aday">${recordDays().map((d) => `<option value="${d}" ${d === ADAY ? 'selected' : ''}>${longDate(d)}</option>`).join('')}</select>`;
function hash(str) { let h = 2166136261; for (const c of str) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }

// Demo patients (the person using the patient portal can be switched in the demo).
const PATIENTS = [{ id: 5778201, age: 34 }, { id: 5778202, age: 61 }, { id: 5778203, age: 27 }];
let CUR = PATIENTS[0].id;
// Demo bookings are also written to output/web_randevulari.xlsx by simulation/web_designs/serve.py (if running).
function sendRecord(path, body) {
  const mark = (ok) => { const u = document.getElementById('xl'); if (u) u.textContent = ok ? ' · Excel kaydı: açık' : ' · Excel kaydı: kapalı (serve.py çalışmıyor)'; };
  try {
    fetch('http://127.0.0.1:8765/' + path, { method: 'POST', body: JSON.stringify(body) }).then((r) => mark(r.ok)).catch(() => mark(false));
  } catch (e) { mark(false); }
}
const RISKS = S.slots.flatMap((sl) => sl.patients.map((p) => p.risk));
// Demo: the model API is not connected, so a new booking gets a risk drawn from the real risk distribution.
const riskOf = (no) => RISKS[hash(no) % RISKS.length];
const BK = [{ no: 'R-5778201', pid: PATIENTS[0].id, iso: '2016-06-14', time: '10:30', kind: 'normal', risk: riskOf('R-5778201'), old: true }];
const ATT = {}; // staff screen: attendance marks of today

const bookingsAt = (i, time) => BK.filter((b) => b.iso === i && b.time === time);
const extrasUsed = (i) => BK.filter((b) => b.iso === i && b.kind === 'extra').length;
// Is slot k of day i free for the current patient? The overbooking rule decides inside the system;
// the patient only sees "free" or "full".
function slotsOf(i) {
  return S.slots.map((sl, k) => {
    const at = bookingsAt(i, sl.time), mine = at.some((b) => b.pid === CUR);
    const open = isOpenDay(i) && !mine && (at.length === 0 || (at.length === 1 && at[0].risk >= THR && extrasUsed(i) < LIM));
    return { k, time: sl.time, mine, open };
  });
}
const freeCount = (i) => (isOpenDay(i) ? slotsOf(i).filter((s) => s.open).length : 0);
function addBooking(i, k) {
  const time = S.slots[k].time, kind = bookingsAt(i, time).length ? 'extra' : 'normal';
  const no = 'R-' + (5780000 + Math.floor(Math.random() * 9999));
  const bk = { no, pid: CUR, iso: i, time, kind, risk: riskOf(no) };
  BK.push(bk);
  sendRecord('kayit', { ...bk, who: (window.SESSION || {}).who });
  return bk;
}
const cancelBooking = (no) => { sendRecord('iptal', { no }); const x = BK.findIndex((b) => b.no === no); if (x >= 0) BK.splice(x, 1); };
const myBookings = () => BK.filter((b) => b.pid === CUR);

// Staff day: patient number, age and (for record days) the real outcome. Record days are read-only.
function dayRecords(i) {
  return (typeof RECORDS !== 'undefined' && RECORDS[i]) || [];
}
function staffDay(i) {
  if (DATA_DAYS.has(i)) {
    const list = dayRecords(i).map((r) => ({ time: null, id: r[0], age: r[1], key: 'r' + r[0], outcome: r[3] ? 'n' : 'g', risk: r[2] }));
    return { mode: 'data', list };
  }
  const list = BK.filter((b) => b.iso === i).map((b) => ({ time: b.time, id: b.pid, age: (PATIENTS.find((p) => p.id === b.pid) || {}).age, key: b.no }));
  list.sort((x, y) => x.time.localeCompare(y.time));
  return { mode: i === TODAY ? 'today' : i > TODAY ? 'future' : 'none', list };
}
// Management: statistics of one record day.
function dayStats(i) {
  const r = dayRecords(i), n = r.length;
  const miss = r.filter((x) => x[3]).length, hi = r.filter((x) => x[2] >= THR).length;
  return { n, miss, rate: n ? miss / n : 0, mean: n ? r.reduce((a, x) => a + x[2], 0) / n : 0, hi, hiShare: n ? hi / n : 0 };
}
const recordDays = () => [...DATA_DAYS].sort();
function dayStatsTable(selected) {
  return `<table><tr><th>Gün</th><th class="r">Randevu</th><th class="r">Gelmeyen</th><th class="r">Gerçek gelmeme</th><th class="r">Ortalama risk</th><th class="r">Risk ≥ %${THR}</th></tr>
 ${recordDays().map((d) => { const x = dayStats(d); return `<tr class="${d === selected ? 'hl' : ''}"><td>${longDate(d)}</td><td class="r">${fmt(x.n)}</td><td class="r">${fmt(x.miss)}</td><td class="r">${pcs(x.rate)}</td><td class="r">%${f1(x.mean)}</td><td class="r">${fmt(x.hi)} (${pcs(x.hiShare)})</td></tr>`; }).join('')}</table>`;
}

function fmtWhen(iso, time, minus) {
  const d = new Date(iso + 'T' + time + ':00');
  d.setHours(d.getHours() - minus);
  return d.toLocaleDateString('tr-TR', { day: '2-digit', month: 'long', year: 'numeric' }) + ' · ' + d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
}
// Patient inbox: confirmations only (no group or rule information).
function inboxHtml() {
  if (!myBookings().length) return '<p style="color:var(--mute);margin:0">Mesaj yok.</p>';
  return '<table>' + myBookings().map((b) => `<tr><td><b>Randevu onayı</b><br><small style="opacity:.75">“Randevunuz alındı: ${fmtWhen(b.iso, b.time, 0)}. Gelemeyecekseniz lütfen iptal edin.”</small></td></tr>`).join('') + '</table>';
}
// Management: message schedule of one appointment, with the A/B explanation.
function msgTable(iso, time) {
  return `<table><tr><th>Mesaj</th><th>Gönderim</th><th>Durum</th></tr>
 <tr><td><b>Onay</b><br><small style="opacity:.75">“Randevunuz alındı: ${fmtWhen(iso, time, 0)}. Gelemeyecekseniz lütfen iptal edin.”</small></td><td>Randevu alındıktan sonra ${REM.confirmation_within_min} dk içinde</td><td>Bekliyor</td></tr>
 <tr><td><b>Hatırlatma</b><br><small style="opacity:.75">“Randevunuz yarın: ${fmtWhen(iso, time, 0)}.”</small></td><td>${fmtWhen(iso, time, REM.hours_before)} (${REM.hours_before} saat önce)</td><td>Bekliyor</td></tr></table>
 <p style="margin:10px 0 0;font-size:12px;opacity:.8">Hatırlatma A/B testinde hastanın grubu yalnızca hastaya bağlıdır: <b>hatırlatma</b> grubu iki mesajı da alır, <b>kontrol</b> grubu yalnızca onay mesajını alır. Randevuya ${REM.hours_before} saatten az kaldıysa hatırlatma planlanmaz ve grup atanmaz.</p>`;
}
function abTable() {
  const g = AB.groups;
  return `<table><tr><th>Grup</th><th class="r">Randevu</th><th class="r">Gelmeyen</th><th class="r">Gelmeme oranı</th></tr>
 ${g.map((x) => `<tr><td>${x.group === 'reminder' ? 'Hatırlatma' : 'Kontrol'}</td><td class="r">${fmt(x.appointments)}</td><td class="r">${fmt(x.no_shows)}</td><td class="r"><b>${pcs(x.no_show_rate)}</b></td></tr>`).join('')}</table>
 <p style="margin:10px 0 0">Fark (kontrol − hatırlatma): <b>${(AB.difference * 100).toLocaleString('tr-TR', { minimumFractionDigits: 1 })} puan</b> · z = ${AB.z.toLocaleString('tr-TR')} · p ${AB.p_value < 0.001 ? '' : '= '}${pv(AB.p_value)}</p>
 <p style="margin:8px 0 0;font-size:12px;opacity:.8"><b>Bu gerçek bir deney değil.</b> Veri setindeki “SMS_received” alanı kullanıldı; gruplar rastgele seçilmedi, bu yüzden fark nedensel okunamaz (SMS alanların gelmeme oranı daha yüksek). Ekran, <code>GET /ab/summary</code> yanıtıyla aynı alanları gösterir; gerçek test başladığında aynı tablo canlı doldurulur. Aynı hastanın randevuları bağımsız olmadığından yönetim ekranında “hasta başına” seçeneği de sunulmalıdır.</p>`;
}

// Management: decision text of one booking.
const decisionText = (b) => (b.kind === 'extra' ? `slottaki 1. hastanın riski ≥ eşik %${THR}` : 'Normal randevu (slot boştu)');
// Staff: calendar helpers shared by both designs.
const dayTag = (i) => (DATA_DAYS.has(i) ? 'kayıt' : i === TODAY ? 'bugün' : '');

// ---- Entry page (demo only). No real authentication: the accounts below are mock-up data. ----
// Patient: form only. Department: demo account. Management: demo access code.
const DEMO_DEPARTMENT={user:'doktor',pass:'doktor123',code:'DR-001'},DEMO_ADMIN_CODE='YON-2026';
const GATE_CSS=`.gate{position:fixed;inset:0;z-index:100;background:var(--bg,#f6f4ef);color:var(--ink,#1f2a2e);display:flex;align-items:center;justify-content:center;padding:16px;overflow:auto;font-family:inherit}
.gate .gc{width:min(440px,100%);background:var(--card,#fff);border:1px solid var(--line,#ddd);border-radius:16px;padding:26px;box-shadow:0 8px 28px rgba(0,0,0,.08)}
.gate h1{margin:0 0 4px;font-size:24px;text-align:center}.gate p.sub{margin:0 0 20px;text-align:center;color:var(--mute,#6b777c);font-size:14px}
.gate .big{display:block;width:100%;margin:10px 0;padding:14px;font:inherit;font-size:16px;font-weight:600;border-radius:12px;border:1px solid var(--line,#ddd);background:var(--soft,#eee);color:var(--ink,#1f2a2e);cursor:pointer}
.gate .big:hover{border-color:var(--acc,var(--brand,#0f766e))}
.gate label{display:block;margin:12px 0 4px;font-size:13px;font-weight:600}.gate input[type=text],.gate input[type=password],.gate input[type=date]{width:100%;box-sizing:border-box;padding:10px;font:inherit;border-radius:8px;border:1px solid var(--line,#ddd);background:var(--bg,#fff);color:inherit}
.gate .yn{display:flex;gap:16px;font-weight:400}.gate .yn label{margin:0;font-weight:400;display:flex;gap:6px;align-items:center}
.gate .row{display:flex;gap:10px;margin-top:20px}.gate .row button{flex:1;padding:11px;font:inherit;font-weight:600;border-radius:10px;border:1px solid var(--line,#ddd);cursor:pointer;background:transparent;color:inherit}
.gate .row button.go{background:var(--acc,var(--brand,#0f766e));border-color:transparent;color:#fff}
.gate .err{color:var(--red,#c0392b);font-size:13px;margin-top:10px;min-height:16px}.gate .hint{margin-top:12px;font-size:12px;color:var(--mute,#6b777c);background:var(--soft,#eee);padding:8px 10px;border-radius:8px}`;
const Gate={
  start(cfg){ // cfg: {hospital, enter(role), roleButtons:[{el,role}], ribbon}
    const st=document.createElement('style');st.textContent=GATE_CSS;document.head.appendChild(st);
    const g=document.createElement('div');g.className='gate';document.body.appendChild(g);
    const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
    const back='<button type="button" data-a="home">Geri</button>';
    const screens={
      home:()=>`<div class="gc"><h1>${esc(cfg.hospital)}</h1><p class="sub">Randevu sistemi · giriş türünü seçin</p>
        <button class="big" data-a="patient">Randevu Oluştur</button><button class="big" data-a="doctor">Doktor Girişi</button><button class="big" data-a="admin">Yönetici Girişi</button></div>`,
      patient:()=>`<form class="gc" data-f="patient"><h1>Randevu Oluştur</h1><p class="sub">Başlamak için bilgilerinizi girin</p>
        <label>İsim Soyisim</label><input type="text" name="name" autocomplete="off">
        <label>Bilinen hastalık var mı?</label><div class="yn"><label><input type="radio" name="ill" value="hayir" checked>Hayır</label><label><input type="radio" name="ill" value="evet">Evet</label></div>
        <div id="illw" style="display:none"><label>Hastalığınız nedir?</label><input type="text" name="illtext" autocomplete="off"></div>
        <label>Doğum tarihi</label><input type="date" name="birth"><label>Mahalle</label><input type="text" name="hood" autocomplete="off">
        <div class="err"></div><div class="row">${back}<button class="go" type="submit">Devam</button></div></form>`,
      doctor:()=>`<form class="gc" data-f="doctor"><h1>Doktor Girişi</h1><p class="sub">Departman paneline giriş</p>
        <label>Kullanıcı adı</label><input type="text" name="user" autocomplete="off"><label>Şifre</label><input type="password" name="pass" autocomplete="off">
        <label>Doktor ünvan kodu</label><input type="text" name="code" autocomplete="off">
        <div class="err"></div><div class="hint">Demo hesap: kullanıcı adı <b>${DEMO_DEPARTMENT.user}</b> · şifre <b>${DEMO_DEPARTMENT.pass}</b> · ünvan kodu <b>${DEMO_DEPARTMENT.code}</b></div>
        <div class="row">${back}<button class="go" type="submit">Giriş</button></div></form>`,
      admin:()=>`<form class="gc" data-f="admin"><h1>Yönetici Girişi</h1><p class="sub">Tüm sayfalara erişim</p>
        <label>Erişim kodu</label><input type="password" name="code" autocomplete="off">
        <div class="err"></div><div class="hint">Demo yönetici erişim kodu: <b>${DEMO_ADMIN_CODE}</b></div>
        <div class="row">${back}<button class="go" type="submit">Giriş</button></div></form>`};
    const show=n=>{g.innerHTML=screens[n]();g.style.display='flex';
      g.querySelectorAll('[data-a]').forEach(b=>b.onclick=()=>show(b.dataset.a));
      g.querySelectorAll('input[name=ill]').forEach(r=>r.onchange=()=>{g.querySelector('#illw').style.display=g.querySelector('input[name=ill]:checked').value==='evet'?'block':'none';});
      const f=g.querySelector('form');if(f)f.onsubmit=e=>{e.preventDefault();const v=Object.fromEntries(new FormData(f));const err=m=>{f.querySelector('.err').textContent=m;};
        if(f.dataset.f==='patient'){if(!v.name.trim()||!v.birth||!v.hood.trim())return err('İsim soyisim, doğum tarihi ve mahalle zorunludur.');
          if(v.ill==='evet'&&!v.illtext.trim())return err('Hastalığınızı yazın.');
          return login('hasta',{name:v.name.trim(),ill:v.ill==='evet'?v.illtext.trim():'',birth:v.birth,hood:v.hood.trim()});}
        if(f.dataset.f==='doctor'){if(v.user!==DEMO_DEPARTMENT.user||v.pass!==DEMO_DEPARTMENT.pass||v.code.trim().toUpperCase()!==DEMO_DEPARTMENT.code)return err('Kullanıcı adı, şifre veya ünvan kodu hatalı.');
          return login('departman',{name:'Dr. '+v.user});}
        if(v.code.trim().toUpperCase()!==DEMO_ADMIN_CODE)return err('Erişim kodu hatalı.');return login('yonetim',{name:'Yönetici'});};};
    const login=(role,who)=>{window.SESSION={role,who};g.style.display='none';
      const allowed=role==='yonetim'?['hasta','departman','yonetim']:[role];
      cfg.roleButtons().forEach(({el,role:r})=>{el.style.display=allowed.includes(r)?'':'none';});
      cfg.setUser(who.name,role,()=>{window.SESSION=null;show('home');});cfg.enter(role);};
    show('home');
  }};
