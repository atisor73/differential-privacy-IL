<script>
  import { scaleLinear } from 'd3';
  import { countLabel, RACES } from './metrics.js';

  export let histogramData = null;
  export let epsilonLabel = '0.5';

  const levels = ['block', 'tract', 'county'];
  const levelLabels = {
    block: 'Blocks',
    tract: 'Tracts',
    county: 'Counties'
  };
  const width = 654;
  const height = 316;
  const panelWidth = 218;
  const margin = { top: 28, right: 18, bottom: 40, left: 58 };
  const plotRaces = RACES.filter((race) => race.id !== 'all');

  let levelRows = [];
  let xScale = scaleLinear();
  let ticks = [-200, -100, 0, 100, 200];
  let clipPct = 200;

  function formatPercent(value) {
    return `${value.toFixed(0)}%`;
  }

  function rowTop(index) {
    return margin.top + index * 60;
  }

  function panelOffset(levelIndex) {
    return levelIndex * panelWidth;
  }

  function panelX(value, levelIndex) {
    return panelOffset(levelIndex) + xScale(value);
  }

  function rowBarHeight(bin, row) {
    const available = 34;
    return (bin.unitShare / row.rowMaxShare) * available;
  }

  function rowBarY(bin, row) {
    return rowTop(row.rowIndex) + 34 - rowBarHeight(bin, row);
  }

  $: {
    clipPct = histogramData?.meta?.clipPct ?? 200;
    xScale = scaleLinear()
      .domain([-clipPct, clipPct])
      .range([margin.left, panelWidth - margin.right]);

    levelRows = levels.map((levelName, levelIndex) => {
      const rows = plotRaces.map((race, rowIndex) => {
        const bins = (histogramData?.rows ?? []).filter(
          (row) => row.epsilon === epsilonLabel && row.level === levelName && row.race === race.id
        );

        return {
          ...race,
          rowIndex,
          bins,
          totalUnits: bins[0]?.totalUnits ?? 0,
          rowMaxShare: Math.max(...bins.map((bin) => bin.unitShare), 0.01)
        };
      });

      return {
        id: levelName,
        label: levelLabels[levelName],
        levelIndex,
        rows,
        totalUnits: Math.max(...rows.map((row) => row.totalUnits), 0)
      };
    });
  }
</script>

<div class="visual-shell">
  <div class="visual-header">
    <div>
      <h2>Race percent-change histograms</h2>
      <p>Block, tract, and county distributions are shown side by side using the same clipped notebook-style percent-error bins.</p>
    </div>
    <span class="badge">ε = {epsilonLabel}</span>
  </div>

  <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Distribution of block, tract, and county percent change by race">
    <rect width={width} height={height} rx="14" class="paper" />

    {#each levelRows as panel}
      <text
        x={panelOffset(panel.levelIndex) + panelWidth / 2}
        y={14}
        text-anchor="middle"
        class="panel-title"
      >
        {panel.label}
      </text>
      <text
        x={panelOffset(panel.levelIndex) + panelWidth / 2}
        y={26}
        text-anchor="middle"
        class="panel-subtitle"
      >
        {countLabel(panel.id, panel.totalUnits)}
      </text>

      {#each ticks as tick}
        <line
          x1={panelX(tick, panel.levelIndex)}
          x2={panelX(tick, panel.levelIndex)}
          y1={margin.top - 2}
          y2={height - margin.bottom}
          class:zero-line={tick === 0}
          class:grid={tick !== 0}
        />
        <text x={panelX(tick, panel.levelIndex)} y={height - 12} text-anchor="middle" class="axis-label">
          {formatPercent(tick)}
        </text>
      {/each}

      {#each panel.rows as row}
        {@const top = rowTop(row.rowIndex)}
        {#if panel.levelIndex === 0}
          <text x={margin.left - 12} y={top + 18} text-anchor="end" class="row-label">{row.label}</text>
        {/if}

        <line
          x1={panelOffset(panel.levelIndex) + margin.left}
          x2={panelOffset(panel.levelIndex) + panelWidth - margin.right}
          y1={top + 34}
          y2={top + 34}
          class="row-guide"
        />

        {#each row.bins as bin}
          {#if bin.unitCount > 0}
            <rect
              x={panelX(bin.start, panel.levelIndex) + 1.6}
              y={rowBarY(bin, row)}
              width={Math.max(1.6, (panelX(bin.end, panel.levelIndex) - panelX(bin.start, panel.levelIndex)) * 0.46)}
              height={rowBarHeight(bin, row)}
              fill="rgba(125, 34, 48, 0.82)"
            >
              <title>{`${panel.label} ${row.label}: ${formatPercent(bin.start)} to ${formatPercent(bin.end)}, ${bin.unitCount.toLocaleString()} units (${(bin.unitShare * 100).toFixed(1)}%)`}</title>
            </rect>
          {/if}
        {/each}
      {/each}
    {/each}

    <text x={width / 2} y={height - 2} text-anchor="middle" class="title-label">Race percent change</text>
  </svg>
</div>

<style>
  .visual-shell {
    display: grid;
    gap: 0.6rem;
  }

  .visual-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
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
    stroke: rgba(28, 25, 23, 0.42);
    stroke-width: 1.4;
  }

  .row-guide {
    stroke: rgba(28, 25, 23, 0.08);
    stroke-width: 1;
  }

  .axis-label,
  .row-label,
  .title-label,
  .panel-title,
  .panel-subtitle {
    fill: var(--muted);
    font-size: 0.72rem;
  }

  .panel-title {
    font-weight: 600;
  }

  .badge {
    font-size: 0.76rem;
    color: var(--muted);
    padding: 0.35rem 0.55rem;
    background: rgba(231, 234, 238, 0.94);
    border-radius: var(--pill-radius);
  }
</style>
