document.getElementById('searchBtn').addEventListener('click', async () => {
    const corpName = document.getElementById('corpName').value.trim();
    if (!corpName) {
        alert('기업명을 입력해주세요.');
        return;
    }

    const statusArea = document.getElementById('statusArea');
    const statusMessage = document.getElementById('statusMessage');
    const resultArea = document.getElementById('resultArea');
    const summaryContent = document.getElementById('summaryContent');
    const searchBtn = document.getElementById('searchBtn');

    // UI 초기화
    statusArea.classList.remove('hidden');
    resultArea.classList.add('hidden');
    summaryContent.innerHTML = '';
    searchBtn.disabled = true;
    searchBtn.classList.add('opacity-50');

    try {
        const response = await fetch(`/analyze?corp_name=${encodeURIComponent(corpName)}`);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (!line.trim()) continue;
                
                try {
                    const data = JSON.parse(line);
                    
                    if (data.status === 'progress') {
                        statusMessage.innerText = data.message;
                    } else if (data.status === 'complete') {
                        // 결과 표시
                        statusArea.classList.add('hidden');
                        resultArea.classList.remove('hidden');
                        document.getElementById('resultTitle').innerText = `${corpName} 분석 결과`;
                        
                        // Markdown 렌더링
                        summaryContent.innerHTML = marked.parse(data.data.summary);
                        
                        // 출처 링크 설정
                        document.getElementById('dartLink').href = data.data.sources.dart;
                        document.getElementById('newsLink').href = data.data.sources.news;
                    } else if (data.status === 'error') {
                        throw new Error(data.message);
                    }
                } catch (e) {
                    console.error('Parsing error:', e, line);
                }
            }
        }
    } catch (error) {
        alert('오류가 발생했습니다: ' + error.message);
        statusArea.classList.add('hidden');
    } finally {
        searchBtn.disabled = false;
        searchBtn.classList.remove('opacity-50');
    }
});
