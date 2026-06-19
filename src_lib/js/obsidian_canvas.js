(function () {
  const defaultOptions = {
    padding: 40,
    canvasSelector: "#canvas",
    fallbackDataSelector: "#fallback-canvas-data",
    center: true
  };

  async function loadCanvasData(url, options = {}) {
    const settings = { ...defaultOptions, ...options };

    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      const fallback = document.querySelector(settings.fallbackDataSelector);
      if (!fallback) throw error;
      return JSON.parse(fallback.textContent);
    }
  }

  function getBounds(nodes) {
    const minX = Math.min(...nodes.map((node) => node.x));
    const minY = Math.min(...nodes.map((node) => node.y));
    const maxX = Math.max(...nodes.map((node) => node.x + node.width));
    const maxY = Math.max(...nodes.map((node) => node.y + node.height));
    return { minX, minY, maxX, maxY };
  }

  function getAnchor(node, side) {
    const anchors = {
      top: { x: node.x + node.width / 2, y: node.y },
      right: { x: node.x + node.width, y: node.y + node.height / 2 },
      bottom: { x: node.x + node.width / 2, y: node.y + node.height },
      left: { x: node.x, y: node.y + node.height / 2 }
    };
    return anchors[side] || { x: node.x + node.width / 2, y: node.y + node.height / 2 };
  }

  function makePath(from, to, fromSide, toSide) {
    const points = getPathPoints(from, to, fromSide, toSide);
    return [
      `M ${points.from.x} ${points.from.y}`,
      `C ${points.cp1.x} ${points.cp1.y},`,
      `${points.cp2.x} ${points.cp2.y},`,
      `${points.to.x} ${points.to.y}`
    ].join(" ");
  }

  function getPathPoints(from, to, fromSide, toSide) {
    const dx = Math.abs(to.x - from.x);
    const dy = Math.abs(to.y - from.y);
    const bend = Math.max(48, Math.min(160, Math.max(dx, dy) * 0.45));
    const sideOffsets = {
      top: { x: 0, y: -bend },
      right: { x: bend, y: 0 },
      bottom: { x: 0, y: bend },
      left: { x: -bend, y: 0 }
    };
    const fromOffset = sideOffsets[fromSide] || { x: bend, y: 0 };
    const toOffset = sideOffsets[toSide] || { x: -bend, y: 0 };

    return {
      from,
      cp1: { x: from.x + fromOffset.x, y: from.y + fromOffset.y },
      cp2: { x: to.x + toOffset.x, y: to.y + toOffset.y },
      to
    };
  }

  function expandBounds(bounds, point) {
    bounds.minX = Math.min(bounds.minX, point.x);
    bounds.minY = Math.min(bounds.minY, point.y);
    bounds.maxX = Math.max(bounds.maxX, point.x);
    bounds.maxY = Math.max(bounds.maxY, point.y);
  }

  function getContentBounds(nodes, edges) {
    const bounds = getBounds(nodes);
    const nodeById = new Map(nodes.map((node) => [node.id, node]));

    for (const edge of edges || []) {
      const fromNode = nodeById.get(edge.fromNode);
      const toNode = nodeById.get(edge.toNode);
      if (!fromNode || !toNode) continue;

      const from = getAnchor(fromNode, edge.fromSide);
      const to = getAnchor(toNode, edge.toSide);
      const points = getPathPoints(from, to, edge.fromSide, edge.toSide);

      expandBounds(bounds, points.from);
      expandBounds(bounds, points.cp1);
      expandBounds(bounds, points.cp2);
      expandBounds(bounds, points.to);
    }

    return bounds;
  }

  function createTextNode(node) {
    const element = document.createElement("article");
    element.className = `node text-node${node.color ? ` color-${node.color}` : ""}`;
    element.textContent = node.text || "";
    return element;
  }

  function createFileNode(node) {
    const element = document.createElement("article");
    element.className = "node file-node";

    const header = document.createElement("div");
    header.className = "file-header";
    header.textContent = node.file || "Untitled file";

    const body = document.createElement("div");
    body.className = "file-body";
    body.textContent = "File card";

    element.append(header, body);
    return element;
  }

  function createArrowMarker() {
    const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    marker.setAttribute("id", "arrow");
    marker.setAttribute("viewBox", "0 0 10 10");
    marker.setAttribute("refX", "8");
    marker.setAttribute("refY", "5");
    marker.setAttribute("markerWidth", "7");
    marker.setAttribute("markerHeight", "7");
    marker.setAttribute("orient", "auto-start-reverse");

    const arrow = document.createElementNS("http://www.w3.org/2000/svg", "path");
    arrow.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
    arrow.setAttribute("fill", "var(--edge)");
    marker.appendChild(arrow);

    return marker;
  }

  function renderCanvas(data, options = {}) {
    const settings = { ...defaultOptions, ...options };
    const canvas = typeof settings.canvasSelector === "string"
      ? document.querySelector(settings.canvasSelector)
      : settings.canvasSelector;

    if (!canvas) {
      throw new Error("Canvas target was not found.");
    }

    const nodes = data.nodes || [];
    const edges = data.edges || [];

    if (!nodes.length) {
      canvas.innerHTML = '<div class="empty-canvas">Empty canvas</div>';
      return;
    }

    const bounds = getContentBounds(nodes, edges);
    const contentWidth = bounds.maxX - bounds.minX;
    const contentHeight = bounds.maxY - bounds.minY;
    const baseWidth = contentWidth + settings.padding * 2;
    const baseHeight = contentHeight + settings.padding * 2;
    const viewportWidth = canvas.parentElement ? canvas.parentElement.clientWidth : baseWidth;
    const viewportHeight = canvas.parentElement ? canvas.parentElement.clientHeight : baseHeight;
    const width = settings.center ? Math.max(baseWidth, viewportWidth) : baseWidth;
    const height = settings.center ? Math.max(baseHeight, viewportHeight) : baseHeight;
    const centerOffsetX = settings.center ? Math.max(0, (width - baseWidth) / 2) : 0;
    const centerOffsetY = settings.center ? Math.max(0, (height - baseHeight) / 2) : 0;
    const offsetX = settings.padding + centerOffsetX - bounds.minX;
    const offsetY = settings.padding + centerOffsetY - bounds.minY;

    const normalizedNodes = new Map(nodes.map((node) => [
      node.id,
      { ...node, x: node.x + offsetX, y: node.y + offsetY }
    ]));

    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    canvas.innerHTML = "";

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("edges");
    svg.setAttribute("width", width);
    svg.setAttribute("height", height);
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    defs.appendChild(createArrowMarker());
    svg.appendChild(defs);

    for (const edge of edges) {
      const fromNode = normalizedNodes.get(edge.fromNode);
      const toNode = normalizedNodes.get(edge.toNode);
      if (!fromNode || !toNode) continue;

      const from = getAnchor(fromNode, edge.fromSide);
      const to = getAnchor(toNode, edge.toSide);
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.classList.add("edge");
      path.setAttribute("d", makePath(from, to, edge.fromSide, edge.toSide));
      path.setAttribute("marker-end", "url(#arrow)");
      svg.appendChild(path);
    }

    canvas.appendChild(svg);

    for (const node of normalizedNodes.values()) {
      const element = node.type === "file" ? createFileNode(node) : createTextNode(node);
      element.style.left = `${node.x}px`;
      element.style.top = `${node.y}px`;
      element.style.width = `${node.width}px`;
      element.style.height = `${node.height}px`;
      canvas.appendChild(element);
    }
  }

  window.ObsidianCanvas = {
    loadCanvasData,
    renderCanvas
  };
}());
