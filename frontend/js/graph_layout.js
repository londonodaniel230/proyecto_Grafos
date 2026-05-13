const REGION_ANCHORS = {
  America: { x: 0.25, y: 0.55 },
  Europe: { x: 0.62, y: 0.35 },
  Africa: { x: 0.58, y: 0.62 },
  Asia: { x: 0.82, y: 0.45 },
  Oceania: { x: 0.9, y: 0.75 },
  Unknown: { x: 0.5, y: 0.5 },
};

const REGION_SPREAD = {
  America: { x: 0.3, y: 0.42 },
  Europe: { x: 0.2, y: 0.25 },
  Africa: { x: 0.22, y: 0.3 },
  Asia: { x: 0.25, y: 0.3 },
  Oceania: { x: 0.14, y: 0.2 },
  Unknown: { x: 0.3, y: 0.35 },
};

const REGION_ALIASES = {
  America: "America",
  Europe: "Europe",
  Africa: "Africa",
  Asia: "Asia",
  Australia: "Oceania",
  Pacific: "Oceania",
  Antarctica: "Unknown",
  Etc: "Unknown",
};

export const LayoutModes = {
  CIRCLE: "circle",
  MAP: "map",
};

export function getLayoutForMode(mode) {
  if (mode === LayoutModes.CIRCLE) {
    return computeCircleLayout;
  }
  return computeMapLayout;
}

export function computeCircleLayout(nodes, width, height) {
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.max(60, Math.min(width, height) * 0.35);

  const positions = new Map();
  const count = nodes.length || 1;
  nodes.forEach((node, index) => {
    const angle = (Math.PI * 2 * index) / count - Math.PI / 2;
    const x = centerX + Math.cos(angle) * radius;
    const y = centerY + Math.sin(angle) * radius;
    positions.set(node.id, { x, y });
  });

  return positions;
}

export function computeMapLayout(nodes, width, height) {
  const safeWidth = Math.max(1, width);
  const safeHeight = Math.max(1, height);
  const margin = Math.min(60, Math.min(safeWidth, safeHeight) * 0.12);
  const areaWidth = Math.max(1, safeWidth - margin * 2);
  const areaHeight = Math.max(1, safeHeight - margin * 2);
  const positions = new Map();

  nodes.forEach((node) => {
    const region = regionFromZone(node.zonaHoraria);
    const anchor = REGION_ANCHORS[region] || REGION_ANCHORS.Unknown;
    const spread = REGION_SPREAD[region] || REGION_SPREAD.Unknown;
    const seed = hashString(`${node.id}-${node.ciudad}-${node.pais}`);
    const rand = seededRandom(seed);

    const jitterX = (rand() - 0.5) * areaWidth * spread.x;
    const jitterY = (rand() - 0.5) * areaHeight * spread.y;
    const x = clamp(
      margin + anchor.x * areaWidth + jitterX,
      margin,
      safeWidth - margin
    );
    const y = clamp(
      margin + anchor.y * areaHeight + jitterY,
      margin,
      safeHeight - margin
    );

    positions.set(node.id, { x, y });
  });

  relaxPositions(positions, nodes, safeWidth, safeHeight, margin);
  return positions;
}

function regionFromZone(zone) {
  if (!zone || typeof zone !== "string") {
    return "Unknown";
  }

  const prefix = zone.split("/")[0];
  return REGION_ALIASES[prefix] || "Unknown";
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function hashString(value) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function seededRandom(seed) {
  let state = seed || 1;
  return () => {
    state = Math.imul(1664525, state) + 1013904223;
    return ((state >>> 0) % 100000) / 100000;
  };
}

function relaxPositions(positions, nodes, width, height, margin) {
  const minDistance = 28;
  const iterations = 24;

  for (let iter = 0; iter < iterations; iter += 1) {
    for (let i = 0; i < nodes.length; i += 1) {
      const nodeA = nodes[i];
      const posA = positions.get(nodeA.id);
      if (!posA) {
        continue;
      }

      for (let j = i + 1; j < nodes.length; j += 1) {
        const nodeB = nodes[j];
        const posB = positions.get(nodeB.id);
        if (!posB) {
          continue;
        }

        const dx = posA.x - posB.x;
        const dy = posA.y - posB.y;
        const dist = Math.hypot(dx, dy) || 1;

        if (dist < minDistance) {
          const push = (minDistance - dist) / dist / 2;
          posA.x += dx * push;
          posA.y += dy * push;
          posB.x -= dx * push;
          posB.y -= dy * push;
        }
      }
    }

    nodes.forEach((node) => {
      const pos = positions.get(node.id);
      if (!pos) {
        return;
      }

      pos.x = clamp(pos.x, margin, width - margin);
      pos.y = clamp(pos.y, margin, height - margin);
    });
  }
}
