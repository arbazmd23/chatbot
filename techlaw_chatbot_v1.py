import streamlit as st
import json
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google import genai
import requests

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="TechLaw25 - Contract Assistant",
    page_icon="⚖️",
    layout="wide"
)

# ============================================================
# CONSTANTS
# ============================================================

STEPS = {
    1: "Create Account",
    2: "Your Role",
    3: "Party Details",
    4: "Select Contract",
    5: "Q&A",
    6: "Payment & Download",
}

CONTRACT_TYPES = [
    {"id": "evaluation-agreement", "name": "Evaluation Agreement", "available": True,
     "description": "For trying out software/services before purchase"},
    {"id": "services-quick", "name": "Services Agreement – Quick", "available": False,
     "description": "Simple services contract for straightforward engagements"},
    {"id": "services-regular", "name": "Services Agreement – Regular", "available": False,
     "description": "Standard services contract with comprehensive terms"},
    {"id": "services-super", "name": "Services Agreement – Super", "available": False,
     "description": "Enterprise-grade services contract with full protections"},
    {"id": "nda", "name": "Confidentiality & Non-Disclosure Agreement", "available": False,
     "description": "For protecting sensitive and confidential information"},
    {"id": "poc", "name": "Proof of Concept Agreement", "available": False,
     "description": "For POC/pilot projects before full commitment"},
    {"id": "software-license", "name": "Software License", "available": False,
     "description": "For software licensing terms and conditions"},
    {"id": "sow", "name": "Statement of Work", "available": False,
     "description": "For specific work orders and deliverables"},
    {"id": "term-sheet", "name": "Term Sheet", "available": False,
     "description": "Summary of key commercial terms"},
    {"id": "loi", "name": "Letter of Intent", "available": False,
     "description": "Expression of interest before formal agreement"},
    {"id": "teaming", "name": "Teaming / Collaboration Agreement", "available": False,
     "description": "For collaborative partnerships and joint ventures"},
]

# Questions from documents - Buyer role (Evaluation Agreement)
BUYER_QUESTIONS = [
    {
        "id": 1,
        "category": "Product to be evaluated",
        "question": "Do you know the name and other details of supplier's product you plan to evaluate?",
        "explanation": "Based on your business requirements or use cases, suppliers recommend their most suitable product(s) for you to evaluate. Suppliers will give trial license for their product.\n\nIf you know the details, you can select Yes and include them in the text box given here. If you don't know, select No or IDK.",
        "fields": ["product_to_be_evaluated", "product_version"],
        "input_type": "product",
    },
    {
        "id": 2,
        "category": "Product to be evaluated",
        "question": "How many trial licenses will you need?",
        "explanation": "This number depends on your business or use case. We suggest you consider the team size who will do the evaluation of the product and accordingly decide on the number.\n\nIf you know the number, you can select Yes and include them in the text box given here. If you don't know, select No or IDK.",
        "fields": ["number_of_licenses", "license_type"],
        "input_type": "licenses",
    },
    {
        "id": 3,
        "category": "Duration",
        "question": "Do you know how many days you will need for this product evaluation?",
        "explanation": "Generally, the user or customer will need 30 to 60 days. We will keep 60 days in our draft.\n\nIf you need lesser or longer period, you can select Yes and enter the duration in the text box given here.\n\nIf you are not sure, you can select No or IDK.",
        "fields": ["period_for_evaluation"],
        "input_type": "duration",
    },
    {
        "id": 4,
        "category": "Duration",
        "question": "Do you know when you want to start the evaluation?",
        "explanation": "If you know the date, you can select Yes and enter the date.\n\nIf you don't know, select No or IDK.",
        "fields": ["agreement_start_date"],
        "input_type": "date",
    },
    {
        "id": 5,
        "category": "Commercials",
        "question": "Do you pay for this trial license?",
        "explanation": "It's a market practice for suppliers to offer trial license for free of cost. Suppliers may insist on nominal cost. We suggest you push back and ask for free of cost trial license.\n\nIf you are paying any fee, then you can select Yes and enter the details in the text box given here.\n\nIf you are not paying, select No. If you are not sure, you can select IDK.",
        "fields": ["fees_options", "currency", "amount", "invoicing", "credit_period", "late_payment_charges", "late_payment_percentage", "tax_fees"],
        "input_type": "fees",
    },
    {
        "id": 6,
        "category": "Parties details",
        "question": "Do you know your company or organization's full name and address?",
        "explanation": "If you know the details, you can select Yes and enter the details. If you don't know, select No or IDK.",
        "fields": ["company_name", "company_address", "company_city", "company_state", "company_pincode", "company_country"],
        "input_type": "address",
        "address_prefix": "company",
    },
    {
        "id": 7,
        "category": "Parties details",
        "question": "Do you know your supplier's full name and address?",
        "explanation": "If you know the details, you can select Yes and enter the details. If you don't know, select No or IDK.",
        "fields": ["other_party_name", "other_party_address", "other_party_city", "other_party_state", "other_party_pincode", "other_party_country"],
        "input_type": "address",
        "address_prefix": "other_party",
    },
    {
        "id": 8,
        "category": "Jurisdiction",
        "question": "Which country's laws should govern this agreement, and which courts will resolve any disputes?",
        "explanation": "This determines the legal jurisdiction for your contract. For example: 'Laws of Karnataka, India' and 'Courts of Bangalore, Karnataka'.\n\nThis is important for determining where any legal disputes would be resolved.",
        "fields": ["laws_which_apply", "courts_which_resolve"],
        "input_type": "jurisdiction",
    },
]

