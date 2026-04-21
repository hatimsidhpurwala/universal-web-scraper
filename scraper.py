import os
import random
import time
import re
import json
from datetime import datetime
from typing import List, Dict, Type

import pandas as pd
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, create_model
import html2text
import tiktoken

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from openai import OpenAI
#import google.generativeai as genai
from groq import Groq
import streamlit as st


from assets import USER_AGENTS,PRICING,HEADLESS_OPTIONS,SYSTEM_MESSAGE,USER_MESSAGE
load_dotenv()
from urllib.parse import urlparse, urljoin, urlunparse
from collections import deque

def safe_load_json(s: str):
    """
    Try to clean the model response and load valid JSON.
    """
    # 1) Strip spaces
    s = s.strip()

    # 2) Remove ```json ... ``` wrappers if present
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"```$", "", s).strip()

    # 3) Try normal json.loads
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # 4) Try to extract first {...} block only
        m = re.search(r"\{.*\}", s, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        # 5) If still fails, re‑raise so you see the real error
        raise
def normalize_url(url: str) -> str:
    """Canonicalize URL: drop fragment, map root to /index.html, strip trailing slash."""
    parsed = urlparse(url)
    parsed = parsed._replace(fragment="")

    # Treat bare domain or "/" as index.html (site-specific)
    if (parsed.path == "" or parsed.path == "/") and not parsed.query:
        parsed = parsed._replace(path="/index.html")

    normalized = urlunparse(parsed).rstrip("/")
    return normalized

def extract_links(html: str, base_url: str, domain: str) -> List[str]:
    """Extract internal links from a page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        raw_href = a["href"].strip()
        abs_href = urljoin(base_url, raw_href)
        norm_href = normalize_url(abs_href)
        if norm_href.startswith(("http://", "https://")) and urlparse(norm_href).netloc == domain:
            links.append(norm_href)
    # dedupe while preserving order
    seen = set()
    uniq = []
    for u in links:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq

# Set up the Chrome WebDriver options
def crawl_site(start_url: str, max_pages: int = 200, max_depth: int = 5) -> Dict[str, str]:
    """
    Crawl all internal pages starting from start_url.
    Returns dict: {url: html_source}.
    """
    start_url = normalize_url(start_url)
    domain = urlparse(start_url).netloc

    visited = set()
    queue = deque([(start_url, 0)])
    pages_html: Dict[str, str] = {}

    while queue and len(pages_html) < max_pages:
        url, depth = queue.popleft()
        url = normalize_url(url)
        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        print(f"[{len(pages_html)+1}] depth {depth} → {url}")

        try:
            html = fetch_html_selenium(url)
            if not html:
                continue
            pages_html[url] = html

            if depth < max_depth:
                child_links = extract_links(html, url, domain)
                for child in child_links:
                    if child not in visited:
                        queue.append((child, depth + 1))
        except Exception as e:
            print(f"  ✗ error on {url}: {e}")

        time.sleep(1)  # politeness between pages

    return pages_html
def setup_selenium():
    options = Options()

    # Randomly select a user agent from the imported list
    user_agent = random.choice(USER_AGENTS)
    options.add_argument(f"user-agent={user_agent}")

    # Add other options
    for option in HEADLESS_OPTIONS:
        options.add_argument(option)

    # Specify the path to the ChromeDriver
    service = Service()  

    # Initialize the WebDriver
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def click_accept_cookies(driver):
    """
    Tries to find and click on a cookie consent button. It looks for several common patterns.
    """
    try:
        # Wait for cookie popup to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button | //a | //div"))
        )
        
        # Common text variations for cookie buttons
        accept_text_variations = [
            "accept", "agree", "allow", "consent", "continue", "ok", "I agree", "got it"
        ]
        
        # Iterate through different element types and common text variations
        for tag in ["button", "a", "div"]:
            for text in accept_text_variations:
                try:
                    # Create an XPath to find the button by text
                    element = driver.find_element(By.XPATH, f"//{tag}[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text}')]")
                    if element:
                        element.click()
                        print(f"Clicked the '{text}' button.")
                        return
                except:
                    continue

        print("No 'Accept Cookies' button found.")
    
    except Exception as e:
        print(f"Error finding 'Accept Cookies' button: {e}")

def fetch_html_selenium(url):
    driver = setup_selenium()
    try:
        driver.get(url)
        
        # Add random delays to mimic human behavior
        time.sleep(1)  # Adjust this to simulate time for user to read or interact
        driver.maximize_window()
        

        # Try to find and click the 'Accept Cookies' button
        # click_accept_cookies(driver)

        # Add more realistic actions like scrolling
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Simulate time taken to scroll and read
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        html = driver.page_source
        return html
    finally:
        driver.quit()

def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove headers and footers based on common HTML tags or classes
    for element in soup.find_all(['header', 'footer']):
        element.decompose()  # Remove these tags and their content

    return str(soup)


def html_to_markdown_with_readability(html_content):

    
    cleaned_html = clean_html(html_content)  
    
    # Convert to markdown
    markdown_converter = html2text.HTML2Text()
    markdown_converter.ignore_links = False
    markdown_content = markdown_converter.handle(cleaned_html)
    
    return markdown_content


    
def save_raw_data(raw_data, timestamp, output_folder='output'):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Save the raw markdown data with timestamp in filename
    raw_output_path = os.path.join(output_folder, f'rawData_{timestamp}.md')
    with open(raw_output_path, 'w', encoding='utf-8') as f:
        f.write(raw_data)
    print(f"Raw data saved to {raw_output_path}")
    return raw_output_path


def remove_urls_from_file(file_path):
    # Regex pattern to find URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

    # Construct the new file name
    base, ext = os.path.splitext(file_path)
    new_file_path = f"{base}_cleaned{ext}"

    # Read the original markdown content
    with open(file_path, 'r', encoding='utf-8') as file:
        markdown_content = file.read()

    # Replace all found URLs with an empty string
    cleaned_content = re.sub(url_pattern, '', markdown_content)

    # Write the cleaned content to a new file
    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.write(cleaned_content)
    print(f"Cleaned file saved as: {new_file_path}")
    return cleaned_content


def create_dynamic_listing_model(field_names: List[str]) -> Type[BaseModel]:
    """
    Dynamically creates a Pydantic model based on provided fields.
    field_name is a list of names of the fields to extract from the markdown.
    """
    # Create field definitions using aliases for Field parameters
    field_definitions = {field: (str, ...) for field in field_names}
    # Dynamically create the model with all field
    return create_model('DynamicListingModel', **field_definitions)


def create_listings_container_model(listing_model: Type[BaseModel]) -> Type[BaseModel]:
    """
    Create a container model that holds a list of the given listing model.
    """
    return create_model('DynamicListingsContainer', listings=(List[listing_model], ...))




def trim_to_token_limit(text, model, max_tokens=120000):
    encoder = tiktoken.encoding_for_model(model)
    tokens = encoder.encode(text)
    if len(tokens) > max_tokens:
        trimmed_text = encoder.decode(tokens[:max_tokens])
        return trimmed_text
    return text

def generate_system_message(listing_model: BaseModel) -> str:
    """
    Dynamically generate a system message based on the fields in the provided listing model.
    """
    # Use the model_json_schema() method to introspect the Pydantic model
    schema_info = listing_model.model_json_schema()

    # Extract field descriptions from the schema
    field_descriptions = []
    for field_name, field_info in schema_info["properties"].items():
        # Get the field type from the schema info
        field_type = field_info["type"]
        field_descriptions.append(f'"{field_name}": "{field_type}"')

    # Create the JSON schema structure for the listings
    schema_structure = ",\n".join(field_descriptions)

    # Generate the system message dynamically
    system_message = f"""
    You are an intelligent text extraction and conversion assistant. Your task is to extract structured information 
                        from the given text and convert it into a pure JSON format. The JSON should contain only the structured data extracted from the text, 
                        with no additional commentary, explanations, or extraneous information. 
                        You could encounter cases where you can't find the data of the fields you have to extract or the data will be in a foreign language.
                        Please process the following text and provide the output in pure JSON format with no words before or after the JSON:
    Please ensure the output strictly follows this schema:

    {{
        "listings": [
            {{
                {schema_structure}
            }}
        ]
    }} """

    return system_message



def format_data(markdown, ListingsContainer, ListingModel, model_name, image_query=""):
    """
    Call the chosen LLM to extract data from `markdown` according to:
    - image_query: full sentence from OCR (preferred)
    - st.session_state["extracted_fields"]: fallback list of fields
    Returns (formatted_data, token_counts).
    """
    import os, json
    from streamlit import session_state as ss

    token_counts = {}

    # 1️⃣ Build the user request text (keep OCR order)
    if image_query:
        query_text = image_query.strip()
    else:
        fields_list = ss.get("extracted_fields", [])
        query_text = " ".join(fields_list)

    SYSTEM_MESSAGE = (
    "You are a helpful assistant. "
    "Read the page content and answer the user's question in plain conversational English. "
    "Give a direct, clear answer like you are explaining to a person. "
    "Do NOT return JSON. Do NOT use bullet points. Just answer naturally in 2-4 sentences."
)

    USER_MESSAGE = (
        f'User request: "{query_text}"\n\n'
        "Page content:\n"
    )

    data = markdown  # page content

    # 2️⃣ OpenAI branch
    if model_name in ["gpt-4o-mini", "gpt-4o-2024-08-06"]:
        from openai import OpenAI
        import tiktoken

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        completion = client.beta.chat.completions.parse(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": USER_MESSAGE + data},
            ],
            response_format=ListingsContainer,
        )

        encoder = tiktoken.encoding_for_model(model_name)
        input_token_count = len(encoder.encode(USER_MESSAGE + data))
        output_token_count = len(
            encoder.encode(json.dumps(completion.choices[0].message.parsed.dict()))
        )
        token_counts = {
            "input_tokens": input_token_count,
            "output_tokens": output_token_count,
        }
        return completion.choices[0].message.parsed, token_counts

    # 3️⃣ Gemini branch
    elif model_name in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]:
        import google.generativeai as genai

        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel(
            model_name,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": ListingsContainer,
            },
        )

        prompt = SYSTEM_MESSAGE + "\n" + USER_MESSAGE + data
        input_tokens = model.count_tokens(prompt)
        completion = model.generate_content(prompt)
        usage_metadata = completion.usage_metadata
        token_counts = {
            "input_tokens": usage_metadata.prompt_token_count,
            "output_tokens": usage_metadata.candidates_token_count,
        }
        return completion.text, token_counts

    # 4️⃣ Groq (llama / mixtral / gemma) branch
    elif model_name in ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"]:
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set, but a Groq model was selected. "
                "Set GROQ_API_KEY or choose another model."
            )

        sys_message = (
            generate_system_message(ListingModel)
            + "\nReturn ONLY valid JSON. Do not add text, explanation, or backticks."
        )

        client = Groq(api_key=api_key)

        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_message},
                {"role": "user", "content": USER_MESSAGE + data},
            ],
            model=model_name,
        )

        response_content = completion.choices[0].message.content
        print("RAW MODEL RESPONSE:\n", response_content)

        try:
            parsed_response = safe_load_json(response_content)
        except Exception:
            parsed_response = response_content  # keep as plain text if not JSON

        token_counts = {
            "input_tokens": completion.usage.prompt_tokens,
            "output_tokens": completion.usage.completion_tokens,
        }

        return parsed_response, token_counts

    # 5️⃣ Unknown model – always raise (never return None silently)
    else:
        raise ValueError(f"Unsupported model: {model_name}")

def save_formatted_data(formatted_data, timestamp, output_folder='output'):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Parse the formatted data if it's a JSON string (from Gemini API)
    if isinstance(formatted_data, str):
        try:
            formatted_data_dict = json.loads(formatted_data)
        except json.JSONDecodeError:
            raise ValueError("The provided formatted data is a string but not valid JSON.")
    else:
        # Handle data from OpenAI or other sources
        formatted_data_dict = formatted_data.dict() if hasattr(formatted_data, 'dict') else formatted_data

    # Save the formatted data as JSON with timestamp in filename
    json_output_path = os.path.join(output_folder, f'sorted_data_{timestamp}.json')
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_data_dict, f, indent=4)
    print(f"Formatted data saved to JSON at {json_output_path}")

    # Prepare data for DataFrame
    if isinstance(formatted_data_dict, dict):
        # If the data is a dictionary containing lists, assume these lists are records
        data_for_df = next(iter(formatted_data_dict.values())) if len(formatted_data_dict) == 1 else formatted_data_dict
    elif isinstance(formatted_data_dict, list):
        data_for_df = formatted_data_dict
    else:
        raise ValueError("Formatted data is neither a dictionary nor a list, cannot convert to DataFrame")

    # Create DataFrame
    try:
        df = pd.DataFrame(data_for_df)
        print("DataFrame created successfully.")

        # Save the DataFrame to an Excel file
        excel_output_path = os.path.join(output_folder, f'sorted_data_{timestamp}.xlsx')
        df.to_excel(excel_output_path, index=False)
        print(f"Formatted data saved to Excel at {excel_output_path}")
        
        return df
    except Exception as e:
        print(f"Error creating DataFrame or saving Excel: {str(e)}")
        return None

def calculate_price(token_counts, model):
    input_token_count = token_counts.get("input_tokens", 0)
    output_token_count = token_counts.get("output_tokens", 0)
    
    # Calculate the costs
    input_cost = input_token_count * PRICING[model]["input"]
    output_cost = output_token_count * PRICING[model]["output"]
    total_cost = input_cost + output_cost
    
    return input_token_count, output_token_count, total_cost

def ingest_site_to_qdrant(pages_html: dict):
    """Full pipeline: clean → chunk → embed → store in Qdrant."""
    from cleaner import deduplicate_chunks
    from chunker import chunk_markdown
    from embedder import embed_chunks
    from vector_store import store_chunks, clear_collection

    clear_collection()

    all_chunks = []
    for url, html in pages_html.items():
        md = html_to_markdown_with_readability(html)
        from cleaner import normalize_text
        md = normalize_text(md)
        page_chunks = chunk_markdown(md, source_url=url)
        all_chunks.extend(page_chunks)

    all_chunks = deduplicate_chunks(all_chunks)
    all_chunks = embed_chunks(all_chunks)
    count = store_chunks(all_chunks)
    return count


if __name__ == "__main__":
    start_url = "https://www.alhutaib.com/"  # or index.html; normalization will unify
    fields = ['Service Name', 'Location', 'Description']  # adjust to your schema

    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 1. Crawl whole site
        pages_html = crawl_site(start_url, max_pages=300, max_depth=6)

        # 2. Convert all pages to markdown and combine
        all_markdown_parts = []
        for url, html in pages_html.items():
            md = html_to_markdown_with_readability(html)
            all_markdown_parts.append(f"\n\n### PAGE: {url}\n\n{md}")

        combined_markdown = "\n".join(all_markdown_parts)

        # 3. Save raw combined markdown
        save_raw_data(combined_markdown, timestamp)

        # 4. Dynamic models based on fields
        DynamicListingModel = create_dynamic_listing_model(fields)
        DynamicListingsContainer = create_listings_container_model(DynamicListingModel)

        # 5. Send combined markdown to LLM for structured extraction
        formatted_data, token_counts = format_data(
            combined_markdown,
            DynamicListingsContainer,
            DynamicListingModel,
            "llama-3.3-70b-versatile"
        )

        print(formatted_data)

        # 6. Save formatted data (JSON + Excel)
        save_formatted_data(formatted_data, timestamp)

        # 7. Pricing info
        input_tokens, output_tokens, total_cost = calculate_price(
            token_counts,
            "llama-3.3-70b-versatile"
        )
        print(f"Input token count: {input_tokens}")
        print(f"Output token count: {output_tokens}")
        print(f"Estimated total cost: ${total_cost:.4f}")

    except Exception as e:
        print(f"An error occurred: {e}")