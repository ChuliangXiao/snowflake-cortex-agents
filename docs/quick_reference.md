# Documentation Quick Reference

This page provides a quick overview of all available documentation for the Snowflake Cortex Agents SDK.

## 🚀 Getting Started

| Document                        | Description                | Best For            |
| ------------------------------- | -------------------------- | ------------------- |
| [Installation](installation.md) | Setup and dependencies     | First-time users    |
| [Quick Start](quickstart.md)    | 5-minute intro to the SDK  | New users           |
| [Examples](guides/agents.md)    | Code snippets and patterns | Learning by example |

## 📖 Comprehensive Guides

### Cortex Analyst Guide
**[Read the full guide →](guides/analyst.md)**

Complete guide to generating SQL from natural language using Cortex Analyst.

**Key Topics:**
- Basic SQL generation
- Semantic models vs views
- Multi-model selection
- Streaming responses
- Multi-turn conversations
- Handling ambiguous questions
- Feedback submission
- Async operations
- Best practices

**Example:**
```python
from cortex_agents import CortexAnalyst

with CortexAnalyst() as analyst:
    response = analyst.message(
        question="What was Q1 revenue?",
        semantic_view="ANALYTICS.PUBLIC.SALES_VIEW"
    )
    print(response.sql)
```

### Thread Management Guide
**[Read the full guide →](guides/threads_api.md)**

Comprehensive guide to managing conversation threads for stateful, multi-turn conversations.

**Key Topics:**
- Thread lifecycle (create, list, get, update, delete)
- Multi-turn conversations
- Branching conversations
- Message hierarchy
- Async thread operations
- Session management patterns
- Thread archival
- Conversation search
- Best practices

**Example:**
```python
from cortex_agents import CortexAgent

with CortexAgent() as agent:
    # Create thread with origin_app (max 16 bytes)
    thread = agent.create_thread(origin_app="my_app")
    thread_id = thread["thread_id"]

    # Multi-turn conversation
    response1 = agent.run(
        "What was Q1 revenue?",
        agent_name="AGENT",
        thread_id=thread_id,
        parent_message_id=0
    )

    response2 = agent.run(
        "How about Q2?",
        agent_name="AGENT",
        thread_id=thread_id,
        parent_message_id=response1.message_id
    )
```

### Agent with Threads Guide
**[Read the full guide →](guides/agents_threads.md)**

Building sophisticated conversational AI applications by combining Agents with thread management.

**Key Topics:**
- Contextual conversations
- Streaming in threads
- Multi-path conversations
- Advanced session managers
- Smart routing
- Multi-user support
- Production patterns
- Response component handling
- Feedback integration
- Complete production examples

**Example:**
```python
from cortex_agents import CortexAgent

class ConversationalAgent:
    def __init__(self, agent_name: str):
        self.agent = CortexAgent()
        self.agent_name = agent_name
        self.sessions = {}

    def start_conversation(self, user_id: str):
        thread = self.agent.create_thread()
        self.sessions[user_id] = {
            "thread_id": thread["thread_id"],
            "current_message_id": 0
        }

    def ask(self, user_id: str, question: str):
        session = self.sessions[user_id]
        response = self.agent.run(
            question,
            agent_name=self.agent_name,
            thread_id=session["thread_id"],
            parent_message_id=session["current_message_id"]
        )
        session["current_message_id"] = response.message_id
        return response
```

## 📚 API Reference

| Module                 | Description          | Link                             |
| ---------------------- | -------------------- | -------------------------------- |
| **CortexAgent**        | Sync agent client    | [API Docs](api/agent.md)         |
| **AsyncCortexAgent**   | Async agent client   | [API Docs](api/async_agent.md)   |
| **CortexAnalyst**      | Sync analyst client  | [API Docs](api/analyst.md)       |
| **AsyncCortexAnalyst** | Async analyst client | [API Docs](api/async_analyst.md) |
| **AgentResponse**      | Response wrapper     | [API Docs](api/response.md)      |
| **AgentThreads**       | Thread management    | [API Docs](api/core_threads.md)  |
| **AgentEntity**        | Agent CRUD ops       | [API Docs](api/core_entity.md)   |
| **AgentRun**           | Run operations       | [API Docs](api/core_run.md)      |
| **AgentFeedback**      | Feedback ops         | [API Docs](api/core_feedback.md) |

## 🎯 Common Tasks

### I want to...

**Generate SQL from natural language**
→ See [Cortex Analyst Guide](guides/analyst.md)

**Build a chatbot with memory**
→ See [Agent with Threads Guide](guides/agents_threads.md)

**Manage conversation threads**
→ See [Thread Management Guide](guides/threads_api.md)

**Stream responses in real-time**
→ See [Quick Start - Streaming](quickstart.md#streaming-responses)

**Handle multiple concurrent users**
→ See [Agent with Threads Guide - Async Multi-User](guides/agents_threads.md#async-multi-user-conversations)

**Submit feedback on responses**
→ See [Analyst Guide - Feedback](guides/analyst.md#submitting-feedback)

**Work with charts and tables**
→ See [Agent with Threads - Response Components](guides/agents_threads.md#working-with-response-components)

**Build a production chatbot**
→ See [Agent with Threads - Complete Example](guides/agents_threads.md#complete-example-full-featured-conversational-app)

**Understand threading and branching**
→ See [Thread Management - Branching Conversations](guides/threads_api.md#branching-conversations)

**Handle ambiguous questions**
→ See [Analyst Guide - Ambiguous Questions](guides/analyst.md#handling-ambiguous-questions)

## 📊 Feature Comparison

| Feature            | Cortex Agent                 | Cortex Analyst          |
| ------------------ | ---------------------------- | ----------------------- |
| **Purpose**        | Agentic workflows with tools | SQL generation          |
| **Threads**        | ✅ Full support               | ❌ Stateless             |
| **Tools**          | ✅ Custom functions           | ❌ N/A                   |
| **SQL Generation** | ✅ Via tools                  | ✅ Native                |
| **Multi-turn**     | ✅ With threads               | ✅ Via messages          |
| **Streaming**      | ✅ text.delta, tool.delta     | ✅ sql.delta, text.delta |
| **Async**          | ✅ AsyncCortexAgent           | ✅ AsyncCortexAnalyst    |

## 🔗 External Resources

- [Snowflake Cortex Agents Documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)
- [Snowflake Cortex Analyst Documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/rest-api)
- [Cortex Analyst Guide](guides/analyst.md)

## 💡 Quick Tips

1. **Always use context managers** (`with` statement) for automatic cleanup
2. **Track message IDs** when working with threads
3. **Handle ambiguous questions** with suggestions in Analyst
4. **Stream responses** for better user experience
5. **Submit feedback** to improve model performance
6. **Use async versions** for concurrent operations
7. **Clean up threads** after sessions end
8. **Name threads meaningfully** for better organization

## 🆘 Getting Help

1. Check the relevant guide above
2. Review [Examples](guides/agents.md)
3. Search [API Reference](api/overview.md)
4. Check the [GitHub repository](https://github.com/chx5/snowflake-cortex-agents)
5. Open an [issue](https://github.com/chx5/snowflake-cortex-agents/issues)