# Questions from documents - Supplier role (Evaluation Agreement)
SUPPLIER_QUESTIONS = [
    {
        "id": 1,
        "category": "Product to be evaluated",
        "question": "Do you know the name and other details of your product you plan to give to your customer for evaluation purpose?",
        "explanation": "Based on customer's business requirements or use cases, you will recommend your most suitable product(s) for customer to evaluate. You will give trial license for that product.\n\nIf you know the details, you can select Yes and enter the details in the text box given here. If you don't know, select No or IDK.",
        "fields": ["product_to_be_evaluated", "product_version"],
        "input_type": "product",
    },
    {
        "id": 2,
        "category": "Product to be evaluated",
        "question": "How many trial licenses will you give?",
        "explanation": "This number depends on customer's business or use case. We suggest you consider the customer's team size who will do the evaluation of the product and accordingly decide on the number.\n\nIf you know the number, you can select Yes and enter the details in the text box given here.\n\nIf you don't know, select No or IDK.",
        "fields": ["number_of_licenses", "license_type"],
        "input_type": "licenses",
    },
    {
        "id": 3,
        "category": "Duration",
        "question": "Do you know how many days the customer will need for this product evaluation?",
        "explanation": "Generally, the user or customer will need 30 to 60 days. We will keep 60 days in our draft.\n\nIf you want lesser or longer period, you can select Yes and then enter the duration in the text box given here.\n\nIf you are not sure, you can select No or IDK.",
        "fields": ["period_for_evaluation"],
        "input_type": "duration",
    },
    {
        "id": 4,
        "category": "Duration",
        "question": "Do you know when the customer wants to start the evaluation?",
        "explanation": "If you know the date, you can select Yes and enter the date.\n\nIf you don't know, select No or IDK.",
        "fields": ["agreement_start_date"],
        "input_type": "date",
    },
    {
        "id": 5,
        "category": "Commercials",
        "question": "Do you charge any fee for this trial license?",
        "explanation": "It's a market practice for suppliers (like you) to offer trial licenses for free of cost. Very few suppliers insist on nominal cost. We suggest you not push hard on this.\n\nIf you are charging any fee, then you can select Yes and enter the details in the text box given here.\n\nIf you are not charging, select No. If you are not sure, select IDK.",
        "fields": ["fees_options", "currency", "amount", "invoicing", "credit_period", "late_payment_charges", "late_payment_percentage", "tax_fees"],
        "input_type": "fees",
    },
    {
        "id": 6,
        "category": "Parties details",
        "question": "Do you know your company or organization's full name and address?",
        "explanation": "If you know the details, you can select Yes and enter the details. If you don't know, select No or IDK.",
        "fields": ["company_name", "company_address", "company_city", "company_state", "company_pincode", "company_country"],
        "input_type": "address",
        "address_prefix": "company",
    },
    {
        "id": 7,
        "category": "Parties details",
        "question": "Do you know your customer's full name and address?",
        "explanation": "If you know the details, you can select Yes and enter the details. If you don't know, select No or IDK.",
        "fields": ["other_party_name", "other_party_address", "other_party_city", "other_party_state", "other_party_pincode", "other_party_country"],
        "input_type": "address",
        "address_prefix": "other_party",
    },
    {
        "id": 8,
        "category": "Jurisdiction",
        "question": "Which country's laws should govern this agreement, and which courts will resolve any disputes?",
        "explanation": "This determines the legal jurisdiction for your contract. For example: 'Laws of Karnataka, India' and 'Courts of Bangalore, Karnataka'.\n\nThis is important for determining where any legal disputes would be resolved.",
        "fields": ["laws_which_apply", "courts_which_resolve"],
        "input_type": "jurisdiction",
    },
]

RECOMMENDATION_RULES = {
    "evaluation-agreement": {
        "keywords": ["trial", "evaluate", "test", "demo", "pilot", "poc", "try", "assess"],
        "description": "For trying out software/services before purchase"
    },
    "nda": {
        "keywords": ["confidential", "secret", "protect", "share", "nda", "non-disclosure"],
        "description": "For protecting sensitive information"
    },
    "services-regular": {
        "keywords": ["service", "support", "maintain", "manage", "outsource", "it services"],
        "description": "For ongoing IT service relationships"
    },
    "software-license": {
        "keywords": ["license", "software", "subscription", "saas", "product"],
        "description": "For software licensing terms"
    },
    "sow": {
        "keywords": ["work", "project", "deliverable", "task", "scope"],
        "description": "For specific work orders and deliverables"
    },
}

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

if 'current_step' not in st.session_state:
    st.session_state.current_step = 1

if 'user_name' not in st.session_state:
    st.session_state.user_name = None

if 'user_email' not in st.session_state:
    st.session_state.user_email = None

if 'role' not in st.session_state:
    st.session_state.role = None

if 'contract_type' not in st.session_state:
    st.session_state.contract_type = None

if 'contract_list_type' not in st.session_state:
    st.session_state.contract_list_type = None

if 'relationship_type' not in st.session_state:
    st.session_state.relationship_type = "New Relationship"

if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0

