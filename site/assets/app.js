/* AIPE Semiconductor Data Explorer: read-only client over the JSON written by scripts/build_site.py.
   Hash routing (works under the GitHub Pages sub-path), device files loaded on demand, no external requests.
   It shows stored values only: nothing is interpolated, fitted or filled in. */
(function () {
  "use strict";
  var app = document.getElementById("app");
  var cache = {};
  var REPO = "https://github.com/AIPE-Labs/AIPE-Semiconductor-Database";
  var COLORS = [1, 2, 3, 4, 5, 6, 7, 8].map(function (i) { return "var(--series-" + i + ")"; });
  var GUARD_K = 773.15;

  function load(path) {
    if (!cache[path]) {
      cache[path] = fetch(path).then(function (r) {
        if (!r.ok) throw new Error("Could not load " + path + " (HTTP " + r.status + ")");
        return r.json();
      });
      cache[path].catch(function () { delete cache[path]; });
    }
    return cache[path];
  }
  function esc(v) {
    return String(v === null || v === undefined ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // -- vocabulary -------------------------------------------------------------------------------------------
  var DATA_CLASS = {
    manufacturer_model: ["Manufacturer model", "ds", "A table from the manufacturer's simulation model. Not a measurement."],
    manufacturer_datasheet: ["Datasheet transcription", "ds", "A value transcribed from the manufacturer's datasheet. Not a measurement."],
    measured: ["Measurement", "exp", "Measured in a laboratory."],
    digitized: ["Digitised", "der", "Read from a published figure."],
    fitted: ["Fitted", "fit", "Model coefficients fitted to data; not a measurement."],
    physics_derived: ["Derived", "der", "Computed from other records."],
    inferred: ["Inferred", "der", "Inferred from other records; not stated by a source."],
    synthetic: ["Synthetic", "der", "Generated example data."]
  };
  var COLLECTION = { canonical: "Manufacturer model record", candidate: "Datasheet candidate (unreviewed)" };
  var GROUP = { ratings: "Ratings", package: "Package", conduction: "Conduction", switching: "Switching", capacitance: "Capacitance",
    gate_charge: "Gate", reverse_conduction: "Reverse conduction", soa: "Safe operating area", thermal: "Thermal" };
  var QTY = { voltage_drop: "Voltage drop", Eon: "Turn-on energy Eon", Eoff: "Turn-off energy Eoff", rds_on: "On-resistance RDS(on)",
    id_max: "Continuous drain current", vds_max: "Drain-source voltage rating", tj_max: "Maximum junction temperature",
    rth_jc: "Thermal resistance junction-case", coss: "Output capacitance Coss", ciss: "Input capacitance Ciss", crss: "Reverse transfer capacitance Crss",
    qg_total: "Total gate charge", qgs: "Gate-source charge", qgd: "Gate-drain charge", rg_internal: "Internal gate resistance",
    Qrr: "Reverse recovery charge", trr: "Reverse recovery time", Irrm: "Peak reverse recovery current", Eoss: "Output capacitance energy Eoss" };
  var AXIS = { junction_temperature: "Junction temperature", case_temperature: "Case temperature", ambient_temperature: "Ambient temperature",
    dc_bus_voltage: "DC bus voltage", current: "Current", drain_current: "Drain current", gate_resistance_on: "Gate resistance (on)",
    gate_resistance_off: "Gate resistance (off)", gate_voltage_on: "Gate voltage (on)", gate_voltage_off: "Gate voltage (off)",
    switching_frequency: "Switching frequency", pulse_width: "Pulse width", duty_cycle: "Duty cycle" };

  // -- display units: stored values stay SI; converted for display only -----------------------------------------
  function num(v) {
    if (v === 0) return "0";
    var a = Math.abs(v);
    return (a >= 1e5 || a < 1e-3) ? v.toExponential(3).replace(/\.?0+e/, "e") : String(+v.toPrecision(5));
  }
  var PREFIX = [[1e-12, "p"], [1e-9, "n"], [1e-6, "µ"], [1e-3, "m"], [1, ""], [1e3, "k"]];
  function display(value, unit) { // -> {v, u}
    if (unit === "K") return { v: +(value - 273.15).toFixed(6), u: "°C" };
    if (unit === "Ohm" || unit === "J" || unit === "F" || unit === "C" || unit === "s" || unit === "H") {
      var a = Math.abs(value), pick = PREFIX[4];
      if (a > 0) PREFIX.forEach(function (p) { if (a >= p[0] * 0.9999) pick = p; });
      return { v: value / pick[0], u: pick[1] + (unit === "Ohm" ? "Ω" : unit) };
    }
    if (unit === "1") return { v: value, u: "" };
    return { v: value, u: unit };
  }
  function shown(value, unit) { var d = display(value, unit); return num(d.v) + (d.u ? " " + d.u : ""); }
  function scale(values, unit) { // one display unit for a whole column
    if (unit === "K") return { f: function (v) { return v - 273.15; }, u: "°C" };
    var max = Math.max.apply(null, values.map(Math.abs)), d = display(max || 1, unit), k = max ? d.v / max : 1;
    return { f: function (v) { return v * k; }, u: d.u };
  }
  function conditionText(c) {
    var parts = Object.keys(c || {}).map(function (k) {
      return k === "gate_state" ? "gate " + c[k] : (AXIS[k] || k.replace(/_/g, " ")) + " " + shown(c[k].value, c[k].unit);
    });
    return parts.length ? esc(parts.join(" · ")) : '<span class="na">not stated by the source</span>';
  }
  function badge(cls) {
    var d = DATA_CLASS[cls] || [cls, "der", ""];
    return '<span class="badge ' + d[1] + '" title="' + esc(d[2]) + '">' + esc(d[0]) + "</span>";
  }
  function review(status) {
    return '<span class="badge ' + (status === "reviewed" ? "exp" : "warn") + '" title="Whether a person has checked this record.">' +
      esc(status === "unreviewed" ? "Not reviewed by a person" : status) + "</span>";
  }
  function rightsLine(r) {
    if (r.status === "not_established")
      return "Rights not established" + (r.owner ? " (owner: " + esc(r.owner) + ")" : "") + ": no licence has been given.";
    return "Licence: " + esc(r.license || "stated by owner") + (r.owner ? " (owner: " + esc(r.owner) + ")" : "") +
      (r.redistribution_allowed === true ? "; redistribution allowed" : r.redistribution_allowed === false ? "; redistribution not allowed" : "");
  }
  function rightsNotice(sources) {
    var open = sources.filter(function (s) { return s.rights.status === "not_established"; });
    if (!open.length) return "";
    var owners = open.map(function (s) { return s.rights.owner; }).filter(function (o, i, a) { return o && a.indexOf(o) === i; });
    return '<div class="notice"><strong>Redistribution rights not established.</strong> These values come from ' +
      esc(owners.join(", ") || "a third party") + ", who has given no licence for them. They are shown here with their source so that they can be " +
      "checked and cited; do not republish them as a dataset. Rights holders can request correction or removal through " +
      '<a href="' + REPO + '/issues">an issue</a>. See <a href="' + REPO + '/blob/main/LICENSING.md">Licensing and data rights</a>.</div>';
  }
  function sourceList(sources, commit) {
    return '<ul class="small">' + sources.map(function (s) {
      var file = s.file ? s.file.replace(/^raw:/, "data/raw/") : null;
      var href = file ? REPO + "/blob/" + (commit || "main") + "/" + file.split("/").map(encodeURIComponent).join("/") : s.url;
      return "<li>" + (href ? '<a href="' + esc(href) + '" rel="noopener">' + esc(s.name) + "</a>" : esc(s.name)) + " · " + esc(s.kind) +
        (file ? ' · original file archived in the repository <span class="mono">' + esc(file.split("/").pop()) + "</span>" : "") +
        (s.sha256 ? ' · SHA-256 <span class="mono">' + esc(s.sha256.slice(0, 12)) + "…</span>" : "") +
        '<br><span class="muted">' + rightsLine(s.rights) + "</span></li>";
    }).join("") + "</ul>";
  }

  // -- views ------------------------------------------------------------------------------------------------
  function overview() {
    return Promise.all([load("data/summary.json"), load("data/devices.json")]).then(function (res) {
      var s = res[0], c = s.collections;
      function stat(href, label, n, sub) {
        return '<a class="stat" href="' + href + '"><div class="label">' + esc(label) + '</div><div class="num">' + esc(n) +
          '</div><div class="sub">' + esc(sub) + "</div></a>";
      }
      app.innerHTML =
        '<section class="hero"><p class="eyebrow">AIPE Semiconductor Database</p>' +
        '<h1 class="display">Power semiconductor data, with the source of every value</h1>' +
        '<p class="lead">A read-only view of the device records in the repository. Each value is shown with its unit, the operating ' +
        "conditions its source stated, whether it is a manufacturer model, a datasheet transcription or a measurement, and what is known about the right to reuse it.</p>" +
        '<form class="search-pill" id="go"><input type="search" id="q" placeholder="Part number, e.g. C3M0040120K" aria-label="Search devices"><button>Search</button></form></section>' +
        '<div class="stats">' +
        stat("#/devices?collection=canonical", "Manufacturer model records", c.canonical.devices, c.canonical.manufacturers.join(", ")) +
        stat("#/devices?collection=candidate", "Datasheet candidates", c.candidate.devices, c.candidate.manufacturers.length + " manufacturers, unreviewed") +
        stat("#/sources", "Measured records", s.measured_records, "no laboratory measurement yet") +
        stat("#/sources", "Reviewed by a person", s.reviewed_devices, "of " + (c.canonical.devices + c.candidate.devices) + " devices") +
        "</div>" +
        '<div class="notice"><strong>What this is not.</strong> None of these values is a measurement, and none has been checked by a person. ' +
        "Manufacturer data keep their owners' rights, and their redistribution rights are not established; they are shown with their source, not republished as a dataset.</div>" +
        '<div class="grid-2"><div class="card"><h2>For people</h2><p>Browse the <a href="#/devices">devices</a>, open a device to see its conduction and switching-loss tables, ' +
        "thermal network and datasheet values, and follow each value back to its original file or datasheet.</p></div>" +
        '<div class="card"><h2>For AI agents</h2><p>The same records are served by a local, read-only MCP server with plugins for Claude Code and Codex. ' +
        '<a href="' + REPO + '/blob/main/docs/agents.md">Setup and tools</a>.</p></div></div>';
      document.getElementById("go").addEventListener("submit", function (e) {
        e.preventDefault();
        location.hash = "#/devices?q=" + encodeURIComponent(document.getElementById("q").value.trim());
      });
    });
  }

  function devices(params) {
    return load("data/devices.json").then(function (rows) {
      var st = { q: params.q || "", manufacturer: params.manufacturer || "", collection: params.collection || "", integration: params.integration || "" };
      function options(key, labels) {
        var seen = rows.map(function (r) { return r[key]; }).filter(function (v, i, a) { return a.indexOf(v) === i; }).sort();
        return '<option value="">All</option>' + seen.map(function (v) {
          return '<option value="' + esc(v) + '"' + (st[key] === v ? " selected" : "") + ">" + esc((labels && labels[v]) || v) + "</option>";
        }).join("");
      }
      app.innerHTML = "<h1>Devices</h1>" +
        '<p class="lead">' + rows.length + " device records. A part can appear twice: once from the manufacturer's model file and once as a datasheet candidate.</p>" +
        '<div class="filters"><label class="wide">Search<input type="search" id="f-q" value="' + esc(st.q) + '" placeholder="Part number or manufacturer"></label>' +
        '<label>Manufacturer<select id="f-manufacturer">' + options("manufacturer") + "</select></label>" +
        '<label>Record type<select id="f-collection">' + options("collection", COLLECTION) + "</select></label>" +
        '<label>Integration<select id="f-integration">' + options("integration") + "</select></label></div>" +
        '<p class="small muted" id="count"></p><div class="table-wrap"><table><thead><tr><th>Part number</th><th>Manufacturer</th><th>Technology</th>' +
        "<th>Integration</th><th>Data</th><th>Record type</th><th>Review</th></tr></thead><tbody id=\"rows\"></tbody></table></div>";
      function draw() {
        var q = st.q.toLowerCase();
        var list = rows.filter(function (r) {
          return (!q || (r.part_number + " " + r.manufacturer + " " + r.device_id).toLowerCase().indexOf(q) >= 0) &&
            (!st.manufacturer || r.manufacturer === st.manufacturer) && (!st.collection || r.collection === st.collection) &&
            (!st.integration || r.integration === st.integration);
        });
        document.getElementById("count").textContent = list.length + " shown";
        document.getElementById("rows").innerHTML = list.map(function (r) {
          return '<tr><td><a href="#/device/' + encodeURIComponent(r.device_id) + '">' + esc(r.part_number) + "</a></td><td>" + esc(r.manufacturer) +
            "</td><td>" + esc(r.technology.replace("_", " ")) + "</td><td>" + esc(r.integration) + "</td><td>" + r.data_classes.map(badge).join(" ") +
            "</td><td>" + esc(COLLECTION[r.collection] || r.collection) + "</td><td>" + review(r.review_status) + "</td></tr>";
        }).join("") || '<tr><td colspan="7" class="muted">No device matches.</td></tr>';
      }
      ["q", "manufacturer", "collection", "integration"].forEach(function (k) {
        document.getElementById("f-" + k).addEventListener("input", function (e) { st[k] = e.target.value; draw(); });
      });
      draw();
    });
  }

  function curveCard(host, rec) {
    var axes = rec.axes, xAxis = axes[axes.length - 1];
    var seriesAxis = axes.filter(function (a) { return a.name === "junction_temperature"; })[0] || axes[0];
    if (seriesAxis === xAxis) seriesAxis = null;
    var fixed = axes.filter(function (a) { return a !== xAxis && a !== seriesAxis; });
    var st = { guard: false, fixed: {} };
    fixed.forEach(function (a) { st.fixed[a.name] = a.values.length - 1; });
    var strides = [], n = 1;
    for (var i = axes.length - 1; i >= 0; i--) { strides[i] = n; n *= axes[i].values.length; }
    var id = "c" + Math.random().toString(36).slice(2);
    host.innerHTML = '<div class="chart-controls">' + fixed.map(function (a) {
      return "<label>" + esc(AXIS[a.name] || a.name) + '<select data-axis="' + esc(a.name) + '">' + a.values.map(function (v, k) {
        return '<option value="' + k + '"' + (k === st.fixed[a.name] ? " selected" : "") + ">" + esc(shown(v, a.unit)) + "</option>";
      }).join("") + "</select></label>";
    }).join("") + '<label class="check"><input type="checkbox" data-guard> Show model guard points (≥ 500 °C)</label></div>' +
      '<div id="' + id + '"></div><details><summary>Stored values shown in this chart</summary><div class="table-wrap" id="' + id + 't"></div></details>';
    function draw() {
      var xs = scale(xAxis.values, xAxis.unit), ys = scale(rec.values, rec.unit), rows = [];
      var groups = seriesAxis ? seriesAxis.values.map(function (v, k) { return { v: v, k: k }; }) : [{ v: null, k: 0 }];
      if (!st.guard && seriesAxis && seriesAxis.name === "junction_temperature") groups = groups.filter(function (g) { return g.v < GUARD_K; });
      var series = groups.map(function (g, gi) {
        var pts = xAxis.values.map(function (x, xi) {
          var index = xi * strides[axes.length - 1];
          axes.forEach(function (a, ai) {
            if (a === seriesAxis) index += g.k * strides[ai];
            else if (a !== xAxis) index += st.fixed[a.name] * strides[ai];
          });
          rows.push([g.v, x, rec.values[index]]);
          return [xs.f(x), ys.f(rec.values[index])];
        });
        return { label: seriesAxis ? shown(g.v, seriesAxis.unit) : rec.name, color: COLORS[gi % COLORS.length], mode: "lines", points: pts };
      });
      MiniPlot.render(document.getElementById(id), {
        ariaLabel: (QTY[rec.name] || rec.name) + " against " + (AXIS[xAxis.name] || xAxis.name),
        x: { label: (AXIS[xAxis.name] || xAxis.name) + " (" + xs.u + ")", format: num },
        y: { label: (QTY[rec.name] || rec.name) + " (" + ys.u + ")", format: num },
        series: series,
        note: "Stored grid points joined by straight lines for reading only; no value between points is claimed."
      });
      document.getElementById(id + "t").innerHTML = "<table><thead><tr>" + (seriesAxis ? "<th class=\"num\">" + esc(AXIS[seriesAxis.name] || seriesAxis.name) + " (" + esc(seriesAxis.unit) + ")</th>" : "") +
        '<th class="num">' + esc(AXIS[xAxis.name] || xAxis.name) + " (" + esc(xAxis.unit) + ')</th><th class="num">' + esc(rec.name) + " (" + esc(rec.unit) + ")</th></tr></thead><tbody>" +
        rows.map(function (r) { return "<tr>" + (seriesAxis ? '<td class="num">' + num(r[0]) + "</td>" : "") + '<td class="num">' + num(r[1]) + '</td><td class="num">' + num(r[2]) + "</td></tr>"; }).join("") +
        "</tbody></table>";
    }
    host.querySelectorAll("select[data-axis]").forEach(function (sel) {
      sel.addEventListener("change", function () { st.fixed[sel.getAttribute("data-axis")] = +sel.value; draw(); });
    });
    host.querySelector("[data-guard]").addEventListener("change", function (e) { st.guard = e.target.checked; draw(); });
    draw();
  }

  function device(id) {
    return Promise.all([load("data/devices/" + encodeURIComponent(id) + ".json"), load("data/summary.json")]).then(function (res) {
      var d = res[0], commit = res[1].build.commit, ident = d.identity;
      var scalars = d.records.filter(function (r) { return r.kind === "scalar"; });
      var curves = d.records.filter(function (r) { return r.kind === "curve"; });
      var thermal = d.records.filter(function (r) { return r.kind === "thermal_network"; });
      var classes = d.records.map(function (r) { return r.data_class; }).filter(function (v, i, a) { return a.indexOf(v) === i; });
      var flags = d.quality_flags.map(function (f) { return '<span class="badge flag">' + esc(f.replace(/_/g, " ")) + "</span>"; }).join(" ");
      var sample = [["Production lot", ident.production_lot_id], ["Physical sample", ident.physical_sample_id]];
      app.innerHTML = '<p class="crumbs"><a href="#/devices">Devices</a> / ' + esc(ident.part_number) + "</p>" +
        "<h1>" + esc(ident.manufacturer) + " " + esc(ident.part_number) + "</h1>" +
        '<p class="head-meta">' + classes.map(badge).join(" ") + " " + review(d.review_status) + " " + flags + "</p>" +
        '<p class="lead">' + esc(d.collection_meaning) + "</p>" + rightsNotice(d.sources) +
        '<div class="grid-2"><div class="card"><h2>Identity</h2><table class="kv"><tbody>' +
        "<tr><th>Manufacturer</th><td>" + esc(ident.manufacturer) + "</td></tr><tr><th>Part number</th><td>" + esc(ident.part_number) + "</td></tr>" +
        "<tr><th>Technology</th><td>" + esc(d.classification.technology.replace("_", " ")) + "</td></tr><tr><th>Integration</th><td>" + esc(d.classification.integration) + "</td></tr>" +
        sample.map(function (p) { return "<tr><th>" + p[0] + "</th><td>" + (p[1] ? esc(p[1]) : '<span class="na">not applicable: not a measured sample</span>') + "</td></tr>"; }).join("") +
        '<tr><th>Record</th><td><span class="mono">' + esc(d.device_id) + "</span> revision " + esc(d.revision) + "</td></tr></tbody></table></div>" +
        '<div class="card"><h2>Source of the data</h2>' + sourceList(d.sources, commit) +
        (d.groups_without_data.length ? '<p class="small muted">No data in this record for: ' + esc(d.groups_without_data.map(function (g) { return GROUP[g] || g; }).join(", ")) +
          ". Missing values are left missing.</p>" : "") + "</div></div>" +
        (scalars.length ? "<h2>Values</h2><div class=\"table-wrap\"><table><thead><tr><th>Quantity</th><th class=\"num\">Value</th><th>Conditions</th><th>Statistic</th><th>Data</th><th>Source</th></tr></thead><tbody>" +
          scalars.map(function (r) {
            var loc = (r.source_locators || [])[0];
            return "<tr><td>" + esc(QTY[r.name] || r.name) + '<br><span class="small muted">' + esc(GROUP[r.group] || r.group) + '</span></td><td class="num">' + esc(shown(r.value, r.unit)) +
              '</td><td class="cond">' + conditionText(r.condition) + "</td><td>" + (r.statistic === "unspecified" ? '<span class="na">not stated</span>' : esc(r.statistic)) + "</td><td>" + badge(r.data_class) +
              '</td><td class="small">' + r.sources.map(function (s) { return s.url ? '<a href="' + esc(s.url) + '" rel="noopener">' + esc(s.name) + "</a>" : esc(s.name); }).join("; ") +
              (loc ? '<br><span class="muted">as printed: ' + esc(loc.original_value) + " " + esc(loc.original_unit) + "</span>" : "") + "</td></tr>";
          }).join("") + "</tbody></table></div>" : "") +
        curves.map(function (r, i) {
          return '<div class="card"><h2>' + esc(QTY[r.name] || r.name) + ' <span class="small muted">' + esc(GROUP[r.group] || r.group) + "</span></h2>" +
            '<p class="head-meta">' + badge(r.data_class) + " " + review(r.review_status) + "</p>" +
            '<p class="small">Fixed conditions: ' + conditionText(r.condition) + ". Conditions that vary are the chart axes. Source: " +
            r.sources.map(function (s) { return esc(s.name) + (s.file ? " (" + esc(s.file.split("/").pop()) + ")" : ""); }).join("; ") +
            '. <span class="mono">' + esc(r.record_id) + '</span></p><div id="curve' + i + '"></div></div>';
        }).join("") +
        thermal.map(function (r) {
          return '<div class="card"><h2>Thermal network <span class="small muted">' + esc(r.topology) + ", " + esc(r.from_node) + " to " + esc(r.to_node) + "</span></h2>" +
            '<p class="head-meta">' + badge(r.data_class) + " " + review(r.review_status) + '</p><div class="table-wrap"><table><thead><tr><th class="num">Stage</th><th class="num">R (K/W)</th><th class="num">C (J/K)</th></tr></thead><tbody>' +
            r.elements.map(function (e, k) { return '<tr><td class="num">' + (k + 1) + '</td><td class="num">' + num(e.resistance.value) + '</td><td class="num">' + num(e.capacitance.value) + "</td></tr>"; }).join("") +
            "</tbody></table></div></div>";
        }).join("") +
        '<p class="small"><a href="' + REPO + "/blob/" + esc(commit || "main") + "/" + esc(d.record_path) + '">Full record (JSON) in the repository</a></p>';
      curves.forEach(function (r, i) { curveCard(document.getElementById("curve" + i), r); });
    });
  }

  function sources() {
    return Promise.all([load("data/summary.json"), load("data/sources.json")]).then(function (res) {
      var s = res[0];
      app.innerHTML = "<h1>Sources and rights</h1>" +
        '<p class="lead">Where the data come from and what is known about the right to reuse them.</p>' +
        '<div class="notice"><strong>Three things are licensed separately.</strong> The code is MIT. Manufacturer data keep whatever rights their owners gave; ' +
        "for every source below those rights are not established, and nothing is relicensed. AIPE's own layer (selection, normalisation, flags) is CC BY 4.0 to the extent AIPE holds rights. " +
        '<a href="' + REPO + '/blob/main/LICENSING.md">Full text</a>.</div>' +
        '<div class="table-wrap"><table><thead><tr><th>Owner</th><th>Kind</th><th>Record type</th><th class="num">Devices</th><th class="num">Original files archived</th><th>Rights</th></tr></thead><tbody>' +
        res[1].map(function (r) {
          return "<tr><td>" + (r.owner ? esc(r.owner) : '<span class="na">not stated</span>') + "</td><td>" + esc(r.kind) + "</td><td>" + esc(COLLECTION[r.collection] || r.collection) +
            '</td><td class="num">' + r.devices + '</td><td class="num">' + r.original_files_archived + "</td><td>" + rightsLine(r.rights) + "</td></tr>";
        }).join("") + "</tbody></table></div>" +
        "<h2>Limits of this data</h2><ul>" + s.limitations.map(function (l) { return "<li>" + esc(l) + "</li>"; }).join("") + "</ul>";
    });
  }

  // -- router -----------------------------------------------------------------------------------------------
  function route() {
    var hash = location.hash.replace(/^#\/?/, ""), parts = hash.split("?"), path = parts[0].split("/"), params = {};
    (parts[1] || "").split("&").forEach(function (kv) { var p = kv.split("="); if (p[0]) params[p[0]] = decodeURIComponent(p[1] || ""); });
    var name = path[0] || "overview";
    var view = name === "devices" ? devices(params) : name === "device" ? device(decodeURIComponent(path[1] || "")) : name === "sources" ? sources() : overview();
    document.querySelectorAll("[data-nav]").forEach(function (a) {
      if (a.getAttribute("data-nav") === (name === "device" ? "devices" : name)) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    view.then(function () { window.scrollTo(0, 0); }).catch(function (e) {
      app.innerHTML = '<div class="notice"><strong>Could not show this page.</strong> ' + esc(e.message) + "</div>";
    });
  }
  window.addEventListener("hashchange", route);
  load("data/summary.json").then(function (s) {
    document.getElementById("build-info").textContent = "Package " + s.package_version + (s.build.commit ? " · commit " + s.build.commit.slice(0, 7) : "") + " · built " + s.build.date;
  }).catch(function () {});
  route();
})();
