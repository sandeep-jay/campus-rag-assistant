# Tenant RAG configuration

Prompts and topic guardrails are **generic by default** and **hydrated per tenant** from environment variables and optional `tenant.rag_config` (JSONB).

## Resolution order

1. **`tenant.rag_config`** (database) — per-tenant overrides when the user has `tenant_id`
2. **Environment / settings** — `ASSISTANT_NAME`, `SUPPORTED_TOPICS`, `OUT_OF_SCOPE_MESSAGE` in `.env`
3. **Template files** — `backend/app/templates/prompt_prefix.txt` uses `{{assistant_name}}`, `{{supported_topics}}`, `{{out_of_scope_message}}`

## `tenant.rag_config` JSON shape

```json
{
  "assistant_name": "Acme LMS Support",
  "supported_topics": "Acme LMS, video hosting, accessibility tools",
  "out_of_scope_message": "I can only answer questions about Acme LMS and related tools.",
  "few_shot_examples": [
    {
      "input": "How do I enroll?",
      "output": ["1. Sign in.", "2. Open Courses.", "3. Click Enroll."]
    }
  ]
}
```

Apply after migration `0002`:

```bash
alembic upgrade head
```

## Example campus sample (optional)

Reference profile: [samples/berkeley/tenant_rag_config.json](../samples/berkeley/tenant_rag_config.json) (Canvas LMS, LTI, accessibility, inclusive teaching). Copy into a tenant’s `rag_config` or use as a seed — not loaded automatically.

## Knowledge base

Live answers come from your **Bedrock Knowledge Base** (vectors in **OpenSearch Serverless**) or **Azure AI Search** index, typically fed by sources such as **ServiceNow** knowledge articles and Canvas LMS help content. Point provider env vars at your corpus; prompts do not embed institution-specific articles in the repo.
