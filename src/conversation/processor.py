"""Main conversation processing logic."""

from typing import List, Dict, Tuple, Any, Generator
import re
import concurrent.futures
import asyncio
import queue

# RAG pipeline imports moved to top for performance
try:
    from ..rag.memvid_pipeline import memvid_rag_pipeline
except ImportError:
    memvid_rag_pipeline = None

try:
    from ..security import scan_input, scan_output
except ImportError:
    # Graceful fallback if security module is missing or broken
    def scan_input(text): return type('obj', (object,), {'is_valid': True, 'sanitized_text': text})
    def scan_output(text, prompt=None): return type('obj', (object,), {'is_valid': True, 'sanitized_text': text})

from ..config.logging_config import get_logger, should_log_sensitive
from ..llm.prompts import get_combined_prompt
from ..llm.tools import get_all_tools, set_current_session, clear_current_session
from ..llm.client import stream_gemini_api, call_gemini_api
from ..utils.helpers import detect_order_inquiry, detect_speech_acts, append_to_history
from ..utils.state_manager import is_order_finished, get_current_order_state, _get_store_and_session
from ..utils.rate_limiter import check_rate_limits
from ..utils.batch_state import batch_state_commits
from ..utils.streaming import SentenceBuffer
from ..utils.errors import is_quota_error
from .phase_manager import ConversationPhaseManager

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.events import Event
from google.genai import types

logger = get_logger(__name__)

# Timeout for RAG pipeline calls to prevent indefinite blocking
RAG_TIMEOUT = 10.0  # seconds

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

def _dispatch_tool(tool_name: str, tool_args: dict, tool_map: dict) -> str:
    """Execute a single tool with args and return the string output."""
    selected_tool = tool_map.get(tool_name)
    if not selected_tool:
        return f"Error: Tool '{tool_name}' not found."
    if not isinstance(tool_args, dict):
        return f"Error: Malformed arguments for tool {tool_name}."
    try:
        tool_output = selected_tool(**tool_args)
        if should_log_sensitive():
            logger.debug(f"Executed tool '{tool_name}' with args {tool_args}. Output: {tool_output}")
        return str(tool_output)
    except TypeError:
        return f"Error: Invalid parameters for tool {tool_name}."
    except Exception as e:
        return f"Error executing tool {tool_name}: {e}"


def _build_order_context(session_id: str, app_state: dict) -> str:
    """Helper to build a summary string of the current order for the system instruction."""
    order_list = get_current_order_state(session_id, app_state)
    if not order_list:
        return "CURRENT ORDER: Empty."
    items_str = []
    for item in order_list:
        q = item.get('quantity', 1)
        mods = item.get('modifiers', 'no modifiers')
        entry = f"{q}x {item['name']}"
        if mods != 'no modifiers':
            entry += f" with {mods}"
        items_str.append(entry)
    return "CURRENT ORDER ALREADY CONTAINS: " + ", ".join(items_str) + ". DO NOT re-add these items unless requested."


