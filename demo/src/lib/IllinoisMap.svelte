<script>
  import { createEventDispatcher } from 'svelte';
  import {
    geoMercator,
    geoPath,
    interpolateRgb
  } from 'd3';
  import { countChange, raceMetricLabel } from './metrics.js';

  export let countiesGeojson;
  export let tractsGeojson;
  export let countyRecords = [];
  export let tractRecords = [];
  export let epsilonIndex = 0;
  export let level = 'county';
  export let changeMode = 'absolute';
  export let selectedRace = 'white';
  export let highlightedGeoid = null;

  const dispatch = createEventDispatcher();
  const width = 360;
  const height = 375;
  const projection = geoMercator();
  let path;
  let countyById = new Map();
  let tractById = new Map();
  let countyDomain = 1;
  let tractDomain = 1;
  let activeDomain = 1;
  let countyNegativeDomain = 1;
  let countyPositiveDomain = 1;
  let tractNegativeDomain = 1;
  let tractPositiveDomain = 1;
  let activeNegativeDomain = 1;
  let activePositiveDomain = 1;
  let metricLabel = 'Population count change';
  const highlightStroke = '#1f2937';
  let countyFeatures = [];
  let tractFeatures = [];
  let nonHighlightedCountyFeatures = [];
  let highlightedCountyFeatures = [];
  let nonHighlightedTractFeatures = [];
  let highlightedTractFeatures = [];

  $: if (countiesGeojson) {
    projection.fitSize([width, height], countiesGeojson);
  }

  $: path = geoPath(projection);
  $: countyFeatures = countiesGeojson?.features ?? [];
  $: tractFeatures = tractsGeojson?.features ?? [];

  $: countyById = new Map(countyRecords.map((record) => [record.geoid, record]));
  $: tractById = new Map(tractRecords.map((record) => [record.geoid, record]));
  $: metricLabel = `${raceMetricLabel(selectedRace)} ${changeMode === 'percent' ? 'percent change' : 'count change'}`;
  $: nonHighlightedCountyFeatures = countyFeatures.filter((feature) => {
    const record = countyById.get(feature.properties.geoid);
    return !isHighlighted(record);
  });
  $: highlightedCountyFeatures = countyFeatures.filter((feature) => {
    const record = countyById.get(feature.properties.geoid);
    return isHighlighted(record);
  });
  $: nonHighlightedTractFeatures = tractFeatures.filter((feature) => {
    const record = tractById.get(feature.properties.geoid);
    return !isHighlighted(record);
  });
  $: highlightedTractFeatures = tractFeatures.filter((feature) => {
    const record = tractById.get(feature.properties.geoid);
    return isHighlighted(record);
  });

  function robustStats(records) {
    const floor = changeMode === 'percent' ? 0.03 : 1;
    const values = records
      .flatMap((record) =>
        (record.adjPop ?? []).map((_, index) => countChange(record, index, selectedRace, changeMode))
      )
      .filter((value) => Number.isFinite(value));
    if (!values.length) {
      return {
        negativeDomain: floor,
        positiveDomain: floor,
        maxAbsDomain: floor
      };
    }

    const positives = values.filter((value) => value > 0).sort((left, right) => left - right);
    const negatives = values.filter((value) => value < 0).map((value) => Math.abs(value)).sort((left, right) => left - right);
    const positiveDomain = positives.length
      ? Math.max(floor, positives[Math.min(positives.length - 1, Math.floor(positives.length * 0.92))])
      : floor;
    const negativeDomain = negatives.length
      ? Math.max(floor, negatives[Math.min(negatives.length - 1, Math.floor(negatives.length * 0.92))])
      : floor;

    return {
      negativeDomain,
      positiveDomain,
      maxAbsDomain: Math.max(negativeDomain, positiveDomain, floor)
    };
  }

  $: ({ negativeDomain: countyNegativeDomain, positiveDomain: countyPositiveDomain, maxAbsDomain: countyDomain } = robustStats(countyRecords));
  $: ({ negativeDomain: tractNegativeDomain, positiveDomain: tractPositiveDomain, maxAbsDomain: tractDomain } = robustStats(tractRecords));
  $: activeDomain = level === 'county' ? countyDomain : tractDomain;
  $: activeNegativeDomain = level === 'county' ? countyNegativeDomain : tractNegativeDomain;
  $: activePositiveDomain = level === 'county' ? countyPositiveDomain : tractPositiveDomain;

  function formatLegendValue(value) {
    if (changeMode === 'percent') {
      return `${(value * 100).toFixed(1)}%`;
    }
    return `${Math.round(value).toLocaleString()}`;
  }

  function fillFor(record) {
    const delta = countChange(record, epsilonIndex, selectedRace, changeMode);
    const floor = changeMode === 'percent' ? 0.0005 : 1;
    const magnitude = Math.abs(delta);
    if (magnitude <= floor) {
      return '#ddd8d2';
    }

    if (activeNegativeDomain <= floor) {
      const scaled = Math.min(1, (delta - floor) / Math.max(0.0001, activePositiveDomain - floor));
      return interpolateRgb('#ddd8d2', '#7d2230')(0.16 + Math.sqrt(Math.max(0, scaled)) * 0.84);
    }

    if (activePositiveDomain <= floor) {
      const scaled = Math.min(1, (magnitude - floor) / Math.max(0.0001, activeNegativeDomain - floor));
      return interpolateRgb('#edeef0', '#6b7280')(0.16 + Math.sqrt(scaled) * 0.84);
    }

    if (delta < 0) {
      const scaled = Math.min(1, (magnitude - floor) / Math.max(0.0001, activeNegativeDomain - floor));
      return interpolateRgb('#edeef0', '#6b7280')(0.16 + Math.sqrt(scaled) * 0.84);
    }

    const scaled = Math.min(1, (delta - floor) / Math.max(0.0001, activePositiveDomain - floor));
    return interpolateRgb('#e8ddd0', '#7d2230')(0.16 + Math.sqrt(scaled) * 0.84);
  }

  function selectCounty(geoid) {
    dispatch('selectCounty', geoid);
  }

  function inspect(record) {
    dispatch('inspect', record);
  }

  function maybeInspect(record) {
    inspect(record);
  }

  function maybeActivate(event, geoid) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectCounty(geoid);
    }
  }

  function maybeInspectActivate(event, record) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      inspect(record);
    }
  }

  function isHighlighted(record) {
    return Boolean(record?.geoid) && record.geoid === highlightedGeoid;
  }

  function countyRecordFor(feature) {
    return countyById.get(feature.properties.geoid);
  }

  function tractRecordFor(feature) {
    return tractById.get(feature.properties.geoid);
  }

