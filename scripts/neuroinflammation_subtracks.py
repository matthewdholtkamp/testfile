import re


NEUROINFLAMMATION_MECHANISM = 'neuroinflammation_microglial_activation'
NEUROINFLAMMATION_SUBTRACK_ORDER = [
    'nlrp3_cytokine_lane',
    'microglial_state_transition_lane',
    'aqp4_glymphatic_astroglial_lane',
]
NEUROINFLAMMATION_SUBTRACK_DISPLAY = {
    'nlrp3_cytokine_lane': 'NLRP3 / Cytokine lane',
    'microglial_state_transition_lane': 'Microglial state-transition lane',
    'aqp4_glymphatic_astroglial_lane': 'AQP4 / Glymphatic / Astroglial lane',
}

SUBTRACK_PATTERNS = {
    'nlrp3_cytokine_lane': [
        (re.compile(r'\bnlrp3\b', re.I), 6),
        (re.compile(r'\binflammasome\b', re.I), 5),
        (re.compile(r'\bcytokine', re.I), 3),
        (re.compile(r'\binterleukin\b', re.I), 3),
        (re.compile(r'\bil-1', re.I), 3),
        (re.compile(r'\bil-6', re.I), 3),
        (re.compile(r'\btnf', re.I), 3),
        (re.compile(r'\bnf-?kb\b', re.I), 3),
        (re.compile(r'\btlr4\b', re.I), 3),
        (re.compile(r'\btlr9\b', re.I), 3),
        (re.compile(r'\brage\b', re.I), 2),
        (re.compile(r'\bdamp', re.I), 2),
        (re.compile(r'\bprr', re.I), 2),
        (re.compile(r'cgas[- ]sting', re.I), 2),
        (re.compile(r'pro-?inflammatory', re.I), 2),
    ],
    'microglial_state_transition_lane': [
        (re.compile(r'\bm1\b', re.I), 4),
        (re.compile(r'\bm2\b', re.I), 4),
        (re.compile(r'm1\s*(to|-|/)\s*m2', re.I), 6),
        (re.compile(r'\bpolariz', re.I), 5),
        (re.compile(r'\bphenotype', re.I), 3),
        (re.compile(r'\bstate transition', re.I), 5),
        (re.compile(r'\bphagocyt', re.I), 4),
        (re.compile(r'\btrem2\b', re.I), 4),
        (re.compile(r'\bgas6\b', re.I), 4),
        (re.compile(r'\bmertk\b', re.I), 4),
        (re.compile(r'\bmicroglial proliferation\b', re.I), 3),
        (re.compile(r'\bmicroglial activ', re.I), 2),
        (re.compile(r'\bhomeostatic\b', re.I), 2),
    ],
    'aqp4_glymphatic_astroglial_lane': [
        (re.compile(r'\baqp-?4\b', re.I), 6),
        (re.compile(r'\baquaporin-?4\b', re.I), 6),
        (re.compile(r'\bglymph', re.I), 5),
        (re.compile(r'\bperivascular\b', re.I), 4),
        (re.compile(r'\bastrogl', re.I), 4),
        (re.compile(r'\bastrocyt', re.I), 3),
        (re.compile(r'\bend-?feet\b', re.I), 4),
        (re.compile(r'\bgfap\b', re.I), 2),
        (re.compile(r'\bs100b\b', re.I), 2),
        (re.compile(r'\brgma\b', re.I), 2),
    ],
}


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def is_neuroinflammation(mechanism):
    return normalize_spaces(mechanism) == NEUROINFLAMMATION_MECHANISM


def neuroinflammation_subtrack_display_name(code):
    return NEUROINFLAMMATION_SUBTRACK_DISPLAY.get(code, '')


def _joined_text(values):
    parts = []
    for value in values:
        if isinstance(value, (list, tuple, set)):
            parts.extend(normalize_spaces(item) for item in value if normalize_spaces(item))
        else:
            text = normalize_spaces(value)
            if text:
                parts.append(text)
    return ' | '.join(parts)


def neuroinflammation_subtrack_scores(*values):
    text = _joined_text(values)
    scores = {}
    for code in NEUROINFLAMMATION_SUBTRACK_ORDER:
        score = 0
        for pattern, weight in SUBTRACK_PATTERNS[code]:
            if pattern.search(text):
                score += weight
        scores[code] = score
    return scores


def infer_neuroinflammation_subtracks(*values):
    scores = neuroinflammation_subtrack_scores(*values)
    ranked = sorted(
        NEUROINFLAMMATION_SUBTRACK_ORDER,
        key=lambda code: (-scores[code], NEUROINFLAMMATION_SUBTRACK_ORDER.index(code)),
    )
    return [code for code in ranked if scores[code] > 0]


def primary_neuroinflammation_subtrack(*values):
    matches = infer_neuroinflammation_subtracks(*values)
    return matches[0] if matches else ''
