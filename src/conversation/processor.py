"""Main conversation processing logic."""

from typing import List, Dict, Tuple, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

# RAG pipeline imports moved to top for performance
try:
    from ..rag.memvid_pipeline import memvid_rag_pipeline
except ImportError:
    memvid_rag_pipeline = None

try:
    from ..rag.pipeline import rag_pipeline
except ImportError:
    rag_pipeline = None

try:
    from ..security import scan_input, scan_output
except ImportError:
    # Graceful fallback if security module is missing or broken
    def scan_input(text): return type('obj', (object,), {'is_valid': True, 'sanitized_text': text})
    def scan_output(text, prompt=None): return type('obj', (object,), {'is_valid': True, 'sanitized_text': text})

from ..config.logging_config import get_logger
from ..llm.prompts import get_combined_prompt
from ..llm.tools import get_all_tools, set_current_session, clear_current_session
from ..utils.helpers import detect_order_inquiry, detect_speech_acts
from ..utils.state_manager import is_order_finished, get_current_order_state
from .phase_manager import ConversationPhaseManager

logger = get_logger(__name__)

def _process_drink_context(drink_context: str) -> str:
    """
    Process multi-token drink context into a single drink item.
    
    Args:
        drink_context: Space-separated drink terms from conversation context
        
    Returns:
        Processed drink string suitable for add_to_order tool
    """
    if not drink_context:
        return ""
    
    # Split and clean drink context
    drink_tokens = [token.strip() for token in drink_context.split() if token.strip()]
    
    # Handle common drink combinations
    drink_combinations = {
        ('whiskey', 'rocks'): 'whiskey on the rocks',
        ('whiskey', 'neat'): 'whiskey neat',
        ('old', 'fashioned'): 'old fashioned',
        ('long', 'island'): 'long island iced tea'
    }
    
    # Check for known combinations
    for combo, result in drink_combinations.items():
        if all(token in drink_tokens for token in combo):
            return result
    
    # Prioritize actual drink names over modifiers
    drink_priorities = ['whiskey', 'beer', 'wine', 'cocktail', 'vodka', 'gin', 'rum', 'tequila',
                       'old fashioned', 'manhattan', 'martini', 'negroni', 'mojito']
    
    for drink in drink_priorities:
        if drink in drink_tokens:
            return drink
    
    # Fallback to first token if no priority match
    return drink_tokens[0] if drink_tokens else ""

def extract_emotion(text):
    """Helper to extract emotion state from text."""
    import re
    match = re.search(r'\[STATE:\s*(\w+)\]', text, re.IGNORECASE)
    if match:
        emotion = match.group(1).lower()
        clean_text = re.sub(r'\[STATE:\s*\w+\]', '', text, flags=re.IGNORECASE).strip()
        return emotion, clean_text
    return None, text

