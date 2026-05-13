<script>
  import { onMount } from 'svelte';
  import DetailPanel from './lib/DetailPanel.svelte';
  import IllinoisMap from './lib/IllinoisMap.svelte';
  import ReadingNotesPanel from './lib/ReadingNotesPanel.svelte';
  import ScopeSummaryPanel from './lib/ScopeSummaryPanel.svelte';
  import ScatterPlot from './lib/ScatterPlot.svelte';
  import { LEVELS, summarize } from './lib/metrics.js';
  import { aggregateBlockLevelReleases } from './lib/simulate.js';

  let countiesGeojson = null;
  let tractsGeojson = null;
  let metrics = null;
  let blockTruthRecords = [];
  let epsilonOptions = ['0.1', '0.2', '0.5', '1', '2'];

  let level = 'county';
  let epsilonSlider = 0;
  let epsilonIndex = 0;
  let epsilonValue = 0.5;
  let epsilonLabel = '0.5';
  let changeMode = 'absolute';
  let inspectedRecord = null;
  let countyRecords = [];
  let tractRecords = [];
  let allTractRecords = [];
  let simulatedCountyRecords = [];
  let simulatedAllTractRecords = [];
  let visibleRecords = [];
  let summary = null;
  let scopeLabel = '';
  const aggregateReleaseCache = new Map();

  const notes = [
    'The map and scatterplot show released aggregates changing while the underlying population stays fixed.',
    'The JavaScript demo adds independent Laplace-style noise to race counts at the block level, clips at zero, and aggregates upward.',
    'Because the released totals come from many noised block-level race cells, tract and county counts can end up above or below the true values.',
    'This is a lightweight visualization model, not the full Census production system.'
  ];

  onMount(async () => {
    const [countiesRes, tractsRes, metricsRes, blockTruthRes] = await Promise.all([
      fetch('/data/counties.geojson'),
      fetch('/data/tracts.geojson'),
      fetch('/data/metrics.json'),
      fetch('/data/block_truth.json')
    ]);

    countiesGeojson = await countiesRes.json();
    tractsGeojson = await tractsRes.json();
    metrics = await metricsRes.json();
    blockTruthRecords = await blockTruthRes.json();

    level = metrics.meta.defaultLevel;
    epsilonOptions = metrics.meta.epsilons ?? epsilonOptions;
    const defaultEpsilon = String(metrics.meta.defaultEpsilon ?? '0.5');
    epsilonIndex = Math.max(0, epsilonOptions.findIndex((value) => String(value) === defaultEpsilon));
    epsilonSlider = epsilonIndex;
  });

  $: countyRecords = metrics?.counties ?? [];
  $: tractRecords = metrics?.tracts ?? [];
  $: epsilonIndex = Math.max(0, Math.min(epsilonOptions.length - 1, Number(epsilonSlider) || 0));
  $: epsilonValue = Number(epsilonOptions[epsilonIndex] ?? 0.5);
  $: epsilonLabel = String(epsilonOptions[epsilonIndex] ?? '0.5');

  $: allTractRecords = tractRecords;
  $: if (blockTruthRecords.length) {
    const cacheKey = `${epsilonLabel}`;
    if (!aggregateReleaseCache.has(cacheKey)) {
      aggregateReleaseCache.set(
        cacheKey,
        aggregateBlockLevelReleases(blockTruthRecords, epsilonValue, ['bias', 'block-truth'])
      );
    }
    const aggregated = aggregateReleaseCache.get(cacheKey);
    simulatedCountyRecords = aggregated.counties;
    simulatedAllTractRecords = aggregated.tracts;
  } else {
    simulatedCountyRecords = [];
    simulatedAllTractRecords = [];
  }

  $: visibleRecords =
    level === 'county'
      ? simulatedCountyRecords
      : simulatedAllTractRecords;

  $: summary = summarize(visibleRecords, 0, changeMode);
  $: scopeLabel =
    level === 'county'
      ? 'Statewide county view'
      : 'Statewide tract view';

  function handleSelectCounty(event) {
    if (level === 'county') {
      inspectedRecord = simulatedCountyRecords.find((record) => record.geoid === event.detail) ?? null;
    }
  }

  function handleInspect(event) {
    inspectedRecord = event.detail ?? null;
  }

  function helperText() {
    if (level === 'county') {
      return 'County values come from noising race counts at the Illinois block level in JavaScript and aggregating those signed block-level errors upward.';
    }
    return 'Tract values come from the same block-level JavaScript noise model aggregated upward from blocks, so they can move above or below truth.';
  }

</script>

