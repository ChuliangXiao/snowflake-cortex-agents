# Thread Management Guide

Comprehensive guide to using conversation threads with Cortex Agents for multi-turn conversations and context management.

## Overview

Threads enable stateful, multi-turn conversations with Cortex Agents. They provide:

- **Conversation Context**: Agents remember previous exchanges
- **Message History**: Track and retrieve conversation history
- **Branching Conversations**: Create alternate conversation paths
- **Session Management**: Organize conversations by user or topic
- **Thread Metadata**: Track creation time, origin, and custom names

## Important: The `origin_app` Parameter

The `origin_app` parameter helps you track which application created a thread, but has an important constraint:

!!! warning "16-Byte Limit"
    The `origin_app` parameter is **limited to 16 bytes (UTF-8 encoded)**. If you exceed this limit, a `ValueError` will be raised.

**Examples:**
```python
# ✓ Valid (within 16 bytes)
thread = agent.create_thread(origin_app="my_app")            # 6 bytes
thread = agent.create_thread(origin_app="chatbot_v1")        # 10 bytes
thread = agent.create_thread(origin_app="app123")            # 6 bytes

# ✗ Invalid (exceeds 16 bytes)
thread = agent.create_thread(origin_app="very_long_chatbot_name")  # 24 bytes - ERROR!
```

## Quick Start

### Basic Thread Usage

```python
from cortex_agents import CortexAgent

with CortexAgent() as agent:
    # Create a thread with origin tracking (within 16 bytes)
    thread = agent.create_thread(origin_app="app_v1")
    thread_id = thread["thread_id"]

    # First message
    response1 = agent.run(
        "What was our Q1 revenue?",
        agent_name="SALES_AGENT",
        database="MY_DB",
        schema="MY_SCHEMA",
        thread_id=thread_id,
        parent_message_id=0  # Root of conversation
    )

    # Follow-up message (maintains context)
    response2 = agent.run(
        "How does that compare to Q2?",
        agent_name="SALES_AGENT",
        database="MY_DB",
        schema="MY_SCHEMA",
        thread_id=thread_id,
        parent_message_id=response1.message_id
    )

    # Retrieve thread history
    thread_data = agent.get_thread(thread_id)
    print(f"Thread has {len(thread_data['messages'])} messages")

    # Clean up
    agent.delete_thread(thread_id)
```

## Thread Lifecycle

### Creating Threads

```python
# Basic thread creation
thread = agent.create_thread()
thread_id = thread["thread_id"]
thread_name = thread["thread_name"]  # Empty by default
created_on = thread["created_on"]    # datetime object
updated_on = thread["updated_on"]    # datetime object

# Create thread with origin tracking (max 16 bytes)
thread = agent.create_thread(origin_app="my_chatbot_v1")
print(f"Created thread {thread['thread_id']} from {thread['origin_application']}")

# Set a meaningful name (thread_name is empty by default)
agent.update_thread(thread_id, name="Customer Support Chat")
```

### Listing Threads

```python
# List all threads
all_threads = agent.list_threads()
for thread in all_threads:
    print(f"ID: {thread['thread_id']}")
    print(f"Name: {thread['thread_name']}")
    print(f"Created: {thread['created_on']}")
    print(f"Origin: {thread['origin_application']}")
    print()

# Filter by origin application
app_threads = agent.list_threads(origin_app="my_chatbot_v1")
print(f"Found {len(app_threads)} threads from my_chatbot_v1")
```

### Retrieving Thread Details

```python
# Get thread with default pagination (20 messages)
thread = agent.get_thread(thread_id)

# Get more messages
thread = agent.get_thread(thread_id, limit=50)

# Paginate through messages
thread_page1 = agent.get_thread(thread_id, limit=20)
last_msg_id = thread_page1["messages"][-1]["message_id"]
thread_page2 = agent.get_thread(thread_id, limit=20, last_message_id=last_msg_id)

# Access messages
for message in thread["messages"]:
    print(f"[{message['role']}]: {message['content']}")
```

### Updating Threads

```python
# Rename a thread
agent.update_thread(thread_id, name="Q1 Sales Analysis")

# Verify update
thread = agent.get_thread(thread_id)
print(f"Thread renamed to: {thread['thread_name']}")
```

### Deleting Threads

```python
# Delete a single thread
result = agent.delete_thread(thread_id)
print(f"Thread {thread_id} deleted")

# Delete all threads from an application
threads = agent.list_threads(origin_app="temp_app")
for thread in threads:
    agent.delete_thread(thread["thread_id"])
print(f"Deleted {len(threads)} threads")
```

