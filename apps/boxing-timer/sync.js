/* Interval Timer — optional cloud sync (Phase 2).
   Loads no network code and does nothing until the user connects a Supabase
   backend in Settings. Offline-first: localStorage stays the source of truth. */
(function(){
  "use strict";
  var CFG_KEY="itBackend", SYNC_KEY="itSyncAt";
  var SUPA_ESM="https://esm.sh/@supabase/supabase-js@2";
  var sb=null, user=null, container=null, status="";

  function cfg(){try{return JSON.parse(localStorage.getItem(CFG_KEY)||"null");}catch(e){return null;}}
  function setCfg(c){try{localStorage.setItem(CFG_KEY,JSON.stringify(c));}catch(e){}}
  function configured(){var c=cfg();return !!(c&&c.url&&c.anonKey);}

  async function ensureClient(){
    if(sb) return sb;
    var c=cfg(); if(!c) return null;
    var mod=await import(SUPA_ESM);
    sb=mod.createClient(c.url,c.anonKey,{auth:{persistSession:true,detectSessionInUrl:true,autoRefreshToken:true}});
    return sb;
  }

  async function init(){
    if(!configured()){ render(); return; }
    try{
      await ensureClient();
      var r=await sb.auth.getSession();
      user=(r.data&&r.data.session)?r.data.session.user:null;
      sb.auth.onAuthStateChange(function(_e,session){user=session?session.user:null;render();if(user)syncNow();});
      render();
      if(user) syncNow();
    }catch(e){status="Backend error: "+(e&&e.message||e); render();}
  }

  function el(html){var d=document.createElement("div");d.innerHTML=html;return d.firstElementChild;}
  function render(){
    if(!container) return;
    container.innerHTML="";
    if(!configured()){
      var b=el('<button class="clearbtn" style="text-decoration:none">☁️ Connect cloud backend</button>');
      b.addEventListener("click",connectFlow); container.appendChild(b); return;
    }
    if(!user){
      var box=el('<div><input id="__itEmail" type="email" inputmode="email" placeholder="you@email.com" style="width:100%;padding:12px;border-radius:10px;border:none;background:var(--panel-2);color:var(--text);font-size:15px;margin-bottom:8px"><button class="primary-btn" id="__itSignin" style="font-size:16px;padding:14px">Email me a sign-in link</button><div style="color:var(--muted);font-size:12px;margin-top:8px">'+esc(status)+'</div></div>');
      container.appendChild(box);
      box.querySelector("#__itSignin").addEventListener("click",function(){signIn(box.querySelector("#__itEmail").value.trim());});
      return;
    }
    var when=localStorage.getItem(SYNC_KEY);
    var line=status||(when?("Last sync: "+new Date(when).toLocaleString()):"Not synced yet");
    var s=el('<div><div class="setrow"><div><div class="lbl">Signed in</div><div class="hint2">'+esc(user.email||"account")+'</div></div><button class="clearbtn" id="__itOut" style="text-decoration:none">Sign out</button></div><button class="primary-btn" id="__itSync" style="font-size:16px;padding:14px;margin-top:6px">Sync now</button><div style="color:var(--muted);font-size:12px;margin-top:8px">'+esc(line)+'</div></div>');
    container.appendChild(s);
    s.querySelector("#__itOut").addEventListener("click",signOut);
    s.querySelector("#__itSync").addEventListener("click",function(){syncNow(true);});
  }
  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c];});}

  function connectFlow(){
    var url=prompt("Paste your Supabase Project URL\n(looks like https://xxxx.supabase.co):","");
    if(!url) return;
    var key=prompt("Paste your Supabase anon / public key\n(Project Settings → API → anon public):","");
    if(!key) return;
    setCfg({url:url.trim(),anonKey:key.trim()}); sb=null; status="Connecting…"; render(); init();
  }
  async function signIn(email){
    if(!email){status="Enter your email first.";render();return;}
    try{
      await ensureClient(); status="Sending link…"; render();
      var redirect=location.href.split("#")[0];
      var r=await sb.auth.signInWithOtp({email:email,options:{emailRedirectTo:redirect}});
      status=r.error?("Error: "+r.error.message):"Check your email for the sign-in link, then reopen this page.";
      render();
    }catch(e){status="Error: "+(e&&e.message||e);render();}
  }
  async function signOut(){try{if(sb)await sb.auth.signOut();}catch(e){} user=null; status=""; render();}

  function loadLS(k){try{return JSON.parse(localStorage.getItem(k)||"[]");}catch(e){return[];}}
  function saveLS(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}

  function sessionToRow(e){return{user_id:user.id,client_id:String(e.id),sport:e.sport,mode:e.mode,started_at:e.ts,ended_at:e.end||null,duration_sec:e.durationSec||0,completed:e.completed!==false,detail:Object.assign({},e.detail||{},{_emoji:e.emoji})};}
  function rowToSession(r){var d=r.detail||{},emoji=d._emoji;if(d._emoji!==undefined){d=Object.assign({},d);delete d._emoji;}return{id:isNaN(+r.client_id)?r.client_id:+r.client_id,ts:r.started_at,end:r.ended_at,sport:r.sport,emoji:emoji,mode:r.mode,durationSec:r.duration_sec,completed:r.completed,detail:d};}
  function workoutToRow(w){return{user_id:user.id,client_id:String(w.id),name:w.name,mode:w.mode,emoji:w.emoji,config:{cfg:w.cfg,meta:w.meta}};}
  function rowToWorkout(r){var c=r.config||{};return{id:isNaN(+r.client_id)?r.client_id:+r.client_id,name:r.name,mode:r.mode,emoji:r.emoji,meta:c.meta,cfg:c.cfg};}

  async function syncNow(manual){
    if(!user){if(manual){status="Sign in first.";render();}return;}
    try{
      status="Syncing…"; render();
      var last=localStorage.getItem(SYNC_KEY);
      var localS=loadLS("itSessions"), localW=loadLS("itWorkouts");
      if(localS.length) await sb.from("sessions").upsert(localS.map(sessionToRow),{onConflict:"user_id,client_id"});
      if(localW.length) await sb.from("workouts").upsert(localW.map(workoutToRow),{onConflict:"user_id,client_id"});
      var qs=sb.from("sessions").select("*"); if(last) qs=qs.gt("updated_at",last);
      var qw=sb.from("workouts").select("*"); if(last) qw=qw.gt("updated_at",last);
      var rs=await qs, rw=await qw;
      if(rs.error) throw rs.error; if(rw.error) throw rw.error;
      if(rs.data) mergeById("itSessions", rs.data.map(rowToSession));
      if(rw.data) mergeById("itWorkouts", rw.data.map(rowToWorkout));
      localStorage.setItem(SYNC_KEY,new Date().toISOString());
      status="Last sync: "+new Date().toLocaleString(); render();
      if(window.__itOnPulled) try{window.__itOnPulled();}catch(e){}
    }catch(e){status="Sync error: "+(e&&e.message||e); render();}
  }
  function mergeById(key,incoming){
    var local=loadLS(key), seen={}; local.forEach(function(x){seen[String(x.id)]=true;});
    var added=false;
    incoming.forEach(function(x){if(!seen[String(x.id)]){local.unshift(x);seen[String(x.id)]=true;added=true;}});
    if(added){local.sort(function(a,b){return (new Date(b.ts||0))-(new Date(a.ts||0));}); saveLS(key,local.slice(0,500));}
  }

  window.ITSync={mount:function(c){container=c;render();},configured:configured,syncSoon:function(){if(user)syncNow();}};
  try{ init(); }catch(e){}
})();
