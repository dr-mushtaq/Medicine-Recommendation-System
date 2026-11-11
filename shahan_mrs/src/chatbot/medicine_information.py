"""Deterministic medicine references; available even when generation is offline."""
import re

from src.chatbot.response_quality import fallback_reply

MEDICINE_REQUEST = re.compile(
    r'\b(?:medicines?|medications?|tablets?|pills?|painkillers?|antibiotics?)\b', re.I)
DOSE_REQUEST = re.compile(
    r'\b(?:dose|dosage|dosing|milligrams|mg)\b|how (?:many|much|often|frequently).*'
    r'(?:tablet|pill|medicin|take)', re.I)


def is_named_medicine(text, data):
    if re.search(r'\b(?:panadol|paracetamol)\b', text, re.I):
        return True
    return any(re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text, re.I)
               for row in data.get('health_library', {}).get('medicines', [])
               for name in [row['name'], *row.get('brand_names', [])] if len(name) >= 4)


def is_medicine_information_question(text, data):
    if is_named_medicine(text, data):
        return True
    return bool(MEDICINE_REQUEST.search(text) and re.search(
        r'\b(?:what (?:is|are)|tell me about|explain|uses? of|side effects? of|ingredients? of)\b', text, re.I))


def medicine_information(text, state, data, blocked=False):
    """Explain named products or limited symptom relief, never approve suitability."""
    if DOSE_REQUEST.search(text):
        return None  # Existing dose boundary handles this request.
    if re.search(r'\bpanadol\b.*\b(?:day|extra)\b', text, re.I):
        variant = 'Extra' if re.search(r'\bextra\b', text, re.I) else 'Cold & Flu Day'
        extra = variant == 'Extra'
        url = 'https://www.haleonhealthpartner.com/en-pk/pain-relief/brands/panadol/products/' + ('extra/' if extra else 'cf-day/')
        return {'text': ('**Panadol Extra** combines paracetamol and caffeine for pain relief. '
                         'It is a different formulation from Panadol CF.' if extra else
                         '**Panadol Cold & Flu Day** in the Pakistan manufacturer reference contains '
                         'paracetamol and phenylephrine for pain, fever and nasal congestion. '
                         'It differs from regular Panadol CF.') +
                ' Check the ingredients on your pack because formulations vary by country. '
                'Avoid combining products containing paracetamol.',
                'sources': [url], 'source_details': [{'publisher': 'Haleon Pakistan', 'url': url}],
                'predictions': [], 'intent': 'medicine_information', 'medicine_withheld': True}
    if re.search(r'\bpanadol\s*(?:c\s*&?\s*f|cold\s*(?:and|&|\+)?\s*flu)\b', text, re.I):
        url = 'https://www.haleonhealthpartner.com/en-pk/pain-relief/brands/panadol/products/regular/'
        return {
            'text': '**Panadol CF is a combination cold and flu medicine.** The Pakistan product '
                    'listed by the manufacturer contains paracetamol for pain and fever, pseudoephedrine '
                    'for congestion, and chlorpheniramine, an antihistamine. Check your pack: formulations vary.\n\n'
                    'It is intended for multiple cold and flu symptoms. That does not establish whether '
                    'it is suitable for you. What is your age, and do you have any medical conditions, '
                    'pregnancy, allergies, or other medicines? Please share the active ingredients on your pack '
                    'so I can explain that exact version.',
            'predictions': [], 'intent': 'medicine_information', 'medicine_withheld': True,
            'sources': [url], 'source_details': [{'publisher': 'Haleon Pakistan', 'url': url}],
        }
    from src.data.health_library import answer_records
    medicines = data.get('health_library', {}).get('medicines', [])
    records = list(answer_records({'conditions': [], 'medicines': medicines}))
    brands = {m['name']: list(m.get('brand_names', [])) for m in medicines}
    brands.setdefault('acetaminophen', []).append('paracetamol')
    named = []
    for record in records:
        if any(re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text, re.I)
               for name in [record['name'], *brands.get(record['name'], [])] if len(name) >= 4):
            named.append(record)
    if named:
        # Prefer the full combination name over a component appearing inside it.
        named.sort(key=lambda r: len(r['name']), reverse=True)
        result = fallback_reply(named[:1], [], reason='local_reference', retryable=False)
        result['intent'] = 'medicine_information'
        return result
    from src.chatbot.dialogue import extract_symptoms
    positive, negative = extract_symptoms(text, data['symptoms'])
    symptoms = (set(state.get('symptoms', [])) | positive) - negative
    if (MEDICINE_REQUEST.search(text) and not blocked and not state.get('active_health_report')
            and not (positive - set(state.get('symptoms', [])))
            and not any(re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text, re.I)
                        for name in data['by_condition'])):
        from src.chatbot.symptom_relief import symptom_relief
        relief = symptom_relief(symptoms, data, text=text)
        if relief and not {'continuous_sneezing', 'runny_nose'} <= symptoms:
            return {'text': relief['text'], 'predictions': [], 'intent': 'medicine_information',
                    'medicine_references': relief['names'], 'medicine_withheld': True,
                    'sources': relief['sources'], 'source_details': relief['source_details']}
    if (MEDICINE_REQUEST.search(text) and not blocked and not state.get('active_health_report')
            and {'continuous_sneezing', 'runny_nose'} <= symptoms
            and symptoms <= {'continuous_sneezing', 'runny_nose', 'congestion', 'itching', 'redness_of_eyes'}):
        selected = [r for r in records if r['name'] in {'cetirizine', 'loratadine'}]
        if selected:
            result = fallback_reply(selected, [], reason='local_reference', retryable=False)
            result['text'] = ('For **sneezing and runny nose**, antihistamines such as **cetirizine** '
                              'or **loratadine** are examples used when the cause is an allergy. '
                              'These symptoms can also have other causes; they do not confirm an allergy. '
                              'These are alternatives to discuss with a pharmacist, not instructions to take both.\n\n' + result['text'] +
                              '\n\nWhat is your age, and do you have allergies, medical conditions, pregnancy, '
                              'or other medicines to consider before choosing a product?')
            result['intent'] = 'medicine_information'
            return result
    return None
