# Agent with Threads Guide

Comprehensive guide to using Cortex Agents with conversation threads for building sophisticated multi-turn conversational AI applications.

## Overview

Combining Cortex Agents with thread management enables:

- **Contextual Conversations**: Agents remember previous exchanges and context
- **Complex Workflows**: Build multi-step data analysis conversations
- **User Session Management**: Track per-user conversations and state
- **Conversation Branching**: Explore different analysis paths
- **History Tracking**: Audit and review conversation flows

## Quick Start

### Basic Agent + Thread Workflow

```python
from cortex_agents import CortexAgent

DATABASE = "MY_DATABASE"
SCHEMA = "MY_SCHEMA"

with CortexAgent() as agent:
    # Step 1: Create thread for conversation
    # Note: origin_app is limited to 16 bytes (UTF-8 encoded)
    thread = agent.create_thread(origin_app="data_assistant")
    thread_id = thread["thread_id"]
    # Note: thread["thread_name"] is empty, use update_thread() to set a name

    # Step 2: First question
    response1 = agent.run(
        "What was our total revenue last quarter?",
        agent_name="SALES_AGENT",
        database=DATABASE,
        schema=SCHEMA,
        thread_id=thread_id,
        parent_message_id=0  # Root message
    )

    print(f"Q1: {response1.text}")
    if response1.sql:
        print(f"SQL: {response1.sql}")

    # Step 3: Follow-up question (agent has context)
    response2 = agent.run(
        "Which region performed best?",
        agent_name="SALES_AGENT",
        database=DATABASE,
        schema=SCHEMA,
        thread_id=thread_id,
        parent_message_id=response1.message_id
    )

    print(f"\nQ2: {response2.text}")

    # Step 4: Another follow-up
    response3 = agent.run(
        "Show me the trend over the last 4 quarters",
        agent_name="SALES_AGENT",
        database=DATABASE,
        schema=SCHEMA,
        thread_id=thread_id,
        parent_message_id=response2.message_id
    )

    print(f"\nQ3: {response3.text}")

    # Step 5: Review conversation
    thread_data = agent.get_thread(thread_id)
    print(f"\n✓ Conversation has {len(thread_data['messages'])} messages")

    # Step 6: Clean up
    agent.delete_thread(thread_id)
```

## Creating Agents for Thread-Based Conversations

### Agent Configuration for Conversations

```python
# Create agent optimized for conversations
agent.create_agent(
    name="CONVERSATIONAL_ANALYST",
    config={
        "comment": "Sales data analyst with conversational context",
        "instructions": {
            "system": """You are a helpful sales analyst assistant.
            Maintain context from previous messages in the conversation.
            Reference prior analysis when relevant.""",
            "response": """Provide clear, concise answers.
            If the user asks a follow-up question, build on previous context.""",
            "profile": "Expert in sales analytics and data interpretation"
        },
        "models": {
            "orchestration": "claude-sonnet-4-6"
        },
        "tools": [
            {
                "type": "builtin_function",
                "name": "QUERY_WAREHOUSE"
            }
        ]
    },
    database=DATABASE,
    schema=SCHEMA
)
```

## Streaming Responses in Threads

### Real-time Streaming with Context

```python
thread_id = agent.create_thread()["thread_id"]
parent_id = 0

questions = [
    "What was Q1 revenue?",
    "How does that compare to Q4?",
    "What drove the change?"
]

for i, question in enumerate(questions, 1):
    print(f"\n{'='*60}")
    print(f"Question {i}: {question}")
    print('='*60)

    response = agent.run(
        question,
        agent_name="CONVERSATIONAL_ANALYST",
        database=DATABASE,
        schema=SCHEMA,
        thread_id=thread_id,
        parent_message_id=parent_id
    )

    # Stream the response
    print("Agent: ", end="", flush=True)
    for event in response:
        if event["type"] == "text.delta":
            print(event["data"]["text"], end="", flush=True)
        elif event["type"] == "tool_use":
            print(f"\n[Using tool: {event['data']['name']}]", flush=True)
        elif event["type"] == "thinking.delta":
            # Optional: show agent's reasoning
            pass

    print()  # Newline after response
    parent_id = response.message_id  # Continue conversation chain
```

## Multi-Path Conversations

### Exploring Different Analysis Paths

