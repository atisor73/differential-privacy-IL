# Illinois Differential Privacy Demo

This is a standalone Svelte + D3 + Vite demo added without modifying the existing notebook workflow.

## What it shows

- Illinois county and tract maps using the local GeoJSON files already in the repo
- A sampled block-centroid layer for block-level exploration that stays responsive in the browser
- A discrete epsilon slider wired to the existing DP release files in `data/processed_data/DP_noise_sparse`
- A race percent-change histogram panel for the currently selected geography level
- A synthetic "demo VTD" overlay that partitions sampled blocks into simple spatial cells within each county

## Generate the demo bundle

From the repo root:

```bash
cd demo
python3 scripts/build_demo_data.py
```

That creates:

- `public/data/counties.geojson`
- `public/data/tracts.geojson`
- `public/data/metrics.json`

## Run the app

```bash
cd demo
npm install
npm run prep-data
npm run dev
```

## Notes

- The block layer is a deterministic sample of real Illinois blocks rendered as centroid points.
- The VTD overlay is synthetic and exists purely as a visual partitioning aid for the demo.
- The visualization is designed to show released aggregates changing, not people being moved between bins.
