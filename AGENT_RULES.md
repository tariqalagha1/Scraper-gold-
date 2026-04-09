# AGENT RULES

## Core Principles
- Each agent must perform ONLY one responsibility
- Agents must NOT overlap responsibilities
- All communication between agents must be structured JSON
- No agent should directly modify another agent’s output

## Execution Rules
- Every agent must log its actions
- Every step must return a status (success / fail)
- Failures must NOT crash the full pipeline
- Retry logic must be implemented for critical steps

## Data Handling
- Always return structured output
- Never return raw unprocessed data unless required
- Include metadata with every result (timestamp, source, type)

## Safety & Compliance
- Respect rate limits
- Respect robots.txt when enabled
- Do NOT bypass authentication illegally
- Only use provided credentials for login

## Performance
- Use async where possible
- Avoid blocking operations
- Optimize for scalability

## Logging
Each agent must log:
- input
- output
- errors
- execution time

## Communication Format (MANDATORY)
All agents must use JSON format like:

{
  "status": "success",
  "data": {},
  "error": null,
  "metadata": {
    "agent": "agent_name",
    "timestamp": "ISO8601"
  }
}
