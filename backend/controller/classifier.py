import re


def classify_query(text: str) -> str:
    text = text.lower()
    
    # Formatting/Transformation signals
    transform_verbs = {"summarize", "shorten", "rephrase", "translate", "bullets", "table"}
    anaphora = {"that", "it", "those", "this"}
    
    has_transform_verb = any(verb in text for verb in transform_verbs)
    has_anaphora = any(re.search(rf"\b{word}\b", text) for word in anaphora)
    
    if has_transform_verb and has_anaphora:
        return "transformation"
        
    if "actually" in text or "instead" in text:
        return "constraint_update"
        
    return "information_seeking"
