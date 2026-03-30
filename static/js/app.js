(function () {
  var statusTimer = null;

  function setActiveNav() {
    var path = window.location.pathname || "/";
    document.querySelectorAll(".nav a").forEach(function (a) {
      var href = a.getAttribute("href") || "";
      if (href === path || (path !== "/" && href !== "/" && path.indexOf(href) === 0)) {
        a.classList.add("active");
      }
    });
  }

  function setupSidebarToggle() {
    var btn = document.getElementById("sidebar-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      document.querySelector(".layout").classList.toggle("sidebar-open");
    });
  }

  function setRunIdInUrl(id) {
    if (!id) return;
    try {
      var u = new URL(window.location.href);
      u.searchParams.set("run_id", String(id));
      window.history.replaceState({}, "", u.toString());
    } catch (e) {}
  }

  function appendRunIdToNavLinks() {
    var id = window.AutoQA.getRunId();
    if (!id) return;
    document.querySelectorAll(".nav a").forEach(function (a) {
      var href = a.getAttribute("href") || "";
      if (!href || href === "#" || href.indexOf("/api/") === 0) return;
      try {
        var u = new URL(href, window.location.origin);
        if (!u.searchParams.get("run_id")) u.searchParams.set("run_id", String(id));
        a.setAttribute("href", u.pathname + u.search + u.hash);
      } catch (e) {}
    });
  }

  function getLatestRun() {
    return fetch("/api/runs/latest")
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        return d && d.run ? d.run : null;
      })
      .catch(function () {
        return null;
      });
  }

  function ensureRunId() {
    var id = window.AutoQA.getRunId();
    if (id) {
      setRunIdInUrl(id);
      appendRunIdToNavLinks();
      return Promise.resolve(id);
    }
    return getLatestRun().then(function (run) {
      if (!run || !run.id) return null;
      window.AutoQA.setRunId(run.id);
      setRunIdInUrl(run.id);
      appendRunIdToNavLinks();
      return run.id;
    });
  }

  function startGlobalRunStatusPolling() {
    if (statusTimer) clearInterval(statusTimer);
    var bar = document.getElementById("global-run-progress");
    var txt = document.getElementById("global-run-status-text");
    if (!bar || !txt) return;
    function tick() {
      var id = window.AutoQA.getRunId();
      if (!id) return;
      fetch("/api/run-status/" + id)
        .then(function (r) {
          return r.json();
        })
        .then(function (s) {
          if (!s || s.error) return;
          var p = Math.max(0, Math.min(100, Number(s.progress || 0)));
          bar.style.width = p + "%";
          txt.textContent = "Run #" + id + " · " + (s.status || "running") + " · " + p.toFixed(0) + "%";
          if (s.status === "completed") {
            txt.style.opacity = "0.7";
          } else {
            txt.style.opacity = "1";
          }
        })
        .catch(function () {});
    }
    tick();
    statusTimer = setInterval(tick, 2500);
  }

  window.AutoQA = {
    setActiveNav: setActiveNav,
    getLatestRun: getLatestRun,
    ensureRunId: ensureRunId,
    startGlobalRunStatusPolling: startGlobalRunStatusPolling,
    getRunId: function () {
      var params = new URLSearchParams(window.location.search);
      var q = params.get("run_id");
      if (q) {
        var n = parseInt(q, 10);
        if (!isNaN(n)) return n;
      }
      var ls = localStorage.getItem("autoqa_last_run_id");
      return ls ? parseInt(ls, 10) : null;
    },
    setRunId: function (id) {
      if (id) {
        localStorage.setItem("autoqa_last_run_id", String(id));
        setRunIdInUrl(id);
        appendRunIdToNavLinks();
      }
    },
  };

  document.addEventListener("DOMContentLoaded", function () {
    setActiveNav();
    setupSidebarToggle();
    ensureRunId().then(function () {
      appendRunIdToNavLinks();
      startGlobalRunStatusPolling();
    });
  });
})();
