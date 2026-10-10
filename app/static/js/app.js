// app.js - ShortVotes 전역 유틸리티 함수

// 1. 토스트 알림 함수
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast-item pointer-events-auto flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-lg text-xs font-semibold text-white max-w-sm`;

    let bgColor = 'bg-slate-800';
    let icon = 'fa-info-circle';

    if (type === 'success') {
        bgColor = 'bg-emerald-600';
        icon = 'fa-check-circle';
    } else if (type === 'error') {
        bgColor = 'bg-rose-600';
        icon = 'fa-exclamation-circle';
    } else if (type === 'warning') {
        bgColor = 'bg-amber-600';
        icon = 'fa-triangle-exclamation';
    }

    toast.classList.add(bgColor);
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    // 슬라이드 애니메이션
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // 3.5초 후 제거
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// 2. LocalStorage 래퍼
const StorageUtil = {
    getKey(slug) {
        return `shortvotes_user_${slug}`;
    },
    getUser(slug) {
        try {
            const raw = localStorage.getItem(this.getKey(slug));
            if (!raw) return null;
            const data = JSON.parse(raw);

            // 클라이언트 사이드 30일(초 단위 2,592,000s) 만료 검사
            const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;
            if (data.issued_at && (Date.now() - data.issued_at > THIRTY_DAYS_MS)) {
                this.removeUser(slug);
                return null;
            }
            return data;
        } catch (e) {
            return null;
        }
    },
    setUser(slug, userObj) {
        try {
            const payload = {
                unique_key: userObj.unique_key || userObj.id,
                user_name: userObj.user_name,
                issued_at: userObj.issued_at || Date.now()
            };
            localStorage.setItem(this.getKey(slug), JSON.stringify(payload));
        } catch (e) {
            console.error('LocalStorage 저장 실패:', e);
        }
    },
    removeUser(slug) {
        try {
            localStorage.removeItem(this.getKey(slug));
        } catch (e) {}
    }
};

// 3. 클립보드 복사
function copyToClipboard(text, successMsg = '복사되었습니다!') {
    navigator.clipboard.writeText(text).then(() => {
        showToast(successMsg, 'success');
    }).catch(() => {
        showToast('클립보드 복사에 실패했습니다.', 'error');
    });
}
