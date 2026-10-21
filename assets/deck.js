(function(){
var slides=[].slice.call(document.querySelectorAll('.slide')),cur=0,stage=document.getElementById('stage'),vp=document.getElementById('viewport');
function fit(){var s=Math.min(vp.clientWidth/1280,vp.clientHeight/720)*0.98;stage.style.transform='translate(-50%,-50%) scale('+s+')';}
function go(i){cur=Math.max(0,Math.min(slides.length-1,i));slides.forEach(function(s,k){s.classList.toggle('active',k===cur)});
 document.getElementById('progbar').style.width=((cur+1)/slides.length*100)+'%';history.replaceState(null,'','#s'+(cur+1));}
function hashIdx(){var m=location.hash.match(/#s(\d+)/);return m?parseInt(m[1])-1:0;}
document.getElementById('prev').onclick=function(){go(cur-1)};document.getElementById('next').onclick=function(){go(cur+1)};
var toc=document.getElementById('toc');
document.getElementById('btnList').onclick=function(){toc.classList.toggle('hidden')};
document.getElementById('btnNotes').onclick=function(){document.body.classList.toggle('shownotes')};
document.getElementById('btnFs').onclick=function(){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()};
toc.addEventListener('click',function(e){var a=e.target.closest('a');if(a){e.preventDefault();go(+a.dataset.go);toc.classList.add('hidden')}});
document.addEventListener('keydown',function(e){var k=e.key;
 if(k==='ArrowRight'||k==='PageDown'||k===' ')go(cur+1);else if(k==='ArrowLeft'||k==='PageUp')go(cur-1);
 else if(k==='Home')go(0);else if(k==='End')go(slides.length-1);
 else if(k==='n'||k==='N')document.body.classList.toggle('shownotes');else if(k==='g'||k==='G')toc.classList.toggle('hidden');
 else if(k==='f'||k==='F')document.getElementById('btnFs').click();});
var tx=null;vp.addEventListener('touchstart',function(e){tx=e.touches[0].clientX});
vp.addEventListener('touchend',function(e){if(tx===null)return;var d=e.changedTouches[0].clientX-tx;if(Math.abs(d)>50)go(cur+(d<0?1:-1));tx=null});
window.addEventListener('resize',fit);window.addEventListener('hashchange',function(){go(hashIdx())});
fit();go(hashIdx());
})();
