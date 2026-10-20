/**
 * Polyomino — Find Hidden Shapes game.
 *
 * Hidden polyominoes are placed on the board. The player traverses
 * the board using piece moves, and landing on a polyomino cell
 * reveals it. The goal is to find all polyominoes.
 */

import {
  GameDefinition,
  GameSettings,
  GameStateSnapshot,
  Position,
  MenuItem,
  getLegalMoves,
  getAllPieces,
  posKey,
  CodecSchema,
  decodeParams,
  StatsPanelContext,
  computeDirectionalCompass,
  buildDirectionalCompassElement,
  CompassDisplayMode,
} from '../../engine';

import {
  getShapesBySize,
  getAllOrientations,
  SHAPE_COLORS,
} from './data';

// ─── Constants ─────────────────────────────────────────────────────────[...]

const BOARD_MIN = 7;
const BOARD_MAX = 12;
const BOARD_DEFAULT = 8;

const SHAPE_CHOICES = [
  'triomino', 'tetromino',
  'pentomino', 'hexomino', 'heptomino', 'octomino', 'mixed',
];
const DENSITY_CHOICES = ['low', 'high'];
const COLOR_CHOICES = ['unique', 'any', 'same'];

const SHAPE_SIZE_MAP: Record<string, number> = {
  triomino: 3, tetromino: 4,
  pentomino: 5, hexomino: 6, heptomino: 7, octomino: 8,
};

const DENSITY_TARGETS: Record<string, number> = {
  low: 0.15, high: 0.35,
};

// ─── Codec Schema ────────────────────────────────────────────────────────[...]

const polyominoSchema: CodecSchema = [
  { name: 'board', bits: 4, encode: (v) => Number(v) - BOARD_MIN, decode: (v) => v + BOARD_MIN },
  {
    name: 'shapes', bits: 4,
    map: Object.fromEntries(SHAPE_CHOICES.map((s, i) => [s, i])),
  },
  {
    name: 'density',
    bits: 2,
    encode: (value) => String(value) === 'high' ? 2 : 0,
    decode: (value) => value >= 2 ? 'high' : 'low',
  },
  { name: 'colors', bits: 2, map: { unique: 0, random: 1, same: 2 } },
];

// ─── Seeded RNG ──────────────────────────────────────────────────────────[...]

function seededRng(seed: number): () => number {
  let s = seed | 0;
  return () => {
    s = (s * 1664525 + 1013904223) | 0;
    return (s >>> 0) / 4294967296;
  };
}

// ─── Shuffle utility ─────────────────────────────────────────────────────[...]

