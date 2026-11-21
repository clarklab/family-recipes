(() => {
  const RECIPES = window.RECIPES || [];
  const bySlug = new Map(RECIPES.map((r) => [r.slug, r]));
  const byCard = new Map();
  for (const r of RECIPES) {
    if (!byCard.has(r.card)) byCard.set(r.card, []);
    byCard.get(r.card).push(r);
  }
  const app = document.getElementById("app");
  const cardCount = byCard.size;

  // ---------- text helpers ----------
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const plain = (s) => String(s || "").replace(/\[([^\]]+?)\?\]/g, "$1");
  // [word?] = hard to read on the card: show the word, gently underlined
  function inline(s, self) {
    let html = esc(s).replace(/\[([^\]\n]+?)\?\]/g,
      '<span class="unsure" title="Hard to read on the original card — take a look at the card below">$1</span>');
    // "card 0084" → link to the recipe on that card
    html = html.replace(/\b(cards?)\s+((?:(?:\d{4}|loose-\d+)(?:,\s*|\s+and\s+)?)+)/g, (m, word, ids) =>
      word + " " + ids.replace(/\d{4}|loose-\d+/g, (id) => {
        const target = (byCard.get(id) || []).find((r) => r.slug !== self) || (byCard.get(id) || [])[0];
        return target && target.slug !== self ? `<a href="#/r/${target.slug}" title="${esc(plain(target.title))}">${id}</a>` : id;
      }));
    return html;
  }

  // ---------- the hand-typed look ----------
  function rng(seed) {
    let h = 1779033703 ^ seed.length;
    for (let i = 0; i < seed.length; i++) { h = Math.imul(h ^ seed.charCodeAt(i), 3432918353); h = (h << 13) | (h >>> 19); }
    return () => {
      h = Math.imul(h ^ (h >>> 16), 2246822507); h = Math.imul(h ^ (h >>> 13), 3266489909);
      return ((h ^= h >>> 16) >>> 0) / 4294967296;
    };
  }
  function typeset(root, seed, strength = 1) {
    const rand = rng(seed);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) if (walker.currentNode.nodeValue.trim()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      const wrap = document.createDocumentFragment();
      const sr = document.createElement("span");
      sr.className = "sr-only"; sr.textContent = node.nodeValue;
      const shown = document.createElement("span");
      shown.setAttribute("aria-hidden", "true");
      for (const part of node.nodeValue.split(/(\s+)/)) {
        if (!part) continue;
        if (/^\s+$/.test(part)) { shown.appendChild(document.createTextNode(part)); continue; }
        const word = document.createElement("span");
        word.className = "w";
        for (const ch of part) {
          const s = document.createElement("span");
          s.className = "ch";
          const r = (rand() - 0.5) * 3.4 * strength;
          const y = (rand() - 0.5) * 1.8 * strength;
          const o = 1 - rand() * 0.34 * strength;
          const roll = rand();
          if (roll < 0.07) s.classList.add("heavy");
          else if (roll > 0.975) s.classList.add("faint");
          s.style.cssText = `--r:${r.toFixed(2)}deg;--y:${y.toFixed(2)}px;--o:${o.toFixed(2)}`;
          s.textContent = ch;
          word.appendChild(s);
        }
        shown.appendChild(word);
      }
      wrap.append(sr, shown);
      node.parentNode.replaceChild(wrap, node);
    }
  }
  const typeAll = (root, sel, seed, strength) =>
    root.querySelectorAll(sel).forEach((el, i) => typeset(el, `${seed}:${i}`, strength));

  // ---------- search ----------
  const norm = (s) => plain(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
  const stem = (w) => {
    if (w.length > 4 && w.endsWith("ies")) return w.slice(0, -3) + "y";
    if (w.length > 4 && /(ches|shes|oes|sses|xes)$/.test(w)) return w.slice(0, -2);
    if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss")) return w.slice(0, -1);
    return w;
  };
  const words = (s) => norm(s).split(" ").filter(Boolean).map(stem);
  const FIELDS = [["title", 10], ["tags", 6], ["from", 6], ["ingredients", 3], ["notes", 1], ["directions", 1]];
  for (const r of RECIPES) {
    const flat = (groups) => groups.flatMap((g) => [g.heading || "", ...g.items]).join(" ");
    const text = {
      title: r.title, tags: r.tags.join(" "), from: r.from || "",
      ingredients: flat(r.ingredients), notes: r.notes.join(" "), directions: flat(r.directions),
    };
    r._idx = FIELDS.map(([f, w]) => [new Set(words(text[f])), w]);
    r._letter = (norm(r.title)[0] || "#").toUpperCase();
  }
  function search(q) {
    const terms = words(q);
    if (!terms.length) return RECIPES;
    const hits = [];
    for (const r of RECIPES) {
      let score = 0, ok = true;
      for (const t of terms) {
        let best = 0;
        for (const [set, w] of r._idx) {
          if (set.has(t)) best = Math.max(best, w * 1.5);
          else if (t.length >= 3) for (const word of set) if (word.startsWith(t)) { best = Math.max(best, w); break; }
        }
        if (!best) { ok = false; break; }
        score += best;
      }
      if (ok) hits.push([score, r]);
    }
    return hits.sort((a, b) => b[0] - a[0]).map((h) => h[1]);
  }

  const CHIPS = ["cake", "cookies", "pie", "candy", "fudge", "bread", "salad", "casserole", "chili", "soup",
    "chicken", "beef", "chocolate", "apple", "pineapple", "cheese", "pecans", "corn", "green chili", "christmas"];
  const chipCounts = CHIPS.map((c) => [c, search(c).length]).filter(([, n]) => n >= 2);
  const PEOPLE = [...new Set(RECIPES.map((r) => plain(r.from)).filter(Boolean)
    .flatMap((f) => f.split("/").map((x) => x.trim())).filter((x) => x && x.length < 30))].sort();

  // ---------- views ----------
  let homeScroll = 0, searchTimer, lastHome = "#/";
  function route() {
    const h = location.hash;
    let m;
    if ((m = h.match(/^#\/r\/([^?]+)/)) && bySlug.has(decodeURIComponent(m[1]))) return showRecipe(bySlug.get(decodeURIComponent(m[1])));
    const q = (h.match(/[?&]q=([^&]*)/) || [])[1];
    showHome(q ? decodeURIComponent(q.replace(/\+/g, " ")) : "");
  }

  function showHome(q) {
    document.title = "Grammie’s Recipes";
    app.innerHTML = `
      <div class="wrap">
        <header class="masthead">
          <h1>Grammie’s Recipes</h1>
          <p>${RECIPES.length} recipes from the family recipe box, typed up from ${cardCount} original cards.</p>
        </header>
        <div class="search">
          <label for="q">Look something up</label>
          <input id="q" type="search" autocomplete="off" spellcheck="false" value="${esc(q)}"
            placeholder="chicken, cake, pecans, Viki…">
          <button class="clear" id="clear" ${q ? "" : "hidden"} aria-label="Clear search">clear ✕</button>
        </div>
        <nav class="shelf" aria-label="Popular">
          <span class="lead">Try:</span>
          ${chipCounts.map(([c, n]) => `<a class="chip" href="#/?q=${encodeURIComponent(c)}" data-q="${esc(c)}">${esc(c)}<small>${n}</small></a>`).join("")}
        </nav>
        ${PEOPLE.length ? `<nav class="shelf" aria-label="From the kitchen of">
          <span class="lead">From the kitchen of:</span>
          ${PEOPLE.map((p) => `<a class="chip" href="#/?q=${encodeURIComponent(p)}" data-q="${esc(p)}">${esc(p)}</a>`).join("")}
        </nav>` : ""}
        <div class="results-head"><span id="count"></span><button class="surprise" id="surprise">surprise me</button></div>
        <section class="index" id="list"></section>
        <footer class="foot">Every recipe links to a photo of its original card.</footer>
      </div>`;
    typeAll(app, ".masthead h1", "masthead", 1.3);
    typeAll(app, ".masthead p, .search label, .shelf .lead, .foot", "home", 0.8);
    const input = document.getElementById("q");
    input.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        const v = input.value.trim();
        history.replaceState(null, "", v ? `#/?q=${encodeURIComponent(v)}` : "#/");
        renderList(v);
      }, 90);
    });
    document.getElementById("clear").onclick = () => { input.value = ""; history.replaceState(null, "", "#/"); renderList(""); input.focus(); };
    document.getElementById("surprise").onclick = () => {
      location.hash = `#/r/${RECIPES[Math.floor(Math.random() * RECIPES.length)].slug}`;
    };
    renderList(q);
    window.scrollTo(0, homeScroll);
    homeScroll = 0;
  }

  function renderList(q) {
    lastHome = q ? `#/?q=${encodeURIComponent(q)}` : "#/";
    const list = document.getElementById("list");
    const results = search(q);
    document.getElementById("clear").hidden = !q;
    document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("on", norm(c.dataset.q) === norm(q)));
    const count = document.getElementById("count");
    count.textContent = q
      ? `${results.length} ${results.length === 1 ? "recipe" : "recipes"} for “${q}”`
      : `All ${results.length} recipes, A to Z`;
    if (!results.length) {
      list.innerHTML = `<p class="empty">Nothing in the recipe box matches “${esc(q)}”. Try one ingredient, like “butter” or “chicken”.</p>`;
      typeAll(list, ".empty", "empty");
      return;
    }
    let html = "", letter = "";
    for (const r of results) {
      if (!q && r._letter !== letter) { letter = r._letter; html += `<div class="letter">${esc(letter)}</div>`; }
      const seen = new Set();
      const kind = r.tags.filter((t) => { const k = words(t).join(" "); return !seen.has(k) && seen.add(k); }).slice(0, 5).join(" · ");
      html += `<a class="entry" href="#/r/${r.slug}">
        <span class="t">${inline(r.title, r.slug)}</span>
        <span class="who">${r.from ? esc(plain(r.from)) : ""}</span>
        <span class="kind">${esc(kind)}</span></a>`;
    }
    list.innerHTML = html;
    list.querySelectorAll(".entry .t").forEach((el, i) => typeset(el, results[i].slug, 0.9));
  }

  function groupsHTML(groups, ordered, self) {
    return groups.map((g) =>
      (g.heading ? `<h3>${inline(g.heading, self)}</h3>` : "") +
      `<${ordered ? "ol" : "ul"}>${g.items.map((it) => `<li>${inline(it, self)}</li>`).join("")}</${ordered ? "ol" : "ul"}>`
    ).join("");
  }

  function showRecipe(r) {
    homeScroll = document.querySelector(".index") ? window.scrollY : homeScroll;
    document.title = `${plain(r.title)} · Grammie’s Recipes`;
    const tilt = rng(r.slug);
    const same = r.sameCard.map((s) => bySlug.get(s)).filter(Boolean);
    app.innerHTML = `
      <div class="wrap">
        <nav class="topnav">
          <a href="#/" id="back">← the recipe box</a>
          <button id="print">print this recipe</button>
        </nav>
        <article class="card">
          <header class="card-head">
            <h1>${inline(r.title, r.slug)}</h1>
            ${r.from ? `<div class="from">From the kitchen of ${inline(r.from, r.slug)}</div>` : ""}
          </header>
          <div class="card-body">
            ${r.ingredients.length ? `<h2>Ingredients</h2>${groupsHTML(r.ingredients, false, r.slug)}` : ""}
            ${r.directions.length ? `<h2>Directions</h2>${groupsHTML(r.directions, true, r.slug)}` : ""}
            ${r.notes.length ? `<h2>Notes</h2><ul class="notes">${r.notes.map((n) => `<li>${inline(n, r.slug)}</li>`).join("")}</ul>` : ""}
          </div>
        </article>
        ${r.tags.length ? `<div class="filed">Filed under: ${r.tags.map((t) => `<a href="#/?q=${encodeURIComponent(t)}">${esc(t)}</a>`).join(" ")}</div>` : ""}
        ${same.length ? `<div class="also">Also on this card: ${same.map((s) => `<a href="#/r/${s.slug}">${esc(plain(s.title))}</a>`).join(", ")}</div>` : ""}
        ${r.images.length ? `<section class="receipts">
          <h2>The original card</h2>
          <p>Tap a picture to see it up close.</p>
          <div class="photos">
            ${r.images.map((im, i) => `<button class="photo" data-i="${i}" style="--tilt:${((tilt() - 0.5) * 4).toFixed(2)}deg">
              <img src="cards/thumb/${encodeURIComponent(im.file)}" alt="${esc(plain(r.title))}, ${esc(im.label || "card")}" loading="lazy">
              <span class="cap">${esc(im.label || "")}</span></button>`).join("")}
          </div></section>` : ""}
      </div>`;
    typeAll(app, ".card h1", r.slug + ":title", 1.15);
    typeAll(app, ".card .from, .card-body h2, .card-body h3, .card-body li", r.slug);
    typeAll(app, ".receipts h2, .receipts p, .photo .cap", r.slug + ":rc", 0.8);
    document.getElementById("print").onclick = () => window.print();
    document.getElementById("back").href = lastHome;
    app.querySelectorAll(".photo").forEach((b) => b.onclick = () => openLightbox(r, +b.dataset.i));
    window.scrollTo(0, 0);
  }

  // ---------- lightbox ----------
  const lb = document.getElementById("lightbox"), stage = document.getElementById("lbStage"), img = document.getElementById("lbImg");
  const lbState = { r: null, i: 0, s: 1, fit: 1, tx: 0, ty: 0 };
  function openLightbox(r, i) {
    lbState.r = r; lb.hidden = false; document.body.style.overflow = "hidden";
    showSide(i);
    document.getElementById("lbClose").focus();
  }
  function closeLightbox() { lb.hidden = true; document.body.style.overflow = ""; img.removeAttribute("src"); }
  function showSide(i) {
    const ims = lbState.r.images;
    lbState.i = (i + ims.length) % ims.length;
    const im = ims[lbState.i];
    img.onload = fitImage;
    img.src = `cards/${encodeURIComponent(im.file)}`;
    img.alt = `${plain(lbState.r.title)}, ${im.label || "card"}`;
    document.getElementById("lbLabel").textContent = `${plain(lbState.r.title)} · ${im.label || ""}`;
    document.getElementById("lbPrev").disabled = document.getElementById("lbNext").disabled = ims.length < 2;
  }
  function applyLB() {
    img.style.transform = `translate(-50%, -50%) translate(${lbState.tx}px, ${lbState.ty}px) scale(${lbState.s})`;
    stage.classList.toggle("zoomed", lbState.s > lbState.fit * 1.05);
  }
  function fitImage() {
    if (!img.naturalWidth) return;
    lbState.fit = Math.min((stage.clientWidth - 32) / img.naturalWidth, (stage.clientHeight - 32) / img.naturalHeight, 1.5);
    lbState.s = lbState.fit; lbState.tx = lbState.ty = 0; applyLB();
  }
  function zoomAt(f, cx, cy) {
    const ns = Math.min(lbState.fit * 6, Math.max(lbState.fit, lbState.s * f));
    const k = ns / lbState.s;
    lbState.tx = cx - (cx - lbState.tx) * k; lbState.ty = cy - (cy - lbState.ty) * k; lbState.s = ns;
    if (ns === lbState.fit) lbState.tx = lbState.ty = 0;
    applyLB();
  }
  const center = (e) => { const b = stage.getBoundingClientRect(); return [e.clientX - b.left - b.width / 2, e.clientY - b.top - b.height / 2]; };
  stage.addEventListener("wheel", (e) => { e.preventDefault(); const [x, y] = center(e); zoomAt(Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.002)), x, y); }, { passive: false });
  let drag = null;
  stage.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, tx: lbState.tx, ty: lbState.ty, moved: false }; stage.setPointerCapture(e.pointerId); });
  stage.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
    if (drag.moved && lbState.s > lbState.fit) { stage.classList.add("dragging"); lbState.tx = drag.tx + dx; lbState.ty = drag.ty + dy; applyLB(); }
  });
  stage.addEventListener("pointerup", (e) => {
    if (drag && !drag.moved) {
      const b = img.getBoundingClientRect();
      const onImage = e.clientX >= b.left && e.clientX <= b.right && e.clientY >= b.top && e.clientY <= b.bottom;
      if (!onImage) closeLightbox();
      else if (lbState.s > lbState.fit * 1.05) fitImage();
      else { const [x, y] = center(e); zoomAt(2.5, x, y); }
    }
    drag = null; stage.classList.remove("dragging");
  });
  document.getElementById("lbClose").onclick = closeLightbox;
  document.getElementById("lbPrev").onclick = () => showSide(lbState.i - 1);
  document.getElementById("lbNext").onclick = () => showSide(lbState.i + 1);
  window.addEventListener("resize", () => { if (!lb.hidden) fitImage(); });
  document.addEventListener("keydown", (e) => {
    if (lb.hidden) {
      if (e.key === "/" && document.getElementById("q") && document.activeElement.tagName !== "INPUT") { e.preventDefault(); document.getElementById("q").focus(); }
      return;
    }
    if (e.key === "Escape") closeLightbox();
    else if (e.key === "ArrowLeft") showSide(lbState.i - 1);
    else if (e.key === "ArrowRight") showSide(lbState.i + 1);
  });

  window.addEventListener("hashchange", () => { if (!lb.hidden) closeLightbox(); route(); });
  route();
})();
