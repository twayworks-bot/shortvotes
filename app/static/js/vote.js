// vote.js - 사용자 식별, 이름 충돌 처리, 투표 인터랙션 및 결과 렌더링

let currentUser = null; // { unique_key, user_name }
let pendingConflictName = null;
let myVotedMenuId = null;

document.addEventListener('DOMContentLoaded', () => {
    initUserIdentity();
    loadResults(false);
});

// 1. 사용자 식별 초기화
async function initUserIdentity() {
    const savedUser = StorageUtil.getUser(window.EVENT_SLUG);

    if (savedUser && savedUser.unique_key) {
        // 기존 키 검증 요청
        try {
            const res = await fetch(`${window.APP_PREFIX}/api/events/${window.EVENT_SLUG}/users/identify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ unique_key: savedUser.unique_key })
            });

            const data = await res.json();
            if (data.status === 'VALID' && data.user) {
                currentUser = {
                    unique_key: data.unique_key || data.user.id,
                    user_name: data.user.user_name
                };
                StorageUtil.setUser(window.EVENT_SLUG, currentUser);
                updateUserBar();
                highlightMyVote();
                return;
            } else if (data.status === 'EXPIRED') {
                StorageUtil.removeUser(window.EVENT_SLUG);
                showToast('유효기간(30일)이 만료되어 새 고유키 발급이 필요합니다.', 'warning');
            } else {
                StorageUtil.removeUser(window.EVENT_SLUG);
            }
        } catch (e) {
            console.error('인증 확인 실패:', e);
        }
    }

    // 키가 없거나 만료된 경우: 등록 모달 표시
    showRegisterModal();
}

function showRegisterModal() {
    document.getElementById('user-register-modal').classList.remove('hidden');
    document.getElementById('input-reg-username').focus();
}

function updateUserBar() {
    if (currentUser) {
        document.getElementById('current-user-name').innerText = currentUser.user_name;
        document.getElementById('user-info-bar').classList.remove('hidden');
    }
}

// 2. 신규 사용자 이름 제출 처리
async function submitUserRegistration() {
    const nameInput = document.getElementById('input-reg-username');
    const name = nameInput.value.trim();

    if (!name) {
        showToast('이름을 입력해 주세요.', 'warning');
        nameInput.focus();
        return;
    }

    const btn = document.getElementById('btn-submit-user');
    btn.disabled = true;

    try {
        const res = await fetch(`${window.APP_PREFIX}/api/events/${window.EVENT_SLUG}/users/identify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_name: name })
        });

        const data = await res.json();

        if (data.status === 'VALID' && data.user) {
            // 신규 발급 완료
            currentUser = {
                unique_key: data.unique_key || data.user.id,
                user_name: data.user.user_name
            };
            StorageUtil.setUser(window.EVENT_SLUG, currentUser);
            document.getElementById('user-register-modal').classList.add('hidden');
            updateUserBar();
            showToast(`${currentUser.user_name}님, 환영합니다! 메뉴를 클릭하여 투표하세요.`, 'success');
            loadResults(false);
        } else if (data.status === 'NAME_EXISTS') {
            // 이름 충돌 발생! 모달 표시
            pendingConflictName = name;
            document.getElementById('user-register-modal').classList.add('hidden');
            document.getElementById('conflict-msg-text').innerText = 
                `'${name}' 이름이 이미 등록되어 있습니다. 다른 이름으로 등록하시겠습니까, 아니면 기존 정보를 리셋하고 새로 이어받으시겠습니까?`;
            document.getElementById('name-conflict-modal').classList.remove('hidden');
        } else if (data.status === 'LIMIT_EXCEEDED') {
            showToast(data.message, 'error');
        } else {
            showToast(data.message || '등록 실패', 'error');
        }
    } catch (e) {
        showToast('서버 통신 오류', 'error');
    } finally {
        btn.disabled = false;
    }
}

