import json
import random
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI

def generate_wrong_conditions(correct_conditions, theorem_context):
    """
    正しい条件から、間違いの条件を生成する関数。
    """
    try:
        prompt = f"""
あなたは数学の証明問題の教育支援AIです。

【定理・文脈】
{theorem_context}

【正しい条件】
{chr(10).join(correct_conditions)}

上記の正しい条件に対して、教育的に有用な「間違いの条件」を3つ生成してください。
間違いの条件は、生徒が陥りやすい誤解や誤りを反映したものにしてください。

以下のJSON形式で出力してください：
{{
  "wrong_conditions": ["間違いの条件1", "間違いの条件2", "間違いの条件3"]
}}
"""
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "あなたは数学の証明問題の教育支援AIです。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=256,
            temperature=0.7
        )
        
        llm_output_text = response.choices[0].message.content
        result = json.loads(llm_output_text)
        return result.get("wrong_conditions", [])
    except Exception as e:
        print(f"Error generating wrong conditions: {e}")
        # エラーが発生した場合は、デフォルトの間違いの条件を返す
        return [
            "条件が不足している",
            "与えられた情報が矛盾している",
            "別の条件が必要である"
        ]

app = Flask(__name__, static_folder='static')
client = OpenAI()

# LLMのモデル名
MODEL_NAME = "gpt-4.1-mini"

# 問題データベースを読み込み
try:
    with open('problems_database.json', 'r', encoding='utf-8') as f:
        PROBLEMS_DB = json.load(f)
except FileNotFoundError:
    PROBLEMS_DB = {"problems": []}

@app.route('/api/generate-problem', methods=['POST'])
def generate_problem():
    """
    問題データベースから証明問題を選択して返すAPIエンドポイント。
    """
    try:
        data = request.get_json() or {}
        
        # パラメータ：証明種別（congruence, similarity）
        proof_type = data.get("proof_type", "congruence")
        # パラメータ：難易度（easy, medium, hard）
        difficulty = data.get("difficulty", "medium")
        
        # 問題データベースから条件に合う問題をフィルタ
        matching_problems = [
            p for p in PROBLEMS_DB['problems']
            if p['type'] == proof_type and p['difficulty'] == difficulty
        ]
        
        # 条件に合う問題がない場合は、証明種別のみで絞る
        if not matching_problems:
            matching_problems = [
                p for p in PROBLEMS_DB['problems']
                if p['type'] == proof_type
            ]
        
        # 最終的に条件に合う問題がない場合は、全問題からランダムに選択
        if not matching_problems:
            matching_problems = PROBLEMS_DB['problems']
        
        # ランダムに問題を選択
        if matching_problems:
            selected_problem = random.choice(matching_problems)
            
            # 与条件がリスト形式の場合は文字列に変換
            given = selected_problem.get('given', [])
            if isinstance(given, list):
                given_text = '\n'.join(given)
            else:
                given_text = given
            
            # 選択肢を生成（正しい条件と間違いの条件を混ぜる）
            correct_conditions = given if isinstance(given, list) else [given]
            
            # 間違いの条件を生成（AIで生成）
            wrong_conditions = generate_wrong_conditions(correct_conditions, selected_problem.get('theorem_context', ''))
            
            # 正しい条件と間違いの条件を混ぜて、ランダムに並べ替え
            all_conditions = correct_conditions + wrong_conditions
            random.shuffle(all_conditions)
            
            # 各条件に対して、正しいかどうかのフラグを付ける
            condition_choices = [
                {"text": cond, "is_correct": cond in correct_conditions}
                for cond in all_conditions
            ]
            
            return jsonify({
                "theorem_context": selected_problem.get('theorem_context', ''),
                "figure_description": selected_problem.get('figure_description', ''),
                "given": given,  # リスト形式で返す
                "to_prove": selected_problem.get('to_prove', ''),
                "condition": selected_problem.get('condition', ''),
                "condition_choices": condition_choices  # 選択肢を追加
            })
        else:
            return jsonify({
                "error": "問題が見つかりません"
            }), 400
            
    except Exception as e:
        print(f"Generate problem error: {e}")
        return jsonify({
            "error": f"エラーが発生しました: {str(e)}"
        }), 500

