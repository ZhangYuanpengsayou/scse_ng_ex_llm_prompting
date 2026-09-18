## Import the necessary modules
import json
import os
import re
import urllib.request

## Import the function from the module parse_data
from parse_data import load_items, get_unclaimed_items, save_result


## Build your prompt based on the description the user provides 
## and the items that are available in the lost-and-found database.
## The model must follow the rules listed in the README file
## The function should return the system prompt and the user prompt.
## You may need to use json.dumps() to convert the available_items list into a JSON string.

def build_prompt(description, available_items):
    items_json = json.dumps(available_items, indent=4)

    system_prompt = """You are a campus lost-and-found matching assistant.
You must use only the given JSON item database.
Not all details of an item must match to be a possible match.
Check every item in the database independently.
The "matches" list must contain all possible matching item IDs, not only the best match.
If multiple items match the same detail, include all of them.
Return only JSON with exactly this structure:
{
    "matches": ["ITEM_ID"],
    "confidence": "LOW"
}
The confidence value must be exactly one of: LOW, MEDIUM, HIGH.
If there is no match, return an empty matches list.
Do not include markdown, explanations, comments, or extra text."""

    user_prompt = f"""Lost item description:
{description}

Available unclaimed items JSON:
{items_json}

Compare the lost item description with every available item.
Return every possible matching item ID in "matches".
Return only the JSON object."""

    return system_prompt, user_prompt
    

## Logic to ask Qwen for all the possible matches based on the system prompt and user prompt.
## The function should return the response from Qwen.
def ask_qwen(system_prompt, user_prompt):
    payload = {
        "model": "qwen3:8b",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "stream": False
    }

    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data["message"]["content"]


## Logic to parse the response from Qwen and return the result. 
## You may need to use json.loads() to convert the response string into a suitable Python data structure.
def parse_response(response_text):
    response_text = response_text.strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)

        if match is None:
            return None

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    


## Logic to validate the result returned by Qwen.
## It should check if the result is a dictionary, contains the keys "matches" and "confidence", and that the values are of the correct type.
## If everything is correct, then it should check if the item IDs in the "matches" list are valid IDs .
def validate_result(result, available_items):
    if not isinstance(result, dict):
        return False

    if set(result.keys()) != {"matches", "confidence"}:
        return False

    if not isinstance(result["matches"], list):
        return False

    if not isinstance(result["confidence"], str):
        return False

    if result["confidence"] not in ["LOW", "MEDIUM", "HIGH"]:
        return False

    valid_ids = []

    for item in available_items:
        valid_ids.append(item["id"])

    for item_id in result["matches"]:
        if not isinstance(item_id, str):
            return False

        if item_id not in valid_ids:
            return False

    return True


## Logic to display the matches found by Qwen in a user-friendly format.
## It should look something like this:
""" 
CAMPUS LOST-AND-FOUND ASSISTANT
==================================================

Describe the item you lost: I lost a black bag somewhere

Searching for possible matches...

MATCH RESULT
--------------------------------------------------
Confidence: MEDIUM

Possible matches:

ID: F101
Item: backpack
Color: black
Location: Library 2nd floor
Date found: 2026-09-15

Result saved to output/match_result.json
 """
## If no matches are found, it should display a message indicating that no matches were found, along with the empty list
def display_matches(result, available_items):
    print("MATCH RESULT")
    print("-" * 50)
    print(f"Confidence: {result['confidence']}")
    print()

    if result["matches"] == []:
        print("No matches found.")
        print("Possible matches: []")
        return

    print("Possible matches:")
    print()

    for item_id in result["matches"]:
        for item in available_items:
            if item["id"] == item_id:
                print(f"ID: {item['id']}")
                print(f"Item: {item['item']}")
                print(f"Color: {item['color']}")
                print(f"Location: {item['location']}")
                print(f"Date found: {item['date']}")
                print()
    

## Control center for the entire program.
def main():
    base_dir = os.path.dirname(__file__)
    input_file = os.path.join(base_dir, "found_items.json")
    output_file = os.path.join(base_dir, "output", "match_result.json")

    items = load_items(input_file)
    available_items = get_unclaimed_items(items)

    print("CAMPUS LOST-AND-FOUND ASSISTANT")
    print("=" * 50)
    print()

    description = input("Describe the item you lost: ").strip()
    print()
    print("Searching for possible matches...")
    print()

    system_prompt, user_prompt = build_prompt(description, available_items)
    response_text = ask_qwen(system_prompt, user_prompt)
    result = parse_response(response_text)

    if not validate_result(result, available_items):
        result = {
            "matches": [],
            "confidence": "LOW"
        }

    display_matches(result, available_items)
    save_result(result, output_file)
    print(f"Result saved to {os.path.join('output', 'match_result.json')}")


if __name__ == "__main__":
    main()
