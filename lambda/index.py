# lambda/index.py
import json
import os
import re
import urllib.request

# ColabのAPIエンドポイント
API_URL = "your_URL/generate"
COLAB_LLM_API_URL = os.environ.get("COLAB_LLM_API_URL", API_URL)

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])

        # プロンプトの作成
        prompt = ""
        for msg in conversation_history:
            if msg["role"] == "user":
                prompt += f"ユーザー: {msg['content']}\n"
            elif msg["role"] == "assistant":
                prompt += f"アシスタント: {msg['content']}\n"
        prompt += f"ユーザー: {message}\nアシスタント:"

        # Colab API へのPOSTリクエスト
        payload = json.dumps({
            "prompt": prompt,
            "max_new_tokens": 200,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }).encode('utf-8')

        req = urllib.request.Request(
            COLAB_LLM_API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode('utf-8')
            response_json = json.loads(response_body)

        assistant_response = response_json.get("generated_text", "")
        if not assistant_response:
            raise Exception("No response from Colab LLM API")

        # 会話履歴の更新
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": assistant_response})

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": conversation_history
            })
        }

    except Exception as error:
        print("Error:", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