## Multi-Turn Conversations

### Linear Conversation

```python
with CortexAgent() as agent:
    thread_id = agent.create_thread()["thread_id"]
    parent_id = 0  # Start at root

    questions = [
        "What was our revenue last quarter?",
        "Which product contributed most?",
        "Show me the trend over the last 4 quarters",
        "What's the forecast for next quarter?"
    ]

    for question in questions:
        response = agent.run(
            question,
            agent_name="SALES_AGENT",
            database="MY_DB",
            schema="MY_SCHEMA",
            thread_id=thread_id,
            parent_message_id=parent_id
        )

        print(f"Q: {question}")
        print(f"A: {response.text}\n")

        parent_id = response.message_id  # Continue chain
```

### Branching Conversations

Create alternate conversation paths:

```python
thread_id = agent.create_thread()["thread_id"]

# Main conversation path
response1 = agent.run(
    "Show me sales by region",
    agent_name="AGENT",
    thread_id=thread_id,
    parent_message_id=0
)

# Branch 1: Focus on East region
branch1_response = agent.run(
    "Tell me more about the East region",
    agent_name="AGENT",
    thread_id=thread_id,
    parent_message_id=response1.message_id
)

# Branch 2: Focus on West region (alternate path)
branch2_response = agent.run(
    "What about the West region?",
    agent_name="AGENT",
    thread_id=thread_id,
    parent_message_id=response1.message_id  # Same parent, different branch
)

# Visualize structure:
#       0 (root)
#         |
#    response1 ("sales by region")
#      /     \
# branch1   branch2
# (East)    (West)
```

## Message Structure

### Understanding Messages

```python
thread = agent.get_thread(thread_id)

for message in thread["messages"]:
    # Message metadata
    message_id = message["message_id"]
    parent_id = message["parent_message_id"]
    role = message["role"]  # "user" or "assistant"
    content = message["content"]
    timestamp = message["created_on"]

    print(f"[{role}] Message {message_id} (parent: {parent_id})")
    print(f"Content: {content}")
    print(f"Created: {timestamp}\n")
```

### Message Hierarchy

```python
def print_thread_tree(thread_data, parent_id=0, depth=0):
    """Recursively print thread message tree."""
    messages = thread_data["messages"]

    for msg in messages:
        if msg["parent_message_id"] == parent_id:
            indent = "  " * depth
            print(f"{indent}[{msg['role']}] {msg['content'][:50]}...")

            # Recursively print children
            print_thread_tree(thread_data, msg["message_id"], depth + 1)

# Use it
thread = agent.get_thread(thread_id)
print_thread_tree(thread)

# Output example:
# [user] What was our Q1 revenue?
#   [assistant] Q1 revenue was $1.2M...
#     [user] How does that compare to Q2?
#       [assistant] Q2 revenue was $1.5M, a 25% increase...
#     [user] What about Q3?
#       [assistant] Q3 revenue was $1.8M...
```

## Async Thread Management

### Basic Async Operations

```python
import asyncio
from cortex_agents import AsyncCortexAgent

async def async_thread_example():
    async with AsyncCortexAgent() as agent:
        # Create thread
        thread = await agent.create_thread(origin_app="async_app")
        thread_id = thread["thread_id"]

        # Have conversation
        response1 = await agent.run(
            "What's our customer count?",
            agent_name="AGENT",
            thread_id=thread_id,
            parent_message_id=0
        )

        response2 = await agent.run(
            "How many are active?",
            agent_name="AGENT",
            thread_id=thread_id,
            parent_message_id=response1.message_id
        )

        # Get thread
        thread_data = await agent.get_thread(thread_id)
        print(f"Messages: {len(thread_data['messages'])}")

        # Clean up
        await agent.delete_thread(thread_id)

asyncio.run(async_thread_example())
```

### Concurrent Thread Operations

```python
async def manage_multiple_threads():
    async with AsyncCortexAgent() as agent:
        # Create multiple threads concurrently
        threads = await asyncio.gather(
            agent.create_thread(origin_app="app1"),
            agent.create_thread(origin_app="app2"),
            agent.create_thread(origin_app="app3")
        )

        thread_ids = [t["thread_id"] for t in threads]
        print(f"Created {len(thread_ids)} threads")

        # Run queries in parallel across threads
        responses = await asyncio.gather(
            agent.run("Query 1", agent_name="A", thread_id=thread_ids[0], parent_message_id=0),
            agent.run("Query 2", agent_name="A", thread_id=thread_ids[1], parent_message_id=0),
            agent.run("Query 3", agent_name="A", thread_id=thread_ids[2], parent_message_id=0)
        )

        # Delete all threads concurrently
        await asyncio.gather(*[agent.delete_thread(tid) for tid in thread_ids])

asyncio.run(manage_multiple_threads())
```

