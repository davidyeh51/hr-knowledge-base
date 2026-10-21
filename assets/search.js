(function(){
var idx=[],q=document.getElementById('q'),res=document.getElementById('results'),map=document.getElementById('map'),chips=document.getElementById('chips'),dom='';
fetch('search-index.json').then(function(r){return r.json()}).then(function(d){idx=d;init();});
function esc(s){return s.replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function init(){
 var ds=[];idx.forEach(function(e){if(ds.indexOf(e.domain)<0)ds.push(e.domain)});
 chips.innerHTML='<button data-d="" class="on">全部領域</button>'+ds.map(function(d){return '<button data-d="'+esc(d)+'">'+esc(d)+'</button>'}).join('');
 chips.onclick=function(e){var b=e.target.closest('button');if(!b)return;dom=b.dataset.d;[].forEach.call(chips.children,function(c){c.classList.toggle('on',c===b)});run();};
 q.addEventListener('input',run);
 var p=new URLSearchParams(location.search).get('q');if(p){q.value=p;}run();
}
function terms(s){return s.toLowerCase().split(/[\s,，、]+/).filter(Boolean)}
function run(){
 var ts=terms(q.value);
 if(!ts.length&&!dom){res.classList.add('hidden');map.classList.remove('hidden');return;}
 var out=[];
 idx.forEach(function(e){
  if(dom&&e.domain!==dom)return;
  var hay=(e.title+' '+e.text+' '+e.deck+' '+e.author+' '+e.type).toLowerCase(),sc=0;
  for(var i=0;i<ts.length;i++){if(hay.indexOf(ts[i])<0)return;
   if(e.title.toLowerCase().indexOf(ts[i])>=0)sc+=5;if(e.deck.toLowerCase().indexOf(ts[i])>=0)sc+=3;if(e.type.toLowerCase().indexOf(ts[i])>=0)sc+=2;sc+=1;}
  out.push({e:e,s:sc});});
 out.sort(function(a,b){return b.s-a.s});
 map.classList.add('hidden');res.classList.remove('hidden');
 var h='<div class="rinfo">找到 <b>'+out.length+'</b> 筆結果'+(dom?'（'+esc(dom)+'）':'')+'　<a href="#" id="clr" style="color:#D97706">清除搜尋</a></div>';
 out.slice(0,60).forEach(function(o){var e=o.e;
  h+='<a class="hit" href="'+e.url+(e.n>1?'#s'+e.n:'')+'"><div class="where">'+esc(e.domain)+' · 《'+esc(e.deck)+'》· '+esc(e.type)+(e.n>1?' · 第'+e.n+'頁':'')+'</div><h5>'+hl(esc(e.title),ts)+'</h5><p>'+snip(e.text,ts)+'</p></a>';});
 res.innerHTML=h;
 document.getElementById('clr').onclick=function(ev){ev.preventDefault();q.value='';dom='';[].forEach.call(chips.children,function(c,i){c.classList.toggle('on',i===0)});run();};
}
function snip(t,ts){var l=t.toLowerCase(),p=-1;for(var i=0;i<ts.length;i++){var k=l.indexOf(ts[i]);if(k>=0){p=k;break}}
 var s=Math.max(0,p-30),r=t.substr(s,130);return (s>0?'…':'')+hl(esc(r),ts)+(s+130<t.length?'…':'');}
function hl(s,ts){ts.forEach(function(t){if(!t)return;var re=new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/&/g,'&amp;'),'gi');s=s.replace(re,function(m){return '<mark>'+m+'</mark>'})});return s;}
})();
