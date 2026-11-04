import numpy as np

from newscheck.embeddings import embed_passages, embed_query

CLAIM = "Microsoft is kicking out 60,000 employees."
PASSAGES = [
    "Microsoft fired 60,000 workers on Monday.",                           # same claim, reworded
    "Microsoft is offering voluntary buyouts to about 60,000 employees.",  # same event, different action
    "Shares of Microsoft rose about 1% on Monday.",                        # same company, other fact
    "Baked Greek meatballs and potatoes: get the one-pan recipe.",          # page noise
]

q = np.array(embed_query(CLAIM))
for text, vec in zip(PASSAGES, embed_passages(PASSAGES)):
    v = np.array(vec)
    cosine = float(q @ v / (np.linalg.norm(q) * np.linalg.norm(v)))
    print(f"{cosine:.3f}  {text}")