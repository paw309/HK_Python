/**
 * PieceLibrary — All piece definitions with move vector generation.
 * Port of piecekeeper.py with all 38+ pieces.
 */

import { MoveVector, PieceDefinition, PieceGroup, Position } from './types';

// ─── Pattern Definitions ─────────────────────────────────────────────────────

// ─── GCD helper (for coprime leapers) ────────────────────────────────────────

function gcd(a: number, b: number): number {
  while (b !== 0) { [a, b] = [b, a % b]; }
  return a;
}

/**
 * Generate canonicalical coprime move vectors for board size n.
 * Returns all (r, s) with 0 ≤ r ≤ s < n, gcd(r,s) == 1.
 * expandPatterns handles full ±/transposition symmetry.
 * Board sizes above ~20 will produce many vectors; typical game boards are 5–16.
 */
function coprimePairs(n: number): MoveVector[] {
  const vectors: MoveVector[] = [];
  for (let r = 0; r < n; r++) {
    for (let s = r; s < n; s++) {
      if (!(r === 0 && s === 0) && gcd(r, s) === 1) {
        vectors.push([r, s]);
      }
    }
  }
  return vectors;
}

// canon
const KNIGHT: MoveVector[] = [[1, 2]];
const KING_PATTERN: MoveVector[] = [[0, 1], [1, 1]]; // All adjacent
const ROOK_DIRS: MoveVector[] = [[1, 0], [-1, 0], [0, 1], [0, -1]];
const BISHOP_DIRS: MoveVector[] = [[1, 1], [1, -1], [-1, 1], [-1, -1]];
const QUEEN_DIRS: MoveVector[] = [...ROOK_DIRS, ...BISHOP_DIRS];

// atomic
const WAZIR: MoveVector[] = [[0, 1]];
const FERZ: MoveVector[] = [[1, 1]];
const DABBABA: MoveVector[] = [[0, 2]];
const ALFIL: MoveVector[] = [[2, 2]];
const THREELEAPER: MoveVector[] = [[0, 3]];
const TRIPPER: MoveVector[] = [[3, 3]];

// leaper
const CAMEL: MoveVector[] = [[1, 3]];
const ZEBRA: MoveVector[] = [[2, 3]];
const GIRAFFE: MoveVector[] = [[1, 4]];
const IBIS: MoveVector[] = [[1, 5]];
const ANTELOPE: MoveVector[] = [[3, 4]];
const GAZELLE: MoveVector[] = [[2, 5]];

// crowned
const CENTAUR_PATTERN: MoveVector[] = [[0, 1], [1, 1], [1,2]];

// mounted
const PRINCE: MoveVector[] = [[0, 1], [1, 2]];
const SQUIRE: MoveVector[] = [[1, 1], [1, 2]];
const LANCER: MoveVector[] = [[0, 2], [1, 2]];
const COURIER: MoveVector[] = [[1, 2], [2, 2]];
const STRIKER: MoveVector[] = [[1, 2], [0, 3]];
const HARRIER: MoveVector[] = [[1, 2], [3, 3]];

// bounder
const GNU: MoveVector[] = [[1, 2], [1, 3]];
const UNICORN: MoveVector[] = [[1, 2], [2, 3]];
const AUROCHS: MoveVector[] = [[1, 2], [1, 4]];
const OSTRICH: MoveVector[] = [[1, 2], [1, 5]];
const IMPALA: MoveVector[] = [[1, 2], [3, 4]];
const WAPITI: MoveVector[] = [[1, 2], [2, 5]];

// fusion
const WAZAMEL: MoveVector[] = [[0, 1], [1, 3]];
const WAZEBRA: MoveVector[] = [[0, 1], [2, 3]];
const FERZEBRA: MoveVector[] = [[1, 1], [2, 3]];
const ZEBBABA: MoveVector[] = [[0, 2], [2, 3]];

// strider
const BISON: MoveVector[] = [[1, 3], [2, 3]];
const ZEBU: MoveVector[] = [[1, 3], [1, 4]];
const VICUNA: MoveVector[] = [[1, 3], [2, 5]];
const OKAPI: MoveVector[] = [[2, 3], [1, 4]];
const KUDU: MoveVector[] = [[2, 3], [1, 5]];
const NYALA: MoveVector[] = [[2, 3], [3, 4]];


// amphibian
const FROG: MoveVector[] = [[1, 1], [0, 3]];
const EFT: MoveVector[] = [[1, 1], [0, 5]];
const TOAD: MoveVector[] = [[0, 2], [0, 3]];
const TADPOLE: MoveVector[] = [[0, 3], [1, 3]];

