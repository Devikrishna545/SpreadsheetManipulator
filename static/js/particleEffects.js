let particles = [];
let mouse = { x: undefined, y: undefined };
const particleInteractionDistance = 180; 
const particleMouseAttractDistance = 150;
let lineElement = null; 

let interParticleLineElements = [];
// Base caps, effective values adapt using getMax* helpers
const MAX_INTER_PARTICLE_LINES_BASE = 20; 
const BASE_MAX_PARTICLES = 50; 
const PARTICLE_RESPAWN_INTERVAL = 500; // Faster respawn rate (ms)
let particleContainerRef = null;
let activeParticleCount = 0;
// Global toggle: disable all mouse interactions (requested behavior)
const ENABLE_MOUSE_INTERACTION = false;

// Motion/accessibility & environment-aware tuning
const REDUCED_MOTION = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
function getMaxParticles() {
    let max = BASE_MAX_PARTICLES;
    // Scale down on smaller viewports
    const area = (window.innerWidth || 0) * (window.innerHeight || 0);
    if (area && area < 800 * 600) max = Math.min(max, 24);
    // Scale down on low core count devices
    if (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4) max = Math.min(max, 32);
    // Respect reduced motion preference
    if (REDUCED_MOTION) max = Math.min(max, 18);
    return max;
}
function getMaxInterParticleLines() {
    return REDUCED_MOTION ? 8 : MAX_INTER_PARTICLE_LINES_BASE;
}

// NEW: ramp-up and respawn rate control
const RAMP_UP_WINDOW_MS = 25000; // spread initial entries across 25s
const RESPAWN_MIN_DELAY_MS = 600;
const RESPAWN_MAX_DELAY_MS = 3000;
let nextSpawnTime = 0;
let spawnTimeouts = [];

// Interval/RAF helpers
function maintenanceTick() {
    // Filter out completed particles
    particles = particles.filter(p => {
        if (!p || !p.element) return false;
        const inDOM = document.body.contains(p.element);
        if (!inDOM) return false;

        const computedStyle = window.getComputedStyle(p.element);
        const opacity = parseFloat(computedStyle.opacity);
        if (opacity > 0 && p.timeCreated && (Date.now() - p.timeCreated < p.animationDuration * 1000 * 0.9)) {
            return true;
        }
        // Remove from DOM and decrement count
        p.element.remove();
        activeParticleCount--;
        return false;
    });

    // Rate-limited respawn to avoid bursts
    if (activeParticleCount < getMaxParticles() && Date.now() >= nextSpawnTime) {
        if (document.body.contains(particleContainerRef)) {
            createParticle();
        }
        nextSpawnTime = Date.now() + RESPAWN_MIN_DELAY_MS + Math.random() * (RESPAWN_MAX_DELAY_MS - RESPAWN_MIN_DELAY_MS);
    }
}
function startMaintenanceInterval() {
    if (window.particleGenerationInterval) clearInterval(window.particleGenerationInterval);
    window.particleGenerationInterval = setInterval(maintenanceTick, PARTICLE_RESPAWN_INTERVAL);
}

