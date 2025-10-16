import os
import json
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI() # 環境変数からAPIキーを自動で読み込みます

# LLMのモデル名
MODEL_NAME = "gpt-4.1-mini" # 適切なモデルを選択してください

@app.route('/api/hint', methods=['POST'])
def get_hint():
    """
    生徒の途中記述に基づいて、次の一歩のヒントをLLMから取得するAPIエンドポイント。
    """
    try:
        data = request.get_json()
        
        # 必須パラメータのチェック
        required_fields = ["theorem_context", "given", "to_prove", "student_attempt"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        theorem_context = data.get("theorem_context", "")
        given = data.get("given", "")
        to_prove = data.get("to_prove", "")
        student_attempt = data.get("student_attempt", "")

        # プロンプトの生成
        prompt_template = """
あなたは中高数学の「証明ヒントAI」です。絶対に完成解答は出さず、
次の一歩だけを短く提示します。日本語。

【定理・文脈】:
{theorem_context}

【与条件】:
{given}

【結論】:
{to_prove}

【生徒の途中】:
{student_attempt}

出力は必ず次のJSON:
{{
 "diagnosis": "誤り/不足の指摘を60字以内",
 "next_hint": "次の一歩だけを80字以内で",
 "why": "なぜその一歩かを80字以内で",
 "do_not_reveal": true
}}
禁止事項: 完成解答、三歩以上の手順、別問題への脱線。
"""
        
        prompt = prompt_template.format(
            theorem_context=theorem_context,
            given=given,
            to_prove=to_prove,
            student_attempt=student_attempt
        )

        # LLMへの問い合わせ
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "あなたは中高数学の「証明ヒントAI」です。絶対に完成解答は出さず、次の一歩だけを短く提示します。出力は必ず指定されたJSON形式に従ってください。"},
                {"role": "user", "content": prompt}
            ],
            # JSON形式での出力を強制
            response_format={"type": "json_object"},
            # ヒントの最小性を担保するため、max_tokensを制限
            max_tokens=256, 
            temperature=0.1 # 安定した出力を得るために低めに設定
        )

        # LLMの応答からJSONを抽出
        llm_output_text = response.choices[0].message.content
        
        # JSON文字列をパース
        try:
            hint_data = json.loads(llm_output_text)
        except json.JSONDecodeError:
            # LLMが不正なJSONを返した場合のフォールバック
            print(f"LLM returned invalid JSON: {llm_output_text}")
            return jsonify({"error": "LLM returned an unparsable response."}), 500

        # do_not_revealがtrueであることを確認（ガードレール）
        if hint_data.get("do_not_reveal") is not True:
             # プロンプトインジェクション対策として、意図しない完全解答を防ぐ
            print("Warning: do_not_reveal was not true. Overriding.")
            hint_data["do_not_reveal"] = True
            hint_data["next_hint"] = "（セキュリティガードによりヒントは表示されません。AIの応答を確認してください。）"
            
        return jsonify(hint_data), 200

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 開発環境での実行
    app.run(debug=True, host='0.0.0.0', port=5000)