if 'show_input_for_question' not in st.session_state:
    st.session_state.show_input_for_question = None

if 'payment_complete' not in st.session_state:
    st.session_state.payment_complete = False

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

if 'account_created' not in st.session_state:
    st.session_state.account_created = False

if 'contract_data' not in st.session_state:
    st.session_state.contract_data = {
        "contract_type": "",
        "relationship_type": "New Relationship",
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
            "courts_which_resolve": "",
        }
    }

# ============================================================
# GEMINI CLIENT (UNCHANGED)
# ============================================================

@st.cache_resource
def initialize_gemini_client():
    """Initialize Gemini API client with Google AI Studio."""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("GEMINI_API_KEY not found in environment variables!")
            return None
        client = genai.Client(api_key=api_key)
        return client
    except Exception as e:
        st.error(f"Error initializing Gemini API: {str(e)}")
        return None

gemini_client = initialize_gemini_client()

# ============================================================
# BACKEND FUNCTIONS (COPIED UNCHANGED FROM techlaw_chatbot.py)
# ============================================================

def extract_name_from_address(text, field_prefix="company"):
    """Fallback regex extraction for Indian addresses."""
    address_indicators = r'(\d+(?:st|nd|rd|th)?\s*(?:cross|main|floor|street|road|nagar|layout|colony|phase|sector|block)|#?\d+[/-]\d+)'
    result = {}
    text_lower = text.lower()
    match = re.search(address_indicators, text_lower)
    if match:
        name_portion = text[:match.start()].strip()
        if name_portion and len(name_portion) > 1:
            name_portion = re.sub(r'[,\s]+$', '', name_portion)
            if name_portion:
                result[f"{field_prefix}_name"] = name_portion.title()
    return result


def calculate_end_date_fallback():
    """Fallback: Calculate end date using Python if AI didn't do it."""
    data = st.session_state.contract_data["questions"]
    if data.get("agreement_end_date"):
        return
    start_date_str = data.get("agreement_start_date", "")
    period_str = data.get("period_for_evaluation", "")
    if not start_date_str or not period_str:
        return
    days_match = re.search(r'(\d+)', period_str)
    if not days_match:
        return
    days = int(days_match.group(1))
    try:
        clean_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', start_date_str)
        start_date = None
        for fmt in ["%d-%b-%Y", "%d-%B-%Y", "%B %d, %Y", "%B %d %Y", "%B %d", "%b %d, %Y", "%b %d", "%Y-%m-%d"]:
            try:
                start_date = datetime.strptime(clean_date.strip(), fmt)
                if "%Y" not in fmt:
                    start_date = start_date.replace(year=datetime.now().year)
                break
            except ValueError:
                continue
        if start_date:
            end_date = start_date + timedelta(days=days)
            data["agreement_end_date"] = end_date.strftime("%d-%b-%Y")
    except Exception as e:
        print(f"[FALLBACK] Error calculating end date: {e}")


def apply_extraction_safety_net(original_user_inputs=None):
    """Catch any data the AI missed using regex patterns."""
    data = st.session_state.contract_data["questions"]
    for prefix in ['company', 'other_party']:
        pincode_field = f'{prefix}_pincode'
        address_field = f'{prefix}_address'
        city_field = f'{prefix}_city'
        state_field = f'{prefix}_state'
        if not data.get(pincode_field):
            full_text = ' '.join(filter(None, [
                data.get(address_field, ''),
                data.get(city_field, ''),
                data.get(state_field, '')
            ]))
            match = re.search(r'\b(\d{2,6})\b', full_text)
            if match:
                data[pincode_field] = match.group(1)

    if data.get('fees_options') in ['yes', 'paid', 'Yes', 'Paid']:
        if not data.get('amount') and original_user_inputs:
            fees_input = original_user_inputs.get('fees', '')
            amount_match = re.search(r'(\d+(?:\.\d{2})?)', fees_input)
            if amount_match:
                data['amount'] = amount_match.group(1)
            if not data.get('currency'):
                currency_match = re.search(r'(USD|INR|EUR|GBP|dollars?|rupees?|\$|₹|€|£)', fees_input, re.I)
                if currency_match:
                    currency = currency_match.group(1).upper()
                    if 'DOLLAR' in currency or currency == '$':
                        currency = 'USD'
                    elif 'RUPEE' in currency or currency == '₹':
                        currency = 'INR'
                    elif currency == '€':
                        currency = 'EUR'
                    elif currency == '£':
                        currency = 'GBP'
                    data['currency'] = currency

    if data.get('fees_options'):
        fees_val = data['fees_options'].lower().strip()
        if fees_val in ['free', 'no', 'none', 'no fees', 'no charges', 'complimentary', 'zero']:
            data['fees_options'] = 'no'
        elif fees_val in ['yes', 'paid', 'charged', 'payable'] or data.get('amount'):
            data['fees_options'] = 'yes'

    period = data.get('period_for_evaluation', '')
    if period:
        period_stripped = period.strip()
        if period_stripped.isdigit():
            data['period_for_evaluation'] = f"{period_stripped} days"

    return data


