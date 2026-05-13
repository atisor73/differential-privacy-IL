export const LEVELS = [
  { id: 'county', label: 'Counties' },
  { id: 'tract', label: 'Tracts' }
];

export const CHANGE_MODES = [
  { id: 'absolute', label: 'Population change' },
  { id: 'percent', label: 'Percent change' }
];

export function safeRatio(numerator, denominator) {
  if (!denominator) {
    return 0;
  }
  return numerator / denominator;
}

export function whiteShare(record, epsilonIndex = null, released = false) {
  if (!record) {
    return 0;
  }
  if (released && epsilonIndex !== null) {
    return safeRatio(record.adjWhite[epsilonIndex], record.adjPop[epsilonIndex]);
  }
  return safeRatio(record.white, record.truePop);
}

export function populationChange(record, epsilonIndex, mode = 'absolute') {
  if (!record) {
    return 0;
  }
  const releasedPop =
    (Array.isArray(record.releasedPopForChange) ? record.releasedPopForChange[epsilonIndex] : undefined) ??
    record.adjPop[epsilonIndex];
  const delta = releasedPop - record.truePop;
  if (mode === 'percent') {
    return safeRatio(delta, record.truePop);
  }
  return delta;
}

export function countLabel(level, count) {
  const nouns = {
    county: 'counties',
    tract: 'tracts'
  };
  return `${count.toLocaleString()} ${nouns[level] ?? 'units'}`;
}

export function formatCountyLabel(geoid) {
  if (!geoid) {
    return 'Statewide';
  }
  return `County ${geoid.slice(-3)} (${geoid})`;
}

export function summarize(records, epsilonIndex, mode) {
  if (!records.length) {
    return {
      count: 0,
      meanChange: 0,
      meanAbsoluteChange: 0,
      meanWhiteShare: 0
    };
  }

  let sum = 0;
  let absSum = 0;
  let whiteSum = 0;
  for (const record of records) {
    const change = populationChange(record, epsilonIndex, mode);
    sum += change;
    absSum += Math.abs(change);
    whiteSum += whiteShare(record);
  }

  return {
    count: records.length,
    meanChange: sum / records.length,
    meanAbsoluteChange: absSum / records.length,
    meanWhiteShare: whiteSum / records.length
  };
}
