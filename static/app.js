/**
 * magicpin Vera Assistant — Command Center & Simulator Application
 */

document.addEventListener("DOMContentLoaded", () => {
  let appState = {
    activeTab: "overview",
    stats: null,
    categories: {},
    merchants: {},
    triggers: {},
    customers: {},
    currentScope: "category",
    chatTurns: [],
    turnNumber: 1,
    testPairs: []
  };

  // Safe DOM helper
  function setText(idOrEl, text) {
    const el = typeof idOrEl === "string" ? document.getElementById(idOrEl) : idOrEl;
    if (el) el.textContent = text;
  }

  function setHTML(idOrEl, html) {
    const el = typeof idOrEl === "string" ? document.getElementById(idOrEl) : idOrEl;
    if (el) el.innerHTML = html;
  }

  // =========================================================================
  // TAB NAVIGATION
  // =========================================================================
  const navItems = document.querySelectorAll(".nav-item");
  const tabPanels = document.querySelectorAll(".tab-panel");
  const pageTitle = document.getElementById("pageTitle");
  const pageSubtitle = document.getElementById("pageSubtitle");

  const tabMeta = {
    overview: { title: "Overview & System Health", desc: "Live status of endpoints, context preloading, and 5-dimension scoring engine." },
    composer: { title: "Live Composer Sandbox", desc: "Test message composition across 4 contexts with instant WhatsApp preview & guardrail checks." },
    simulator: { title: "WhatsApp Chat Replay Simulator", desc: "Simulate multi-turn merchant/customer conversations against the AI judge state machine." },
    explorer: { title: "4-Context Schema Explorer", desc: "Inspect raw Category, Merchant, Customer, and Trigger contexts stored in memory." },
    submission: { title: "Canonical Test Pairs & Submission", desc: "Generate and inspect the 30-item submission.jsonl file for judge evaluation." }
  };

  navItems.forEach(btn => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      switchTab(tab);
    });
  });

  function switchTab(tabId) {
    appState.activeTab = tabId;
    navItems.forEach(n => n.classList.toggle("active", n.dataset.tab === tabId));
    tabPanels.forEach(p => p.classList.toggle("active", p.id === `tab-${tabId}`));
    
    if (tabMeta[tabId]) {
      setText(pageTitle, tabMeta[tabId].title);
      setText(pageSubtitle, tabMeta[tabId].desc);
    }

    if (tabId === "composer") {
      populateComposerDropdowns();
    } else if (tabId === "explorer") {
      loadExplorerList();
    } else if (tabId === "submission") {
      loadTestPairs();
    }
  }

  // Quick action buttons
  document.getElementById("quickComposeBtn")?.addEventListener("click", () => switchTab("composer"));
  document.getElementById("refreshDataBtn")?.addEventListener("click", loadDashboardStats);

  // =========================================================================
  // DASHBOARD DATA FETCHING
  // =========================================================================
  async function loadDashboardStats() {
    try {
      const res = await fetch("/api/dashboard_stats");
      const data = await res.json();
      appState.stats = data;

      setText("countCategories", data.counts?.category || 5);
      setText("countMerchants", data.counts?.merchant || 50);
      setText("countCustomers", data.counts?.customer || 200);
      setText("countTriggers", data.counts?.trigger || 100);

      setText("healthStatusText", `Bot Online (${data.uptime || 0}s uptime)`);
      const pill = document.getElementById("healthPill");
      if (pill) {
        const dot = pill.querySelector(".status-dot");
        if (dot) dot.className = "status-dot online";
      }
    } catch (err) {
      console.warn("Failed fetching dashboard stats:", err);
      setText("healthStatusText", "Bot Offline / Connecting...");
      const pill = document.getElementById("healthPill");
      if (pill) {
        const dot = pill.querySelector(".status-dot");
        if (dot) dot.className = "status-dot offline";
      }
    }
  }

  // =========================================================================
  // COMPOSER SANDBOX
  // =========================================================================
  const selectCat = document.getElementById("selectCategory");
  const selectMerch = document.getElementById("selectMerchant");
  const selectTrig = document.getElementById("selectTrigger");
  const selectCust = document.getElementById("selectCustomer");
  const runComposeBtn = document.getElementById("runComposeBtn");
  const loadRandomPresetBtn = document.getElementById("loadRandomPresetBtn");

  async function populateComposerDropdowns() {
    if (!appState.stats) await loadDashboardStats();
    if (!appState.stats) return;

    // Populate Merchants
    if (selectMerch && appState.stats.merchants) {
      selectMerch.innerHTML = "";
      appState.stats.merchants.forEach(mId => {
        const opt = document.createElement("option");
        opt.value = mId;
        opt.textContent = mId.replace("m_", "").replace(/_/g, " ");
        selectMerch.appendChild(opt);
      });
    }

    // Populate Triggers
    if (selectTrig && appState.stats.triggers) {
      selectTrig.innerHTML = "";
      appState.stats.triggers.forEach(tId => {
        const opt = document.createElement("option");
        opt.value = tId;
        opt.textContent = tId.replace("trg_", "").replace(/_/g, " ");
        selectTrig.appendChild(opt);
      });
    }

    // Populate Customers
    if (selectCust && appState.stats.customers) {
      selectCust.innerHTML = '<option value="">None (Merchant-Facing Message - Vera)</option>';
      appState.stats.customers.forEach(cId => {
        const opt = document.createElement("option");
        opt.value = cId;
        opt.textContent = cId.replace("c_", "").replace(/_/g, " ");
        selectCust.appendChild(opt);
      });
    }
  }

  runComposeBtn?.addEventListener("click", async () => {
    runComposeBtn.disabled = true;
    runComposeBtn.innerHTML = '<span class="icon">⏳</span> Composing...';

    const payload = {
      category_id: selectCat ? selectCat.value : "dentists",
      merchant_id: selectMerch ? selectMerch.value : "",
      trigger_id: selectTrig ? selectTrig.value : "",
      customer_id: selectCust ? (selectCust.value || null) : null
    };

    try {
      const res = await fetch("/api/compose_custom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      const comp = data.composed || {};

      // Update WhatsApp Preview safely
      const bodyEl = document.getElementById("waBubbleBodyText") || document.getElementById("waBubbleBody");
      if (bodyEl) bodyEl.textContent = comp.body || "No message generated";

      setText("waCtaPill", comp.cta || "open_ended");
      setText("waSendAsBadge", `send_as: ${comp.send_as || "vera"}`);
      setText("rationaleText", comp.rationale || "Composed following 4-context specifications and guardrails.");

      const now = new Date();
      setText("waTime", now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));

      if (comp.send_as === "merchant_on_behalf") {
        setText("waSenderTitle", "Dr. Meera's Clinic (via Vera)");
        setText("waAvatar", "M");
      } else {
        setText("waSenderTitle", "Vera (magicpin Assistant)");
        setText("waAvatar", "V");
      }

    } catch (err) {
      console.error("Composition error:", err);
      alert("Error composing message: " + err);
    } finally {
      if (runComposeBtn) {
        runComposeBtn.disabled = false;
        runComposeBtn.innerHTML = '<span class="icon">⚡</span> Compose WhatsApp Message';
      }
    }
  });

  loadRandomPresetBtn?.addEventListener("click", () => {
    if (!appState.stats) return;
    const cats = ["dentists", "salons", "restaurants", "gyms", "pharmacies"];
    if (selectCat) selectCat.value = cats[Math.floor(Math.random() * cats.length)];

    if (selectMerch && selectMerch.options.length > 0) {
      selectMerch.selectedIndex = Math.floor(Math.random() * selectMerch.options.length);
    }

    if (selectTrig && selectTrig.options.length > 0) {
      selectTrig.selectedIndex = Math.floor(Math.random() * selectTrig.options.length);
    }

    if (runComposeBtn) runComposeBtn.click();
  });

  // =========================================================================
  // WHATSAPP CHAT REPLAY SIMULATOR
  // =========================================================================
  const chatMessages = document.getElementById("chatMessages");
  const merchantInput = document.getElementById("merchantInput");
  const sendMerchantReplyBtn = document.getElementById("sendMerchantReplyBtn");
  const resetChatBtn = document.getElementById("resetChatBtn");
  const turnLogs = document.getElementById("turnLogs");

  const inspectorTurn = document.getElementById("inspectorTurn");
  const inspectorAction = document.getElementById("inspectorAction");
  const inspectorAutoCount = document.getElementById("inspectorAutoCount");
  const inspectorMode = document.getElementById("inspectorMode");

  const SIMULATED_CONV_ID = "conv_replay_interactive_001";
  const SIMULATED_MERCHANT_ID = "m_001_drmeera_dentist_delhi";

  function appendChatMsg(sender, text) {
    if (!chatMessages) return;
    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-msg ${sender}`;
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    msgDiv.innerHTML = `
      <div class="msg-bubble">
        ${text}
        <div class="msg-time">${now}</div>
      </div>
    `;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function appendLog(text) {
    if (!turnLogs) return;
    const logDiv = document.createElement("div");
    logDiv.className = "log-entry";
    const now = new Date().toLocaleTimeString();
    logDiv.innerHTML = `<span class="log-time">[${now}]</span> ${text}`;
    turnLogs.appendChild(logDiv);
    turnLogs.scrollTop = turnLogs.scrollHeight;
  }

  async function handleMerchantSend(text) {
    if (!text || !text.trim()) return;
    if (merchantInput) merchantInput.value = "";
    appendChatMsg("merchant", text);
    appState.turnNumber += 1;
    setText(inspectorTurn, `Turn ${appState.turnNumber}`);

    appendLog(`Merchant sent: "${text.substring(0, 45)}..."`);

    try {
      const res = await fetch("/v1/reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: SIMULATED_CONV_ID,
          merchant_id: SIMULATED_MERCHANT_ID,
          from_role: "merchant",
          message: text,
          received_at: new Date().toISOString(),
          turn_number: appState.turnNumber
        })
      });
      const data = await res.json();

      setText(inspectorAction, data.action || "send");
      if (data.action === "end") {
        if (inspectorAction) inspectorAction.className = "s-value text-red";
        setText(inspectorMode, "CLOSED");
        setText("chatStateStatus", "Status: CLOSED • Session Completed");
      } else if (data.action === "wait") {
        if (inspectorAction) inspectorAction.className = "s-value text-yellow";
        appendLog(`Bot executed WAIT for ${data.wait_seconds}s (${data.rationale})`);
      } else {
        if (inspectorAction) inspectorAction.className = "s-value green";
        if (data.body && (data.body.toLowerCase().includes("done") || data.body.toLowerCase().includes("draft"))) {
          setText(inspectorMode, "ACTION");
        }
      }

      if (data.body) {
        appendChatMsg("vera", data.body);
        appendLog(`Bot responded with ACTION: "${data.action}". Rationale: ${data.rationale || ""}`);
      }

    } catch (err) {
      appendLog(`Error in reply handler: ${err}`);
    }
  }

  sendMerchantReplyBtn?.addEventListener("click", () => {
    if (merchantInput) handleMerchantSend(merchantInput.value);
  });
  
  merchantInput?.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && merchantInput) handleMerchantSend(merchantInput.value);
  });

  document.querySelectorAll(".btn-scenario").forEach(btn => {
    btn.addEventListener("click", () => {
      handleMerchantSend(btn.dataset.text);
    });
  });

  resetChatBtn?.addEventListener("click", () => {
    if (chatMessages) {
      chatMessages.innerHTML = `
        <div class="chat-msg vera">
          <div class="msg-bubble">
            Dr. Meera, JIDA's Oct issue landed. One item relevant to your high-risk adult patients — 2,100-patient trial showed 3-month fluoride recall cuts caries recurrence 38% better than 6-month. Worth a look (2-min abstract). Want me to pull it + draft a patient-ed WhatsApp you can share? — JIDA Oct 2026 p.14
            <div class="msg-time">10:30 AM</div>
          </div>
        </div>
      `;
    }
    appState.turnNumber = 1;
    setText(inspectorTurn, "Turn 1");
    setText(inspectorAction, "send");
    if (inspectorAction) inspectorAction.className = "s-value green";
    setText(inspectorMode, "QUALIFYING");
    setText("chatStateStatus", "Mode: QUALIFYING • Status: Active");
    if (turnLogs) {
      turnLogs.innerHTML = `<div class="log-entry"><span class="log-time">[10:30:00]</span> Replay session reset. Proactive trigger composed.</div>`;
    }
  });

  // =========================================================================
  // 4-CONTEXT EXPLORER
  // =========================================================================
  const expTabs = document.querySelectorAll(".exp-tab");
  const contextItemList = document.getElementById("contextItemList");
  const jsonViewerContent = document.getElementById("jsonViewerContent");
  const viewerTitle = document.getElementById("viewerTitle");
  const viewerBadge = document.getElementById("viewerBadge");
  const explorerSearch = document.getElementById("explorerSearch");

  expTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      expTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      appState.currentScope = tab.dataset.scope;
      loadExplorerList();
    });
  });

  async function loadExplorerList() {
    if (!appState.stats) await loadDashboardStats();
    const scope = appState.currentScope;
    let items = [];
    if (scope === "category") items = appState.stats?.categories || [];
    else if (scope === "merchant") items = appState.stats?.merchants || [];
    else if (scope === "customer") items = appState.stats?.customers || [];
    else if (scope === "trigger") items = appState.stats?.triggers || [];

    renderExplorerItems(items);
    if (items.length > 0) {
      loadContextDetail(scope, items[0]);
    }
  }

  function renderExplorerItems(items) {
    if (!contextItemList) return;
    contextItemList.innerHTML = "";
    const filter = explorerSearch ? explorerSearch.value.toLowerCase() : "";
    const filtered = items.filter(id => id.toLowerCase().includes(filter));

    filtered.forEach((id, idx) => {
      const li = document.createElement("li");
      li.textContent = id;
      if (idx === 0) li.classList.add("active");
      li.addEventListener("click", () => {
        document.querySelectorAll(".context-item-list li").forEach(l => l.classList.remove("active"));
        li.classList.add("active");
        loadContextDetail(appState.currentScope, id);
      });
      contextItemList.appendChild(li);
    });
  }

  explorerSearch?.addEventListener("input", () => {
    let items = [];
    const scope = appState.currentScope;
    if (scope === "category") items = appState.stats?.categories || [];
    else if (scope === "merchant") items = appState.stats?.merchants || [];
    else if (scope === "customer") items = appState.stats?.customers || [];
    else if (scope === "trigger") items = appState.stats?.triggers || [];
    renderExplorerItems(items);
  });

  async function loadContextDetail(scope, id) {
    try {
      const res = await fetch(`/api/context/${scope}/${id}`);
      const data = await res.json();
      setText(viewerTitle, id);
      setText(viewerBadge, `${scope}: ${id}`);
      setText(jsonViewerContent, JSON.stringify(data.payload, null, 2));
    } catch (err) {
      setText(jsonViewerContent, `Error loading context: ${err}`);
    }
  }

  // =========================================================================
  // SUBMISSION GENERATOR & TEST PAIRS TABLE
  // =========================================================================
  const testPairsTbody = document.getElementById("testPairsTbody");
  const generateSubmissionBtn = document.getElementById("generateSubmissionBtn");
  const submissionStatus = document.getElementById("submissionStatus");
  const downloadSubmissionLink = document.getElementById("downloadSubmissionLink");

  async function loadTestPairs() {
    try {
      const res = await fetch("/api/test_pairs");
      const data = await res.json();
      appState.testPairs = data.pairs || [];
      setText("testPairCount", appState.testPairs.length);

      if (testPairsTbody) {
        testPairsTbody.innerHTML = "";
        appState.testPairs.forEach(p => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td><span class="test-id-badge">${p.test_id}</span></td>
            <td><code>${p.trigger_id}</code></td>
            <td><code>${p.merchant_id}</code></td>
            <td>${p.customer_id ? `<code>${p.customer_id}</code>` : '<span class="text-muted">None</span>'}</td>
            <td><span class="pill ${p.customer_id ? 'purple' : 'cyan'}">${p.customer_id ? 'merchant_on_behalf' : 'vera'}</span></td>
            <td id="preview-${p.test_id}"><em>Click generate to compose</em></td>
            <td><button class="btn btn-sm btn-secondary" onclick="window.previewPair('${p.test_id}')">Inspect</button></td>
          `;
          testPairsTbody.appendChild(tr);
        });
      }
    } catch (err) {
      console.warn("Failed loading test pairs:", err);
    }
  }

  generateSubmissionBtn?.addEventListener("click", async () => {
    generateSubmissionBtn.disabled = true;
    generateSubmissionBtn.innerHTML = '<span class="icon">⏳</span> Composing 30 Test Pairs...';
    setText(submissionStatus, "Composing batch...");

    try {
      const res = await fetch("/api/generate_submission_jsonl", { method: "POST" });
      const data = await res.json();

      if (data.success) {
        setText(submissionStatus, `Generated ${data.count} compositions in submission.jsonl!`);
        if (submissionStatus) submissionStatus.className = "text-green";

        // Update previews in table
        data.items.forEach(item => {
          setText(`preview-${item.test_id}`, `"${item.body.substring(0, 70)}..."`);
        });

        // Setup download link
        if (downloadSubmissionLink) {
          const blob = new Blob([data.items.map(i => JSON.stringify(i)).join("\n")], { type: "application/x-jsonlines" });
          const url = URL.createObjectURL(blob);
          downloadSubmissionLink.href = url;
          downloadSubmissionLink.download = "submission.jsonl";
          downloadSubmissionLink.style.display = "inline-flex";
        }
      }
    } catch (err) {
      alert("Error generating submission: " + err);
    } finally {
      if (generateSubmissionBtn) {
        generateSubmissionBtn.disabled = false;
        generateSubmissionBtn.innerHTML = '<span class="icon">⚙️</span> Run Batch Composition & Save submission.jsonl';
      }
    }
  });

  window.previewPair = (testId) => {
    const pair = appState.testPairs.find(p => p.test_id === testId);
    if (!pair) return;
    switchTab("composer");
    if (selectMerch) selectMerch.value = pair.merchant_id;
    if (selectTrig) selectTrig.value = pair.trigger_id;
    if (selectCust) {
      if (pair.customer_id) selectCust.value = pair.customer_id;
      else selectCust.value = "";
    }
    if (runComposeBtn) runComposeBtn.click();
  };

  // Initial Boot
  loadDashboardStats();
});
