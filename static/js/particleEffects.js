let particles = [];
let mouse = { x: undefined, y: undefined };
const particleInteractionDistance = 180; 
const particleMouseAttractDistance = 150;
let lineElement = null; 

let interParticleLineElements = [];
const MAX_INTER_PARTICLE_LINES = 20; 
const NUM_PARTICLES = 50; 
const PARTICLE_RESPAWN_INTERVAL = 500; // Faster respawn rate (ms)
let particleContainerRef = null;
let activeParticleCount = 0;

export function initParticleBackground() {
    particleContainerRef = document.getElementById('particleBackground');
    if (!particleContainerRef) return;
    particleContainerRef.innerHTML = ''; 
    particles = []; 
    interParticleLineElements = []; 
    activeParticleCount = 0;

    // Create only a few particles initially
    for (let i = 0; i < 5; i++) {
        createParticle();
    }

    // Schedule the rest of the particles to spawn with random delays
    const spawnRemainingParticles = () => {
        const particlesToSpawn = NUM_PARTICLES / 2 - 5; // Remaining particles from initial batch
        
        for (let i = 0; i < particlesToSpawn; i++) {
            const randomDelay = Math.random() * 5000; // Random delay up to 5 seconds
            setTimeout(() => {
                if (document.body.contains(particleContainerRef)) {
                    createParticle();
                }
            }, randomDelay);
        }
    };
    
    // Start spawning particles with random delays
    spawnRemainingParticles();

    // Create line elements
    if (!lineElement) {
        lineElement = document.createElement('div');
        lineElement.classList.add('particle-line');
        lineElement.style.display = 'none'; 
        document.body.appendChild(lineElement); 
    }

    for (let i = 0; i < MAX_INTER_PARTICLE_LINES; i++) {
        const ipl = document.createElement('div');
        ipl.classList.add('inter-particle-line');
        ipl.style.display = 'none';
        particleContainerRef.appendChild(ipl); 
        interParticleLineElements.push(ipl);
    }

    // Mouse tracking
    if (!window.hasParticleMouseMoveListener) {
        window.addEventListener('mousemove', (event) => {
            mouse.x = event.clientX;
            mouse.y = event.clientY;
        });
        window.hasParticleMouseMoveListener = true;
    }

    // Clear any previous intervals
    if (window.particleGenerationInterval) {
        clearInterval(window.particleGenerationInterval);
    }
    
    // Set up continuous particle generation with random timing
    if (window.particleGenerationInterval) {
        clearInterval(window.particleGenerationInterval);
    }
    
    window.particleGenerationInterval = setInterval(() => {
        // Filter out completed particles
        particles = particles.filter(p => {
            if (!p || !p.element) return false;
            
            // Check if element is still in DOM and animation is complete
            const inDOM = document.body.contains(p.element);
            if (!inDOM) return false;
            
            // Check animation state - if it's complete, we'll remove it
            const computedStyle = window.getComputedStyle(p.element);
            const opacity = parseFloat(computedStyle.opacity);
            
            // Keep if opacity > 0 and animation not at end
            if (opacity > 0 && p.timeCreated && (Date.now() - p.timeCreated < p.animationDuration * 1000 * 0.9)) {
                return true;
            }
            
            // Remove from DOM
            p.element.remove();
            activeParticleCount--;
            return false;
        });
        
        // Add new particles to maintain target count, but with random timing
        const particlesToAdd = NUM_PARTICLES - activeParticleCount;
        if (particlesToAdd > 0) {
            // Add one particle now
            createParticle();
            
            // Schedule any additional particles with random delays
            for (let i = 1; i < particlesToAdd; i++) {
                const randomDelay = Math.random() * 2000; // Random delay up to 2 seconds
                setTimeout(() => {
                    if (document.body.contains(particleContainerRef)) {
                        createParticle();
                    }
                }, randomDelay);
            }
        }
    }, PARTICLE_RESPAWN_INTERVAL);

    // Start animation loop if not already running
    if (!window.particleAnimationLoopId) {
        animateParticles();
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
    particleEl.style.animationDuration = `${animationDuration}s`;
    particleEl.style.animationDelay = '0s';
    
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
        
        const distToMouse = (mouse.x !== undefined && mouse.y !== undefined) ? 
                            Math.sqrt((pX - mouse.x)**2 + (pY - mouse.y)**2) : Infinity;

        if (distToMouse < particleMouseAttractDistance) {
            const scaleFactor = 1 + (1 - distToMouse / particleMouseAttractDistance) * 0.8; 
            p.element.style.transform = `scale(${scaleFactor})`;
            p.element.style.opacity = p.baseOpacity + (1 - distToMouse / particleMouseAttractDistance) * 0.5;
            
            if (distToMouse < minDistToMouse) {
                minDistToMouse = distToMouse;
                closestParticleToMouse = {x: pX, y: pY};
            }
        } else {
            p.element.style.transform = 'scale(1)';
            p.element.style.opacity = p.baseOpacity;
        }

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
                if (interParticleLinePoolIndex < MAX_INTER_PARTICLE_LINES) {
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

        if (distToMouse < particleMouseAttractDistance) {
            // Mouse interaction glow handled
        } else if (isInteractingWithOtherParticle) {
             p.element.style.opacity = Math.min(1, p.baseOpacity + 0.3); 
             p.element.style.boxShadow = `0 0 12px var(--main-accent), 0 0 20px var(--main-accent)`;
        } else {
             p.element.style.boxShadow = `0 0 8px var(--main-accent), 0 0 12px var(--main-accent)`; 
        }
    }
    
    if (closestParticleToMouse && mouse.x !== undefined && lineElement) {
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
    particles = [];
    interParticleLineElements = [];
}