```python
# Start conversation
thread_id = agent.create_thread()["thread_id"]

# Initial question
initial_response = agent.run(
    "Analyze our customer acquisition",
    agent_name="MARKETING_AGENT",
    database=DATABASE,
    schema=SCHEMA,
    thread_id=thread_id,
    parent_message_id=0
)

print(f"Initial Analysis: {initial_response.text}")
initial_msg_id = initial_response.message_id

# Path 1: Deep dive into channels
channel_response = agent.run(
    "Focus on acquisition channels - which performed best?",
    agent_name="MARKETING_AGENT",
    database=DATABASE,
    schema=SCHEMA,
    thread_id=thread_id,
    parent_message_id=initial_msg_id
)

print(f"\nChannel Analysis: {channel_response.text}")

# Path 2: Geographic analysis (alternate branch from same parent)
geo_response = agent.run(
    "Show me geographic breakdown instead",
    agent_name="MARKETING_AGENT",
    database=DATABASE,
    schema=SCHEMA,
    thread_id=thread_id,
    parent_message_id=initial_msg_id  # Same parent, different branch
)

print(f"\nGeographic Analysis: {geo_response.text}")

# Continue on channel path
channel_deep_dive = agent.run(
    "Compare channel performance to last year",
    agent_name="MARKETING_AGENT",
    database=DATABASE,
    schema=SCHEMA,
    thread_id=thread_id,
    parent_message_id=channel_response.message_id
)

# Conversation tree:
#           Initial
#          /       \
#    Channel      Geographic
#       |
# Channel Deep Dive
```

## Advanced Patterns

### Session Manager with Context Preservation

```python
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ConversationContext:
    """Track conversation context and metadata."""
    thread_id: str
    current_message_id: int
    agent_name: str
    database: str
    schema: str
    started_at: datetime
    last_activity: datetime
    message_count: int = 0

class ConversationalAgent:
    """Enhanced agent with conversation management."""

    def __init__(self, agent_name: str, database: str, schema: str):
        self.agent = CortexAgent()
        self.agent_name = agent_name
        self.database = database
        self.schema = schema
        self.contexts = {}  # session_id -> ConversationContext

    def start_conversation(self, session_id: str) -> str:
        """Initialize new conversation thread."""
        thread = self.agent.create_thread(origin_app=f"session_{session_id}")

        context = ConversationContext(
            thread_id=thread["thread_id"],
            current_message_id=0,
            agent_name=self.agent_name,
            database=self.database,
            schema=self.schema,
            started_at=datetime.now(),
            last_activity=datetime.now()
        )

        self.contexts[session_id] = context
        return context.thread_id

    def ask(self, session_id: str, question: str, stream: bool = True):
        """Ask question in conversation context."""
        if session_id not in self.contexts:
            self.start_conversation(session_id)

        context = self.contexts[session_id]

        response = self.agent.run(
            question,
            agent_name=context.agent_name,
            database=context.database,
            schema=context.schema,
            thread_id=context.thread_id,
            parent_message_id=context.current_message_id
        )

        # Update context
        context.current_message_id = response.message_id
        context.last_activity = datetime.now()
        context.message_count += 1

        if stream:
            return response  # Iterable for streaming
        else:
            # Consume stream and return text
            for _ in response:
                pass
            return response.text

    def get_history(self, session_id: str) -> list:
        """Retrieve conversation history."""
        if session_id not in self.contexts:
            return []

        context = self.contexts[session_id]
        thread = self.agent.get_thread(context.thread_id)

        return [
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg.get("created_on")
            }
            for msg in thread["messages"]
        ]

    def get_context_summary(self, session_id: str) -> Optional[dict]:
        """Get conversation context summary."""
        if session_id not in self.contexts:
            return None

        context = self.contexts[session_id]
        return {
            "thread_id": context.thread_id,
            "message_count": context.message_count,
            "started_at": context.started_at,
            "last_activity": context.last_activity,
            "duration_minutes": (
                context.last_activity - context.started_at
            ).total_seconds() / 60
        }

    def end_conversation(self, session_id: str):
        """End and cleanup conversation."""
        if session_id in self.contexts:
            context = self.contexts[session_id]
            self.agent.delete_thread(context.thread_id)
            del self.contexts[session_id]

    def cleanup_all(self):
        """Cleanup all active conversations."""
        for session_id in list(self.contexts.keys()):
            self.end_conversation(session_id)
        self.agent.close()

# Use the conversational agent
if __name__ == "__main__":
    conv_agent = ConversationalAgent(
        agent_name="DATA_ANALYST",
        database="ANALYTICS",
        schema="PUBLIC"
    )

    try:
        # User session
        session = "user_alice_123"
        conv_agent.start_conversation(session)

        # Interactive conversation
        questions = [
            "What was our revenue last month?",
            "Which products contributed most?",
            "Show me the trend for the top product"
        ]

        for question in questions:
            print(f"\nUser: {question}")
            print("Agent: ", end="", flush=True)

            response = conv_agent.ask(session, question, stream=True)

            # Stream response
            for event in response:
                if event["type"] == "text.delta":
                    print(event["data"]["text"], end="", flush=True)
            print()

        # Check conversation summary
        summary = conv_agent.get_context_summary(session)
        print(f"\n{'='*60}")
        print(f"Conversation Summary:")
        print(f"  Messages: {summary['message_count']}")
        print(f"  Duration: {summary['duration_minutes']:.1f} minutes")
        print('='*60)

    finally:
        conv_agent.cleanup_all()
```

