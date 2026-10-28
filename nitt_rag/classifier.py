from __future__ import annotations

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


TRAINING_EXAMPLES = [
    ("course plan syllabus assessment faculty course code credits", "course_plan"),
    ("what is the course plan for ar507", "course_plan"),
    ("show assessment methods for data structures", "course_plan"),
    ("who teaches architectural design viii", "course_plan"),
    ("course outcomes for machine learning", "course_plan"),
    ("fees btech 2026 tuition remission refund", "fees"),
    ("what is the fee structure for btech", "fees"),
    ("income based tuition fee remission", "fees"),
    ("hostel fees odd semester", "fees"),
    ("curriculum syllabus regulation credits programme structure", "curriculum"),
    ("btech cse curriculum 2024 syllabus", "curriculum"),
    ("mtech data analytics curriculum", "curriculum"),
    ("academic calendar schedule semester registration", "academics"),
    ("registration assessment transcript scholarship stipend notice", "academics"),
    ("admission eligibility josaa csab mtech mca mba phd", "admissions"),
    ("how to apply for mca admission", "admissions"),
    ("opening closing rank btech admission", "admissions"),
    ("department faculty research projects cse mechanical civil", "department"),
    ("computer science department faculty", "department"),
    ("placement training career internship", "placements"),
    ("library hostel hospital sports transport student facilities", "student_facilities"),
]


class QuestionClassifier:
    def __init__(self) -> None:
        self.pipeline = Pipeline(
            [
                ("vectorizer", CountVectorizer(ngram_range=(1, 2), stop_words="english")),
                ("model", MultinomialNB()),
            ]
        )
        texts, labels = zip(*TRAINING_EXAMPLES)
        self.pipeline.fit(texts, labels)

    def predict(self, question: str) -> tuple[str, float]:
        label = self.pipeline.predict([question])[0]
        probabilities = self.pipeline.predict_proba([question])[0]
        classes = list(self.pipeline.classes_)
        confidence = float(probabilities[classes.index(label)])
        return label, confidence
