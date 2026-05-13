<script>
  import { onMount } from 'svelte';
  import CompositionTiles from './lib/CompositionTiles.svelte';
  import DetailPanel from './lib/DetailPanel.svelte';
  import IllinoisMap from './lib/IllinoisMap.svelte';
  import ReadingNotesPanel from './lib/ReadingNotesPanel.svelte';
  import ScopeSummaryPanel from './lib/ScopeSummaryPanel.svelte';
  import RepeatedReleasePanel from './lib/RepeatedReleasePanel.svelte';
  import ScatterPlot from './lib/ScatterPlot.svelte';
  import { CHANGE_MODES, LEVELS, summarize } from './lib/metrics.js';
  const TABS = [
    { id: 'bias', label: 'Spatial bias' },
    { id: 'releases', label: 'Repeated releases' },
    { id: 'tiles', label: 'Composition tiles' }
  ];

  let countiesGeojson = null;
  let tractsGeojson = null;
  let blocksSampleGeojson = null;
  let metrics = null;
  let epsilonOptions = ['0.1', '0.2', '0.5', '1', '2'];

  let activeTab = 'bias';
  let level = 'county';
  let epsilonSlider = 0;
  let epsilonIndex = 0;
  let epsilonValue = 0.5;
  let epsilonLabel = '0.5';
  let changeMode = 'absolute';
  let overlayVtd = true;
  let inspectedRecord = null;
  let countyRecords = [];
  let tractRecords = [];
  let blockSample = [];
  let allTractRecords = [];
  let allBlockRecords = [];
  let visibleRecords = [];
  let summary = null;
  let scopeLabel = '';

  const notes = [
    'The map and scatterplot show released aggregates changing while the underlying population stays fixed.',
    'Synthetic demo VTDs are spatial partitions of sampled blocks, not official election units.',
    'At the block level, the map uses sampled block polygons only and switches to click-to-inspect so the statewide view stays responsive.'
  ];

  onMount(async () => {
    const [countiesRes, tractsRes, blocksRes, metricsRes] = await Promise.all([
      fetch('/data/counties.geojson'),
      fetch('/data/tracts.geojson'),
      fetch('/data/blocks_sample.geojson'),
      fetch('/data/metrics.json')
    ]);

    countiesGeojson = await countiesRes.json();
    tractsGeojson = await tractsRes.json();
    blocksSampleGeojson = await blocksRes.json();
    metrics = await metricsRes.json();

    level = metrics.meta.defaultLevel;
    epsilonOptions = metrics.meta.epsilons ?? epsilonOptions;
    const defaultEpsilon = String(metrics.meta.defaultEpsilon ?? '0.5');
    epsilonIndex = Math.max(0, epsilonOptions.findIndex((value) => String(value) === defaultEpsilon));
    epsilonSlider = epsilonIndex;
  });

  $: countyRecords = metrics?.counties ?? [];
  $: tractRecords = metrics?.tracts ?? [];
  $: blockSample = metrics?.blockSample ?? [];
  $: epsilonIndex = Math.max(0, Math.min(epsilonOptions.length - 1, Number(epsilonSlider) || 0));
  $: epsilonValue = Number(epsilonOptions[epsilonIndex] ?? 0.5);
  $: epsilonLabel = String(epsilonOptions[epsilonIndex] ?? '0.5');

  $: allTractRecords = tractRecords;
  $: allBlockRecords = blockSample;

  $: visibleRecords =
    level === 'county'
      ? countyRecords
      : level === 'tract'
        ? allTractRecords
        : allBlockRecords;

  $: summary = summarize(visibleRecords, epsilonIndex, changeMode);
  $: scopeLabel =
    level === 'county'
      ? 'Statewide county view'
      : level === 'tract'
        ? 'Statewide tract view'
        : 'Statewide sampled blocks';

  function handleSelectCounty(event) {
    if (level === 'county') {
      inspectedRecord = countyRecords.find((record) => record.geoid === event.detail) ?? null;
    }
  }

  function handleInspect(event) {
    inspectedRecord = event.detail ?? null;
  }

  function helperText() {
    if (activeTab === 'bias') {
      if (level === 'county') {
        return 'County and tract levels use precomputed OpenDP releases loaded from the local Illinois DP pipeline outputs.';
      }
      if (level === 'tract') {
        return 'The tract map and scatterplot show all Illinois tracts at once using precomputed OpenDP-adjusted releases aggregated upward from blocks.';
      }
      return 'Block mode uses a deterministic statewide sample of Illinois block polygons with precomputed OpenDP-adjusted releases from the Python pipeline.';
    }
    if (activeTab === 'releases') {
      return 'These repeated frames are still simulated in-browser; the spatial bias and composition views use the precomputed OpenDP releases.';
    }
    if (activeTab === 'tiles') {
      return 'The tiles compare the true composition to the selected precomputed OpenDP release, so any race share can move up or down from tile to tile.';
    }
    return '';
  }