def deterministic_enrichment():
    """Apply deterministic rules to fill missing fields."""
    data = st.session_state.contract_data["questions"]
    INDIAN_STATES = {
        "karnataka": "India", "karnatake": "India", "maharashtra": "India",
        "tamil nadu": "India", "tamilnadu": "India", "telangana": "India",
        "andhra pradesh": "India", "kerala": "India", "gujarat": "India",
        "rajasthan": "India", "uttar pradesh": "India", "madhya pradesh": "India",
        "west bengal": "India", "bihar": "India", "punjab": "India",
        "haryana": "India", "odisha": "India", "delhi": "India", "goa": "India"
    }
    INDIAN_CITIES = {
        "mumbai": "Maharashtra", "navi mumbai": "Maharashtra", "vashi": "Maharashtra", "thane": "Maharashtra", "pune": "Maharashtra",
        "bangalore": "Karnataka", "bengaluru": "Karnataka", "koramangala": "Karnataka", "whitefield": "Karnataka", "electronic city": "Karnataka",
        "chennai": "Tamil Nadu", "hyderabad": "Telangana", "kolkata": "West Bengal", "delhi": "Delhi", "new delhi": "Delhi",
        "gurgaon": "Haryana", "gurugram": "Haryana", "noida": "Uttar Pradesh", "faridabad": "Haryana",
        "ahmedabad": "Gujarat", "jaipur": "Rajasthan", "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh",
        "hubbli": "Karnataka", "hubli": "Karnataka", "mysore": "Karnataka", "mysuru": "Karnataka"
    }
    if data.get("company_state") and not data.get("company_country"):
        state_lower = data["company_state"].lower().strip()
        if state_lower in INDIAN_STATES:
            data["company_country"] = "India"
    if data.get("other_party_state") and not data.get("other_party_country"):
        state_lower = data["other_party_state"].lower().strip()
        if state_lower in INDIAN_STATES:
            data["other_party_country"] = "India"
    for prefix in ['company', 'other_party']:
        city_field = f'{prefix}_city'
        state_field = f'{prefix}_state'
        country_field = f'{prefix}_country'
        if data.get(city_field) and not data.get(state_field):
            city_lower = data[city_field].lower().strip()
            if city_lower in INDIAN_CITIES:
                data[state_field] = INDIAN_CITIES[city_lower]
                data[country_field] = "India"
    for field in ["company_state", "other_party_state"]:
        if data.get(field):
            normalized = data[field].lower().replace("karnatake", "karnataka").title()
            data[field] = normalized
    for field in ["company_country", "other_party_country"]:
        if data.get(field):
            data[field] = data[field].title()


def enrich_contract_data():
    """AI-powered enrichment: Reviews collected contract data and fills missing fields."""
    try:
        current_data = st.session_state.contract_data["questions"]
        prompt = f"""
        You are a data enrichment assistant. Review the following contract data collected from 8 questions.
        Your task is to intelligently infer and fill missing fields based on the data provided.

        CURRENT DATA (28 fields):
        {json.dumps(current_data, indent=2)}

        ENRICHMENT RULES:
        1. **Geographic Inference**: If company_city is "Bangalore" → set company_state to "Karnataka" and company_country to "India". Apply same logic to other_party_* fields.
        2. **Compound Answer Parsing**: If product_to_be_evaluated contains version info, split them.
        3. **Jurisdiction Normalization**: If laws_which_apply is just a state (e.g., "Karnataka") → expand to "Laws of Karnataka, India".
        4. **Address Completion**: If state or country are empty but can be inferred from city, fill them.
        5. **End Date Calculation**: If agreement_start_date and period_for_evaluation are provided, calculate agreement_end_date. Use dd-MMM-yyyy format (e.g., "01-Feb-2026").
        6. **Pincode Validation**: ANY number at the end of an address should be treated as pincode.
        7. **Fees Field Validation**: Normalize fees_options to "yes" or "no".
        8. **Metro City Normalization**: Vashi→Maharashtra, Koramangala→Karnataka, etc.
        9. **DO NOT**: Make up data that cannot be inferred, change correct data, or fill fields with guesses.

        Return ONLY the enriched fields:
        {{
            "enriched_fields": {{
                "field_name": "new_value"
            }},
            "notes": "Brief summary of what was inferred"
        }}
        """
        if gemini_client is None:
            return
        full_prompt = f"You are a data enrichment assistant. Respond with valid JSON only.\n\n{prompt}"
        response = gemini_client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=full_prompt
        )
        response_text = response.text.strip()
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            if result.get("enriched_fields"):
                enriched = result["enriched_fields"]
                for field_name, field_value in enriched.items():
                    if field_name in st.session_state.contract_data["questions"]:
                        st.session_state.contract_data["questions"][field_name] = field_value
    except Exception as e:
        print(f"Warning: Enrichment step failed: {str(e)}")


def swap_fields_for_buyer_role():
    """Swap company_* and other_party_* fields when user is BUYER."""
    if st.session_state.contract_type != "buyer":
        return
    data = st.session_state.contract_data["questions"]
    swap_pairs = [
        ("company_name", "other_party_name"),
        ("company_address", "other_party_address"),
        ("company_city", "other_party_city"),
        ("company_state", "other_party_state"),
        ("company_pincode", "other_party_pincode"),
        ("company_country", "other_party_country"),
    ]
    for field1, field2 in swap_pairs:
        temp = data.get(field1, "")
        data[field1] = data.get(field2, "")
        data[field2] = temp


