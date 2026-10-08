"""Kod klonu tespiti: normalleştirilmiş anlamlı satırların kayan pencere özetleriyle eşlenmesi (dil bağımsız).

Tip-1 klonlar: yorumlar ve boşluk farkları yok sayılır; string ve sayı değerleri DAHİL birebir aynı olmalıdır
(yalnızca metni farklı `lines.append("...")` dizileri veya veri tabloları klon sayılmaz). Yalnızca noktalama olan
satırlar ve import benzeri satırlar atılır.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

_SPACES = re.compile(r'\s+')
_TRIVIAL = re.compile(r'^[\s{}()\[\];,:]*$')
_IMPORT_LIKE = re.compile(r'^(?:import\b|from\b.+\bimport\b|#\s*include\b|using\b|package\b|use\b|extern crate\b|export\s+\*)')
MIN_WINDOW_CHARS = 100          # çok kısa satırlardan oluşan pencereler (ör. tekrarlayan `x = 0`) klon sayılmaz
MAX_OCCURRENCES = 100           # tek özetin tutulan en fazla konumu (kopyası çok olan standart metinler için)
MAX_PARTNERS = 50
POSITION_BITS = 24
POSITION_MASK = (1 << POSITION_BITS) - 1


@dataclass(frozen=True)
class CloneLocation:
    key: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class CloneGroup:
    lines: int                      # ilk konumun anlamlı satır sayısı (diğer konumlar pencere kadar veya daha uzun eşleşir)
    locations: Tuple[CloneLocation, ...]

    @property
    def copies(self) -> int:
        return len(self.locations)

    @property
    def duplicated_lines(self) -> int:
        return self.lines * (self.copies - 1)


def normalize(text: str) -> Tuple[List[str], List[int]]:
    """(anlamlı satırlar, her birinin 1 tabanlı özgün satır numarası)."""
    lines: List[str] = []
    numbers: List[int] = []
    for number, raw in enumerate(text.split('\n'), start=1):
        line = _SPACES.sub(' ', raw).strip()
        if len(line) < 2 or _TRIVIAL.match(line) or _IMPORT_LIKE.match(line):
            continue
        lines.append(line)
        numbers.append(number)
    return lines, numbers


class CloneFinder:
    def __init__(self, window: int = 8):
        self.window = window
        self._intern: Dict[str, int] = {}
        self._lengths: List[int] = []                   # kimlik -> satır uzunluğu
        self._keys: List[str] = []
        self._ids: List[List[int]] = []
        self._numbers: List[List[int]] = []
        self._signatures: Dict[int, int] = {}              # dosya özeti -> dosya sırası
        self.identical_files: List[Tuple[str, str]] = []   # (kopya, ilk dosya): tüm dosya aynı; klon sayılmaz
        self.total_lines = 0

    # ---- giriş --------------------------------------------------------------------------------------

    def add_file(self, key: str, lines: List[str], numbers: List[int]):
        if len(lines) < self.window:
            return
        ids = []
        for line in lines:
            identifier = self._intern.get(line)
            if identifier is None:
                identifier = self._intern[line] = len(self._lengths)
                self._lengths.append(len(line))
            ids.append(identifier)
        signature = hash(tuple(ids))
        original = self._signatures.get(signature)
        if original is not None and self._ids[original] == ids:
            self.identical_files.append((key, self._keys[original]))
            return
        self._signatures[signature] = len(self._keys)
        self._keys.append(key)
        self._ids.append(ids)
        self._numbers.append(numbers)
        self.total_lines += len(ids)

    # ---- tespit ---------------------------------------------------------------------------------------

    def _window_hashes(self, ids: List[int]) -> List[Optional[int]]:
        k = self.window
        lengths = self._lengths
        hashes: List[Optional[int]] = []
        for start in range(len(ids) - k + 1):
            chunk = ids[start:start + k]
            hashes.append(hash(tuple(chunk)) if sum(lengths[i] for i in chunk) >= MIN_WINDOW_CHARS else None)
        return hashes

    def find(self) -> List[CloneGroup]:
        all_hashes = [self._window_hashes(ids) for ids in self._ids]
        occurrences = self._collect_occurrences(all_hashes)
        consumed = set()
        groups: List[CloneGroup] = []
        for file_index, hashes in enumerate(all_hashes):
            for start, digest in enumerate(hashes):
                packed = (file_index << POSITION_BITS) | start
                if digest is None or packed in consumed or digest not in occurrences:
                    continue
                group = self._grow(file_index, start, all_hashes, occurrences, consumed)
                if group is not None:
                    groups.append(group)
        groups.sort(key=lambda g: (-g.duplicated_lines, -g.lines, g.locations[0].key, g.locations[0].start_line))
        return groups

    def _collect_occurrences(self, all_hashes: List[List[Optional[int]]]) -> Dict[int, List[int]]:
        first: Dict[int, int] = {}
        repeated: Dict[int, List[int]] = {}
        for file_index, hashes in enumerate(all_hashes):
            for start, digest in enumerate(hashes):
                if digest is None:
                    continue
                packed = (file_index << POSITION_BITS) | start
                seen = first.get(digest)
                if seen is None:
                    first[digest] = packed
                elif digest in repeated:
                    if len(repeated[digest]) < MAX_OCCURRENCES:
                        repeated[digest].append(packed)
                else:
                    repeated[digest] = [seen, packed]
        return repeated

    def _grow(self, file_index: int, start: int, all_hashes, occurrences, consumed) -> Optional[CloneGroup]:
        """`start` penceresinden başlayan ortak bloğu uzatır, ortakları doğrular ve tükettiği pencereleri işaretler."""
        partners = self._first_partners(file_index, start, all_hashes, occurrences)
        if not partners:
            return None
        end = self._extend(file_index, start, partners, all_hashes, occurrences)
        kept = self._verified(file_index, start, end - start + self.window, partners)
        if not kept:
            return None
        lines = max(length for _, _, length in kept)
        locations = [self._location(file_index, start, lines)]
        for other, other_start, length in sorted(kept):
            locations.append(self._location(other, other_start, length))
            consumed.update((other << POSITION_BITS) | (other_start + t) for t in range(length - self.window + 1))
        consumed.update((file_index << POSITION_BITS) | (start + t) for t in range(lines - self.window + 1))
        return CloneGroup(lines, tuple(locations))

    def _first_partners(self, file_index: int, start: int, all_hashes, occurrences) -> List[int]:
        """Aynı özetli diğer konumlar (kendisi ve aynı dosyada örtüşenler hariç)."""
        own = (file_index << POSITION_BITS) | start
        digest = all_hashes[file_index][start]
        partners = [p for p in occurrences[digest]
                    if p != own and not (p >> POSITION_BITS == file_index and (p & POSITION_MASK) < start + self.window)]
        return partners[:MAX_PARTNERS]

    @staticmethod
    def _extend(file_index: int, start: int, partners: List[int], all_hashes, occurrences) -> int:
        """Ortaklardan en az biri eşleşmeyi sürdürdüğü sürece pencere pencere ilerler; son pencere indeksini döner."""
        alive = partners
        end = start
        while end + 1 < len(all_hashes[file_index]):
            digest = all_hashes[file_index][end + 1]
            if digest is None or digest not in occurrences:
                break
            candidates = set(occurrences[digest])
            alive = [p + 1 for p in alive
                     if (p + 1) in candidates and (p & POSITION_MASK) + 1 < len(all_hashes[p >> POSITION_BITS])]
            if not alive:
                break
            end += 1
        return end

    def _verified(self, file_index: int, start: int, span: int, partners: List[int]) -> List[Tuple[int, int, int]]:
        """Özet çakışmalarını satır satır doğrular: (dosya, başlangıç, gerçek ortak uzunluk), uzunluk >= pencere."""
        own_ids = self._ids[file_index]
        kept: List[Tuple[int, int, int]] = []
        for partner in partners:
            other = partner >> POSITION_BITS
            other_start = partner & POSITION_MASK
            limit = other_start - start if other == file_index else span      # aynı dosyada bloklar örtüşemez
            length = self._common_length(own_ids, start, self._ids[other], other_start, min(span, limit))
            if length >= self.window:
                kept.append((other, other_start, length))
        return kept

    @staticmethod
    def _common_length(ids_a: List[int], start_a: int, ids_b: List[int], start_b: int, limit: int) -> int:
        length = 0
        while length < limit and start_a + length < len(ids_a) and start_b + length < len(ids_b) \
                and ids_a[start_a + length] == ids_b[start_b + length]:
            length += 1
        return length

    def _location(self, file_index: int, start: int, length: int) -> CloneLocation:
        numbers = self._numbers[file_index]
        return CloneLocation(self._keys[file_index], numbers[start], numbers[start + length - 1])
