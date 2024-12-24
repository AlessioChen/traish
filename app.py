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
from toolhouse import Toolhouse

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

def init_tool_house():
    api_key = st.secrets['api_keys']['toolhouse']
    return Toolhouse(api_key=api_key,
provider="openai")


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

        prompt = """Analyze this image and identify items.
Guidelines for identification:
- List only physical objects you can clearly see
- Use simple, generic terms
- Specify quantities if multiple similar items exist
- Ignore background elements or non-disposable items
Format your response as a comma-separated list. Example:
"glass wine bottle, plastic yogurt container, banana peel, cardboard box"
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a waste sorting assistant that identifies items based on established recycling categories. Identify items precisely to help users determine the correct disposal method."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
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
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

def get_groq_response(client, content, prompt, th=None):
    if not client:
        return "Error: Groq client not initialized"
    
    try:
        MODEL = "llama-3.3-70b-versatile"
        messages = [
            {
                "role": "system",
                "content": content
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        
        if th is None: 

            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.0,  # Lower temperature for more consistent responses
                max_tokens=2000,

            )
        
            return response.choices[0].message.content
    
    
    
        # Add tools if th is provided
        messages = [{
            "role": "user",
            "content": "Search on web for recycling facilities near Binario F, Rome, Via Marsala, 29H, 00185 Roma RM and give me the results."
        }]

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            # Passes Code Execution as a tool
            tools=th.get_tools()
        )



        # Runs the Code Execution tool, gets the result, 
        # and appends it to the context
        th_response = th.run_tools(response)
        messages += th_response
       
        messages.append({
            "role": "system", 
            "content": "return the result to the user you must NEVER use thesearch tool again"
        })

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
        )
                

        return response.choices[0].message.content
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
       "famacie": "images/farmacie.jpg",
       "yellow_street": "images/yellow_street.png",

    }
    return bin_images.get(waste_type.lower(), None)

# Streamlit UI
def main():
    st.title("🌍 Recycling Assistant")
    # st.write("Ask questions about how to properly sort and recycle different items")

    # tab1, tab2 = st.tabs(["📸 Capture Image", "📝 Analysis Results"])
    
    # # Load recycling data
    recycling_data = load_recycling_data()

    if not recycling_data:
        st.stop()

    th = init_tool_house()

    groq_client = init_groq()
    openai_client = init_openai()
  

    if not groq_client or not openai_client or not th:
        st.stop()


    img_file = st.camera_input("Take a picture of the item")
    if img_file is not None:
        with st.spinner("Analyzing image..."):
            identified_items = analyze_image(openai_client, img_file, recycling_data)
            
            if not isinstance(identified_items, str) or identified_items.startswith("Error"):
                st.error(identified_items)
            else:
                st.write("Detected Items:", identified_items)

                items = identified_items
                context = json.dumps(recycling_data)
                GROQ_CONTENT = """You are a specialized recycling assistant with deep knowledge of waste sorting.
                    Your goal is to provide accurate, practical advice that helps users correctly dispose of items.
                    Always prioritize environmental safety and proper waste separation."""
                GROQ_PROMPT = f"""You are a recycling expert assistant. Using the provided recycling guidelines, analyze these items: {items} Context (recycling guidelines):
{context}
For each item, provide a structured analysis:
1. Item Name:
- Correct Bin: [Specify the exact bin color/type]
- Preparation Required: [List any cleaning/preparation steps]
- Reason: [Explain why this bin is correct]
- Special Notes: [Any warnings, alternatives, or important details]
Guidelines for your response:
- Separate each item with a blank line
- Be specific about bin colors and types
- If an item isn't in the guidelines, recommend the safest disposal method
- Mention if items need to be clean, disassembled, or specially prepared
- Include any relevant warnings about contamination or hazardous materials
- If an item has multiple components, explain how to separate them
Please format your response clearly and concisely for each item."""

                recycling_advice = get_groq_response(groq_client, GROQ_CONTENT, GROQ_PROMPT)
                
                st.write("### Recycling Instructions:")
                items = recycling_advice.split('\n\n')
                
                for item in items:
                 
                    if item.strip():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(item)
                        with col2:
                            # Map waste types to their corresponding images
                            if "unsorted waste" in item.lower() or "grey" in item.lower():
                                st.image(get_bin_image("grey"), width=200)
                            elif "organic" in item.lower() or "food waste" in item.lower() or "brown" in item.lower():
                                st.image(get_bin_image("brown"), width=200)
                            elif "plastic" in item.lower() or "metal" in item.lower() or "yellow" in item.lower():
                                st.image(get_bin_image("yellow"), width=200)
                            elif "paper" in item.lower() or "blue" in item.lower():
                                st.image(get_bin_image("blue"), width=200)
                            elif "collection centers" in item.lower() or "electronic" in item.lower() or "red" in item.lower():
                                st.image(get_bin_image("red"), width=200)
                            elif "oil" in item.lower():
                                st.image(get_bin_image("oil_symbol"), width=200)
                            elif "battery" in item.lower():
                                st.image(get_bin_image("battery_symbol"), width=200),
                            elif "farmacy" in item.lower():
                                st.image(get_bin_image("farmacie"), width=200)

    # Add the new button and ecological sites finder
    if st.button("🔍 Find Nearby Ecological Sites"):
    
        with st.spinner("Searching for ecological sites..."):
            ecological_sites = get_groq_response(groq_client, '', '', th)
            st.write("### 📍 Nearby Ecological Sites:")
            st.write(ecological_sites)
            
if __name__ == "__main__":
    main()
