from newscheck.pipeline import check

INPUTS = [
    "BREAKING 🚨 Microsoft is kicking out 60,000 employees!!! Share before it's deleted 😱",
    "Infosys fired 20,000 people. What a shameful company.",
    "Virat Kohli is the greatest batsman of all time.",
]

for text in INPUTS:
    print("=" * 70)
    print(f"INPUT: {text}\n")
    print(check(text))