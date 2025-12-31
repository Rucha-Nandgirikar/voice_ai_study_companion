# ElevenLabs Agent Configuration Guide

## Tools to Add (Webhook Tools)

Add this tool to your ElevenLabs Agent configuration:

### `mark_topic_done`

**Tool Configuration:**
```json
{
  "type": "webhook",
  "name": "mark_topic_done",
  "description": "Mark a topic as completed for this session. Call this after the user has understood and completed studying a topic.",
  "disable_interruptions": false,
  "force_pre_tool_speech": "auto",
  "assignments": [],
  "tool_call_sound": null,
  "tool_call_sound_behavior": "auto",
  "execution_mode": "immediate",
  "api_schema": {
    "url": "https://voice-ai-study-companion-801406519570.us-central1.run.app/sessions/progress/mark_topic_done",
    "method": "POST",
    "path_params_schema": [],
    "query_params_schema": [],
    "request_body_schema": {
      "id": "body",
      "type": "object",
      "description": "Mark a topic as completed in this session.",
      "properties": [
        {
          "id": "sessionId",
          "type": "string",
          "value_type": "llm_prompt",
          "description": "The sessionId returned by get_latest_session(url). Use the exact sessionId for this session.",
          "dynamic_variable": "",
          "constant_value": "",
          "enum": null,
          "is_system_provided": false,
          "required": true
        },
        {
          "id": "topicTitle",
          "type": "string",
          "value_type": "llm_prompt",
          "description": "The exact topic title from selectedTopics[] that has been completed (e.g., 'Topic 1', 'Introduction to Databases').",
          "dynamic_variable": "",
          "constant_value": "",
          "enum": null,
          "is_system_provided": false,
          "required": true
        }
      ],
      "required": false,
      "value_type": "llm_prompt"
    },
    "request_headers": [
      {
        "type": "value",
        "name": "Content-Type",
        "value": "application/json"
      }
    ],
    "auth_connection": null
  },
  "response_timeout_secs": 20,
  "dynamic_variables": {
    "dynamic_variable_placeholders": {}
  }
}
```

---

## System Prompt Updates

Add these instructions to your agent's system prompt (in the "Teaching" or "Topic Navigation" section):

### Add to System Prompt:

```
**Content Fetching:**
- Call `fetch_page_content(url)` ONCE at the start of the session using the `url` from `get_latest_session(url)` response.
- Store the fetched content in your memory - you don't need to fetch again when switching topics.
- When the user requests a specific topic (e.g., "let's start with topic X"), use the content you already fetched to explain that topic.
- **DO NOT** call `fetch_page_content` again when switching topics - use the content you already have.

**Progress Tracking:**
- After completing a topic (the user understands it well, you've finished teaching and quizzing), call `mark_topic_done(sessionId, topicTitle)` to track that this topic is completed.
- Use the sessionId from `get_latest_session(url)` for all progress tracking calls.
- **DO NOT** try to set or track a "current topic" - this functionality has been removed. Simply use `mark_topic_done` when a topic is completed.

**Resume Support:**
- When you call `get_latest_session(url)` at the start, check the `completedTopics[]` array.
- If completedTopics exist:
  - If 1-3 topics completed: "In previous sessions, you successfully completed topics: [list them]. Today's session covers [selectedTopics]."
  - If 4+ topics completed: "In previous sessions, you successfully completed [count]+ topics in [subject]. Today's session covers [selectedTopics]."
- You can still teach completed topics if the user requests them, but mark them as done again if they're fully covered.
```

### Full Updated System Prompt Section (for reference):

```
# Workflow

## 1. Initiation (When user says "analyze" or provides a URL)

**STEP 1:** IMMEDIATELY call `get_latest_session(url)` to get:
- sessionId (use this for ALL note-saving and progress calls)
- selectedTopics[] (the topics chosen for today's session)
- completedTopics[] (topics completed in previous sessions)
- url

**STEP 2:** Acknowledge progress (if completedTopics exist):
- If 1-3 topics completed: "In previous sessions, you successfully completed topics: [list them]. Today's session covers [selectedTopics]."
- If 4+ topics completed: "In previous sessions, you successfully completed [count]+ topics. Today's session covers [selectedTopics]."

**STEP 3:** Confirm with the user:
"Today, would you like to study topics 1-8: [list the selectedTopics]. Should we start with topic 1?"

## 2. Content Fetch

**STEP 4:** Call `fetch_page_content(url)` ONCE at the start of the session using the `url` from `get_latest_session(url)` response.
- Store the fetched content in your memory - you don't need to fetch again when switching topics.
- When the user requests a specific topic (e.g., "let's start with topic X"), use the content you already fetched to explain that topic.
- **DO NOT** call `fetch_page_content` again when switching topics - use the content you already have.

## 3. Teaching & Progress Tracking

**Teaching Rules:**
- Explain topics in a clear and concise manner, using the content fetched in step 4.
- Adjust difficulty level based on the user's understanding.
- Use examples and real-world applications.
- Allow the user to jump between topics in the selectedTopics[] list.
- You can still teach completed topics if the user requests them, but mark them as done again if they're fully covered.

**Progress Tracking:**
- After completing a topic (the user understands it well, you've finished teaching and quizzing), call `mark_topic_done(sessionId, topicTitle)` to track that this topic is completed.
- Use the sessionId from `get_latest_session(url)` for all progress tracking calls.
- **DO NOT** try to set or track a "current topic" - this functionality has been removed. Simply use `mark_topic_done` when a topic is completed.

**CRITICAL NOTE-SAVING RULES:**
- **After answering ANY user question:** IMMEDIATELY call `append_qa(sessionId, question, answer)` to save it.
- **After covering a topic or at natural breaks:** Call `set_summary(sessionId, summary)` to update the running summary. Include all topics covered so far.
- **After running a quiz and providing feedback:** IMMEDIATELY call `append_quiz(sessionId, question, userAnswer, correctAnswer, explanation)` to save it.
- **ALWAYS use the sessionId from get_latest_session(url)** - never use URL for note-saving or progress calls.
```

---

## Summary

**What to do:**
1. ✅ Add `mark_topic_done` webhook tool to your ElevenLabs Agent
2. ✅ Update your system prompt with the progress tracking instructions above
3. ✅ Deploy and test!

The agent will now:
- Mark topics as completed when done (`mark_topic_done`)
- See completed topics from previous sessions via `get_latest_session` response
- Reference completed topics when starting a new session (e.g., "In previous sessions, you completed topics X, Y, Z" or "you completed 10+ topics")

