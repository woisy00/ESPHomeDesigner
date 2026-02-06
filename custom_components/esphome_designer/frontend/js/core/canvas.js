import { AppState } from './state.js';
import { on, EVENTS } from './events.js';
import { render, applyZoom, renderContextToolbar } from './canvas_renderer.js';
import { CanvasRulers } from './canvas_rulers.js';
import { setupInteractions, setupPanning, setupZoomControls, setupDragAndDrop, zoomIn, zoomOut, zoomReset, onMouseMove, onMouseUp } from './canvas_interactions.js';
import { setupTouchInteractions } from './canvas_touch.js';
import { clearSnapGuides, addSnapGuideVertical, addSnapGuideHorizontal, getSnapLines, applySnapToPosition } from './canvas_snap.js';

export class Canvas {
    constructor() {
        this.canvas = document.getElementById("canvas");
        this.canvasContainer = document.getElementById("canvasContainer");
        this.viewport = document.querySelector(".canvas-viewport");
        this.dragState = null;
        this.panX = 0;
        this.panY = 0;

        // Touch state for mobile devices
        this.touchState = null;    // Single-touch widget drag state
        this.pinchState = null;    // Two-finger pinch/pan state
        this.lastTapTime = 0;      // Double-tap detection

        // External drag state (from palette)
        // Fixes race condition where auto-refresh destroys drop target
        this.isExternalDragging = false;

        // Helper bindings for listeners that need removal reference
        // (Though interactions module manages them via direct reference or stored props)
        this._boundMouseMove = (ev) => onMouseMove(ev, this);
        this._boundMouseUp = (ev) => onMouseUp(ev, this);

        this.rulers = new CanvasRulers(this);

        this.init();
    }

    init() {
        // Subscribe to events
        on(EVENTS.STATE_CHANGED, () => this.render());
        on(EVENTS.PAGE_CHANGED, (e) => {
            this.render();
            // Focus the new page after render, unless suppressed
            if (!e.suppressFocus) {
                // GUARD: Skip auto-zoom during active drag operations
                // User must explicitly click on empty canvas to zoom to fit
                const isDragActive = this.dragState || this.isExternalDragging || this.touchState;

                // If it's the first time landing on this page index, zoom to fit
                // But NOT if we're mid-drag (prevents jarring zoom when dragging widgets between pages)
                if (this._lastFocusedIndex !== e.index && !isDragActive) {
                    this.focusPage(e.index, true, true);
                    this._lastFocusedIndex = e.index;
                } else if (!isDragActive) {
                    this.focusPage(e.index);
                }
                // If drag is active, skip focus entirely - maintain current view
            }
        });
        on(EVENTS.SELECTION_CHANGED, () => this.updateSelectionVisuals());
        on(EVENTS.SETTINGS_CHANGED, () => {
            this.render();
            this.applyZoom();
            this.rulers.update();
        });
        on(EVENTS.ZOOM_CHANGED, () => {
            this.applyZoom();
            this.rulers.update();
        });

        // Handle window resizing to keep canvas centered
        this._boundResize = () => {
            if (AppState.currentPageIndex !== -1) {
                // On resize, we want to maintain the fit if the user hasn't zoomed manually 
                // but for now let's just refocus with fit as a default smart behavior.
                this.focusPage(AppState.currentPageIndex, false, true);
            }
        };
        window.addEventListener("resize", this._boundResize);

        this.setupInteractions();
        this.render();
        this.applyZoom();

        // Start a 1-second interval to update time-dependent widgets (like datetime)
        if (this.updateInterval) clearInterval(this.updateInterval);
        this.updateInterval = setInterval(() => {
            // SKIP auto-render during active interaction to prevent DOM detachment
            if (this.touchState || this.pinchState || this.dragState || this.panState || this.lassoState || this.isExternalDragging) return;

            // Only re-render if there is a datetime widget on the current page to avoid unnecessary overhead
            const page = AppState.getCurrentPage();
            if (page && page.widgets.some(w => w.type === 'datetime')) {
                this.render();
            }
        }, 1000);
    }

    // --- Delegation Methods ---

    render() {
        render(this);
    }

    applyZoom() {
        applyZoom(this);
        if (this.rulers) this.rulers.update();
    }

    /**
     * Lightweight update for selection changes.
     * Updates widget `.active` classes without full DOM rebuild.
     */
    updateSelectionVisuals() {
        const selectedIds = AppState.selectedWidgetIds;
        const widgetEls = this.canvas.querySelectorAll('.widget');
        widgetEls.forEach(el => {
            const id = el.dataset.id;
            if (selectedIds.includes(id)) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        });

        // Re-render toolbar synchronously
        renderContextToolbar(this);
    }

    setupInteractions() {
        setupPanning(this);
        setupInteractions(this);
        setupZoomControls(this);
        setupDragAndDrop(this);
        setupTouchInteractions(this);
    }

    // Exposed methods for external callers (if any) or internal use
    zoomIn() { zoomIn(this); }
    zoomOut() { zoomOut(this); }
    zoomReset() { zoomReset(this); }
    zoomToFit() {
        if (AppState.currentPageIndex !== -1) {
            this.focusPage(AppState.currentPageIndex, true, true);
        }
    }
    focusPage(index, smooth = true, fitZoom = false) {
        import('./canvas_renderer.js').then(m => m.focusPage(this, index, smooth, fitZoom));
    }

    /**
     * Clean up resources when destroying the canvas.
     */
    destroy() {
        // Stop the update interval
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }

        // Remove window listeners
        if (this._boundResize) {
            window.removeEventListener("resize", this._boundResize);
        }

        // Assuming we rely on page refresh for now, but good practice to clear timers.
    }
}
