<script>
  import { csvParse } from 'd3';
  import { onMount } from 'svelte';
  import IllinoisMap from './lib/IllinoisMap.svelte';
  import ReadingNotesPanel from './lib/ReadingNotesPanel.svelte';
  import ScopeSummaryPanel from './lib/ScopeSummaryPanel.svelte';
  import VisualTabsPanel from './lib/VisualTabsPanel.svelte';
  import { CHANGE_MODES, LEVELS, summarize } from './lib/metrics.js';

  let countiesGeojson = null;
  let tractsGeojson = null;
  let metrics = null;
  let epsilonOptions = ['0.1', '0.2', '0.5', '1', '2'];

  let level = 'county';
  const selectedRace = 'all';
  let epsilonSlider = 0;
  let epsilonIndex = 0;
  let epsilonLabel = '0.5';
  let changeMode = 'absolute';
  let inspectedRecord = null;
  let countyRecords = [];
  let tractRecords = [];
  let histogramData = null;
  let hasLoadedRelease = false;
  let isLoadingRelease = false;
  let visibleRecords = [];
  let summary = null;
  let scopeLabel = '';
  const selectedRaceLabel = 'Population';
  const selectedRaceSubject = 'population';
  const releaseCache = new Map();
  let releaseLoadToken = 0;
  let loadedEpsilonLabel = '';
  const activeReleaseIndex = 0;

  const notes = [
    'The map reads county and tract population counts directly from the OpenDP CSV releases copied into the demo bundle.',
    'Changing epsilon swaps to a different precomputed OpenDP county and tract release instead of resampling in the browser.',
    'The map now stays on total population rather than switching between race-specific queries.',
    'The right-hand panel compares block, tract, and county race percent-error histograms from the same sparse OpenDP release set.'
  ];

  function toNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function parseReleaseCsv(text) {
    return csvParse(text, (row) => ({
      geoid: row.geoid,
      parentGeoid: row.parent_geoid,
      truePop: toNumber(row.true_pop),
      white: toNumber(row.white),
      black: toNumber(row.black),
      asian: toNumber(row.asian),
      other: toNumber(row.other),
      adjPop: [toNumber(row.adj_pop)],
      adjWhite: [toNumber(row.adj_white)],
      adjBlack: [toNumber(row.adj_black)],
      adjAsian: [toNumber(row.adj_asian)],
      adjOther: [toNumber(row.adj_other)]
    }));
  }

  async function fetchReleaseBundle(label) {
    if (releaseCache.has(label)) {
      return releaseCache.get(label);
    }

    const base = `/data/opendp/epsilon_${label}`;
    const [countyRes, tractRes] = await Promise.all([
      fetch(`${base}/DF_IL_2010_COUNTY_DP.csv`),
      fetch(`${base}/DF_IL_2010_TRACT_DP.csv`)
    ]);

    const [countyText, tractText] = await Promise.all([countyRes.text(), tractRes.text()]);
    const bundle = {
      counties: parseReleaseCsv(countyText),
      tracts: parseReleaseCsv(tractText)
    };
    releaseCache.set(label, bundle);
    return bundle;
  }

  async function loadReleaseBundle(label) {
    if (!label || label === loadedEpsilonLabel) {
      return;
    }

    const token = ++releaseLoadToken;
    isLoadingRelease = true;
    try {
      const bundle = await fetchReleaseBundle(label);
      if (token !== releaseLoadToken) {
        return;
      }

      countyRecords = bundle.counties;
      tractRecords = bundle.tracts;
      loadedEpsilonLabel = label;
      hasLoadedRelease = true;

      if (inspectedRecord?.geoid) {
        const source = level === 'county' ? bundle.counties : bundle.tracts;
        inspectedRecord = source.find((record) => record.geoid === inspectedRecord.geoid) ?? null;
      }
    } finally {
      if (token === releaseLoadToken) {
        isLoadingRelease = false;
      }
    }
  }

  onMount(async () => {
    const [countiesRes, tractsRes, metricsRes, histogramsRes] = await Promise.all([
      fetch('/data/counties.geojson'),
      fetch('/data/tracts.geojson'),
      fetch('/data/metrics.json'),
      fetch('/data/race_histograms.json')
    ]);

    countiesGeojson = await countiesRes.json();
    tractsGeojson = await tractsRes.json();
    metrics = await metricsRes.json();
    histogramData = await histogramsRes.json();

    level = metrics.meta.defaultLevel;
    epsilonOptions = metrics.meta.epsilons ?? epsilonOptions;
    const defaultEpsilon = String(metrics.meta.defaultEpsilon ?? '0.5');
    epsilonIndex = Math.max(0, epsilonOptions.findIndex((value) => String(value) === defaultEpsilon));
    epsilonSlider = epsilonIndex;
  });

  $: epsilonIndex = Math.max(0, Math.min(epsilonOptions.length - 1, Number(epsilonSlider) || 0));
  $: epsilonLabel = String(epsilonOptions[epsilonIndex] ?? '0.5');
  $: if (metrics && epsilonLabel) {
    loadReleaseBundle(epsilonLabel);
  }

  $: visibleRecords = level === 'county' ? countyRecords : tractRecords;
  $: summary = summarize(visibleRecords, activeReleaseIndex, changeMode, selectedRace);
  $: scopeLabel =
    level === 'county'
      ? 'Statewide county view'
      : 'Statewide tract view';

  function handleSelectCounty(event) {
    if (level === 'county') {
      inspectedRecord = countyRecords.find((record) => record.geoid === event.detail) ?? null;
    }
  }

  function handleInspect(event) {
    inspectedRecord = event.detail ?? null;
  }

