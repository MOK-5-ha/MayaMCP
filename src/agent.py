# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo
import os

if os.getenv("INTEGRATION_TEST") == "TRUE":
    # Set dummy keys
    os.environ["GEMINI_API_KEY"] = "dummy-key"
    os.environ["CARTESIA_API_KEY"] = "dummy-key"
    
    try:
        import google.genai
        from google.genai import types
        from types import SimpleNamespace as NS

        class MockCandidate:
            def __init__(self, text):
                self.finish_reason = types.FinishReason.STOP
                self.finish_message = ""
                self.content = types.Content(role="model", parts=[types.Part.from_text(text=text)])
            def __getattr__(self, name):
                return None

        class MockResponse:
            def __init__(self, text):
                self.candidates = [MockCandidate(text)]
                self.usage_metadata = NS(prompt_token_count=10, candidates_token_count=10, total_token_count=20)
                self.grounding_metadata = None
                self.citation_metadata = None
            def __getattr__(self, name):
                return None

        class MockModelsAsync:
            async def generate_content_stream(self, model, contents, config=None):
                async def _stream():
                    yield MockResponse("This is a mock streaming response from Gemini.")
                return _stream()
            async def generate_content(self, model, contents, config=None):
                return MockResponse("This is a mock response from Gemini.")

        class MockModelsSync:
            def generate_content(self, model, contents, config=None):
                return MockResponse("This is a mock response from Gemini.")
            def generate_content_stream(self, model, contents, config=None):
                yield MockResponse("This is a mock response from Gemini.")
            def embed_content(self, model, contents, config=None):
                if isinstance(contents, list):
                    return types.EmbedContentResponse(embeddings=[types.Embedding(values=[0.1]*768) for _ in contents])
                return types.EmbedContentResponse(embeddings=[types.Embedding(values=[0.1]*768)])

        class MockAio:
            def __init__(self):
                self.models = MockModelsAsync()

        # Override properties on Client class
        google.genai.Client.models = property(lambda self: MockModelsSync())
        google.genai.Client.aio = property(lambda self: MockAio())
    except Exception:
        pass

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# TODO: Replace with Maya's bartending agent persona and tools if routing A2A requests directly here.
root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are a helpful AI assistant designed to provide accurate and useful information.",
    tools=[get_weather, get_current_time],
)

app = App(
    root_agent=root_agent,
    name="src",
)
