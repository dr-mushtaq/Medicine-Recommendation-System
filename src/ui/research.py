"""Dataset inspection and saved model evaluation pages."""
import json

import pandas as pd
import streamlit as st

from src.data.loading import ARTIFACT_DIR, DATA_DIR
from src.data.regional import false_negative_rate, load_regional_preview
from .resources import EVAL_NAMES, model_metrics


def dataset_page(data):
    st.title('Dataset Preview')
    st.write('Original educational data and labelled illustrative additions, with separate hospital research cohorts.')
    library = data.get('health_library', {})
    if library.get('manifest'):
        st.subheader('Expanded health reference library')
        for col, label, key in zip(st.columns(3),
                                   ['Condition topics', 'Scoped symptom phrases', 'Distinct medicine names'],
                                   ['conditions', 'symptoms', 'medicines']):
            col.metric(label, len(library[key]))
        st.caption('Reference coverage is separate from trained condition labels and symptom features. '
                   'Medicine records are US label excerpts; availability in Pakistan has not been verified.')
        dictionary_count = sum(r.get('data_type') == 'ontology_definition' for r in library['conditions'])
        st.caption(f'{dictionary_count:,} topics are disease dictionary definitions; '
                   f'{len(library["conditions"]) - dictionary_count:,} are health guidance excerpts. '
                   'Dictionary definitions do not supply symptom or treatment rules.')
        chosen = st.selectbox('Reference library', ['conditions', 'symptoms', 'medicines'])
        st.dataframe(pd.DataFrame(library[chosen]), use_container_width=True, hide_index=True)
        st.download_button('Download reference ' + chosen, json.dumps(library[chosen], indent=2),
                           file_name='health_library_' + chosen + '.json', mime='application/json')
    stats = data['manifest']
    labels = ['Total input rows', 'Unique patterns', 'Conditions', 'Symptom features']
    values = [stats['raw_rows'], stats['unique_rows'], stats['condition_count'], stats['feature_count']]
    for col, label, value in zip(st.columns(4), labels, values):
        col.metric(label, value)
    st.info(
        f"{stats['duplicates_removed']:,} repeated patterns were removed before splitting. "
        'Repeated variants are not independent clinical cases.'
    )
    st.info(f"{len(data['reference_conditions'])} source-linked reference records provide educational summaries. "
            'They are not clinically reviewed prescribing guidance or patient observations.')
    hospital = data['pakistan_hospital_symptoms']
    st.subheader('Pakistani hospital symptom references')
    for col, label, value in zip(st.columns(3),
                                ['Symptom terms', 'Topic–symptom links', 'Hospital pages'],
                                [len({r['term'] for r in hospital}), len(hospital),
                                 len({r['source']['url'] for r in hospital})]):
        col.metric(label, value)
    st.caption('Published guidance from Aga Khan University Hospital, Shifa International Hospital and PKLI. '
               'These references improve wording coverage and answers; they are separate from patient cases and classifier training.')
    table = st.selectbox('JSON table', ['training', 'conditions', 'symptoms', 'manifest',
                                      'reference_conditions', 'symptom_metadata', 'pakistan_hospital_symptoms'])
    if table == 'manifest':
        st.json(stats)
    else:
        st.dataframe(pd.DataFrame(data[table]), use_container_width=True, hide_index=True)
        st.download_button(
            'Download ' + table + '.json',
            json.dumps(data[table], indent=2, ensure_ascii=False),
            file_name=table + '.json',
            mime='application/json',
        )
    counts = pd.Series([row['condition'] for row in data['training']]).value_counts().rename('Unique patterns')
    st.bar_chart(counts)
    st.caption('Medicine, diet, exercise and precaution records are unreviewed source material. Only condition classification is evaluated.')
    if stats.get('illustrative_rows'):
        added_labels = sum(r.get('data_type') == 'illustrative_condition_profile' for r in data['conditions'])
        st.info(f"{stats['legacy_unique_rows']:,} original educational patterns plus {stats['illustrative_rows']:,} labelled illustrative examples. Generated subsets are not hospital cases or clinical evidence. The {added_labels} added condition labels have no independent evaluation. Symptom features include exact source phrases, which can describe overlapping symptoms.")
    st.subheader('Hospital research datasets')
    try:
        catalog, regional, audit = load_regional_preview()
    except (OSError, ValueError, KeyError) as exc:
        st.warning(f'Hospital dataset preview unavailable: {exc}')
        return
    for col, label, value in zip(st.columns(3),
                                 ['Distinct observations', 'Research datasets', 'Countries'],
                                 [regional['unique_rows'], len(catalog['sources']), len(audit['countries'])]):
        col.metric(label, value)
    st.info('These public clinical cohorts are collected for research. Their targets include infant referral, '
            'heart-failure survival, diabetes and kidney disease. They are not used by the symptom classifier, '
            f"which contains {len(data['training']):,} educational patterns including labelled illustrative examples.")
    summaries = {s['source_id']: s for s in regional['sources']}
    st.dataframe(pd.DataFrame([{
        'Dataset': source['name'], 'Country': source['country'],
        'Raw rows': summaries[source['id']]['raw_rows'],
        'Distinct observations': summaries[source['id']]['unique_rows'],
        'Duplicates removed': summaries[source['id']]['duplicates_removed'],
        'Task': source['task'],
    } for source in catalog['sources']]), use_container_width=True, hide_index=True)
    source_by_name = {source['name']: source for source in catalog['sources']}
    chosen_name = st.selectbox('Hospital dataset', list(source_by_name))
    chosen = source_by_name[chosen_name]
    st.markdown(f"[Published dataset]({chosen['source_url']}) · [Licence]({chosen['license']['url']})")
    st.caption(chosen['target_meaning'])
    st.write(chosen['attribution'])
    prepared = DATA_DIR / 'regional' / summaries[chosen['id']]['file']
    st.download_button('Download clinical observations', prepared.read_bytes(), file_name=prepared.name,
                       mime='application/x-ndjson')
    st.download_button('Download hospital source catalog', json.dumps(catalog, indent=2),
                       file_name='hospital_sources.json', mime='application/json')
    with st.expander('Clinical dataset limitations and audit'):
        st.write(chosen['population'])
        for note in chosen['limitations']:
            st.write(note)
        for note in audit['warnings']:
            st.caption(note)



