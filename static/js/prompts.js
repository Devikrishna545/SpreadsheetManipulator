import { getCurrentPromptText, setCurrentPromptText } from './main.js';

const saveBtn = document.getElementById('savePromptBtn');
const promptLibraryBtn = document.getElementById('promptLibraryBtn');
const promptModal = document.getElementById('promptModal');
const promptList = document.getElementById('promptList');
const closePromptModalBtn = document.getElementById('closePromptModalBtn');

const PROMPT_API = '/prompts'; // Backend endpoint for prompt operations

// Predefined prompts (not deletable)
const PREDEFINED_PROMPTS = [
    "Remove row",
    "Remove column",
    "Add row",
    "Add column"
];

// Show modal using Bootstrap
function showPromptModal() {
    const modal = bootstrap.Modal.getOrCreateInstance(promptModal);
    modal.show();
}

// Hide modal
function hidePromptModal() {
    const modal = bootstrap.Modal.getOrCreateInstance(promptModal);
    modal.hide();
}

// Fetch prompts from backend
async function fetchPrompts() {
    const res = await fetch(PROMPT_API);
    if (!res.ok) return [];
    return await res.json();
}

// Save prompt to backend
async function savePrompt(prompt) {
    await fetch(PROMPT_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
    });
}

// Delete prompt from backend
async function deletePrompt(prompt) {
    await fetch(PROMPT_API, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
    });
}

// Render prompts in modal
function renderPromptList(prompts) {
    promptList.innerHTML = '';

    // Add predefined prompts first (no delete button)
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

    // Filter out predefined prompts from user prompts (avoid duplicates)
    const userPrompts = prompts.filter(
        p => !PREDEFINED_PROMPTS.includes(p)
    );

    if (!userPrompts.length && PREDEFINED_PROMPTS.length === 0) {
        promptList.innerHTML = '<li class="list-group-item text-muted">No saved prompts.</li>';
        return;
    }

    // Add user prompts (with delete button)
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

// Save prompt button handler
saveBtn.addEventListener('click', async () => {
    const prompt = getCurrentPromptText().trim();
    if (!prompt) return;
    await savePrompt(prompt);
    saveBtn.classList.add('btn-success');
    setTimeout(() => saveBtn.classList.remove('btn-success'), 600);
});

// Prompt library button handler
promptLibraryBtn.addEventListener('click', async () => {
    const prompts = await fetchPrompts();
    renderPromptList(prompts);
    showPromptModal();
});

// Close modal on close button
closePromptModalBtn.addEventListener('click', hidePromptModal);

// Hide modal when clicking outside
promptModal.addEventListener('click', (e) => {
    if (e.target === promptModal) hidePromptModal();
});

// Responsive: Modal is already responsive via Bootstrap

// Optional: Hide modal on ESC
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') hidePromptModal();
});
