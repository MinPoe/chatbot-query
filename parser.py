def main(current_query: str, previous_query: str) -> dict: 

    import re 

    current_query_cleaned = current_query.lower().strip()
    previous_query_cleaned = previous_query.lower().strip() 

    followup_patterns = {
        # pattern_type : pattern
        # "what about X??" --> X grouped and extracted
        'what_about': r'^what about\s+(.+?)\?*$',
        'how_about': r'^how about\s(.+?)\?*$',
        'and': r'^and\s(.+?)\?*$',
        'what_if': r'^what if\s(.+?)\?*$',

        # "for X?" "in X?" "with X?"
        'preposition': r'^(for|in|with|on|at|from|to)\s+(.+?)\?*$',
        
        # "X instead?" "X though?"
        'alternative': r'^(.+?)\s+(instead|though|however)\?*$',

        # single entities, 1-2 word follow-up questions like "Japan? "
        'single_entity': r'^([a-z0-9\s\-_]+)\?*$'
    }

    extracted_query = None
    pattern_type = None

    # classify the current_query's followup pattern type, then extract the core of the question
    # if it's not a followup question, exit 
    for p_type, pattern in followup_patterns.items():
        match = re.match(pattern, current_query_cleaned) 

        if match: 
            # start with the most verbose branch
            if p_type == 'single_entity': 
                candidate = match.group(1).strip()

                question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'is', 'are', 'do', 'does', 'can', 'will']
                
                if len(candidate.split()) <= 3 and not any(word in candidate for word in question_words): 
                    extracted_query = candidate 
                    pattern_type = p_type
                
            elif p_type == 'preposition':
                extracted_query = match.group(2).strip()
                pattern_type = p_type
            
            elif p_type == 'alternative':
                extracted_query = match.group(1).strip()
                pattern_type = p_type
            
            else:
                extracted_query = match.group(1).strip()
                pattern_type = p_type
            
            break

    if not extracted_query: 
        return {
            "fused_query": current_query
        }
    
    # detecting previous question pattern, preparing to replace core of old question with core of new question in {entity}
    question_patterns = [
        # What _?
        (r'^(what\s+(?:is|are|was|were|will|would|can|could|should|do|does|did))\s+(.+?)(\s+(?:for|in|with|of|about|from|to)\s+.+?)?(\??)$', 
         r'\1 \2 for {entity}\4'),
        
        # How _?  
        (r'^(how\s+(?:do|does|did|can|could|should|would|will|to|is|are|was|were))\s+(.+?)(\s+(?:for|in|with|of|about|from|to)\s+.+?)?(\??)$',
         r'\1 \2 for {entity}\4'),
        
        # Why _?
        (r'^(why\s+(?:is|are|was|were|do|does|did|can|could|should|would|will))\s+(.+?)(\s+(?:for|in|with|of|about|from|to)\s+.+?)?(\??)$',
         r'\1 \2 for {entity}\4'),
        
        # When _?
        (r'^(when\s+(?:is|are|was|were|do|does|did|can|could|should|would|will))\s+(.+?)(\s+(?:for|in|with|of|about|from|to)\s+.+?)?(\??)$',
         r'\1 \2 for {entity}\4'),
        
        # Where _?
        (r'^(where\s+(?:is|are|was|were|do|does|did|can|could|should|would|will))\s+(.+?)(\s+(?:for|in|with|of|about|from|to)\s+.+?)?(\??)$',
         r'\1 \2 for {entity}\4'),
        
        # Who _?
        (r'^(who\s+(?:is|are|was|were|do|does|did|can|could|should|would|will))\s+(.+?)(\s+(?:for|in|with|of|about|from|to)\s+.+?)?(\??)$',
         r'\1 \2 for {entity}\4'),
        
        # Which _?
        (r'^(which\s+.+?\s+(?:is|are|was|were|do|does|did|can|could|should|would|will))\s+(.+?)(\s+(?:for|in|with|of|about|from|to)\s+.+?)?(\??)$',
         r'\1 \2 for {entity}\4'),
        
        # Show/Tell me _?
        (r'^(show\s+me|tell\s+me|give\s+me)\s+(.+?)(\s+(?:for|in|with|of|about|from|to)\s+.+?)?(\??)$',
         r'\1 \2 for {entity}\4'),
        
        # Can/Could _?
        (r'^(can|could|would|should|will)\s+(.+?)(\s+(?:for|in|with|of|about|from|to)\s+.+?)?(\??)$',
         r'\1 \2 for {entity}\4'),
        
        # Simple verb questions (is, are, do, does, etc.)
        (r'^(is|are|was|were|do|does|did)\s+(.+?)(\s+(?:for|in|with|of|about|from|to)\s+.+?)?(\??)$',
         r'\1 \2 for {entity}\4'),
    ]
    
    fused_query = None
    
    # get corresponding pattern and template by matching with old query, then replace 
    for pattern, template in question_patterns:
        match = re.match(pattern, previous_query_cleaned)
        if match:
            # replace 
            fused_query = re.sub(pattern, template, previous_query_cleaned)
            fused_query = fused_query.replace('{entity}', extracted_query)

    # previous_query doesn't match any standard question pattern
    if not fused_query:
        # find the last significant entity in previous_query and replace it ("Accommodation limit for Japan" + "Indonesia?" --> "Accommodation limit for Indonesia?")
        patterns = [
            r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b(?=\s*\??$)',  # proper nouns at end
            r'\b(\w+)\s*\??$',  # last word
        ]
        
        for pattern in patterns:
            match = re.search(pattern, previous_query_cleaned)
            if match:
                old_entity = match.group(1)
                fused_query = previous_query_cleaned.replace(old_entity, extracted_query, 1)
                break
    
    # final try for not fused_query
    if not fused_query:
        # "Best place to stay?" + "Japan?" = "Best place to stay for Japan?"
        if '?' in previous_query_cleaned:
            fused_query = previous_query_cleaned.replace('?', f' for {extracted_query}?')
        else:
            fused_query = f"{previous_query_cleaned} for {extracted_query}"
    
    # clean up result
    if fused_query:

        # fix capitalization
        fused_query = fused_query[0].upper() + fused_query[1:] if fused_query else fused_query
        
        # remove extra spaces
        fused_query = re.sub(r'\s+', ' ', fused_query).strip()
        
        # question mark check 
        if previous_query_cleaned.endswith('?') and not fused_query.endswith('?'):
            fused_query += '?'
    
    return {
        "fused_query": fused_query or current_query_cleaned
    }