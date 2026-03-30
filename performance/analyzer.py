"""Collect browser performance metrics from Selenium pages."""
from __future__ import annotations

from typing import Any, Dict


def collect_window_performance(driver) -> Dict[str, Any]:
    """Collect key timing metrics from window.performance API."""
    script = """
    const nav = performance.getEntriesByType('navigation')[0] || {};
    const paint = performance.getEntriesByType('paint') || [];
    const fcp = paint.find(p => p.name === 'first-contentful-paint');
    const resources = performance.getEntriesByType('resource') || [];
    const t = performance.timing || {};
    const domNodes = document.getElementsByTagName('*').length || 0;
    const scripts = document.scripts ? document.scripts.length : 0;
    const imgs = Array.from(document.images || []).map(i => ({
      src: i.currentSrc || i.src || '',
      loading: i.loading || '',
      bytes: 0
    }));
    let lcp = 0;
    let cls = 0;
    try {
      if (window.__autoqaLcp == null) {
        new PerformanceObserver((entryList) => {
          const entries = entryList.getEntries();
          const last = entries[entries.length - 1];
          if (last) window.__autoqaLcp = Math.max(window.__autoqaLcp || 0, last.startTime || 0);
        }).observe({ type: 'largest-contentful-paint', buffered: true });
      }
    } catch (e) {}
    try {
      if (window.__autoqaCls == null) {
        window.__autoqaCls = 0;
        new PerformanceObserver((entryList) => {
          for (const entry of entryList.getEntries()) {
            if (!entry.hadRecentInput) window.__autoqaCls += entry.value || 0;
          }
        }).observe({ type: 'layout-shift', buffered: true });
      }
      cls = window.__autoqaCls || 0;
    } catch (e) {}
    lcp = window.__autoqaLcp || 0;
    const loadTime = (nav.loadEventEnd || 0) - (nav.startTime || 0);
    const domLoaded = (nav.domContentLoadedEventEnd || 0) - (nav.startTime || 0);
    const response = (nav.responseEnd || 0) - (nav.requestStart || 0);
    const ttfb = (nav.responseStart || 0) - (nav.requestStart || 0);
    const fidApprox = (nav.domInteractive || 0) - (nav.responseEnd || 0);
    const longTasks = performance.getEntriesByType('longtask') || [];
    const tbt = longTasks.reduce((sum, lt) => sum + Math.max(0, (lt.duration || 0) - 50), 0);
    const tti = Math.max(loadTime, domLoaded + 300);
    return {
      load_time_ms: loadTime > 0 ? loadTime : (t.loadEventEnd && t.navigationStart ? (t.loadEventEnd - t.navigationStart) : 0),
      dom_loaded_ms: domLoaded > 0 ? domLoaded : (t.domContentLoadedEventEnd && t.navigationStart ? (t.domContentLoadedEventEnd - t.navigationStart) : 0),
      fcp_ms: fcp ? (fcp.startTime || 0) : 0,
      tti_ms: tti || 0,
      tbt_ms: tbt || 0,
      lcp_ms: lcp || 0,
      cls: cls || 0,
      fid_ms: fidApprox > 0 ? fidApprox : 0,
      ttfb_ms: ttfb > 0 ? ttfb : (response > 0 ? response : 0),
      resource_count: resources.length,
      script_count: scripts,
      dom_nodes: domNodes,
      images: imgs
    };
    """
    try:
        out = driver.execute_script(script) or {}
        if isinstance(out, dict):
            return out
    except Exception:
        pass
    return {}
