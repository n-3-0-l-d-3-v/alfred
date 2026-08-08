/**
 * Panel controller. Holds all API calls (this page carries the host
 * permissions); the content script only reads the DOM.
 */
(function () {
  const $ = (id) => document.getElementById(id);
  const ext = LL.ext;

  const state = {
    ctx: null,        // { slug, language, code, ... } from the content script
    sessionId: null,
    card: null,
    hints: [],        // hints revealed this session
    solved: false,
    failedAttempts: 0,
  };

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  function show(paneId) {
    for (const p of ["auth", "notProblem", "main"]) $(p).classList.toggle("hidden", p !== paneId);
  }

  // ---------- context ----------

  async function activeTab() {
    const tabs = await ext.tabs.query({ active: true, currentWindow: true });
    return tabs[0] ?? null;
  }

  async function readContext() {
    const tab = await activeTab();
    if (!tab?.url || !/leetcode\.com\/problems\//.test(tab.url)) return null;
    try {
      return await ext.tabs.sendMessage(tab.id, { type: "LL_EXTRACT" });
    } catch (_) {
      // content script not injected yet (page loaded before the extension)
      return null;
    }
  }

  // ---------- boot ----------

  async function boot() {
    if (!(await LL.api.isSignedIn())) return show("auth");

    const ctx = await readContext();
    if (!ctx?.ok) {
      show("notProblem");
      return;
    }
    state.ctx = ctx;
    show("main");

    try {
      // The adapter reports null when it genuinely could not read the language.
      // Defaulting here rather than in the adapter keeps the guess visible and
      // in one place — silently inventing one is what previously sent
      // "Choose a type" to the API and took static analysis down with it.
      const s = await LL.api.startSession(ctx.slug, ctx.language ?? "python");
      state.sessionId = s.session_id;
      state.solved = s.solved;
      await Promise.all([loadCard(), loadProgress(), loadPersonas()]);
    } catch (e) {
      $("understandBody").innerHTML =
        `<p class="error">${esc(e.message)}</p>` +
        (e.status === 404
          ? `<p class="muted small">There's no Problem Card for <code>${esc(ctx.slug)}</code> yet. The knowledge base currently covers a small seed set.</p>`
          : "");
    }
  }

  // ---------- understand ----------

  async function loadCard() {
    const card = await LL.api.card(state.sessionId);
    state.card = card;
    state.solved = card.solved;

    // LeetCode colours difficulty rather than outlining it; matching that is
    // most of what makes the panel read as part of the page.
    $("contextLabel").textContent = card.title || state.ctx?.slug || "";
    const diff = String(card.difficulty || "").toLowerCase();
    $("problemBar").innerHTML =
      `<span class="title">${esc(card.title)}</span>` +
      `<span class="badge ${esc(diff)}">${esc(card.difficulty)}</span>` +
      (card.solved ? `<span class="badge solved">solved</span>` : "") +
      (card.verified === false ? `<span class="badge unverified" title="Auto-generated card — report it if it's wrong">unverified</span>` : "");

    const patterns = (card.patterns ?? [])
      .map((p) => `<li>${esc(p.name)} <span class="muted small">${Math.round(p.confidence * 100)}%</span></li>`)
      .join("");

    $("understandBody").innerHTML = `
      <p>${esc(card.understanding)}</p>
      <section class="lens">
        <h3>Likely patterns</h3>
        <ul>${patterns || "<li class='muted'>—</li>"}</ul>
      </section>
      <p class="muted small">Topics: ${(card.topics ?? []).map(esc).join(", ") || "—"}</p>
    `;

    renderReviewGate();
  }

  // ---------- hints ----------

  async function nextHint() {
    const level = state.hints.length + 1;
    $("hintError").textContent = "";

    if (level > 4) {
      $("hintError").textContent =
        "That's the whole ladder. The full solution unlocks after you pass — keep going, you're close.";
      $("nextHint").disabled = true;
      return;
    }

    $("nextHint").disabled = true;
    try {
      const fresh = await readContext();
      const h = await LL.api.hint(state.sessionId, level, fresh?.code ?? null, false);
      state.hints.push(h);
      renderHints();
      $("hintMeta").textContent = `${h.hints_remaining_today} hint reads left today.`;
    } catch (e) {
      $("hintError").textContent = e.message;
    } finally {
      $("nextHint").disabled = state.hints.length >= 4;
    }
  }

  function renderHints() {
    $("hintList").innerHTML = state.hints
      .map(
        (h, i) => `
      <div class="hint">
        <div class="lvl">Nudge ${i + 1} of 4</div>
        <div>${esc(h.nudge)}</div>
        <button class="report" data-level="${h.level}">this hint wasn't helpful</button>
      </div>`
      )
      .join("");

    for (const b of $("hintList").querySelectorAll(".report")) {
      b.addEventListener("click", async () => {
        b.disabled = true;
        b.textContent = "thanks — logged";
        try {
          await LL.api.feedback(state.ctx.slug, Number(b.dataset.level), "unclear", null);
        } catch (_) {}
      });
    }

    $("nextHint").textContent =
      state.hints.length === 0 ? "Give me a nudge" : `Next nudge (${state.hints.length + 1} of 4)`;
    $("nextHint").disabled = state.hints.length >= 4;
  }

  // ---------- review ----------

  async function loadPersonas() {
    try {
      const { personas } = await LL.api.personas();
      $("persona").innerHTML = personas
        .map((p) => `<option value="${esc(p.key)}" title="${esc(p.blurb)}">${esc(p.label)}</option>`)
        .join("");
    } catch (_) {}
  }

  function renderReviewGate() {
    $("reviewLocked").classList.toggle("hidden", state.solved);
    $("reviewBody").classList.toggle("hidden", !state.solved);

    // The tab itself is marked locked, not just its contents. The AC gate only
    // works as motivation if the learner can see there is something waiting
    // and that solving it themselves is what opens it.
    const tab = document.querySelector('.tab[data-tab="review"]');
    if (tab) {
      tab.classList.toggle("locked", !state.solved);
      tab.title = state.solved
        ? "Your code review"
        : "Unlocks when you get a passing submission — that's the whole point.";
    }

    if (state.solved && !$("reviewOut").innerHTML) runReview();
  }

  async function runReview() {
    const fresh = await readContext();
    const code = fresh?.code;

    // Partial code produces confidently wrong conclusions: a truncated buffer
    // has no loops in it, so the analyser reports O(1) and the review tells the
    // learner their solution is optimal. Refusing is the honest option.
    if (code && fresh.codeComplete === false) {
      $("reviewOut").innerHTML =
        `<p class="error">I could only read part of your editor, so any complexity
          claim I made would be wrong.</p>
         <p class="muted small">Paste your full solution and I'll review it properly.</p>
         <textarea id="manualCode" rows="8" placeholder="paste your solution"></textarea>
         <button id="manualGo" class="primary">Review this</button>`;
      $("manualGo").addEventListener("click", () => reviewWith($("manualCode").value));
      return;
    }

    if (!code) {
      $("reviewOut").innerHTML =
        `<p class="error">Couldn't read your code from the editor.</p>
         <p class="muted small">Paste it below and I'll review it.</p>
         <textarea id="manualCode" rows="8" placeholder="paste your solution"></textarea>
         <button id="manualGo" class="primary">Review this</button>`;
      $("manualGo").addEventListener("click", () => reviewWith($("manualCode").value));
      return;
    }
    reviewWith(code);
  }

  async function reviewWith(code) {
    $("reviewOut").innerHTML = `<p class="loading">Reviewing…</p>`;
    try {
      const r = await LL.api.review(state.sessionId, code, $("persona").value, state.failedAttempts);
      renderReview(r);
    } catch (e) {
      $("reviewOut").innerHTML = `<p class="error">${esc(e.message)}</p>`;
    }
  }

  function renderReview(r) {
    const optimal = r.verdict === "optimal";
    // A typographic stamp rather than a 26px emoji. The joke lives in the
    // writing, which ages better than any meme format and doesn't announce
    // itself as generated.
    const reaction = r.reaction
      ? `<div class="reaction">
           <div class="stamp ${esc(r.reaction.tone)}">${esc(r.reaction.stamp)}</div>
           <div class="line">${esc(r.reaction.line)}</div>
         </div>`
      : "";

    const lenses = (r.sections ?? [])
      .filter((s) => s.findings?.length)
      .map(
        (s) => `<section class="lens"><h3>${esc(s.title)}</h3>
          <ul>${s.findings.map((f) => `<li>${esc(f)}</li>`).join("")}</ul></section>`
      )
      .join("");

    const failures = (r.failure_gallery ?? [])
      .map(
        (f) => `<div class="failure">
          <div class="mistake">${esc(f.mistake)}</div>
          <div class="row"><span class="k">Input</span><code>${esc(f.trigger)}</code></div>
          <div class="row"><span class="k">Expected</span><code>${esc(f.expected)}</code></div>
          <div class="row"><span class="k">You'd get</span><code>${esc(f.actual)}</code></div>
          <div class="why">${esc(f.why)}</div>
        </div>`
      )
      .join("");

    $("reviewOut").innerHTML = `
      <div class="headline">${esc(r.headline)}</div>
      ${reaction}
      <div class="cx">
        <div><div class="k">Yours</div><div class="v ${optimal ? "good" : "warn"}">${esc(r.complexity_time)}</div></div>
        <div><div class="k">Target</div><div class="v">${esc(r.target_time)}</div></div>
      </div>

      <section class="lens"><h3>What you did well</h3>
        <ul>${(r.what_you_did_well ?? []).map((s) => `<li>${esc(s)}</li>`).join("")}</ul></section>

      ${lenses}

      ${failures ? `<section class="lens"><h3>${esc(r.failure_intro)}</h3>${failures}</section>` : ""}

      ${
        (r.try_next ?? []).length
          ? `<section class="lens"><h3>${esc(r.next_intro)}</h3>
             <ul>${r.try_next.map((s) => `<li>${esc(s)}</li>`).join("")}</ul></section>`
          : ""
      }

      ${r.card_verified === false ? `<p class="muted small">This card is auto-generated and unverified. If something's off, use the report link on a hint.</p>` : ""}
    `;
  }

  // ---------- progress ----------

  async function loadProgress() {
    try {
      const p = await LL.api.progress();
      $("streak").textContent = `🔥 ${p.streak_current}  ·  ${p.xp_total} XP`;
      $("progressBody").innerHTML = `
        <div class="stat-grid">
          <div class="stat"><div class="n">${p.streak_current}</div><div class="l">day streak</div></div>
          <div class="stat"><div class="n">${p.xp_total}</div><div class="l">total XP</div></div>
          <div class="stat"><div class="n">${p.streak_longest}</div><div class="l">longest streak</div></div>
          <div class="stat"><div class="n">${p.freezes_left}</div><div class="l">streak freezes</div></div>
        </div>
        <p class="muted small">${p.card_hints_left_today} hint reads left today · ${p.llm_calls_left_today} AI calls left today</p>
      `;
    } catch (e) {
      $("progressBody").innerHTML = `<p class="error">${esc(e.message)}</p>`;
    }
  }

  // ---------- verdict from the page ----------

  ext.runtime.onMessage.addListener(async (msg) => {
    if (msg?.type === "LL_VERDICT" && state.sessionId) {
      if (msg.verdict !== "Accepted") {
        state.failedAttempts += 1;
        return;
      }
      try {
        await LL.api.verdict(state.sessionId, "Accepted");
        state.solved = true;
        await Promise.all([loadCard(), loadProgress()]);
        switchTab("review");
      } catch (_) {}
    }
    if (msg?.type === "LL_NAVIGATED") {
      Object.assign(state, { ctx: null, sessionId: null, card: null, hints: [], solved: false, failedAttempts: 0 });
      $("hintList").innerHTML = "";
      $("reviewOut").innerHTML = "";
      boot();
    }
  });

  // ---------- tabs & wiring ----------

  function switchTab(name) {
    // Bounce the learner back to Hints rather than showing an empty locked
    // pane — the useful thing pre-AC is the ladder.
    const target = document.querySelector(`.tab[data-tab="${name}"]`);
    if (target?.classList.contains("locked")) {
      $("hintError").textContent =
        "The review unlocks once you pass. Until then the hints are the help — that's the deal.";
      name = "hints";
    }
    for (const t of document.querySelectorAll(".tab")) t.classList.toggle("active", t.dataset.tab === name);
    for (const p of document.querySelectorAll(".tabpane")) p.classList.toggle("hidden", p.id !== `tab-${name}`);
    if (name === "progress") loadProgress();
    if (name === "review") renderReviewGate();
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const { apiBase } = await LL.storage.get(["apiBase"]);
    $("apiBase").value = apiBase || "http://localhost:8000";

    for (const t of document.querySelectorAll(".tab")) {
      t.addEventListener("click", () => switchTab(t.dataset.tab));
    }

    // The dev sign-in form only appears if the server actually accepts it, so
    // a deployed build shows GitHub alone.
    try {
      const { auth } = await LL.api.health();
      $("devAuth").classList.toggle("hidden", !auth?.dev);
      $("signinGithub").classList.toggle("hidden", !auth?.github);
      if (!auth?.github && !auth?.dev) {
        $("authError").textContent = "This server has no sign-in method configured.";
      }
    } catch (_) {
      // Server unreachable — leave both visible; the attempt will report why.
    }

    $("signinGithub").addEventListener("click", async () => {
      $("authError").textContent = "";
      $("signinGithub").disabled = true;
      try {
        await LL.api.loginWithGithub();
        boot();
      } catch (e) {
        $("authError").textContent = e.message;
      } finally {
        $("signinGithub").disabled = false;
      }
    });

    $("signin").addEventListener("click", async () => {
      $("authError").textContent = "";
      const email = $("email").value.trim();
      if (!email) return ($("authError").textContent = "Enter an email.");
      try {
        await LL.api.login(email);
        boot();
      } catch (e) {
        $("authError").textContent = e.message;
      }
    });

    $("saveBase").addEventListener("click", async () => {
      await LL.api.setBase($("apiBase").value.trim());
      $("authError").textContent = "Saved.";
    });

    $("signout").addEventListener("click", async () => {
      await LL.api.logout();
      show("auth");
    });

    $("nextHint").addEventListener("click", nextHint);
    $("rerun").addEventListener("click", runReview);
    $("persona").addEventListener("change", runReview);

    boot();
  });
})();