function shuffleArray<T>(arr: T[], rng: () => number): T[] {
  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

// ─── Puzzle Generation ───────────────────────────────────────────────────────

interface PlacedShape {
  shapeId: string;
  cells: Position[];
  color: string;
  revealed: boolean[];
}

interface PuzzleLayout {
  shapes: PlacedShape[];
  allShapeCells: Map<string, { shapeIdx: number; cellIdx: number }>;
}

function generatePuzzle(
  size: number,
  shapeSetting: string,
  densitySetting: string,
  colorSetting: string,
  seed: number,
): PuzzleLayout {
  const rng = seededRng(seed);
  const colorRng = seededRng(seed ^ 0x9e3779b9);  // Use XOR with golden ratio for independent RNG
  const targetCoverage = DENSITY_TARGETS[densitySetting] ?? DENSITY_TARGETS.low;
  const targetCellCount = size * size * targetCoverage;
  const shapes: PlacedShape[] = [];
  const occupied = new Set<string>();
  let placedCellCount = 0;

  // Pre-shuffle colors once with the independent color RNG
  const shuffledColors = shuffleArray([...SHAPE_COLORS], colorRng);
  const shapeIdToColor = new Map<string, string>();
  let colorIndex = 0;

  // Determine which shape sizes to use
  let targetSizes: number[];
  if (shapeSetting === 'mixed') {
    targetSizes = [3, 4, 5, 6, 7, 8];
  } else {
    targetSizes = [SHAPE_SIZE_MAP[shapeSetting] ?? 4];
  }

  // Try to place whole shapes until the target coverage is reached or space runs out.
  const maxFailedPlacements = 200;
  let failedPlacements = 0;
  while (placedCellCount < targetCellCount && failedPlacements < maxFailedPlacements) {
    // Pick random size
    const targetSize = targetSizes[Math.floor(rng() * targetSizes.length)];
    const availableShapes = getShapesBySize(targetSize);
    if (availableShapes.length === 0) {
      failedPlacements++;
      continue;
    }

    // Pick random shape
    const shape = availableShapes[Math.floor(rng() * availableShapes.length)];

    // Pick random orientation
    const orientations = getAllOrientations(shape.cells);
    const cells = orientations[Math.floor(rng() * orientations.length)];

    // Pick random position
    const maxRow = size - Math.max(...cells.map(c => c.row)) - 1;
    const maxCol = size - Math.max(...cells.map(c => c.col)) - 1;
    if (maxRow < 0 || maxCol < 0) {
      failedPlacements++;
      continue;
    }

    const offsetRow = Math.floor(rng() * (maxRow + 1));
    const offsetCol = Math.floor(rng() * (maxCol + 1));

    const placedCells = cells.map(c => ({
      row: c.row + offsetRow,
      col: c.col + offsetCol,
    }));

    // Check no overlap
    const cellKeys = placedCells.map(posKey);
    if (cellKeys.some(k => occupied.has(k))) {
      failedPlacements++;
      continue;
    }

    // Place it
    for (const k of cellKeys) occupied.add(k);

    let color: string;
    if (colorSetting === 'unique') {
      // Assign a stable color per canonical shapeId from the shuffled palette
      if (!shapeIdToColor.has(shape.id)) {
        shapeIdToColor.set(shape.id, shuffledColors[shapeIdToColor.size % shuffledColors.length]);
      }
      color = shapeIdToColor.get(shape.id)!;
    } else if (colorSetting === 'same') {
      color = SHAPE_COLORS[0];
    } else {
      // Random mode: cycle through pre-shuffled colors
      color = shuffledColors[colorIndex % shuffledColors.length];
      colorIndex++;
    }

    shapes.push({
      shapeId: shape.id,
      cells: placedCells,
      color,
      revealed: new Array(placedCells.length).fill(false),
    });
    placedCellCount += placedCells.length;
    failedPlacements = 0;
  }

  // Build cell lookup
  const allShapeCells = new Map<string, { shapeIdx: number; cellIdx: number }>();
  for (let si = 0; si < shapes.length; si++) {
    for (let ci = 0; ci < shapes[si].cells.length; ci++) {
      allShapeCells.set(posKey(shapes[si].cells[ci]), { shapeIdx: si, cellIdx: ci });
    }
  }

  return { shapes, allShapeCells };
}

// ─── Game State Extension ────────────────────────────────────────────────────

interface PolyominoState extends GameStateSnapshot {
  path: Position[];
  visited: Position[];
  shapes: PlacedShape[];
  allShapeCellKeys: string[];  // Serializable version of the map
  totalCells: number;
  revealedCells: number;
  completedShapes: number;
}

function getRemainingShapeCells(state: PolyominoState): Position[] {
  return state.shapes.flatMap(shape =>
    shape.cells.filter((_, idx) => !shape.revealed[idx]),
  );
}

// ─── Game Definition ─────────────────────────────────────────────────────────

const polyominoGame: GameDefinition = {
  name: 'Polyomino',
  icon: 'knight',
  description: 'Find all hidden polyominoes by traversing the board!',
  slug: 'polyominoes',
  showPieceInStatus: true,
  // No more legal moves is a soft ending: keep CONTROLS active and let the
  // player undo and keep exploring. Only the "end game" (resign) button
  // ends the game for real.
  softEndgame: true,
  userSelectsStart: true,

  menuItems: [
    {
      label: 'board',
      options: Array.from({ length: BOARD_MAX - BOARD_MIN + 1 }, (_, i) => i + BOARD_MIN),
      defaultIndex: BOARD_DEFAULT - BOARD_MIN,
    },
    {
      label: 'piece',
      options: getAllPieces(),
      defaultIndex: 0,
      excludedPieces: [
        'queen', 'rook', 'bishop',  // royal
        'wazir', 'ferz', 'dabbaba', 'alfil', 'threeleaper', 'tripper', 'fourleaper', 'commuter', // atomic
        'camel', 'zebra', 'giraffe', 'ibis', 'antelope', 'gazelle', 'flamingo', 'bharal',  // leaper
        'amazon', 'rooferz', 'bizir',  // crowned
        'striker', 'harrier', 'vanguard', 'voyager',  // mounted
        'ostrich', 'aurochs', 'impala', 'wapiti', 'emu', 'argali',   // bounder
        'ferzebra', 'zebbaba',  // fusion
        'kudu', 'nyala', 'vicuna', 'gerenuk', 'markhor',  // strider
        'eft',  // amphibian
        'Pythagoras', 'Fibonacci', 'chiral', 'Minkowski', 'gunkan', 'pterodactyl',  'zebbaba',  // special
      ],
    },
    {
      label: 'shapes',
      options: SHAPE_CHOICES,
      defaultIndex: 1, // tetromino
    },
    {
      label: 'density',
      options: DENSITY_CHOICES,
      defaultIndex: 0,
      buttonGroup: true,
    },
    {
      label: 'colors',
      options: COLOR_CHOICES,
      defaultIndex: 0, // unique
      buttonGroup: true,
    },
  ] as MenuItem[],

  defaultSettings: {
    boardSize: BOARD_DEFAULT,
    piece: 'knight',
    clock: { seconds: 0, mode: 'game' },
    shapes: 'tetromino',
    density: 'low',
    colors: 'unique',
    compassHorizon: 1,
    compassDisplayMode: 'counts',
  },

  getMinBoardSize(pieceName: string): number {
    const minimums: Record<string, number> = {
      knight: 5, zebra: 6, camel: 7, giraffe: 9,
    };
    return minimums[pieceName] ?? 5;
  },

  getEncodeParams(settings: GameSettings): Record<string, number> {
    return {
      board: settings.boardSize,
      shapes: SHAPE_CHOICES.indexOf(String(settings['shapes'])),
      density: String(settings['density']) === 'high' ? 2 : 0,
      colors: COLOR_CHOICES.indexOf(String(settings['colors'])),
    };
  },

  getCodecSchema(): CodecSchema {
    return polyominoSchema;
  },

  validateCodec(code: string): GameSettings | null {
    const result = decodeParams(code, polyominoSchema);
    if (!result) return null;

    return {
      boardSize: Number(result.params['board']),
      piece: 'knight',
      clock: { seconds: 0, mode: 'game' },
      shapes: result.params['shapes'] as string,
      density: result.params['density'] as string,
      colors: result.params['colors'] as string,
      compassHorizon: 1,
      compassDisplayMode: 'counts',
      seed: result.seed,
    };
  },

  setupGame(seed: number, settings: GameSettings): PolyominoState {
    const size = settings.boardSize;
    const shapeSetting = String(settings['shapes'] ?? 'tetromino');
    const densitySetting = String(settings['density'] ?? 'low');
    const colorSetting = String(settings['colors'] ?? 'unique');

    const puzzle = generatePuzzle(size, shapeSetting, densitySetting, colorSetting, seed);

    const totalCells = puzzle.shapes.reduce((sum, s) => sum + s.cells.length, 0);

    return {
      path: [],
      visited: [],
      shapes: puzzle.shapes,
      allShapeCellKeys: Array.from(puzzle.allShapeCells.entries())
        .map(([k, v]) => `${k}:${v.shapeIdx}:${v.cellIdx}`),
      totalCells,
      revealedCells: 0,
      completedShapes: 0,
    };
  },

  makeMove(state: GameStateSnapshot, target: Position): PolyominoState {
    const pState = state as PolyominoState;
    const targetKey = posKey(target);

    // Deep copy shapes
    const shapes = pState.shapes.map(s => ({
      ...s,
      revealed: [...s.revealed],
      cells: [...s.cells],
    }));

    let revealedCells = pState.revealedCells;
    let completedShapes = pState.completedShapes;

    // Check if target is on a shape cell
    const cellEntry = pState.allShapeCellKeys.find(e => e.startsWith(targetKey + ':'));
    if (cellEntry) {
      const [, shapeIdxStr, cellIdxStr] = cellEntry.split(':');
      const shapeIdx = parseInt(shapeIdxStr);
      const cellIdx = parseInt(cellIdxStr);

      if (!shapes[shapeIdx].revealed[cellIdx]) {
        shapes[shapeIdx].revealed[cellIdx] = true;
        revealedCells++;

        // Check if shape is complete
        if (shapes[shapeIdx].revealed.every(Boolean)) {
          completedShapes++;
        }
      }
    }

    // First click: establish the starting square
    if (pState.path.length === 0) {
      return {
        ...pState,
        path: [target],
        visited: [target],
        shapes,
        revealedCells,
        completedShapes,
      };
    }

    return {
      ...pState,
      path: [...pState.path, target],
      visited: [...pState.visited, target],
      shapes,
      revealedCells,
      completedShapes,
    };
  },

  validateMove(state: GameStateSnapshot, target: Position, settings: GameSettings): boolean {
    // Any square is valid as the starting position
    if (state.path.length === 0) return true;

    const currentPos = state.path[state.path.length - 1];
    if (!currentPos) return false;

    const visitedSet = new Set(state.path.map(posKey));
    const legalMoves = getLegalMoves(
      settings.piece,
      currentPos,
      settings.boardSize,
      settings.boardSize,
      visitedSet,
    );

    return legalMoves.some(m => m.row === target.row && m.col === target.col);
  },

  checkEndgame(state: GameStateSnapshot, settings: GameSettings) {
    const pState = state as PolyominoState;

    // No piece placed yet (player hasn't clicked a starting square) — game
    // can't be over.
    if (pState.path.length === 0) return null;

    // Win: all polyomino cells revealed
    if (pState.revealedCells === pState.totalCells && pState.totalCells > 0) {
      return {
        won: true,
        message: `all shapes found in ${pState.path.length - 1} moves`,
        score: pState.completedShapes * 100 + (settings.boardSize * settings.boardSize - pState.path.length),
      };
    }

    // No more moves
    const currentPos = pState.path[pState.path.length - 1];
    const visitedSet = new Set(pState.path.map(posKey));
    const legalMoves = getLegalMoves(
      settings.piece,
      currentPos,
      settings.boardSize,
      settings.boardSize,
      visitedSet,
    );

    if (legalMoves.length === 0) {
      return {
        won: false,
        message: `no legal moves`, // ${pState.revealedCells}/${pState.totalCells} cells (${pState.completedShapes} complete shapes).`,
        score: pState.revealedCells,
      };
    }

    return null;
  },

  captureState(state: GameStateSnapshot): PolyominoState {
    const pState = state as PolyominoState;
    return {
      ...pState,
      path: [...pState.path],
      visited: [...pState.visited],
      shapes: pState.shapes.map(s => ({ ...s, revealed: [...s.revealed], cells: [...s.cells] })),
      solution: pState.solution ? [...pState.solution] : undefined,
      solutionMeta: pState.solutionMeta ? { ...pState.solutionMeta } : undefined,
    };
  },

  restoreState(snapshot: GameStateSnapshot): PolyominoState {
    const pState = snapshot as PolyominoState;
    return {
      ...pState,
      path: [...pState.path],
      visited: [...pState.visited],
      shapes: pState.shapes.map(s => ({ ...s, revealed: [...s.revealed], cells: [...s.cells] })),
      solution: pState.solution ? [...pState.solution] : undefined,
      solutionMeta: pState.solutionMeta ? { ...pState.solutionMeta } : undefined,
    };
  },

  getStatsEntries(): { label: string; value: string }[] {
    return [];
  },

  getStatsPanelElement(state: GameStateSnapshot, settings: GameSettings, context?: StatsPanelContext): HTMLElement | null {
    const pState = state as PolyominoState;
    if (!pState.shapes || pState.shapes.length === 0) return null;

    const currentPos = pState.path[pState.path.length - 1] ?? null;
    const blocked = new Set(pState.path.map(posKey));
    if (currentPos) {
      blocked.delete(posKey(currentPos));
    }

    const compass = computeDirectionalCompass({
      pieceName: settings.piece,
      origin: currentPos,
      rows: settings.boardSize,
      cols: settings.boardSize,
      targets: getRemainingShapeCells(pState),
      horizon: Number(settings['compassHorizon'] ?? 1),
      blocked,
    });

    const container = document.createElement('div');
    container.style.cssText = 'display:flex;flex-direction:column;gap:8px;padding:4px 0;';

    container.appendChild(buildDirectionalCompassElement({
      data: compass,
      displayMode: (settings['compassDisplayMode'] as CompassDisplayMode | undefined) ?? 'counts',
      onHorizonChange: (horizon) => context?.onSettingChange?.('compassHorizon', horizon),
      onDisplayModeChange: (displayMode) => context?.onSettingChange?.('compassDisplayMode', displayMode),
    }));

    const moveCount = Math.max(0, pState.path.length - 1);

    const grid = document.createElement('div');
    grid.style.cssText = 'display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:2px 8px;margin-top:12px;font-size:13px;line-height:1.4;';

    const addRow = (
      col1: string,
      col2: string,
      col4: string,
      opts?: { header?: boolean },
    ) => {
      const col1El = document.createElement('span');
      col1El.textContent = col1;
      col1El.style.cssText = 'text-align:left;color:#000000;';
      if (opts?.header) col1El.style.fontWeight = 'bold';

      const col2El = document.createElement('span');
      col2El.textContent = '';

      const col3El = document.createElement('span');
      col3El.textContent = col2;
      col3El.style.cssText = 'text-align:center;color:#1a56db;';
      if (opts?.header) col3El.style.fontWeight = 'bold';

      const col4El = document.createElement('span');
      col4El.textContent = col4;
      col4El.style.cssText = 'text-align:center;color:#000000;';
      if (opts?.header) col4El.style.fontWeight = 'bold';

      grid.append(col1El, col2El, col3El, col4El);
    };

    addRow('', 'you', 'goal', { header: true });
    addRow('units', String(pState.revealedCells), String(pState.totalCells));
    addRow('shapes', String(pState.completedShapes), String(pState.shapes.length));
    addRow('moves', String(moveCount), '');

    container.appendChild(grid);
    return container;
  },
};

export default polyominoGame;