// 3. 이름 충돌 해결 버튼 처리
function resolveConflictChangeName() {
    document.getElementById('name-conflict-modal').classList.add('hidden');
    document.getElementById('user-register-modal').classList.remove('hidden');
    const input = document.getElementById('input-reg-username');
    input.value = `${pendingConflictName}2`;
    input.focus();
}

async function resolveConflictReset() {
    if (!pendingConflictName) return;

    try {
        const res = await fetch(`${window.APP_PREFIX}/api/events/${window.EVENT_SLUG}/users/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_name: pendingConflictName,
                force_reset: true
            })
        });

        if (!res.ok) {
            const err = await res.json();
            showToast(err.detail || '리셋 등록 실패', 'error');
            return;
        }

        const newUser = await res.json();
        currentUser = {
            unique_key: newUser.id,
            user_name: newUser.user_name
        };
        StorageUtil.setUser(window.EVENT_SLUG, currentUser);
        document.getElementById('name-conflict-modal').classList.add('hidden');
        updateUserBar();
        showToast(`'${currentUser.user_name}' 기존 정보를 리셋하고 새 고유키로 등록되었습니다!`, 'success');
        loadResults(true);
    } catch (e) {
        showToast('리셋 요청 중 통신 오류', 'error');
    }
}

function resetMyIdentity() {
    if (confirm('이름을 변경하시겠습니까? 현재 기기에 저장된 식별 정보가 초기화됩니다.')) {
        StorageUtil.removeUser(window.EVENT_SLUG);
        currentUser = null;
        myVotedMenuId = null;
        document.getElementById('user-info-bar').classList.add('hidden');
        clearMenuCardStyles();
        showRegisterModal();
    }
}

// 4. 메뉴 클릭 투표 처리
async function handleMenuClick(menuItemId) {
    if (window.EVENT_STATUS === 'CLOSED') {
        showToast('이 투표는 마감되었습니다.', 'warning');
        return;
    }

    if (!currentUser || !currentUser.unique_key) {
        showRegisterModal();
        return;
    }

    try {
        const res = await fetch(`${window.APP_PREFIX}/api/events/${window.EVENT_SLUG}/vote`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                unique_key: currentUser.unique_key,
                menu_item_id: menuItemId
            })
        });

        if (!res.ok) {
            const err = await res.json();
            showToast(err.detail || '투표 처리 실패', 'error');
            return;
        }

        const data = await res.json();
        myVotedMenuId = data.menu_item_id;

        updateMenuCardsVisual(myVotedMenuId);
        showToast(data.message, 'success');
        loadResults(false);

    } catch (e) {
        showToast('투표 요청 통신 실패', 'error');
    }
}

function updateMenuCardsVisual(activeMenuId) {
    clearMenuCardStyles();

    if (activeMenuId) {
        const activeCard = document.getElementById(`menu-card-${activeMenuId}`);
        const activeBadge = document.getElementById(`badge-my-choice-${activeMenuId}`);
        if (activeCard) activeCard.classList.add('selected');
        if (activeBadge) activeBadge.classList.remove('hidden');
    }
}

function clearMenuCardStyles() {
    document.querySelectorAll('.menu-card').forEach(card => {
        card.classList.remove('selected');
    });
    document.querySelectorAll('[id^="badge-my-choice-"]').forEach(badge => {
        badge.classList.add('hidden');
    });
}

function highlightMyVote() {
    if (myVotedMenuId) {
        updateMenuCardsVisual(myVotedMenuId);
    }
}

// 5. 탭 전환 (투표하기 vs 결과보기)
function switchVoteTab(tab) {
    const voteBtn = document.getElementById('tab-vote-btn');
    const resultsBtn = document.getElementById('tab-results-btn');
    const panelVote = document.getElementById('panel-vote');
    const panelResults = document.getElementById('panel-results');

    if (tab === 'vote') {
        voteBtn.className = 'py-2.5 px-3 text-sm font-bold border-b-2 border-indigo-600 text-indigo-600 flex items-center gap-1.5 transition-colors';
        resultsBtn.className = 'py-2.5 px-3 text-sm font-bold border-b-2 border-transparent text-slate-500 hover:text-slate-800 flex items-center gap-1.5 transition-colors';
        panelVote.classList.remove('hidden');
        panelResults.classList.add('hidden');
    } else {
        resultsBtn.className = 'py-2.5 px-3 text-sm font-bold border-b-2 border-indigo-600 text-indigo-600 flex items-center gap-1.5 transition-colors';
        voteBtn.className = 'py-2.5 px-3 text-sm font-bold border-b-2 border-transparent text-slate-500 hover:text-slate-800 flex items-center gap-1.5 transition-colors';
        panelVote.classList.add('hidden');
        panelResults.classList.remove('hidden');
        loadResults(true);
    }
}

// 6. 결과 집계 조회 및 렌더링
async function loadResults(showToastMsg = false) {
    try {
        const userParam = currentUser && currentUser.unique_key ? `?unique_key=${currentUser.unique_key}` : '';
        const res = await fetch(`${window.APP_PREFIX}/api/events/${window.EVENT_SLUG}/results${userParam}`);

        if (!res.ok) return;

        const data = await res.json();
        document.getElementById('total-vote-count').innerText = data.total_votes;
        document.getElementById('res-total-votes').innerText = data.total_votes;
        document.getElementById('res-total-users').innerText = data.total_participants;

        if (data.my_vote_menu_id) {
            myVotedMenuId = data.my_vote_menu_id;
            highlightMyVote();
        }

        renderResultsList(data);

        if (showToastMsg) {
            showToast('투표 결과를 갱신했습니다.', 'info');
        }
    } catch (e) {
        console.error('결과 로드 실패:', e);
    }
}

function renderResultsList(data) {
    const container = document.getElementById('results-list');
    container.innerHTML = '';

    if (data.items.length === 0) {
        container.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">등록된 메뉴가 없습니다.</div>';
        return;
    }

    // 득표순 정렬
    const sorted = [...data.items].sort((a, b) => b.vote_count - a.vote_count);

    sorted.forEach((item, index) => {
        const isMyChoice = item.menu_item_id === myVotedMenuId;
        const itemDiv = document.createElement('div');
        itemDiv.className = `p-3.5 rounded-xl border ${isMyChoice ? 'border-indigo-400 bg-indigo-50/30' : 'border-slate-100 bg-slate-50/50'} space-y-2`;

        itemDiv.innerHTML = `
            <div class="flex items-center justify-between text-xs">
                <div class="flex items-center gap-2">
                    <span class="w-5 h-5 rounded-md ${index === 0 && item.vote_count > 0 ? 'bg-amber-100 text-amber-700 font-bold' : 'bg-slate-200 text-slate-600'} text-[11px] flex items-center justify-center font-bold">
                        ${index + 1}
                    </span>
                    <span class="font-bold text-slate-900">${item.name}</span>
                    ${isMyChoice ? '<span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-600 text-white">내 선택</span>' : ''}
                </div>
                <div class="flex items-center gap-2">
                    <span class="font-bold ${item.vote_count > 0 ? 'text-indigo-600' : 'text-slate-400'}">${item.vote_count}표</span>
                    <span class="text-slate-400 text-[11px]">(${item.percentage}%)</span>
                </div>
            </div>

            <!-- 프로그레스 바 -->
            <div class="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                <div class="bg-gradient-to-r from-fuchsia-500 to-indigo-600 h-2 rounded-full transition-all duration-500" style="width: ${item.percentage}%"></div>
            </div>

            <!-- 투표자 명단 -->
            ${item.voters && item.voters.length > 0 ? `
            <div class="pt-1 flex flex-wrap gap-1 items-center">
                <span class="text-[10px] text-slate-400 mr-1">투표자:</span>
                ${item.voters.map(v => `<span class="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 text-[10px] font-medium">${v}</span>`).join('')}
            </div>
            ` : ''}
        `;

        container.appendChild(itemDiv);
    });
}

function copyCurrentUrl() {
    copyToClipboard(window.location.href, '투표 링크가 복사되었습니다!');
}