def generate_document():
    """Generate document by calling the API."""
    try:
        swap_fields_for_buyer_role()
        final_data = {
            "contract_type": st.session_state.contract_type,
            "relationship_type": st.session_state.relationship_type,
            "contract_list_type": st.session_state.contract_list_type,
            "questions": st.session_state.contract_data["questions"]
        }
        print("\n" + "=" * 50)
        print("FINAL REQUEST TO DOCUMENT API:")
        print("=" * 50)
        print(json.dumps(final_data, indent=2))
        print("=" * 50 + "\n")

        base_url = "https://qvik.munark.in/api/v1"
        headers = {"Content-Type": "application/json"}

        with st.spinner("Creating agreement..."):
            response = requests.post(
                f"{base_url}/ai-agreement",
                json=final_data,
                headers=headers,
                timeout=30
            )
            if response.status_code not in [200, 201]:
                st.error(f"API Error: {response.status_code} - {response.text}")
                return
            result = response.json()
            agreement_id = result.get("id")

        with st.spinner("Generating documents..."):
            pdf_response = requests.get(f"{base_url}/ai-agreement/{agreement_id}/pdf", timeout=30)
            word_response = requests.get(f"{base_url}/ai-agreement/{agreement_id}/word", timeout=30)

        if pdf_response.status_code == 200:
            st.session_state.pdf_content = pdf_response.content
            st.session_state.pdf_filename = f"agreement-{agreement_id}.pdf"
        if word_response.status_code == 200:
            st.session_state.word_content = word_response.content
            st.session_state.word_filename = f"agreement-{agreement_id}.docx"

        st.session_state.documents_ready = True

    except Exception as e:
        st.error(f"Error generating document: {str(e)}")


def recommend_contract(user_input):
    """Simple keyword-based contract recommendation."""
    input_lower = user_input.lower()
    scores = {}
    for contract_type, rules in RECOMMENDATION_RULES.items():
        score = sum(1 for kw in rules['keywords'] if kw in input_lower)
        if score > 0:
            scores[contract_type] = score
    if scores:
        best = max(scores, key=scores.get)
        return best, RECOMMENDATION_RULES[best]['description']
    return None, None


# ============================================================
# UI RENDERING FUNCTIONS
# ============================================================

def render_progress_bar():
    """Render the step progress bar at the top."""
    step = st.session_state.current_step
    progress = step / len(STEPS)
    st.progress(progress)
    st.markdown(f"**Step {step} of {len(STEPS)}: {STEPS[step]}**")
    st.markdown("---")


def render_step_1_account():
    """Step 1: Create Account - Name and Email."""
    if st.session_state.account_created:
        st.success(f"Hey {st.session_state.user_name}, your account has been created!")
        if st.button("Continue to Step 2 →", key="step1_continue", use_container_width=True):
            st.session_state.current_step = 2
            st.rerun()
        return

    st.markdown("### Welcome to TechLaw25")
    st.markdown("Please provide your details to get started.")

    with st.form("account_form"):
        name = st.text_input("Your Name", placeholder="e.g., Arbaz Mohammed")
        email = st.text_input("Your Email", placeholder="e.g., arbaz@company.com")
        submitted = st.form_submit_button("Create Account", use_container_width=True)

        if submitted:
            if not name or not name.strip():
                st.error("Please enter your name.")
            elif not email or not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', email):
                st.error("Please enter a valid email address.")
            else:
                st.session_state.user_name = name.strip()
                st.session_state.user_email = email.strip()
                st.session_state.account_created = True
                st.rerun()


def render_step_2_role():
    """Step 2: Role Selection - Buyer or Provider."""
    st.markdown("### Are you a buyer or a provider?")
    st.markdown("Select your role in this agreement.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🏢 Provider (Supplier)")
        st.caption("You are providing the product or service to your customer.")
        if st.button("I am a Provider", key="role_provider", use_container_width=True):
            st.session_state.role = "supplier"
            st.session_state.contract_type = "supplier"
            st.session_state.current_step = 3
            st.rerun()
    with col2:
        st.markdown("#### 👤 Buyer (Customer)")
        st.caption("You are receiving or evaluating the product or service.")
        if st.button("I am a Buyer", key="role_buyer", use_container_width=True):
            st.session_state.role = "buyer"
            st.session_state.contract_type = "buyer"
            st.session_state.current_step = 3
            st.rerun()


def render_step_3_party_details():
    """Step 3: Party Details - Address forms with Yes/No/IDK."""
    questions = BUYER_QUESTIONS if st.session_state.role == "buyer" else SUPPLIER_QUESTIONS
    # Party detail questions are Q6 and Q7
    party_questions = [q for q in questions if q["input_type"] == "address"]

    # Track which sub-question we're on (0 = Q6, 1 = Q7)
    if 'party_question_index' not in st.session_state:
        st.session_state.party_question_index = 0

    idx = st.session_state.party_question_index

    if idx >= len(party_questions):
        # All party questions done, move to step 4
        st.session_state.current_step = 4
        st.rerun()
        return

    pq = party_questions[idx]
    q_num = idx + 1
    total = len(party_questions)

    st.markdown(f"### Party Details ({q_num} of {total})")

    # Render question with (i) icon
    render_question_header(pq)

    # Show Yes/No/IDK buttons
    if st.session_state.show_input_for_question != f"party_{idx}":
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Yes", key=f"party_{idx}_yes", use_container_width=True):
                st.session_state.show_input_for_question = f"party_{idx}"
                st.rerun()
        with col2:
            if st.button("❌ No", key=f"party_{idx}_no", use_container_width=True):
                st.session_state.party_question_index += 1
                st.session_state.show_input_for_question = None
                st.rerun()
        with col3:
            if st.button("🤷 IDK", key=f"party_{idx}_idk", use_container_width=True):
                st.session_state.party_question_index += 1
                st.session_state.show_input_for_question = None
                st.rerun()
    else:
        # Show address form
        prefix = pq["address_prefix"]
        render_address_form(prefix, f"party_{idx}")