</script>

{#if !metrics || !countiesGeojson || !tractsGeojson || !blocksSampleGeojson}
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
        <p class="eyebrow">Differential privacy, visualized</p>
        <h1>How Illinois counts wobble when the release changes</h1>
        <p class="lede">
          This demo keeps the underlying population fixed and lets the published counts change with the privacy
          level. The tabs below explore different metaphors: spatial bias, repeated releases, and composition-change
          tiles.
        </p>
      </div>
    </section>

    <section class="tabs">
      {#each TABS as tab}
        <button type="button" class:active={activeTab === tab.id} on:click={() => (activeTab = tab.id)}>
          {tab.label}
        </button>
      {/each}
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

      {#if activeTab === 'bias'}
        <div class="control-group">
          <span class="control-label">Y-axis</span>
          <div class="segmented">
            {#each CHANGE_MODES as option}
              <button type="button" class:active={changeMode === option.id} on:click={() => (changeMode = option.id)}>
                {option.label}
              </button>
            {/each}
          </div>
        </div>
      {/if}

      {#if activeTab === 'bias'}
        <label class="toggle">
          <input type="checkbox" bind:checked={overlayVtd} disabled={level !== 'block'} />
          <span>Show demo VTD overlay</span>
        </label>
      {/if}
    </section>

    {#if helperText()}
      <p class="helper">{helperText()}</p>
    {/if}

    {#if activeTab === 'bias'}
      <section class="content">
        <div class="map-column">
          <IllinoisMap
            {countiesGeojson}
            {tractsGeojson}
            blocksGeojson={blocksSampleGeojson}
            countyRecords={countyRecords}
            tractRecords={allTractRecords}
            blockRecords={allBlockRecords}
            {epsilonIndex}
            {level}
            {changeMode}
            {overlayVtd}
            on:selectCounty={handleSelectCounty}
            on:inspect={handleInspect}
          />
          <DetailPanel
            selectedRecord={inspectedRecord}
            {epsilonIndex}
            {changeMode}
            {level}
          />
        </div>

        <div class="side-column">
          <ScopeSummaryPanel {epsilonLabel} {changeMode} {scopeLabel} {summary} />

          <ScatterPlot
            records={visibleRecords}
            {epsilonIndex}
            {changeMode}
            {level}
            on:inspect={handleInspect}
          />

          <ReadingNotesPanel {notes} />
        </div>
      </section>
    {:else if activeTab === 'releases'}
      <RepeatedReleasePanel
        records={level === 'county' ? countyRecords : level === 'tract' ? allTractRecords : allBlockRecords}
        {epsilonValue}
        {level}
        {scopeLabel}
      />
    {:else if activeTab === 'tiles'}
      <CompositionTiles records={visibleRecords} {epsilonIndex} {level} {epsilonValue} />
    {/if}
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

  .tabs,
  .segmented {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .tabs {
    margin-bottom: 1rem;
  }

  .tabs button,
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

  .tabs button.active,
  .segmented button.active {
    background: var(--accent);
    color: white;
    transform: translateY(-1px);
  }

  .controls {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, auto));
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
    font-size: 0.8rem;
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
    font-size: 1.1rem;
    color: #111827;
  }

  input[type="range"] {
    width: 100%;
    accent-color: var(--accent);
  }

  .epsilon-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.76rem;
    color: var(--muted);
  }

  .toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    color: var(--muted);
    padding-bottom: 0.75rem;
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
