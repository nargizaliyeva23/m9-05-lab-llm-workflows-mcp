import json
from google import genai
from google.genai import types

# -------------------------
# CLIENT
# -------------------------
client = genai.Client()

# FIXED MODEL
MODEL = "gemini-1.5-flash"

# -------------------------
# LOAD DATA
# -------------------------
with open("orders.json", "r") as f:
    orders = json.load(f)

# -------------------------
# TOOLS
# -------------------------
def lookup_order(order_id: str):
    return orders.get(order_id, {"error": "not found"})

def calculate(expression: str):
    try:
        return eval(expression, {"__builtins__": {}})
    except Exception as e:
        return str(e)

TOOLS = {
    "lookup_order": lookup_order,
    "calculate": calculate
}

# -------------------------
# SYSTEM PROMPT
# -------------------------
SYSTEM_PROMPT = """
You are a strict tool-using assistant.

You MUST respond ONLY in JSON.

If tool is needed:
{"tool":"lookup_order","args":{"order_id":"A1001"}}

or:
{"tool":"calculate","args":{"expression":"3*1200"}}

If final answer:
{"final":"answer"}

Rules:
- Never explain
- Never ask questions
- Always use tools for calculations
"""

# -------------------------
# SAFE JSON PARSER
# -------------------------
def safe_json(text):
    try:
        return json.loads(text)
    except:
        return {"final": text}

# -------------------------
# TOOL RUNNER
# -------------------------
def run_tool(name, args):
    if name == "lookup_order":
        return lookup_order(args["order_id"])
    elif name == "calculate":
        return calculate(args["expression"])
    return {"error": "unknown tool"}

# -------------------------
# AGENT LOOP
# -------------------------
def run_agent(user_input, messages):

    # user message
    messages.append(
        types.Content(
            role="model",
            parts=[types.Part.from_text(text=user_input)]
        )
    )

    for step in range(5):
        print(f"\n===== STEP {step+1} =====")

        response = client.models.generate_content(
            model=MODEL,
            contents=messages
        )

        text = response.text
        print("MODEL OUTPUT:\n", text)

        data = safe_json(text)

        # -------------------------
        # TOOL CALL
        # -------------------------
        if "tool" in data:
            tool_name = data["tool"]
            args = data.get("args", {})

            print("TOOL:", tool_name, args)

            result = run_tool(tool_name, args)
            print("TOOL RESULT:", result)

            # FIX 1: save model output correctly
            messages.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=text)]
                )
            )

            # FIX 2: tool result must be JSON
            messages.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=json.dumps(result))]
                )
            )

            # FIX 3: force reasoning step
            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(
                        text="Use tool result and return FINAL answer in JSON"
                    )]
                )
            )

            continue

        # -------------------------
        # FINAL ANSWER
        # -------------------------
        print("FINAL:", data.get("final", text))

        messages.append(
            types.Content(
                role="assistant",
                parts=[types.Part.from_text(text=text)]
            )
        )

        return data.get("final", text)

    print("couldn't finish in time")


# -------------------------
# MAIN (TWO TURNS)
# -------------------------
def main():

    messages = []

    print("\n\n===== TURN 1 =====")
    run_agent("What did order A1001 cost?", messages)

    print("\n\n===== TURN 2 =====")
    run_agent("And what about three of them?", messages)


if __name__ == "__main__":
    main()