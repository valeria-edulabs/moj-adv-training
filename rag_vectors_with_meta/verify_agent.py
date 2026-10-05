from backend import stream

# Test a query about discount bank
print("--- Querying agent about Discount bank ---")
for chunk in stream("What are the steps to get a loan at Discount bank?", "thread_1"):
    # If the chunk has a message content, print it
    if "model" in chunk:
        msg = chunk["model"]["messages"][0]
        if hasattr(msg, "content") and msg.content:
            print(msg.content, end="", flush=True)
print("\n")

print("\n--- Querying agent about Hapoalim bank ---")
# Test a query about hapoalim bank
for chunk in stream("What is the phone number for Hapoalim bank mortgage help?", "thread_1"):
    if "model" in chunk:
        msg = chunk["model"]["messages"][0]
        if hasattr(msg, "content") and msg.content:
            print(msg.content, end="", flush=True)
print("\n")
