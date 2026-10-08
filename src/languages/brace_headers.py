"""Süslü parantezli dillerde `{` öncesi başlığın sınıflanması: sınıf mı, fonksiyon mu, kontrol bloğu mu, kaç parametre.

`brace.py` yapı taramasında her `{` için bu sınıfı çağırır. Sözcük tabanlıdır, sonuçlar yaklaşıktır.
"""
import re
from typing import Optional, Tuple

# `{` öncesi başlığın kontrol bloğu mu olduğu: 'cog' bilişsel iç içe seviyeyi artırır, 'block' yalnızca derinliği.
_COGNITIVE_CONTROL = re.compile(r'(?:^|[\s;}])(?:else\s+if|else|if|for|foreach|while|switch|catch|do|loop|match|select)\b[^{}]*\Z')
_BLOCK_CONTROL = re.compile(r'(?:^|[\s;}])(?:try|finally|using|lock|synchronized|unsafe|fixed|checked|unchecked)\b[^{}]*\Z')
_SELF_PARAMETER = re.compile(r'^(?:&\s*)?(?:mut\s+)?self\b|^this\s*:|^void$')
_NAME_TAIL = re.compile(
    r'((?:~?[A-Za-z_][\w$]*|operator\s*(?:[^\s\w(]+|\w+))'
    r'(?:\s*::\s*(?:~?[A-Za-z_][\w$]*|operator\s*(?:[^\s\w(]+|\w+)))*)\s*$')
_IDENTIFIER = re.compile(r'[A-Za-z_$][\w$]*')
_NO_PARAMETERS = -1                                    # `_parameters_open`: parantez grubundan önce `{` ya da `;` geldi

Found = Tuple[str, str, int]                           # (tür: 'class' | 'func', ad, başlık içi ofset)


def blank(token: str) -> str:
    """Aynı uzunlukta boşluk; satır sonları korunur (satır numaraları kaymaz)."""
    if '\n' not in token:
        return ' ' * len(token)
    return re.sub(r'[^\n]', ' ', token)


def blank_matches(pattern: 're.Pattern', text: str) -> str:
    return pattern.sub(lambda m: blank(m.group(0)), text)


