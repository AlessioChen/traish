import streamlit as st
import json
from groq import Groq
import os
from dotenv import load_dotenv
import base64
from openai import OpenAI
from io import BytesIO
from PIL import Image
import toml

# Function to load the recycling data
def load_recycling_data():
    current_dir = os.getcwd()
    file_path = os.path.join(current_dir, 'data.json')

    try:
        with open(file_path, ) as file:

            return json.load(file)
    except FileNotFoundError:
        st.error("Could not find data.json file")
        return None

# Initialize Groq client
def init_groq():
    api_key = st.secrets['api_keys']['groq']
    if not api_key:
        st.error("Please set your Groq API key")
        return None
    return Groq(api_key=api_key)

def init_openai():
    api_key = st.secrets['api_keys']['openai']
    if not api_key:
        st.error("Please set your OpenAI API key")
        return None
    return OpenAI(api_key=api_key)

def analyze_image(client, image_data, recycling_data):
    if not client:
        return "Error: OpenAI client not initialized"
    
    try:
        # Encode image to base64
        base64_image = base64.b64encode(image_data.getvalue()).decode('utf-8')
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "List the recyclable items you see in this image. Format your response as a comma-separated list of items."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

def get_groq_response(client, items, context):
    if not client:
        return "Error: Groq client not initialized"
    
    prompt = f"""You are a recycling assistant
Using this recycling information:
{context}

For each item listed: {items}, please tell me:
1. Which waste type it is using the "name" property from the recycling data
2. Any special preparation needed (if applicable)
3. Why it goes in that bin or place 
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful recycling assistant that provides accurate information based on the given context."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.1-70b-versatile",
            temperature=0.0,
            max_tokens=2000
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {str(e)}"

def get_bin_image(waste_type):
    """Return the image path for a given waste type"""
    bin_images = {
       "battery_symbol": "images/battery_symbol.png",
       "blue": "images/blu.png",
       "brown": "images/brown.png",
       "green": "images/green.png",
       "yellow": "images/yellow.png",
       "grey": "images/grey.png",
       "oil_symbol": "images/oil_symbol.png",
       "red": "images/red.png",
       "white_with_green_cross": "images/white_with_green_cross.png",
       "yellow_street": "images/yellow_street.png",
       "yellow": "images/yellow.png"

    }
    return bin_images.get(waste_type.lower(), None)

# Streamlit UI
def main():
    st.title("🌍 Recycling Assistant")
    st.write("Ask questions about how to properly sort and recycle different items")

    # tab1, tab2 = st.tabs(["📸 Capture Image", "📝 Analysis Results"])
    
    # # Load recycling data
    recycling_data = load_recycling_data()

    if not recycling_data:
        st.stop()

    
    # Initialize Groq
    groq_client = init_groq()
    openai_client = init_openai()
    if not groq_client or not openai_client:
        st.stop()


    img_file = st.camera_input("Take a picture of the item")
    if img_file is not None:
        with st.spinner("Analyzing image..."):
            identified_items = analyze_image(openai_client, img_file, recycling_data)
            
            if not isinstance(identified_items, str) or identified_items.startswith("Error"):
                st.error(identified_items)
            else:
                st.write("Detected Items:", identified_items)
                
                recycling_advice = get_groq_response(groq_client, 
                                                   identified_items, 
                                                   json.dumps(recycling_data))
                
                st.write("### Recycling Instructions:")
                items = recycling_advice.split('\n\n')

                for item in items:
                 
                    if item.strip():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(item)
                        with col2:
                            # Map waste types to their corresponding images
                            if "unsorted waste" in item.lower():
                                st.image(get_bin_image("grey"), width=200)
                            elif "organic" in item.lower() or "food waste" in item.lower():
                                st.image(get_bin_image("brown"), width=200)
                            elif "plastic" in item.lower() or "metal" in item.lower():
                                st.image(get_bin_image("yellow"), width=200)
                            elif "paper" in item.lower():
                                st.image(get_bin_image("blue"), width=200)
                            elif "collection centers" in item.lower():
                                st.image(get_bin_image("red"), width=200)


if __name__ == "__main__":
    main()