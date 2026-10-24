
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sentiment_analyzer = SentimentIntensityAnalyzer()

# Starter examples for the local classifier.
# This is a baseline model, not a model trained on verified Bihar complaints.
TRAINING_DATA = [
    ("large potholes and damaged road", "Roads"),
    ("road broken and traffic problems", "Roads"),
    ("street full of garbage and waste", "Sanitation"),
    ("garbage collection not happening", "Sanitation"),
    ("water supply stopped and no drinking water", "Water"),
    ("dirty water coming from the tap", "Water"),
    ("street lights are not working", "Electricity"),
    ("power outage and electricity failure", "Electricity"),
    ("bus service delayed and public transport", "Transport"),
    ("sewage overflow and blocked drainage", "Drainage"),
    ("hospital lacks medicine and medical services", "Healthcare"),
    ("school building and teacher problems", "Education"),
]

training_texts = [item[0] for item in TRAINING_DATA]
training_labels = [item[1] for item in TRAINING_DATA]

vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
training_vectors = vectorizer.fit_transform(training_texts)


KEYWORDS = {
    "Roads": ["pothole", "road", "highway", "street damage", "broken road"],
    "Sanitation": ["garbage", "rubbish", "waste", "trash", "dirty street"],
    "Water": ["water", "drinking water", "tap", "pipeline", "water supply"],
    "Electricity": ["electricity", "power cut", "power outage", "street light"],
    "Transport": ["bus", "transport", "traffic", "public transport"],
    "Drainage": ["drain", "sewage", "flooding", "drainage"],
    "Healthcare": ["hospital", "doctor", "medicine", "health centre"],
    "Education": ["school", "teacher", "classroom", "education"],
}

URGENT_TERMS = [
    "emergency", "danger", "urgent", "life threatening",
    "collapsed", "accident", "electrocut", "contaminated",
    "severe flooding", "no drinking water",
]


def clean_text(text):
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def classify_issue(text):
    cleaned = clean_text(text)
    if not cleaned:
        return "Other", 0.0

    query_vector = vectorizer.transform([cleaned])
    similarities = cosine_similarity(query_vector, training_vectors)[0]

    # Use keyword evidence as a simple extra signal.
    keyword_scores = {}
    lower_text = cleaned.lower()

    for department, keywords in KEYWORDS.items():
        keyword_scores[department] = sum(
            1 for keyword in keywords if keyword in lower_text
        )

    best_index = int(similarities.argmax())
    model_department = training_labels[best_index]
    model_score = float(similarities[best_index])

    best_keyword_department = max(keyword_scores, key=keyword_scores.get)
    best_keyword_score = keyword_scores[best_keyword_department]

    if best_keyword_score > 0:
        department = best_keyword_department
        confidence = min(
            0.95,
            0.55 + 0.12 * best_keyword_score + 0.25 * model_score
        )
    elif model_score >= 0.18:
        department = model_department
        confidence = min(0.85, model_score)
    else:
        department = "Other"
        confidence = 0.0

    return department, round(confidence, 2)


def analyze_sentiment(text):
    score = sentiment_analyzer.polarity_scores(clean_text(text))["compound"]

    if score >= 0.05:
        label = "Positive"
    elif score <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"

    return label, round(score, 3)



def score_priority(text):
    lower_text = clean_text(text).lower()

    critical_terms = [
        "life threatening", "electrocuted", "live electric wire",
        "building collapse", "major accident", "severe flooding",
        "contaminated drinking water",
    ]

    high_terms = [
        "large pothole", "large potholes", "deep pothole",
        "deep potholes", "road collapsed", "road collapse",
        "dangerous road", "no drinking water", "sewage overflow",
        "electricity exposed wire",
    ]

    medium_terms = [
        "pothole", "potholes", "road damage", "broken road",
        "street light", "street lights", "not working",
        "water supply", "garbage", "blocked drain",
    ]

    critical_matches = [
        term for term in critical_terms if term in lower_text
    ]
    high_matches = [
        term for term in high_terms if term in lower_text
    ]
    medium_matches = [
        term for term in medium_terms if term in lower_text
    ]

    if critical_matches:
        return "Critical", 95, critical_matches

    if high_matches:
        return "High", 75, high_matches

    if medium_matches:
        return "Medium", 50, medium_matches

    return "Normal", 25, []




def find_similar_complaints(text, complaints, threshold=0.25):
    cleaned = clean_text(text)
    existing = [clean_text(item) for item in complaints]

    # Ignore empty complaint records
    valid_items = [
        (index, original, clean)
        for index, (original, clean) in enumerate(
            zip(complaints, existing)
        )
        if clean
    ]

    if not cleaned or not valid_items:
        return []

    # Compare only non-empty records
    all_text = [item[2] for item in valid_items] + [cleaned]

    local_vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
    )

    vectors = local_vectorizer.fit_transform(all_text)
    scores = cosine_similarity(
        vectors[-1], vectors[:-1]
    ).flatten()

    matches = []

    for (original_index, original_text, _), score in zip(
        valid_items, scores
    ):
        if score >= threshold:
            matches.append({
                "index": original_index,
                "similarity": round(float(score), 3),
                "text": original_text,
            })

    return sorted(
        matches,
        key=lambda item: item["similarity"],
        reverse=True,
    )



def analyze_grievance(text):
    cleaned = clean_text(text)

    if not cleaned:
        raise ValueError("Please enter a grievance.")

    department, confidence = classify_issue(cleaned)
    sentiment, sentiment_score = analyze_sentiment(cleaned)
    priority, priority_score, reasons = score_priority(cleaned)

    return {
        "cleaned_text": cleaned,
        "department": department,
        "classification_confidence": confidence,
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "priority": priority,
        "priority_score": priority_score,
        "priority_reasons": reasons,
    }
    if __name__ == "__main__":
        print(score_priority("large potholes are damaging our road"))