def render_step_4_contract():
    """Step 4: Contract Selection with Coming Soon items."""
    st.markdown("### Select Your Contract Type")
    st.markdown("Choose the type of agreement you need.")

    for contract in CONTRACT_TYPES:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**📄 {contract['name']}**")
            st.caption(contract['description'])
        with col2:
            if contract['available']:
                if st.button("Select", key=f"contract_{contract['id']}", use_container_width=True):
                    st.session_state.contract_list_type = contract['id']
                    st.session_state.contract_data["contract_list_type"] = contract['id']
                    st.session_state.current_step = 5
                    st.session_state.current_question_index = 0
                    st.session_state.show_input_for_question = None
                    st.rerun()
            else:
                st.button("Coming Soon", key=f"contract_{contract['id']}", disabled=True, use_container_width=True)

    # Contract recommendation
    st.markdown("---")
    st.markdown("**Not sure which contract you need?**")
    rec_col1, rec_col2 = st.columns([3, 1])
    with rec_col1:
        user_need = st.text_input("Describe your need", placeholder="e.g., I want to try software before buying", key="contract_rec_input", label_visibility="collapsed")
    with rec_col2:
        if st.button("Get Suggestion", key="get_rec", use_container_width=True):
            if user_need:
                contract_id, desc = recommend_contract(user_need)
                if contract_id:
                    # Find the contract name
                    contract_name = next((c['name'] for c in CONTRACT_TYPES if c['id'] == contract_id), contract_id)
                    st.session_state.recommendation = f"We recommend: **{contract_name}** - {desc}"
                else:
                    st.session_state.recommendation = "Please provide more details about your need."

    if st.session_state.get("recommendation"):
        st.info(st.session_state.recommendation)


def render_step_5_qa():
    """Step 5: Q&A - Clickable questions with conditional input forms."""
    questions = BUYER_QUESTIONS if st.session_state.role == "buyer" else SUPPLIER_QUESTIONS
    # Q&A questions are Q1-Q5 and Q8 (exclude address questions Q6, Q7 which were in Step 3)
    qa_questions = [q for q in questions if q["input_type"] != "address"]

    idx = st.session_state.current_question_index

    if idx >= len(qa_questions):
        # All questions done - proceed to document generation
        finalize_and_generate()
        return

    q = qa_questions[idx]
    total = len(qa_questions)

    st.markdown(f"### Question {idx + 1} of {total}")
    st.caption(f"Category: {q['category']}")

    # Render question with (i) icon
    render_question_header(q)

    # Different rendering based on input type
    if q["input_type"] == "jurisdiction":
        # Jurisdiction always shows input (no Yes/No/IDK)
        render_jurisdiction_form(q)
    elif st.session_state.show_input_for_question != f"qa_{idx}":
        # Show Yes/No/IDK buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Yes", key=f"qa_{idx}_yes", use_container_width=True):
                st.session_state.show_input_for_question = f"qa_{idx}"
                st.rerun()
        with col2:
            if st.button("❌ No", key=f"qa_{idx}_no", use_container_width=True):
                handle_no_idk_answer(q)
        with col3:
            if st.button("🤷 IDK", key=f"qa_{idx}_idk", use_container_width=True):
                handle_no_idk_answer(q)
    else:
        # Show the appropriate input form based on question type
        if q["input_type"] == "product":
            render_product_form(q)
        elif q["input_type"] == "licenses":
            render_licenses_form(q)
        elif q["input_type"] == "duration":
            render_duration_form(q)
        elif q["input_type"] == "date":
            render_date_form(q)
        elif q["input_type"] == "fees":
            render_fees_form(q)


def render_step_6_payment():
    """Step 6: Payment & Download."""
    if not st.session_state.documents_ready:
        st.warning("Documents are still being generated. Please wait...")
        return

    st.markdown("### Your Evaluation Agreement is ready!")

    if not st.session_state.payment_complete:
        st.markdown("To download your contract, please complete payment.")
        st.markdown("")

        if st.button("💳 Pay Now", key="pay_now", use_container_width=True, type="primary"):
            st.session_state.show_payment_dialog = True
            st.rerun()

        # Payment dialog
        if st.session_state.get("show_payment_dialog"):
            with st.container(border=True):
                st.markdown("#### Payment (Demo)")
                st.markdown("---")
                st.markdown("**Contract:** Evaluation Agreement")
                st.markdown("**Amount:** Demo - No charge")
                st.markdown("")
                if st.button("✅ Complete Payment", key="complete_payment", use_container_width=True, type="primary"):
                    st.session_state.payment_complete = True
                    st.session_state.show_payment_dialog = False
                    st.rerun()
                if st.button("Cancel", key="cancel_payment", use_container_width=True):
                    st.session_state.show_payment_dialog = False
                    st.rerun()
    else:
        st.success("✅ Payment successful! You can now download your documents.")
        st.markdown("---")
        st.markdown("### 📥 Download Your Documents")
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