def process_order(
    user_input_text: str,
    current_session_history: List[Dict[str, str]],
    llm,
    rag_index=None,
    rag_documents: List[str] = None,
    rag_retriever=None,
    api_key: str = None,
    session_id: str = "default",
    app_state: Any = None
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, Any]], Any, str]:
    """
    Process user input using LLM with tool calling, updates state.
    
    Args:
        user_input_text: User's input
        current_session_history: Session history for Gradio
        llm: Initialized LLM instance
        rag_index: FAISS index for RAG (optional)
        rag_documents: Documents for RAG (optional)
        rag_retriever: Memvid retriever for video-based RAG (optional)
        api_key: API key for RAG pipeline (optional)
        
    Returns:
        Tuple of (response_text, updated_history, updated_history_for_gradio, updated_order, audio_data, emotion_state)
    """
    if not user_input_text:
        logger.warning("Received empty user input.")
        return "Please tell me what you'd like to order.", current_session_history, current_session_history, get_current_order_state(session_id, app_state), None, "neutral"

    # Security Scan: Input
    scan_result = scan_input(user_input_text)
    if not scan_result.is_valid:
        logger.warning(f"Input blocked by security scanner: {scan_result.blocked_reason}")
        blocked_msg = scan_result.blocked_reason
        
        updated_history = current_session_history[:]
        updated_history.append({'role': 'user', 'content': user_input_text})
        updated_history.append({'role': 'assistant', 'content': blocked_msg})
        
        return blocked_msg, updated_history, updated_history, get_current_order_state(session_id, app_state), None, "neutral"

    # Set session context for tools to access
    # This allows payment tools to know which session they're operating on
    # Treat None as "no active session" - tools fall back to legacy behavior
    set_current_session(session_id)
    
    # Initialize phase manager
    phase_manager = ConversationPhaseManager(session_id, app_state)
    
    # Detect if this is the first interaction (empty history)
    is_first_interaction = len(current_session_history) == 0
    if is_first_interaction:
        from ..utils.state_manager import initialize_state
        initialize_state(session_id, app_state)

    # Extract conversation context for speech act analysis
    conversation_context = [entry.get('content', '') for entry in current_session_history[-5:]]  # Last 5 messages
    
    # Enhanced intent detection using speech acts
    speech_act_result = detect_speech_acts(user_input_text, conversation_context)
    intent_match = detect_order_inquiry(user_input_text)
    
    # Check speech acts first for order confirmation patterns
    if speech_act_result['intent'] == 'order_confirmation' and speech_act_result['confidence'] > 0.4:
        logger.info(f"Detected order confirmation via speech act: {speech_act_result['speech_act']} with confidence {speech_act_result['confidence']}")
        
        # Handle commissive speech acts ("I can get you that whiskey")
        tools = get_all_tools()
        tool_map = {tool.name: tool for tool in tools}
        
        # Extract drink from context and add to order with improved error handling
        drink_context = speech_act_result.get('drink_context', '')
        if drink_context:
            # Guard against missing add_to_order tool
            if 'add_to_order' not in tool_map:
                logger.error("add_to_order tool not available in tool_map")
                agent_response_text = "I understand you'd like that drink, but I'm having trouble processing orders right now."
            else:
                # Process multi-token drink context
                processed_drink_items = _process_drink_context(drink_context)
                
                try:
                    # Use add_to_order tool with processed drink
                    add_result = tool_map['add_to_order'].invoke({'item': processed_drink_items})
                    agent_response_text = f"Perfect! {add_result}"
                    
                    # Update phase since order was placed
                    phase_manager.update_phase(order_placed=True)
                    
                except KeyError as e:
                    logger.error(f"Tool invocation failed - missing key: {e}")
                    agent_response_text = "I understand your order, but I'm having trouble processing it right now."
                except Exception as e:
                    logger.warning(f"Failed to add contextual drink {processed_drink_items}: {e}")
                    agent_response_text = "Got it! I'll prepare that for you."
        else:
            agent_response_text = "Absolutely! I'll take care of that for you."
            

        # Parse emotion from response
        emotion_state, agent_response_text = extract_emotion(agent_response_text)
        
        # Update history for Gradio display
        updated_history_for_gradio = current_session_history[:] 
        updated_history_for_gradio.append({'role': 'user', 'content': user_input_text})
        
        # Security Scan: Output
        output_scan_result = scan_output(agent_response_text, prompt=user_input_text)
        if not output_scan_result.is_valid:
            logger.warning("Output blocked by security scanner (speech act)")
            agent_response_text = output_scan_result.sanitized_text
            emotion_state = "neutral"

        updated_history_for_gradio.append({'role': 'assistant', 'content': agent_response_text})
        
        # Clear session context before returning
        clear_current_session()
        # Return emotion_state as the last element (modifying return signature implicity, caller must adapt)
        return agent_response_text, updated_history_for_gradio, updated_history_for_gradio, get_current_order_state(session_id, app_state), None, emotion_state
    
    # Fallback to traditional intent detection
    elif intent_match['intent'] and intent_match['confidence'] >= 0.5:
        logger.info(f"Detected order intent: {intent_match['intent']} with confidence {intent_match['confidence']}")
        
        # Directly call the appropriate tool based on intent
        tools = get_all_tools()
        tool_map = {tool.name: tool for tool in tools}
        
        if intent_match['intent'] == 'show_order':
            tool_result = tool_map['get_order'].invoke({})
            agent_response_text = f"Here's your current order:\n{tool_result}"
        elif intent_match['intent'] == 'get_bill':
            tool_result = tool_map['get_bill'].invoke({})
            agent_response_text = f"Here's your bill:\n{tool_result}"
        elif intent_match['intent'] == 'pay_bill':
            tool_result = tool_map['pay_bill'].invoke({})
            agent_response_text = tool_result
        else:
            agent_response_text = "I'm not sure what you're asking for. Could you please clarify?"
            
        # Parse emotion from response
        emotion_state, agent_response_text = extract_emotion(agent_response_text)
        
        # Update history for Gradio display
        updated_history_for_gradio = current_session_history[:] 
        updated_history_for_gradio.append({'role': 'user', 'content': user_input_text})
        
        # Security Scan: Output
        output_scan_result = scan_output(agent_response_text, prompt=user_input_text)
        if not output_scan_result.is_valid:
            logger.warning("Output blocked by security scanner (intent)")
            agent_response_text = output_scan_result.sanitized_text
            emotion_state = "neutral"

        updated_history_for_gradio.append({'role': 'assistant', 'content': agent_response_text})
        
        # Clear session context before returning
        clear_current_session()
        return agent_response_text, updated_history_for_gradio, updated_history_for_gradio, get_current_order_state(session_id, app_state), None, emotion_state

    # Prepare message history for LangChain model
    messages = []
    
    # Get current phase and create appropriate prompt
    current_phase = phase_manager.get_current_phase()
    from ..llm.tools import get_menu
    menu_text = get_menu.invoke({})
    combined_prompt = get_combined_prompt(current_phase, menu_text)
    
    # Add System Prompt
    messages.append(SystemMessage(content=combined_prompt))
    
    # Add Menu (as system/context info)
    messages.append(SystemMessage(content="\nHere is the menu:\n" + menu_text))

    # Convert Gradio history to LangChain message types
    history_limit = 10
    limited_history = current_session_history[-history_limit:]
    for entry in limited_history:
        role = entry.get("role")
        content = entry.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content)) 

    # Add the latest user input
    messages.append(HumanMessage(content=user_input_text))

    logger.info(f"Processing user input for session: {user_input_text}")
    
    try:
        # --- LLM Interaction Loop (Handles Tool Calls) ---
        while True:
            # Invoke the LLM with current messages
            try:
                ai_response: AIMessage = llm.invoke(messages)
            except Exception as invoke_err:
                err_msg = str(invoke_err).lower()
                err_code = getattr(invoke_err, "status_code", None)
                if (
                    err_code == 429
                    or "429" in err_msg
                    or "rate" in err_msg
                    or "quota" in err_msg
                    or ("resource" in err_msg and "exhaust" in err_msg)
                ):
                    logger.warning(f"LLM quota/rate limit hit for session: {invoke_err}")
                    # Return early so the sentinel never reaches emotion
                    # parsing, security scanning, or conversation history.
                    # The caller (handlers.py) intercepts response_text ==
                    # QUOTA_ERROR_SENTINEL and rebuilds the history with a
                    # user-facing message + shows the quota popup.
                    quota_history = current_session_history[:]
                    quota_history.append({'role': 'user', 'content': user_input_text})
                    clear_current_session()
                    return (
                        "QUOTA_ERROR", quota_history, quota_history,
                        get_current_order_state(session_id, app_state),
                        None, "neutral",
                    )
                else:
                    logger.error(f"LLM invocation failed: {invoke_err}")
                    agent_response_text = "I'm having a bit of trouble reaching my brain right now, but I can still help you with drinks."
                    break

            # Append the AI's response (could be text or tool call request)
            if not hasattr(ai_response, "content"):
                logger.warning("LLM returned a response without content; ending loop.")
                agent_response_text = "I'm having a moment—could you repeat that while I get my bearings?"
                break
            messages.append(ai_response)

            tool_calls = getattr(ai_response, 'tool_calls', None)
            if not tool_calls:
                # No tool calls requested, this is the final response to the user
                agent_response_text = ai_response.content
                
                # Determine if this is a casual conversation vs. an order/menu-related interaction
                should_use_rag = phase_manager.should_use_rag(user_input_text)
                
                # If this appears to be casual conversation and RAG is available, try enhancing with RAG
                if should_use_rag and api_key is not None:
                    # Early validation of RAG components before any heavy processing/try
                    rag_available = False
                    if rag_retriever is not None and memvid_rag_pipeline is not None:
                        rag_available = True
                    elif rag_index is not None and rag_documents is not None and rag_pipeline is not None:
                        # Ensure rag_documents is a non-empty sized collection
                        try:
                            if isinstance(rag_documents, (list, tuple)) or hasattr(rag_documents, "__len__"):
                                rag_available = len(rag_documents) > 0
                        except Exception:
                            rag_available = False
                    if not rag_available:
                        logger.debug("Skipping RAG enhancement: required components not initialized/available")
                    else:
                        try:
                            # Try Memvid first, then FAISS with improved error handling
                            rag_response = None
                            if rag_retriever is not None and memvid_rag_pipeline is not None:
                                logger.info("Enhancing response with Memvid RAG for casual conversation")
                                try:
                                    rag_response = memvid_rag_pipeline(
                                        query_text=user_input_text,
                                        memvid_retriever=rag_retriever,
                                        api_key=api_key
                                    )
                                except Exception as memvid_error:
                                    logger.warning(f"Memvid RAG failed: {memvid_error}")
                            elif rag_index is not None and rag_documents is not None and rag_pipeline is not None:
                                logger.info("Enhancing response with FAISS RAG for casual conversation")
                                try:
                                    rag_response = rag_pipeline(
                                        query_text=user_input_text,
                                        index=rag_index,
                                        documents=rag_documents,
                                        api_key=api_key
                                    )
                                except Exception as faiss_error:
                                    logger.warning(f"FAISS RAG failed: {faiss_error}")
                            else:
                                logger.debug("No RAG system available or imports failed")

                            # Safely use rag_response only if it's a sized, non-empty value
                            has_content = False
                            if rag_response is not None:
                                try:
                                    if isinstance(rag_response, (str, list, tuple, dict)) or hasattr(rag_response, "__len__"):
                                        has_content = len(rag_response) > 0
                                except Exception:
                                    has_content = False
                            if has_content:
                                # Log original response for comparison
                                logger.info(f"Original response: {agent_response_text}")
                                logger.info(f"RAG-enhanced response: {rag_response}")
                                # Use the RAG-enhanced response
                                agent_response_text = rag_response
                        except Exception as rag_error:
                            # If RAG fails, just use the original response
                            logger.warning(f"RAG enhancement failed: {rag_error}. Using original response.")

                break 
                
            # --- Tool Call Execution ---
            logger.info(f"LLM requested tool calls: {tool_calls}")
            tool_messages = []
            
            # Get available tools
            tools = get_all_tools()
            tool_map = {tool.name: tool for tool in tools}
            
            for tool_call in tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id") 

                # Find the corresponding tool function
                selected_tool = tool_map.get(tool_name)

                if selected_tool:
                    if not isinstance(tool_args, dict):
                        logger.warning(f"Malformed arguments for tool '{tool_name}': {type(tool_args)}")
                        tool_output = f"Error: Malformed arguments for tool {tool_name}."
                    else:
                        try:
                            # Execute the tool function with its arguments
                            tool_output = selected_tool.invoke(tool_args)
                            logger.info(f"Executed tool '{tool_name}' with args {tool_args}. Output: {tool_output}")
                        except TypeError as te:
                            logger.warning(f"Invalid parameters for tool '{tool_name}': {te}")
                            tool_output = f"Error: Invalid parameters for tool {tool_name}."
                        except Exception as e:
                            logger.error(f"Error executing tool '{tool_name}': {e}")
                            tool_output = f"Error executing tool {tool_name}: {e}"

                    # Append the result as a ToolMessage
                    tool_messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_id))
                else:
                    logger.error(f"Tool '{tool_name}' requested by LLM not found.")
                    tool_messages.append(ToolMessage(content=f"Error: Tool '{tool_name}' not found.", tool_call_id=tool_id))

            # Add the tool results to the message history
            messages.extend(tool_messages)
            # Continue the loop to send results back to LLM
            logger.info("Sending tool results back to LLM...")

        # --- End of LLM Interaction Loop ---

        # Final response text is now set
        logger.info(f"Final agent response: {agent_response_text}")

        # --- Update Conversation State ---
        phase_manager.increment_turn()
        
        # Check if an order was placed
        order_placed = is_order_finished(session_id, app_state)
        if order_placed:
            phase_manager.handle_order_placed()
        
        # Update phase based on interaction
        if phase_manager.get_current_phase() == 'small_talk':
            phase_manager.increment_small_talk()
        
        # Determine next phase
        next_phase = phase_manager.update_phase(order_placed)
        
        # Parse emotion from response
        emotion_state, agent_response_text = extract_emotion(agent_response_text)

        # Update history for Gradio display
        updated_history_for_gradio = current_session_history[:] 
        updated_history_for_gradio.append({'role': 'user', 'content': user_input_text})
        
        # Security Scan: Output
        output_scan_result = scan_output(agent_response_text, prompt=user_input_text)
        if not output_scan_result.is_valid:
            logger.warning("Output blocked by security scanner")
            agent_response_text = output_scan_result.sanitized_text
            emotion_state = "neutral"

        updated_history_for_gradio.append({'role': 'assistant', 'content': agent_response_text})

        return agent_response_text, updated_history_for_gradio, updated_history_for_gradio, get_current_order_state(session_id, app_state), None, emotion_state

    except Exception as e:
        logger.exception(f"Critical error in process_order: {str(e)}")
        error_message = "I'm sorry, an unexpected error occurred during processing. Please try again later."
        # Return original state on critical error
        safe_history = current_session_history[:]
        safe_history.append({'role': 'user', 'content': user_input_text})
        safe_history.append({'role': 'assistant', 'content': error_message})
        return error_message, safe_history, safe_history, get_current_order_state(session_id, app_state), None, "neutral"
    finally:
        # Always clear session context after processing completes
        # This ensures the session context is cleaned up even if an error occurs
        clear_current_session()