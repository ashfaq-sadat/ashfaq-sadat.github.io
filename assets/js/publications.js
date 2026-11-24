/* Publication list: Google Scholar citation labels, sorting, topic filters,
   copy-citation buttons and the short preview on the home page.

   The list (#pubs) can carry:
     data-limit="3"   show only the first N items (home page preview)
   Sort controls:   buttons with data-sort="recent" | "cited"
   Filter controls: buttons with data-f="all" | a topic from data-t
   Count readout:   an element with id="pub-shown"
*/
(function () {
  var list = document.getElementById('pubs');
  if (!list) return;
  var items = Array.prototype.slice.call(list.querySelectorAll('li'));
  var limit = parseInt(list.getAttribute('data-limit') || '0', 10);
  var state = { sort: 'recent', filter: 'all' };
  var SCHOLAR = 'https://scholar.google.com/citations?user=pQL-hZsAAAAJ&hl=en';

  // ---- Matching Scholar papers to the list, by title words
  function words(t) {
    return (t || '').toLowerCase().normalize('NFKD').replace(/[^a-z0-9 ]+/g, ' ')
      .split(/\s+/).filter(function (w) { return w.length > 2; });
  }
  function similar(a, b) {
    var A = words(a), B = words(b);
    if (!A.length || !B.length) return 0;
    var setB = {};
    B.forEach(function (w) { setB[w] = true; });
    var shared = A.filter(function (w) { return setB[w]; }).length;
    return shared / Math.min(A.length, B.length);
  }
  function label(papers) {
    items.forEach(function (li) {
      var title = li.querySelector('.ptitle').textContent, best = null, score = 0;
      papers.forEach(function (p) {
        var s = similar(title, p.title);
        if (s > score) { score = s; best = p; }
      });
      var n = best && score >= 0.8 ? (best.cited_by || 0) : 0;
      li.setAttribute('data-cites', n);
      if (n > 0 && !li.querySelector('.cites')) {
        var a = document.createElement('a');
        a.className = 'cites';
        a.href = SCHOLAR;
        a.target = '_blank';
        a.rel = 'noopener';
        a.title = 'Citations on Google Scholar';
        a.textContent = 'Cited by ' + n;
        li.querySelector('.meta').appendChild(a);
      }
    });
  }

  // ---- Sort, filter and limit
  function apply() {
    var sorted = items.slice().sort(function (a, b) {
      var ya = +a.getAttribute('data-year'), yb = +b.getAttribute('data-year');
      if (state.sort === 'cited') {
        var d = (+b.getAttribute('data-cites') || 0) - (+a.getAttribute('data-cites') || 0);
        if (d) return d;
      }
      return yb - ya;
    });
    var shown = 0;
    sorted.forEach(function (li) {
      list.appendChild(li);
      var topics = ' ' + li.getAttribute('data-t') + ' ';
      var match = state.filter === 'all' || topics.indexOf(' ' + state.filter + ' ') >= 0;
      var visible = match && (!limit || shown < limit);
      li.hidden = !visible;
      if (visible) shown++;
    });
    var readout = document.getElementById('pub-shown');
    if (readout) readout.textContent = shown === items.length ? 'All ' + shown + ' publications'
      : 'Showing ' + shown + ' of ' + items.length;
  }

  function wire(selector, attr, key) {
    var btns = document.querySelectorAll(selector);
    btns.forEach(function (b) {
      b.addEventListener('click', function () {
        state[key] = b.getAttribute(attr);
        btns.forEach(function (x) {
          var on = x === b;
          x.setAttribute(x.getAttribute('role') === 'tab' ? 'aria-selected' : 'aria-pressed', on ? 'true' : 'false');
        });
        apply();
      });
    });
  }
  wire('[data-sort]', 'data-sort', 'sort');
  wire('[data-f]', 'data-f', 'filter');

  // ---- Copy citation
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
    return new Promise(function (ok, fail) {
      var ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy') ? ok() : fail(); } catch (e) { fail(e); }
      document.body.removeChild(ta);
    });
  }
  list.querySelectorAll('.copy').forEach(function (c) {
    c.addEventListener('click', function () {
      copyText(c.closest('li').getAttribute('data-cite')).then(function () {
        c.textContent = 'Copied';
      }, function () {
        c.textContent = 'Copy failed';
      }).then(function () {
        setTimeout(function () { c.textContent = 'Copy citation'; }, 1800);
      });
    });
  });

  // ---- Topic counts on filter buttons
  document.querySelectorAll('[data-f]').forEach(function (b) {
    var f = b.getAttribute('data-f');
    var n = f === 'all' ? items.length : items.filter(function (li) {
      return (' ' + li.getAttribute('data-t') + ' ').indexOf(' ' + f + ' ') >= 0;
    }).length;
    var c = document.createElement('span');
    c.className = 'count';
    c.textContent = n;
    b.appendChild(c);
  });

  apply();

  // ---- Citation counts (and totals on the publications page) from the weekly Scholar refresh
  fetch(list.getAttribute('data-scholar') || 'assets/data/scholar.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      if (!d) return;
      if (d.papers && d.papers.length) { label(d.papers); apply(); }
      var totals = document.getElementById('pub-totals');
      if (totals && typeof d.citations === 'number') {
        var bits = [d.citations.toLocaleString('en') + ' citations'];
        if (typeof d.h_index === 'number') bits.push('h-index ' + d.h_index);
        if (typeof d.i10_index === 'number') bits.push('i10-index ' + d.i10_index);
        totals.textContent = bits.join(' · ') + ' on Google Scholar';
        totals.hidden = false;
      }
    })
    .catch(function () { });
})();
