"""Pure, deterministic six-human matching; no persistence or oTree imports.

Identities are nonempty strings without whitespace, compared exactly (case is
significant), never coerced/stripped. Input identities are sorted by Python's
Unicode lexicographic order. Matrix members and groups are sorted likewise;
group ordering/positions have no economic meaning. JSON arrays can be restored
through validate_matrix. Keep the returned matrix for later persistence.
"""

from collections import Counter
from collections.abc import Mapping
import hashlib
from itertools import combinations
import json
import random

from lab_rules import BLOCKS_PER_SECTION, GROUP_SIZE, TOTAL_BLOCKS, section_offset


CANDIDATE_COUNT = 100
ALGORITHM_VERSION = 'lab-matching-v1'
Matrix = tuple[tuple[str, ...], ...]


def _identity(value):
    if type(value) is not str or not value or any(char.isspace() for char in value):
        raise ValueError('participant identities must be nonempty strings without whitespace.')


def canonical_participants(participants) -> tuple[str, ...]:
    """Validate exactly 18/24 unique codes and sort independently of input order."""
    if isinstance(participants, (str, bytes, Mapping)):
        raise ValueError('participants must be an iterable of 18 or 24 identities.')
    try:
        people = tuple(participants)
    except TypeError as exc:
        raise ValueError('participants must be an iterable of 18 or 24 identities.') from exc
    if len(people) not in (18, 24):
        raise ValueError('participants must contain exactly 18 or 24 identities.')
    for person in people:
        _identity(person)
    if len(set(people)) != len(people):
        raise ValueError('participants contain duplicate identities.')
    return tuple(sorted(people))


def _rows(matrix) -> Matrix:
    if not isinstance(matrix, (list, tuple)) or not matrix:
        raise ValueError('matrix must be a nonempty list or tuple of groups.')
    rows = []
    for group in matrix:
        if not isinstance(group, (list, tuple)) or len(group) != GROUP_SIZE:
            raise ValueError('each matrix group must contain exactly six identities.')
        for person in group:
            _identity(person)
        rows.append(tuple(group))
    return tuple(rows)


def validate_matrix(matrix, participants) -> Matrix:
    """Validate a complete configured partition and return its canonical copy."""
    people = canonical_participants(participants)
    rows = _rows(matrix)
    if len(rows) != len(people) // GROUP_SIZE:
        raise ValueError('matrix must have exactly three groups for 18 or four for 24.')
    flat = tuple(person for group in rows for person in group)
    if len(set(flat)) != len(flat):
        raise ValueError('matrix contains duplicate participant identities.')
    if set(flat) != set(people):
        raise ValueError('matrix has missing or unknown participant identities.')
    return tuple(sorted(tuple(sorted(group)) for group in rows))


def matrix_pairs(matrix) -> frozenset[tuple[str, str]]:
    """Unordered pairs as sorted two-code tuples, from a valid lab partition."""
    rows = _rows(matrix)
    people = tuple(person for group in rows for person in group)
    canonical = validate_matrix(rows, people)
    return frozenset(pair for group in canonical for pair in combinations(group, 2))


def build_pair_counts(prior_matrices) -> Counter:
    """Count co-memberships in explicitly supplied same-section matrices.

    Use prior_section_matrices first when history is keyed by global block.
    Each matrix must be a valid lab partition of the same participant set.
    """
    counts = Counter()
    people = None
    for matrix in prior_matrices:
        rows = _rows(matrix)
        if people is None:
            people = canonical_participants(person for group in rows for person in group)
        counts.update(matrix_pairs(validate_matrix(rows, people)))
    return counts


def repeated_pair_score(matrix, pair_counts: Mapping) -> int:
    """Sum previous co-membership multiplicities for pairs together now.

    pair_counts is the mapping returned by build_pair_counts (or an equivalent
    mapping of canonical pairs to nonnegative integer counts).
    """
    if not isinstance(pair_counts, Mapping):
        raise ValueError('pair_counts must be a mapping.')
    for pair, count in pair_counts.items():
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise ValueError('pair_counts keys must be canonical pairs.')
        for person in pair:
            _identity(person)
        if pair[0] >= pair[1] or type(count) is not int or count < 0:
            raise ValueError('pair_counts requires sorted distinct pairs and nonnegative integer counts.')
    return sum(pair_counts.get(pair, 0) for pair in matrix_pairs(matrix))


