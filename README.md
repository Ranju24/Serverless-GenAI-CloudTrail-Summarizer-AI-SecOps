# Serverless-GenAI-CloudTrail-Summarizer-AI-SecOps

Designed and deployed an event-driven automation pipeline using S3, Lambda, and Amazon Bedrock to transform complex, multi-event CloudTrail JSON logs into structured, human-readable Markdown summaries in real time.


Core Purpose: Automatically transforms raw, complex AWS CloudTrail JSON audit logs into human-readable Markdown security summaries in real time.

Automation pipeline using AWS CloudTrail, S3, Lambda, and Amazon Bedrock (using the amazon.nova-lite-v1:0 model) to turn complex CloudTrail JSON logs into clean Markdown summaries.

When CloudTrail delivers compressed .json.gz logs to S3, an S3 Event Notification automatically triggers a Python Lambda function. The function filters out read-only calls (Get, List, Describe) to process only state-changing actions (Create, Delete, Modify), converts timestamps to IST, and passes the event payload to Amazon Nova Lite via Bedrock. The model parses the dense API data and generates a structured Markdown report (_summary.md) saved back to S3, featuring an executive summary, an event breakdown table, and high-priority security alerts.