// special
const PYTHAGORAS: MoveVector[] = [[0, 5], [3, 4]];
const FIBONACCI: MoveVector[] = [[0, 1], [1, 1], [1, 2], [2, 3], [3, 5], [5, 8], [8,13]];
const PTERODACTYL: MoveVector[] = [[3, 3], [5, 5], [0, 15]];


export const PIECES: Record<string, PieceDefinition> = {
  // canon
  knight:    { name: 'knight', vectors: KNIGHT, icon: '/pieces/knight.svg', group: 'canon' },
  king:      { name: 'king', vectors: KING_PATTERN, icon: '/pieces/king.svg', group: 'canon' },
  queen:     { name: 'queen', sliderDirs: QUEEN_DIRS, icon: '/pieces/queen.svg', group: 'canon' },
  rook:      { name: 'rook', sliderDirs: ROOK_DIRS, icon: '/pieces/rook.svg', group: 'canon' },
  bishop:    { name: 'bishop', sliderDirs: BISHOP_DIRS, colorBound: true, icon: '/pieces/bishop.svg', group: 'canon' },

  // atomic
  wazir:        { name: 'wazir', vectors: WAZIR, icon: '/pieces/wazir.svg', group: 'atomic' },
  dabbaba:      { name: 'dabbaba', vectors: DABBABA, colorBound: true, icon: '/pieces/dabbaba.svg', group: 'atomic' },
  threeleaper:  { name: 'threeleaper', vectors: THREELEAPER, icon: '/pieces/threeleaper.svg', group: 'atomic' },
  ferz:         { name: 'ferz', vectors: FERZ, colorBound: true, icon: '/pieces/ferz.svg', group: 'atomic' },
  alfil:        { name: 'alfil', vectors: ALFIL, colorBound: true, icon: '/pieces/alfil.svg', group: 'atomic' },
  tripper:      { name: 'tripper', vectors: TRIPPER, colorBound: true, icon: '/pieces/tripper.svg', group: 'atomic' },

  // leaper
  camel:        { name: 'camel', vectors: CAMEL, colorBound: true, icon: '/pieces/camel.svg', group: 'leaper' },
  zebra:        { name: 'zebra', vectors: ZEBRA, icon: '/pieces/zebra.svg', group: 'leaper' },
  giraffe:      { name: 'giraffe', vectors: GIRAFFE, icon: '/pieces/giraffe.svg', group: 'leaper' },
  ibis:         { name: 'ibis', vectors: IBIS, colorBound: true, icon: '/pieces/ibis.svg', group: 'leaper' },
  antelope:     { name: 'antelope', vectors: ANTELOPE, icon: '/pieces/antelope.svg', group: 'leaper' },
  gazelle:      { name: 'gazelle', vectors: GAZELLE, icon: '/pieces/gazelle.svg', group: 'leaper' },

  // crowned
  amazon:    { name: 'amazon', sliderDirs: QUEEN_DIRS, vectors: KNIGHT, icon: '/pieces/amazon.svg', group: 'crowned' },
  empress:   { name: 'empress', sliderDirs: ROOK_DIRS, vectors: KNIGHT, icon: '/pieces/empress.svg', group: 'crowned' },
  princess:  { name: 'princess', sliderDirs: BISHOP_DIRS, vectors: KNIGHT, icon: '/pieces/princess.svg', group: 'crowned' },
  centaur:  { name: 'centaur', vectors: CENTAUR_PATTERN, icon: '/pieces/centaur.svg', group: 'crowned' },
  zebrook:  { name: 'zebrook', sliderDirs: ROOK_DIRS, vectors: ZEBRA, icon: '/pieces/zebrook.svg', group: 'crowned' },
  zebbish:   { name: 'zebbish', sliderDirs: BISHOP_DIRS, vectors: ZEBRA, icon: '/pieces/zebbish.svg', group: 'crowned' },

  // mounted
  prince:       { name: 'prince', vectors: PRINCE, icon: '/pieces/prince.svg', group: 'mounted' },
  squire:       { name: 'squire', vectors: SQUIRE, icon: '/pieces/squire.svg', group: 'mounted' },
  lancer:       { name: 'lancer', vectors: LANCER, icon: '/pieces/lancer.svg', group: 'mounted' },
  courier:      { name: 'courier', vectors: COURIER, icon: '/pieces/courier.svg', group: 'mounted' },
  striker:      { name: 'striker', vectors: STRIKER, icon: '/pieces/striker.svg', group: 'mounted' },
  harrier:      { name: 'harrier', vectors: HARRIER, icon: '/pieces/harrier.svg', group: 'mounted' },

  // bounder
  gnu:          { name: 'gnu', vectors: GNU, icon: '/pieces/gnu.svg', group: 'bounder' },
  unicorn:      { name: 'unicorn', vectors: UNICORN, icon: '/pieces/unicorn.svg', group: 'bounder' },
  aurochs:      { name: 'aurochs', vectors: AUROCHS, icon: '/pieces/aurochs.svg', group: 'bounder' },
  ostrich:      { name: 'ostrich', vectors: OSTRICH, icon: '/pieces/ostrich.svg', group: 'bounder' },
  impala:       { name: 'impala', vectors: IMPALA, icon: '/pieces/impala.svg', group: 'bounder' },
  wapiti:       { name: 'wapiti', vectors: WAPITI, icon: '/pieces/wapiti.svg', group: 'bounder' },

  // fusion
  wazamel:  { name: 'wazamel', vectors: WAZAMEL, icon: '/pieces/wazamel.svg', group: 'fusion' },
  wazebra:  { name: 'wazebra', vectors: WAZEBRA, icon: '/pieces/wazebra.svg', group: 'fusion' },
  ferzebra: { name: 'ferzebra', vectors: FERZEBRA, icon: '/pieces/ferzebra.svg', group: 'fusion' },
  zebbaba:  { name: 'zebbaba', vectors: ZEBBABA, icon: '/pieces/zebbaba.svg', group: 'fusion' },

  // strider
  bison:        { name: 'bison', vectors: BISON, icon: '/pieces/bison.svg', group: 'strider' },
  zebu:         { name: 'zebu', vectors: ZEBU, icon: '/pieces/zebu.svg', group: 'strider' },
  vicuna:       { name: 'vicuna', vectors: VICUNA, icon: '/pieces/vicuna.svg', group: 'strider' },
  okapi:        { name: 'okapi', vectors: OKAPI, icon: '/pieces/okapi.svg', group: 'strider' },
  kudu:         { name: 'kudu', vectors: KUDU, icon: '/pieces/kudu.svg', group: 'strider' },
  nyala:        { name: 'nyala', vectors: NYALA, icon: '/pieces/nyala.svg', group: 'strider' },

  // amphibian
  frog:         { name: 'frog', vectors: FROG, icon: '/pieces/frog.svg', group: 'amphibian' },
  eft:          { name: 'eft', vectors: EFT, icon: '/pieces/eft.svg', group: 'amphibian' },
  toad:         { name: 'toad', vectors: TOAD, icon: '/pieces/toad.svg', group: 'amphibian' },
  tadpole:      { name: 'tadpole', vectors: TADPOLE, icon: '/pieces/tadpole.svg', group: 'amphibian' },

  // special
  Pythagoras:   { name: 'Pythagoras', vectors: PYTHAGORAS, icon: '/pieces/pythagoras.svg', group: 'special' },
  Fibonacci:    { name: 'Fibonacci', vectors: FIBONACCI, icon: '/pieces/fibonacci.svg', group: 'special' },
  pterodactyl:  { name: 'pterodactyl', vectors: PTERODACTYL, icon: '/pieces/pterodactyl.svg', group: 'special' },
  gunkan:       { name: 'gunkan', vectorsFn: coprimePairs, icon: '/pieces/gunkan.svg', group: 'special' },
};

