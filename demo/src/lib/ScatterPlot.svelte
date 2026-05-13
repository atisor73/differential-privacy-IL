<script>
  import { createEventDispatcher } from 'svelte';
  import {
    extent,
    line,
    max,
    scaleLinear,
    schemeTableau10
  } from 'd3';
  import { populationChange, whiteShare } from './metrics.js';

  export let records = [];
  export let epsilonIndex = 0;
  export let changeMode = 'absolute';
  export let level = 'county';

  const dispatch = createEventDispatcher();
  const width = 520;
  const height = 220;
  const margin = { top: 14, right: 14, bottom: 40, left: 50 };
  let plotted = [];
  let xScale = scaleLinear();
  let yMin = -1;
  let yMax = 1;
  let yScale = scaleLinear();
  let bins = [];
  let trendLine = null;

  $: plotted = records.map((record) => ({
    record,
    x: whiteShare(record),
    y: populationChange(record, epsilonIndex, changeMode)
  }));

  $: xScale = scaleLinear().domain([0, 1]).range([margin.left, width - margin.right]);

  $: {
    const values = plotted.map((point) => point.y).filter((value) => Number.isFinite(value));
    const domainMin = values.length ? Math.min(...values, 0) : (changeMode === 'percent' ? -0.01 : -1);
    const domainMax = values.length ? Math.max(...values, 0) : (changeMode === 'percent' ? 0.01 : 1);
    if (changeMode === 'percent') {
      const maxAbs = Math.max(Math.abs(domainMin), Math.abs(domainMax), 0.01);
      yMin = -maxAbs;
      yMax = maxAbs;
    } else {
      const maxAbs = Math.max(Math.abs(domainMin), Math.abs(domainMax), 1);
      yMin = -maxAbs;
      yMax = maxAbs;
    }
  }
  $: yScale = scaleLinear().domain([yMin, yMax]).range([height - margin.bottom, margin.top]).nice();

  $: bins = buildBins(plotted, 12);
  $: trendLine = line()
    .x((point) => xScale(point.x))
    .y((point) => yScale(point.y))(bins);

  function buildBins(points, count) {
    const buckets = Array.from({ length: count }, (_, index) => ({
      x0: index / count,
      x1: (index + 1) / count,
      values: []
    }));
    for (const point of points) {
      const idx = Math.min(count - 1, Math.floor(point.x * count));
      buckets[idx].values.push(point.y);
    }
    return buckets
      .filter((bucket) => bucket.values.length)
      .map((bucket) => ({
        x: (bucket.x0 + bucket.x1) / 2,
        y: bucket.values.reduce((sum, value) => sum + value, 0) / bucket.values.length
      }));
  }

  function dotColor(point) {
    if (level === 'block') {
      const vtdIndex = Number(point.record.demoVtd.split('-v')[1]) - 1;
      return schemeTableau10[vtdIndex % schemeTableau10.length];
    }
    return 'rgba(125, 34, 48, 0.72)';
  }

  function inspect(record) {
    dispatch('inspect', record);
  }

  function maybeInspect(record) {
    if (level !== 'block') {
      inspect(record);
    }
  }

  function maybeInspectActivate(event, record) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      inspect(record);
    }
  }

  function formatPercent(value) {
    return `${(value * 100).toFixed(0)}%`;
  }

  function gridTicks() {
    return [0, 0.25, 0.5, 0.75, 1];
  }

  function yTicks() {
    if (changeMode === 'percent') {
      return yScale.ticks(7);
    }

    const preferred = [-500, -150, -100, -10, -5, -1, 0, 1, 5, 10, 100, 150, 500];
    const [domainMin, domainMax] = yScale.domain();
    const visible = preferred.filter((tick) => tick >= domainMin && tick <= domainMax);
    if (!visible.includes(0)) {
      visible.push(0);
    }
    return visible.sort((left, right) => left - right);
  }

  function formatYAxisTick(value) {
    if (changeMode === 'percent') {
      return `${(value * 100).toFixed(1)}%`;
    }

    const absValue = Math.abs(value);
    if (absValue >= 1000) {
      return Math.round(value).toLocaleString();
    }
    if (absValue >= 100) {
      return `${Math.round(value)}`;
    }
    if (absValue >= 10) {
      return value.toFixed(0);
    }
    if (absValue >= 1) {
      return value.toFixed(1).replace(/\.0$/, '');
    }
    if (absValue === 0) {
      return '0';
    }
    return value.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
  }