</script>

<figure class="panel map-panel">
  <div class="panel-header">
    <div>
      <h2>Illinois map</h2>
      <p>Color encodes released {metricLabel} at the current privacy level.</p>
    </div>
  </div>

  <div class="legend" aria-label="Map color legend">
    <div class="legend-copy">
      <span class="legend-title">Released {metricLabel}</span>
    </div>
    <div class="legend-bar" aria-hidden="true"></div>
    <div class="legend-labels">
      <span>{formatLegendValue(-activeDomain)}</span>
      <span>0</span>
      <span>{formatLegendValue(activeDomain)}</span>
    </div>
  </div>

  <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Illinois differential privacy map">
    <rect width={width} height={height} rx="14" class="paper" />
    {#each countyFeatures as feature}
      <path d={path(feature)} class="outline-base" pointer-events="none" />
    {/each}

    {#if level === 'county'}
      {#each nonHighlightedCountyFeatures as feature}
        {@const geoid = feature.properties.geoid}
        {@const record = countyRecordFor(feature)}
        <path
          d={path(feature)}
          class="map-region"
          fill={record ? fillFor(record) : '#ece8e1'}
          stroke={isHighlighted(record) ? highlightStroke : 'rgba(44,35,40,0.32)'}
          stroke-width={isHighlighted(record) ? 2.2 : 0.95}
          vector-effect="non-scaling-stroke"
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
      {#each highlightedCountyFeatures as feature}
        {@const geoid = feature.properties.geoid}
        {@const record = countyRecordFor(feature)}
        <path
          d={path(feature)}
          class="map-region"
          fill={record ? fillFor(record) : '#ece8e1'}
          stroke={highlightStroke}
          stroke-width="2.2"
          vector-effect="non-scaling-stroke"
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
      {#each nonHighlightedTractFeatures as feature}
        {@const geoid = feature.properties.geoid}
        {@const record = tractRecordFor(feature)}
        <path
          d={path(feature)}
          class="map-region"
          fill={record ? fillFor(record) : '#ece8e1'}
          stroke={isHighlighted(record) ? highlightStroke : 'rgba(44,35,40,0.22)'}
          stroke-width={isHighlighted(record) ? 1.45 : 0.4}
          vector-effect="non-scaling-stroke"
          tabindex="0"
          role="button"
          aria-label={`Inspect tract ${geoid}`}
          on:mouseenter={() => maybeInspect(record)}
          on:click={() => inspect(record)}
          on:keydown={(event) => maybeInspectActivate(event, record)}
        >
          <title>{geoid}</title>
        </path>
      {/each}
      {#each countyFeatures as feature}
        <path
          d={path(feature)}
          fill="none"
          stroke="rgba(44,35,40,0.34)"
          stroke-width="0.9"
          pointer-events="none"
        />
      {/each}
      {#each highlightedTractFeatures as feature}
        {@const geoid = feature.properties.geoid}
        {@const record = tractRecordFor(feature)}
        <path
          d={path(feature)}
          class="map-region"
          fill={record ? fillFor(record) : '#ece8e1'}
          stroke={highlightStroke}
          stroke-width="1.45"
          vector-effect="non-scaling-stroke"
          tabindex="0"
          role="button"
          aria-label={`Inspect tract ${geoid}`}
          on:mouseenter={() => maybeInspect(record)}
          on:click={() => inspect(record)}
          on:keydown={(event) => maybeInspectActivate(event, record)}
        >
          <title>{geoid}</title>
        </path>
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
    width: 100%;
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

  .map-region:focus,
  .map-region:focus-visible {
    outline: none;
  }

  .legend {
    margin-top: 0.65rem;
  }

  .legend-copy {
    display: block;
    margin-bottom: 0.35rem;
  }

  .legend-title {
    display: block;
    font-size: 0.84rem;
    color: var(--ink);
    font-weight: 600;
  }

  .legend-labels {
    font-size: 0.78rem;
    color: var(--muted);
  }

  .legend-bar {
    height: 12px;
    border-radius: 6px;
    border: 1px solid rgba(44, 35, 40, 0.12);
    background: linear-gradient(90deg, #6b7280 0%, #e5e7eb 34%, #ddd8d2 50%, #e8ddd0 66%, #7d2230 100%);
  }

  .legend-labels {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    margin-top: 0.28rem;
  }
</style>