// ─── Piece Groups ─────────────────────────────────────────────────────────────

export const PIECE_GROUPS: Record<PieceGroup, string[]> = {
  canon:        ['knight', 'king', 'queen', 'rook', 'bishop'],
  atomic:       ['wazir', 'ferz', 'dabbaba', 'alfil', 'threeleaper', 'tripper'],
  leaper:       ['camel', 'zebra', 'giraffe', 'ibis', 'antelope', 'gazelle'],
  crowned:      ['amazon', 'empress', 'princess', 'centaur', 'zebrook', 'zebbish'],
  mounted:      ['prince', 'squire', 'lancer', 'courier', 'striker', 'harrier'],
  bounder:      ['gnu', 'unicorn', 'aurochs', 'ostrich', 'impala', 'wapiti'],
  fusion:       ['wazamel', 'wazebra', 'ferzebra', 'zebbaba'],
  strider:      ['bison', 'zebu', 'vicuna', 'okapi', 'kudu', 'nyala'],
  amphibian:    ['frog', 'eft', 'toad', 'tadpole'],
  special:      ['Pythagoras', 'Fibonacci', 'pterodactyl', 'gunkan'],
};

// ─── Move Generation ─────────────────────────────────────────────────────────

/**
 * Expand pattern vectors into all symmetric move deltas.
 * For (a, b): generates ±a,±b and ±b,±a (8 variants unless a==b or a/b==0)
 */