</script>

<figure class="panel scatter-panel">
  <div class="panel-header">
    <div>
      <h2>% white vs. released change</h2>
      <p>The dark line bins points by white share so you can quickly scan for a U-shape.</p>
    </div>
    <span class="badge">{records.length.toLocaleString()} points</span>
  </div>

  <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Scatterplot of white share and differential privacy change">
    <rect width={width} height={height} rx="14" class="paper" />

    {#each gridTicks() as tick}
      <line
        x1={xScale(tick)}
        x2={xScale(tick)}
        y1={margin.top}
        y2={height - margin.bottom}
        class="grid"
      />
      <text x={xScale(tick)} y={height - margin.bottom + 24} text-anchor="middle" class="axis-label">
        {formatPercent(tick)}
      </text>
    {/each}

    {#each yTicks() as tick}
      <line
        x1={margin.left}
        x2={width - margin.right}
        y1={yScale(tick)}
        y2={yScale(tick)}
        class="grid"
      />
      <text x={margin.left - 10} y={yScale(tick) + 4} text-anchor="end" class="axis-label">
        {formatYAxisTick(tick)}
      </text>
    {/each}

    <line x1={margin.left} x2={width - margin.right} y1={yScale(0)} y2={yScale(0)} class="zero-line" />

    {#each plotted as point}
      <circle
        cx={xScale(point.x)}
        cy={yScale(point.y)}
        r={level === 'block' ? 2.6 : 3.1}
        fill={dotColor(point)}
        opacity={level === 'block' ? 0.5 : 0.72}
        role="button"
        tabindex="0"
        aria-label="Inspect scatter point"
        on:mouseenter={() => maybeInspect(point.record)}
        on:click={() => inspect(point.record)}
        on:keydown={(event) => maybeInspectActivate(event, point.record)}
      />
    {/each}

    {#if trendLine}
      <path d={trendLine} class="trend-line" />
    {/if}

    <text x={width / 2} y={height - 12} text-anchor="middle" class="title-label">True share white</text>
    <text
      x={18}
      y={height / 2}
      text-anchor="middle"
      class="title-label"
      transform={`rotate(-90 18 ${height / 2})`}
    >
      {changeMode === 'percent' ? 'Released percent change' : 'Released population change'}
    </text>
  </svg>
</figure>

<style>
  .panel {
    margin: 0;
    padding: 1rem;
    border-radius: var(--panel-radius);
    background: var(--paper);
    box-shadow: var(--shadow);
    border: 1px solid rgba(44, 35, 40, 0.08);
  }

  .scatter-panel {
    width: min(100%, 540px);
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
    margin-bottom: 0.65rem;
  }

  h2 {
    margin: 0;
    font-family: "Fraunces", serif;
    font-size: 1.3rem;
  }

  p {
    margin: 0.2rem 0 0;
    color: var(--muted);
    line-height: 1.4;
    font-size: 0.92rem;
  }

  svg {
    width: 100%;
    height: auto;
    display: block;
  }

  .paper {
    fill: #e7eaee;
  }

  .grid {
    stroke: rgba(28, 25, 23, 0.11);
    stroke-width: 1;
  }

  .zero-line {
    stroke: rgba(125, 34, 48, 0.55);
    stroke-width: 1.4;
  }

  .trend-line {
    fill: none;
    stroke: #641824;
    stroke-width: 2.4;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .axis-label,
  .title-label {
    fill: var(--muted);
    font-size: 0.75rem;
  }

  .badge {
    font-size: 0.76rem;
    color: var(--muted);
    padding: 0.35rem 0.55rem;
    background: rgba(231, 234, 238, 0.94);
    border-radius: var(--pill-radius);
  }
</style>
