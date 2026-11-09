"""Grounded replies when the optional generative provider cannot answer."""
import re
from src.services.medical_files import is_account_file

LAB_TERMS = re.compile(r'\b(?:hemoglobin|haemoglobin|hgb|hb|glucose|hba1c|creatinine|urea|egfr|cholesterol|'
                       r'triglycerides|hdl|ldl|platelets?|wbc|rbc|white blood|red blood|sodium|potassium|'
                       r'calcium|bilirubin|alt|ast|tsh|thyroxine|ferritin|vitamin|hematocrit|haematocrit|mcv|mch|crp)\b', re.I)
PAGE_MARKER = re.compile(r'\[Page (\d+)\]')
RESULT_FLAG = re.compile(r'(?i)^(?:low|high|h|l|normal|in range|abnormal|critical|positive|negative)$')
RESULT_UNIT = re.compile(r'(?i)^[a-zµμ]{1,8}(?:/[a-zµμ0-9.^]{1,12})?$')
INSTRUCTION = re.compile(r'\bignore\b.{0,40}\binstructions?\b', re.I)


def _plain(line):
    return re.sub(r'[`*<>\[\]]', '', line.strip())


def _value_fragment(line):
    """A table cell that belongs to the lab name above it, not the next sentence."""
    if not line or len(line) > 40 or INSTRUCTION.search(line):
        return False
    if RESULT_FLAG.fullmatch(line) or RESULT_UNIT.fullmatch(line):
        return True
    return bool(re.search(r'\d', line) and not re.search(r'[A-Za-z]{8,}', line))


def report_findings(text):
    """Read lab rows even when a PDF table places the name, value and unit on separate lines."""
    rows, page, lines = [], None, [line.strip() for line in text.splitlines()]
    index = 0
    while index < len(lines) and len(rows) < 6:
        line = lines[index]
        marker = PAGE_MARKER.fullmatch(line)
        if marker:
            page = marker.group(1)
            index += 1
            continue
        if LAB_TERMS.search(line) and len(line) <= 180 and not INSTRUCTION.search(line):
            if re.search(r'\d', line):
                rows.append('• ' + _plain(line) + (f' (page {page})' if page else ''))
                index += 1
                continue
            parts, cursor, blanks = [line], index + 1, 0
            while cursor < len(lines) and len(parts) < 5:
                nxt = lines[cursor]
                if not nxt:
                    blanks += 1
                    if blanks > 1:
                        break
                    cursor += 1
                    continue
                if PAGE_MARKER.fullmatch(nxt) or LAB_TERMS.search(nxt) or not _value_fragment(nxt):
                    break
                parts.append(nxt)
                cursor += 1
            if any(re.search(r'\d', part) for part in parts[1:]):
                rows.append('• ' + _plain(' '.join(parts)) + (f' (page {page})' if page else ''))
                index = cursor
                continue
        index += 1
    return rows


def report_excerpt(text):
    """Quote a short slice of a report that has no separate lab-result rows."""
    kept, page = [], None
    for raw in text.splitlines():
        line = raw.strip()
        marker = PAGE_MARKER.fullmatch(line)
        if marker:
            page = marker.group(1)
            continue
        if not line or len(line) > 180 or INSTRUCTION.search(line) or not any(c.isalnum() for c in line):
            continue
        kept.append('• ' + _plain(line) + (f' (page {page})' if page else ''))
        if len(kept) == 8:
            break
    return kept


def protected_attachment_reply(reports):
    if reports and all(is_account_file(r.get('name', '')) for r in reports):
        return {'text': 'This attachment appears to contain account recovery information rather than a medical report. '
                'Please choose a test result, medical report or prescription. You can also describe your symptoms here.',
                'predictions': [], 'intent': 'attachment_not_medical', 'medicine_withheld': True}


def fallback_reply(records, reports, reason='connection', retryable=True):
    reports = [r for r in reports if not is_account_file(r.get('name', ''))]
    if reports:
        sections = ['I can read your uploaded text. Here are the report details available while the full explanation is unavailable:']
        found = False
        for report in reports:
            # Verbatim report values only. No reference ranges, units or conclusions are invented.
            lines = report_findings(report.get('text', '')) or report_excerpt(report.get('text', ''))
            if lines:
                found = True
                sections.append('**' + re.sub(r'[`*<>\[\]]', '', report['name']) + '**\n\n' + '\n\n'.join(lines))
        if found:
            sections.append('Here is the text I could read from your file. '
                            'Please check it against the original report. ' +
                            ('Select **Retry answer** for a detailed explanation, or tell me which result you would like to discuss.'
                             if retryable else 'The explanation service is unavailable. It must be connected before I can explain these findings.'))
        else:
            sections = ['Your file is available in this conversation, but I couldn’t read any of its text just now. '
                        + ('Please select **Retry answer**, or paste the test name, result, unit and reference range you want to understand.'
                           if retryable else 'The explanation service must be connected before I can explain the report.')]
        return {'text': '\n\n'.join(sections), 'predictions': [], 'intent': 'report_summary_fallback',
                'retryable': retryable, 'medicine_withheld': True, 'generation_status': reason}
    if records:
        sections = ['Here is the source-backed information I can share:']
        for record in records[:2]:
            sections.append('**' + record['name'] + '**\n\n' + record['description'])
            if record.get('care_notes'):
                sections.append('**General care**\n\n' + ' '.join(record['care_notes']))
            if record.get('seek_help_notes'):
                title = 'Label safety notes' if record.get('data_type') == 'drug_label_excerpt' else 'When to seek help'
                sections.append('**' + title + '**\n\n' + ' '.join(record['seek_help_notes']))
            if record.get('data_type') == 'drug_label_excerpt':
                sections.append('This is a brief extract from the US product label. Read the full label for complete instructions and safety information.')
        sources = [s for r in records[:2] for s in r['sources']]
        return {'text': '\n\n'.join(sections), 'predictions': [], 'intent': 'reference_fallback',
                'sources': list(dict.fromkeys(s['url'] for s in sources)), 'source_details': sources,
                'generation_status': reason, 'medicine_withheld': True}
    lead = ('I couldn’t complete your answer at the moment. Please try again shortly.' if reason == 'busy'
            else 'I couldn’t complete your answer right now.')
    action = (' Please retry using **Retry answer**. Your message is still here.' if retryable
              else ' General answers are temporarily unavailable. You can describe your symptoms here and continue with guided questions.')
    return {'text': lead + action, 'predictions': [], 'intent': 'general_question_unavailable',
            'retryable': retryable, 'generation_status': reason}
