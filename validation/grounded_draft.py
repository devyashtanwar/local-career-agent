"""Restricted rendering from operator-approved statements, not semantic verification.
The model selects IDs only. Free-form prose must remain an unvalidated draft.
"""
def render(facts, selection):
    if type(facts) is not dict or not facts or len(facts) > 100:
        raise ValueError('facts must be a nonempty approved statement mapping')
    for key, text in facts.items():
        if type(key) is not str or not key or len(key) > 100:
            raise ValueError('invalid fact ID')
        if type(text) is not str or not text.strip() or len(text) > 5000:
            raise ValueError('invalid approved statement')
    if type(selection) is not list or not selection or len(selection) > len(facts):
        raise ValueError('select approved IDs only')
    if any(type(key) is not str or key not in facts for key in selection):
        raise ValueError('unsupported claim or unknown fact ID')
    if len(set(selection)) != len(selection):
        raise ValueError('duplicate statement')
    text = '\n\n'.join(facts[key] for key in selection)
    if len(text.split()) > 120:
        raise ValueError('draft exceeds 120 words')
    return text
