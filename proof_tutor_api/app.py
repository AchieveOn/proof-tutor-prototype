import os
import json
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI

app = Flask(__name__, static_folder='static')
client = OpenAI() # 環境変数からAPIキーを自動で読み込みます

# LLMのモデル名
MODEL_NAME = "gpt-4.1-mini" # 適切なモデルを選択してください

@app.route('/api/generate-problem', methods=['POST'])
def generate_problem():
    """
    AIが証明問題を自動生成するAPIエンドポイント。
    """
    try:
        data = request.get_json() or {}
        
        # オプションパラメータ：証明種別（congruence, similarity）
        proof_type = data.get("proof_type", "congruence")
        # オプションパラメータ：難易度（easy, medium, hard）
        difficulty = data.get("difficulty", "medium")
        
        # 証明種別に応じたプロンプト
        proof_type_guidance = {
            "congruence": "三角形の合同条件を使った証明問題",
            "similarity": "三角形の相似条件を使った証明問題"
        }
        
        # 難易度に応じたプロンプト
        difficulty_guidance = {
            "easy": "中学1年生レベルの簡単な",
            "medium": "中学2-3年生レベルの標準的な",
            "hard": "高校1年生レベルの難しい"
        }
        
        proof_guidance = proof_type_guidance.get(proof_type, proof_type_guidance["congruence"])
        difficulty_text = difficulty_guidance.get(difficulty, difficulty_guidance["medium"])
        guidance = difficulty_text + proof_guidance
        
        # プロンプトの生成
        prompt_template = """
あなたは中高数学の問題出題AIです。{guidance}を生成してください。

以下のJSON形式で出力してください：
{{
  "theorem_context": "証明の分野・定理名（例：三角形の合同条件）",
  "given": "与条件を箇条書きで（例：AB=DE, BC=EF, ∠B=∠E）",
  "to_prove": "証明すべき結論（例：△ABC ≡ △DEF）"
}}

注意：
- 数学的に正確な問題を生成してください
- 与条件と結論が矛盾しないようにしてください
- 日本語で記述してください
"""
        
        prompt = prompt_template.format(guidance=guidance)
        
        # LLMへの問い合わせ
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "あなたは中高数学の問題出題AIです。数学的に正確な証明問題を生成し、必ず指定されたJSON形式で出力してください。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=512,
            temperature=0.7  # 創意性を高めるため、温度を上げる
        )
        
        # LLMの応答からJSONを抽出
        llm_output_text = response.choices[0].message.content
        
        # JSON文字列をパース
        try:
            problem_data = json.loads(llm_output_text)
        except json.JSONDecodeError:
            print(f"LLM returned invalid JSON: {llm_output_text}")
            return jsonify({"error": "LLM returned an unparsable response."}), 500
        
        # 必須フィールドの確認
        required_fields = ["theorem_context", "given", "to_prove"]
        if not all(field in problem_data for field in required_fields):
            return jsonify({"error": "Generated problem is missing required fields"}), 500
        
        return jsonify(problem_data), 200
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500

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

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    # 開発環境での実行
    app.run(debug=True, host='0.0.0.0', port=5000)

