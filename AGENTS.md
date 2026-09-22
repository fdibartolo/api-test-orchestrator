# Agents

## api-learner

- **Definition:** `.github/agents/api-learner.agent.md`
- **Purpose:** Learns a user-provided API endpoint from its OpenAPI document and generates sample inputs for the local `/validate` endpoint.
- **Required input:** The target API endpoint URL.
- **Capabilities:** OpenAPI retrieval, repository inspection, and JSON sample generation under `samples/`.