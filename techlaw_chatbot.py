import streamlit as st
import json
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import requests

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="TechLaw25 - Contract Assistant",
    page_icon="⚖️",
    layout="wide"
)

# Initialize session state variables
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'user_name' not in st.session_state:
    st.session_state.user_name = None

if 'user_email' not in st.session_state:
    st.session_state.user_email = None

if 'conversation_stage' not in st.session_state:
    st.session_state.conversation_stage = 'greeting'

if 'contract_type' not in st.session_state:
    st.session_state.contract_type = None

if 'relationship_type' not in st.session_state:
    st.session_state.relationship_type = None

if 'contract_list_type' not in st.session_state:
    st.session_state.contract_list_type = None

if 'role' not in st.session_state:
    st.session_state.role = None

if 'contract_data' not in st.session_state:
    st.session_state.contract_data = {
        "contract_type": "",
        "relationship_type": "",
        "contract_list_type": "",
        "questions": {
            "company_name": "",
            "company_address": "",
            "company_city": "",
            "company_state": "",
            "company_pincode": "",
            "company_country": "",
            "other_party_name": "",
            "other_party_address": "",
            "other_party_city": "",
            "other_party_state": "",
            "other_party_pincode": "",
            "other_party_country": "",
            "product_to_be_evaluated": "",
            "product_version": "",
            "number_of_licenses": "",
            "license_type": "",
            "period_for_evaluation": "",
            "fees_options": "",
            "currency": "",
            "amount": "",
            "invoicing": "",
            "credit_period": "",
            "late_payment_charges": "",
            "late_payment_percentage": "",
            "tax_fees": "",
            "agreement_start_date": "",
            "agreement_end_date": "",
            "laws_which_apply": "",
            "courts_which_resolve": ""
        }
    }

if 'document_url' not in st.session_state:
    st.session_state.document_url = None

if 'documents_ready' not in st.session_state:
    st.session_state.documents_ready = False

if 'pdf_content' not in st.session_state:
    st.session_state.pdf_content = None

if 'word_content' not in st.session_state:
    st.session_state.word_content = None

if 'pdf_filename' not in st.session_state:
    st.session_state.pdf_filename = None

if 'word_filename' not in st.session_state:
    st.session_state.word_filename = None

if 'collected_fields' not in st.session_state:
    st.session_state.collected_fields = []

if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0

if 'asked_questions' not in st.session_state:
    st.session_state.asked_questions = []

if 'follow_up_count' not in st.session_state:
    st.session_state.follow_up_count = 0

# Questions from documents - Buyer role
BUYER_QUESTIONS = [
    {
        "id": 1,
        "question": "What is the name and version of the supplier's product you plan to evaluate?",
        "explanation": "Based on your business requirements or use cases, suppliers recommend their most suitable product(s) for you to evaluate.",
        "fields": ["product_to_be_evaluated", "product_version"]
    },
    {
        "id": 2,
        "question": "How many trial licenses will you need, and what type of licenses?",
        "explanation": "Consider your team size and evaluation scope. License types can be concurrent, named-user, or server licenses.",
        "fields": ["number_of_licenses", "license_type"]
    },
    {
        "id": 3,
        "question": "How many days do you need for the evaluation?",
        "explanation": "Generally 30-60 days. We'll suggest 60 days if not specified.",
        "fields": ["period_for_evaluation"]
    },
    {
        "id": 4,
        "question": "When would you like to start the evaluation?",
        "explanation": "Provide a specific date if you know it, or we can use a standard start date.",
        "fields": ["agreement_start_date"]
    },
    {
        "id": 5,
        "question": "Will there be any fees for this trial? If yes, provide the amount, currency, and payment terms.",
        "explanation": "Suppliers typically offer free trials. If there's a fee, specify amount, currency, invoicing method, credit period, and any late payment terms.",
        "fields": ["fees_options", "currency", "amount", "invoicing", "credit_period", "late_payment_charges", "late_payment_percentage", "tax_fees"]
    },
    {
        "id": 6,
        "question": "What is your company or organization's full name and complete address?",
        "explanation": "Include your full company name, street address, city, state/province, postal code, and country.",
        "fields": ["company_name", "company_address", "company_city", "company_state", "company_pincode", "company_country"]
    },
    {
        "id": 7,
        "question": "What is your supplier's full name and complete address?",
        "explanation": "Include the supplier's full company name, street address, city, state/province, postal code, and country.",
        "fields": ["other_party_name", "other_party_address", "other_party_city", "other_party_state", "other_party_pincode", "other_party_country"]
    },
    {
        "id": 8,
        "question": "Which country's laws should govern this agreement, and which courts will resolve any disputes?",
        "explanation": "For example: 'Laws of Karnataka, India' and 'Courts of Bangalore, Karnataka'. This determines the legal jurisdiction.",
        "fields": ["laws_which_apply", "courts_which_resolve"]
    }
]

