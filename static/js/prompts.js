import { getCurrentPromptText, setCurrentPromptText } from './main.js';

const saveBtn = document.getElementById('savePromptBtn');
const promptLibraryBtn = document.getElementById('promptLibraryBtn');
const promptModal = document.getElementById('promptModal');
const promptList = document.getElementById('promptList');
const closePromptModalBtn = document.getElementById('closePromptModalBtn');

const PROMPT_API = '/prompts';

const PREDEFINED_PROMPTS = [
    "Remove row",
    "Remove column",
    "Add row",
    "Add column"
];

function showPromptModal() {
    const modal = bootstrap.Modal.getOrCreateInstance(promptModal);
    modal.show();
}

function hidePromptModal() {
    const modal = bootstrap.Modal.getOrCreateInstance(promptModal);
    modal.hide();
}

async function fetchPrompts() {
    const res = await fetch(PROMPT_API);
    if (!res.ok) return [];
    return await res.json();
}

async function savePrompt(prompt) {
    await fetch(PROMPT_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
    });
}

async function deletePrompt(prompt) {
    await fetch(PROMPT_API, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
    });
}

function renderPromptList(prompts) {
    promptList.innerHTML = '';

    PREDEFINED_PROMPTS.forEach((p) => {
        const li = document.createElement('li');
        li.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        li.style.cursor = 'pointer';

        const textSpan = document.createElement('span');
        textSpan.textContent = p;
        textSpan.style.flex = '1';
        textSpan.onclick = () => {
            setCurrentPromptText(p);
            hidePromptModal();
        };

        li.appendChild(textSpan);
        promptList.appendChild(li);
    });

    const userPrompts = prompts.filter(
        p => !PREDEFINED_PROMPTS.includes(p)
    );

    if (!userPrompts.length && PREDEFINED_PROMPTS.length === 0) {
        promptList.innerHTML = '<li class="list-group-item text-muted">No saved prompts.</li>';
        return;
    }

    userPrompts.forEach((p, idx) => {
        const li = document.createElement('li');
        li.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        li.style.cursor = 'pointer';

        const textSpan = document.createElement('span');
        textSpan.textContent = p;
        textSpan.style.flex = '1';
        textSpan.onclick = () => {
            setCurrentPromptText(p);
            hidePromptModal();
        };

        const delBtn = document.createElement('button');
        delBtn.className = 'btn btn-outline-danger btn-futuristic btn-sm icon-btn ms-2';
        delBtn.innerHTML = '<i class="fas fa-trash"></i>';
        delBtn.title = 'Delete Prompt';
        delBtn.style.padding = '4px 8px';
        delBtn.style.display = 'flex';
        delBtn.style.alignItems = 'center';
        delBtn.onclick = async (e) => {
            e.stopPropagation();
            await deletePrompt(p);
            const updatedPrompts = await fetchPrompts();
            renderPromptList(updatedPrompts);
        };

        li.appendChild(textSpan);
        li.appendChild(delBtn);
        promptList.appendChild(li);
    });
}

saveBtn.addEventListener('click', async () => {
    const prompt = getCurrentPromptText().trim();
    if (!prompt) return;
    await savePrompt(prompt);
    saveBtn.classList.add('btn-success');
    setTimeout(() => saveBtn.classList.remove('btn-success'), 600);
});

promptLibraryBtn.addEventListener('click', async () => {
    const prompts = await fetchPrompts();
    renderPromptList(prompts);
    showPromptModal();
});

closePromptModalBtn.addEventListener('click', hidePromptModal);

promptModal.addEventListener('click', (e) => {
    if (e.target === promptModal) hidePromptModal();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') hidePromptModal();
});