def process_order(
    user_input_text: str,
    current_session_history: List[Dict[str, str]],
    llm,
    rag_retriever=None,
    api_key: str = None,
    session_id: str = "default",
    app_state: Any = None
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, Any]], Any]:
    """
    Process user input using LLM with tool calling, updates state.
    
    Args:
        user_input_text: User's input
        current_session_history: Session history for Gradio
        llm: Initialized LLM instance
        rag_retriever: Memvid retriever for video-based RAG (optional)
        api_key: API key for RAG pipeline (optional)
        
    Returns:
        Tuple of (response_text, updated_history, updated_history_for_gradio, updated_order, audio_data, emotion_state)
    """
    session_id, app_state = _get_store_and_session(session_id, app_state)
    from google.adk.models import Gemini
    if llm is None or not isinstance(llm, Gemini):
        from ..llm.session_registry import get_session_llm
        llm = get_session_llm(session_id, api_key=api_key)
    if not user_input_text:
        logger.warning("Received empty user input.")
        return "Please tell me what you'd like to order.", current_session_history, current_session_history, get_current_order_state(session_id, app_state), None

    # Security Scan: Input
    scan_result = scan_input(user_input_text)
    if not scan_result.is_valid:
        logger.warning(f"Input blocked by security scanner: {scan_result.blocked_reason}")
        blocked_msg = scan_result.blocked_reason
        
        updated_history = append_to_history(current_session_history, user_input_text, blocked_msg)
        
        return blocked_msg, updated_history, updated_history, get_current_order_state(session_id, app_state), None

    # Rate limiting check
    rate_allowed, rate_reason = check_rate_limits(session_id)
    if not rate_allowed:
        logger.warning(f"Rate limit exceeded: {rate_reason}")
        rate_error_msg = f"Rate limit exceeded: {rate_reason}"
        
        updated_history = append_to_history(current_session_history, user_input_text, rate_error_msg)
        
        return rate_error_msg, updated_history, updated_history, get_current_order_state(session_id, app_state), None

    # Set session context for tools to access
    # This allows payment tools to know which session they're operating on
    # Treat None as "no active session" - tools fall back to legacy behavior
    set_current_session(session_id)
    
    # Initialize phase manager
    phase_manager = ConversationPhaseManager(session_id, app_state)
    
    # Detect if this is the first interaction (empty history) and state is not yet initialized
    is_first_interaction = len(current_session_history) == 0
    if is_first_interaction and (app_state is None or session_id not in app_state):
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
                    add_result = tool_map['add_to_order'](item_name=processed_drink_items)
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
            

        # Security Scan: Output
        output_scan_result = scan_output(agent_response_text, prompt=user_input_text)
        if not output_scan_result.is_valid:
            logger.warning("Output blocked by security scanner (speech act)")
            agent_response_text = output_scan_result.sanitized_text

        updated_history_for_gradio = append_to_history(current_session_history, user_input_text, agent_response_text)
        
        # Return documented 5-tuple
        clear_current_session()
        return agent_response_text, updated_history_for_gradio, updated_history_for_gradio, get_current_order_state(session_id, app_state), None
    
    # Fallback to traditional intent detection (only if not asking about tips)
    elif intent_match['intent'] and intent_match['confidence'] >= 0.5 and not re.search(r'\btips?\b', user_input_text, re.IGNORECASE):
        logger.info(f"Detected order intent: {intent_match['intent']} with confidence {intent_match['confidence']}")
        
        # Directly call the appropriate tool based on intent
        tools = get_all_tools()
        tool_map = {tool.name: tool for tool in tools}
        
        if intent_match['intent'] == 'show_order':
            tool_result = tool_map['get_order']()
            agent_response_text = f"Here's your current order:\n{tool_result}"
        elif intent_match['intent'] == 'get_bill':
            tool_result = tool_map['get_bill']()
            agent_response_text = f"Here's your bill:\n{tool_result}"
        elif intent_match['intent'] == 'pay_bill':
            tool_result = tool_map['pay_bill']()
            agent_response_text = tool_result
        else:
            agent_response_text = "I'm not sure what you're asking for. Could you please clarify?"
            
        # Security Scan: Output
        output_scan_result = scan_output(agent_response_text, prompt=user_input_text)
        if not output_scan_result.is_valid:
            logger.warning("Output blocked by security scanner (intent)")
            agent_response_text = output_scan_result.sanitized_text

        updated_history_for_gradio = append_to_history(current_session_history, user_input_text, agent_response_text)
        
        clear_current_session()
        return agent_response_text, updated_history_for_gradio, updated_history_for_gradio, get_current_order_state(session_id, app_state), None

    # Prepare message history
    # Get current phase and create appropriate prompt
    current_phase = phase_manager.get_current_phase()
    from ..llm.tools import get_menu
    menu_text = get_menu()
    combined_prompt = get_combined_prompt(current_phase, menu_text)
    
    # Combine system prompt and menu context for system instruction
    # Inject current order to prevent the LLM from duplicating orders across turns
    order_context = _build_order_context(session_id, app_state)

    system_instruction = combined_prompt + "\n\nHere is the menu:\n" + menu_text + "\n\n" + order_context

    # Convert Gradio history
    history_limit = 10
    limited_history = current_session_history[-history_limit:]
    
    # Apply RAG context to the user input before executing the agent
    should_use_rag = phase_manager.should_use_rag(user_input_text)
    if should_use_rag and api_key:
        if rag_retriever is not None and memvid_rag_pipeline is not None:
            logger.info("Enhancing response with Memvid RAG for casual conversation")
            try:
                rag_response = memvid_rag_pipeline(
                    query_text=user_input_text,
                    memvid_retriever=rag_retriever,
                    api_key=api_key
                )
                if rag_response and rag_response.strip():
                    rag_context = f"\n\nRelevant context: {rag_response.strip()}"
                    user_input_text += rag_context
            except Exception as memvid_error:
                logger.warning(f"Memvid RAG failed: {memvid_error}")

    # Initialize a temporary stateless session service for this runner call
    session_service = InMemorySessionService()

    async def _execute_runner():
        # Setup session
        session = await session_service.create_session(
            app_name="mayamcp", user_id="user", session_id=session_id
        )
        
        # Populate history
        for entry in limited_history:
            role = entry.get("role")
            content = entry.get("content", "")
            # Clean state annotations like [STATE: ...] if present
            clean_content = re.sub(r'\[STATE:\s*\w+\]', '', content, flags=re.IGNORECASE).strip()
            sdk_role = "model" if role == "assistant" else "user"
            msg = types.Content(role=sdk_role, parts=[types.Part.from_text(text=clean_content)])
            event = Event(
                invocation_id="history",
                author=sdk_role,
                content=msg
            )
            await session_service.append_event(session=session, event=event)

        # Instantiate ADK Agent
        agent = Agent(
            name="bartender",
            model=llm,
            instruction=system_instruction,
            tools=get_all_tools()
        )

        # Instantiate Runner
        runner = Runner(
            agent=agent,
            app_name="mayamcp",
            session_service=session_service,
            auto_create_session=False
        )

        new_msg = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_input_text)]
        )

        final_response_text = ""
        async for event in runner.run_async(
            user_id="user",
            session_id=session_id,
            new_message=new_msg
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = "".join(
                        part.text for part in event.content.parts if part.text
                    )
        return final_response_text

    # Use batch state commits to optimize remote dictionary operations
    with batch_state_commits(session_id, app_state):
        try:
            # Set current session for tool calls
            set_current_session(session_id)

            try:
                def _run_coro(coro):
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None
                    if loop and loop.is_running():
                        import concurrent.futures
                        def _run_in_thread():
                            set_current_session(session_id)
                            return asyncio.run(coro)
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(_run_in_thread)
                            return future.result()
                    else:
                        return asyncio.run(coro)
                agent_response_text = _run_coro(_execute_runner())
                if should_log_sensitive():
                    logger.debug(f"Original response: {agent_response_text}")
            except Exception as invoke_err:
                if is_quota_error(invoke_err):
                    logger.warning(f"LLM quota/rate limit hit for session: {invoke_err}")
                    quota_history = current_session_history[:]
                    quota_history.append({'role': 'user', 'content': user_input_text})
                    return (
                        "QUOTA_ERROR", quota_history, quota_history,
                        get_current_order_state(session_id, app_state),
                        None,
                    )
                else:
                    logger.error(f"LLM invocation failed: {invoke_err}")
                    agent_response_text = "I'm having a bit of trouble reaching my brain right now, but I can still help you with drinks."

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
            
            # Security Scan: Output
            output_scan_result = scan_output(agent_response_text, prompt=user_input_text)
            if not output_scan_result.is_valid:
                logger.warning("Output blocked by security scanner")
                agent_response_text = output_scan_result.sanitized_text
    
            updated_history_for_gradio = append_to_history(current_session_history, user_input_text, agent_response_text)
    
            return agent_response_text, updated_history_for_gradio, updated_history_for_gradio, get_current_order_state(session_id, app_state), None
    
        except Exception as e:
            logger.exception(f"Critical error in process_order: {str(e)}")
            error_message = "I'm sorry, an unexpected error occurred during processing. Please try again later."
            # Return original state on critical error
            safe_history = append_to_history(current_session_history, user_input_text, error_message)
            return error_message, safe_history, safe_history, get_current_order_state(session_id, app_state), None
        finally:
            # Always clear session context after processing completes
            clear_current_session()


def process_order_stream(
    user_input_text: str,
    current_session_history: List[Dict[str, str]],
    llm,
    rag_retriever=None,
    api_key: str = None,
    session_id: str = "default",
    app_state: Any = None
) -> Generator[dict, None, None]:
    """
    Process user input using streaming LLM with tool calling.
    
    Args:
        user_input_text: User's input
        current_session_history: Session history for Gradio
        llm: Initialized LLM instance
        rag_retriever: Memvid retriever for video-based RAG (optional)
        api_key: API key for RAG pipeline (optional)
        session_id: Session identifier for state management
        app_state: Application state for session management
        
    Yields:
        Dict with streaming response data
    """
    session_id, app_state = _get_store_and_session(session_id, app_state)
    # Initialize phase manager for conversation flow
    phase_manager = ConversationPhaseManager(session_id, app_state)
    
    # Security Scan: Input
    input_scan_result = scan_input(user_input_text)
    if not input_scan_result.is_valid:
        logger.warning("Input blocked by security scanner")
        yield {
            'type': 'error',
            'content': input_scan_result.sanitized_text
        }
        return
    
    # Use sanitized input for processing
    sanitized_input = input_scan_result.sanitized_text
    
    # Rate limiting check
    rate_allowed, rate_reason = check_rate_limits(session_id)
    if not rate_allowed:
        logger.warning(f"Rate limit exceeded: {rate_reason}")
        yield {
            'type': 'error',
            'content': f"Rate limit exceeded: {rate_reason}"
        }
        return
    
    # Convert Gradio history to Gemini format with same window
    history_limit = 10
    truncated_history = current_session_history[-history_limit:]

    # Determine if this is a casual conversation vs. an order/menu-related interaction
    should_use_rag = phase_manager.should_use_rag(sanitized_input)
    
    # If this appears to be casual conversation and RAG is available, try enhancing with RAG
    if should_use_rag and api_key:
        # Early validation of RAG components before any heavy processing/try
        if rag_retriever is None or memvid_rag_pipeline is None:
            logger.debug("Skipping RAG enhancement: required components not initialized/available")
        else:
            logger.info("Enhancing response with Memvid RAG for casual conversation")
            try:
                # Execute RAG pipeline with timeout to prevent indefinite blocking
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        memvid_rag_pipeline,
                        query_text=sanitized_input,
                        memvid_retriever=rag_retriever,
                        api_key=api_key
                    )
                    try:
                        rag_response = future.result(timeout=RAG_TIMEOUT)
                    except concurrent.futures.TimeoutError:
                        logger.warning(f"RAG pipeline timed out after {RAG_TIMEOUT} seconds")
                        rag_response = None
                # Add RAG context to the user input
                if rag_response and rag_response.strip():
                    rag_context = f"\n\nRelevant context: {rag_response.strip()}"
                    sanitized_input += rag_context
            except Exception as memvid_error:
                logger.warning(f"Memvid RAG failed: {memvid_error}")

    worker_thread = None

    # Use batch state commits to optimize remote dictionary operations
    with batch_state_commits(session_id, app_state):
        try:
            # Set current session for tool calls
            set_current_session(session_id)

            # Get current phase and create appropriate prompt
            current_phase = phase_manager.get_current_phase()
            from ..llm.tools import get_menu
            menu_text = get_menu()
            combined_prompt = get_combined_prompt(current_phase, menu_text)
            
            # Combine system prompt and menu context for system instruction
            # Inject current order to prevent the LLM from duplicating orders across turns
            order_context = _build_order_context(session_id, app_state)

            system_instruction = combined_prompt + "\n\nHere is the menu:\n" + menu_text + "\n\n" + order_context

            # Queue for transferring events from the async background thread
            event_queue = queue.Queue()

            async def _execute_runner_stream():
                try:
                    session_service = InMemorySessionService()
                    session = await session_service.create_session(
                        app_name="mayamcp", user_id="user", session_id=session_id
                    )
                    
                    # Populate history
                    for entry in truncated_history:
                        role = entry.get("role")
                        content = entry.get("content", "")
                        clean_content = re.sub(r'\[STATE:\s*\w+\]', '', content, flags=re.IGNORECASE).strip()
                        sdk_role = "model" if role == "assistant" else "user"
                        msg = types.Content(role=sdk_role, parts=[types.Part.from_text(text=clean_content)])
                        event = Event(
                            invocation_id="history",
                            author=sdk_role,
                            content=msg
                        )
                        await session_service.append_event(session=session, event=event)

                    # Instantiate ADK Agent
                    agent = Agent(
                        name="bartender",
                        model=llm,
                        instruction=system_instruction,
                        tools=get_all_tools()
                    )

                    # Instantiate Runner
                    runner = Runner(
                        agent=agent,
                        app_name="mayamcp",
                        session_service=session_service,
                        auto_create_session=False
                    )

                    new_msg = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=sanitized_input)]
                    )

                    async for event in runner.run_async(
                        user_id="user",
                        session_id=session_id,
                        new_message=new_msg
                    ):
                        event_queue.put(('event', event))
                    
                    event_queue.put(('done', None))
                except Exception as err:
                    event_queue.put(('error', err))

            import threading

            def _async_thread_worker():
                try:
                    set_current_session(session_id)
                    asyncio.run(_execute_runner_stream())
                except Exception as t_err:
                    event_queue.put(('error', t_err))

            # Run the worker thread
            worker_thread = threading.Thread(target=_async_thread_worker)
            worker_thread.start()

            # Create sentence buffer for TTS pipelining
            sentence_buffer = SentenceBuffer()
            accumulated_text = ""
            
            while True:
                try:
                    msg_type, data = event_queue.get(timeout=30)
                except queue.Empty:
                    logger.error("Queue timed out waiting for ADK runner stream.")
                    yield {
                        'type': 'error',
                        'content': "Sorry, I'm having a bit of trouble completing that response."
                    }
                    return

                if msg_type == 'error':
                    if is_quota_error(data):
                        logger.warning(f"Quota error in stream: {data}")
                        yield {
                            'type': 'error',
                            'content': "It looks like your API key has hit its rate limit. Please check the popup for details."
                        }
                    else:
                        logger.error(f"Error in runner thread: {data}")
                        yield {
                            'type': 'error',
                            'content': "I'm sorry, an unexpected error occurred during processing. Please try again later."
                        }
                    return

                elif msg_type == 'done':
                    break

                elif msg_type == 'event':
                    event: Event = data
                    if event.author == 'model' and event.content and event.content.parts:
                        text_chunk = "".join(part.text for part in event.content.parts if part.text)
                        
                        if text_chunk:
                            accumulated_text += text_chunk
                            
                            # Security scan only the new chunk before yielding
                            chunk_scan_result = scan_output(text_chunk, prompt=sanitized_input)
                            if not chunk_scan_result.is_valid:
                                logger.warning("Streaming content blocked by security scanner")
                                yield {
                                    'type': 'error',
                                    'content': chunk_scan_result.sanitized_text,
                                    'emotion_state': 'neutral'
                                }
                                return
                            
                            sanitized_chunk = chunk_scan_result.sanitized_text if chunk_scan_result.sanitized_text is not None else text_chunk
                            
                            # Check for complete sentences using sanitized text
                            sentences = sentence_buffer.add_text(sanitized_chunk)
                            
                            # Yield text chunk for immediate UI update
                            yield {
                                'type': 'text_chunk',
                                'content': sanitized_chunk,
                                'partial': sentence_buffer.get_partial()
                            }
                            
                            # Yield complete sentences for TTS
                            for sentence in sentences:
                                yield {
                                    'type': 'sentence',
                                    'content': sentence
                                }
            
            # Flush remaining content
            remaining_sentences = sentence_buffer.flush()
            for sentence in remaining_sentences:
                yield {
                    'type': 'sentence',
                    'content': sentence
                }
            
            clean_response = accumulated_text
            
            # Final Security Scan
            output_scan_result = scan_output(
                clean_response, prompt=sanitized_input
            )
            if not output_scan_result.is_valid:
                logger.warning("Final output blocked by security scanner")
                clean_response = output_scan_result.sanitized_text
            
            # Signal completion with final data
            yield {
                'type': 'complete',
                'content': clean_response,
                'full_response': clean_response
            }

            # --- Update Conversation State ---
            phase_manager.increment_turn()

        except Exception as e:
            logger.exception(f"Critical error in process_order_stream: {str(e)}")
            error_message = "I'm sorry, an unexpected error occurred during processing. Please try again later."
            yield {
                'type': 'error',
                'content': error_message
            }
        finally:
            # Always clear session context after processing completes
            clear_current_session()
            if worker_thread is not None:
                worker_thread.join(timeout=1)