# Questions from documents - Supplier role
SUPPLIER_QUESTIONS = [
    {
        "id": 1,
        "question": "What is the name and version of your product that you'll provide to the customer for evaluation?",
        "explanation": "Based on the customer's business requirements or use cases, you'll recommend your most suitable product(s) for evaluation.",
        "fields": ["product_to_be_evaluated", "product_version"]
    },
    {
        "id": 2,
        "question": "How many trial licenses will you provide, and what type of licenses?",
        "explanation": "Consider the customer's team size and evaluation scope. License types can be concurrent, named-user, or server licenses.",
        "fields": ["number_of_licenses", "license_type"]
    },
    {
        "id": 3,
        "question": "How many days will the customer need for the evaluation?",
        "explanation": "Generally 30-60 days. We'll suggest 60 days if not specified.",
        "fields": ["period_for_evaluation"]
    },
    {
        "id": 4,
        "question": "When would you like the customer to start the evaluation?",
        "explanation": "Provide a specific date if you know it, or we can use a standard start date.",
        "fields": ["agreement_start_date"]
    },
    {
        "id": 5,
        "question": "Will you charge any fees for this trial? If yes, provide the amount, currency, and payment terms.",
        "explanation": "Most suppliers offer free trials. If you'll charge a fee, specify amount, currency, invoicing method, credit period, and any late payment terms.",
        "fields": ["fees_options", "currency", "amount", "invoicing", "credit_period", "late_payment_charges", "late_payment_percentage", "tax_fees"]
    },
    {
        "id": 6,
        "question": "What is your company or organization's full name and complete address?",
        "explanation": "Include your full company name, street address, city, state/province, postal code, and country.",
        "fields": ["company_name", "company_address", "company_city", "company_state", "company_pincode", "company_country"]
    },
    {
        "id": 7,
        "question": "What is your customer's full name and complete address?",
        "explanation": "Include the customer's full company name, street address, city, state/province, postal code, and country.",
        "fields": ["other_party_name", "other_party_address", "other_party_city", "other_party_state", "other_party_pincode", "other_party_country"]
    },
    {
        "id": 8,
        "question": "Which country's laws should govern this agreement, and which courts will resolve any disputes?",
        "explanation": "For example: 'Laws of Karnataka, India' and 'Courts of Bangalore, Karnataka'. This determines the legal jurisdiction.",
        "fields": ["laws_which_apply", "courts_which_resolve"]
    }
]

# Initialize Perplexity client
@st.cache_resource
def initialize_perplexity_client():
    """Initialize Perplexity API client."""
    try:
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            st.error("PERPLEXITY_API_KEY not found in environment variables!")
            return None
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai"
        )
        return client
    except Exception as e:
        st.error(f"Error initializing Perplexity API: {str(e)}")
        return None

# Initialize client
perplexity_client = initialize_perplexity_client()

