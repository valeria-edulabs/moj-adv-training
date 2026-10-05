from rag_vectors.const import EMBEDDING_MODEL
import numpy as np
from dotenv import load_dotenv
load_dotenv()

# from langchain_openai import OpenAIEmbeddings
# embedding_model = OpenAIEmbeddings()

from langchain_google_genai import GoogleGenerativeAIEmbeddings
embedding_model = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

example_text = """Dogs are loyal, intelligent companions known for their playful energy and unconditional love."""
embedding = embedding_model.embed_query(example_text)
print(f"Example embedding for text {example_text}:\n{embedding}")
print(len(embedding))


# p1 = embedding_model.embed_query("I adopted a small dog from the animal shelter.")
# p2 = embedding_model.embed_query("I adopted a small dog from the animal shelter.")
# p2 = embedding_model.embed_query("I got a little puppy from the rescue center.")
# p2 = embedding_model.embed_query("Quantum cryptography functions via independent thermodynamic fluctuations.")

# p1 = embedding_model.embed_query("The stock market crashed during the economic crisis.")
# p2 = embedding_model.embed_query("I took my dog for a walk in the park this morning.")

# p1 = embedding_model.embed_query("The stock market crashed during the economic crisis.")
# p2 = embedding_model.embed_query("""מה קורה איש?""")

# p1 = embedding_model.embed_query("What's up dude?")
# p2 = embedding_model.embed_query("""מה קורה איש?""")

# p1 = embedding_model.embed_query("The stock market crashed during the economic crisis.")
# p2 = embedding_model.embed_query("The stock market did not crashed during the economic crisis. ")

# p1 = embedding_model.embed_query("The stock market crashed during the economic crisis.")
# p2 = embedding_model.embed_query("The stock market crashed during the economic crisis.")

# print(p1)
# print(p2)
# cosine_similarity = np.dot(p1, p2) / (np.linalg.norm(p1) * np.linalg.norm(p2))
# print(cosine_similarity)
