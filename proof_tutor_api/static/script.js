const GENERATE_API_URL = '/api/generate-problem';
const HINT_API_URL = '/api/hint';

// グローバル変数：現在の問題データを保持
let currentProblem = null;

document.addEventListener('DOMContentLoaded', () => {
    // フェーズ管理用の要素
    const phaseGenerate = document.getElementById('phase-generate');
    const phaseProblem = document.getElementById('phase-problem');
    const hintOutput = document.getElementById('hint-output');

    // 出題フェーズのボタン
    const generateButton = document.getElementById('generate-button');
    const generateLoading = document.getElementById('generate-loading');
    const generateError = document.getElementById('generate-error');
    const difficultySelect = document.getElementById('difficulty');

    // 問題表示フェーズの要素
    const problemTheorem = document.getElementById('problem-theorem');
    const problemGiven = document.getElementById('problem-given');
    const problemToProve = document.getElementById('problem-to-prove');
    const studentAttempt = document.getElementById('student_attempt');
    const hintForm = document.getElementById('hint-form');
    const submitButton = document.getElementById('submit-button');
    const hintLoading = document.getElementById('hint-loading');
    const backButton = document.getElementById('back-button');

    // ヒント表示フェーズの要素
    const nextHintText = document.getElementById('next-hint-text');
    const whyText = document.getElementById('why-text');
    const diagnosisText = document.getElementById('diagnosis-text');
    const continueButton = document.getElementById('continue-button');

    const errorMessage = document.getElementById('error-message');

    // 出題ボタンのクリックハンドラ
    generateButton.addEventListener('click', async () => {
        generateError.classList.add('hidden');
        generateLoading.classList.remove('hidden');
        generateButton.disabled = true;

        const difficulty = difficultySelect.value;

        try {
            const response = await fetch(GENERATE_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ difficulty }),
            });

            if (!response.ok) {
                const errorBody = await response.json().catch(() => ({}));
                const errorMsg = errorBody.error || `サーバーエラー (ステータス: ${response.status})`;
                throw new Error(errorMsg);
            }

            const problemData = await response.json();

            // 問題データを保存
            currentProblem = problemData;

            // 問題を表示
            problemTheorem.textContent = problemData.theorem_context || '';
            
            // givenがArrayの場合は結合、文字列の場合はそのまま使用
            let givenText = '';
            if (Array.isArray(problemData.given)) {
                givenText = problemData.given.join(', ');
            } else {
                givenText = problemData.given || '';
            }
            problemGiven.textContent = givenText;
            
            problemToProve.textContent = problemData.to_prove || '';

            // フェーズを切り替え
            phaseGenerate.classList.add('hidden');
            phaseProblem.classList.remove('hidden');
            hintOutput.classList.add('hidden');
            studentAttempt.value = '';
            errorMessage.classList.add('hidden');

        } catch (error) {
            console.error('Generate error:', error);
            generateError.textContent = `エラーが発生しました: ${error.message}`;
            generateError.classList.remove('hidden');
        } finally {
            generateLoading.classList.add('hidden');
            generateButton.disabled = false;
        }
    });

    // ヒント取得フォームのサブミットハンドラ
    hintForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!currentProblem) {
            errorMessage.textContent = 'エラー: 問題データが見つかりません。';
            errorMessage.classList.remove('hidden');
            return;
        }

        // 状態のリセット
        hintOutput.classList.add('hidden');
        errorMessage.classList.add('hidden');
        hintLoading.classList.remove('hidden');
        submitButton.disabled = true;

        // 入力データの収集
        // givenがArrayの場合は結合
        let givenForAPI = currentProblem.given;
        if (Array.isArray(givenForAPI)) {
            givenForAPI = givenForAPI.join(', ');
        }
        
        const data = {
            theorem_context: currentProblem.theorem_context,
            given: givenForAPI,
            to_prove: currentProblem.to_prove,
            student_attempt: studentAttempt.value,
        };

        try {
            const response = await fetch(HINT_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
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
            hintLoading.classList.add('hidden');
            submitButton.disabled = false;
        }
    });

    // 別の問題を出題するボタンのハンドラ
    backButton.addEventListener('click', () => {
        phaseGenerate.classList.remove('hidden');
        phaseProblem.classList.add('hidden');
        hintOutput.classList.add('hidden');
        currentProblem = null;
        errorMessage.classList.add('hidden');
    });

    // 別の途中記述を試すボタンのハンドラ
    continueButton.addEventListener('click', () => {
        hintOutput.classList.add('hidden');
        studentAttempt.focus();
    });
});