### Contextual Follow-ups with Smart Routing

```python
class SmartConversationalAgent:
    """Agent that routes questions to appropriate specialists."""

    def __init__(self, database: str, schema: str):
        self.agent = CortexAgent()
        self.database = database
        self.schema = schema

        # Define specialist agents
        self.specialists = {
            "sales": "SALES_AGENT",
            "marketing": "MARKETING_AGENT",
            "finance": "FINANCE_AGENT",
            "operations": "OPERATIONS_AGENT"
        }

        self.router_agent = "ROUTER_AGENT"
        self.threads = {}  # specialist -> thread_id

    def route_question(self, question: str) -> str:
        """Determine which specialist should handle question."""
        routing_response = self.agent.run(
            f"""Categorize this question into one of: sales, marketing, finance, operations.

            Question: {question}

            Respond with just the category name.""",
            agent_name=self.router_agent,
            instructions={
                "system": "You are a question router. Respond with only the category."
            }
        )

        # Extract category
        category = routing_response.text.strip().lower()

        # Validate category
        if category not in self.specialists:
            category = "sales"  # Default fallback

        return category

    def ask_with_routing(self, question: str, session_id: str):
        """Ask question with automatic specialist routing."""
        # Route to specialist
        category = self.route_question(question)
        specialist = self.specialists[category]

        print(f"[Routing to {category} specialist: {specialist}]")

        # Get or create thread for this specialist
        thread_key = f"{session_id}_{category}"
        if thread_key not in self.threads:
            thread = self.agent.create_thread(
                origin_app=f"{session_id[:5]}_{category[:8]}"  # Ensure stays under 16 bytes
            )
            self.threads[thread_key] = {
                "thread_id": thread["thread_id"],
                "current_message_id": 0
            }

        thread_info = self.threads[thread_key]

        # Run with specialist
        response = self.agent.run(
            question,
            agent_name=specialist,
            database=self.database,
            schema=self.schema,
            thread_id=thread_info["thread_id"],
            parent_message_id=thread_info["current_message_id"]
        )

        # Update thread state
        thread_info["current_message_id"] = response.message_id

        return response, category

    def cleanup(self):
        """Cleanup all threads."""
        for thread_info in self.threads.values():
            self.agent.delete_thread(thread_info["thread_id"])
        self.agent.close()

# Use smart routing
smart_agent = SmartConversationalAgent(database="ANALYTICS", schema="PUBLIC")

try:
    session = "user_session_1"

    # Mixed questions - automatically routed
    questions = [
        "What was our Q1 revenue?",           # -> sales
        "How many new leads did we get?",     # -> marketing
        "What's our cash flow status?",       # -> finance
        "What about Q2 revenue?",             # -> sales (continues thread)
    ]

    for question in questions:
        print(f"\nQ: {question}")
        response, category = smart_agent.ask_with_routing(question, session)
        print(f"A [{category}]: {response.text}")

finally:
    smart_agent.cleanup()
```

### Async Multi-User Conversations

