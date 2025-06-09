"""LLM client initialization and API calls."""

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
import logging
from typing import Dict, List, Any, Optional
from ..config.logging_config import get_logger
from ..config.model_config import get_model_config, get_generation_config

logger = get_logger(__name__)

def initialize_llm(api_key: str, tools: Optional[List] = None) -> ChatGoogleGenerativeAI:
    """
    Initialize and return the LLM used for completion.
    
    Args:
        api_key: Google API key
        tools: List of tools to bind to the LLM
        
    Returns:
        Initialized ChatGoogleGenerativeAI instance
    """
    try:
        config = get_model_config()
        
        # Initialize ChatGoogleGenerativeAI with the Gemini model
        llm = ChatGoogleGenerativeAI(
            model=config["model_version"],
            temperature=config["temperature"],
            top_p=config["top_p"],
            top_k=config["top_k"],
            max_output_tokens=config["max_output_tokens"],
            google_api_key=api_key
        )
        
        # Bind tools if provided
        if tools:
            llm = llm.bind_tools(tools)
            logger.info(f"Successfully initialized LangChain ChatGoogleGenerativeAI model bound with {len(tools)} tools.")
        else:
            logger.info(f"Successfully initialized LangChain ChatGoogleGenerativeAI model without tools.")
            
        return llm
        
    except Exception as e:
        logger.error(f"Error initializing LLM: {e}")
        raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True 
)
def call_gemini_api(
    prompt_content: List[Dict], 
    config: Dict,
    api_key: str
) -> genai.types.GenerateContentResponse:
    """
    Internal function to call the Gemini API with retry logic.
    
    Args:
        prompt_content: List of message dictionaries
        config: Generation configuration
        api_key: Google API key
        
    Returns:
        Gemini API response
    """
    logger.debug("Calling Gemini API...")
    
    # Configure genai with the API key
    genai.configure(api_key=api_key)
    
    # Get model config
    model_config = get_model_config()
    model = genai.GenerativeModel(model_config["model_version"])
    
    # Call the API
    response = model.generate_content(
        contents=prompt_content, 
        generation_config=config
    )
    
    logger.debug("Gemini API call successful.")
    return response