export function initParticleBackground() {
    particleContainerRef = document.getElementById('particleBackground');
    if (!particleContainerRef) return;
    particleContainerRef.innerHTML = ''; 
    particles = []; 
    interParticleLineElements = []; 
    activeParticleCount = 0;

    // Clear any previous scheduled spawns
    spawnTimeouts.forEach(clearTimeout);
    spawnTimeouts = [];
    nextSpawnTime = Date.now() + 300 + Math.random() * 1200;

    // Create only a few particles initially
    for (let i = 0; i < 5; i++) {
        createParticle();
    }

    // Schedule the remaining particles to spawn with randomized delays (staggered ramp-up)
    // NOTE: replaces previous spawnRemainingParticles logic
    const remainingToSpawn = Math.max(0, getMaxParticles() - 5);
    for (let i = 0; i < remainingToSpawn; i++) {
        const delay = Math.random() * RAMP_UP_WINDOW_MS; // up to 25s
        const id = setTimeout(() => {
            if (!document.body.contains(particleContainerRef)) return;
            if (activeParticleCount < getMaxParticles()) {
                createParticle();
            }
        }, delay);
        spawnTimeouts.push(id);
    }

    // Create mouse line element only if mouse interaction is enabled
    if (ENABLE_MOUSE_INTERACTION) {
        if (!lineElement) {
            lineElement = document.createElement('div');
            lineElement.classList.add('particle-line');
            lineElement.style.display = 'none';
            document.body.appendChild(lineElement);
        }
    } else if (lineElement) {
        lineElement.style.display = 'none';
    }

    for (let i = 0; i < getMaxInterParticleLines(); i++) {
        const ipl = document.createElement('div');
        ipl.classList.add('inter-particle-line');
        ipl.style.display = 'none';
        particleContainerRef.appendChild(ipl); 
        interParticleLineElements.push(ipl);
    }

    // Mouse tracking (disabled when not needed)
    if (ENABLE_MOUSE_INTERACTION) {
        if (!window.hasParticleMouseMoveListener) {
            window.addEventListener('mousemove', (event) => {
                mouse.x = event.clientX;
                mouse.y = event.clientY;
            });
            window.hasParticleMouseMoveListener = true;
        }
    }

    // Clear previous and start maintenance interval
    startMaintenanceInterval();

    // Start animation loop if not already running
    if (!window.particleAnimationLoopId) {
        animateParticles();
    }

    // Pause/resume on tab visibility to save CPU
    document.removeEventListener('visibilitychange', onVisibilityChange, true);
    document.addEventListener('visibilitychange', onVisibilityChange, true);
}

function onVisibilityChange() {
    if (document.hidden) {
        if (window.particleAnimationLoopId) {
            cancelAnimationFrame(window.particleAnimationLoopId);
            window.particleAnimationLoopId = null;
        }
        if (window.particleGenerationInterval) {
            clearInterval(window.particleGenerationInterval);
            window.particleGenerationInterval = null;
        }
    } else {
        if (!window.particleAnimationLoopId) animateParticles();
        if (!window.particleGenerationInterval) startMaintenanceInterval();
    }
}

function createParticle() {
    if (!particleContainerRef) return;
    
    const particleEl = document.createElement('div');
    particleEl.classList.add('particle');
    
    const size = Math.random() * 10 + 5; 
    particleEl.style.width = `${size}px`;
    particleEl.style.height = `${size}px`;
    
    let startX, startY, endX, endY;
    const screenWidth = window.innerWidth;
    const screenHeight = window.innerHeight;
    const offScreenBuffer = 100;
    const travelDistanceMultiplier = 1.5; // Increased slightly for better coverage

    // Choose a random edge to start from
    const startEdge = Math.floor(Math.random() * 4); // 0: top, 1: right, 2: bottom, 3: left

    switch (startEdge) {
        case 0: // Top edge
            startX = Math.random() * screenWidth;
            startY = -offScreenBuffer - size;
            break;
        case 1: // Right edge
            startX = screenWidth + offScreenBuffer + size;
            startY = Math.random() * screenHeight;
            break;
        case 2: // Bottom edge
            startX = Math.random() * screenWidth;
            startY = screenHeight + offScreenBuffer + size;
            break;
        case 3: // Left edge
            startX = -offScreenBuffer - size;
            startY = Math.random() * screenHeight;
            break;
    }

    // Calculate end position to ensure the particle crosses the screen
    // Instead of a random angle, target a point on the opposite side of the screen
    let targetX, targetY;
    
    // Target a point on the opposite side plus random offset to create varied paths
    switch (startEdge) {
        case 0: // Started from top, end at bottom
            targetX = Math.random() * screenWidth;
            targetY = screenHeight + offScreenBuffer + size;
            break;
        case 1: // Started from right, end at left
            targetX = -offScreenBuffer - size;
            targetY = Math.random() * screenHeight;
            break;
        case 2: // Started from bottom, end at top
            targetX = Math.random() * screenWidth;
            targetY = -offScreenBuffer - size;
            break;
        case 3: // Started from left, end at right
            targetX = screenWidth + offScreenBuffer + size;
            targetY = Math.random() * screenHeight;
            break;
    }
    
    // Add some randomness to the target to create more varied paths
    targetX += (Math.random() - 0.5) * screenWidth * 0.3;
    targetY += (Math.random() - 0.5) * screenHeight * 0.3;
    
    // Calculate the direct line between start and target
    const dx = targetX - startX;
    const dy = targetY - startY;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    // Scale this distance to ensure particles cross the screen
    const scaleFactor = (Math.max(screenWidth, screenHeight) * travelDistanceMultiplier) / distance;
    
    // Calculate end point based on scaled direction
    endX = startX + dx * scaleFactor;
    endY = startY + dy * scaleFactor;
    
    particleEl.style.setProperty('--start-x', `${startX}px`);
    particleEl.style.setProperty('--start-y', `${startY}px`);
    particleEl.style.setProperty('--end-x', `${endX}px`);
    particleEl.style.setProperty('--end-y', `${endY}px`);
    particleEl.style.setProperty('--scale', Math.random() * 0.6 + 0.4); 
    particleEl.style.setProperty('--opacity-base', Math.random() * 0.4 + 0.2);

    // Set animation duration (significantly slower for better visibility)
    const animationDuration = 45 + Math.random() * 25; // Increased from 25+15 to 45+25 seconds
    // particleEl.style.animationDuration = `${animationDuration}s`;
    // particleEl.style.animationDelay = '0s';
    // NEW: per-particle durations/delay for float + twinkle
    particleEl.style.setProperty('--float-duration', `${animationDuration}s`);
    particleEl.style.setProperty('--twinkle-duration', `${(1.6 + Math.random() * 2.2).toFixed(2)}s`);
    particleEl.style.setProperty('--twinkle-delay', `${(Math.random() * 2).toFixed(2)}s`);

    // Initial opacity (explicitly start transparent)
    particleEl.style.opacity = '0';

    // Store particle data with creation time for lifecycle tracking
    const particleData = {
        element: particleEl,
        size: size,
        baseOpacity: parseFloat(particleEl.style.getPropertyValue('--opacity-base')),
        timeCreated: Date.now(),
        animationDuration: animationDuration
    };
    particles.push(particleData);
    particleContainerRef.appendChild(particleEl);
    activeParticleCount++;
}