```python
import asyncio
from cortex_agents import AsyncCortexAgent

class AsyncMultiUserAgent:
    """Handle multiple concurrent user conversations."""

    def __init__(self, agent_name: str, database: str, schema: str):
        self.agent_name = agent_name
        self.database = database
        self.schema = schema
        self.user_contexts = {}  # user_id -> context
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize async agent."""
        self.agent = AsyncCortexAgent()
        return self

    async def start_user_conversation(self, user_id: str):
        """Start conversation for user."""
        async with self._lock:
            thread = await self.agent.create_thread(
                origin_app=f"user_{user_id[:10]}"  # Truncate to ensure under 16 bytes
            )

            self.user_contexts[user_id] = {
                "thread_id": thread["thread_id"],
                "current_message_id": 0
            }

            return thread["thread_id"]

    async def process_user_message(self, user_id: str, message: str):
        """Process message for specific user."""
        # Ensure user has context
        if user_id not in self.user_contexts:
            await self.start_user_conversation(user_id)

        context = self.user_contexts[user_id]

        # Run agent
        response = await self.agent.run(
            message,
            agent_name=self.agent_name,
            database=self.database,
            schema=self.schema,
            thread_id=context["thread_id"],
            parent_message_id=context["current_message_id"]
        )

        # Update context
        context["current_message_id"] = response.message_id

        # Collect response text
        text_parts = []
        async for event in response.astream():
            if event["type"] == "text.delta":
                text_parts.append(event["data"]["text"])

        return "".join(text_parts)

    async def cleanup(self):
        """Cleanup all user threads."""
        tasks = [
            self.agent.delete_thread(ctx["thread_id"])
            for ctx in self.user_contexts.values()
        ]
        await asyncio.gather(*tasks)
        await self.agent.close()

async def handle_multiple_users():
    """Simulate multiple users chatting concurrently."""
    multi_agent = await AsyncMultiUserAgent(
        agent_name="SUPPORT_AGENT",
        database="ANALYTICS",
        schema="PUBLIC"
    ).initialize()

    try:
        # Simulate 3 users asking questions concurrently
        user_conversations = [
            ("alice", ["What's our revenue?", "Show by region"]),
            ("bob", ["How many customers?", "Growth rate?"]),
            ("charlie", ["Top products?", "Sales trends?"])
        ]

        async def user_conversation(user_id: str, questions: list):
            """Handle one user's conversation."""
            await multi_agent.start_user_conversation(user_id)

            for question in questions:
                print(f"\n[{user_id}] Q: {question}")
                response = await multi_agent.process_user_message(
                    user_id, question
                )
                print(f"[{user_id}] A: {response[:100]}...")

                # Simulate think time
                await asyncio.sleep(0.5)

        # Run all conversations concurrently
        await asyncio.gather(
            *[user_conversation(uid, questions)
              for uid, questions in user_conversations]
        )

        print(f"\n✓ Handled {len(user_conversations)} concurrent users")

    finally:
        await multi_agent.cleanup()

# Run async example
asyncio.run(handle_multiple_users())
```

## Working with Response Components

### Extracting Charts and Tables from Threaded Conversations

```python
from cortex_agents.chart_utils import plot_charts

# Start data exploration thread
thread_id = agent.create_thread()["thread_id"]
parent_id = 0

# Ask for visualization
response = agent.run(
    "Show me monthly revenue as a chart",
    agent_name="ANALYTICS_AGENT",
    database=DATABASE,
    schema=SCHEMA,
    thread_id=thread_id,
    parent_message_id=parent_id
)

# Extract charts
charts = response.get_charts()
if charts:
    print(f"Generated {len(charts)} chart(s)")
    plot_charts(charts, interactive=True)

# Extract tables
tables = response.get_tables()
if tables:
    print(f"Generated {len(tables)} table(s)")
    for table in tables:
        print(f"Table: {table.get('title')}")

# Continue conversation
parent_id = response.message_id
response2 = agent.run(
    "Now show me quarterly comparison",
    agent_name="ANALYTICS_AGENT",
    database=DATABASE,
    schema=SCHEMA,
    thread_id=thread_id,
    parent_message_id=parent_id
)

print(response2.text)
```

## Feedback Integration in Conversations

### Collecting User Feedback

