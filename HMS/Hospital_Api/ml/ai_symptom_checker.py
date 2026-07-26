import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any

load_dotenv()

# --- 1. Define State ---
class AgentState(TypedDict):
    symptoms: str
    severity: str # "NORMAL" or "EMERGENCY"
    disease: str
    probability: float
    medicine: str
    tips: str

# --- 2. Initialize LLM ---
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

# --- 3. Define Agents (Nodes) ---

def triage_agent(state: AgentState):
    """Evaluates if the symptoms are an emergency."""
    prompt = """You are a Medical Triage Agent.
Analyze the symptoms and output EXACTLY ONE WORD: "EMERGENCY" if the symptoms are life-threatening (e.g. severe chest pain, unable to breathe, stroke signs) or "NORMAL" for everything else.
"""
    messages = [SystemMessage(content=prompt), HumanMessage(content=state["symptoms"])]
    response = llm.invoke(messages).content.strip().upper()
    
    if "EMERGENCY" in response:
        state["severity"] = "EMERGENCY"
        state["disease"] = "Emergency Department"
        state["probability"] = 99.9
        state["medicine"] = "DO NOT SELF-MEDICATE."
        state["tips"] = "SEEK IMMEDIATE EMERGENCY MEDICAL HELP OR CALL AN AMBULANCE."
    else:
        state["severity"] = "NORMAL"
        
    return state

def symptom_analyst_agent(state: AgentState):
    """Determines the condition and the hospital department."""
    prompt = """You are an expert Symptom Analyst Agent.
Analyze the symptoms and determine the most relevant hospital department/specialist (e.g., General Physician, Dermatologist, Cardiologist, Gastroenterologist).
Also provide a realistic confidence probability (0.0 to 100.0).
Return ONLY valid JSON:
{"department": "String", "probability": Float}
"""
    messages = [SystemMessage(content=prompt), HumanMessage(content=state["symptoms"])]
    response = llm.invoke(messages).content.strip()
    
    try:
        if response.startswith("```json"):
            response = response.split("```json")[1].split("```")[0].strip()
        elif response.startswith("```"):
            response = response.split("```")[1].strip()
        data = json.loads(response)
        state["disease"] = data.get("department", "General Physician")
        state["probability"] = float(data.get("probability", 50.0))
    except Exception as e:
        state["disease"] = "General Physician"
        state["probability"] = 30.0
        
    return state

def treatment_recommender_agent(state: AgentState):
    """Recommends safe OTC medicine and tips."""
    prompt = f"""You are a Treatment Recommender Agent.
The patient has symptoms: '{state['symptoms']}'.
They are being referred to: '{state['disease']}'.
Provide perfectly safe, OVER-THE-COUNTER medical advice and lifestyle tips. NEVER prescribe specific dosages of dangerous drugs.
Return ONLY valid JSON:
{{"medicine": "String", "tips": "String"}}
"""
    messages = [SystemMessage(content=prompt), HumanMessage(content=state["symptoms"])]
    response = llm.invoke(messages).content.strip()
    
    try:
        if response.startswith("```json"):
            response = response.split("```json")[1].split("```")[0].strip()
        elif response.startswith("```"):
            response = response.split("```")[1].strip()
        data = json.loads(response)
        state["medicine"] = data.get("medicine", "Consult a pharmacist for safe OTC options.")
        state["tips"] = data.get("tips", "Rest and stay hydrated.")
    except Exception as e:
        state["medicine"] = "Consult a pharmacist."
        state["tips"] = "Please visit a doctor for a proper diagnosis."
        
    return state

# --- 4. Define Edges & Routing ---
def route_triage(state: AgentState):
    """Route to emergency end or normal analyst."""
    if state.get("severity") == "EMERGENCY":
        return END
    return "analyst"

# --- 5. Compile Graph ---
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("triage", triage_agent)
workflow.add_node("analyst", symptom_analyst_agent)
workflow.add_node("treatment", treatment_recommender_agent)

# Add Edges
workflow.set_entry_point("triage")
workflow.add_conditional_edges("triage", route_triage)
workflow.add_edge("analyst", "treatment")
workflow.add_edge("treatment", END)

# Compile
multi_agent_system = workflow.compile()

# --- 6. Interface Class for Django ---
class AISymptomChecker:
    def __init__(self):
        self.agent = multi_agent_system

    def predict_disease(self, symptoms_text):
        """Runs the multi-agent graph."""
        initial_state = {
            "symptoms": symptoms_text,
            "severity": "",
            "disease": "",
            "probability": 0.0,
            "medicine": "",
            "tips": ""
        }
        
        try:
            final_state = self.agent.invoke(initial_state)
            
            # Format to match what the frontend expects
            result = {
                "disease": final_state.get("disease", "Unknown"),
                "probability": final_state.get("probability", 0.0),
                "medicine": final_state.get("medicine", ""),
                "tips": final_state.get("tips", "")
            }
            return [result]
        except Exception as e:
            print("Multi-Agent Error:", e)
            return [{
                "disease": "System Error",
                "probability": 0.0,
                "medicine": "AI Service Unavailable",
                "tips": "Please try again later."
            }]
