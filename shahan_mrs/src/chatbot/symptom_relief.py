"""Curated educational symptom relief, independent of unreliable disease mappings."""
import re


def symptom_relief(symptoms, data, *, blocked=False, text=''):
    """Return supported examples, not a personal medicine choice or dose."""
    if blocked or re.search(r'\b(?:baby|infant|child|toddler|pregnan\w*|severe|unbearable|sudden|blood|overdose)\b', text, re.I):
        return None
    age = re.search(r'\b(\d{1,3})\s*[- ]?\s*(?:years?[- ]?old|year[- ]old|yo)\b', text, re.I)
    if age and int(age.group(1)) < 16:
        return None
    symptoms = set(symptoms)
    allowed = {'headache', 'fatigue', 'high_fever', 'mild_fever', 'muscle_pain',
               'body_ache', 'throat_irritation', 'cough', 'continuous_sneezing',
               'runny_nose', 'congestion', 'redness_of_eyes', 'itching', 'diarrhoea', 'constipation'}
    if not symptoms or symptoms - allowed:
        return None
    names, notes, sources = [], [], []
    medicines = {m['name']: m for m in data.get('health_library', {}).get('medicines', [])}

    def add(name, explanation):
        record = medicines.get(name)
        if not record or not record.get('indications_excerpt') or not record.get('source', {}).get('url'):
            return
        names.append(name)
        notes.append(explanation)
        sources.append(record['source'])

    if symptoms & {'continuous_sneezing', 'runny_nose'}:
        add('cetirizine', '**Cetirizine** is an antihistamine used for allergy-related sneezing and runny nose; this does not establish that your symptoms are an allergy.')
    if symptoms & {'headache', 'high_fever', 'mild_fever', 'muscle_pain', 'body_ache', 'throat_irritation'}:
        add('acetaminophen', '**Paracetamol (acetaminophen)** is used for pain or fever relief. Avoid combining it with other products containing paracetamol.')
    if symptoms == {'constipation'}:
        add('polyethylene glycol 3350', '**Polyethylene glycol 3350 (macrogol)** is a laxative used for occasional constipation; check the exact product leaflet and suitability.')
    if symptoms == {'diarrhoea'}:
        names.append('oral rehydration solution (ORS)')
        notes.append('**Oral rehydration solution (ORS)** replaces fluid and salts lost through diarrhoea. It is supportive treatment rather than a cure for the cause.')
        sources.append({'publisher': 'NHS', 'url': 'https://www.nhs.uk/symptoms/diarrhoea-and-vomiting/'})
    if not names:
        return None
    return {'names': names, 'text': '\n\n'.join(notes) +
            '\n\nThese are educational relief options, not a prescription. Suitability depends on age, allergies, health conditions and other medicines; follow the product leaflet and check with a pharmacist.',
            'source_details': sources, 'sources': list(dict.fromkeys(s['url'] for s in sources))}