```python
thread_id = agent.create_thread()["thread_id"]
parent_id = 0

# Ask question
response = agent.run(
    "What were our top 5 products last quarter?",
    agent_name="PRODUCT_AGENT",
    database=DATABASE,
    schema=SCHEMA,
    thread_id=thread_id,
    parent_message_id=parent_id
)

print(f"Response: {response.text}")

# User reviews and provides feedback
user_rating = input("Was this helpful? (y/n): ")

if user_rating.lower() == 'y':
    agent.submit_feedback(
        agent_name="PRODUCT_AGENT",
        database=DATABASE,
        schema=SCHEMA,
        positive=True,
        feedback_message="Accurate and helpful analysis",
        categories=["accurate", "helpful"]
    )
else:
    feedback_text = input("What went wrong? ")
    agent.submit_feedback(
        agent_name="PRODUCT_AGENT",
        database=DATABASE,
        schema=SCHEMA,
        positive=False,
        feedback_message=feedback_text,
        categories=["needs_improvement"]
    )

# Continue conversation based on feedback
if user_rating.lower() == 'n':
    # Clarification round
    response2 = agent.run(
        "Let me rephrase: I need more detail on product performance",
        agent_name="PRODUCT_AGENT",
        database=DATABASE,
        schema=SCHEMA,
        thread_id=thread_id,
        parent_message_id=response.message_id
    )
    print(f"Clarified response: {response2.text}")
```

## Best Practices

### 1. Initialize Threads Early

```python
# Start thread at beginning of session
thread_id = agent.create_thread(origin_app="my_app")["thread_id"]

# Use throughout session
# ...

# Clean up at end
agent.delete_thread(thread_id)
```

### 2. Track Message IDs Carefully

```python
# Always maintain current message ID
current_msg_id = 0

for question in questions:
    response = agent.run(
        question,
        agent_name="AGENT",
        thread_id=thread_id,
        parent_message_id=current_msg_id
    )
    current_msg_id = response.message_id  # Update for next message
```

### 3. Use Descriptive Thread Names

```python
thread = agent.create_thread()
thread_id = thread["thread_id"]

# After first meaningful exchange
agent.update_thread(thread_id, name="Q1 Sales Analysis - Alice")
```

### 4. Implement Timeout/Cleanup Logic

```python
from datetime import datetime, timedelta

class ThreadManager:
    def __init__(self, agent: CortexAgent, timeout_minutes: int = 30):
        self.agent = agent
        self.timeout = timedelta(minutes=timeout_minutes)
        self.active_threads = {}  # thread_id -> last_activity

    def cleanup_stale_threads(self):
        """Remove threads inactive for too long."""
        now = datetime.now()
        stale_threads = [
            tid for tid, last_active in self.active_threads.items()
            if now - last_active > self.timeout
        ]

        for thread_id in stale_threads:
            self.agent.delete_thread(thread_id)
            del self.active_threads[thread_id]

        return len(stale_threads)
```

### 5. Handle Errors Gracefully

```python
from cortex_agents.base import SnowflakeAPIError

try:
    response = agent.run(
        question,
        agent_name="AGENT",
        thread_id=thread_id,
        parent_message_id=parent_id
    )
except SnowflakeAPIError as e:
    if e.status_code == 404:
        # Thread deleted, create new one
        thread_id = agent.create_thread()["thread_id"]
        parent_id = 0
        # Retry
        response = agent.run(
            question,
            agent_name="AGENT",
            thread_id=thread_id,
            parent_message_id=parent_id
        )
    else:
        raise
```

### 6. Paginate Long Thread Histories

```python
def get_full_history(agent: CortexAgent, thread_id: str) -> list:
    """Get all messages from long thread."""
    all_messages = []
    last_msg_id = None

    while True:
        thread = agent.get_thread(
            thread_id,
            limit=50,
            last_message_id=last_msg_id
        )

        if not thread["messages"]:
            break

        all_messages.extend(thread["messages"])
        last_msg_id = thread["messages"][-1]["message_id"]

        if len(thread["messages"]) < 50:
            break

    return all_messages
```

## Complete Example: Full-Featured Conversational App

