#!/usr/bin/env python3
"""
Simple script to test if Gemini API is working with service account credentials.
This uses Vertex AI which requires the API to be enabled in Google Cloud Console.
"""

import os
import json
from google.oauth2 import service_account
from google import genai

# Path to your service account key file
KEY_FILE = "robust-slice-485915-b8-ec1cfaaca8ab.json"

def test_gemini():
    """Test Gemini API connection and generate a simple response."""
    
    print("=" * 60)
    print("Testing Gemini API Connection (Vertex AI)")
    print("=" * 60)
    
    # Check if the key file exists
    if not os.path.exists(KEY_FILE):
        print(f"[ERROR] Key file '{KEY_FILE}' not found!")
        return False
    
    print(f"[OK] Found key file: {KEY_FILE}")
    
    try:
        # Load the service account credentials
        print("\n[INFO] Loading credentials...")
        credentials = service_account.Credentials.from_service_account_file(
            KEY_FILE,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        print(f"[OK] Loaded credentials for: {credentials.service_account_email}")
        print(f"[OK] Project ID: {credentials.project_id}")
        
        # Create a client with the credentials
        print("\n[INFO] Creating Gemini client (Vertex AI)...")
        client = genai.Client(
            vertexai=True,
            project=credentials.project_id,
            location="us-central1",
            credentials=credentials
        )
        print("[OK] Client created")
        
        # Test with a simple prompt
        print("\n[INFO] Sending test prompt...")
        test_prompt = "Hello! Please respond with 'Gemini is working!' if you can read this."
        
        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=test_prompt
        )
        
        print("\n" + "=" * 60)
        print("[SUCCESS] Gemini API is working!")
        print("=" * 60)
        print(f"\nResponse:\n{response.text}")
        print("\n" + "=" * 60)
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("[ERROR] Error occurred!")
        print("=" * 60)
        print(f"\nError type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Check if it's a permission denied error
        if "PERMISSION_DENIED" in str(e) or "SERVICE_DISABLED" in str(e):
            print("\n" + "=" * 60)
            print("SOLUTION: Enable Vertex AI API")
            print("=" * 60)
            print("\nThe Vertex AI API is not enabled for your project.")
            print("\nTo enable it:")
            print("1. Visit: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com")
            print("2. Select your project: techlaw-gemini")
            print("3. Click 'Enable'")
            print("4. Wait a few minutes for the change to propagate")
            print("5. Run this script again")
            print("\n" + "=" * 60)
        
        # Check if it's a billing error
        if "BILLING_DISABLED" in str(e) or "billing" in str(e).lower():
            print("\n" + "=" * 60)
            print("SOLUTION: Enable Billing")
            print("=" * 60)
            print("\nGreat! Vertex AI API is now enabled.")
            print("However, billing needs to be enabled for your project.")
            print("\nTo enable billing:")
            print("1. Visit: https://console.cloud.google.com/billing/enable?project=techlaw-gemini")
            print("2. Select or create a billing account")
            print("3. Link it to your project: techlaw-gemini")
            print("4. Wait a few minutes for the change to propagate")
            print("5. Run this script again")
            print("\nNote: Vertex AI has a free tier, but billing account is required.")
            print("\n" + "=" * 60)
        
        return False

if __name__ == "__main__":
    success = test_gemini()
    exit(0 if success else 1)
