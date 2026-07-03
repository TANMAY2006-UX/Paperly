document.addEventListener('DOMContentLoaded', () => {

    // --- 1. THEME SYSTEM & FONT SIZES (Internals kept) ---
    const root = document.documentElement;

    // Handle Theme Switching
    const themeBtns = document.querySelectorAll('.theme-btn');
    const applyTheme = (themeClass) => {
        root.className = themeClass; // Reset classes and set theme
        localStorage.setItem('reader_theme', themeClass);
        themeBtns.forEach(b => b.classList.toggle('active', b.dataset.theme === themeClass));
    };

    themeBtns.forEach(btn => {
        btn.addEventListener('click', () => applyTheme(btn.dataset.theme));
    });

    // Handle Font Size
    const fontBtns = document.querySelectorAll('.font-btn');
    const applyFontSize = (size) => {
        root.style.setProperty('--reading-font-size', size);
        localStorage.setItem('reader_font_size', size);
        fontBtns.forEach(b => b.classList.toggle('active', b.dataset.size === size));
    };

    fontBtns.forEach(btn => {
        btn.addEventListener('click', () => applyFontSize(btn.dataset.size));
    });

    // Initialize Preferences from localStorage
    const savedTheme = localStorage.getItem('reader_theme') || 'theme-paper';
    applyTheme(savedTheme);
    const savedFontSize = localStorage.getItem('reader_font_size') || '18px';
    applyFontSize(savedFontSize);


    // --- 2. TABLE OF CONTENTS (COLLAPSIBLE & MOBILE) ---
    const tocSidebar = document.getElementById('toc-sidebar');
    const tocToggle = document.getElementById('toc-toggle');
    const tocStateBtns = document.querySelectorAll('.toc-state-btn');
    const mobileTocBtn = document.getElementById('mobile-toc-trigger');

    const setTocState = (state) => {
        if (state === 'collapsed') {
            tocSidebar.classList.add('collapsed');
        } else {
            tocSidebar.classList.remove('collapsed');
            // Open TOC -> Visuals closes
            if (typeof window.closeAllSurfaces === 'function') {
                window.closeAllSurfaces();
            }
        }
        localStorage.setItem('reader_toc_collapsed', state);
        tocStateBtns.forEach(b => b.classList.toggle('active', b.dataset.state === state));
    };

    tocToggle.addEventListener('click', () => {
        const newState = tocSidebar.classList.contains('collapsed') ? 'expanded' : 'collapsed';
        setTocState(newState);
    });

    tocStateBtns.forEach(btn => {
        btn.addEventListener('click', () => setTocState(btn.dataset.state));
    });

    // TOC Resizing
    const tocResizer = document.getElementById('toc-resizer');
    let isResizing = false;
    
    if (tocResizer) {
        tocResizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            document.body.classList.add('resizing');
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            // Only resize if not collapsed
            if (!tocSidebar.classList.contains('collapsed')) {
                const newWidth = Math.max(240, Math.min(e.clientX, 480));
                root.style.setProperty('--toc-width', `${newWidth}px`);
            }
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                document.body.classList.remove('resizing');
                localStorage.setItem('reader_toc_width', root.style.getPropertyValue('--toc-width'));
            }
        });

        const savedTocWidth = localStorage.getItem('reader_toc_width');
        if (savedTocWidth) {
            root.style.setProperty('--toc-width', savedTocWidth);
        }
    }

    // Initialize TOC state
    const savedToc = localStorage.getItem('reader_toc_collapsed') || 'expanded';
    setTocState(savedToc);

    // Mobile Drawer
    mobileTocBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        tocSidebar.classList.toggle('mobile-open');
    });

    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 1024 && tocSidebar.classList.contains('mobile-open')) {
            if (!tocSidebar.contains(e.target) && !mobileTocBtn.contains(e.target)) {
                tocSidebar.classList.remove('mobile-open');
            }
        }
    });

    // --- 2.5 TOC HIERARCHY BEHAVIOR ---
    const expandSection = (parentId) => {
        const parentBtn = document.querySelector(`.toc-link[data-target="${parentId}"] .toc-expand-btn`);
        if (parentBtn) {
            parentBtn.classList.add('expanded');
        }
        // Show immediate children
        const children = document.querySelectorAll(`.toc-item[data-parent="${parentId}"]`);
        children.forEach(child => child.classList.remove('toc-hidden'));
    };

    const collapseSection = (parentId) => {
        const parentBtn = document.querySelector(`.toc-link[data-target="${parentId}"] .toc-expand-btn`);
        if (parentBtn) {
            parentBtn.classList.remove('expanded');
        }
        // Hide and recursively collapse children
        const children = document.querySelectorAll(`.toc-item[data-parent="${parentId}"]`);
        children.forEach(child => {
            child.classList.add('toc-hidden');
            const childId = child.querySelector('.toc-link').dataset.target;
            collapseSection(childId); // Recursive collapse
        });
    };

    // Click handler for expand buttons
    document.querySelectorAll('.toc-expand-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const isExpanded = btn.classList.contains('expanded');
            const parentId = btn.closest('.toc-link').dataset.target;

            if (isExpanded) {
                collapseSection(parentId);
            } else {
                expandSection(parentId);
            }
        });
    });

    // Auto-expand parents upward
    const expandParentsUpward = (targetId) => {
        const targetItem = document.querySelector(`.toc-link[data-target="${targetId}"]`);
        if (!targetItem) return;

        const parentId = targetItem.closest('.toc-item').dataset.parent;
        if (parentId) {
            expandSection(parentId);
            expandParentsUpward(parentId); // Recursive up
        }
    };

    // Auto-expand on initial load if there's a hash
    if (window.location.hash) {
        const hashTarget = window.location.hash.substring(1);
        expandParentsUpward(hashTarget);
    }

    // --- 3. READING TRAIL & INTERSECTION OBSERVER ---
    const sections = document.querySelectorAll('.paper-section');
    const tocLinks = document.querySelectorAll('.toc-link');
    const paperSlug = window.PAPER_SLUG || 'default';

    // Load visited sections trail
    let visitedTrail = [];
    try {
        visitedTrail = JSON.parse(localStorage.getItem(`reader_trail_${paperSlug}`)) || [];
    } catch (e) { }

    const markVisited = (id) => {
        if (!visitedTrail.includes(id)) {
            visitedTrail.push(id);
            localStorage.setItem(`reader_trail_${paperSlug}`, JSON.stringify(visitedTrail));
        }
        const link = document.querySelector(`.toc-link[data-target="${id}"]`);
        if (link) link.classList.add('visited');
    };

    // Apply trail on load
    visitedTrail.forEach(id => {
        const link = document.querySelector(`.toc-link[data-target="${id}"]`);
        if (link) link.classList.add('visited');
    });

    let currentActiveId = null;

    // --- PHASE 2D: READING PROGRESS ---
    let deepestSectionIndex = -1;
    const totalWords = parseInt(document.body.getAttribute('data-total-words')) || 0;
    const progressWhisper = document.getElementById('progress-whisper');
    let lastRemainingTime = null;
    let whisperTimeout = null;

    const updateReadingProgress = () => {
        let wordsRead = 0;
        for (let i = 0; i <= deepestSectionIndex; i++) {
            wordsRead += parseInt(sections[i].getAttribute('data-words')) || 0;
        }
        
        let remainingWords = totalWords - wordsRead;
        if (remainingWords < 0) remainingWords = 0;
        
        const remainingTime = Math.ceil(remainingWords / 200);
        
        if (progressWhisper && remainingTime !== lastRemainingTime) {
            if (lastRemainingTime !== null) {
                // Only show whisper if it's not the initial load
                const minText = remainingTime === 1 ? 'min' : 'mins';
                progressWhisper.textContent = `${remainingTime} ${minText} remaining`;
                progressWhisper.classList.add('visible');
                
                clearTimeout(whisperTimeout);
                whisperTimeout = setTimeout(() => {
                    progressWhisper.classList.remove('visible');
                }, 1500);
            }
            lastRemainingTime = remainingTime;
        }
    };

    const observerOptions = {
        root: null,
        rootMargin: '-10% 0px -70% 0px',
        threshold: 0
    };

    const sectionObserver = new IntersectionObserver((entries) => {
        let visibleSection = null;
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                visibleSection = entry.target;
            }
        });

        if (visibleSection) {
            const id = visibleSection.getAttribute('id');
            const newIndex = Array.from(sections).indexOf(visibleSection);
            
            if (newIndex > deepestSectionIndex) {
                deepestSectionIndex = newIndex;
                updateReadingProgress();
            }

            if (currentActiveId !== id) {
                // Remove active from all
                tocLinks.forEach(link => link.classList.remove('active'));

                // Add active to current
                const activeLink = document.querySelector(`.toc-link[data-target="${id}"]`);
                if (activeLink) {
                    activeLink.classList.add('active');
                    // Scroll TOC to keep active item in view if needed
                    const tocNav = document.querySelector('.toc-nav');
                    if (tocNav) {
                        const targetTop = activeLink.offsetTop - (tocNav.clientHeight / 2);
                        tocNav.scrollTo({
                            top: targetTop,
                            behavior: 'smooth'
                        });
                    }
                }

                markVisited(id);
                currentActiveId = id;
            }
        }
    }, observerOptions);

    sections.forEach(sec => sectionObserver.observe(sec));

    // Click TOC to handle smooth scroll and close mobile drawer
    tocLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            // Only handle left clicks
            if (e.button !== 0) return;
            
            const targetId = link.getAttribute('data-target');
            if (targetId) {
                const targetEl = document.getElementById(targetId);
                if (targetEl) {
                    targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }

            if (window.innerWidth <= 1024) {
                tocSidebar.classList.remove('mobile-open');
            }
        });
    });





    // --- 5. FIGURE LIGHTBOX ---
    const lightbox = document.getElementById('lightbox-overlay');
    const lightboxImg = document.getElementById('lightbox-img');
    const lightboxCaption = document.getElementById('lightbox-caption');
    const lightboxCounter = document.getElementById('lightbox-counter');

    // Collect all figures for navigation
    const figures = Array.from(document.querySelectorAll('.paper-figure'));
    let currentFigIndex = 0;

    const openLightbox = (index) => {
        if (index < 0 || index >= figures.length) return;
        currentFigIndex = index;
        const fig = figures[index];
        const img = fig.querySelector('img');
        const caption = fig.querySelector('figcaption').textContent.replace('⤢', '').trim();

        lightboxImg.src = img.src;
        lightboxCaption.textContent = caption;
        lightboxCounter.textContent = `Figure ${index + 1} of ${figures.length}`;

        lightbox.classList.remove('hidden');
    };

    const closeLightbox = () => {
        lightbox.classList.add('hidden');
        lightboxImg.src = '';
    };

    figures.forEach((fig, idx) => {
        const expandBtn = fig.querySelector('.expand-fig-btn');
        const img = fig.querySelector('img');

        const trigger = () => openLightbox(idx);
        if (expandBtn) expandBtn.addEventListener('click', trigger);
        if (img) img.addEventListener('click', trigger);
    });

    document.querySelector('.lightbox-close').addEventListener('click', closeLightbox);
    document.querySelector('.lightbox-prev').addEventListener('click', (e) => { e.stopPropagation(); openLightbox(currentFigIndex - 1); });
    document.querySelector('.lightbox-next').addEventListener('click', (e) => { e.stopPropagation(); openLightbox(currentFigIndex + 1); });

    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox || e.target.classList.contains('lightbox-content')) {
            closeLightbox();
        }
    });



    // --- 7. KEYBOARD SHORTCUTS ---
    const showToast = (msg) => {
        const toast = document.getElementById('toast');
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
    };

    document.addEventListener('keydown', (e) => {
        // Don't trigger shortcuts if user is typing in an input (future proofing)
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        // Esc: close things
        if (e.key === 'Escape') {
            closeLightbox();
            prefsPanel.classList.add('hidden');
            if (window.innerWidth <= 1024) tocSidebar.classList.remove('mobile-open');
        }

        // Lightbox open: Left/Right arrows and [/]
        if (!lightbox.classList.contains('hidden')) {
            if (e.key === 'ArrowLeft' || e.key === '[') openLightbox(currentFigIndex - 1);
            if (e.key === 'ArrowRight' || e.key === ']') openLightbox(currentFigIndex + 1);
            return;
        }

        // B for Bookmark (Stub)
        if (e.key.toLowerCase() === 'b') {
            showToast("Bookmark saved.");
        }
    });

    // --- 8. CITATION HIGHLIGHTING ---
    document.querySelectorAll('.cite-link').forEach(link => {
        link.addEventListener('click', (e) => {
            const targetId = link.getAttribute('href').substring(1);
            const targetEl = document.getElementById(targetId);
            if (targetEl) {
                // Add highlight
                targetEl.classList.add('highlighted');
                setTimeout(() => {
                    targetEl.classList.remove('highlighted');
                }, 1500);
            }
        });
    });

    // --- 9. PHASE 2C: READING DOCK & VISUALS DRAWER ---
    
    const readingDockMenu = document.getElementById('reading-dock-menu');
    const readingDockTrigger = document.getElementById('reading-dock-trigger');
    const visualsDrawer = document.getElementById('visuals-drawer');
    const visualsTriggerBtn = document.getElementById('visuals-trigger');
    const visualsIconOpen = visualsTriggerBtn.querySelector('.icon-open');
    const visualsIconClosed = visualsTriggerBtn.querySelector('.icon-closed');
    const lightboxOverlay = document.getElementById('lightbox-overlay');

    // Surface Management (Exclusivity)
    window.closeAllSurfaces = function() {
        readingDockMenu.classList.add('hidden');
        visualsDrawer.classList.remove('open');
        visualsDrawer.classList.add('hidden');
        visualsIconClosed.classList.remove('hidden');
        visualsIconOpen.classList.add('hidden');
    };
    const closeAllSurfaces = window.closeAllSurfaces;

    // Prevent Lightbox from having other surfaces open
    const lightboxObserver = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                if (!lightboxOverlay.classList.contains('hidden')) {
                    closeAllSurfaces();
                }
            }
        });
    });
    if (lightboxOverlay) {
        lightboxObserver.observe(lightboxOverlay, { attributes: true });
    }

    // Toggle Reading Dock
    readingDockTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isHidden = readingDockMenu.classList.contains('hidden');
        closeAllSurfaces();
        if (isHidden) {
            readingDockMenu.classList.remove('hidden');
        }
    });

    // Toggle Visuals Drawer
    visualsTriggerBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isHidden = visualsDrawer.classList.contains('hidden');
        closeAllSurfaces();
        if (isHidden) {
            visualsDrawer.classList.remove('hidden');
            visualsDrawer.classList.add('open');
            visualsIconClosed.classList.add('hidden');
            visualsIconOpen.classList.remove('hidden');
        }
    });

    // Close surfaces on outside click
    document.addEventListener('click', (e) => {
        if (!readingDockMenu.contains(e.target) && e.target !== readingDockTrigger) {
            readingDockMenu.classList.add('hidden');
        }
        if (!visualsDrawer.contains(e.target) && !visualsTriggerBtn.contains(e.target)) {
            visualsDrawer.classList.remove('open');
            visualsDrawer.classList.add('hidden');
            visualsIconClosed.classList.remove('hidden');
            visualsIconOpen.classList.add('hidden');
        }
    });

    // Prevent drawer clicks from closing itself
    visualsDrawer.addEventListener('click', (e) => e.stopPropagation());
    readingDockMenu.addEventListener('click', (e) => e.stopPropagation());

    // Font Controls
    const FONT_MIN = 14;
    const FONT_MAX = 24;
    const FONT_DEFAULT = 18;
    
    function updateFontSize(newSize) {
        if (newSize >= FONT_MIN && newSize <= FONT_MAX) {
            applyFontSize(`${newSize}px`);
        }
    }

    document.getElementById('font-decrease').addEventListener('click', () => {
        const currentSize = parseInt(getComputedStyle(root).getPropertyValue('--reading-font-size')) || FONT_DEFAULT;
        updateFontSize(currentSize - 2);
    });

    document.getElementById('font-increase').addEventListener('click', () => {
        const currentSize = parseInt(getComputedStyle(root).getPropertyValue('--reading-font-size')) || FONT_DEFAULT;
        updateFontSize(currentSize + 2);
    });

    document.getElementById('font-reset').addEventListener('click', () => {
        updateFontSize(FONT_DEFAULT);
    });

    // Reading Modes (Focus & Scroll)
    const modeBtns = document.querySelectorAll('.mode-btn');
    const setReadingMode = (mode) => {
        localStorage.setItem('reader_mode', mode);
        modeBtns.forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
        if (mode === 'focus') {
            document.body.classList.add('focus-mode');
            document.documentElement.classList.add('focus-fullscreen');
            setTocState('collapsed');
        } else {
            document.body.classList.remove('focus-mode');
            document.documentElement.classList.remove('focus-fullscreen');
        }
    };

    const requestFocusFullscreen = () => {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(err => {
                console.log(`Error attempting to enable fullscreen: ${err.message}`);
                // Still apply styling if fullscreen fails
                setReadingMode('focus');
            });
        }
    };

    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.mode === 'focus') {
                requestFocusFullscreen();
            } else {
                if (document.fullscreenElement) {
                    document.exitFullscreen().catch(err => console.error(err));
                } else {
                    setReadingMode('scroll');
                }
            }
        });
    });

    // Initialize Reading Mode from localStorage
    // Always start with scroll to avoid permission issues and intermediate states
    localStorage.setItem('reader_mode', 'scroll');
    setReadingMode('scroll');

    // Fullscreen API & Keyboard logic
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        // F key for Focus Mode true fullscreen
        if (e.key.toLowerCase() === 'f') {
            e.preventDefault();
            if (!document.fullscreenElement) {
                requestFocusFullscreen();
            } else {
                document.exitFullscreen().catch(err => console.error(err));
            }
        }
    });

    document.addEventListener('fullscreenchange', () => {
        if (document.fullscreenElement) {
            setReadingMode('focus');
        } else {
            setReadingMode('scroll');
        }
    });

    // Visuals Drawer Smooth Scrolling
    document.querySelectorAll('.visual-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('data-target');
            const targetEl = document.getElementById(targetId);
            if (targetEl) {
                // Close drawer if on mobile or just to get out of the way
                if (window.innerWidth <= 768) {
                    closeAllSurfaces();
                }
                
                // Smooth scroll
                const headerOffset = 60;
                const elementPosition = targetEl.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.scrollY - headerOffset;
                
                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
                
                // Flash highlight
                targetEl.style.transition = 'background-color 0.5s';
                const originalBg = targetEl.style.backgroundColor;
                targetEl.style.backgroundColor = 'rgba(255, 215, 0, 0.3)';
                setTimeout(() => {
                    targetEl.style.backgroundColor = originalBg;
                    targetEl.style.transition = '';
                }, 1500);
            }
        });
    });

    // --- 10. IDLE BEHAVIOR (ALL SURFACE CONTROLS) ---
    const backToTopBtn = document.getElementById('back-to-top');
    const surfaceControls = document.querySelectorAll('.surface-control');
    let idleTimer;

    function resetIdleTimer() {
        surfaceControls.forEach(ctrl => ctrl.classList.remove('idle'));
        clearTimeout(idleTimer);
        
        idleTimer = setTimeout(() => {
            surfaceControls.forEach(ctrl => ctrl.classList.add('idle'));
        }, 5000);
    }

    let scrollTimeout;
    document.addEventListener('scroll', (e) => {
        if (!scrollTimeout) {
            scrollTimeout = requestAnimationFrame(() => {
                // Determine the scroll position regardless of which element is actually scrolling (window, document, or a specific container)
                const scrollY = window.scrollY || document.documentElement.scrollTop;
                
                if (scrollY > 300) {
                    backToTopBtn.classList.remove('hidden');
                } else {
                    backToTopBtn.classList.add('hidden');
                }
                resetIdleTimer();
                scrollTimeout = null;
            });
        }
    });

    document.addEventListener('mousemove', resetIdleTimer);
    document.addEventListener('keydown', resetIdleTimer);
    document.addEventListener('click', resetIdleTimer);

    // Initial timer start
    resetIdleTimer();

    backToTopBtn.addEventListener('click', (e) => {
        e.preventDefault();
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

    // --- 11. VISUAL LINK AUTO-COLLAPSE ---
    const visualLinks = document.querySelectorAll('.visual-link');
    visualLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            if (e.button !== 0) return;
            
            const targetId = link.getAttribute('data-target');
            if (targetId) {
                const targetEl = document.getElementById(targetId);
                if (targetEl) {
                    targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            
            // Let the smooth scroll happen, then close drawer
            setTimeout(() => {
                if (typeof window.closeAllSurfaces === 'function') {
                    window.closeAllSurfaces();
                }
            }, 250);
        });
    });

    // --- 12. CITATION HOVER CARDS ---
    const citationDataScript = document.getElementById('citation-data');
    if (citationDataScript) {
        try {
            const citations = JSON.parse(citationDataScript.textContent);
            const citationMap = {};
            citations.forEach(c => citationMap[c.id] = c);

            const hoverCard = document.createElement('div');
            hoverCard.className = 'citation-hover-card';
            hoverCard.id = 'citation-hover-card';
            document.body.appendChild(hoverCard);

            const citeLinks = document.querySelectorAll('.cite-link');
            let hoverTimeout;

            citeLinks.forEach(link => {
                link.addEventListener('mouseenter', (e) => {
                    const targetId = link.getAttribute('href').substring(1);
                    const citeData = citationMap[targetId];
                    
                    if (citeData) {
                        clearTimeout(hoverTimeout);
                        hoverTimeout = setTimeout(() => {
                            hoverCard.innerHTML = `<div class="citation-hover-text">${citeData.text}</div>`;
                            
                            // Position the card
                            hoverCard.style.display = 'block'; // Make measurable
                            const rect = link.getBoundingClientRect();
                            const cardRect = hoverCard.getBoundingClientRect();
                            
                            // Prefer above
                            let top = rect.top + window.scrollY - cardRect.height - 8;
                            // Fallback below
                            if (top < window.scrollY) {
                                top = rect.bottom + window.scrollY + 8;
                            }
                            
                            let left = rect.left + window.scrollX;
                            
                            // Prevent overflowing screen edge
                            if (left + cardRect.width > window.innerWidth - 20) {
                                left = window.innerWidth - cardRect.width - 20;
                            }
                            
                            hoverCard.style.top = `${top}px`;
                            hoverCard.style.left = `${left}px`;
                            hoverCard.classList.add('visible');
                        }, 250); // 250ms delay
                    }
                });

                link.addEventListener('mouseleave', () => {
                    clearTimeout(hoverTimeout);
                    hoverCard.classList.remove('visible');
                });
            });
        } catch (e) {
            console.error('Failed to parse citation data for hover cards', e);
        }
    }

});
