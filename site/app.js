(() => {
  const page = document.body.dataset.page;

  // Old links from the single-page version (#/r/slug, #/?q=…) → the real pages.
  const old = location.hash.match(/^#\/r\/([^?&#]+)/);
  if (old) { location.replace(`r/${old[1]}/`); return; }
  const oldQ = location.hash.match(/^#\/\?q=([^&#]*)/);
  if (oldQ) { location.replace(`./?q=${oldQ[1]}`); return; }

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
    if (root.dataset.typed) return;
    root.dataset.typed = "1";
    const rand = rng(seed);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) if (walker.currentNode.nodeValue.trim()) nodes.push(walker.currentNode);
    for (const node of nodes) {
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
      const frag = document.createDocumentFragment();
      frag.append(sr, shown);
      node.parentNode.replaceChild(frag, node);
    }
  }
  const typeAll = (sel, seed, strength) =>
    document.querySelectorAll(sel).forEach((el, i) => typeset(el, `${seed}:${i}`, strength));

  if (page === "home") home();
  else if (page === "recipe") recipe();
  else typeAll(".masthead h1, .masthead p", "404", 1);

  // ---------- home: search over the pre-rendered list ----------
  function home() {
    const RECIPES = window.RECIPES || [];
    const plain = (s) => String(s || "").replace(/\[([^\]]+?)\?\]/g, "$1");
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
      const text = { ...r, tags: r.tags.join(" "), from: r.from || "" };
      r._idx = FIELDS.map(([f, w]) => [new Set(words(text[f])), w]);
    }
    function search(q) {
      const terms = words(q);
      if (!terms.length) return null;
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
        if (ok) hits.push([score, r.slug]);
      }
      return hits.sort((a, b) => b[0] - a[0]).map((h) => h[1]);
    }

    const list = document.getElementById("list");
    const entries = [...list.querySelectorAll(".entry")];
    const original = [...list.children];
    const bySlug = new Map(entries.map((e) => [e.dataset.slug, e]));
    const input = document.getElementById("q");
    const count = document.getElementById("count");
    const empty = document.getElementById("empty");
    const clear = document.getElementById("clear");

    // keep the chip counts in step with how search really behaves
    document.querySelectorAll(".shelf[aria-label=Popular] .chip").forEach((c) => {
      const small = c.querySelector("small");
      if (small) small.textContent = (search(c.dataset.q) || []).length;
    });

    function render(q) {
      const slugs = search(q);
      clear.hidden = !q;
      document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("on", !!q && norm(c.dataset.q) === norm(q)));
      if (!slugs) {
        original.forEach((el) => { el.hidden = el === empty; list.appendChild(el); });
        count.textContent = `All ${entries.length} recipes, A to Z`;
        return;
      }
      original.forEach((el) => (el.hidden = true));
      slugs.forEach((s) => { const el = bySlug.get(s); el.hidden = false; list.appendChild(el); });
      list.appendChild(empty);
      empty.hidden = slugs.length > 0;
      empty.textContent = `Nothing in the recipe box matches “${q}”. Try one ingredient, like “butter” or “chicken”.`;
      count.textContent = `${slugs.length} ${slugs.length === 1 ? "recipe" : "recipes"} for “${q}”`;
      slugs.slice(0, 40).forEach((s) => typeset(bySlug.get(s).querySelector(".t"), s, 0.9));
    }

    const q0 = new URLSearchParams(location.search).get("q") || "";
    input.value = q0;
    render(q0);
    let timer;
    input.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const v = input.value.trim();
        history.replaceState(null, "", v ? `?q=${encodeURIComponent(v)}` : location.pathname);
        render(v);
      }, 90);
    });
    input.form.addEventListener("submit", (e) => e.preventDefault());
    clear.onclick = () => { input.value = ""; history.replaceState(null, "", location.pathname); render(""); input.focus(); };
    document.getElementById("surprise").onclick = () => {
      location.href = `r/${entries[Math.floor(Math.random() * entries.length)].dataset.slug}/`;
    };
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.activeElement !== input) { e.preventDefault(); input.focus(); }
    });

    typeAll(".masthead h1", "masthead", 1.3);
    typeAll(".masthead p, .search label, .shelf .lead, .foot", "home", 0.8);
    // Type the visible titles first, the rest when the browser has a moment.
    const titles = entries.map((e) => [e.querySelector(".t"), e.dataset.slug]);
    titles.slice(0, 30).forEach(([el, s]) => typeset(el, s, 0.9));
    const rest = titles.slice(30);
    const idle = window.requestIdleCallback || ((f) => setTimeout(f, 50));
    (function more() { rest.splice(0, 40).forEach(([el, s]) => typeset(el, s, 0.9)); if (rest.length) idle(more); })();
  }

  // ---------- recipe page ----------
  function recipe() {
    const slug = document.body.dataset.slug;
    typeAll(".card h1", slug + ":title", 1.15);
    typeAll(".card .from, .card-body h2, .card-body h3, .card-body li", slug);
    typeAll(".receipts h2, .receipts p, .photo .cap", slug + ":rc", 0.8);
    const tilt = rng(slug);
    document.querySelectorAll(".photo").forEach((b) => b.style.setProperty("--tilt", `${((tilt() - 0.5) * 4).toFixed(2)}deg`));

    document.getElementById("print").onclick = () => window.print();
    // Going back to the list keeps your search and scroll position.
    const back = document.getElementById("back");
    try {
      const ref = new URL(document.referrer);
      if (ref.origin === location.origin && new URL(back.href).pathname === ref.pathname) {
        back.addEventListener("click", (e) => { e.preventDefault(); history.back(); });
      }
    } catch { /* no referrer */ }

    const photos = [...document.querySelectorAll(".photo")].map((b) => ({ full: b.dataset.full, label: b.dataset.label }));
    document.querySelectorAll(".photo").forEach((b, i) => b.addEventListener("click", () => openLightbox(i)));

    const lb = document.getElementById("lightbox"), stage = document.getElementById("lbStage"), img = document.getElementById("lbImg");
    const st = { i: 0, s: 1, fit: 1, tx: 0, ty: 0 };
    const title = document.body.dataset.title;
    function openLightbox(i) { lb.hidden = false; document.body.style.overflow = "hidden"; show(i); document.getElementById("lbClose").focus(); }
    function close() { lb.hidden = true; document.body.style.overflow = ""; img.removeAttribute("src"); }
    function show(i) {
      st.i = (i + photos.length) % photos.length;
      const ph = photos[st.i];
      img.onload = fit;
      img.src = ph.full;
      img.alt = `${title}, ${ph.label || "card"}`;
      document.getElementById("lbLabel").textContent = `${title} · ${ph.label || ""}`;
      document.getElementById("lbPrev").disabled = document.getElementById("lbNext").disabled = photos.length < 2;
    }
    function apply() {
      img.style.transform = `translate(-50%, -50%) translate(${st.tx}px, ${st.ty}px) scale(${st.s})`;
      stage.classList.toggle("zoomed", st.s > st.fit * 1.05);
    }
    function fit() {
      if (!img.naturalWidth) return;
      st.fit = Math.min((stage.clientWidth - 32) / img.naturalWidth, (stage.clientHeight - 32) / img.naturalHeight, 1.5);
      st.s = st.fit; st.tx = st.ty = 0; apply();
    }
    function zoomAt(f, cx, cy) {
      const ns = Math.min(st.fit * 6, Math.max(st.fit, st.s * f));
      const k = ns / st.s;
      st.tx = cx - (cx - st.tx) * k; st.ty = cy - (cy - st.ty) * k; st.s = ns;
      if (ns === st.fit) st.tx = st.ty = 0;
      apply();
    }
    const center = (e) => { const b = stage.getBoundingClientRect(); return [e.clientX - b.left - b.width / 2, e.clientY - b.top - b.height / 2]; };
    stage.addEventListener("wheel", (e) => { e.preventDefault(); const [x, y] = center(e); zoomAt(Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.002)), x, y); }, { passive: false });
    let drag = null;
    stage.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, tx: st.tx, ty: st.ty, moved: false }; stage.setPointerCapture(e.pointerId); });
    stage.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
      if (drag.moved && st.s > st.fit) { stage.classList.add("dragging"); st.tx = drag.tx + dx; st.ty = drag.ty + dy; apply(); }
    });
    stage.addEventListener("pointerup", (e) => {
      if (drag && !drag.moved) {
        const b = img.getBoundingClientRect();
        const onImage = e.clientX >= b.left && e.clientX <= b.right && e.clientY >= b.top && e.clientY <= b.bottom;
        if (!onImage) close();
        else if (st.s > st.fit * 1.05) fit();
        else { const [x, y] = center(e); zoomAt(2.5, x, y); }
      }
      drag = null; stage.classList.remove("dragging");
    });
    document.getElementById("lbClose").onclick = close;
    document.getElementById("lbPrev").onclick = () => show(st.i - 1);
    document.getElementById("lbNext").onclick = () => show(st.i + 1);
    window.addEventListener("resize", () => { if (!lb.hidden) fit(); });
    document.addEventListener("keydown", (e) => {
      if (lb.hidden) return;
      if (e.key === "Escape") close();
      else if (e.key === "ArrowLeft") show(st.i - 1);
      else if (e.key === "ArrowRight") show(st.i + 1);
    });
  }
})();
