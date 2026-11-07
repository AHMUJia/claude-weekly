(() => {
  'use strict';
  const scenes = [...document.querySelectorAll('.scene')];
  const chapterButtons = [...document.querySelectorAll('[data-page]')];
  const previous = document.getElementById('previous-page');
  const next = document.getElementById('next-page');
  const viewToggle = document.getElementById('view-toggle');
  const dialog = document.getElementById('record-dialog');
  const records = [...document.querySelectorAll('.record')];
  const recordMenu = [...document.querySelectorAll('.record-menu [data-record]')];
  let current = 0;
  let continuous = false;
  let framePending = false;
  let recordOpener = null;
  let printing = false;

  function updatePage(index) {
    current = Math.max(0, Math.min(index, scenes.length - 1));
    scenes.forEach((scene, i) => scene.classList.toggle('current', i === current));
    chapterButtons.forEach(button => {
      const active = Number(button.dataset.page) === current;
      button.classList.toggle('active', active);
      if (active) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
    previous.disabled = current === 0;
    next.disabled = current === scenes.length - 1;
    document.getElementById('page-count').textContent = `${String(current + 1).padStart(2,'0')} / ${String(scenes.length).padStart(2,'0')}`;
  }

  function goTo(index, moveFocus = false) {
    const focused = document.activeElement;
    const wasInScene = focused && focused.closest('.scene');
    updatePage(index);
    if (continuous) scenes[current].scrollIntoView({behavior:'instant',block:'start'});
    else window.scrollTo({top:0,behavior:'instant'});
    document.getElementById('page-status').textContent = `第 ${current + 1} 页：${scenes[current].dataset.title}`;
    if (moveFocus || (wasInScene && !scenes[current].contains(focused))) {
      const title = scenes[current].querySelector('h1');
      title.setAttribute('tabindex','-1');
      title.focus({preventScroll:true});
    }
    // Keep the current chapter reachable in the small-screen horizontal menu.
    const active = document.querySelector('.chapters .active');
    const menu = document.querySelector('.chapters');
    if (active && menu.scrollWidth > menu.clientWidth) {
      menu.scrollTo({left:active.offsetLeft - menu.offsetLeft - menu.clientWidth / 2 + active.offsetWidth / 2,behavior:'instant'});
    }
  }
  chapterButtons.forEach(button => button.addEventListener('click', () => goTo(Number(button.dataset.page))));
  previous.addEventListener('click', () => goTo(current - 1));
  next.addEventListener('click', () => goTo(current + 1));
  document.querySelector('.brand').addEventListener('click', event => {event.preventDefault();goTo(0);});

  viewToggle.addEventListener('click', () => {
    continuous = !continuous;
    document.body.classList.toggle('continuous', continuous);
    viewToggle.setAttribute('aria-pressed',String(continuous));
    viewToggle.textContent = continuous ? '逐页图解' : '连续浏览';
    goTo(current);
  });

  function openRecord(key, opener) {
    const wanted = document.getElementById('record-' + key);
    if (!wanted) return;
    if (!dialog.open) recordOpener = opener;
    records.forEach(record => {record.hidden = record !== wanted;});
    recordMenu.forEach(button => {
      const active = button.dataset.record === key;
      button.classList.toggle('active',active);
      if (active) button.setAttribute('aria-current','page');
      else button.removeAttribute('aria-current');
    });
    document.getElementById('record-title').textContent = recordMenu.find(button=>button.dataset.record===key)?.textContent || '完整记录';
    if (!dialog.open) {dialog.showModal();document.body.style.overflow='hidden';}
    document.querySelector('.record-content').scrollTo({top:0,behavior:'instant'});
  }
  document.querySelectorAll('[data-record]').forEach(button => button.addEventListener('click',()=>openRecord(button.dataset.record,button)));
  document.getElementById('close-records').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click', event => {
    if(event.target !== dialog) return;
    const rect=dialog.getBoundingClientRect();
    if(event.clientX<rect.left || event.clientX>rect.right || event.clientY<rect.top || event.clientY>rect.bottom) dialog.close();
  });
  dialog.addEventListener('close',()=>{document.body.style.overflow='';recordOpener?.focus({preventScroll:true});});

  document.addEventListener('keydown',event=>{
    if(dialog.open || printing || event.altKey || event.ctrlKey || event.metaKey || /INPUT|TEXTAREA|SELECT/.test(event.target.tagName) || event.target.isContentEditable) return;
    if(event.target.closest('.heat-grid')) return;
    if(event.key==='ArrowRight' || event.key==='PageDown'){event.preventDefault();goTo(current+1);}
    if(event.key==='ArrowLeft' || event.key==='PageUp'){event.preventDefault();goTo(current-1);}
  });
  document.querySelectorAll('[data-chart]').forEach(button=>button.addEventListener('click',()=>{
    document.querySelectorAll('[data-chart]').forEach(item=>{const active=item===button;item.classList.toggle('selected',active);item.setAttribute('aria-pressed',String(active));});
    document.querySelectorAll('.daily-chart').forEach(chart=>{chart.hidden=chart.id!=='chart-'+button.dataset.chart;});
  }));
  document.querySelectorAll('[data-share]').forEach(button=>button.addEventListener('click',()=>{
    document.getElementById('share-value').textContent=Number(button.dataset.share).toFixed(1)+'%';
    document.getElementById('share-label').textContent=button.dataset.label;
    document.querySelectorAll('[data-share]').forEach(item=>{const active=item===button;item.classList.toggle('selected',active);item.setAttribute('aria-pressed',String(active));});
  }));
  const heatCells=[...document.querySelectorAll('.heat-cell')];
  const describe=button=>{document.getElementById('heat-readout').textContent=button.dataset.label;};
  heatCells.forEach((button,index)=>{
    button.addEventListener('mouseenter',()=>describe(button));
    button.addEventListener('focus',()=>describe(button));
    button.addEventListener('click',()=>describe(button));
    button.addEventListener('keydown',event=>{
      const delta={ArrowRight:1,ArrowLeft:-1,ArrowDown:24,ArrowUp:-24}[event.key];
      if(delta===undefined) return;
      event.preventDefault();event.stopPropagation();
      const target=Math.max(0,Math.min(heatCells.length-1,index+delta));
      heatCells.forEach((item,i)=>{item.tabIndex=i===target?0:-1;});
      heatCells[target].focus();
    });
  });
  function followScroll(){
    if(!continuous || dialog.open || printing) return;
    const threshold=document.querySelector('.app-header').getBoundingClientRect().bottom+70;
    let index=0;
    scenes.forEach((scene,i)=>{if(scene.getBoundingClientRect().top<=threshold)index=i;});
    updatePage(index);
  }
  window.addEventListener('scroll',()=>{
    if(framePending)return;
    framePending=true;requestAnimationFrame(()=>{framePending=false;followScroll();});
  },{passive:true});
  window.addEventListener('beforeprint',()=>{printing=true;});
  window.addEventListener('afterprint',()=>{printing=false;});
  document.getElementById('print-report').addEventListener('click',()=>window.print());
  updatePage(0);
})();
