import { getCurrentPromptText, setCurrentPromptText } from './main.js';

const saveBtn = document.getElementById('savePromptBtn');
const promptLibraryBtn = document.getElementById('promptLibraryBtn');
const promptModal = document.getElementById('promptModal');
const promptList = document.getElementById('promptList');
const closePromptModalBtn = document.getElementById('closePromptModalBtn');

const PROMPT_API = '/prompts'; // Backend endpoint for prompt operations

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

// Render prompts in modal
function renderPromptList(prompts) {
    promptList.innerHTML = '';
    if (!prompts.length) {
        promptList.innerHTML = '<li class="list-group-item text-muted">No saved prompts.</li>';
        return;
    }
    prompts.forEach((p, idx) => {
        const li = document.createElement('li');
        li.className = 'list-group-item list-group-item-action';
        li.style.cursor = 'pointer';
        li.textContent = p;
        li.onclick = () => {
            setCurrentPromptText(p);
            hidePromptModal();
        };
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