def evaluation_page(version):
    st.title('Model Evaluation')
    st.write('Measured results from the saved training run. The final test set is separate from model tuning.')
    try:
        metrics = model_metrics(version)
    except (FileNotFoundError, ValueError) as exc:
        st.warning(str(exc))
        return
    sizes = metrics['split_sizes']
    st.caption(f"Train: {sizes['train']} · Validation: {sizes['validation']} · Test: {sizes['test']} · Seed: {metrics['seed']}")
    rows = []
    for key, name in EVAL_NAMES.items():
        item = metrics['models'][key]
        rows.append({
            'Model': name,
            'Accuracy': item['accuracy'],
            'Macro F1': item['report']['macro avg']['f1-score'],
            'Precision': item['report']['macro avg']['precision'],
            'Recall': item['report']['macro avg']['recall'],
            'False negative rate': 1 - item['report']['macro avg']['recall'],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.warning('This is a technical benchmark on 61 template-like held-out records, not a clinical validation. '
               'Perfect scores do not establish real-world diagnosis, triage or medicine safety.')
    if metrics.get('unevaluated_labels'):
        st.warning(f"{len(metrics['unevaluated_labels'])} condition labels have no independent test examples.")
        with st.expander('Labels awaiting evaluation'):
            st.write(', '.join(metrics['unevaluated_labels']))
    chosen = st.selectbox('Inspect model', list(EVAL_NAMES), format_func=lambda k: EVAL_NAMES[k])
    item = metrics['models'][chosen]
    st.metric('Test accuracy', f"{item['accuracy']:.2%}")
    with st.expander('Precision, recall and F1', expanded=True):
        st.dataframe(pd.DataFrame(item['report']).transpose(), use_container_width=True)
    with st.expander('Confusion matrix — rows actual, columns predicted'):
        st.dataframe(pd.DataFrame(item['confusion_matrix'], index=metrics['labels'], columns=metrics['labels']))
    st.subheader('Fine-tuning history')
    st.line_chart(pd.DataFrame(metrics['training']['history']).set_index('epoch')[['train_loss', 'validation_loss']])
    st.caption(f"Best epoch: {metrics['training']['best_epoch']} · All encoder layers fine-tuned · Batch size: 16")
    with st.expander('Hyperparameters and optimization'):
        st.json(metrics['optimization'])
        st.write('Head regularization selected on fixed original validation examples. Training gives each condition and training family equal total weight. Transformer checkpoint selected by validation accuracy, then validation loss. Test data is not used for model selection.')
    research_path = ARTIFACT_DIR.parent / 'research/metrics.json'
    if research_path.exists():
        st.subheader('Published hospital data benchmarks')
        research = json.loads(research_path.read_text())
        st.caption('Separate research tasks using original study labels. These models are not used for chat responses.')
        st.dataframe(pd.DataFrame([{
            'Dataset': row['name'], 'Country': row['country'], 'Study task': row['task'],
            'Train / validation / test': ' / '.join(str(row['split_sizes'][key]) for key in ['train', 'validation', 'test']),
            'Balanced accuracy': row['test']['balanced_accuracy'], 'ROC AUC': row['test']['roc_auc'],
            'False negative rate': false_negative_rate(row['test']['confusion_matrix']),
            'Majority baseline': row['majority_baseline']['balanced_accuracy'],
        } for row in research['models']]), use_container_width=True, hide_index=True)
        with st.expander('Hospital benchmark methods and limitations'):
            st.write(research['selection_policy'])
            for row in research['models']:
                st.markdown('**' + row['name'] + '**')
                for note in row['limitations']:
                    st.caption(note)
            st.caption('The infant-referral cohort is excluded until its coded features and timing are reviewed.')
        st.download_button('Download hospital benchmark results', research_path.read_bytes(),
                           file_name='hospital_benchmarks.json', mime='application/json')
    st.download_button(
        'Download evaluation JSON',
        (ARTIFACT_DIR / 'metrics.json').read_bytes(),
        file_name='evaluation.json',
        mime='application/json',
    )