def get_ai_conversation_response(user_input, stage, context):
    """Use AI to handle conversation flow and ask questions naturally."""
    try:
        if perplexity_client is None:
            return "I apologize, but I'm having trouble connecting to my AI backend. Please try again later.", None
        
        # Build context
        context_str = json.dumps(context, indent=2)
        
        # Get questions based on role
        questions = BUYER_QUESTIONS if context.get("role") == "buyer" else SUPPLIER_QUESTIONS
        questions_context = json.dumps(questions, indent=2)

        # Get the current question being answered (for data_collection stage)
        current_question_text = ""
        current_question_fields = []
        if stage == "data_collection" and context.get("current_question_index", 0) < len(questions):
            current_q = questions[context.get("current_question_index", 0)]
            current_question_text = current_q["question"]
            current_question_fields = current_q.get("fields", [])

        prompt = f"""
        You are TechLaw25, a friendly and professional legal contract assistant. Your role is to guide users through creating legal agreements in a conversational manner.

        Current Stage: {stage}

        Context:
        {context_str}

        Questions to ask (from documents):
        {questions_context}

        User's Last Response: {user_input}

        Current Question Index: {context.get("current_question_index", 0)}
        Asked Questions (IDs): {context.get("asked_questions", [])}
        Follow-up Count for Current Question: {context.get("follow_up_count", 0)}

        CRITICAL - THE USER IS CURRENTLY ANSWERING THIS QUESTION:
        Question: "{current_question_text}"
        Expected Fields to Extract: {current_question_fields}

        The user's response "{user_input}" is their answer to THIS specific question above.
        Extract the appropriate fields from their answer based on what THIS question asks for.
        Do NOT confuse their answer with any other question.
        
        Your task is to:
        1. Analyze the user's response
        2. Extract relevant information and determine which FIELDS it corresponds to from the questions list
        3. Each question may map to MULTIPLE fields - extract ALL relevant fields from the user's answer
        4. Decide what information is still missing based on the questions
        5. Ask the next appropriate question from the questions list in a natural, conversational tone
        6. Be friendly and professional in your responses
        
        CRITICAL: Only ask questions from the questions list when in the "data_collection" stage.
        For other stages, provide appropriate responses to guide the user to the next stage.
        
        IMPORTANT: You must respond in the following JSON format:
        {{
            "extracted_fields": {{
                "field_name_1": "value_1",
                "field_name_2": "value_2"
            }},
            "missing_fields": ["field_name_3"],
            "response": "Your conversational response to the user",
            "is_complete": false,
            "next_stage": "next_stage or null"
        }}

        For backward compatibility during greeting stage only, you may also use:
        {{
            "extracted_field": "user_name or user_email",
            "extracted_value": "value",
            "response": "...",
            "next_stage": "..."
        }}

        CRITICAL PARSING RULES FOR INDIAN ADDRESSES:
        1. The FIRST word(s) before any address indicators (numbers, "cross", "street", "road", "nagar", "layout") is the company/party NAME
        2. Address indicators to watch for: cross, street, road, nagar, layout, colony, phase, sector, block, main
        3. Indian state names: Karnataka, Maharashtra, Tamil Nadu, Telangana, Kerala, Andhra Pradesh, Gujarat, Rajasthan, etc.
        4. If a state name like "Karnataka", "karnataka", "karnatake" is present, the country is "India"
        5. Indian pincodes are 6 digits (e.g., 560001, 503401)

        EXAMPLE PARSING:
        Input: "munark 5th cross bradhshaws street nehrupuran bangalore karnataka 560001"
        - "munark" = company_name (first token before "5th cross" address indicator)
        - "5th cross bradhshaws street nehrupuran" = company_address
        - "bangalore" = company_city
        - "karnataka" = company_state
        - "560001" = company_pincode
        - "India" = company_country (inferred from Karnataka)

        EXTRACTION EXAMPLES:
        - User: "Acme Corp, 123 Main St, NYC, NY 10001, USA"
          extracted_fields: {{"company_name": "Acme Corp", "company_address": "123 Main St", "company_city": "NYC", "company_state": "NY", "company_pincode": "10001", "company_country": "USA"}}

        - User: "munark 5th cross bradhshaws street, nehrupuran, bangalore, karnataka, 560001"
          extracted_fields: {{"company_name": "munark", "company_address": "5th cross bradhshaws street, nehrupuran", "company_city": "bangalore", "company_state": "karnataka", "company_pincode": "560001", "company_country": "India"}}

        - User: "TechSolutions Pvt Ltd 42 MG Road Koramangala Bangalore Karnataka 560034"
          extracted_fields: {{"company_name": "TechSolutions Pvt Ltd", "company_address": "42 MG Road Koramangala", "company_city": "Bangalore", "company_state": "Karnataka", "company_pincode": "560034", "company_country": "India"}}

        - User: "avinash 3rd cross jp nagar hubbli karnataka 503401"
          extracted_fields: {{"other_party_name": "avinash", "other_party_address": "3rd cross jp nagar", "other_party_city": "hubbli", "other_party_state": "karnataka", "other_party_pincode": "503401", "other_party_country": "India"}}

        - User: "CloudSync Pro version 2.1"
          extracted_fields: {{"product_to_be_evaluated": "CloudSync Pro", "product_version": "2.1"}}

        - User: "5 concurrent licenses"
          extracted_fields: {{"number_of_licenses": "5", "license_type": "concurrent"}}

        - User: "Free trial, no charges"
          extracted_fields: {{"fees_options": "free"}}

        - User: "Laws of Karnataka, India and Courts of Bangalore"
          extracted_fields: {{"laws_which_apply": "Laws of Karnataka, India", "courts_which_resolve": "Courts of Bangalore, Karnataka"}}

        Stages:
        - greeting: Extract name and email from user input. Use "user_name" as extracted_field for name and "user_email" for email. You can extract them one at a time or together. If both are provided in the same message, extract the name first, and set "next_stage": "contract_type". Provide a brief acknowledgment without mentioning any specific contract types, and tell the user to look at the available agreement types shown above their message input. If name or email is missing, ask for the missing information in a friendly way.
        - contract_type: The user will see interactive buttons above for available contract types (currently: evaluation-agreement). Simply acknowledge that they should select one of the agreement types shown in the buttons above. Do NOT mention specific agreement types in your text response. Do NOT ask questions from the questions list.
        - role_selection: Acknowledge that they need to select their role from the available options (Supplier/Buyer). Do NOT ask questions from the questions list.
        - relationship_type: Acknowledge that they need to select the relationship type from the available options (New/Existing). Do NOT ask questions from the questions list.
        - data_collection: Ask questions ONE BY ONE sequentially (8 questions total). Track Current Question Index to know which question to ask next.

          CRITICAL WORKFLOW:
          1. The user's response is their answer to Question #{context.get("current_question_index", 0)} (the question that was just shown to them)
          2. Extract ALL relevant fields from their answer based on that specific question's fields
          3. Acknowledge the answer briefly (e.g., "Thanks! Got it." or "Perfect, noted.")
          4. **DO NOT ask the next question** - the system will automatically show it
          5. Just provide a brief acknowledgment in your "response" field
          6. After question 8 is answered → Set is_complete: true

          RULES:
          - The user is answering the CURRENT question (index {context.get("current_question_index", 0)}), not any other question
          - Accept whatever answer the user provides (even "no" or minimal info)
          - Extract fields based on what the CURRENT question asks for
          - Do NOT confuse their answer with previous or future questions
          - Do NOT ask follow-up questions
          - Do NOT include the next question in your response
          - ONLY provide a brief acknowledgment (1-2 sentences max)
          - The system will automatically display the next question

          Response format: Just a brief acknowledgment like "Thanks! Noted." or "Perfect, got it!"
        - document_generation: Document has been generated.
        
        When all questions from the list have been asked and answered, set "is_complete": true and "next_stage": "document_generation".
        
        Respond ONLY with valid JSON. Do not include any other text.
        """
        
        response = perplexity_client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {
                    "role": "system",
                    "content": "You are TechLaw25, a helpful legal contract assistant. You must respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Parse the JSON response
        try:
            result = json.loads(response.choices[0].message.content)
            return result, None
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response.choices[0].message.content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result, None
            else:
                return None, "Could not parse AI response"
                
    except Exception as e:
        return None, f"Error: {str(e)}"

def send_to_document_api(contract_data):
    """Send contract data to document generation API."""
    try:
        api_url = os.getenv("DOCUMENT_API_URL", "https://qvik.munark.in/api/v1/ai-agreement")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            api_url,
            json=contract_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            return result.get("document_url"), result.get("document_type")
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None, None
            
    except Exception as e:
        st.error(f"Error calling document generation API: {str(e)}")
        return None, None

def display_message(role, content):
    """Display a chat message."""
    with st.chat_message(role):
        st.markdown(content)

def main():
    st.title("⚖️ TechLaw25 - Contract Assistant")
    st.markdown("---")

    # Display chat history
    for message in st.session_state.messages:
        display_message(message["role"], message["content"])

    # Show download buttons if documents are ready
    if st.session_state.get("documents_ready"):
        st.markdown("---")
        st.subheader("📥 Download Your Documents")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.get("pdf_content"):
                st.download_button(
                    label="📄 Download PDF",
                    data=st.session_state.pdf_content,
                    file_name=st.session_state.get("pdf_filename", "agreement.pdf"),
                    mime="application/pdf",
                    use_container_width=True
                )
        with col2:
            if st.session_state.get("word_content"):
                st.download_button(
                    label="📝 Download Word",
                    data=st.session_state.word_content,
                    file_name=st.session_state.get("word_filename", "agreement.docx"),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
        st.markdown("---")

    # Show interactive options based on stage
    show_interactive_options()

    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        display_message("user", prompt)
        
        # Process conversation using AI
        process_conversation_with_ai(prompt)

def show_interactive_options():
    """Show interactive options based on conversation stage."""
    
    if st.session_state.conversation_stage == 'contract_type':
        st.markdown("### Available Agreement Types:")
        if st.button("📄 Evaluation Agreement", key="eval_agreement"):
            handle_contract_type_selection("evaluation-agreement")
    
    elif st.session_state.conversation_stage == 'role_selection':
        st.markdown("### Select Your Role:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏢 Supplier", key="role_supplier", use_container_width=True):
                handle_role_selection("supplier")
            st.caption("The party providing the product/service")
        with col2:
            if st.button("👤 Buyer", key="role_buyer", use_container_width=True):
                handle_role_selection("buyer")
            st.caption("The party receiving the service (customer)")
    
    elif st.session_state.conversation_stage == 'relationship_type':
        st.markdown("### Relationship Type:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🆕 New Relationship", key="rel_new"):
                handle_relationship_selection("New Relationship")
        with col2:
            if st.button("🔄 Existing Relationship", key="rel_existing"):
                handle_relationship_selection("Existing Relationship")

def handle_contract_type_selection(contract_type):
    """Handle contract type selection."""
    st.session_state.contract_list_type = contract_type
    st.session_state.conversation_stage = 'role_selection'
    
    response = f"Great choice! You've selected **{contract_type}**."
    response += "\n\nNow, please define who you are in this agreement:"
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

def handle_role_selection(role):
    """Handle role selection."""
    st.session_state.role = role
    st.session_state.contract_type = role
    st.session_state.conversation_stage = 'relationship_type'
    
    response = f"Perfect! You've selected **{role.capitalize()}** role."
    response += "\n\nIs this a new or existing relationship with the other party?"
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

def handle_relationship_selection(relationship_type):
    """Handle relationship type selection."""
    st.session_state.relationship_type = relationship_type
    st.session_state.conversation_stage = 'data_collection'
    st.session_state.current_question_index = 0  # Reset to first question

    response = f"Excellent! This is a **{relationship_type}**."
    # Format the contract type name nicely (e.g., "evaluation-agreement" -> "Evaluation Agreement")
    contract_type_display = st.session_state.contract_list_type.replace('-', ' ').title()
    response += f"\n\nTo create your **{contract_type_display}**, I'll ask you 8 questions one by one. Please answer each in detail.\n\n"

    # Get questions based on role
    questions = BUYER_QUESTIONS if st.session_state.role == "buyer" else SUPPLIER_QUESTIONS

    # Show ONLY the first question
    first_question = questions[0]
    response += f"**Question 1 of {len(questions)}:**\n\n"
    response += f"**{first_question['question']}**\n\n"
    if first_question.get('explanation'):
        response += f"_{first_question['explanation']}_\n\n"
    response += "Please provide your answer in detail."

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

def extract_name_from_address(text, field_prefix="company"):
    """
    Fallback regex extraction for Indian addresses.
    Extracts name that appears before address indicators.
    """
    import re

    # Address indicators that suggest the address portion is starting
    address_indicators = r'(\d+(?:st|nd|rd|th)?\s*(?:cross|main|floor|street|road|nagar|layout|colony|phase|sector|block)|#?\d+[/-]\d+)'

    result = {}
    text_lower = text.lower()

    # Try to find where address starts (after the name)
    match = re.search(address_indicators, text_lower)

    if match:
        # Everything before the address indicator is likely the name
        name_portion = text[:match.start()].strip()
        if name_portion and len(name_portion) > 1:
            # Clean up the name (remove trailing commas/spaces)
            name_portion = re.sub(r'[,\s]+$', '', name_portion)
            if name_portion:
                result[f"{field_prefix}_name"] = name_portion.title()
                print(f"[REGEX FALLBACK] Extracted {field_prefix}_name: {name_portion.title()}")

    return result

def process_conversation_with_ai(user_input):
    """Process user input using AI."""

    # Track if stage changed to trigger UI refresh
    stage_changed = False

    # HARDCODED: Extract email and name using regex for greeting stage
    if st.session_state.conversation_stage == 'greeting':
        import re
        # Look for email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, user_input)

        if email_match:
            extracted_email = email_match.group()
            # Store email (legitimate or not) if we don't have one yet
            # Validation will happen later before auto-transition
            if not st.session_state.user_email:
                st.session_state.user_email = extracted_email

        # Extract name (simple approach - take first word if no name yet)
        if not st.session_state.user_name:
            # Remove email from input to extract name
            name_text = re.sub(email_pattern, '', user_input)
            # Remove common words
            name_text = re.sub(r'\b(and|my|name|is|email|hi|hello)\b', '', name_text, flags=re.IGNORECASE)
            # Clean up and get first meaningful word
            name_parts = [part.strip() for part in name_text.split() if len(part.strip()) > 1]
            if name_parts:
                st.session_state.user_name = name_parts[0].capitalize()

        # Check if we have both name and email AND email looks legitimate
        if st.session_state.user_name and st.session_state.user_email:
            # Validate the stored email
            stored_email_local = st.session_state.user_email.split('@')[0].lower()
            suspicious_patterns = ['email', 'test', 'user', 'example', 'sample', 'demo', 'fake']
            is_stored_email_legitimate = not any(pattern in stored_email_local for pattern in suspicious_patterns)

            # Only auto-transition if email looks legitimate
            if is_stored_email_legitimate:
                # Transition to contract_type stage immediately
                st.session_state.conversation_stage = 'contract_type'
                stage_changed = True

                # Add response and skip AI processing
                response = f"Thank you, {st.session_state.user_name}! I've got your details (Email: {st.session_state.user_email}). Please select one of the available agreement types from the options shown above."
                st.session_state.messages.append({"role": "assistant", "content": response})
                display_message("assistant", response)
                st.rerun()  # Immediately show the buttons
                return  # Exit early, don't call AI
            # If email looks suspicious, continue to AI so it can ask for confirmation

    # Build context
    context = {
        "user_name": st.session_state.user_name,
        "user_email": st.session_state.user_email,
        "contract_type": st.session_state.contract_type,
        "relationship_type": st.session_state.relationship_type,
        "contract_list_type": st.session_state.contract_list_type,
        "role": st.session_state.role,
        "collected_data": st.session_state.contract_data["questions"],
        "collected_fields": st.session_state.collected_fields,
        "current_question_index": st.session_state.current_question_index,
        "asked_questions": st.session_state.asked_questions,
        "follow_up_count": st.session_state.follow_up_count
    }
    
    # Use AI to handle conversation
    result, error = get_ai_conversation_response(
        user_input,
        st.session_state.conversation_stage,
        context
    )
    
    if error:
        response = f"I encountered an error: {error}. Please try again."
    elif result:
        # Handle greeting stage - extract name and email
        if st.session_state.conversation_stage == 'greeting' and result.get("extracted_field"):
            field_name = result["extracted_field"]
            field_value = result["extracted_value"]

            # Store name and email in session state
            if field_name == "user_name" or field_name == "name":
                st.session_state.user_name = field_value
            elif field_name == "user_email" or field_name == "email":
                st.session_state.user_email = field_value

            # HARDCODED: Automatically transition to contract_type stage if both name and email are present
            if st.session_state.user_name and st.session_state.user_email:
                st.session_state.conversation_stage = 'contract_type'
                stage_changed = True
                # Override AI response with hardcoded message
                result["response"] = f"Thank you, {st.session_state.user_name}! I've got your details. Please select one of the available agreement types from the options shown above."

        # NEW: Extract and store multiple fields from extracted_fields dictionary
        if result.get("extracted_fields"):
            extracted_fields = result["extracted_fields"]

            for field_name, field_value in extracted_fields.items():
                # Store in contract data (only for non-greeting fields)
                if field_name not in ["user_name", "name", "user_email", "email"]:
                    st.session_state.contract_data["questions"][field_name] = field_value

                    # Track collected fields
                    if field_name not in st.session_state.collected_fields:
                        st.session_state.collected_fields.append(field_name)

            # Increment question index after processing answer (only in data_collection stage)
            if st.session_state.conversation_stage == 'data_collection':
                # Get current question before incrementing
                current_idx = st.session_state.current_question_index
                questions = BUYER_QUESTIONS if st.session_state.role == "buyer" else SUPPLIER_QUESTIONS

                # Apply regex fallback for name extraction if AI missed it
                if current_idx < len(questions):
                    current_fields = questions[current_idx].get("fields", [])

                    # Check if company_name should have been extracted but wasn't
                    if "company_name" in current_fields:
                        if not extracted_fields.get("company_name") and not st.session_state.contract_data["questions"].get("company_name"):
                            fallback = extract_name_from_address(user_input, "company")
                            for k, v in fallback.items():
                                if not st.session_state.contract_data["questions"].get(k):
                                    st.session_state.contract_data["questions"][k] = v

                    # Check if other_party_name should have been extracted but wasn't
                    if "other_party_name" in current_fields:
                        if not extracted_fields.get("other_party_name") and not st.session_state.contract_data["questions"].get("other_party_name"):
                            fallback = extract_name_from_address(user_input, "other_party")
                            for k, v in fallback.items():
                                if not st.session_state.contract_data["questions"].get(k):
                                    st.session_state.contract_data["questions"][k] = v

                st.session_state.current_question_index += 1

        # BACKWARD COMPATIBILITY: Extract and store single field value (old format)
        elif result.get("extracted_field") and result.get("extracted_value"):
            field_name = result["extracted_field"]
            field_value = result["extracted_value"]

            # Store in contract data (only for non-greeting fields)
            if field_name not in ["user_name", "name", "user_email", "email"]:
                st.session_state.contract_data["questions"][field_name] = field_value

                # Track collected fields
                if field_name not in st.session_state.collected_fields:
                    st.session_state.collected_fields.append(field_name)

        # Update stage if needed and trigger rerun to show new UI elements
        if result.get("next_stage"):
            st.session_state.conversation_stage = result["next_stage"]
            stage_changed = True

        # Check if data collection is complete
        if result.get("is_complete"):
            # Update contract data with metadata
            st.session_state.contract_data["contract_type"] = st.session_state.contract_type
            st.session_state.contract_data["relationship_type"] = st.session_state.relationship_type
            st.session_state.contract_data["contract_list_type"] = st.session_state.contract_list_type

            response = result.get("response", "Excellent! I've collected all the necessary information.")
            response += "\n\nLet me prepare your contract document..."
            response += "\n\nPlease wait while I generate your Evaluation Agreement..."

            # Enrich data before generating document
            enrich_contract_data()

            # Fallback: Calculate end date if AI didn't
            calculate_end_date_fallback()

            # Apply deterministic rules as final fallback
            deterministic_enrichment()

            # Generate document
            generate_document()

            # Add download info to response
            if st.session_state.get("documents_ready"):
                response += f"\n\n✅ **Your document is ready!**"
                response += "\n\n👇 Use the download buttons below to get your documents."
                response += "\n\nIs there anything else I can help you with?"
            else:
                response += "\n\n❌ There was an error generating your document. Please try again."
        else:
            # Get AI's acknowledgment response
            response = result.get("response", "Thank you for your response.")

            # PYTHON-CONTROLLED QUESTION PROGRESSION
            # After AI acknowledges, explicitly add the next question from Python
            if st.session_state.conversation_stage == 'data_collection':
                current_idx = st.session_state.current_question_index
                questions = BUYER_QUESTIONS if st.session_state.role == "buyer" else SUPPLIER_QUESTIONS

                # Check if there's a next question to ask
                if current_idx < len(questions):
                    next_question = questions[current_idx]

                    # Append next question to response
                    response += f"\n\n**Question {current_idx + 1} of {len(questions)}:**\n\n"
                    response += f"**{next_question['question']}**\n\n"

                    if next_question.get('explanation'):
                        response += f"_{next_question['explanation']}_\n\n"

                    response += "Please provide your answer in detail."

                # If all 8 questions answered, mark as complete
                elif current_idx >= len(questions):
                    # Update contract data with metadata
                    st.session_state.contract_data["contract_type"] = st.session_state.contract_type
                    st.session_state.contract_data["relationship_type"] = st.session_state.relationship_type
                    st.session_state.contract_data["contract_list_type"] = st.session_state.contract_list_type

                    response += "\n\nExcellent! I've collected all the necessary information."
                    response += "\n\n🔍 Reviewing and finalizing details..."

                    # Enrich data before generating document
                    enrich_contract_data()

                    # Fallback: Calculate end date if AI didn't
                    calculate_end_date_fallback()

                    # Apply deterministic rules as final fallback
                    deterministic_enrichment()

                    response += "\n\n📝 Generating your Evaluation Agreement..."

                    # Generate document
                    generate_document()

                    # Add download info to response
                    if st.session_state.get("documents_ready"):
                        response += f"\n\n✅ **Your document is ready!**"
                        response += "\n\n👇 Use the download buttons below to get your documents."
                        response += "\n\nIs there anything else I can help you with?"
                    else:
                        response += "\n\n❌ There was an error generating your document. Please try again."
    else:
        response = "I apologize, but I encountered an error processing your response. Please try again."
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    display_message("assistant", response)

    # Trigger rerun if stage changed to show new UI elements (buttons)
    if 'stage_changed' in locals() and stage_changed:
        st.rerun()

def calculate_end_date_fallback():
    """Fallback: Calculate end date using Python if AI didn't do it."""
    data = st.session_state.contract_data["questions"]

    # Skip if already calculated
    if data.get("agreement_end_date"):
        print("[FALLBACK] End date already set, skipping")
        return

    start_date_str = data.get("agreement_start_date", "")
    period_str = data.get("period_for_evaluation", "")

    if not start_date_str or not period_str:
        print(f"[FALLBACK] Missing data - start: '{start_date_str}', period: '{period_str}'")
        return

    # Extract days
    days_match = re.search(r'(\d+)', period_str)
    if not days_match:
        print(f"[FALLBACK] Could not extract days from: {period_str}")
        return
    days = int(days_match.group(1))

    # Parse start date
    try:
        # Clean up date string (remove "st", "nd", "rd", "th")
        clean_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', start_date_str)

        start_date = None
        for fmt in ["%B %d, %Y", "%B %d %Y", "%B %d", "%b %d, %Y", "%b %d"]:
            try:
                start_date = datetime.strptime(clean_date.strip(), fmt)
                if "%Y" not in fmt:
                    start_date = start_date.replace(year=2026)
                break
            except ValueError:
                continue

        if start_date:
            end_date = start_date + timedelta(days=days)
            data["agreement_end_date"] = end_date.strftime("%B %d, %Y")
            print(f"[FALLBACK] Calculated end date: {data['agreement_end_date']} (from {start_date_str} + {days} days)")
        else:
            print(f"[FALLBACK] Could not parse date: {start_date_str}")
    except Exception as e:
        print(f"[FALLBACK] Error calculating end date: {e}")

def deterministic_enrichment():
    """
    Apply deterministic rules to fill missing fields.
    Runs AFTER AI enrichment as a safety net.
    """
    data = st.session_state.contract_data["questions"]

    # Indian state to country mapping (handles typos like "karnatake")
    INDIAN_STATES = {
        "karnataka": "India", "karnatake": "India", "maharashtra": "India",
        "tamil nadu": "India", "tamilnadu": "India", "telangana": "India",
        "andhra pradesh": "India", "kerala": "India", "gujarat": "India",
        "rajasthan": "India", "uttar pradesh": "India", "madhya pradesh": "India",
        "west bengal": "India", "bihar": "India", "punjab": "India",
        "haryana": "India", "odisha": "India", "delhi": "India", "goa": "India"
    }

    # Company country from state
    if data.get("company_state") and not data.get("company_country"):
        state_lower = data["company_state"].lower().strip()
        if state_lower in INDIAN_STATES:
            data["company_country"] = "India"
            print(f"[DETERMINISTIC] Set company_country to India from state {data['company_state']}")

    # Other party country from state
    if data.get("other_party_state") and not data.get("other_party_country"):
        state_lower = data["other_party_state"].lower().strip()
        if state_lower in INDIAN_STATES:
            data["other_party_country"] = "India"
            print(f"[DETERMINISTIC] Set other_party_country to India from state {data['other_party_state']}")

    # Normalize state name capitalization and fix typos
    for field in ["company_state", "other_party_state"]:
        if data.get(field):
            normalized = data[field].lower().replace("karnatake", "karnataka").title()
            data[field] = normalized

    # Normalize country capitalization
    for field in ["company_country", "other_party_country"]:
        if data.get(field):
            data[field] = data[field].title()

def enrich_contract_data():
    """
    AI-powered enrichment: Reviews all collected contract data and intelligently
    fills missing fields through inference and parsing.

    Updates st.session_state.contract_data["questions"] in place.
    """
    print("\n>>> enrich_contract_data() called")  # DEBUG
    try:
        # Get current contract data
        current_data = st.session_state.contract_data["questions"]

        # Build enrichment prompt
        prompt = f"""
        You are a data enrichment assistant. Review the following contract data collected from 8 questions.
        Your task is to intelligently infer and fill missing fields based on the data provided.

        CURRENT DATA (28 fields):
        {json.dumps(current_data, indent=2)}

        ENRICHMENT RULES:

        1. **Geographic Inference**:
           - If company_city is "Bangalore" or "bangalore" → set company_state to "Karnataka" and company_country to "India"
           - If company_state is "Karnataka" or "karnataka" or "karnatake" → set company_country to "India"
           - Apply same logic to other_party_* fields
           - Normalize spelling/capitalization (e.g., "karnatake" → "Karnataka")

        2. **Compound Answer Parsing**:
           - If product_to_be_evaluated contains version info (e.g., "apti and production", "X version Y"):
             * Extract product name → product_to_be_evaluated
             * Extract version → product_version
           - Look for patterns: "X and Y", "X version Y", "X Y.Z"

        3. **Jurisdiction Normalization**:
           - If laws_which_apply is just a state/region (e.g., "Karnataka"):
             * Expand to "Laws of Karnataka, India"
           - If courts_which_resolve is just a state/region:
             * Expand to "Courts of [city], Karnataka, India" or "Courts of Karnataka, India"

        4. **Address Completion**:
           - If state or country are empty but can be inferred from city, fill them
           - Ensure proper capitalization

        5. **End Date Calculation**:
           - If agreement_start_date and period_for_evaluation are provided, calculate agreement_end_date
           - Extract the number of days from period_for_evaluation (e.g., "60 days" → 60)
           - Add those days to agreement_start_date to get agreement_end_date
           - Example: start="February 1, 2026" + period="60 days" → end="April 2, 2026"
           - Use the same date format as the start date

        6. **DO NOT**:
           - Make up data that cannot be inferred
           - Change data that is already correct
           - Fill fields with guesses if no logical inference exists

        Return ONLY the enriched fields (fields that changed or were filled). Use this JSON format:
        {{
            "enriched_fields": {{
                "field_name": "new_value",
                ...
            }},
            "notes": "Brief summary of what was inferred"
        }}
        """

        # Call Perplexity AI
        perplexity_client = initialize_perplexity_client()
        if perplexity_client is None:
            print("Warning: Could not initialize AI for enrichment. Skipping enrichment step.")
            return

        response = perplexity_client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {
                    "role": "system",
                    "content": "You are a data enrichment assistant. Respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temperature for more deterministic inference
            max_tokens=1000
        )

        # Parse response
        response_text = response.choices[0].message.content.strip()

        # DEBUG: Log raw AI response
        print("\n" + "="*50)
        print("PERPLEXITY AI RAW RESPONSE:")
        print("="*50)
        print(response_text)
        print("="*50 + "\n")

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())

            # Apply enriched fields
            if result.get("enriched_fields"):
                enriched = result["enriched_fields"]

                for field_name, field_value in enriched.items():
                    if field_name in st.session_state.contract_data["questions"]:
                        # Update the field
                        st.session_state.contract_data["questions"][field_name] = field_value

                # Log enrichment
                print("\n" + "="*50)
                print("DATA ENRICHMENT APPLIED:")
                print("="*50)
                print(json.dumps(enriched, indent=2))
                if result.get("notes"):
                    print(f"\nNotes: {result['notes']}")
                print("="*50 + "\n")

    except Exception as e:
        print(f"Warning: Enrichment step failed: {str(e)}")
        print("Proceeding with unenriched data.")
        # Don't fail document generation if enrichment fails

def generate_document():
    """Generate document by calling the API."""
    try:
        # Prepare the final data structure
        final_data = {
            "contract_type": st.session_state.contract_type,
            "relationship_type": st.session_state.relationship_type,
            "contract_list_type": st.session_state.contract_list_type,
            "questions": st.session_state.contract_data["questions"]
        }

        # Print the final JSON to console/logs
        print("\n" + "="*50)
        print("FINAL REQUEST TO DOCUMENT API:")
        print("="*50)
        print(json.dumps(final_data, indent=2))
        print("="*50 + "\n")

        base_url = "https://qvik.munark.in/api/v1"
        headers = {"Content-Type": "application/json"}

        # Step 1: Create agreement with loading spinner
        with st.spinner("Creating agreement..."):
            response = requests.post(
                f"{base_url}/ai-agreement",
                json=final_data,
                headers=headers,
                timeout=30
            )

            if response.status_code not in [200, 201]:
                st.error(f"API Error: {response.status_code} - {response.text}")
                print(f"API Error: {response.status_code} - {response.text}")
                return

            result = response.json()
            agreement_id = result.get("id")
            print(f"Agreement created with ID: {agreement_id}")

        # Step 2: Fetch PDF and Word documents
        with st.spinner("Generating documents..."):
            # Fetch PDF
            pdf_response = requests.get(
                f"{base_url}/ai-agreement/{agreement_id}/pdf",
                timeout=30
            )
            # Fetch Word
            word_response = requests.get(
                f"{base_url}/ai-agreement/{agreement_id}/word",
                timeout=30
            )

        # Store in session state for download buttons
        if pdf_response.status_code == 200:
            st.session_state.pdf_content = pdf_response.content
            st.session_state.pdf_filename = f"agreement-{agreement_id}.pdf"
            print(f"PDF fetched: {len(pdf_response.content)} bytes")

        if word_response.status_code == 200:
            st.session_state.word_content = word_response.content
            st.session_state.word_filename = f"agreement-{agreement_id}.docx"
            print(f"Word fetched: {len(word_response.content)} bytes")

        st.session_state.documents_ready = True
        st.success("Documents generated successfully!")
        st.rerun()  # Rerun to show download buttons

    except Exception as e:
        st.error(f"Error generating document: {str(e)}")
        print(f"Error generating document: {str(e)}")

def reset_conversation():
    """Reset the conversation to start over."""
    st.session_state.messages = []
    st.session_state.user_name = None
    st.session_state.user_email = None
    st.session_state.conversation_stage = 'greeting'
    st.session_state.contract_type = None
    st.session_state.relationship_type = None
    st.session_state.contract_list_type = None
    st.session_state.role = None
    st.session_state.collected_fields = []
    st.session_state.current_question_index = 0
    st.session_state.contract_data = {
        "contract_type": "",
        "relationship_type": "",
        "contract_list_type": "",
        "questions": {
            "company_name": "",
            "company_address": "",
            "company_city": "",
            "company_state": "",
            "company_pincode": "",
            "company_country": "",
            "other_party_name": "",
            "other_party_address": "",
            "other_party_city": "",
            "other_party_state": "",
            "other_party_pincode": "",
            "other_party_country": "",
            "product_to_be_evaluated": "",
            "product_version": "",
            "number_of_licenses": "",
            "license_type": "",
            "period_for_evaluation": "",
            "fees_options": "",
            "currency": "",
            "amount": "",
            "invoicing": "",
            "credit_period": "",
            "late_payment_charges": "",
            "late_payment_percentage": "",
            "tax_fees": "",
            "agreement_start_date": "",
            "agreement_end_date": "",
            "laws_which_apply": "",
            "courts_which_resolve": ""
        }
    }
    st.session_state.document_url = None
    st.session_state.documents_ready = False
    st.session_state.pdf_content = None
    st.session_state.word_content = None
    st.session_state.pdf_filename = None
    st.session_state.word_filename = None

# Sidebar removed - cleaner interface without status display

# Initial greeting
if not st.session_state.messages:
    greeting = "Hi TechLaw25 here. Please provide your name and email id to get started."
    st.session_state.messages.append({"role": "assistant", "content": greeting})

# Run the main function
if __name__ == "__main__":
    main()
