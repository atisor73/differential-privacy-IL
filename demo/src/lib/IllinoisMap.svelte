<script>
  import { createEventDispatcher } from 'svelte';
  import {
    geoMercator,
    geoPath,
    interpolateRgb,
    max,
    polygonHull,
    scaleLinear,
    schemeTableau10
  } from 'd3';
  import { populationChange } from './metrics.js';

  export let countiesGeojson;
  export let tractsGeojson;
  export let countyRecords = [];
  export let tractRecords = [];
  export let epsilonIndex = 0;
  export let level = 'county';
  export let changeMode = 'absolute';

  const dispatch = createEventDispatcher();
  const width = 360;
  const height = 340;
  const projection = geoMercator();
  let path;
  let countyById = new Map();
  let tractById = new Map();
  let countyDomain = 1;
  let tractDomain = 1;
  let activeDomain = 1;

  $: if (countiesGeojson) {
    projection.fitSize([width, height], countiesGeojson);
  }

  $: path = geoPath(projection);

  $: countyById = new Map(countyRecords.map((record) => [record.geoid, record]));
  $: tractById = new Map(tractRecords.map((record) => [record.geoid, record]));

  function robustDomain(records) {
    const values = records
      .flatMap((record) =>
        (record.adjPop ?? []).map((_, index) => Math.abs(populationChange(record, index, changeMode)))
      )
      .filter((value) => Number.isFinite(value) && value > 0)
      .sort((left, right) => left - right);
    if (!values.length) {
      return changeMode === 'percent' ? 0.03 : 1;
    }
    const percentileIndex = Math.min(values.length - 1, Math.floor(values.length * 0.92));
    return Math.max(changeMode === 'percent' ? 0.03 : 1, values[percentileIndex]);
  }

  $: countyDomain = robustDomain(countyRecords);
  $: tractDomain = robustDomain(tractRecords);
  $: activeDomain = level === 'county' ? countyDomain : tractDomain;

  function formatLegendValue(value) {
    if (changeMode === 'percent') {
      return `${(value * 100).toFixed(1)}%`;
    }
    return `${Math.round(value).toLocaleString()}`;
  }

  function fillFor(record) {
    const delta = populationChange(record, epsilonIndex, changeMode);
    const floor = changeMode === 'percent' ? 0.0005 : 5;
    const magnitude = Math.abs(delta);
    if (magnitude <= floor) {
      return '#d7dbe0';
    }
    const scaled = Math.min(1, (magnitude - floor) / Math.max(0.0001, activeDomain - floor));
    const ramp = delta < 0
      ? interpolateRgb('#e3e6ea', '#4a5a6a')
      : interpolateRgb('#e3e6ea', '#7d2230');
    return ramp(0.18 + Math.sqrt(scaled) * 0.82);
  }

  function selectCounty(geoid) {
    dispatch('selectCounty', geoid);
  }

  function inspect(record) {
    dispatch('inspect', record);
  }

  function maybeInspect(record) {
    if (level !== 'block') {
      inspect(record);
    }
  }

  function maybeActivate(event, geoid) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectCounty(geoid);
    }
  }

</script>

<figure class="panel map-panel">
  <div class="panel-header">
    <div>
      <h2>Illinois map</h2>
      <p>Color encodes released population change at the current privacy level.</p>
    </div>
  </div>

  <div class="legend" aria-label="Map color legend">
    <div class="legend-copy">
      <span class="legend-title">{changeMode === 'percent' ? 'Released percent change' : 'Released population change'}</span>
      <span class="legend-note">Slate shows released undercounts, grey marks near-zero change, and maroon shows released overcounts.</span>
    </div>
    <div class="legend-bar" aria-hidden="true"></div>
    <div class="legend-labels">
      <span>{formatLegendValue(-activeDomain)}</span>
      <span>0</span>
      <span>{formatLegendValue(changeMode === 'percent' ? 0.0005 : 5)}</span>
      <span>{formatLegendValue(activeDomain)}</span>
    </div>
  </div>

  <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Illinois differential privacy map">
    <rect width={width} height={height} rx="14" class="paper" />
    {#each countiesGeojson.features as feature}
      <path d={path(feature)} class="outline-base" pointer-events="none" />
    {/each}

    {#if level === 'county'}
      {#each countiesGeojson.features as feature}
        {@const geoid = feature.properties.geoid}
        {@const record = countyById.get(geoid)}
        <path
          d={path(feature)}
          fill={record ? fillFor(record) : '#ece8e1'}
          stroke="rgba(44,35,40,0.32)"
          stroke-width="0.95"
          tabindex="0"
          role="button"
          aria-label={`Select county ${geoid}`}
          on:click={() => selectCounty(geoid)}
          on:keydown={(event) => maybeActivate(event, geoid)}
          on:mouseenter={() => maybeInspect(record)}
        >
          <title>{geoid}</title>
        </path>
      {/each}
    {:else if level === 'tract'}
      {#each tractsGeojson.features as feature}
        {@const geoid = feature.properties.geoid}
        {@const record = tractById.get(geoid)}
        <path
          d={path(feature)}
          fill={record ? fillFor(record) : '#ece8e1'}
          stroke="rgba(44,35,40,0.22)"
          stroke-width="0.4"
          tabindex="0"
          role="button"
          aria-label={`Inspect tract ${geoid}`}
          on:mouseenter={() => maybeInspect(record)}
        >
          <title>{geoid}</title>
        </path>
      {/each}
      {#each countiesGeojson.features as feature}
        <path
          d={path(feature)}
          fill="none"
          stroke="rgba(44,35,40,0.34)"
          stroke-width="0.9"
          pointer-events="none"
        />
      {/each}
    {/if}
  </svg>
</figure>

<style>
  .panel {
    margin: 0;
    padding: 0.85rem;
    border-radius: var(--panel-radius);
    background: var(--paper);
    box-shadow: var(--shadow);
    border: 1px solid rgba(44, 35, 40, 0.08);
  }

  .map-panel {
    width: min(100%, 420px);
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
    margin-bottom: 0.55rem;
  }

  h2 {
    margin: 0;
    font-family: "Fraunces", serif;
    font-size: 1.5rem;
  }

  p {
    margin: 0.2rem 0 0;
    color: var(--muted);
    line-height: 1.45;
  }

  svg {
    width: 100%;
    height: auto;
    display: block;
  }

  .paper {
    fill: #e7eaee;
  }

  .outline-base {
    fill: rgba(231, 234, 238, 0.42);
    stroke: rgba(44, 35, 40, 0.42);
    stroke-width: 1.05;
  }

  .legend {
    margin-top: 0.65rem;
  }

  .legend-copy {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: baseline;
    margin-bottom: 0.35rem;
  }

  .legend-title {
    font-size: 0.84rem;
    color: var(--ink);
    font-weight: 600;
  }

  .legend-note,
  .legend-labels {
    font-size: 0.78rem;
    color: var(--muted);
  }

  .legend-bar {
    height: 12px;
    border-radius: 6px;
    border: 1px solid rgba(44, 35, 40, 0.12);
    background: linear-gradient(90deg, #4a5a6a 0%, #d7dbe0 44%, #e3e6ea 50%, #d7dbe0 56%, #7d2230 100%);
  }

  .legend-labels {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    margin-top: 0.28rem;
  }
</style>
