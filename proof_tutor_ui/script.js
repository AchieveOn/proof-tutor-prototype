const API_URL = '/api/hint'; // バックエンドAPIのエンドポイント

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('hint-form');
    const submitButton = document.getElementById('submit-button');
    const loadingMessage = document.getElementById('loading-message');
    const hintOutput = document.getElementById('hint-output');
    const errorMessage = document.getElementById('error-message');

    const nextHintText = document.getElementById('next-hint-text');
    const whyText = document.getElementById('why-text');
    const diagnosisText = document.getElementById('diagnosis-text');
    const diagnosisLog = document.querySelector('.diagnosis-log');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // 状態のリセット
        hintOutput.classList.add('hidden');
        errorMessage.classList.add('hidden');
        loadingMessage.classList.remove('hidden');
        submitButton.disabled = true;

        // 入力データの収集
        const data = {
            theorem_context: document.getElementById('theorem_context').value,
            given: document.getElementById('given').value,
            to_prove: document.getElementById('to_prove').value,
            student_attempt: document.getElementById('student_attempt').value,
        };

        try {
            // API_URLはデプロイ時に調整が必要ですが、ここでは相対パスとしておきます
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                // HTTPエラーの場合
                const errorBody = await response.json().catch(() => ({}));
                const errorMsg = errorBody.error || `サーバーエラー (ステータス: ${response.status})`;
                throw new Error(errorMsg);
            }

            const result = await response.json();

            // 結果の表示
            nextHintText.textContent = result.next_hint || 'ヒントがありませんでした。';
            whyText.textContent = result.why || '理由がありませんでした。';
            diagnosisText.textContent = result.diagnosis || '診断結果がありませんでした。';

            // do_not_revealがtrueであることを確認（必須要件）
            if (result.do_not_reveal === true) {
                hintOutput.classList.remove('hidden');
                diagnosisLog.classList.remove('hidden'); // 教員ダッシュボードへのログとして表示
            } else {
                // 万が一、do_not_revealがfalseだった場合の安全策
                errorMessage.textContent = 'エラー: AIが完全解答を返そうとしました。システムがこれをブロックしました。';
                errorMessage.classList.remove('hidden');
            }

        } catch (error) {
            console.error('Fetch error:', error);
            errorMessage.textContent = `通信エラーが発生しました: ${error.message}`;
            errorMessage.classList.remove('hidden');
        } finally {
            loadingMessage.classList.add('hidden');
            submitButton.disabled = false;
        }
    });
});

