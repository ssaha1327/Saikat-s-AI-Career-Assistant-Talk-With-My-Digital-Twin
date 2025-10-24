from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr


load_dotenv(override=True)

def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )


def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

# Tool 3: Record conversation log
def record_conversation_log(summary, sentiment="Not provided", next_action="Not provided"):
    push(f"Recording conversation log - Summary: {summary}, Sentiment: {sentiment}, Next Action: {next_action}")
    return {"recorded": "ok"}

# Tool 4: Record job interest
def record_job_interest(role_title, company="Not provided", status="Not provided"):
    push(f"Recording job interest - Role: {role_title}, Company: {company}, Status: {status}")
    return {"recorded": "ok"}



record_user_details_json = {
    "name": "record_user_details",
    "description": "Records when a recruiter or user provides contact details or shows interest.",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "Email address of the recruiter or user"
            },
            "name": {
                "type": "string",
                "description": "Full name of the recruiter or user, if provided"
            },
            "organization": {
                "type": "string",
                "description": "Company or organization the user represents, if known"
            },
            "role": {
                "type": "string",
                "description": "User's job title or recruiting role, if provided"
            },
            "notes": {
                "type": "string",
                "description": "Summary of the conversation or their interest (e.g., internship, full-time role)"
            },
            "source": {
                "type": "string",
                "description": "Source of interaction (LinkedIn, website chat, email, etc.)"
            },
            "timestamp": {
                "type": "string",
                "description": "UTC timestamp of when the interaction was recorded"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Records questions the AI agent couldn't answer to improve future responses.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that the AI could not answer"
            },
            "intent_estimation": {
                "type": "string",
                "description": "Best guess of the user's intent (e.g., 'Job Role Inquiry', 'Project Detail', 'Education Background')"
            },
            "timestamp": {
                "type": "string",
                "description": "When this occurred (UTC format)"
            }
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

record_conversation_log_json = {
    "name": "record_conversation_log",
    "description": "Summarizes key conversation points for long-term memory or analytics.",
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Brief summary of what the user and AI discussed"
            },
            "sentiment": {
                "type": "string",
                "description": "Overall tone of the conversation (e.g., friendly, professional, curious)"
            },
            "next_action": {
                "type": "string",
                "description": "Recommended next step (e.g., 'follow up via email', 'send resume', 'schedule call')"
            }
        },
        "required": ["summary"],
        "additionalProperties": False
    }
}

record_job_interest_json = {
    "name": "record_job_interest",
    "description": "Records when a recruiter or user mentions a role or opportunity of interest.",
    "parameters": {
        "type": "object",
        "properties": {
            "role_title": {
                "type": "string",
                "description": "Job title or position discussed"
            },
            "company": {
                "type": "string",
                "description": "Company or organization name"
            },
            "status": {
                "type": "string",
                "description": "Status of interaction (interested, applied, follow-up scheduled)"
            }
        },
        "required": ["role_title"],
        "additionalProperties": False
    }
}

tools = [
    {"type": "function", "function": record_conversation_log_json},
    {"type": "function", "function": record_job_interest_json}
]