class HeaderClassifier:
    """Bir dil tanımı (`brace.LanguageSpec`) için başlık sınıflayıcı."""

    def __init__(self, spec):
        self.spec = spec
        self._cleaners = [re.compile(p) for p in spec.header_cleaners]
        self._class_keyword = (re.compile(r'(?<![.\w$])(%s)\b' % '|'.join(spec.class_kinds))
                               if spec.class_kinds else None)

    def clean(self, header: str) -> str:
        cleaned = header
        for cleaner in self._cleaners:
            cleaned = blank_matches(cleaner, cleaned)
        return cleaned

    def classify(self, header: str) -> Optional[Tuple[str, str, int, int]]:
        """`{` öncesi başlığı ('class'|'func', ad, başlık içi ofset, parametre sayısı) olarak sınıflar; yoksa None."""
        cleaned = self.clean(header)
        if not cleaned.strip(' \t\r\n,'):
            return None

        family = self.spec.family
        if family == 'go':
            found = self._go_function(cleaned)
        elif family == 'rust':
            found = self._rust_header(cleaned)
        else:
            found = self._class_header(cleaned) or (
                self._js_function(cleaned) if family == 'js' else self._c_like_function(cleaned))
        if found is None:
            return None
        kind, name, rel = found
        return kind, name, rel, (self.count_params(cleaned, rel) if kind == 'func' else 0)

    def control_kind(self, header: str) -> Optional[str]:
        """Düz bloğun başlığı kontrol yapısı mı: 'cog' (if/else/for/while/switch/catch ...) ya da 'block' (try/using/lock ...)."""
        cleaned = self.clean(header)
        if _COGNITIVE_CONTROL.search(cleaned):
            return 'cog'
        if _BLOCK_CONTROL.search(cleaned):
            return 'block'
        return None

    # ---- parametre sayısı ------------------------------------------------------

    @staticmethod
    def _angle_delta(header: str, index: int, angle: int, name_chars: str = '') -> int:
        """`header[index]` jenerik açan `<` ise +1, kapatan `>` ise -1 (`->` ve `=>` hariç), değilse 0."""
        char = header[index]
        if char == '<' and index > 0 and (header[index - 1].isalnum() or header[index - 1] in name_chars):
            return 1
        if char == '>' and angle and header[index - 1] not in '-=':
            return -1
        return 0

    @classmethod
    def _parameters_open(cls, header: str, start: int) -> Optional[int]:
        """`start` sonrasındaki ilk üst düzey `(` konumu (ad sonrası jenerikler atlanır); `_NO_PARAMETERS` ya da None."""
        angle = 0
        for index in range(start, len(header)):
            delta = cls._angle_delta(header, index, angle, '_$')
            angle += delta
            if delta or angle:
                continue
            if header[index] == '(':
                return index
            if header[index] in '{;':
                return _NO_PARAMETERS
        return None

    @classmethod
    def _split_parameters(cls, header: str, begin: int) -> list:
        """`begin` konumundaki parantez grubunun üst düzey virgüllerle ayrılmış ham parametre metinleri."""
        depth, angle, parts = 1, 0, []
        for position in range(begin, len(header)):
            delta = cls._angle_delta(header, position, angle)
            angle += delta
            if delta:
                continue
            char = header[position]
            if char in '([{':
                depth += 1
            elif char in ')]}':
                depth -= 1
                if depth == 0:
                    parts.append(header[begin:position])
                    break
            elif char == ',' and depth == 1 and angle == 0:
                parts.append(header[begin:position])
                begin = position + 1
        return parts

    @classmethod
    def count_params(cls, header: str, start: int) -> int:
        """`start` sonrasındaki ilk üst düzey parantez grubunun parametre sayısı (self / void / TS this hariç)."""
        opening = cls._parameters_open(header, start)
        if opening is None:
            return 1 if re.search(r'[\w$]\s*=>\s*\Z', header) else 0       # `x => {` tek parametre
        if opening == _NO_PARAMETERS:
            return 0
        parameters = [part.strip() for part in cls._split_parameters(header, opening + 1)]
        return len([part for part in parameters if part and not _SELF_PARAMETER.match(part)])

    # ---- sınıflar (c_like, js) ------------------------------------------------

    def _class_header(self, header: str) -> Optional[Found]:
        if self._class_keyword is None:
            return None
        for match in self._class_keyword.finditer(header):
            before = header[:match.start()].rstrip()
            if before.endswith(('<', ',')) or re.search(r'\benum$', before):
                continue                                   # template<class T>, enum class
            rest = header[match.end():]
            if '=' in header[match.start():] or ';' in rest:
                continue
            if not self.spec.class_header_parens and '(' in rest:
                continue
            name = self._class_name(rest)
            if name:
                return 'class', name, match.start()
        return None

    def _class_name(self, rest: str) -> Optional[str]:
        if self.spec.id in ('c', 'cpp'):
            rest = re.split(r'(?<!:):(?!:)|<', rest, maxsplit=1)[0]
            names = [n for n in _IDENTIFIER.findall(rest) if n not in ('final', 'sealed')]
            return names[-1] if names else None
        match = _IDENTIFIER.match(rest.lstrip())
        return match.group(0) if match else None

    # ---- C ailesi, Java, C# ----------------------------------------------------

    def _c_like_function(self, header: str) -> Optional[Found]:
        paren = header.find('(')
        if paren < 0:
            return None
        name_part = header[:paren].rstrip()
        match = _NAME_TAIL.search(name_part)
        if not match:
            return None
        prefix = name_part[:match.start()]
        name = re.split(r'\s*::\s*', match.group(1))[-1].strip()
        if name in self.spec.keywords or '=' in prefix or prefix.rstrip().endswith(('.', '->')):
            return None
        if self.spec.new_guard and re.search(r'\bnew\b', prefix):
            return None
        return 'func', name, match.start(1)

    # ---- JavaScript / TypeScript ---------------------------------------------------

    _JS_FUNCTION = re.compile(
        r'(?m)^[ \t,]*(?:export\s+)?(?:default\s+)?(?:(?:const|let|var)\s+[\w$]+\s*(?::[^=]+)?=\s*)?'
        r'(?:async\s+)?function\b\s*\*?\s*(?P<name>[\w$]*)\s*(?:<[^>]*>)?\s*\(.*\)\s*(?::[^=]*)?\Z',
        re.S)
    _JS_KEYED_FUNCTION = re.compile(
        r'(?m)^[ \t,]*(?P<name>[\w$]+)\s*:\s*(?:async\s+)?function\b\s*\*?\s*[\w$]*\s*\(.*\)\s*(?::[^=]*)?\Z', re.S)
    _JS_ARROW_NAME = re.compile(
        r'(?m)^[ \t,]*(?:(?:export|default|const|let|var|public|private|protected|static|readonly|async)\s+)*'
        r'(?P<name>[\w$.]+)\s*(?::[^=()]*)?=\s*(?!=)(?:async\b|\(|<|[\w$]+\s*=>)')
    _JS_METHOD = re.compile(
        r'(?m)^[ \t,]*(?:(?:public|private|protected|static|async|get|set|readonly|abstract|override|declare)\s+)*'
        r'\*?\s*(?P<name>[\w$]+|\[[^\]\n]+\])\s*(?:<[^>]*>)?\s*\(.*\)\s*(?::\s*[^={]*)?\Z', re.S)

    def _js_function(self, header: str) -> Optional[Found]:
        stripped = header.rstrip()
        if stripped.endswith('=>'):
            match = self._JS_ARROW_NAME.search(header)
            return 'func', match.group('name') if match else '<anonymous>', match.start('name') if match else 0
        for pattern in (self._JS_FUNCTION, self._JS_KEYED_FUNCTION):
            match = pattern.search(header)
            if match:
                return 'func', match.group('name') or '<anonymous>', match.start()
        match = self._JS_METHOD.search(header)
        if match and match.group('name') not in self.spec.keywords:
            return 'func', match.group('name'), match.start('name')
        return None

    # ---- Go --------------------------------------------------------------------------

    _GO_FUNCTION = re.compile(r'(?m)^[ \t]*func\b\s*(?:\([^)]*\)\s*)?(?P<name>\w+)\s*(?:\[[^\]]*\]\s*)?\(')

    def _go_function(self, header: str) -> Optional[Found]:
        match = self._GO_FUNCTION.search(header)
        return ('func', match.group('name'), match.start('name')) if match else None

    # ---- Rust ----------------------------------------------------------------------------

    _RUST_FN = re.compile(r'(?<![\w])fn\s+(?P<name>[A-Za-z_]\w*)')
    _RUST_IMPL = re.compile(r'^\s*(?:unsafe\s+)?impl\b(?P<rest>.*)\Z', re.S)
    _RUST_TYPE = re.compile(r'^\s*(?:pub(?:\([^)]*\))?\s+)?(?:unsafe\s+)?(?:struct|trait)\s+(?P<name>[A-Za-z_]\w*)')

    def _rust_header(self, header: str) -> Optional[Found]:
        fn = self._RUST_FN.search(header)
        if fn:
            return 'func', fn.group('name'), fn.start('name')
        impl = self._RUST_IMPL.match(header)
        if impl:
            name = self._rust_impl_name(impl.group('rest'))
            return ('class', name, impl.start()) if name else None
        typed = self._RUST_TYPE.match(header)
        return ('class', typed.group('name'), typed.start('name')) if typed else None

    @staticmethod
    def _rust_impl_name(rest: str) -> Optional[str]:
        rest = re.sub(r'\bwhere\b.*', '', rest, flags=re.S)
        previous = None
        while previous != rest:                          # jenerikleri içten dışa sil
            previous, rest = rest, re.sub(r'<[^<>]*>', '', rest)
        rest = re.split(r'\bfor\b', rest)[-1]
        names = re.findall(r'[A-Za-z_]\w*', rest)
        return names[-1] if names else None