## Advanced Patterns

### Session Management

Track user sessions with threads:

```python
class UserSession:
    def __init__(self, user_id: str, agent: CortexAgent):
        self.user_id = user_id
        self.agent = agent
        self.thread_id = None
        self.current_message_id = 0

    def start_session(self):
        """Create a new conversation thread for user."""
        thread = self.agent.create_thread(origin_app=f"user_{self.user_id[:8]}")  # Keep under 16 bytes
        self.thread_id = thread["thread_id"]
        self.current_message_id = 0
        return self.thread_id

    def send_message(self, message: str, agent_name: str):
        """Send message in user's thread."""
        response = self.agent.run(
            message,
            agent_name=agent_name,
            thread_id=self.thread_id,
            parent_message_id=self.current_message_id
        )
        self.current_message_id = response.message_id
        return response

    def get_history(self):
        """Get conversation history."""
        return self.agent.get_thread(self.thread_id)

    def end_session(self):
        """Clean up session thread."""
        if self.thread_id:
            self.agent.delete_thread(self.thread_id)

# Use it
with CortexAgent() as agent:
    session = UserSession("user123", agent)
    session.start_session()

    session.send_message("What's our revenue?", "SALES_AGENT")
    session.send_message("Show me by region", "SALES_AGENT")

    history = session.get_history()
    print(f"Session had {len(history['messages'])} exchanges")

    session.end_session()
```

### Thread Archival

Archive old threads before deletion:

```python
import json
from datetime import datetime, timedelta

def archive_old_threads(agent: CortexAgent, days_old: int = 30):
    """Archive threads older than specified days."""
    cutoff_date = datetime.now() - timedelta(days=days_old)
    threads = agent.list_threads()

    archived = []
    for thread in threads:
        if thread["created_on"] < cutoff_date:
            # Get full thread data
            thread_data = agent.get_thread(thread["thread_id"])

            # Save to file
            filename = f"archive/thread_{thread['thread_id']}.json"
            with open(filename, "w") as f:
                json.dump(thread_data, f, default=str)

            # Delete from Snowflake
            agent.delete_thread(thread["thread_id"])
            archived.append(thread["thread_id"])

    print(f"Archived {len(archived)} threads")
    return archived

# Use it
with CortexAgent() as agent:
    archive_old_threads(agent, days_old=30)
```

### Conversation Summarization

Summarize long threads:

```python
def summarize_thread(agent: CortexAgent, thread_id: str) -> str:
    """Generate summary of thread conversation."""
    thread = agent.get_thread(thread_id, limit=100)

    # Build conversation text
    conversation = []
    for msg in thread["messages"]:
        conversation.append(f"{msg['role']}: {msg['content']}")

    conversation_text = "\n".join(conversation)

    # Use agent to summarize
    summary_response = agent.run(
        f"Summarize this conversation:\n\n{conversation_text}",
        agent_name="SUMMARIZER_AGENT",
        instructions={"system": "You are a conversation summarizer."}
    )

    return summary_response.text

# Use it
with CortexAgent() as agent:
    summary = summarize_thread(agent, thread_id)
    print(f"Thread Summary:\n{summary}")
```

### Thread Search

Find threads by content:

```python
def search_threads(agent: CortexAgent, search_term: str) -> list:
    """Find threads containing specific content."""
    matching_threads = []
    threads = agent.list_threads()

    for thread_info in threads:
        thread = agent.get_thread(thread_info["thread_id"], limit=100)

        # Search messages
        for message in thread["messages"]:
            if search_term.lower() in message["content"].lower():
                matching_threads.append({
                    "thread_id": thread_info["thread_id"],
                    "thread_name": thread_info["thread_name"],
                    "message": message["content"][:100]
                })
                break  # Found in this thread

    return matching_threads

# Use it
with CortexAgent() as agent:
    results = search_threads(agent, "revenue")
    print(f"Found '{search_term}' in {len(results)} threads")
    for result in results:
        print(f"- {result['thread_name']}: {result['message']}...")
```

## Best Practices

### 1. Always Clean Up Threads

```python
# Use context managers
with CortexAgent() as agent:
    thread_id = agent.create_thread()["thread_id"]
    try:
        # Use thread
        pass
    finally:
        agent.delete_thread(thread_id)
```

### 2. Track Origin Applications

```python
# Tag threads by application for easy filtering
thread = agent.create_thread(origin_app="my_app_v2")
```

