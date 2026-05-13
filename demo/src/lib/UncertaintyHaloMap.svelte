<script>
  import {
    geoMercator,
    geoPath,
    interpolateRgb,
    max,
    scaleSqrt
  } from 'd3';
  import { populationChange, whiteShare } from './metrics.js';

  export let countiesGeojson;
  export let tractsGeojson;
  export let countyRecords = [];
  export let tractRecords = [];
  export let blockRecords = [];
  export let selectedCountyGeoid = '';
  export let epsilonIndex = 0;
  export let level = 'county';

  const width = 760;
  const height = 760;
  const projection = geoMercator();
  let path;
  let countyById = new Map();
  let tractById = new Map();
  let domain = 1;
  let radius = scaleSqrt();

  $: if (countiesGeojson) {
    projection.fitSize([width, height], countiesGeojson);
  }

  $: path = geoPath(projection);
  $: countyById = new Map(countyRecords.map((record) => [record.geoid, record]));
  $: tractById = new Map(tractRecords.map((record) => [record.geoid, record]));
  $: domain = max(
    (level === 'county' ? countyRecords : level === 'tract' ? tractRecords : blockRecords).map((record) =>
      Math.abs(populationChange(record, epsilonIndex))
    )
  ) || 1;
  $: radius = scaleSqrt().domain([0, domain]).range([4, level === 'block' ? 18 : 36]);

  function pointColor(record) {
    return interpolateRgb('#6f7884', '#7d2230')(0.18 + whiteShare(record, epsilonIndex, true) * 0.72);
  }

  function pointOpacity(record) {
    return 0.15 + (Math.abs(populationChange(record, epsilonIndex)) / domain) * 0.55;
  }

  function centroidForFeature(feature) {
    return path.centroid(feature);
  }

  $: activeTractFeatures =
    tractsGeojson?.features.filter(
      (feature) => !selectedCountyGeoid || feature.properties.countyGeoid === selectedCountyGeoid
    ) ?? [];

  $: countyPoints =
    countiesGeojson?.features
      .map((feature) => {
        const record = countyById.get(feature.properties.geoid);
        if (!record) {
          return null;
        }
        return { record, point: centroidForFeature(feature) };
      })
      .filter(Boolean) ?? [];

  $: tractPoints = activeTractFeatures
    .map((feature) => {
      const record = tractById.get(feature.properties.geoid);
      if (!record) {
        return null;
      }
      return { record, point: centroidForFeature(feature) };
    })
    .filter(Boolean);

  $: blockPoints = blockRecords
    .map((record) => ({ record, point: projection([record.lon, record.lat]) }))
    .filter((item) => item.point);
</script>

<article class="panel">
  <div class="panel-header">
    <div>
      <h2>Uncertainty halo map</h2>
      <p>
        Stronger instability creates larger, fuzzier halos. The fill reflects published % white, while the halo
        reflects how much the released total moves away from the underlying total.
      </p>
    </div>
  </div>

  <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Uncertainty halo map">
    <defs>
      <filter id="halo-blur">
        <feGaussianBlur stdDeviation="8"></feGaussianBlur>
      </filter>
    </defs>

    <rect width={width} height={height} rx="14" class="paper"></rect>

    {#if level === 'county'}
      {#each countiesGeojson.features as feature}
        <path d={path(feature)} class="base-shape"></path>
      {/each}
      {#each countyPoints as item}
        <circle
          cx={item.point[0]}
          cy={item.point[1]}
          r={radius(Math.abs(populationChange(item.record, epsilonIndex)))}
          fill={pointColor(item.record)}
          opacity={pointOpacity(item.record)}
          filter="url(#halo-blur)"
        ></circle>
        <circle
          cx={item.point[0]}
          cy={item.point[1]}
          r="4.2"
          fill={pointColor(item.record)}
          stroke="rgba(44,35,40,0.45)"
        ></circle>
      {/each}
    {:else if level === 'tract'}
      {#each activeTractFeatures as feature}
        <path d={path(feature)} class="base-shape tract"></path>
      {/each}
      {#each tractPoints as item}
        <circle
          cx={item.point[0]}
          cy={item.point[1]}
          r={radius(Math.abs(populationChange(item.record, epsilonIndex)))}
          fill={pointColor(item.record)}
          opacity={pointOpacity(item.record)}
          filter="url(#halo-blur)"
        ></circle>
        <circle
          cx={item.point[0]}
          cy={item.point[1]}
          r="2.6"
          fill={pointColor(item.record)}
        ></circle>
      {/each}
    {:else}
      {#each countiesGeojson.features as feature}
        <path d={path(feature)} class="base-shape"></path>
      {/each}
      {#each blockPoints as item}
        <circle
          cx={item.point[0]}
          cy={item.point[1]}
          r={radius(Math.abs(populationChange(item.record, epsilonIndex)))}
          fill={pointColor(item.record)}
          opacity={pointOpacity(item.record)}
          filter="url(#halo-blur)"
        ></circle>
        <circle
          cx={item.point[0]}
          cy={item.point[1]}
          r="2"
          fill={pointColor(item.record)}
        ></circle>
      {/each}
    {/if}
  </svg>
</article>

<style>
  .panel {
    margin: 0;
    padding: 1rem;
    border-radius: var(--panel-radius);
    background: var(--paper);
    box-shadow: var(--shadow);
    border: 1px solid rgba(44, 35, 40, 0.08);
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
    margin-bottom: 0.85rem;
  }

  h2 {
    margin: 0;
    font-family: "Fraunces", serif;
    font-size: 1.45rem;
  }

  p {
    margin: 0.2rem 0 0;
    color: var(--muted);
    line-height: 1.5;
  }

  svg {
    width: 100%;
    height: auto;
    display: block;
  }

  .paper {
    fill: #e7eaee;
  }

  .base-shape {
    fill: rgba(231, 234, 238, 0.54);
    stroke: rgba(44, 35, 40, 0.32);
    stroke-width: 0.9;
  }

  .base-shape.tract {
    stroke-width: 0.35;
  }
</style>
