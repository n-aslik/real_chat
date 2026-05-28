

function parseJwt(token) {
    try {
        return JSON.parse(atob(token.split('.')[1]));
    } catch {
        return null;
    }
}

const token = localStorage.getItem('chat_token');
if (!token) window.location.href = "/chats/v1/sign-in";

let roomId = localStorage.getItem('chat_room_id');
let ws = null;
let usersCache = [];




function connectWebSocket() {

    console.log(555555)
    if (!roomId) return;
    const wsUrl = `ws://${window.location.host}/chats/v1/ws/chat/${roomId}?token=${token}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log(99999)
    }

    ws.onmessage = (event) => {

        console.log(666666)

        const data = JSON.parse(event.data);
    
    
    
        // DELETE
        if (data.action === 'delete') {
    
            const el = document.getElementById(`msg-${data.message_id}`);
    
            if (el) {
                el.remove();
                loadedMessages.delete(String(data.message_id));
            }
    
            return;
        }

        const messageId = data.id || data.message_id; 
        const el = messageId ? document.getElementById(`msg-${messageId}`) : null;

        if (el && (data.action === 'update' || data.status === 0)) {
            
            const textDiv = el.querySelector('.text-content'); 
            if (textDiv) {
                textDiv.innerText = data.messages; 

                let timeStr = data.day || data.edited_text; 
                
                if (!timeStr) {
                    const now = new Date();
                    const hh = String(now.getHours()).padStart(2, '0');
                    const mm = String(now.getMinutes()).padStart(2, '0');
                    timeStr = `${hh}:${mm}`; 
                }

                let timeDiv = el.querySelector('.text-right');
                if (timeDiv) {
                    timeDiv.innerText = timeStr;
                }
                
                console.log(`Сообщение msg-${messageId} успешно обновлено. Время из ответа: ${timeStr}`);
            } else {
                console.error("Не найден элемент .text-content внутри сообщения"); 
            }
            return; // Выходим, так как мы обновили СУЩЕСТВУЮЩЕЕ сообщение
        }
        
        // Если это не редактирование существующего сообщения, а экшен 'update' без элемента — это странно
        if (el && data.action === 'update') {
            const textDiv = el.querySelector('.text-content'); 
            if (textDiv) {
                textDiv.innerText = data.messages; 
        
                let timeStr = data.day || data.edited_text; 
                if (!timeStr) {
                    const now = new Date();
                    const hh = String(now.getHours()).padStart(2, '0');
                    const mm = String(now.getMinutes()).padStart(2, '0');
                    timeStr = `${hh}:${mm}`; 
                }
        
                let timeDiv = el.querySelector('.text-right');
                if (timeDiv) {
                    timeDiv.innerText = timeStr;
                }
                console.log(`Сообщение msg-${messageId} успешно обновлено.`);
            }
            return; // Выходим, так как обновили существующее
        }
        // ЕСЛИ ЭЛЕМЕНТА НЕ БЫЛО НА СТРАНИЦЕ — это новое сообщение! Отрисовываем его:
        displayMessage(data);
    };

    ws.onclose = (v) => {
        console.log(v,"v")
        console.log("WS reconnect...");
        setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = (e) => console.error("WS error:", e);
}

let editMessageId = null;

// Добавляем аргумент event
function sendMessage(event) {
    // Если событие передано (например, клик или нажатие Enter), отменяем отправку формы
    if (event) {
        event.preventDefault();
    }

    const messageInput = document.getElementById('messageInput');
    const fileInput = document.getElementById('fileInput');
    const message = messageInput.value.trim();

    if (!message && (!fileInput.files || fileInput.files.length === 0)) return;

    const sendData = (fileData = null, fileName = null) => {
        const payload = {
            "messages": message,
            "file_path": fileData, 
            "file_name": fileName
        };
        
        // Если это редактирование
        if (editMessageId) {
            payload["action"] = "update";
            payload["message_id"] = editMessageId;
        } else {
            // Рекомендуется явно указывать экшен создания для бэкенда, если он требуется
            payload["action"] = "create"; 
        }

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(payload));
            messageInput.value = '';
            fileInput.value = ''; 
            editMessageId = null; 
            
            // Замена селектора на более безопасный, так как мы изменили onclick
            const btn = document.querySelector('button[onclick*="sendMessage"]');
            if (btn) btn.innerText = "➤";
        } else {
            console.error("WebSocket не подключен. Состояние:", ws ? ws.readyState : "null");
        }
    };

    if (fileInput.files && fileInput.files[0]) {
        const file = fileInput.files[0];
        const reader = new FileReader();
        reader.onload = (e) => sendData(e.target.result, file.name);
        reader.readAsDataURL(file);
    } else {
        sendData();
    }
}
window.startEdit = function(id, text) {
    text = decodeURIComponent(text);
    editMessageId = id;
    const input = document.getElementById('messageInput');
    input.value = text;
    input.focus();
    
    const btn = document.querySelector('button[onclick="sendMessage()"]');
    if (btn) btn.innerText = "💾"; 
};

window.deleteMessage = function(id) {
    if (!confirm("Удалить это сообщение?")) return;

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            "action": "delete",
            "message_id": id
        }));
    }
};

/**
 * Управляет видимостью поля ввода сообщений и кнопки вложений
 */
function checkInputPermissions() {
    const inputArea = document.getElementById('messageInput');
    const fileArea = document.getElementById('fileInput');
    if (!inputArea && ! fileArea) return;

    const userData = parseJwt(token);
    const roleId = userData?.role_id;
    const isGroup = localStorage.getItem('is_group_chat') === 'true';

    if (isGroup) {
        if (roleId === 1) {
            inputArea.style.display = 'flex';
            fileArea.style.display = 'flex';
        } else {
            inputArea.style.display = 'none';
            fileArea.style.display = 'None';
        }
    } 
    // Сценарий 2: Обычный чат (Диалог)
    // Разрешаем ввод только если role_id === 2 (или 1, если админ тоже может там писать)
    else {
        if (roleId === 2 || roleId === 1) {
            inputArea.style.display = 'flex';
        } else {
            inputArea.style.display = 'none';
        }
    }
}



// Функция, которая вызывается при клике на иконку корзины в списке чатов
let chatToDeleteId = null;

window.deleteChat = function (chatId, event) {
    if (event) event.stopPropagation(); // Останавливаем открытие чата при клике на корзину
    
    chatToDeleteId = chatId;
    
    const modal = document.getElementById('delete-chat-modal');
    const checkbox = document.getElementById('delete-all-checkbox');
    
    // Каждый раз при открытии снимаем галочку
    if (checkbox) checkbox.checked = false;

    // Просто показываем модальное окно (оно одинаково для всех)
    if (modal) modal.classList.remove('hidden');
};

// Инициализация обработчиков для новой модалки
document.addEventListener('DOMContentLoaded', () => {
    // Клик по кнопке "Удалить" в модальном окне
    // Находим элементы модалки на странице
    const deleteModal = document.getElementById('delete-chat-modal');
const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
const confirmDeleteBtn = document.getElementById('confirm-delete-btn');

if (cancelDeleteBtn && deleteModal) {
    cancelDeleteBtn.onclick = () => deleteModal.classList.add('hidden');
}

if (confirmDeleteBtn) {
    confirmDeleteBtn.onclick = async () => {
        const checkbox = document.getElementById('delete-all-checkbox');
        
        // Значение переменнойisAll строго зависит от того, поставлена галочка или нет
        const isAll = checkbox ? checkbox.checked : false;

        if (deleteModal) deleteModal.classList.add('hidden');

        try {
            // Отправляем запрос на бэкенд: is_all будет true или false
            const url = `/chats/v1/delete-chat?chat_id=${encodeURIComponent(chatToDeleteId)}&is_all=${isAll}`; //
            const res = await fetch(url, { //
                method: 'DELETE', //
                headers: { 'Authorization': `Bearer ${token}` } //
            });

            if (!res.ok) { //
                const errorData = await res.json(); //
                throw new Error(errorData.detail || "Ошибка при удалении чата"); //
            }

            alert(isAll ? "Чат успешно удален для всех участников" : "Чат успешно удален"); //

            // Если удалили чат, который сейчас открыт — чистим localstorage
            const currentRoomId = localStorage.getItem('chat_room_id'); //
            if (String(currentRoomId) === String(chatToDeleteId)) { //
                localStorage.removeItem('chat_room_id'); //
                localStorage.removeItem('chat_room_name'); //
                localStorage.removeItem('is_group_chat'); //
            }

            window.location.reload(); // Перезагрузка страницы
        } catch (err) {
            console.error("Ошибка удаления чата:", err); //
            alert("Не удалось удалить чат: " + err.message); //
        }
    };
}
});

let oldestCursor = null;
let isLoadingHistory = false;
let hasMoreMessages = true;
let initialHistoryLoaded = false;

const loadedMessages = new Set();

async function loadChatHistory(roomId, isPrepend = false) {

    if (isLoadingHistory) return;

    if (isPrepend && !hasMoreMessages) return;

    const container = document.getElementById("messages-container");

    if (!container) return;

    isLoadingHistory = true;

    // Сохраняем позицию скролла
    const previousScrollHeight = container.scrollHeight;
    const previousScrollTop = container.scrollTop;

    var pageSize = 100;

    try {

        // -----------------------------
        // Формируем URL
        // -----------------------------

        let url = `/chats/v1/chats/${roomId}/history?limit=${pageSize}`;
        pageSize++

        // Если это подгрузка старых сообщений —
        // отправляем cursor
        if (isPrepend && oldestCursor) {

            url +=
                `&last_date=${encodeURIComponent(oldestCursor.send_at)}` +
                `&last_id=${oldestCursor.id}`;
        }

        const res = await fetch(url, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });

        if (!res.ok) {
            throw new Error("Ошибка загрузки истории");
        }

        const response = await res.json();

        console.log("История чата:", response);

        // PostgreSQL json_agg response
        let finalMessages = [];

        if (Array.isArray(response) && response[0]?.j) {
            finalMessages = response[0].j;
        }
        else if (Array.isArray(response)) {
            finalMessages = response;
        }

        // -----------------------------
        // Если сообщений больше нет
        // -----------------------------

        if (!finalMessages || finalMessages.length === 0) {

            hasMoreMessages = false;

            return;
        }

        // -----------------------------
        // Обновляем cursor
        // -----------------------------

        // Сервер возвращает:
        // old -> new
        // Поэтому первый элемент —
        // самое старое сообщение страницы

        const oldestMessage = finalMessages[0];

        oldestCursor = {
            send_at: oldestMessage.send_at,
            id: oldestMessage.message_id
        };

        // -----------------------------
        // Проверяем конец истории
        // -----------------------------

        if (finalMessages.length < pageSize) {
            hasMoreMessages = false;
        }

        // -----------------------------
        // PREPEND старых сообщений
        // -----------------------------

        if (isPrepend) {

            finalMessages.forEach(msg => {

                // защита от дублей
                if (loadedMessages.has(msg.message_id)) {
                    return;
                }

                loadedMessages.add(msg.message_id);

                displayMessage(msg, true);
            });

            // Восстанавливаем scroll position
            container.scrollTop =
                container.scrollHeight
                - previousScrollHeight
                + previousScrollTop;
        }

        // -----------------------------
        // INITIAL LOAD
        // -----------------------------

        else {

            container.innerHTML = "";

            loadedMessages.clear();

            finalMessages.forEach(msg => {

                loadedMessages.add(msg.message_id);

                displayMessage(msg);
            });

            // Скролл вниз
            requestAnimationFrame(() => {
                container.scrollTop = container.scrollHeight;
            });

            initialHistoryLoaded = true;
        }

    }
    catch (err) {

        console.error("Ошибка истории:", err);
    }
    finally {

        isLoadingHistory = false;
    }
}


function displayMessage(data, prepend = false) {
    let html = '';
    const container = document.getElementById("messages-container");
    if (!container) return;

    // Проверяем все возможные варианты ID
    const msgId = data.message_id || data.id;

    if (!msgId) {
        console.error("Ошибка: у сообщения нет ID", data);
        return; 
    }

    if (loadedMessages.has(String(msgId))) return;
    loadedMessages.add(String(msgId));

    const myId = parseJwt(token)?.user_id;
    const isMy = String(data.sender_id) === String(myId);

    const div = document.createElement("div");
    div.id = `msg-${msgId}`;
    div.className = `flex flex-col ${isMy ? "items-end" : "items-start"} mb-3 group relative`;

    const fileUrl = `/chats/v1/files/${data.file_name}`;
    const textContent = data.messages || ""; 

    // 1. Сначала инициализируем строку html
    html = `
        ${!isMy ? `<span class="text-[10px] text-indigo-400 mb-1 ml-1">${data.username || 'Аноним'}</span>` : ''}
        <div class="relative px-4 py-2 rounded-xl max-w-[70%] ${isMy ? 'bg-indigo-600 text-white' : 'bg-white border shadow-sm'}">
    `;

    // Кнопки редактирования
    if (isMy) {
        html += `
            <div class="hidden group-hover:flex gap-2 absolute -left-16 top-1 text-gray-400 text-xs bg-gray-100 p-1 rounded shadow">
                ${!data.file_name ? `<button onclick="startEdit('${msgId}', '${encodeURIComponent(textContent)}')">✏️</button>` : ''}
                <button onclick="deleteMessage('${msgId}')">🗑️</button>
            </div>
        `;
    }

    // Отображение файла
    if (data.file_name) {
        const isImg = data.file_name.match(/\.(jpg|jpeg|png|gif|webp)$/i);
        html += isImg 
            ? `<img src="${fileUrl}" class="rounded mb-2 max-h-64 cursor-pointer" onclick="window.open('${fileUrl}')">`
            : `<a href="${fileUrl}" target="_blank" download class="flex items-center space-x-2 underline mb-2 block text-sm"><span>📁</span><span class="truncate">${data.file_name}</span></a>`;
    }

    // 2. ТЕПЕРЬ безопасно добавляем текст сообщения
    if (textContent) {
        // text-content содержит ТОЛЬКО чистый текст сообщения
        html += `<div class="text-content break-words">${textContent}</div>`; //
    }
    let displayTime = data.day;
    if (!displayTime) {
        const now = new Date();
        const hh = String(now.getHours()).padStart(2, '0');
        const mm = String(now.getMinutes()).padStart(2, '0');
        displayTime = `${hh}:${mm}`; 
    }
    // Закрываем контейнеры и выводим ровно ОДНУ строку времени/статуса, пришедшую из БД (data.day)
    html += `<div class="text-[10px] ${isMy ? 'text-indigo-200' : 'text-gray-400'} mt-1 text-right">${displayTime}</div></div>`;
    div.innerHTML = html; //

    if (prepend) {
        container.prepend(div);
    } else {
        container.appendChild(div);
        if (container.scrollHeight - container.scrollTop - container.clientHeight < 150) {
            container.scrollTop = container.scrollHeight;
        }
    }
}

window.triggerFileInput = () =>
    document.getElementById('fileInput').click();

window.uploadFile = async function (event) {
    const file = event.target.files[0];
    if (!file || ws?.readyState !== WebSocket.OPEN) return;

    // 1. Подготавливаем данные для отправки в MinIO
    const formData = new FormData();
    formData.append('file', file);

    try {
        // 2. Отправляем файл на ваш новый эндпоинт
        const response = await fetch('/chats/v1/upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}` // Передаем токен для ACL
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const result = await response.json();
        console.log("File uploaded to MinIO:", result);

        ws.send(JSON.stringify({
            messages: "",
            file_path: file.name, 
            file_name: file.name
        }));

    } catch (err) {
        console.error("Upload error:", err);
        alert("Ошибка при загрузке файла: " + err.message);
    } finally {
        event.target.value = ""; // Очищаем инпут
    }
};