</script>

{#if !metrics || !countiesGeojson || !tractsGeojson || !histogramData || !hasLoadedRelease}
  <main class="loading-shell">
    <section class="hero">
      <p class="eyebrow">Preparing the view</p>
      <h1>Illinois differential privacy explorer</h1>
      <p class="lede">Loading geography and OpenDP county and tract CSV releases from the local demo bundle.</p>
    </section>
  </main>
{:else}
  <main class="shell">
    <section class="hero">
      <div>
        <p class="eyebrow">Rosita Fu & Alyssa Nguyen - DATA 35900 - Spring 2026</p>
        <h1>Visualizing differential privacy in Illinois at various ε</h1>
        <p class="lede">
          This demo aims to provide a visual modality for policy-makers to understand how parameters
          of differential privacy algorithms affect the original population sample.
          Data from Illinois 2010 census is noised with the open source framework OpenDP. Post-processing attempts
          a simplified version of the TDA algorithm.
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
          <strong>ε = {epsilonLabel}{#if isLoadingRelease} · updating{/if}</strong>
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

      <div class="control-group">
        <span class="control-label">Metric</span>
        <div class="segmented">
          {#each CHANGE_MODES as mode}
            <button
              type="button"
              class:active={changeMode === mode.id}
              on:click={() => {
                changeMode = mode.id;
              }}
            >
              {mode.label}
            </button>
          {/each}
        </div>
      </div>

    </section>

    <section class="content">
      <div class="map-column">
        <IllinoisMap
          {countiesGeojson}
          {tractsGeojson}
          {countyRecords}
          {tractRecords}
          epsilonIndex={activeReleaseIndex}
          {level}
          {changeMode}
          {selectedRace}
          highlightedGeoid={inspectedRecord?.geoid ?? null}
          on:selectCounty={handleSelectCounty}
          on:inspect={handleInspect}
        />
      </div>

      <div class="side-column">
        <ScopeSummaryPanel
          {epsilonLabel}
          {changeMode}
          {scopeLabel}
          {summary}
          {selectedRaceLabel}
          {selectedRaceSubject}
          {level}
        />

        <VisualTabsPanel
          visibleRecords={visibleRecords}
          epsilonIndex={activeReleaseIndex}
          {epsilonLabel}
          {changeMode}
          {level}
          highlightedGeoid={inspectedRecord?.geoid ?? null}
          selectedRecord={inspectedRecord}
          {selectedRace}
          {histogramData}
        />
      </div>
    </section>

    <section class="notes-row">
      <ReadingNotesPanel {notes} />
    </section>
  </main>
{/if}

<style>
  .shell,
  .loading-shell {
    padding: 2rem 1.25rem 3rem;
    max-width: 1520px;
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

  .content {
    display: grid;
    grid-template-columns: minmax(330px, 0.62fr) minmax(700px, 1fr);
    gap: 1.2rem;
    margin-top: 1.2rem;
    align-items: start;
    justify-content: stretch;
  }

  .map-column,
  .side-column {
    display: grid;
    gap: 1rem;
    min-width: 0;
  }

  .notes-row {
    margin-top: 1rem;
    max-width: 1080px;
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