{#if !metrics || !countiesGeojson || !tractsGeojson}
  <main class="loading-shell">
    <section class="hero">
      <p class="eyebrow">Preparing the view</p>
      <h1>Illinois differential privacy explorer</h1>
      <p class="lede">Loading geography and released counts from the local demo bundle.</p>
    </section>
  </main>
{:else}
  <main class="shell">
    <section class="hero">
      <div>
        <p class="eyebrow">Rosita Fu & Alyssa Nguyen - DATA 35900 - Spring 2026</p>
        <h1>Visualizing differential privacy in Illinois at various ε</h1>
        <p class="lede">
          This demo keeps the underlying population fixed and lets the published counts change with the privacy
          level through a simple block-level noise model.
        </p>
      </div>
    </section>

    <section class="controls">
      <div class="control-group">
        <span class="control-label">Level</span>
        <div class="segmented">
          {#each LEVELS as option}
            <button
              type="button"
              class:active={level === option.id}
              on:click={() => {
                level = option.id;
                inspectedRecord = null;
              }}
            >
              {option.label}
            </button>
          {/each}
        </div>
      </div>

      <div class="control-group slider-group">
        <div class="slider-copy">
          <span class="control-label">Privacy level</span>
          <strong>ε = {epsilonLabel}</strong>
        </div>
        <input
          type="range"
          min="0"
          max={Math.max(0, epsilonOptions.length - 1)}
          step="1"
          bind:value={epsilonSlider}
        />
        <div class="epsilon-labels">
          {#each epsilonOptions as option}
            <span>{option}</span>
          {/each}
        </div>
      </div>

      <div class="control-group mode-group">
        <span class="control-label">Metric</span>
        <label class="mode-check">
          <input
            type="checkbox"
            checked={changeMode === 'absolute'}
            on:change={() => (changeMode = 'absolute')}
          />
          <span>Population change</span>
        </label>
        <label class="mode-check">
          <input
            type="checkbox"
            checked={changeMode === 'percent'}
            on:change={() => (changeMode = 'percent')}
          />
          <span>Percent change</span>
        </label>
      </div>
    </section>

    {#if helperText()}
      <p class="helper">{helperText()}</p>
    {/if}

    <section class="content">
      <div class="map-column">
        <IllinoisMap
          {countiesGeojson}
          {tractsGeojson}
          countyRecords={simulatedCountyRecords}
          tractRecords={simulatedAllTractRecords}
          epsilonIndex={0}
          {level}
          {changeMode}
          on:selectCounty={handleSelectCounty}
          on:inspect={handleInspect}
        />
        <DetailPanel
          selectedRecord={inspectedRecord}
          epsilonIndex={0}
          {changeMode}
          {level}
        />
      </div>

      <div class="side-column">
        <ScopeSummaryPanel {epsilonLabel} {changeMode} {scopeLabel} {summary} />

        <ScatterPlot
          records={visibleRecords}
          epsilonIndex={0}
          {changeMode}
          {level}
          on:inspect={handleInspect}
        />

        <ReadingNotesPanel {notes} />
      </div>
    </section>
  </main>
{/if}

<style>
  .shell,
  .loading-shell {
    padding: 2rem 1.25rem 3rem;
    max-width: 1440px;
    margin: 0 auto;
  }

  .hero {
    display: grid;
    gap: 1rem;
    grid-template-columns: minmax(0, 1.5fr) minmax(260px, 0.8fr);
    align-items: end;
    margin-bottom: 1.2rem;
  }

  .hero > div:first-child {
    min-width: 0;
  }

  .eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: var(--warm);
    font-size: 0.8rem;
    margin: 0 0 0.55rem;
  }

  h1 {
    margin: 0;
    font-family: "Fraunces", serif;
    font-size: clamp(1.95rem, 3vw, 3.1rem);
    line-height: 1;
    max-width: none;
    white-space: nowrap;
    color: #111827;
  }

  .lede {
    margin: 0.9rem 0 0;
    color: var(--muted);
    max-width: 72ch;
    line-height: 1.6;
    font-size: 1rem;
  }

  .helper {
    color: var(--muted);
  }

  .segmented {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .segmented button {
    border: 0;
    border-radius: var(--pill-radius);
    padding: 0.7rem 0.95rem;
    background: rgba(233, 236, 240, 0.88);
    color: var(--ink);
    transition:
      transform 180ms ease,
      background 180ms ease,
      color 180ms ease;
  }

  .segmented button.active {
    background: var(--accent);
    color: white;
    transform: translateY(-1px);
  }

  .controls {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, auto));
    gap: 1rem;
    align-items: end;
    padding: 1rem;
    border-radius: var(--panel-radius);
    background: rgba(233, 236, 240, 0.94);
    border: 1px solid rgba(44, 35, 40, 0.08);
    box-shadow: var(--shadow);
  }

  .control-group {
    display: grid;
    gap: 0.55rem;
  }

  .control-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .slider-group {
    min-width: 270px;
  }

  .slider-copy {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: baseline;
  }

  .slider-copy strong {
    font-family: "Fraunces", serif;
    font-size: 0.98rem;
    color: #111827;
  }

  input[type="range"] {
    width: 100%;
    accent-color: var(--accent);
  }

  .epsilon-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.68rem;
    color: var(--muted);
  }

  .mode-group {
    min-width: 180px;
  }

  .mode-check {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--muted);
    font-size: 0.82rem;
  }

  .helper {
    margin: 0.9rem 0 1rem;
    padding-left: 0.2rem;
    line-height: 1.5;
  }

  .content {
    display: grid;
    grid-template-columns: minmax(360px, 430px) minmax(0, 540px);
    gap: 1rem;
    align-items: start;
    justify-content: start;
  }

  .map-column,
  .side-column {
    display: grid;
    gap: 1rem;
  }

  @media (max-width: 1100px) {
    .hero,
    .content {
      grid-template-columns: 1fr;
    }

    .controls {
      grid-template-columns: 1fr;
    }

    h1 {
      font-size: clamp(1.7rem, 5vw, 2.4rem);
      white-space: normal;
    }
  }
</style>