```python
"""
Production-ready conversational agent with all features.
"""
from cortex_agents import CortexAgent
from cortex_agents.base import SnowflakeAPIError
from datetime import datetime, timedelta
from typing import Optional
import json

class ProductionConversationalAgent:
    """Production-grade conversational agent with full features."""

    def __init__(self, agent_name: str, database: str, schema: str):
        self.agent = CortexAgent()
        self.agent_name = agent_name
        self.database = database
        self.schema = schema
        self.sessions = {}
        self.session_timeout = timedelta(hours=1)

    def create_session(self, user_id: str, metadata: dict = None) -> str:
        """Create new conversation session."""
        thread = self.agent.create_thread(
            origin_app=f"app_user_{user_id[:8]}"  # Keep under 16 bytes
        )

        session_id = f"{user_id}_{datetime.now().timestamp()}"
        self.sessions[session_id] = {
            "user_id": user_id,
            "thread_id": thread["thread_id"],
            "current_message_id": 0,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "metadata": metadata or {},
            "message_count": 0
        }

        return session_id

    def send_message(self, session_id: str, message: str,
                    stream_callback=None) -> dict:
        """Send message and get response."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.sessions[session_id]

        try:
            response = self.agent.run(
                message,
                agent_name=self.agent_name,
                database=self.database,
                schema=self.schema,
                thread_id=session["thread_id"],
                parent_message_id=session["current_message_id"]
            )

            # Stream if callback provided
            text_parts = []
            for event in response:
                if event["type"] == "text.delta":
                    text_parts.append(event["data"]["text"])
                    if stream_callback:
                        stream_callback(event["data"]["text"])

            # Update session
            session["current_message_id"] = response.message_id
            session["last_activity"] = datetime.now()
            session["message_count"] += 1

            return {
                "text": "".join(text_parts),
                "sql": response.sql,
                "message_id": response.message_id,
                "request_id": response.request_id,
                "charts": response.get_charts(),
                "tables": response.get_tables()
            }

        except SnowflakeAPIError as e:
            return {
                "error": str(e),
                "status_code": e.status_code,
                "request_id": e.request_id
            }

    def get_session_history(self, session_id: str) -> list:
        """Get full conversation history."""
        if session_id not in self.sessions:
            return []

        session = self.sessions[session_id]
        thread = self.agent.get_thread(session["thread_id"])

        return thread["messages"]

    def submit_user_feedback(self, session_id: str, message_id: int,
                            positive: bool, comment: str = None):
        """Submit user feedback on response."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        self.agent.submit_feedback(
            agent_name=self.agent_name,
            database=self.database,
            schema=self.schema,
            positive=positive,
            feedback_message=comment
        )

    def cleanup_stale_sessions(self) -> int:
        """Remove inactive sessions."""
        now = datetime.now()
        stale = []

        for sid, session in self.sessions.items():
            if now - session["last_activity"] > self.session_timeout:
                stale.append(sid)

        for sid in stale:
            self.end_session(sid)

        return len(stale)

    def end_session(self, session_id: str):
        """End and cleanup session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]

            # Archive session (optional)
            self._archive_session(session_id, session)

            # Delete thread
            self.agent.delete_thread(session["thread_id"])
            del self.sessions[session_id]

    def _archive_session(self, session_id: str, session: dict):
        """Archive session to file."""
        archive_data = {
            "session_id": session_id,
            "user_id": session["user_id"],
            "created_at": session["created_at"].isoformat(),
            "ended_at": datetime.now().isoformat(),
            "message_count": session["message_count"],
            "metadata": session["metadata"]
        }

        filename = f"archives/session_{session_id}.json"
        with open(filename, "w") as f:
            json.dump(archive_data, f, indent=2)

    def shutdown(self):
        """Gracefully shutdown and cleanup all sessions."""
        for session_id in list(self.sessions.keys()):
            self.end_session(session_id)
        self.agent.close()

# Use in production
if __name__ == "__main__":
    app = ProductionConversationalAgent(
        agent_name="SALES_ASSISTANT",
        database="ANALYTICS",
        schema="PUBLIC"
    )

    try:
        # Create user session
        session = app.create_session(
            user_id="alice@company.com",
            metadata={"department": "sales", "role": "manager"}
        )

        # Interactive conversation
        questions = [
            "What was our revenue last month?",
            "Which products performed best?",
            "Show me the trend"
        ]

        for question in questions:
            print(f"\nUser: {question}")

            # Stream response
            print("Agent: ", end="", flush=True)
            result = app.send_message(
                session,
                question,
                stream_callback=lambda text: print(text, end="", flush=True)
            )
            print()

            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                # User provides feedback
                app.submit_user_feedback(
                    session,
                    result["message_id"],
                    positive=True,
                    comment="Helpful response"
                )

        # Get history
        history = app.get_session_history(session)
        print(f"\n✓ Session completed with {len(history)} messages")

    finally:
        app.shutdown()
```

## Next Steps

- Review [Thread Management Guide](threads_api.md) for thread-specific operations
- See [Agent API Reference](../api/agent.md) for detailed method documentation
- Explore [Async Agent](../api/async_agent.md) for scalable concurrent operations
- Check [Examples](agents.md) for more patterns and use cases