export function expandPatterns(patterns: MoveVector[]): Position[] {
  const deltas: Set<string> = new Set();
  const result: Position[] = [];

  for (const [a, b] of patterns) {
    const candidates: [number, number][] = [];
    for (const sx of [1, -1]) {
      for (const sy of [1, -1]) {
        candidates.push([sx * a, sy * b]);
        if (a !== b) {
          candidates.push([sx * b, sy * a]);
        }
      }
    }
    for (const [dr, dc] of candidates) {
      const key = `${dr},${dc}`;
      if (!deltas.has(key) && (dr !== 0 || dc !== 0)) {
        deltas.add(key);
        result.push({ row: dr, col: dc });
      }
    }
  }

  return result;
}

/**
 * Generate all legal moves for a leaper piece from a position.
 */
export function getLeaperMoves(
  pos: Position,
  patterns: MoveVector[],
  rows: number,
  cols: number,
  visited: Set<string>,
  forbidden?: Set<string>,
): Position[] {
  const deltas = expandPatterns(patterns);
  const moves: Position[] = [];

  for (const delta of deltas) {
    const target: Position = { row: pos.row + delta.row, col: pos.col + delta.col };
    if (target.row >= 0 && target.row < rows &&
        target.col >= 0 && target.col < cols &&
        !visited.has(`${target.row},${target.col}`) &&
        !(forbidden?.has(`${target.row},${target.col}`))) {
      moves.push(target);
    }
  }

  return moves;
}

/**
 * Generate all legal moves for a slider piece from a position.
 */
export function getSliderMoves(
  pos: Position,
  directions: MoveVector[],
  rows: number,
  cols: number,
  visited: Set<string>,
  forbidden?: Set<string>,
): Position[] {
  const moves: Position[] = [];

  for (const [dr, dc] of directions) {
    let r = pos.row + dr;
    let c = pos.col + dc;
    while (r >= 0 && r < rows && c >= 0 && c < cols) {
      const key = `${r},${c}`;
      if (!visited.has(key) && !(forbidden?.has(key))) {
        moves.push({ row: r, col: c });
      }
      r += dr;
      c += dc;
    }
  }

  return moves;
}

/**
 * Get all legal moves for a named piece from a position.
 */
export function getLegalMoves(
  pieceName: string,
  pos: Position,
  rows: number,
  cols: number,
  visited: Set<string>,
  forbidden?: Set<string>,
  stepSizeN?: number,
): Position[] {
  const piece = PIECES[pieceName];
  if (!piece) return [];

  // Board-state-aware move generator takes precedence
  if (piece.movesFn) {
    return piece.movesFn(pos, rows, cols, visited, forbidden, stepSizeN);
  }

  let moves: Position[] = [];

  if (piece.vectorsFn) {
    const n = Math.min(rows, cols);
    moves.push(...getLeaperMoves(pos, piece.vectorsFn(n), rows, cols, visited, forbidden));
  } else if (piece.vectors) {
    moves.push(...getLeaperMoves(pos, piece.vectors, rows, cols, visited, forbidden));
  }

  // Slider moves (rook, bishop, queen)
  if (piece.sliderDirs) {
    moves.push(...getSliderMoves(pos, piece.sliderDirs, rows, cols, visited, forbidden));
  }

  return moves;
}

/**
 * Get pieces valid for Hamiltonian tour (non-color-bound).
 */
export function getValidTourPieces(): string[] {
  return Object.keys(PIECES).filter(name => !PIECES[name].colorBound);
}

/**
 * Get all piece names in group order (canonical → atomic → leaper → synaptic → bounder →
 * homage → fusion).
 * Use as the `options` array for piece menu items together with
 * `excludedPieces` to hide the pieces that don't apply to a particular game.
 */
export function getAllPieces(): string[] {
  return Object.values(PIECE_GROUPS).flat();
}

/**
 * Human-readable move set for a named piece: one canonical entry per move
 * family. Slider directions are shown as "(0,n)" (orthogonal) / "(n,n)"
 * (diagonal); leaper vectors as "(a,b)" with 0 ≤ a ≤ b. Pieces with a
 * board-state-aware generator (movesFn) or unknown pieces return [].
 */
export function getPieceMoveSet(pieceName: string, boardSize: number): string[] {
  const piece = PIECES[pieceName];
  if (!piece) return [];

  const entries: string[] = [];
  const add = (label: string) => {
    if (!entries.includes(label)) entries.push(label);
  };

  for (const [dr, dc] of piece.sliderDirs ?? []) {
    add(dr !== 0 && dc !== 0 ? '(n,n)' : '(0,n)');
  }

  const vectors = piece.vectorsFn ? piece.vectorsFn(boardSize) : (piece.vectors ?? []);
  for (const [r, s] of vectors) {
    const a = Math.min(Math.abs(r), Math.abs(s));
    const b = Math.max(Math.abs(r), Math.abs(s));
    add(`(${a},${b})`);
  }

  return entries;
}

/**
 * Position to string key helper.
 */
export function posKey(pos: Position): string {
  return `${pos.row},${pos.col}`;
}
