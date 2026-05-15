export const LEVELS = [
  { id: 'county', label: 'Counties' },
  { id: 'tract', label: 'Tracts' }
];

export const RACES = [
  { id: 'all', label: 'All', trueKey: 'truePop', adjustedKey: 'adjPop', color: '#7d2230' },
  { id: 'white', label: 'White', trueKey: 'white', adjustedKey: 'adjWhite', color: '#3b82f6' },
  { id: 'black', label: 'Black', trueKey: 'black', adjustedKey: 'adjBlack', color: '#ef4444' },
  { id: 'asian', label: 'Asian', trueKey: 'asian', adjustedKey: 'adjAsian', color: '#f59e0b' },
  { id: 'other', label: 'Other', trueKey: 'other', adjustedKey: 'adjOther', color: '#10b981' }
];

export const CHANGE_MODES = [
  { id: 'absolute', label: 'Count change' },
  { id: 'percent', label: 'Percent change' }
];

export function safeRatio(numerator, denominator) {
  if (!denominator) {
    return 0;
  }
  return numerator / denominator;
}

export function raceOption(raceId) {
  return RACES.find((race) => race.id === raceId) ?? RACES[0];
}

export function raceLabel(raceId) {
  return raceOption(raceId).label;
}

export function raceMetricLabel(raceId) {
  return raceId === 'all' ? 'Population' : raceLabel(raceId);
}

export function raceSubjectLabel(raceId) {
  return raceId === 'all' ? 'population' : raceLabel(raceId).toLowerCase();
}

export function raceColor(raceId) {
  return raceOption(raceId).color;
}

export function trueRaceCount(record, raceId) {
  if (!record) {
    return 0;
  }

  const option = raceOption(raceId);
  return Number(record[option.trueKey] ?? 0);
}

export function releasedRaceCount(record, epsilonIndex, raceId) {
  if (!record) {
    return 0;
  }

  const option = raceOption(raceId);
  const values = record[option.adjustedKey];
  if (!Array.isArray(values)) {
    return 0;
  }

  return Number(values[epsilonIndex] ?? 0);
}

export function raceShare(record, raceId, epsilonIndex = null, released = false) {
  if (!record) {
    return 0;
  }

  if (released && epsilonIndex !== null) {
    return safeRatio(releasedRaceCount(record, epsilonIndex, raceId), record.adjPop[epsilonIndex]);
  }

  return safeRatio(trueRaceCount(record, raceId), record.truePop);
}

export function countChange(record, epsilonIndex, raceId, mode = 'absolute') {
  if (!record) {
    return 0;
  }

  const delta = releasedRaceCount(record, epsilonIndex, raceId) - trueRaceCount(record, raceId);
  if (mode === 'percent') {
    return safeRatio(delta, trueRaceCount(record, raceId));
  }
  return delta;
}

export function countLabel(level, count) {
  const nouns = {
    block: 'blocks',
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

export function summarize(records, epsilonIndex, mode, raceId) {
  if (!records.length) {
    return {
      count: 0,
      meanChange: 0,
      meanAbsoluteChange: 0,
      meanShare: 0
    };
  }

  let sum = 0;
  let absSum = 0;
  let shareSum = 0;
  for (const record of records) {
    const change = countChange(record, epsilonIndex, raceId, mode);
    sum += change;
    absSum += Math.abs(change);
    shareSum += raceShare(record, raceId);
  }

  return {
    count: records.length,
    meanChange: sum / records.length,
    meanAbsoluteChange: absSum / records.length,
    meanShare: shareSum / records.length
  };
}
