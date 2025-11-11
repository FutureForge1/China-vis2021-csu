const { createApp, ref, computed, onMounted } = Vue;

createApp({
  setup() {
    const pollutants = ['pm25', 'pm10'];
    const selectedPollutant = ref('pm25');
    const raw = ref([]);
    // default to full year 2013
    const fromDate = ref('2013-01-01');
    const toDate = ref('2013-12-31');

    const mapChart = ref(null);
    const timeChart = ref(null);
    const loadedFiles = ref([]);

    // global diagnostic helper accessible from anywhere in this script
    function updateDiag(msg) {
      try { console.log('[demo diag]', msg); } catch (e) { }
      const d = document.getElementById('diag');
      if (d) d.innerText = String(msg);
      // also append to loadedFilesList if message indicates a loaded file
      try {
        if (String(msg).startsWith('Loaded')) {
          const list = document.getElementById('loadedFilesList');
          if (list) {
            const li = document.createElement('li');
            li.style.fontSize = '13px';
            li.style.margin = '2px 0';
            li.innerText = msg.replace(/^Loaded \d+ rows from /, '');
            list.appendChild(li);
          }
        }
      } catch (e) { /* ignore DOM errors */ }
    }
    // expose for manual testing in console
    window.demoDiag = updateDiag;

    const tryFetchJson = async (url) => {
      try {
        const res = await fetch(url);
        if (!res.ok) return null;
        const j = await res.json();
        if (Array.isArray(j)) return j;
        if (j && Array.isArray(j.data)) return j.data;
        if (j && Array.isArray(j.rows)) return j.rows;
        for (const k of Object.keys(j || {})) if (Array.isArray(j[k])) return j[k];
        return null;
      } catch (e) {
        return null;
      }
    };

    const fetchText = async (url) => {
      try {
        const res = await fetch(url);
        if (!res.ok) return null;
        return await res.text();
      } catch (e) {
        return null;
      }
    };

    const parseDirListing = (html, baseUrl) => {
      try {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const anchors = Array.from(doc.querySelectorAll('a'));
        const links = anchors.map(a => a.getAttribute('href')).filter(Boolean).map(h => new URL(h, baseUrl).toString());
        return links;
      } catch (e) {
        return [];
      }
    };

    const gatherCsvLinksFromDir = async (dirUrl, seen = new Set()) => {
      // dirUrl should end with '/'
      if (!dirUrl.endsWith('/')) dirUrl = dirUrl + '/';
      if (seen.has(dirUrl)) return [];
      seen.add(dirUrl);
      const html = await fetchText(dirUrl);
      if (!html) return [];
      const links = parseDirListing(html, dirUrl);
      const csvs = [];
      for (const l of links) {
        if (l.toLowerCase().endsWith('.csv')) csvs.push(l);
        else if (l.endsWith('/')) {
          const sub = await gatherCsvLinksFromDir(l, seen);
          csvs.push(...sub);
        }
      }
      return csvs;
    };

    const parseCsv = (text) => {
      const lines = text.split(/\r?\n/).filter(l => l.trim() !== '');
      if (!lines.length) return [];
      const header = lines[0].split(',').map(h => h.trim());
      const out = [];
      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(',');
        if (cols.length < 1) continue;
        const obj = {};
        for (let j = 0; j < header.length; j++) {
          obj[header[j]] = cols[j] !== undefined ? cols[j].trim() : '';
        }
        out.push(obj);
      }
      return out;
    };

    const fetchAndParseCsv = async (url) => {
      const t = await fetchText(url);
      if (!t) return [];
      const rows = parseCsv(t);
      // infer date from filename like 20130101.csv
      try {
        const u = new URL(url, window.location.href);
        const parts = u.pathname.split('/');
        const fname = parts[parts.length - 1] || '';
        const m = fname.match(/(\d{4})(\d{2})(\d{2})/);
        let day = null;
        if (m) day = `${m[1]}-${m[2]}-${m[3]}`;
        // attach time field if missing
        if (day) {
          for (const r of rows) {
            if (!r.time) r.time = day;
          }
        }
        // record loaded file if we got rows
        if (rows && rows.length) {
          try { if (!loadedFiles.value.includes(url)) loadedFiles.value.push(url); } catch (e) { }
          updateDiag(`Loaded ${rows.length} rows from ${url}`);
          console.log('loaded csv', url, rows.length);
        }
      } catch (e) {
        // ignore
      }
      return rows;
    };

    const loadData = async () => {
      const params = new URLSearchParams(window.location.search);
      const userPath = params.get('data');

      // 1) explicit override
      if (userPath) {
        const maybeJson = await tryFetchJson(userPath);
        if (maybeJson && maybeJson.length) { raw.value = maybeJson; initCharts(); return; }
        // try CSV
        const csvRows = await fetchAndParseCsv(userPath);
        if (csvRows && csvRows.length) { raw.value = csvRows; initCharts(); return; }
      }

      // 2) try output echarts JSONs under resources (directory listing required; works with python -m http.server)
      const outDir = '/resources/output/echarts/';
      const outListHtml = await fetchText(outDir);
      if (outListHtml) {
        const links = parseDirListing(outListHtml, outDir).filter(u => u.toLowerCase().endsWith('.json'));
        for (const jurl of links) {
          const j = await tryFetchJson(jurl);
          if (j && j.length) { raw.value = j; console.log('loaded echarts json from', jurl); initCharts(); return; }
        }
      }

      // 3) aggregated CSVs for 2013
      const aggDir = '/resources/aggregated/2013/';
      const csvs = await gatherCsvLinksFromDir(aggDir);
      if (csvs && csvs.length) {
        let combined = [];
        for (const c of csvs) {
          const rows = await fetchAndParseCsv(c);
          combined = combined.concat(rows);
        }
        if (combined.length) { raw.value = combined; console.log('loaded aggregated csvs from', aggDir); initCharts(); return; }
      }

      // 4) processed city CSVs under resources/processed/city/2013
      const procDir = '/resources/processed/city/2013/';
      const procCsvs = await gatherCsvLinksFromDir(procDir);
      if (procCsvs && procCsvs.length) {
        let combined = [];
        for (const c of procCsvs) {
          const rows = await fetchAndParseCsv(c);
          combined = combined.concat(rows);
        }
        if (combined.length) { raw.value = combined; console.log('loaded processed city csvs from', procDir); initCharts(); return; }
      }

      // fallback: relative sample data
      const sample = await tryFetchJson('./data/sample_data.json');
      if (sample && sample.length) { raw.value = sample; initCharts(); return; }

      console.warn('no dataset found; frontend will be empty');
      raw.value = [];
      initCharts();
    };

    // ------------------ file / drag-drop handling ------------------
    const handleParsed = (rows) => {
      if (!rows || !rows.length) return;
      // normalize keys to lower-case common names
      raw.value = rows.map((r, i) => {
        // if PapaParse returned meta fields, plain object is ok
        const obj = {};
        for (const k of Object.keys(r)) {
          const lk = k.trim();
          obj[lk] = r[k];
        }
        if (!obj.id) obj.id = i + 1;
        return obj;
      });
      initCharts();
    };

    const handleFile = (file) => {
      if (!file) return;
      const name = file.name.toLowerCase();
      if (name.endsWith('.json')) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          try {
            const j = JSON.parse(ev.target.result);
            if (Array.isArray(j)) handleParsed(j);
            else if (j && Array.isArray(j.data)) handleParsed(j.data);
            else console.warn('JSON file does not contain array');
          } catch (e) { console.error('failed parsing json', e); }
        };
        reader.readAsText(file);
      } else if (name.endsWith('.csv')) {
        if (window.Papa && Papa.parse) {
          Papa.parse(file, { header: true, dynamicTyping: true, skipEmptyLines: true, complete: (res) => { handleParsed(res.data); } });
        } else {
          // fallback: read text and parse simple CSV
          const reader = new FileReader();
          reader.onload = (ev) => { handleParsed(parseCsv(ev.target.result)); };
          reader.readAsText(file);
        }
      } else {
        console.warn('unsupported file type', file.name);
      }
    };

    const handleFiles = (fileList) => {
      if (!fileList || fileList.length === 0) return;
      // take first file for now
      handleFile(fileList[0]);
    };

    const filtered = computed(() => {
      let rows = raw.value;
      if (fromDate.value) rows = rows.filter(r => r.time >= fromDate.value);
      if (toDate.value) rows = rows.filter(r => r.time <= toDate.value);
      return rows;
    });

    const sampleRows = computed(() => filtered.value.slice(0, 50));

    const columns = computed(() => {
      if (!raw.value || !raw.value.length) return ['time', 'province', 'city', 'pm25', 'pm10'];
      const keys = Object.keys(raw.value[0] || {});
      // prefer order: time, province, city, pm25, pm10 then others
      const preferred = ['time', 'province', 'city', 'pm25', 'pm10'];
      const rest = keys.filter(k => !preferred.includes(k));
      const ordered = preferred.filter(k => keys.includes(k)).concat(rest);
      return ordered;
    });

    function initCharts() {
      // diagnostics helper: write to #diag if present
      function showDiag(msg) {
        try { console.log('[demo diag]', msg); } catch (e) { }
        const d = document.getElementById('diag');
        if (d) d.innerText = String(msg);
      }

      // check ECharts available
      if (typeof echarts === 'undefined') {
        showDiag('ECharts is not available (echarts is undefined). Ensure ./js/echarts.min.js is reachable from this page.');
        return;
      }

      // map scatter: lat/lon axes
      const mapDom = document.getElementById('mapChart');
      if (!mapDom) { showDiag('mapChart DOM element not found (id=mapChart)'); return; }
      const mapRect = mapDom.getBoundingClientRect();
      if (mapRect.width === 0 || mapRect.height === 0) {
        showDiag('mapChart has zero width/height. Check CSS or container layout.');
        // still attempt to init but warn
      }

      try {
        mapChart.value = echarts.init(mapDom);
      } catch (e) {
        showDiag('Failed to initialize ECharts on mapChart: ' + (e && e.message ? e.message : String(e)));
        return;
      }

      // time chart
      const timeDom = document.getElementById('timeChart');
      if (!timeDom) { showDiag('timeChart DOM element not found (id=timeChart)'); return; }
      try {
        timeChart.value = echarts.init(timeDom);
      } catch (e) {
        showDiag('Failed to initialize ECharts on timeChart: ' + (e && e.message ? e.message : String(e)));
        return;
      }

      // clear any previous diag if everything looks good
      showDiag('ECharts initialized — rendering charts');

      renderAll();
      window.addEventListener('resize', () => {
        mapChart.value && mapChart.value.resize();
        timeChart.value && timeChart.value.resize();
      });
    }

    function renderAll() {
      renderMap();
      renderTimeSeries();
    }

    function renderMap() {
      // if data has numeric lon/lat, render scatter; otherwise render top-city bar chart
      const hasCoords = filtered.value.some(r => r.lon !== undefined && r.lat !== undefined && !isNaN(Number(r.lon)) && !isNaN(Number(r.lat)));
      if (hasCoords) {
        const data = filtered.value.map((r, idx) => ({
          name: r.city || `p${idx}`,
          value: [Number(r.lon) || 0, Number(r.lat) || 0, Number(r[selectedPollutant.value]) || 0],
          raw: r
        }));
        const option = {
          title: { text: `散点地图 — ${selectedPollutant.value.toUpperCase()}`, left: 'center' },
          tooltip: {
            trigger: 'item',
            formatter: params => {
              const d = params.data.raw;
              return `${d.city || 'unknown'}<br/>time: ${d.time}<br/>${selectedPollutant.value}: ${d[selectedPollutant.value]}`;
            }
          },
          xAxis: { name: 'lon', type: 'value' },
          yAxis: { name: 'lat', type: 'value' },
          grid: { left: 40, right: 20, top: 60, bottom: 40 },
          series: [
            {
              type: 'scatter',
              symbolSize: val => Math.max(4, Math.sqrt(val[2] || 0) * 1.8),
              data: data,
              encode: { x: 0, y: 1, value: 2 }
            }
          ]
        };
        mapChart.value.setOption(option);
      } else {
        // aggregate by city and show top 20 cities as bar chart
        const byCity = {};
        for (const r of filtered.value) {
          const c = r.city || r.province || 'unknown';
          const v = Number(r[selectedPollutant.value]) || 0;
          if (!byCity[c]) byCity[c] = { sum: 0, n: 0 };
          byCity[c].sum += v; byCity[c].n += 1;
        }
        const rows = Object.keys(byCity).map(k => ({ city: k, val: byCity[k].n ? byCity[k].sum / byCity[k].n : 0 }));
        rows.sort((a, b) => b.val - a.val);
        const top = rows.slice(0, 20).reverse(); // reverse for proper bar order
        const option = {
          title: { text: `按城市平均值排名（${selectedPollutant.value.toUpperCase()}）`, left: 'center' },
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'value' },
          yAxis: { type: 'category', data: top.map(d => d.city) },
          series: [{ type: 'bar', data: top.map(d => d.val) }]
        };
        mapChart.value.setOption(option);
      }
    }

    function renderTimeSeries() {
      // aggregate mean by date
      const byDate = {};
      for (const r of filtered.value) {
        const d = (r.time && String(r.time).split('T')[0]) || r.date || r.day || 'unknown';
        if (!byDate[d]) byDate[d] = { sum: 0, n: 0 };
        const v = Number(r[selectedPollutant.value]) || 0;
        byDate[d].sum += v; byDate[d].n += 1;
      }
      const dates = Object.keys(byDate).sort();
      const vals = dates.map(d => (byDate[d].n ? (byDate[d].sum / byDate[d].n) : 0));

      const option = {
        title: { text: `时间序列平均 — ${selectedPollutant.value.toUpperCase()}`, left: 'center' },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: dates },
        yAxis: { type: 'value' },
        series: [{ type: 'line', data: vals, smooth: true }]
      };
      timeChart.value.setOption(option);
    }

    function resetFilters() {
      fromDate.value = '';
      toDate.value = '';
      selectedPollutant.value = pollutants[0];
      renderAll();
    }

    // watch pollutant and date filters
    const doRender = () => renderAll();

    onMounted(() => {
      loadData();
      // reactive watchers (simple)
      const vm = Vue.reactive({ p: selectedPollutant, from: fromDate, to: toDate });
      // simple interval-based re-render when filters change
      setInterval(() => { renderAll(); }, 800);
      // wire file input
      try {
        const fi = document.getElementById('fileInput');
        if (fi) fi.addEventListener('change', (e) => handleFiles(e.target.files));
      } catch (e) { /* ignore */ }
      // drag and drop on body
      window.addEventListener('dragover', (e) => { e.preventDefault(); });
      window.addEventListener('drop', (e) => { e.preventDefault(); if (e.dataTransfer && e.dataTransfer.files) handleFiles(e.dataTransfer.files); });
    });

    return { pollutants, selectedPollutant, fromDate, toDate, sampleRows, resetFilters };
  }
}).mount('#app');