# ============================================================
# QUESTION RENDERING HELPERS
# ============================================================

def render_question_header(question):
    """Render question text with (i) explanation icon."""
    st.markdown(f"**{question['question']}**")
    with st.expander("ℹ️ What does this mean? (Click to expand)"):
        st.markdown(question['explanation'])


def render_address_form(prefix, form_key):
    """Render structured address form."""
    with st.form(f"address_form_{form_key}"):
        name_label = "Company/Organization Name" if prefix == "company" else "Other Party's Name"
        name = st.text_input(name_label, placeholder="e.g., Infosys Limited", key=f"{form_key}_name")
        address = st.text_input("Address", placeholder="e.g., 44 Electronics City, Phase 1", key=f"{form_key}_addr")
        col1, col2, col3 = st.columns(3)
        with col1:
            city = st.text_input("City", placeholder="e.g., Bangalore", key=f"{form_key}_city")
        with col2:
            state = st.text_input("State", placeholder="e.g., Karnataka", key=f"{form_key}_state")
        with col3:
            pincode = st.text_input("Pincode", placeholder="e.g., 560100", key=f"{form_key}_pin")
        country = st.text_input("Country", placeholder="e.g., India", key=f"{form_key}_country")

        submitted = st.form_submit_button("Submit & Continue →", use_container_width=True)
        if submitted:
            data = st.session_state.contract_data["questions"]
            data[f"{prefix}_name"] = name.strip() if name else ""
            data[f"{prefix}_address"] = address.strip() if address else ""
            data[f"{prefix}_city"] = city.strip() if city else ""
            data[f"{prefix}_state"] = state.strip() if state else ""
            data[f"{prefix}_pincode"] = pincode.strip() if pincode else ""
            data[f"{prefix}_country"] = country.strip() if country else ""
            st.session_state.party_question_index += 1
            st.session_state.show_input_for_question = None
            st.rerun()


def render_product_form(question):
    """Render product name + version form."""
    with st.form(f"product_form_{question['id']}"):
        col1, col2 = st.columns(2)
        with col1:
            product_name = st.text_input("Product Name", placeholder="e.g., SAP S/4HANA", key=f"prod_name_{question['id']}")
        with col2:
            product_version = st.text_input("Version", placeholder="e.g., 2023", key=f"prod_ver_{question['id']}")

        submitted = st.form_submit_button("Submit & Next →", use_container_width=True)
        if submitted:
            data = st.session_state.contract_data["questions"]
            data["product_to_be_evaluated"] = product_name.strip() if product_name else ""
            data["product_version"] = product_version.strip() if product_version else ""
            advance_qa_question()


def render_licenses_form(question):
    """Render licenses count + type form."""
    with st.form(f"license_form_{question['id']}"):
        col1, col2 = st.columns(2)
        with col1:
            num_licenses = st.number_input("Number of Licenses", min_value=1, value=5, key=f"num_lic_{question['id']}")
        with col2:
            license_type = st.selectbox("License Type", ["Concurrent", "Named User", "Server", "Trial", "Standard", "Other"], key=f"lic_type_{question['id']}")

        submitted = st.form_submit_button("Submit & Next →", use_container_width=True)
        if submitted:
            data = st.session_state.contract_data["questions"]
            data["number_of_licenses"] = str(num_licenses)
            data["license_type"] = license_type
            advance_qa_question()


def render_duration_form(question):
    """Render evaluation duration form."""
    # Use session state to track selection so custom input appears dynamically
    dur_key = f"dur_selection_{question['id']}"
    if dur_key not in st.session_state:
        st.session_state[dur_key] = "60 days"

    duration = st.selectbox(
        "Evaluation Period",
        ["30 days", "60 days", "90 days", "Custom"],
        index=["30 days", "60 days", "90 days", "Custom"].index(st.session_state[dur_key]),
        key=f"dur_{question['id']}",
        on_change=lambda: setattr(st.session_state, dur_key, st.session_state[f"dur_{question['id']}"]),
    )
    st.session_state[dur_key] = duration

    custom_days = None
    if duration == "Custom":
        custom_days = st.number_input("Enter number of days", min_value=1, value=60, key=f"custom_dur_{question['id']}")

    if st.button("Submit & Next →", key=f"dur_submit_{question['id']}", use_container_width=True):
        data = st.session_state.contract_data["questions"]
        if duration == "Custom" and custom_days:
            data["period_for_evaluation"] = f"{custom_days} days"
        else:
            data["period_for_evaluation"] = duration
        advance_qa_question()


def render_date_form(question):
    """Render date picker form."""
    with st.form(f"date_form_{question['id']}"):
        start_date = st.date_input("Evaluation Start Date", value=datetime.now(), key=f"start_date_{question['id']}")

        submitted = st.form_submit_button("Submit & Next →", use_container_width=True)
        if submitted:
            data = st.session_state.contract_data["questions"]
            data["agreement_start_date"] = start_date.strftime("%d-%b-%Y")
            advance_qa_question()


