// ai_parser.js - 메뉴 자동 추출 및 이벤트 생성 관리 스크립트

let menuItems = []; // 현재 테이블에 등록된 메뉴 배열 [{name, category, price}]
let selectedImageFile = null;
let createdSlug = null;

// 1. 탭 전환
function switchMenuTab(tab) {
    const tabs = ['ocr', 'text', 'manual'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab-btn-${t}`);
        const content = document.getElementById(`tab-content-${t}`);
        if (t === tab) {
            btn.className = 'py-2.5 px-4 text-xs font-bold border-b-2 border-indigo-600 text-indigo-600 flex items-center gap-1.5 transition-colors';
            content.classList.remove('hidden');
        } else {
            btn.className = 'py-2.5 px-4 text-xs font-bold border-b-2 border-transparent text-slate-500 hover:text-slate-800 flex items-center gap-1.5 transition-colors';
            content.classList.add('hidden');
        }
    });
}

// 2. 이미지 파일 드래그앤드롭 및 선택 리스너
document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('image-file-input');

    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => fileInput.click());

        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('border-indigo-500', 'bg-indigo-100/40');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('border-indigo-500', 'bg-indigo-100/40');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('border-indigo-500', 'bg-indigo-100/40');
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleImageSelected(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                handleImageSelected(e.target.files[0]);
            }
        });
    }
});

function handleImageSelected(file) {
    if (!file.type.startsWith('image/')) {
        showToast('이미지 파일만 선택할 수 있습니다.', 'warning');
        return;
    }
    selectedImageFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('image-preview').src = e.target.result;
        document.getElementById('image-name').innerText = file.name;
        document.getElementById('image-preview-container').classList.remove('hidden');
    };
    reader.readAsDataURL(file);
}

// 3. 이미지 OCR 실행
async function startImageOcr() {
    if (!selectedImageFile) {
        showToast('먼저 메뉴판 이미지를 선택해 주세요.', 'warning');
        return;
    }

    const aiLoading = document.getElementById('ai-loading');
    const btn = document.getElementById('btn-run-ocr');
    aiLoading.classList.remove('hidden');
    btn.disabled = true;

    try {
        const formData = new FormData();
        formData.append('image_file', selectedImageFile);

        // 기존에 이미 등록된 메뉴 리스트가 있다면 참조용으로 전달
        if (menuItems.length > 0) {
            const existingNames = menuItems.map(m => m.name);
            formData.append('existing_menus', JSON.stringify(existingNames));
        }

        const res = await fetch(`${window.APP_PREFIX}/api/ai/ocr-menu`, {
            method: 'POST',
            body: formData
        });

        const data = await res.json();
        if (!res.ok || !data.success) {
            showToast(data.message || '메뉴 추출에 실패했습니다.', 'error');
            return;
        }

        // 추출된 메뉴 추가
        if (data.items && data.items.length > 0) {
            data.items.forEach(item => {
                menuItems.push({
                    name: item.name,
                    category: item.category || '기본',
                    price: item.price || 0
                });
            });
            renderMenuTable();
            showToast(`${data.items.length}개 메뉴가 AI로 추출 및 오타 교정되었습니다!`, 'success');
        } else {
            showToast('이미지에서 인식된 메뉴가 없습니다.', 'warning');
        }
    } catch (e) {
        showToast('AI 서비스 통신 중 오류가 발생했습니다.', 'error');
    } finally {
        aiLoading.classList.add('hidden');
        btn.disabled = false;
    }
}

// 4. 텍스트 파싱 실행
async function startTextParse() {
    const rawText = document.getElementById('raw-menu-text').value.trim();
    if (!rawText) {
        showToast('메뉴 텍스트를 입력해 주세요.', 'warning');
        return;
    }

    const aiLoading = document.getElementById('ai-loading');
    const btn = document.getElementById('btn-run-text');
    aiLoading.classList.remove('hidden');
    btn.disabled = true;

    try {
        const payload = {
            raw_text: rawText,
            existing_menus: menuItems.map(m => m.name)
        };

        const res = await fetch(`${window.APP_PREFIX}/api/ai/text-menu`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok || !data.success) {
            showToast(data.message || '텍스트 정제에 실패했습니다.', 'error');
            return;
        }

        if (data.items && data.items.length > 0) {
            data.items.forEach(item => {
                menuItems.push({
                    name: item.name,
                    category: item.category || '기본',
                    price: item.price || 0
                });
            });
            renderMenuTable();
            document.getElementById('raw-menu-text').value = '';
            showToast(`${data.items.length}개 메뉴가 오타 교정 및 정형화되었습니다!`, 'success');
        } else {
            showToast('유효한 메뉴 항목을 찾을 수 없습니다.', 'warning');
        }
    } catch (e) {
        showToast('통신 오류가 발생했습니다.', 'error');
    } finally {
        aiLoading.classList.add('hidden');
        btn.disabled = false;
    }
}

// 5. 메뉴 테이블 렌더링 및 조작
function renderMenuTable() {
    const tbody = document.getElementById('menu-tbody');
    const countBadge = document.getElementById('menu-count-badge');
    countBadge.innerText = menuItems.length;

    if (menuItems.length === 0) {
        tbody.innerHTML = `
            <tr id="empty-row" class="text-center text-slate-400 py-6">
                <td colspan="5" class="py-8">
                    등록된 메뉴가 없습니다. 상단에서 AI 추출을 진행하거나 [+ 메뉴 직접 추가]를 누르세요.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = '';
    menuItems.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50 transition-colors';
        tr.innerHTML = `
            <td class="py-2.5 px-3 text-center text-slate-400 font-mono">${index + 1}</td>
            <td class="py-2.5 px-3">
                <input type="text" value="${escapeHtml(item.name)}" onchange="updateItemName(${index}, this.value)" class="w-full px-2 py-1 text-xs border border-transparent hover:border-slate-300 focus:border-indigo-500 rounded bg-transparent focus:bg-white focus:outline-none">
            </td>
            <td class="py-2.5 px-3">
                <input type="text" value="${escapeHtml(item.category)}" onchange="updateItemCategory(${index}, this.value)" class="w-full px-2 py-1 text-xs border border-transparent hover:border-slate-300 focus:border-indigo-500 rounded bg-transparent focus:bg-white focus:outline-none">
            </td>
            <td class="py-2.5 px-3">
                <input type="number" value="${item.price}" onchange="updateItemPrice(${index}, this.value)" class="w-full px-2 py-1 text-xs border border-transparent hover:border-slate-300 focus:border-indigo-500 rounded bg-transparent focus:bg-white focus:outline-none">
            </td>
            <td class="py-2.5 px-3 text-center">
                <button type="button" onclick="removeMenuItem(${index})" class="text-slate-400 hover:text-rose-600 transition-colors p-1">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function addMenuRow() {
    menuItems.push({
        name: '새 메뉴 항목',
        category: '기본',
        price: 0
    });
    renderMenuTable();
}

function removeMenuItem(index) {
    menuItems.splice(index, 1);
    renderMenuTable();
}

function updateItemName(index, val) {
    menuItems[index].name = val.trim();
}

function updateItemCategory(index, val) {
    menuItems[index].category = val.trim();
}

function updateItemPrice(index, val) {
    menuItems[index].price = parseInt(val) || 0;
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// 6. 이벤트 최종 생성 제출
async function submitCreateEvent() {
    const title = document.getElementById('event-title').value.trim();
    const slug = document.getElementById('event-slug').value.trim();
    const pin = document.getElementById('event-pin').value.trim();
    const description = document.getElementById('event-desc').value.trim();

    if (!title) {
        showToast('이벤트 제목을 입력해 주세요.', 'warning');
        document.getElementById('event-title').focus();
        return;
    }

    if (!pin || pin.length < 4) {
        showToast('관리자 핀코드(PIN)를 최소 4자리 이상 입력해 주세요.', 'warning');
        document.getElementById('event-pin').focus();
        return;
    }

    if (menuItems.length === 0) {
        showToast('최소 1개 이상의 메뉴를 등록해야 합니다.', 'warning');
        return;
    }

    const btn = document.getElementById('btn-submit-event');
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> 생성 중...`;

    try {
        const payload = {
            title: title,
            slug: slug || null,
            pin: pin,
            description: description,
            menu_items: menuItems.map((m, idx) => ({
                name: m.name,
                category: m.category,
                price: m.price,
                display_order: idx
            }))
        };

        const res = await fetch(`${window.APP_PREFIX}/api/events`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            showToast(err.detail || '이벤트 생성 실패', 'error');
            return;
        }

        const data = await res.json();
        createdSlug = data.slug;

        // 성공 모달 띄우기
        const fullUrl = `${window.location.origin}${window.APP_PREFIX}/${data.slug}`;
        document.getElementById('share-link-input').value = fullUrl;
        document.getElementById('success-modal').classList.remove('hidden');

    } catch (e) {
        showToast('서버와의 통신에 실패했습니다.', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-check"></i> 이벤트 개설 및 링크 생성 완료`;
    }
}

function copyShareLink() {
    const input = document.getElementById('share-link-input');
    copyToClipboard(input.value, '투표 링크가 복사되었습니다!');
}

function goToVotePage() {
    if (createdSlug) {
        window.location.href = `${window.APP_PREFIX}/${createdSlug}`;
    }
}

function goToAdminPage() {
    if (createdSlug) {
        window.location.href = `${window.APP_PREFIX}/${createdSlug}/admin`;
    }
}
