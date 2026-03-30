// Animations initializer for GestorPV
// Observa elementos con `data-animate="..."` o `data-animate-child` para staggering
(function(){
  const prefs = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(prefs) return; // no animations if user prefers reduced motion

  function whenVisible(el, cb){
    if(!('IntersectionObserver' in window)){
      cb(el); return;
    }
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(en =>{
        if(en.isIntersecting){ cb(en.target); obs.unobserve(en.target); }
      });
    }, {threshold: 0.09});
    io.observe(el);
  }

  function initElement(el){
    const type = el.dataset.animate || '';
    // map dataset values to classes
    if(type === 'page'){
      el.classList.add('gpv-page');
      // small timeout to allow paint
      requestAnimationFrame(()=> setTimeout(()=> el.classList.add('gpv-in'), 30));
      return;
    }

    // For specific animation types, add marker classes
    const map = {
      'fade-up': 'gpv-fade-up',
      'slide-left': 'gpv-slide-left',
      'scale-in': 'gpv-scale-in',
      'pulse': 'gpv-pulse',
      'stagger': 'gpv-stagger'
    };
    const cls = map[type] || map['fade-up'];
    el.classList.add('gpv-anim');
    if(cls) el.classList.add(cls);

    whenVisible(el, (target) => {
      // if it's a stagger container, add gpv-in to parent to reveal children
      if(type === 'stagger'){
        // assign index vars for children
        Array.from(target.children).forEach((ch, i) => ch.style.setProperty('--i', i));
        target.classList.add('gpv-in');
      } else {
        target.classList.add('gpv-in');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    // auto-initialize elements with data-animate
    const els = document.querySelectorAll('[data-animate]');
    els.forEach(el => initElement(el));

    // convenience: also enable data-animate-child on immediate children
    document.querySelectorAll('[data-animate-child]').forEach(container => {
      Array.from(container.children).forEach(ch => {
        if(!ch.hasAttribute('data-animate')) ch.setAttribute('data-animate', container.dataset.animateChild || 'fade-up');
      });
      // init children
      Array.from(container.children).forEach(ch => initElement(ch));
    });
  });
})();
