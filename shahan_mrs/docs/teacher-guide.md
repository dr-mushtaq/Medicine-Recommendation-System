# Explaining the Medicine Recommendation System

This project demonstrates a supervised machine-learning workflow inside a health
information chatbot. Begin with the data, explain how models are trained and
evaluated, and then demonstrate how a saved model is used in a conversation.
The outputs are educational condition matches, not clinically validated diagnoses.

## 1. Explain the problem

Input: a person's symptom description.
Target: a condition label from the prepared educational dataset.
Output: possible condition matches, follow-up questions and educational information.

This is multiclass classification. A separate intent classifier recognizes requests
such as summaries, explanations and duration updates. General-answer generation and
medical report explanations use a configured language-model service; they are not
outputs of the condition classifier.

## 2. Show the data

Open these files in order:

1. `references/supervisor/dataset/Training.csv`: original symptom flags and condition labels.
2. `scripts/prepare_json.py`: CSV cleaning, validation and conversion entry point.
3. `data/training.json`: prepared examples with IDs, symptoms, labels and split metadata.
4. `data/manifest.json`: source hashes, record counts and provenance.
5. `src/data/loading.py`: integrity checks and lookup construction used by the app.

The project also includes source-linked reference records and illustrative training
additions. Reference text and generated symptom combinations are not observed
patient cases. The regional clinical datasets are separate research tasks; they do
not train the chatbot's symptom classifier.

## 3. Explain feature preparation

Open `src/ml/features.py` and show `symptom_text()`.
It turns stable symptom IDs into readable text, preserving the actual wording for
source-derived phrases. Training and prediction use the same conversion.

The baseline converts that text into TF-IDF unigram and bigram features.
MiniLM tokenizes the text and creates contextual vector representations using masked
mean pooling and normalization. Its classification head predicts condition labels.

## 4. Explain the train validation test split

Open `src/ml/condition_training.py` and show `split_dataset()`.

- Training examples fit the models.
- Validation examples choose regularization and the fine-tuning checkpoint.
- Test examples measure the selected models after fitting and selection.

When the dataset supplies fixed splits, those assignments are preserved and related
training families cannot overlap held-out families. Without supplied splits, the
function uses a reproducible stratified 60/20/20 split.

The saved run has 5,878 training, 61 validation and 61 test examples. This is not a
60/20/20 split of the expanded dataset: illustrative additions remain in training,
while the original holdouts stay fixed. `calculate_training_weights()` prevents
families with many illustrative variations from gaining extra influence.

## 5. Explain the three model comparisons

Open `src/ml/condition_training.py` and follow the numbered comments in `main()`.

1. TF-IDF plus logistic regression is the traditional ML baseline.
2. Frozen MiniLM embeddings plus logistic regression test a pretrained representation
   without changing the encoder.
3. Fine-tuned MiniLM updates the encoder and classification head using training data.

`select_model()` tries regularization values using validation accuracy.
Fine-tuning selects its best checkpoint by validation accuracy, then validation loss,
and stops after three epochs without improvement.

The train command is `python scripts/train_chatbot.py`. It writes model artifacts
and metrics, so do not run it during a short demonstration merely to view results.
Use `python scripts/train_chatbot.py --help` to show the available options safely.

## 6. Explain evaluation honestly

Open `src/ml/evaluation.py` and show `evaluate()`.
It calculates accuracy, a per-class classification report and the confusion matrix.
In the app, open About & sources, then Model Evaluation.

The saved condition-model run reports 100 percent accuracy for all three models on
61 template-like test records. This does not demonstrate real-world medical accuracy.
There are 510 output labels, but 469 have no independent test examples. Explain this
limitation when presenting results; illustrative augmentation cannot replace an
independent patient evaluation.

The intent model is a different experiment. Its examples are authored language
utterances, with a 342/54/54 train/validation/test split. It measures routing behavior,
not diagnostic performance. Its implementation is `src/ml/intent_training.py`.

## 7. Trace a live prediction

Open these functions in order:

1. `src/ui/chat.py` → `chat_page()`: accepts a submitted message.
2. `src/chatbot/dialogue.py` → `respond()`: handles safety, symptoms and routing.
3. `src/ml/condition_model.py` → `predict()`: converts symptoms, runs the saved model
   and ranks up to three condition matches.
4. `src/ui/messages.py` → `render_message()`: displays the result and supporting information.

`load_bundle()` loads saved artifacts and checks their dataset fingerprint. It does
not retrain the model when a visitor asks a question. Model scores are ranking
outputs, not calibrated medical confidence.

Medicine names come from stored condition mappings, not a separately trained
prescription model. The chatbot can withhold them based on context and safety rules.
Hospital navigation, OCR, voice input and history are supporting application features.

## 8. Suggested classroom demonstration

1. Start with `README.md` and explain the folders.
2. Show one original record and its prepared JSON representation.
3. Explain feature conversion, splitting and the three model alternatives.
4. Open saved evaluation results and state the holdout limitations.
5. Run `streamlit run app.py` and demonstrate a symptom conversation.
6. Demonstrate a follow-up question and conversation summary.
7. If showing report uploads, use a fictional report and explain which model service receives it.
8. Finish by showing the automated tests and describing what they check.

A useful opening statement is: “This is an educational health-information chatbot
that compares traditional ML and transformer classification, preserves independent
holdouts, and connects saved predictions to a conversational interface.”
