const GENERATE_API_URL = '/api/generate-problem';
const HINT_API_URL = '/api/hint';
const GRADE_CONDITIONS_API_URL = '/api/grade-conditions';

// グローバル変数：現在の問題データを保持
let currentProblem = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded event fired');

    // フェーズ管理用の要素
    const phaseGenerate = document.getElementById('phase-generate');
    const phaseProblem = document.getElementById('phase-problem');
    const hintOutput = document.getElementById('hint-output');

    // 出題フェーズのボタン
    const generateButton = document.getElementById('generate-button');
    const generateLoading = document.getElementById('generate-loading');
    const generateError = document.getElementById('generate-error');
    const proofTypeSelect = document.getElementById('proof-type');
    const difficultySelect = document.getElementById('difficulty');

    // 問題表示フェーズの要素
    const problemTheorem = document.getElementById('problem-theorem');
    const problemFigure = document.getElementById('problem-figure');
    const problemConditions = document.getElementById('problem-conditions');
    const problemToProve = document.getElementById('problem-to-prove');
    const studentAttempt = document.getElementById('student_attempt');
    const hintForm = document.getElementById('hint-form');
    const submitButton = document.getElementById('submit-button');
    const hintLoading = document.getElementById('hint-loading');
    const backButton = document.getElementById('back-button');
    const gradeConditionsButton = document.getElementById('grade-conditions-button');
    const gradingResult = document.getElementById('grading-result');
    const tryAnotherAttemptButton = document.getElementById('try-another-attempt-button');

    // ヒント表示フェーズの要素
    const nextHintText = document.getElementById('next-hint-text');
    const whyText = document.getElementById('why-text');
    const diagnosisText = document.getElementById('diagnosis-text');
    const continueButton = document.getElementById('continue-button');

    const errorMessage = document.getElementById('error-message');

    // 出題ボタンのクリックハンドラ
    if (generateButton) {
        console.log('generateButton found');
        generateButton.addEventListener('click', async (e) => {
            console.log('Generate button clicked');
            e.preventDefault();
            
            generateError.classList.add('hidden');
            generateLoading.classList.remove('hidden');
            generateButton.disabled = true;

            const proofType = proofTypeSelect.value;
            const difficulty = difficultySelect.value;

            console.log('Sending request:', { proofType, difficulty });

            try {
                const response = await fetch(GENERATE_API_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ proof_type: proofType, difficulty }),
                });

                console.log('Response status:', response.status);

                if (!response.ok) {
                    const errorBody = await response.json().catch(() => ({}));
                    const errorMsg = errorBody.error || `サーバーエラー (ステータス: ${response.status})`;
                    throw new Error(errorMsg);
                }

                const problemData = await response.json();
                console.log('Problem data received:', problemData);

                // 問題データを保存
                currentProblem = problemData;

                // 問題を表示
                problemTheorem.textContent = problemData.theorem_context || '';
                problemFigure.textContent = problemData.figure_description || '（図の説明がありません）';
                problemToProve.textContent = problemData.to_prove || '';

                // 条件の選択肢を表示
                problemConditions.innerHTML = '';
                if (problemData.condition_choices && Array.isArray(problemData.condition_choices)) {
                    problemData.condition_choices.forEach((choice, index) => {
                        const label = document.createElement('label');
                        label.className = 'condition-checkbox';
                        
                        const input = document.createElement('input');
                        input.type = 'checkbox';
                        input.value = choice.text;
                        input.dataset.isCorrect = choice.is_correct;
                        input.className = 'condition-input';
                        
                        const span = document.createElement('span');
                        span.textContent = choice.text;
                        
                        label.appendChild(input);
                        label.appendChild(span);
                        problemConditions.appendChild(label);
                    });
                }

                // フェーズを切り替え
                phaseGenerate.classList.remove('active');
                phaseProblem.classList.add('active');
                hintOutput.classList.add('hidden');
                studentAttempt.value = '';
                errorMessage.classList.add('hidden');
                gradingResult.classList.add('hidden');
                hintForm.classList.add('hidden');
                tryAnotherAttemptButton.classList.add('hidden');

            } catch (error) {
                console.error('Generate error:', error);
                generateError.textContent = `エラーが発生しました: ${error.message}`;
                generateError.classList.remove('hidden');
            } finally {
                generateLoading.classList.add('hidden');
                generateButton.disabled = false;
            }
        });
    } else {
        console.error('generateButton not found');
    }

    // 条件採点ボタンのハンドラ
    if (gradeConditionsButton) {
        gradeConditionsButton.addEventListener('click', async (e) => {
            e.preventDefault();
            
            if (!currentProblem) {
                errorMessage.textContent = 'エラー: 問題データが見つかりません。';
                errorMessage.classList.remove('hidden');
                return;
            }
            
            // チェックされた条件を取得
            const selectedConditions = Array.from(document.querySelectorAll('.condition-input:checked'))
                .map(input => input.value);
            
            const data = {
                selected_conditions: selectedConditions,
                condition_choices: currentProblem.condition_choices
            };
            
            try {
                const response = await fetch(GRADE_CONDITIONS_API_URL, {
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
                
                // 採点結果を表示
                gradingResult.innerHTML = '';
                const resultCard = document.createElement('div');
                resultCard.className = result.is_correct ? 'grading-correct' : 'grading-incorrect';
                
                const scoreText = document.createElement('p');
                scoreText.className = 'grading-score';
                scoreText.textContent = `スコア: ${result.score}点`;
                
                const feedbackText = document.createElement('p');
                feedbackText.className = 'grading-feedback';
                feedbackText.textContent = result.feedback;
                
                resultCard.appendChild(scoreText);
                resultCard.appendChild(feedbackText);
                gradingResult.appendChild(resultCard);
                gradingResult.classList.remove('hidden');
                
                // 正解の場合は途中記述フェーズに進む
                if (result.is_correct) {
                    setTimeout(() => {
                        hintForm.classList.remove('hidden');
                        tryAnotherAttemptButton.classList.add('hidden');
                        studentAttempt.focus();
                    }, 1500);
                } else {
                    // 不正解の場合は再度選択できるようにする
                    tryAnotherAttemptButton.classList.remove('hidden');
                }
                
            } catch (error) {
                console.error('Grade conditions error:', error);
                errorMessage.textContent = `採点エラーが発生しました: ${error.message}`;
                errorMessage.classList.remove('hidden');
            }
        });
    }
    
    // 別の途中記述を試すボタン（採点失敗時）
    if (tryAnotherAttemptButton) {
        tryAnotherAttemptButton.addEventListener('click', () => {
            gradingResult.classList.add('hidden');
            tryAnotherAttemptButton.classList.add('hidden');
        });
    }

    // ヒント取得フォームのサブミットハンドラ
    if (hintForm) {
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
                givenForAPI = givenForAPI.join('\n');
            }
            
            // チェックされた条件を取得
            const selectedConditions = Array.from(document.querySelectorAll('.condition-input:checked'))
                .map(input => input.value);
            
            const data = {
                theorem_context: currentProblem.theorem_context,
                given: givenForAPI,
                to_prove: currentProblem.to_prove,
                student_attempt: studentAttempt.value,
                selected_conditions: selectedConditions
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
    }

    // 別の問題を出題するボタンのハンドラ
    if (backButton) {
        backButton.addEventListener('click', () => {
            phaseGenerate.classList.add('active');
            phaseProblem.classList.remove('active');
            hintOutput.classList.add('hidden');
            gradingResult.classList.add('hidden');
            hintForm.classList.add('hidden');
            tryAnotherAttemptButton.classList.add('hidden');
            currentProblem = null;
            errorMessage.classList.add('hidden');
        });
    }

    // 別の途中記述を試すボタンのハンドラ
    if (continueButton) {
        continueButton.addEventListener('click', () => {
            hintOutput.classList.add('hidden');
            hintForm.classList.remove('hidden');
            studentAttempt.value = '';
            studentAttempt.focus();
        });
    }
});