function animateParticles() {
    updateParticlesInteraction();
    window.particleAnimationLoopId = requestAnimationFrame(animateParticles);
}

function updateParticlesInteraction() {
    let closestParticleToMouse = null;
    let minDistToMouse = particleMouseAttractDistance;
    let interParticleLinePoolIndex = 0;

    // Helper: line-of-sight occlusion between particle (x1,y1) and mouse (x2,y2)
    // Returns true if any non-particle content is between them.
    function isOccluded(x1, y1, x2, y2) {
        // If mouse coords are undefined, treat as occluded to avoid interaction
        if (x2 === undefined || y2 === undefined) return true;
        const samples = 4; // sample a few points along the line
        for (let i = 1; i <= samples; i++) {
            const t = i / (samples + 1); // avoid sampling exactly at the ends
            const sx = Math.round(x1 + (x2 - x1) * t);
            const sy = Math.round(y1 + (y2 - y1) * t);
            const el = document.elementFromPoint(sx, sy);
            if (!el) continue; // unlikely
            // Allow elements that are part of the particle system
            if (
                el.id === 'particleBackground' ||
                el.classList?.contains('particle') ||
                el.classList?.contains('particle-line') ||
                el.classList?.contains('inter-particle-line') ||
                el.closest?.('#particleBackground')
            ) {
                continue; // not occluding
            }
            // Any other element means occluded
            return true;
        }
        return false;
    }

    // Check if spreadsheet is visible - if so, disable mouse interactions
    const spreadsheetContainer = document.getElementById('spreadsheetContainer');
    const isSpreadsheetVisible = spreadsheetContainer && spreadsheetContainer.style.display !== 'none';

    // Hide all inter-particle lines
    for (const line of interParticleLineElements) {
        line.style.display = 'none';
    }
    
    // Hide mouse line by default
    if (lineElement) {
        lineElement.style.display = 'none';
    }

    for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        if (!p || !p.element || !document.body.contains(p.element)) continue;
        
        const rect = p.element.getBoundingClientRect(); 
        const pX = rect.left + p.size / 2;
        const pY = rect.top + p.size / 2;

        // Skip particles that are off-screen or invisible
        if (rect.bottom < 0 || rect.top > window.innerHeight || 
            rect.right < 0 || rect.left > window.innerWidth || 
            p.element.style.opacity === '0') {
            p.element.style.transform = 'scale(1)';
            p.element.style.opacity = p.baseOpacity;
            continue; 
        }
        
        // Skip mouse interactions if spreadsheet is visible
    // Mouse interaction disabled: always keep base transform/opacity
    p.element.style.transform = 'scale(1)';
    p.element.style.opacity = p.baseOpacity;

        let isInteractingWithOtherParticle = false;
        for (let j = i + 1; j < particles.length; j++) { 
            const otherP = particles[j];
            if (!otherP || !otherP.element || !document.body.contains(otherP.element)) continue;
            
            const otherRect = otherP.element.getBoundingClientRect();
            const otherPX = otherRect.left + otherP.size / 2;
            const otherPY = otherRect.top + otherP.size / 2;

            if (otherRect.bottom < 0 || otherRect.top > window.innerHeight || otherRect.right < 0 || otherRect.left > window.innerWidth) {
                continue;
            }

            const distBetweenParticles = Math.sqrt((pX - otherPX)**2 + (pY - otherPY)**2);

            if (distBetweenParticles < particleInteractionDistance && distBetweenParticles > 0) {
                isInteractingWithOtherParticle = true;
                // Use the actual pool size instead of an undefined constant
                if (interParticleLinePoolIndex < interParticleLineElements.length) {
                    const line = interParticleLineElements[interParticleLinePoolIndex];
                    const angle = Math.atan2(otherPY - pY, otherPX - pX) * 180 / Math.PI;
                    const length = distBetweenParticles;

                    line.style.width = `${length}px`;
                    line.style.left = `${pX}px`; 
                    line.style.top = `${pY}px`;  
                    line.style.transform = `rotate(${angle}deg)`;
                    line.style.opacity = `${0.4 * (1 - length / particleInteractionDistance)}`; 
                    line.style.display = 'block';
                    interParticleLinePoolIndex++;
                }
            }
        }

    if (isInteractingWithOtherParticle) {
             p.element.style.opacity = Math.min(1, p.baseOpacity + 0.3); 
             p.element.style.boxShadow = `0 0 12px var(--main-accent), 0 0 20px var(--main-accent)`;
        } else {
             p.element.style.boxShadow = `0 0 8px var(--main-accent), 0 0 12px var(--main-accent)`; 
        }
    }
    
    // Mouse line disabled entirely
    if (ENABLE_MOUSE_INTERACTION && !isSpreadsheetVisible && closestParticleToMouse && mouse.x !== undefined && lineElement && !isOccluded(closestParticleToMouse.x, closestParticleToMouse.y, mouse.x, mouse.y)) {
        lineElement.style.display = 'block';
        const angle = Math.atan2(mouse.y - closestParticleToMouse.y, mouse.x - closestParticleToMouse.x) * 180 / Math.PI;
        const length = Math.sqrt((mouse.x - closestParticleToMouse.x)**2 + (mouse.y - closestParticleToMouse.y)**2);
        
        lineElement.style.width = `${length}px`;
        lineElement.style.left = `${closestParticleToMouse.x}px`;
        lineElement.style.top = `${closestParticleToMouse.y}px`;
        lineElement.style.transform = `rotate(${angle}deg)`;
        lineElement.style.opacity = `${0.7 * (1 - minDistToMouse/particleMouseAttractDistance)}`;
    }
}

// Clean up function to be called when the page is unloaded
export function cleanUpParticles() {
    if (window.particleGenerationInterval) {
        clearInterval(window.particleGenerationInterval);
    }
    if (window.particleAnimationLoopId) {
        cancelAnimationFrame(window.particleAnimationLoopId);
    }
    if (lineElement && document.body.contains(lineElement)) {
        lineElement.remove();
    }

    // NEW: clear any scheduled ramp-up spawns
    spawnTimeouts.forEach(clearTimeout);
    spawnTimeouts = [];
    nextSpawnTime = 0;

    particles = [];
    interParticleLineElements = [];
}
