---
name: archive-conversation
description: >-
  Use this skill when the user asks to save, archive, or dump the full chat or conversation verbatim. It guides you on how to extract the exact text of the conversation and save it to a markdown file.
---

# Archive Conversation Skill

This skill provides instructions on how to create a verbatim backup or archive of the current conversation history.

## When to use
Activate this skill when the user asks to:
- "Save the chat"
- "Archive the conversation"
- "Dump the conversation log verbatim"
- Or any similar request to preserve the exact back-and-forth messages.

## Execution Steps

1. **Extract the Conversation History**:
   Read through the conversation history currently available in your context window. Identify the exact text of every User message and every Agent response. 

2. **Format as Markdown**:
   Compile these messages chronologically into a single markdown structure. Use clear formatting, for example:
   ```markdown
   # Conversation Archive
   
   ## Message 1
   **User:**
   [Exact text of user request]
   
   **Agent:**
   [Exact text of your response]
   
   ---
   ```

3. **Save the Archive**:
   Use the `write_to_file` tool to save the compiled markdown string. 
   - **TargetFile**: Save it to the current conversation's artifact directory (e.g. `<appDataDir>/brain/<conversation-id>/Conversation_Archive.md`) unless the user explicitly requested a different path (like `~/Documents`).
   - **Crucial Rule**: Do NOT summarize the messages. They must be exact, verbatim copies of the text.

4. **Confirm with the User**:
   Inform the user that the archive has been created and provide a clickable markdown link to the generated artifact or file path so they can easily access it.
