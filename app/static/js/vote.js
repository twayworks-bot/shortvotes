// vote.js - 사용자 식별, 이름 충돌 처리, 투표 인터랙션 및 결과 렌더링

let currentUser = null; // { unique_key, user_name, option_text }
let pendingConflictName = null;
let myVotedMenuId = null;

document.addEventListener('DOMContentLoaded', async () => {
    await initUserIdentity();
    await loadResults(false);
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
                const resolvedOpt = (data.vote_option !== undefined && data.vote_option !== null)
                    ? data.vote_option
                    : (data.user.option_text || savedUser.option_text || "");
                currentUser = {
                    unique_key: data.unique_key || data.user.id,
                    user_name: data.user.user_name,
                    option_text: resolvedOpt
                };
                if (data.voted_menu_id !== undefined) {
                    myVotedMenuId = data.voted_menu_id;
                }
                StorageUtil.setUser(window.EVENT_SLUG, currentUser);
                updateUserBar();
                updateMenuCardsVisual(myVotedMenuId);
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
        const opt = (currentUser.option_text || "").trim();
        const nameEl = document.getElementById('current-user-name');
        if (window.EVENT_ENABLE_OPTIONS && opt) {
            nameEl.innerText = `${currentUser.user_name}(${opt})`;
        } else {
            nameEl.innerText = currentUser.user_name;
        }
        document.getElementById('user-info-bar').classList.remove('hidden');

        const optInput = document.getElementById('vote-option-input');
        if (optInput && document.activeElement !== optInput) {
            optInput.value = opt;
        }
        syncPresetButtonsVisual();
    }
}

// 기본 옵션 칩(hot, cold, 오트밀, 샷추가 등) 선택/토글 처리
function togglePresetOption(optName) {
    const optInput = document.getElementById('vote-option-input');
    if (!optInput) return;

    let parts = optInput.value
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0);

    const lowerTarget = optName.toLowerCase();
    const existingIdx = parts.findIndex(p => p.toLowerCase() === lowerTarget);

    if (existingIdx >= 0) {
        // 이미 선택된 기본 옵션이면 제거 (토글)
        parts.splice(existingIdx, 1);
    } else {
        // hot / cold 온도 옵션은 상호 배타적으로 교체 후 맨 앞에 배치
        if (lowerTarget === 'hot' || lowerTarget === 'cold') {
            parts = parts.filter(p => {
                const lp = p.toLowerCase();
                return lp !== 'hot' && lp !== 'cold';
            });
            parts.unshift(optName);
        } else {
            parts.push(optName);
        }
    }

    optInput.value = parts.join(', ');
    syncPresetButtonsVisual();
    saveVoteOption(true);
}

function clearVoteOption() {
    const optInput = document.getElementById('vote-option-input');
    if (!optInput) return;
    optInput.value = '';
    syncPresetButtonsVisual();
    saveVoteOption(false);
}

function syncPresetButtonsVisual() {
    const optInput = document.getElementById('vote-option-input');
    if (!optInput) return;

    const activeSet = new Set(
        optInput.value
            .split(',')
            .map(s => s.trim().toLowerCase())
            .filter(s => s.length > 0)
    );

    document.querySelectorAll('.preset-opt-btn').forEach(btn => {
        const opt = (btn.getAttribute('data-opt') || '').toLowerCase();
        if (activeSet.has(opt)) {
            btn.className = 'preset-opt-btn px-2 py-0.5 rounded-full border border-indigo-600 bg-indigo-600 text-white text-[11px] font-bold transition-colors shadow-sm';
        } else {
            btn.className = 'preset-opt-btn px-2 py-0.5 rounded-full border border-slate-200 bg-slate-50 hover:border-indigo-300 hover:bg-indigo-50 text-slate-600 text-[11px] font-medium transition-colors';
        }
    });
}

// 옵션선택 버튼 클릭(또는 엔터/칩 선택) 시 서버에 추가옵션 기록 및 저장
async function saveVoteOption(silent = false) {
    if (!window.EVENT_ENABLE_OPTIONS) return;

    if (window.EVENT_STATUS === 'CLOSED') {
        if (!silent) showToast('이미 마감된 투표입니다.', 'warning');
        return;
    }

    if (!currentUser || !currentUser.unique_key) {
        showRegisterModal();
        return;
    }

    const optInput = document.getElementById('vote-option-input');
    const optText = optInput ? optInput.value.trim() : '';

    try {
        const res = await fetch(`${window.APP_PREFIX}/api/events/${window.EVENT_SLUG}/vote/option`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                unique_key: currentUser.unique_key,
                option_text: optText
            })
        });

        if (!res.ok) {
            const err = await res.json();
            if (!silent) showToast(err.detail || '옵션 저장 실패', 'error');
            return;
        }

        const data = await res.json();
        currentUser.option_text = data.option_text || '';
        StorageUtil.setUser(window.EVENT_SLUG, currentUser);
        updateUserBar();
        loadResults(false);

        if (!silent) {
            showToast(data.message || '옵션이 저장되었습니다.', 'success');
        }
    } catch (e) {
        if (!silent) showToast('옵션 저장 중 통신 오류', 'error');
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
                user_name: data.user.user_name,
                option_text: data.user.option_text || ""
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
            user_name: newUser.user_name,
            option_text: newUser.option_text || ""
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
        const nameEl = document.getElementById('current-user-name');
        if (nameEl) nameEl.innerText = '이름 입력 필요';
        const optInput = document.getElementById('vote-option-input');
        if (optInput) optInput.value = '';
        syncPresetButtonsVisual();
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

    const optInput = document.getElementById('vote-option-input');
    const optionText = (window.EVENT_ENABLE_OPTIONS && optInput) ? optInput.value.trim() : null;

    try {
        const payload = {
            unique_key: currentUser.unique_key,
            menu_item_id: menuItemId
        };
        if (optionText !== null) {
            payload.option_text = optionText;
        }

        const res = await fetch(`${window.APP_PREFIX}/api/events/${window.EVENT_SLUG}/vote`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            showToast(err.detail || '투표 처리 실패', 'error');
            return;
        }

        const data = await res.json();
        myVotedMenuId = data.menu_item_id;
        if (window.EVENT_ENABLE_OPTIONS && data.option_text !== undefined) {
            currentUser.option_text = data.option_text || "";
            StorageUtil.setUser(window.EVENT_SLUG, currentUser);
            updateUserBar();
        }

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
    updateMenuCardsVisual(myVotedMenuId);
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
        loadResults(false);
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

        if (data.my_vote_menu_id !== undefined) {
            myVotedMenuId = data.my_vote_menu_id;
            highlightMyVote();
        }
        if (currentUser && window.EVENT_ENABLE_OPTIONS && data.my_vote_option !== undefined) {
            currentUser.option_text = data.my_vote_option || "";
            StorageUtil.setUser(window.EVENT_SLUG, currentUser);
            updateUserBar();
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
