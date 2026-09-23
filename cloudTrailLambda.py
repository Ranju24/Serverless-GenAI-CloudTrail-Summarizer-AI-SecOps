import json
import gzip
import urllib.parse
import boto3

s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

MODEL_ID = 'us.amazon.nova-lite-v1:0'

def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
        
        # Guardrail 1: Process only raw CloudTrail log files
        if not key.endswith('.json.gz') or '_summary.md' in key or '_summary.txt' in key:
            print(f"Skipping file: {key}")
            continue

        # Save summary in the SAME directory alongside the .json.gz file
        summary_key = key.replace('.json.gz', '_summary.md')

        # Guardrail 2: Skip if summary already exists
        try:
            s3_client.head_object(Bucket=bucket, Key=summary_key)
            print(f"Skipping {key}: Summary file {summary_key} already exists.")
            continue
        except Exception:
            pass

        try:
            # 1. Fetch & Decompress Log File
            s3_response = s3_client.get_object(Bucket=bucket, Key=key)
            decompressed = gzip.decompress(s3_response['Body'].read())
            cloudtrail_json = json.loads(decompressed)

            records = cloudtrail_json.get('Records', [])
            if not records:
                print(f"No records found in {key}.")
                continue

            sample_records = records[:10]

            # 2. Comprehensive Identity & Action Prompt
            prompt_text = f"""Analyze these CloudTrail log events and extract detailed security and audit information.
CRITICAL INSTRUCTION: Do NOT wrap your output in markdown code blocks (do NOT use ``` or ```yaml). Output plain Markdown text directly.

Format your output EXACTLY as shown in this template:

Changes Detected at This Timestamp
Key Finding: <Short 1-line Summary of the primary action>

| Attribute | Value |
| --- | --- |
| Action Type | <Create / Delete / Modify / Read / Other> |
| Event Name | <eventName> |
| Target AWS Service | <eventSource service, e.g., s3.amazonaws.com, lambda.amazonaws.com> |
| Resource Name / ARN | <Target Resource ARN or Name from resources/requestParameters> |
| Username / Principal | <userName or principalId> |
| User Type | <IAMUser / AssumedRole / Root / FederatedUser / Existing User> |
| Principal ARN | <userIdentity.arn> |
| Access Key ID | <userIdentity.accessKeyId or 'N/A'> |
| MFA Authenticated | <Yes/No based on sessionContext.attributes.mfaAuthenticated> |
| AWS Region | <awsRegion> |
| Source IP | <sourceIPAddress> |
| Timestamp | <eventTime> |
| Account ID | <recipientAccountId> |

CloudTrail Log Data:
{json.dumps(sample_records)}"""

            # 3. Call Bedrock
            response = bedrock_client.converse(
                modelId=MODEL_ID,
                messages=[{"role": "user", "content": [{"text": prompt_text}]}],
                inferenceConfig={"maxTokens": 500, "temperature": 0.1}
            )

            # 4. Clean residual code block formatting
            summary_text = response['output']['message']['content'][0]['text'].strip()
            if summary_text.startswith("```"):
                summary_text = summary_text.split("\n", 1)[-1]
            if summary_text.endswith("```"):
                summary_text = summary_text.rsplit("\n", 1)[0]
            summary_text = summary_text.replace("```yaml", "").replace("```markdown", "").replace("```", "").strip()

            # 5. Save Formatted Output
            s3_client.put_object(
                Bucket=bucket,
                Key=summary_key,
                Body=summary_text.encode('utf-8'),
                ContentType='text/markdown'
            )

            print(f"Successfully created detailed summary at: s3://{bucket}/{summary_key}")

        except Exception as err:
            print(f"Error processing {key}: {str(err)}")
            raise err