@app.route('/api/grade-conditions', methods=['POST'])
def grade_conditions():
    """
    生徒が選択した条件を採点するAPIエンドポイント。
    """
    try:
        data = request.get_json() or {}
        
        selected_conditions = data.get("selected_conditions", [])
        condition_choices = data.get("condition_choices", [])
        
        # 正しい条件を特定
        correct_conditions = [c["text"] for c in condition_choices if c.get("is_correct", False)]
        
        # 採点
        is_correct = set(selected_conditions) == set(correct_conditions)
        
        # フィードバック生成
        if is_correct:
            feedback = "素晴らしい！すべての条件を正しく選択できました。"
            score = 100
        else:
            # 間違った選択を特定
            incorrect_selected = [c for c in selected_conditions if c not in correct_conditions]
            missing_conditions = [c for c in correct_conditions if c not in selected_conditions]
            
            feedback_parts = []
            if incorrect_selected:
                feedback_parts.append(f"間違った条件が選ばれています：{', '.join(incorrect_selected)}")
            if missing_conditions:
                feedback_parts.append(f"選ばれていない正しい条件：{', '.join(missing_conditions)}")
            
            feedback = "もう一度確認してください。" + "\n".join(feedback_parts)
            
            # スコア計算（正しく選んだ条件の割合）
            correct_selected = len([c for c in selected_conditions if c in correct_conditions])
            score = int((correct_selected / len(correct_conditions)) * 100) if correct_conditions else 0
        
        return jsonify({
            "is_correct": is_correct,
            "score": score,
            "feedback": feedback,
            "correct_conditions": correct_conditions,
            "selected_conditions": selected_conditions
        })
        
    except Exception as e:
        print(f"Grade conditions error: {e}")
        return jsonify({
            "error": f"エラーが発生しました: {str(e)}"
        }), 500

@app.route('/api/hint', methods=['POST'])
def get_hint():
    """
    生徒の途中記述に対して、次の一歩のヒントを返すAPIエンドポイント。
    完全解答は返さない（安全機構）。
    """
    try:
        data = request.get_json() or {}
        
        theorem_context = data.get("theorem_context", "")
        given = data.get("given", [])
        to_prove = data.get("to_prove", "")
        student_attempt = data.get("student_attempt", "")
        
        # 与条件の処理
        if isinstance(given, list):
            given_text = '\n'.join(given)
        else:
            given_text = given
        
        # プロンプトの生成
        prompt = f"""
あなたは数学の証明問題の教育支援AIです。

【問題】
定理・文脈：{theorem_context}

【与条件】
{given_text}

【証明すべき結論】
{to_prove}

【生徒の現在までの記述】
{student_attempt}

生徒の記述を分析して、以下の3つを日本語で提供してください：

1. 【次の一歩】：生徒が次にすべき一つのステップのみを提示してください。完全な解答は絶対に返さないでください。
2. 【なぜその一歩か】：そのステップが必要な理由を簡潔に説明してください。
3. 【診断】：生徒の記述から見える理解度や課題を簡潔に診断してください。

以下のJSON形式で出力してください：
{{
  "next_hint": "次の一歩のみ（1-2文）",
  "why": "その理由（1-2文）",
  "diagnosis": "診断結果（1-2文）",
  "do_not_reveal": true
}}

重要：必ず do_not_reveal を true に設定してください。これは完全解答を返していないことの確認です。
"""
        
        # LLMへの問い合わせ
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "あなたは数学の証明問題の教育支援AIです。生徒の学習を支援するため、次の一歩のヒントのみを提供し、完全な解答は絶対に返しません。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=512,
            temperature=0.7
        )
        
        # LLMの応答からJSONを抽出
        llm_output_text = response.choices[0].message.content
        
        try:
            result = json.loads(llm_output_text)
        except json.JSONDecodeError:
            print(f"LLM returned invalid JSON: {llm_output_text}")
            return jsonify({
                "error": "AIの応答をパースできませんでした"
            }), 500
        
        # do_not_revealの確認（安全機構）
        if result.get("do_not_reveal") != True:
            print("Warning: do_not_reveal is not true")
            return jsonify({
                "error": "安全機構によってブロックされました"
            }), 400
        
        return jsonify({
            "next_hint": result.get("next_hint", ""),
            "why": result.get("why", ""),
            "diagnosis": result.get("diagnosis", ""),
            "do_not_reveal": result.get("do_not_reveal", False)
        })
        
    except Exception as e:
        print(f"Hint error: {e}")
        return jsonify({
            "error": f"エラーが発生しました: {str(e)}"
        }), 500

@app.route('/', methods=['GET'])
def serve_index():
    """
    静的ファイル（index.html）を提供する。
    """
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>', methods=['GET'])
def serve_static(path):
    """
    静的ファイル（CSS、JavaScript等）を提供する。
    """
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