class Me:

    def __init__(self):
        self.openai = OpenAI()
        self.name = "Saikat Saha"
        reader = PdfReader("me/linkedin.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()


    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
    
    def system_prompt(self):
        system_prompt = f"""
You are an AI agent acting as **{self.name}**, representing him on his website.

When a conversation begins, always greet the user warmly before answering questions. 
Start with something like:
"Hi there! I’m {self.name}’s AI agent — how can I help you today?"
Then, guide them naturally based on their query.

Be professional, approachable, and stay in character as {self.name}. Use the tools provided for recording user details or unknown questions when needed.
...
"""
        system_prompt += f"You are an AI agent acting as {self.name}, representing him professionally on his website and digital portfolio. Your purpose is to engage visitors—especially recruiters, hiring managers, and collaborators—by answering questions about {self.name}'s background, experience, projects, and technical expertise in a clear, confident, and personable way. Always stay in character as {self.name}, responding as though you are speaking directly with a potential employer or professional contact. --- ### 🎯 Your Core Objectives: 1. Represent {self.name} accurately and authentically. - Base responses on {self.name}'s resume, LinkedIn profile, and professional summary. - When possible, highlight key achievements and project outcomes rather than generic descriptions. 2. Engage professionally. - Maintain a warm, confident, and articulate tone. - Keep answers concise but meaningful—show both technical depth and business acumen. - Adapt communication style to the user's tone (formal, conversational, technical, etc.). 3. Encourage meaningful connection. - If a recruiter or visitor expresses interest, politely ask for their email and record it using the record_user_details tool. - If the user mentions a specific role or opportunity, log it with the record_job_interest tool. - If a discussion suggests potential collaboration, summarize it using record_conversation_log. 4. Handle uncertainty gracefully. - If you don’t know the answer, don’t guess. Instead, call the record_unknown_question tool to store the question for future improvement, then respond politely that you’ll get back with more details. 5. Demonstrate expertise. - Confidently reference {self.name}’s expertise in Agentic AI, GenAI applications, LangChain, LangGraph, RAG pipelines, Power BI, and data analytics. - Showcase experience as a Data & Business Intelligence Analyst and past work in machine learning forecasting, automation, and dashboard design. - When discussing AI work, explain how {self.name} applies AI tools (e.g., LangChain, LangGraph, Python, SQL, Power BI) to solve business problems efficiently. --- ### 🧠 Key Personality Traits: - Professional and respectful, but approachable. - Confident in technical and analytical discussions. - Data-driven and solution-oriented. - Always positive and forward-looking. --- ### 📄 Reference Materials: Summary: {self.summary} LinkedIn Profile: {self.linkedin} --- With this context, engage in natural, professional dialogue with users as {self.name}. When appropriate, use available tools to: - Record user details (record_user_details) - Capture unknown questions (record_unknown_question) - Log conversation summaries (record_conversation_log) - Note role or company interest (record_job_interest) Always act as an intelligent, conversational representative of {self.name}, aiming to leave a professional and memorable impression. "

        return system_prompt
    
    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            if response.choices[0].finish_reason=="tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        return response.choices[0].message.content
    

if __name__ == "__main__":
    me = Me()

    def gr_chat_wrapper(user_message, chat_history):
        """Convert Gradio-style chat history to OpenAI format, then back."""
        formatted_history = []
        if chat_history:
            for user, ai in chat_history:
                if user:
                    formatted_history.append({"role": "user", "content": user})
                if ai:
                    formatted_history.append({"role": "assistant", "content": ai})

        ai_reply = me.chat(user_message, formatted_history)
        chat_history = (chat_history or []) + [(user_message, ai_reply)]
        return chat_history

    # --- UI Design ---
    with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate")) as demo:
        # Header with banner & intro
        gr.HTML(
            f"""
            <div style='text-align:center; padding: 25px; border-radius: 12px; background: linear-gradient(90deg, #e0f2ff, #f8fafc); box-shadow: 0 0 8px rgba(0,0,0,0.05);'>
                <h1 style='font-family: Inter, sans-serif; font-size: 32px; color:#1e3a8a; margin-bottom: 4px;'>💼 Saikat Saha's — AI Career Agent</h1>
                <p style='font-size: 17px; color:#334155;'>Ask about my experience, AI projects, or skills in analytics, automation, and business intelligence.</p>
            </div>
            """
        )

        # Greeting message
        greeting = f"Hi there! 👋 I’m {me.name}’s AI agent — how can I help you today?"
        chatbot = gr.Chatbot(
            value=[("", greeting)],
            show_label=False,
            height=500,
            bubble_full_width=False,
        )

        # Input & buttons
        with gr.Row():
            msg = gr.Textbox(
                placeholder="Type something like 'Tell me about Saikat’s core skillsets'...",
                label="Your Message",
                scale=10,
            )
            send = gr.Button("Send", variant="primary", scale=2)
            clear = gr.Button("Clear Chat", variant="secondary", scale=2)

        # Interaction logic
        msg.submit(gr_chat_wrapper, [msg, chatbot], chatbot)
        send.click(gr_chat_wrapper, [msg, chatbot], chatbot)  # ✅ Added send button
        clear.click(lambda: [], None, chatbot, queue=False)

        # Footer
        gr.HTML(
            """
            <div style='text-align:center; font-size: 14px; color:#64748b; margin-top: 18px;'>
                © 2025 Saikat Saha | Powered by OpenAI & Gradio
            </div>
            """
        )

    demo.launch()


    