def render_fees_form(question):
    """Render multi-field fees form."""
    with st.form(f"fees_form_{question['id']}"):
        st.markdown("**Fee Details**")
        col1, col2 = st.columns(2)
        with col1:
            currency = st.selectbox("Currency", ["USD", "INR", "EUR", "GBP"], key=f"fee_curr_{question['id']}")
            amount = st.text_input("Amount", placeholder="e.g., 500", key=f"fee_amt_{question['id']}")
            invoicing = st.selectbox("Invoicing", ["Upfront", "Monthly", "Quarterly", "Annually", "On Completion"], key=f"fee_inv_{question['id']}")
        with col2:
            credit_period = st.text_input("Credit Period", placeholder="e.g., 30 days", key=f"fee_credit_{question['id']}")
            late_charges = st.selectbox("Late Payment Charges?", ["No", "Yes"], key=f"fee_late_{question['id']}")
            tax = st.selectbox("Tax", ["Excluded", "Included", "Exempt"], key=f"fee_tax_{question['id']}")

        late_pct = ""
        if late_charges == "Yes":
            late_pct = st.text_input("Late Payment Percentage", placeholder="e.g., 2%", key=f"fee_late_pct_{question['id']}")

        submitted = st.form_submit_button("Submit & Next →", use_container_width=True)
        if submitted:
            data = st.session_state.contract_data["questions"]
            data["fees_options"] = "yes"
            data["currency"] = currency
            data["amount"] = amount.strip() if amount else ""
            data["invoicing"] = invoicing.lower()
            data["credit_period"] = credit_period.strip() if credit_period else ""
            data["late_payment_charges"] = "yes" if late_charges == "Yes" else "no"
            data["late_payment_percentage"] = late_pct.strip() if late_pct else ""
            data["tax_fees"] = tax.lower()
            advance_qa_question()


def render_jurisdiction_form(question):
    """Render jurisdiction form (always shown, no Yes/No/IDK)."""
    with st.form(f"jurisdiction_form_{question['id']}"):
        laws = st.text_input("Laws which apply", placeholder="e.g., Laws of Karnataka, India", key=f"laws_{question['id']}")
        courts = st.text_input("Courts which resolve disputes", placeholder="e.g., Courts of Bangalore, Karnataka", key=f"courts_{question['id']}")

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Submit & Next →", use_container_width=True)
        with col2:
            skip = st.form_submit_button("Skip (IDK)", use_container_width=True)

        if submitted:
            data = st.session_state.contract_data["questions"]
            data["laws_which_apply"] = laws.strip() if laws else ""
            data["courts_which_resolve"] = courts.strip() if courts else ""
            advance_qa_question()
        elif skip:
            advance_qa_question()


# ============================================================
# HANDLER FUNCTIONS
# ============================================================

def handle_no_idk_answer(question):
    """Handle No/IDK answer - store defaults and advance."""
    data = st.session_state.contract_data["questions"]

    # For fees question, set fees_options to "no" when user says No
    if question["input_type"] == "fees":
        data["fees_options"] = "no"

    # For duration, set default 60 days
    if question["input_type"] == "duration" and "period_for_evaluation" in question["fields"]:
        if not data.get("period_for_evaluation"):
            data["period_for_evaluation"] = "60 days"

    advance_qa_question()


def advance_qa_question():
    """Move to the next Q&A question."""
    st.session_state.current_question_index += 1
    st.session_state.show_input_for_question = None
    st.rerun()


def finalize_and_generate():
    """Finalize data collection and generate document."""
    # Set metadata
    st.session_state.contract_data["contract_type"] = st.session_state.contract_type
    st.session_state.contract_data["relationship_type"] = st.session_state.relationship_type
    st.session_state.contract_data["contract_list_type"] = st.session_state.contract_list_type

    # Run enrichment pipeline
    with st.spinner("🔍 Reviewing and enriching your answers..."):
        enrich_contract_data()
        calculate_end_date_fallback()
        deterministic_enrichment()
        apply_extraction_safety_net()

    # Generate document
    with st.spinner("📝 Generating your Evaluation Agreement..."):
        generate_document()

    # Move to payment step
    st.session_state.current_step = 6
    st.rerun()


def reset_conversation():
    """Reset the entire conversation to start over."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ============================================================
# MAIN FUNCTION
# ============================================================

def main():
    st.title("⚖️ TechLaw25 - Contract Assistant")

    # Sidebar with reset button
    with st.sidebar:
        st.markdown("### TechLaw25")
        if st.session_state.get("user_name"):
            st.markdown(f"👤 **{st.session_state.user_name}**")
        if st.session_state.get("role"):
            role_display = "Buyer" if st.session_state.role == "buyer" else "Provider"
            st.markdown(f"🏷️ Role: **{role_display}**")
        if st.session_state.get("contract_list_type"):
            contract_display = st.session_state.contract_list_type.replace("-", " ").title()
            st.markdown(f"📄 Contract: **{contract_display}**")
        st.markdown("---")
        if st.button("🔄 Start Over", key="reset", use_container_width=True):
            reset_conversation()

    # Progress bar
    render_progress_bar()

    # Render the current step
    step = st.session_state.current_step

    if step == 1:
        render_step_1_account()
    elif step == 2:
        render_step_2_role()
    elif step == 3:
        render_step_3_party_details()
    elif step == 4:
        render_step_4_contract()
    elif step == 5:
        render_step_5_qa()
    elif step == 6:
        render_step_6_payment()


if __name__ == "__main__":
    main()