def matching_section(destination_block: int) -> str:
    """Strict global block 1–9 → F, Z, or P(Z); bool/float/string rejected."""
    if type(destination_block) is not int or not 1 <= destination_block <= TOTAL_BLOCKS:
        raise ValueError('destination_block must be an integer from 1 through 9.')
    return ('F', 'Z', 'P(Z)')[(destination_block - 1) // BLOCKS_PER_SECTION]


def prior_section_matrices(participants, destination_block: int, prior_matrices: Mapping) -> tuple:
    """Validate supplied block-keyed history and keep only the current section.

    Keys are strict global-block integers preceding destination_block. Earlier
    sections may be omitted; every preceding block WITHIN the current section
    is required to avoid silently losing pair penalties. All supplied matrices
    are validated, including earlier-section matrices that will not be scored.
    Mapping insertion order is irrelevant. No internal history is read/written.
    """
    people = canonical_participants(participants)
    section = matching_section(destination_block)
    if not isinstance(prior_matrices, Mapping):
        raise ValueError('prior_matrices must map global block integers to matrices.')
    checked = {}
    for block, matrix in prior_matrices.items():
        matching_section(block)
        if block >= destination_block:
            raise ValueError('prior_matrices must contain only preceding blocks.')
        checked[block] = validate_matrix(matrix, people)
    required = range(section_offset(section) + 1, destination_block)
    if any(block not in checked for block in required):
        raise ValueError('prior_matrices is missing a preceding block in the current section.')
    return tuple(checked[block] for block in required)


def derive_rng_seed(matching_seed, destination_block: int) -> int:
    """SHA-256 of versioned compact ASCII JSON [version, typed seed, section, block].

    Integer and string seeds remain distinct, matching Task 1's seed contract.
    No built-in hash(), global RNG, or silent seed generation is used.
    """
    section = matching_section(destination_block)
    if type(matching_seed) is int:
        typed_seed = ['int', matching_seed]
    elif isinstance(matching_seed, str) and matching_seed.strip():
        typed_seed = ['str', matching_seed]
    else:
        raise ValueError('matching_seed must be an explicit integer or nonblank string.')
    payload = json.dumps(
        [ALGORITHM_VERSION, typed_seed, section, destination_block],
        ensure_ascii=True, separators=(',', ':'),
    ).encode('ascii')
    return int.from_bytes(hashlib.sha256(payload).digest(), 'big')


def generate_candidates(participants, matching_seed, destination_block: int) -> tuple[Matrix, ...]:
    """Generate exactly CANDIDATE_COUNT partitions in seeded encounter order."""
    people = canonical_participants(participants)
    rng = random.Random(derive_rng_seed(matching_seed, destination_block))
    candidates = []
    for _ in range(CANDIDATE_COUNT):
        shuffled = list(people)
        rng.shuffle(shuffled)
        groups = [shuffled[start:start + GROUP_SIZE]
                  for start in range(0, len(shuffled), GROUP_SIZE)]
        candidates.append(validate_matrix(groups, people))
    return tuple(candidates)


def select_best_candidate(candidates, pair_counts: Mapping) -> Matrix:
    """Return the first minimum-score valid candidate; positive scores are valid."""
    best, best_score, people = None, None, None
    for candidate in candidates:
        rows = _rows(candidate)
        if people is None:
            people = canonical_participants(person for group in rows for person in group)
        matrix = validate_matrix(rows, people)
        score = repeated_pair_score(matrix, pair_counts)
        if best is None or score < best_score:
            best, best_score = matrix, score
    if best is None:
        raise ValueError('candidates must contain at least one valid partition.')
    return best


def select_matching(participants, matching_seed, destination_block: int, prior_matrices: Mapping) -> Matrix:
    """Select a fresh seeded partition with mild within-section pair minimisation.

    Supply {} at a section start or a mapping of preceding global blocks to
    selected matrices. Output is immutable and JSON serializable; callers own
    persistence. No zero-repeat constraint or guarantee is imposed.
    """
    people = canonical_participants(participants)
    history = prior_section_matrices(people, destination_block, prior_matrices)
    counts = build_pair_counts(history)
    candidates = generate_candidates(people, matching_seed, destination_block)
    return select_best_candidate(candidates, counts)
