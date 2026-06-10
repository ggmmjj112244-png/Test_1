let fetchedItems = [];

// 검색 버튼 클릭 이벤트
document.getElementById('searchBtn').addEventListener('click', async () => {
    const corpName = document.getElementById('corpName').value.trim();
    if (!corpName) {
        alert('기업명을 입력해주세요.');
        return;
    }

    const statusArea = document.getElementById('statusArea');
    const statusMessage = document.getElementById('statusMessage');
    const listArea = document.getElementById('listArea');
    const resultArea = document.getElementById('resultArea');
    const searchBtn = document.getElementById('searchBtn');

    // UI 초기화
    statusArea.classList.remove('hidden');
    listArea.classList.add('hidden');
    resultArea.classList.add('hidden');
    statusMessage.innerText = `'${corpName}' 관련 정보를 찾는 중입니다...`;
    searchBtn.disabled = true;

    try {
        const response = await fetch(`/search?corp_name=${encodeURIComponent(corpName)}`);
        const data = await response.json();

        if (data.status === 'success') {
            fetchedItems = data.items;
            renderItemList(data.items);
            listArea.classList.remove('hidden');
            statusArea.classList.add('hidden');
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        alert('오류가 발생했습니다: ' + error.message);
        statusArea.classList.add('hidden');
    } finally {
        searchBtn.disabled = false;
    }
});

// 엔터키 지원
document.getElementById('corpName').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('searchBtn').click();
    }
});

// 아이템 목록 렌더링
function renderItemList(items) {
    const itemList = document.getElementById('itemList');
    const itemCount = document.getElementById('itemCount');
    itemList.innerHTML = '';
    itemCount.innerText = items.length;

    items.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'item-card bg-slate-900 border border-slate-800 rounded-2xl p-5 transition-all flex flex-col h-full hover:border-slate-600 group cursor-pointer';
        card.innerHTML = `
            <div class="flex justify-between items-start mb-4">
                <span class="text-[10px] font-bold px-2.5 py-1 rounded-lg bg-slate-800 text-blue-400 border border-slate-700 uppercase tracking-wider">${item.type}</span>
                <input type="checkbox" id="check_${index}" value="${index}" class="w-5 h-5 rounded-md border-slate-700 bg-slate-950 text-blue-600 focus:ring-blue-500 cursor-pointer transition-all">
            </div>
            <div class="flex-1">
                <h3 class="font-bold text-base text-slate-100 line-clamp-2 mb-3 leading-tight group-hover:text-blue-400 transition-colors">${item.title}</h3>
                <p class="text-xs text-slate-400 line-clamp-4 leading-relaxed">${item.content}</p>
            </div>
            <div class="mt-6 pt-4 border-t border-slate-800/50 flex justify-between items-center">
                <button type="button" class="detail-btn text-xs text-slate-400 font-semibold hover:text-blue-400 transition-colors flex items-center gap-1">
                    상세보기 <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
                </button>
                ${item.link ? `<a href="${item.link}" target="_blank" class="text-slate-500 hover:text-blue-400 transition-colors"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg></a>` : ''}
            </div>
        `;
        
        // 카드 클릭 시 체크박스 토글
        card.addEventListener('click', (e) => {
            if (e.target.closest('.detail-btn') || e.target.tagName === 'INPUT' || e.target.tagName === 'A' || e.target.closest('a')) return;
            const cb = card.querySelector('input');
            cb.checked = !cb.checked;
            updateSelectedCount();
            card.classList.toggle('selected', cb.checked);
        });

        // 상세보기 버튼 이벤트 (모달 오픈)
        const detailBtn = card.querySelector('.detail-btn');
        detailBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            openModal(item.type, item.title, item.content, item.link);
        });

        // 체크박스 변경 시 카드 스타일 업데이트
        card.querySelector('input').addEventListener('change', (e) => {
            card.classList.toggle('selected', e.target.checked);
            updateSelectedCount();
        });

        itemList.appendChild(card);
    });
    updateSelectedCount();
}

// 모달 관련 로직
const modal = document.getElementById('contentModal');
const modalType = document.getElementById('modalType');
const modalTitle = document.getElementById('modalTitle');
const modalContent = document.getElementById('modalContent');
const modalLink = document.getElementById('modalLink');
const closeModal = document.getElementById('closeModal');

function openModal(type, title, content, link) {
    modalType.innerText = type;
    modalTitle.innerText = title;
    modalContent.innerHTML = content; // HTML 태그(<b> 등) 반영
    
    if (link && link !== '#') {
        modalLink.href = link;
        modalLink.classList.remove('hidden');
    } else {
        modalLink.classList.add('hidden');
    }
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // 스크롤 방지
}

function hideModal() {
    modal.classList.add('hidden');
    document.body.style.overflow = ''; // 스크롤 복원
}

closeModal.addEventListener('click', hideModal);
modal.addEventListener('click', (e) => {
    if (e.target === modal) hideModal();
});

// 키보드 ESC로 모달 닫기
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
        hideModal();
    }
});

// 선택된 항목 개수 업데이트
function updateSelectedCount() {
    const selected = document.querySelectorAll('#itemList input:checked');
    document.getElementById('selectedCount').innerText = selected.length;
}

// 전체 선택/해제
document.getElementById('selectAllBtn').onclick = () => {
    document.querySelectorAll('#itemList input').forEach(cb => {
        cb.checked = true;
        cb.closest('.item-card').classList.add('selected');
    });
    updateSelectedCount();
};
document.getElementById('deselectAllBtn').onclick = () => {
    document.querySelectorAll('#itemList input').forEach(cb => {
        cb.checked = false;
        cb.closest('.item-card').classList.remove('selected');
    });
    updateSelectedCount();
};

// 요약하기 버튼 클릭 이벤트
document.getElementById('summarizeBtn').addEventListener('click', async () => {
    const selectedCheckboxes = document.querySelectorAll('#itemList input:checked');
    if (selectedCheckboxes.length === 0) {
        alert('요약할 항목을 최소 하나 이상 선택해주세요.');
        return;
    }

    const corpName = document.getElementById('corpName').value.trim();
    const selectedContents = Array.from(selectedCheckboxes).map(cb => {
        const item = fetchedItems[cb.value];
        return `[${item.type}] ${item.title}\n${item.content}`;
    });

    const statusArea = document.getElementById('statusArea');
    const statusMessage = document.getElementById('statusMessage');
    const resultArea = document.getElementById('resultArea');
    const summaryContent = document.getElementById('summaryContent');
    const summarizeBtn = document.getElementById('summarizeBtn');

    // UI 초기화
    statusArea.classList.remove('hidden');
    statusMessage.innerText = 'AI가 선택된 정보를 바탕으로 보고서를 작성 중입니다...';
    resultArea.classList.add('hidden');
    summaryContent.innerHTML = '';
    summarizeBtn.disabled = true;

    try {
        const response = await fetch('/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ corp_name: corpName, selected_items: selectedContents })
        });

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
                    if (data.status === 'partial') {
                        statusArea.classList.add('hidden');
                        resultArea.classList.remove('hidden');
                        summaryContent.innerHTML = marked.parse(data.data.summary);
                        window.scrollTo({ top: resultArea.offsetTop - 100, behavior: 'smooth' });
                    } else if (data.status === 'complete') {
                        document.getElementById('resultTitle').innerText = `${corpName} 분석 결과`;
                    }
                } catch (e) { console.error(e); }
            }
        }
    } catch (error) {
        alert('요약 중 오류가 발생했습니다.');
        statusArea.classList.add('hidden');
    } finally {
        summarizeBtn.disabled = false;
    }
});