### 3. Name Threads Meaningfully

```python
thread = agent.create_thread()
thread_id = thread["thread_id"]
# Note: thread["thread_name"] is empty at this point

# Ask first question
first_response = agent.run(
    "Analyze Q1 sales",
    agent_name="AGENT",
    thread_id=thread_id,
    parent_message_id=0
)

# Set meaningful name based on first question
agent.update_thread(thread_id, name="Q1 Sales Analysis")
```

### 4. Implement Pagination for Long Threads

```python
def get_all_messages(agent: CortexAgent, thread_id: str) -> list:
    """Retrieve all messages from a thread."""
    all_messages = []
    last_message_id = None

    while True:
        thread = agent.get_thread(
            thread_id,
            limit=50,
            last_message_id=last_message_id
        )

        messages = thread["messages"]
        if not messages:
            break

        all_messages.extend(messages)
        last_message_id = messages[-1]["message_id"]

        if len(messages) < 50:  # Last page
            break

    return all_messages
```

### 5. Handle Thread Errors Gracefully

```python
from cortex_agents.base import SnowflakeAPIError

try:
    thread = agent.get_thread(thread_id)
except SnowflakeAPIError as e:
    if e.status_code == 404:
        print("Thread not found, creating new one")
        thread = agent.create_thread()
    else:
        raise
```

### 6. Maintain Message ID Chain

```python
# Always track the current message ID
current_message_id = 0

response = agent.run(..., parent_message_id=current_message_id)
current_message_id = response.message_id  # Update for next message
```

## Complete Example: Chatbot with Thread Management

```python
"""
Complete chatbot with thread management, history, and cleanup.
"""
from cortex_agents import CortexAgent
from datetime import datetime

class ChatBot:
    def __init__(self, agent_name: str, database: str, schema: str):
        self.agent = CortexAgent()
        self.agent_name = agent_name
        self.database = database
        self.schema = schema
        self.sessions = {}  # user_id -> thread_info

    def start_chat(self, user_id: str) -> str:
        """Start new chat session for user."""
        thread = self.agent.create_thread(origin_app=f"bot_{user_id[:9]}")  # Keep under 16 bytes

        self.sessions[user_id] = {
            "thread_id": thread["thread_id"],
            "current_message_id": 0,
            "started_at": datetime.now()
        }

        return thread["thread_id"]

    def send_message(self, user_id: str, message: str) -> str:
        """Send message in user's chat session."""
        if user_id not in self.sessions:
            self.start_chat(user_id)

        session = self.sessions[user_id]

        response = self.agent.run(
            message,
            agent_name=self.agent_name,
            database=self.database,
            schema=self.schema,
            thread_id=session["thread_id"],
            parent_message_id=session["current_message_id"]
        )

        # Update message chain
        session["current_message_id"] = response.message_id

        return response.text

    def get_history(self, user_id: str) -> list:
        """Get user's chat history."""
        if user_id not in self.sessions:
            return []

        thread_id = self.sessions[user_id]["thread_id"]
        thread = self.agent.get_thread(thread_id)

        return [
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["created_on"]
            }
            for msg in thread["messages"]
        ]

    def end_chat(self, user_id: str):
        """End chat session for user."""
        if user_id in self.sessions:
            thread_id = self.sessions[user_id]["thread_id"]
            self.agent.delete_thread(thread_id)
            del self.sessions[user_id]

    def cleanup_all(self):
        """Clean up all active sessions."""
        for user_id in list(self.sessions.keys()):
            self.end_chat(user_id)
        self.agent.close()

# Use the chatbot
if __name__ == "__main__":
    bot = ChatBot(
        agent_name="SALES_ASSISTANT",
        database="ANALYTICS",
        schema="PUBLIC"
    )

    try:
        # User 1 conversation
        user1 = "alice"
        bot.start_chat(user1)
        print(bot.send_message(user1, "What was Q1 revenue?"))
        print(bot.send_message(user1, "How about Q2?"))

        # User 2 conversation
        user2 = "bob"
        bot.start_chat(user2)
        print(bot.send_message(user2, "Show me customer count"))

        # Get history
        history = bot.get_history(user1)
        print(f"\nAlice's history: {len(history)} messages")

    finally:
        # Clean up
        bot.cleanup_all()
```

## Next Steps

- Explore [API Reference](../api/core_threads.md) for detailed method documentation
- See [Agent Guide](../quickstart.md) for agent-specific features
- Learn about [Async Operations](../api/async_agent.md) for scalable applications
- Check [Examples](agents.md) for more code samples
