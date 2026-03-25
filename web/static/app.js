/**
 * Eval Agent Web — 前端交互逻辑
 * 负责 tab 切换、API 调用、图表/图谱渲染
 */

const App = (() => {
  /* ── 全局状态 ── */
  const state = {
    currentTab: 'console',
    scanResult: null,       // 最近一次扫描结果
    report: null,           // 最近一次评估报告 (raw markdown)
    codeGraphNetwork: null, // vis.Network 实例
    knowledgeNetwork: null,
    charts: {},             // Chart.js 实例缓存（防重复创建）
  };

  /* ══════════════ Tab 切换 ══════════════ */
  function switchTab(tab) {
    state.currentTab = tab;
    document.querySelectorAll('.nav-item').forEach(el => {
      el.classList.toggle('active', el.dataset.tab === tab);
    });
    document.querySelectorAll('.tab-panel').forEach(el => {
      el.classList.toggle('active', el.id === `tab-${tab}`);
    });
    // 延迟渲染某些组件（避免 canvas 尺寸为 0）
    if (tab === 'codegraph' && state.scanResult) renderCodeGraph();
    if (tab === 'stats'     && state.scanResult) renderStats();
    if (tab === 'knowledge') loadKnowledge();
    if (tab === 'memory')    loadMemory();
  }

  /* ══════════════ 扫描目录 ══════════════ */
  async function scan() {
    const dirInput = document.getElementById('dir-input');
    const directory = dirInput.value.trim();
    if (!directory) { alert('请输入项目目录路径'); return; }

    const statusBar = document.getElementById('scan-status');
    const btnScan = document.getElementById('btn-scan');
    statusBar.className = 'status-bar loading';
    statusBar.textContent = '⏳ 正在扫描 …';
    statusBar.classList.remove('hidden');
    btnScan.disabled = true;

    try {
      const res = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ directory }),
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || '扫描失败');

      state.scanResult = data;
      statusBar.className = 'status-bar success';
      statusBar.textContent = `✅ 扫描完成 — ${data.metrics.total_files} 个文件, ${data.metrics.total_lines} 行代码`;
      renderOverview(data);
      renderFileList(data.files);
      renderIssues(data);
    } catch (err) {
      statusBar.className = 'status-bar error';
      statusBar.textContent = `❌ ${err.message}`;
    } finally {
      btnScan.disabled = false;
    }
  }

  /* ── 渲染概览卡片 ── */
  function renderOverview(data) {
    const m = data.metrics;
    document.getElementById('m-files').textContent = m.total_files;
    document.getElementById('m-lines').textContent = m.total_lines.toLocaleString();
    document.getElementById('m-functions').textContent = m.total_functions;
    document.getElementById('m-classes').textContent = m.total_classes;
    document.getElementById('m-imports').textContent = m.total_imports;
    document.getElementById('m-comments').textContent = m.comment_ratio.toFixed(1) + '%';
    document.getElementById('overview-cards').classList.remove('hidden');
  }

  /* ── 渲染文件列表 ── */
  function renderFileList(files) {
    const tbody = document.querySelector('#file-table tbody');
    tbody.innerHTML = '';
    files
      .sort((a, b) => b.lines - a.lines)
      .forEach(f => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${escapeHtml(f.path)}</td>
          <td>${f.lines}</td>
          <td>${f.code_lines}</td>
          <td>${f.functions}</td>
          <td>${f.classes}</td>
          <td>${f.max_complexity}</td>`;
        tbody.appendChild(tr);
      });
    document.getElementById('file-list-section').classList.remove('hidden');
  }

  /* ── 渲染问题提示 ── */
  function renderIssues(data) {
    const el = document.getElementById('issues-content');
    const parts = [];
    if (data.circular_deps && data.circular_deps.length) {
      parts.push(`<div class="status-bar error">⚠️ 循环依赖: ${data.circular_deps.map(c => c.join(' → ')).join('; ')}</div>`);
    }
    if (data.duplicate_names && data.duplicate_names.length) {
      parts.push(`<div class="status-bar" style="border-color:var(--yellow);color:var(--yellow)">⚠️ 重名定义: ${data.duplicate_names.map(d => `${d.name} (${d.count}处)`).join(', ')}</div>`);
    }
    if (data.syntax_errors && data.syntax_errors.length) {
      parts.push(`<div class="status-bar error">❌ 语法错误: ${data.syntax_errors.map(e => `${e.file}:${e.line}`).join(', ')}</div>`);
    }
    if (parts.length === 0) {
      parts.push('<div class="status-bar success">✅ 未发现结构性问题</div>');
    }
    el.innerHTML = parts.join('');
    document.getElementById('issues-section').classList.remove('hidden');
  }

  /* ══════════════ Code Graph ══════════════ */
  function renderCodeGraph() {
    if (!state.scanResult || !state.scanResult.code_graph) return;
    const graphData = state.scanResult.code_graph;
    document.getElementById('codegraph-placeholder').classList.add('hidden');
    document.getElementById('codegraph-controls').classList.remove('hidden');
    document.getElementById('codegraph-container').classList.remove('hidden');
    document.getElementById('codegraph-legend').classList.remove('hidden');

    const showFiles     = document.getElementById('cg-show-files').checked;
    const showClasses   = document.getElementById('cg-show-classes').checked;
    const showFunctions = document.getElementById('cg-show-functions').checked;
    const showMethods   = document.getElementById('cg-show-methods').checked;

    const visibleGroups = new Set();
    if (showFiles)     visibleGroups.add('file');
    if (showClasses)   visibleGroups.add('class');
    if (showFunctions) visibleGroups.add('function');
    if (showMethods)   visibleGroups.add('method');

    const nodes = graphData.nodes
      .filter(n => visibleGroups.has(n.group))
      .map(n => ({
        id: n.id,
        label: n.label,
        group: n.group,
        title: n.title || n.label,
        size: n.size || 15,
      }));

    const nodeIds = new Set(nodes.map(n => n.id));
    const edges = graphData.edges
      .filter(e => nodeIds.has(e.from) && nodeIds.has(e.to))
      .map(e => ({
        from: e.from,
        to: e.to,
        label: e.label || '',
        dashes: e.dashes || false,
        color: e.color || '#475569',
        arrows: e.arrows || 'to',
        width: e.width || 1,
      }));

    const container = document.getElementById('codegraph-container');
    const options = {
      nodes: {
        font: { color: '#e2e8f0', size: 11, face: 'system-ui' },
        borderWidth: 1,
      },
      edges: {
        font: { color: '#64748b', size: 9, face: 'system-ui', strokeWidth: 0 },
        smooth: { type: 'cubicBezier', roundness: 0.4 },
        arrows: { to: { scaleFactor: 0.6 } },
      },
      groups: {
        file:     { color: { background: '#3b82f6', border: '#2563eb' }, shape: 'box', font: { color: '#fff' } },
        class:    { color: { background: '#a855f7', border: '#7c3aed' }, shape: 'diamond' },
        function: { color: { background: '#22c55e', border: '#16a34a' }, shape: 'dot' },
        method:   { color: { background: '#06b6d4', border: '#0891b2' }, shape: 'dot' },
      },
      physics: {
        stabilization: { iterations: 150 },
        barnesHut: { gravitationalConstant: -4000, springLength: 120 },
      },
      interaction: { hover: true, tooltipDelay: 150, zoomView: true },
    };

    if (state.codeGraphNetwork) state.codeGraphNetwork.destroy();
    state.codeGraphNetwork = new vis.Network(
      container,
      { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) },
      options,
    );
  }

  function fitCodeGraph() {
    if (state.codeGraphNetwork) state.codeGraphNetwork.fit({ animation: true });
  }

  // 监听复选框变化重新渲染
  document.addEventListener('DOMContentLoaded', () => {
    ['cg-show-files', 'cg-show-classes', 'cg-show-functions', 'cg-show-methods'].forEach(id => {
      document.getElementById(id)?.addEventListener('change', () => {
        if (state.currentTab === 'codegraph') renderCodeGraph();
      });
    });
  });

  /* ══════════════ 统计分析 ══════════════ */
  function renderStats() {
    if (!state.scanResult) return;
    document.getElementById('stats-placeholder').classList.add('hidden');
    document.getElementById('stats-content').classList.remove('hidden');

    const data = state.scanResult;
    renderLineChart(data);
    renderFileSizeChart(data);
    renderComplexityChart(data);
    renderCodeCommentsChart(data);
    renderComplexityTable(data);
  }

  function renderLineChart(data) {
    const files = data.files.slice().sort((a, b) => b.code_lines - a.code_lines).slice(0, 15);
    renderOrUpdate('chart-lines', 'bar', {
      labels: files.map(f => shortName(f.path)),
      datasets: [{
        label: '代码行',
        data: files.map(f => f.code_lines),
        backgroundColor: 'rgba(59, 130, 246, 0.6)',
        borderColor: '#3b82f6',
        borderWidth: 1,
      }, {
        label: '注释行',
        data: files.map(f => f.comment_lines),
        backgroundColor: 'rgba(34, 197, 94, 0.6)',
        borderColor: '#22c55e',
        borderWidth: 1,
      }],
    }, { indexAxis: 'y', scales: defaultScales() });
  }

  function renderFileSizeChart(data) {
    const bins = { '0-50': 0, '51-100': 0, '101-200': 0, '201-500': 0, '500+': 0 };
    data.files.forEach(f => {
      const l = f.lines;
      if (l <= 50) bins['0-50']++;
      else if (l <= 100) bins['51-100']++;
      else if (l <= 200) bins['101-200']++;
      else if (l <= 500) bins['201-500']++;
      else bins['500+']++;
    });
    renderOrUpdate('chart-file-sizes', 'doughnut', {
      labels: Object.keys(bins),
      datasets: [{ data: Object.values(bins), backgroundColor: ['#3b82f6', '#06b6d4', '#22c55e', '#eab308', '#ef4444'] }],
    }, { plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 11 } } } } });
  }

  function renderComplexityChart(data) {
    const ranking = (data.complexity_ranking || []).slice(0, 15);
    renderOrUpdate('chart-complexity', 'bar', {
      labels: ranking.map(r => r.name),
      datasets: [{
        label: '圈复杂度',
        data: ranking.map(r => r.complexity),
        backgroundColor: ranking.map(r => r.complexity > 10 ? 'rgba(239,68,68,0.6)' : r.complexity > 5 ? 'rgba(234,179,8,0.6)' : 'rgba(34,197,94,0.6)'),
        borderWidth: 0,
      }],
    }, { scales: defaultScales() });
  }

  function renderCodeCommentsChart(data) {
    const m = data.metrics;
    const codeOnly = m.total_code_lines - m.total_comment_lines;
    renderOrUpdate('chart-code-comments', 'doughnut', {
      labels: ['代码', '注释', '空行/其他'],
      datasets: [{ data: [codeOnly > 0 ? codeOnly : 0, m.total_comment_lines, m.total_lines - m.total_code_lines], backgroundColor: ['#3b82f6', '#22c55e', '#334155'] }],
    }, { plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 11 } } } } });
  }

  function renderComplexityTable(data) {
    const tbody = document.querySelector('#complexity-table tbody');
    tbody.innerHTML = '';
    (data.complexity_ranking || []).slice(0, 20).forEach((r, i) => {
      const tr = document.createElement('tr');
      const color = r.complexity > 10 ? 'var(--red)' : r.complexity > 5 ? 'var(--yellow)' : 'var(--green)';
      tr.innerHTML = `
        <td>${i + 1}</td>
        <td>${escapeHtml(r.name)}</td>
        <td>${escapeHtml(r.file)}</td>
        <td>${r.line}</td>
        <td style="color:${color};font-weight:600">${r.complexity}</td>`;
      tbody.appendChild(tr);
    });
  }

  /* Chart.js 辅助 */
  function renderOrUpdate(canvasId, type, data, extraOpts) {
    if (state.charts[canvasId]) state.charts[canvasId].destroy();
    const ctx = document.getElementById(canvasId).getContext('2d');
    const opts = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#94a3b8', font: { size: 11 } } } },
      ...extraOpts,
    };
    state.charts[canvasId] = new Chart(ctx, { type, data, options: opts });
  }

  function defaultScales() {
    const axis = { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: 'rgba(51,65,85,0.4)' } };
    return { x: axis, y: axis };
  }

  /* ══════════════ 深度评估 (SSE) ══════════════ */
  async function evaluate() {
    const dirInput = document.getElementById('dir-input');
    const directory = dirInput.value.trim();
    if (!directory) { alert('请先在控制台输入项目目录路径'); switchTab('console'); return; }

    const requirements = document.getElementById('eval-requirements').value.trim();
    const focus = [...document.querySelectorAll('.eval-focus:checked')].map(c => c.value);
    const selfCheck = document.getElementById('eval-self-check').checked;

    const btnEval = document.getElementById('btn-evaluate');
    const progressArea = document.getElementById('eval-progress');
    const progressText = document.getElementById('eval-progress-text');
    const logEl = document.getElementById('eval-log');
    const reportArea = document.getElementById('eval-report');

    btnEval.disabled = true;
    progressArea.classList.remove('hidden');
    reportArea.classList.add('hidden');
    logEl.innerHTML = '';
    progressText.textContent = '正在初始化评估 …';

    try {
      const res = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ directory, requirements, focus, self_check: selfCheck }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop(); // 保留不完整的最后一行

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          let event;
          try { event = JSON.parse(line.slice(6)); } catch { continue; }

          if (event.type === 'progress') {
            progressText.textContent = event.message;
            logEl.innerHTML += `<div class="log-line">${escapeHtml(event.message)}</div>`;
            logEl.scrollTop = logEl.scrollHeight;
          } else if (event.type === 'done') {
            state.report = event.report;
            progressArea.classList.add('hidden');
            showReport(event.report);
          } else if (event.type === 'error') {
            progressText.textContent = '❌ ' + event.error;
            progressArea.querySelector('.spinner').style.display = 'none';
          }
        }
      }
    } catch (err) {
      progressText.textContent = '❌ ' + err.message;
      progressArea.querySelector('.spinner').style.display = 'none';
    } finally {
      btnEval.disabled = false;
    }
  }

  function showReport(md) {
    const el = document.getElementById('eval-report');
    el.classList.remove('hidden');
    document.getElementById('eval-report-content').innerHTML = marked.parse(md || '*无报告内容*');
  }

  function copyReport() {
    if (state.report) navigator.clipboard.writeText(state.report).then(() => alert('已复制到剪贴板'));
  }

  function downloadReport() {
    if (!state.report) return;
    const blob = new Blob([state.report], { type: 'text/markdown' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'eval_report.md';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  /* ══════════════ 知识图谱 ══════════════ */
  async function loadKnowledge() {
    try {
      const res = await fetch('/api/knowledge');
      const data = await res.json();
      renderKnowledgeGraph(data.graph);
      renderKnowledgeList(data.categories);
    } catch (err) {
      document.getElementById('knowledge-categories').innerHTML =
        `<div class="status-bar error">加载知识库失败: ${escapeHtml(err.message)}</div>`;
    }
  }

  function renderKnowledgeGraph(graph) {
    if (!graph || !graph.nodes.length) return;
    const container = document.getElementById('knowledge-graph-container');
    const options = {
      nodes: { font: { color: '#e2e8f0', size: 11 }, borderWidth: 1 },
      edges: { color: '#475569', smooth: { type: 'cubicBezier' }, arrows: { to: { scaleFactor: 0.5 } } },
      physics: { barnesHut: { gravitationalConstant: -2000, springLength: 100 } },
      interaction: { hover: true },
    };
    if (state.knowledgeNetwork) state.knowledgeNetwork.destroy();
    state.knowledgeNetwork = new vis.Network(
      container,
      { nodes: new vis.DataSet(graph.nodes), edges: new vis.DataSet(graph.edges) },
      options,
    );
  }

  function renderKnowledgeList(categories) {
    const el = document.getElementById('knowledge-categories');
    if (!categories || !Object.keys(categories).length) {
      el.innerHTML = '<div class="placeholder-msg">知识库暂无内容</div>';
      return;
    }
    el.innerHTML = Object.entries(categories)
      .map(([cat, entries]) => `
        <div class="k-category">
          <div class="k-category-title">${escapeHtml(cat)} (${entries.length})</div>
          ${entries.map(e => `<div class="k-entry">${escapeHtml(typeof e === 'string' ? e : JSON.stringify(e))}</div>`).join('')}
        </div>`)
      .join('');
  }

  /* ══════════════ 记忆库 ══════════════ */
  async function loadMemory() {
    try {
      const res = await fetch('/api/memory');
      const data = await res.json();
      const statsEl = document.getElementById('memory-stats');
      statsEl.textContent = `共 ${data.entries.length} 条长期记忆`;
      statsEl.className = 'status-bar';

      const el = document.getElementById('memory-entries');
      if (!data.entries.length) {
        el.innerHTML = '<div class="placeholder-msg">暂无长期记忆</div>';
        return;
      }
      el.innerHTML = data.entries.map(e => `
        <div class="mem-entry">
          <div class="mem-file">${escapeHtml(e.file || '—')}<span class="mem-score">评分: ${e.score ?? '-'}</span></div>
          <div class="mem-content">${escapeHtml(truncate(e.evaluation || e.content || '', 400))}</div>
          <div class="mem-meta">${e.timestamp || ''}</div>
        </div>`).join('');
    } catch (err) {
      document.getElementById('memory-entries').innerHTML =
        `<div class="status-bar error">加载记忆库失败: ${escapeHtml(err.message)}</div>`;
    }
  }

  /* ══════════════ 目录浏览器 ══════════════ */
  let browserCurrentPath = '';

  async function openBrowser() {
    document.getElementById('dir-browser-overlay').classList.remove('hidden');
    const initial = document.getElementById('dir-input').value.trim() || '~';
    await browseTo(initial);
  }

  function closeBrowser(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('dir-browser-overlay').classList.add('hidden');
  }

  async function browseTo(path) {
    const listEl = document.getElementById('browser-list');
    listEl.innerHTML = '<div class="browser-loading">加载中…</div>';

    try {
      const res = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
      const data = await res.json();
      if (!data.success) { listEl.innerHTML = `<div class="browser-loading">${escapeHtml(data.error)}</div>`; return; }

      browserCurrentPath = data.current;
      document.getElementById('browser-current-path').textContent = data.current;
      renderBreadcrumb(data.current);

      let html = '';
      if (data.parent) {
        html += `<div class="dir-entry dir-entry-up" onclick="App.browseTo('${escapeAttr(data.parent)}')">
          <span class="dir-icon">⬆️</span><span class="dir-name">..</span></div>`;
      }
      if (data.entries.length === 0 && !data.parent) {
        html += '<div class="browser-loading">此目录为空</div>';
      }
      for (const e of data.entries) {
        html += `<div class="dir-entry" ondblclick="App.browseTo('${escapeAttr(e.path)}')" onclick="App.previewDir('${escapeAttr(e.path)}')">
          <span class="dir-icon">📁</span><span class="dir-name">${escapeHtml(e.name)}</span></div>`;
      }
      listEl.innerHTML = html;
    } catch (err) {
      listEl.innerHTML = `<div class="browser-loading">请求失败: ${escapeHtml(err.message)}</div>`;
    }
  }

  function previewDir(path) {
    browserCurrentPath = path;
    document.getElementById('browser-current-path').textContent = path;
  }

  function renderBreadcrumb(fullPath) {
    const bcEl = document.getElementById('browser-breadcrumb');
    const parts = fullPath.split('/').filter(Boolean);
    let html = '';
    let accumulated = '';
    for (let i = 0; i < parts.length; i++) {
      accumulated += '/' + parts[i];
      const isLast = i === parts.length - 1;
      if (i > 0) html += '<span class="bc-sep">/</span>';
      if (isLast) {
        html += `<span class="bc-item bc-current">${escapeHtml(parts[i])}</span>`;
      } else {
        html += `<button class="bc-item" onclick="App.browseTo('${escapeAttr(accumulated)}')">${escapeHtml(parts[i])}</button>`;
      }
    }
    bcEl.innerHTML = html;
  }

  function selectDir() {
    if (browserCurrentPath) {
      document.getElementById('dir-input').value = browserCurrentPath;
    }
    document.getElementById('dir-browser-overlay').classList.add('hidden');
  }

  function escapeAttr(s) {
    return s.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
  }

  /* ══════════════ 工具函数 ══════════════ */
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
  }
  function shortName(p) { return p.split('/').pop(); }
  function truncate(s, n) { return s.length > n ? s.slice(0, n) + '…' : s; }

  /* ══════════════ 初始化 ══════════════ */
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-item').forEach(el => {
      el.addEventListener('click', () => switchTab(el.dataset.tab));
    });
    // Enter 键触发扫描
    document.getElementById('dir-input')?.addEventListener('keydown', e => {
      if (e.key === 'Enter') scan();
    });
  });

  /* ── 暴露公共 API ── */
  return {
    scan, evaluate, switchTab, fitCodeGraph, copyReport, downloadReport,
    openBrowser, closeBrowser, browseTo, previewDir, selectDir,
  };
})();