window.downloadFile = async function (fileName) {
    if (!fileName) return;

    try {
        
        const url = `/chats/v1/files/${encodeURIComponent(fileName)}`;

        const res = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}` 
            }
        });

        // 3. Проверяем, нашел ли сервер файл
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Файл не найден");
        }

        // 4. Получаем данные файла (тот самый StreamingResponse из Python)
        const blob = await res.blob();
        
        // 5. Создаем "невидимую" ссылку для браузера, чтобы инициировать сохранение
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        
        a.download = fileName; 
        
        document.body.appendChild(a);
        a.click(); 
        
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);

    } catch (error) {
        console.error("Ошибка при получении файла:", error);
        alert("Не удалось загрузить файл: " + error.message);
    }
};

async function loadUsers() {
    const res = await fetch('/chats/v1/get-users', {
        headers: { Authorization: `Bearer ${token}` }
    });

    if (!res.ok) return;

    const users = await res.json();
    usersCache = users;

    const container = document.getElementById('users-list');
    if (!container) return;

    container.innerHTML = '';

    users.forEach(u => {
        const el = document.createElement('div');
        el.className = "p-2 border cursor-pointer hover:bg-gray-100";
        el.innerText = u.username;

        el.onclick = () => createDialog(u.id);

        container.appendChild(el);
    });
}

async function loadProfile() {
    const el = document.getElementById('my-name');
    if (!el) return;

    const userData = parseJwt(token);
    if (userData && userData.username) {
        el.innerText = userData.username;
    }

    const res = await fetch('/chats/v1/get-profile', {
        headers: { Authorization: `Bearer ${token}` }
    });

    if (res.ok) {
        const user = await res.json();
        // Если в объекте пользователя поле называется username
        if (user.username) el.innerText = user.username;
    }
}



async function loadChats() {
    const res = await fetch('/chats/v1/my-chats', {
        headers: { Authorization: `Bearer ${token}` }
    });
    if (!res.ok) return;

    const data = await res.json();
    let chats = Array.isArray(data) ? data : (data && data[0]?.j ? data[0].j : []);
    
    const container = document.getElementById('chats-list');
    if (!container) return;
    container.innerHTML = '';

    const myData = parseJwt(token);
    const myUsername = myData && myData.username ? myData.username.trim().toLowerCase() : null;
    // Определяем, является ли пользователь администратором/учителем (role_id === 1)
    const isAdmin = myData && (myData.role_id === 1 || myData.role === "Роҳбари синф");

    chats.forEach(chat => {
        const div = document.createElement('div');
        const active = String(chat.id) === String(roomId);
        div.className = `p-3 border-b cursor-pointer transition group relative ${active ? 'bg-indigo-100 border-l-4 border-indigo-600' : 'hover:bg-gray-50'}`;
        
        // --- ЛОГИКА ПОДМЕНЫ НАЗВАНИЯ ---
        let chatDisplayName = chat.name || 'Чат';

        if (chat.is_group) {
            // Если это группа и пользователь — админ, ставим спец. название
            if (isAdmin) {
                chatDisplayName = "Эълонҳо ва вазифаи хонагӣ";
            }
        } else if (chatDisplayName.includes(' / ')) {
            // Логика для личных диалогов (оставляем как было)
            const names = chatDisplayName.split(' / ');
            const otherName = names.find(n => n.trim().toLowerCase() !== myUsername);
            chatDisplayName = otherName ? otherName.trim() : names[0].trim();
        }
        // ------------------------------

        if (String(chat.id) === String(roomId)) {
            const titleEl = document.getElementById('current-chat-name');
            if (titleEl) {
                titleEl.innerText = chatDisplayName;
            }
            localStorage.setItem('chat_room_name', chatDisplayName);
        
            // Добавьте этот принудительный запуск проверки прав при загрузке активного чата:
            const participantsBtn = document.getElementById('participants-btn');
            if (participantsBtn) {
                const isGroupFlag = (chat.is_group === true || chat.is_group === 1 || chat.is_group === "true");
                if (isGroupFlag && isAdmin) { // Переменная isAdmin уже объявлена у вас в начале loadChats()
                    participantsBtn.classList.remove('hidden');
                } else {
                    participantsBtn.classList.add('hidden');
                }
            }
        }

        let lastMsgText = 'Нет сообщений';
        let lastMsgDate = '';
        if (chat.last_message) {
            lastMsgText = chat.last_message.message || (chat.last_message.file_path ? `📁 ${chat.last_message.file_path}` : lastMsgText);
            lastMsgDate = chat.last_message.day || '';
        }

        

                div.innerHTML = `
            <div class="flex justify-between items-start w-full mb-1">
                <span class="font-medium text-sm text-gray-900 truncate pr-2 flex-1">${chatDisplayName}</span>
                <div class="flex items-center space-x-2 flex-shrink-0">
                    <span class="text-[10px] text-gray-400 font-normal">${lastMsgDate}</span>
                    <button onclick="deleteChat('${chat.id}', event)" 
                            class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity px-1" 
                            title="Удалить чат">
                        🗑️
                    </button>
                </div>
            </div>
            <div class="text-[11px] text-gray-500 truncate w-full">${lastMsgText}</div>
        `;
        
        div.onclick = () => {
            localStorage.setItem('chat_room_id', chat.id);
            localStorage.setItem('chat_room_name', chatDisplayName);
            
            const isGroupFlag = (chat.is_group === true || chat.is_group === 1 || chat.is_group === "true");
            localStorage.setItem('is_group_chat', isGroupFlag ? 'true' : 'false'); 
            
            checkInputPermissions();
            window.location.reload();
        };

        container.appendChild(div);
    });
}

window.createDialog = async function (userId) {

    const myId = parseJwt(token)?.user_id;

    const res = await fetch('/chats/v1/create-dialog-chat', {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify([myId, userId]) 
    });

    if (!res.ok) return;

    const data = await res.json();

    localStorage.setItem('chat_room_id', data.chat_id);
    localStorage.setItem('chat_room_name', data.chat_name || "Диалог");

    window.location.reload();
};


window.createGroupUI = function () {
    const container = document.getElementById('group-users');
    if (!container) return;
    
    container.innerHTML = '';

    // Выводим всех, кроме самого себя (чтобы не отправлять объявление самому себе)
    const myData = parseJwt(token);
    const targets = usersCache.filter(u => String(u.id) !== String(myData?.user_id));

    if (targets.length === 0) {
        container.innerHTML = '<p class="text-xs text-gray-500">Нет доступных пользователей</p>';
        return;
    }

    targets.forEach(u => {
        const el = document.createElement('label');
        el.className = "flex items-center space-x-2 p-1 hover:bg-gray-50 rounded cursor-pointer";
        el.innerHTML = `
            <input type="checkbox" value="${u.id}" name="group-users" class="rounded text-indigo-600">
            <span class="text-sm text-gray-700">${u.username} <small class="text-gray-400">(${u.role || 'Волидайн'})</small></span>
        `;
        container.appendChild(el);
    });
};

function hideNoticeButtonForUsers() {
    const userData = parseJwt(token);
    const noticeBtn = document.querySelector('button.bg-green-500') || Array.from(document.querySelectorAll('button')).find(el => el.textContent.includes('Эълон'));

    if (noticeBtn) {
        if (userData?.role === "Волидайн" || userData?.role_id === 2) {
            noticeBtn.style.display = 'none'; 
        } else {
            noticeBtn.style.display = 'block'; 
        }
    }
}

window.submitCreateGroup = async function () {

    const users = Array.from(
        document.querySelectorAll('input[name="group-users"]:checked')
    ).map(x => x.value);

    if (users.length === 0) return;

    const res = await fetch('/chats/v1/create-notice-chat', {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_ids: users
        })
    });

    if (!res.ok) return;

    const data = await res.json();

    localStorage.setItem('chat_room_id', data.chat_id);

    window.location.reload();
};



window.removeParticipants = async function (groupId, userIds, isGroup = true) {
    if (!confirm("Вы уверены, что хотите удалить выбранных пользователей?")) return;

    try {
        const url = `/chats/v1/delete-group-participants?is_group=${isGroup}`;
        
        const res = await fetch(url, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                group_id: groupId,
                user_ids: userIds
            })
        });

        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || "Ошибка при удалении участников");

        alert("Участники удалены");
        window.location.reload(); 
    } catch (err) {
        console.error("Removal error:", err);
        alert(err.message);
    }
};
/**
 * ЛОГИКА ДЛЯ ВОЗВРАТА / ДОБАВЛЕНИЯ УЧАСТНИКОВ В ЧАТ
 */

// Открытие модального окна возврата участников
window.openReturnParticipantsModal = function() {
    const modal = document.getElementById('returnParticipantsModal');
    if (modal) modal.classList.remove('hidden');
    renderReturnUsersUI();
};

// Закрытие модального окна
window.closeReturnParticipantsModal = function() {
    const modal = document.getElementById('returnParticipantsModal');
    if (modal) modal.classList.add('hidden');
};

// Отрисовка списка пользователей внутри модального окна
window.renderReturnUsersUI = function() {
    const container = document.getElementById('return-users-list');
    if (!container) return;
    
    container.innerHTML = '';

    const myData = parseJwt(token);
    // Исключаем текущего пользователя из списка доступных для добавления
    const availableUsers = usersCache.filter(u => String(u.id) !== String(myData?.user_id));

    if (availableUsers.length === 0) {
        container.innerHTML = '<p class="text-xs text-gray-500 p-2 text-center">Нет доступных пользователей</p>';
        return;
    }

    availableUsers.forEach(u => {
        const el = document.createElement('label');
        el.className = "flex items-center space-x-2 p-1.5 hover:bg-gray-100 rounded-lg cursor-pointer transition-colors";
        el.innerHTML = `
            <input type="checkbox" value="${u.id}" name="return-chat-users" class="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4">
            <span class="text-sm text-gray-700 font-medium">${u.username} <small class="text-gray-400">(${u.role || 'Пользователь'})</small></span>
        `;
        container.appendChild(el);
    });
};

// Отправка запроса на бэкенд эндпоинт @router.put('/return-chat-participants')
window.submitReturnParticipants = async function() {
    const currentRoomId = localStorage.getItem('chat_room_id');
    if (!currentRoomId) {
        alert("Чат не выбран");
        return;
    }

    // Собираем массив UUID выбранных пользователей
    const selectedUserIds = Array.from(
        document.querySelectorAll('input[name="return-chat-users"]:checked')
    ).map(input => input.value);

    if (selectedUserIds.length === 0) {
        alert("Выберите хотя бы одного пользователя");
        return;
    }

    try {
        // Формируем payload в соответствии с ожидаемой структурой Pydantic-модели бэкенда
        const payloadData = {
            group_id: String(currentRoomId),
            user_ids: selectedUserIds // массив строк/UUID
        };

        const res = await fetch('/chats/v1/return-chat-participants', {
            method: 'PUT', // В бэкенде используется @router.put
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payloadData)
        });

        if (res.status === 403) {
            throw new Error("У вас нет прав администратора для добавления участников.");
        }

        if (!res.ok) {
            const errorResult = await res.json();
            throw new Error(errorResult.detail || "Ошибка при возвращении участников в чат");
        }

        const data = await res.json();
        console.log("Участники успешно обновлены:", data);
        
        alert("Изменения успешно сохранены");
        closeReturnParticipantsModal();
        window.location.reload(); // Перезагрузка для обновления состояния
        
    } catch (err) {
        console.error("Ошибка return_chat_participants:", err);
        alert(err.message);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    loadProfile();
    loadUsers();

    const savedRoomId = localStorage.getItem('chat_room_id');
    const savedRoomName = localStorage.getItem('chat_room_name');
    const isGroupStatus = localStorage.getItem('is_group_chat'); 
    
    const participantsBtn = document.getElementById('participants-btn');
    const titleEl = document.getElementById('current-chat-name');

    console.log(savedRoomId, "savedRoomId")

    if (savedRoomId && savedRoomId !== "undefined") {
        roomId = savedRoomId; 
        
        loadChatHistory(roomId);
        connectWebSocket(); 
    
        if (titleEl) {
            titleEl.innerText = savedRoomName || "Эълонҳо ва вазифаи хонагӣ";
        }
    
        // Обновленная проверка кнопки управления участниками
        // Находим проверку participantsBtn внутри DOMContentLoaded
if (participantsBtn) {
    const userData = parseJwt(token);
    const isGroup = isGroupStatus === 'true';
    
    // Выводим в консоль для отладки, чтобы точно видеть, какие данные приходят в токене
    console.log("Данные пользователя из JWT:", userData);
    console.log("Является ли чат группой:", isGroup);

    // Более надежная проверка прав: 
    // Роль НЕ должна быть обычной родительской/пользовательской ('User', 'Волидайн', role_id: 2)
    const isTeacherOrAdmin = 
        userData?.role_id === 1 || 
        userData?.role === "Роҳбари синф" || 
        (userData?.role !== 'User' && userData?.role !== 'Волидайн' && userData?.role_id !== 2);

    if (isGroup && isTeacherOrAdmin) {
        participantsBtn.classList.remove('hidden');
        console.log("Кнопка 'Участники' успешно отображена для администратора.");
    } else {
        participantsBtn.classList.add('hidden');
        console.log("Кнопка 'Участники' скрыта: не группа или недостаточно прав.", { isGroup, isTeacherOrAdmin });
    }
}
    } else {
        if (participantsBtn) participantsBtn.classList.add('hidden');
    }

    loadChats();
    hideNoticeButtonForUsers();

    document.getElementById("messageInput")?.addEventListener("keypress", e => {
        if (e.key === "Enter") {
            sendMessage(e); // Передаем событие e
        }
    });
});

window.logout = () => {
    localStorage.clear();
    window.location.href = "/chats/v1/sign-in";
};