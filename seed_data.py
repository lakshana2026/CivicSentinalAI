
from ai_engine import analyze_grievance
from case_store import init_db, save_case, get_cases


SAMPLE_COMPLAINTS = [
    "A large pothole is damaging vehicles on our road.",
    "There is no drinking water supply in our area.",
    "Streetlights are not working near the bus stop.",
    "Garbage has not been collected for several days.",
    "A damaged road is causing severe traffic congestion.",
    "The drainage system is overflowing after rainfall.",
    "Several streetlights are broken near the school.",
    "Water is leaking continuously from a public pipeline.",
    "An uncovered manhole is creating a safety hazard.",
    "A public road has been blocked by construction debris.",
    "The municipal park is poorly maintained.",
    "Sewage water is flowing onto the main road.",
    "A traffic signal is not functioning at the junction.",
    "There is a suspected scam message impersonating a bank.",
    "Someone is posting suspicious links claiming to be a government service.",
    "A public building has damaged steps that need repair.",
    "The garbage collection vehicle has missed our street.",
    "The road near the hospital has several dangerous potholes.",
    "There has been a power outage in our neighbourhood.",
    "A broken water pipe is flooding the street.",
]


def main():
    init_db()

    existing_cases = get_cases()
    existing_complaints = {
        str(case["complaint"]).strip().casefold()
        for case in existing_cases
    }

    added = 0
    skipped = 0

    for complaint in SAMPLE_COMPLAINTS:
        if complaint.strip().casefold() in existing_complaints:
            skipped += 1
            continue

        try:
            result = analyze_grievance(complaint)

            save_case(
                complaint=complaint,
                department=result["department"],
                priority=result["priority"],
                priority_score=result["priority_score"],
                sentiment=result["sentiment"],
            )

            existing_complaints.add(complaint.strip().casefold())
            added += 1
            print(f"Added: {complaint}")

        except Exception as error:
            print(f"Failed: {complaint}")
            print(f"Reason: {error}")

    print("\nDataset loading finished.")
    print(f"New cases added: {added}")
    print(f"Existing cases skipped: {skipped}")


if __name__ == "__main__":
    main()
