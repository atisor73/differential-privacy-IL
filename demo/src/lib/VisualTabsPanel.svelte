<script>
  import DetailPanel from './DetailPanel.svelte';
  import RaceChangeDistribution from './RaceChangeDistribution.svelte';

  export let selectedRecord = null;
  export let visibleRecords = [];
  export let epsilonIndex = 0;
  export let epsilonLabel = '0.5';
  export let changeMode = 'absolute';
  export let level = 'county';
  export let highlightedGeoid = null;
  export let selectedRace = 'all';
  export let histogramData = null;

  let activeView = 'histograms';

  const views = [
    { id: 'histograms', label: 'Percent Population Change by Race' },
    { id: 'bars', label: 'Composition' }
  ];
</script>

<figure class="panel">
  <div class="toggle-row" role="tablist" aria-label="Visual type">
    {#each views as view}
      <button
        type="button"
        role="tab"
        class:active={activeView === view.id}
        aria-selected={activeView === view.id}
        on:click={() => {
          activeView = view.id;
        }}
      >
        {view.label}
      </button>
    {/each}
  </div>

  {#if activeView === 'bars'}
    <DetailPanel
      {selectedRecord}
      {epsilonIndex}
      {changeMode}
      {level}
      {selectedRace}
      embedded={true}
    />
  {:else}
    <RaceChangeDistribution
      {epsilonLabel}
      {histogramData}
    />
  {/if}
</figure>

<style>
  .panel {
    margin: 0;
    padding: 1rem;
    border-radius: var(--panel-radius);
    background: var(--paper);
    box-shadow: var(--shadow);
    border: 1px solid rgba(44, 35, 40, 0.08);
    width: 100%;
  }

  .toggle-row {
    display: inline-flex;
    gap: 0.4rem;
    margin-bottom: 0.85rem;
  }

  .toggle-row button {
    border: 1px solid rgba(44, 35, 40, 0.14);
    border-radius: var(--pill-radius);
    padding: 0.55rem 0.8rem;
    background: rgba(233, 236, 240, 0.88);
    color: var(--ink);
    transition:
      transform 180ms ease,
      border-color 180ms ease,
      background 180ms ease,
      color 180ms ease;
  }

  .toggle-row button.active {
    border-color: rgba(125, 34, 48, 0.9);
    background: var(--accent);
    color: white;
    transform: translateY(-1px);
  }
</style>
