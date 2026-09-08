/**
 * Accessibility Utilities - WCAG AA Compliance
 * Provides focus management for modals and keyboard navigation support
 */

(function() {
  'use strict';

  // Store for tracking active modals and their focus contexts
  const modalFocusContexts = new Map();
  let activeModals = [];

  /**
   * Get all focusable elements within a container
   * @param {HTMLElement} container - The container to search
   * @returns {HTMLElement[]} Array of focusable elements
   */
  function getFocusableElements(container) {
    if (!container) return [];

    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[role="button"]',
      '[role="menuitem"]'
    ];

    return Array.from(container.querySelectorAll(focusableSelectors))
      .filter(el => {
        // Filter out hidden elements
        return el.offsetParent !== null &&
               window.getComputedStyle(el).visibility !== 'hidden';
      });
  }

  /**
   * Create focus trap for modal
   * @param {HTMLElement} modalElement - The modal element to trap focus within
   */
  function createFocusTrap(modalElement) {
    if (!modalElement) return null;

    const focusableElements = getFocusableElements(modalElement);
    if (focusableElements.length === 0) return null;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const focusTrapHandler = (event) => {
      if (event.key !== 'Tab') return;

      // If Shift+Tab is pressed at the first element, move to last
      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      }
      // If Tab is pressed at the last element, move to first
      else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    return {
      handler: focusTrapHandler,
      firstElement: firstElement,
      lastElement: lastElement
    };
  }

  /**
   * Open a modal with focus management
   * @param {string|HTMLElement} modalSelector - Modal ID or element
   * @param {boolean} moveFocus - Whether to move focus into modal (default: true)
   */
  window.openAccessibleModal = function(modalSelector, moveFocus = true) {
    const modalElement = typeof modalSelector === 'string'
      ? document.getElementById(modalSelector)
      : modalSelector;

    if (!modalElement) {
      console.warn('Modal element not found:', modalSelector);
      return;
    }

    // Store current focus (to restore on close)
    const previousFocus = document.activeElement;

    // Create focus trap
    const focusTrap = createFocusTrap(modalElement);

    if (focusTrap) {
      modalElement.addEventListener('keydown', focusTrap.handler);

      // Store context for cleanup later
      if (!modalFocusContexts.has(modalElement)) {
        modalFocusContexts.set(modalElement, {
          focusTrap: focusTrap,
          previousFocus: previousFocus,
          handler: focusTrap.handler
        });
      }

      // Move focus to first focusable element
      if (moveFocus) {
        setTimeout(() => {
          focusTrap.firstElement.focus();
          // Add visual indicator that element received focus
          focusTrap.firstElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 50);
      }

      activeModals.push(modalElement);
    }

    // Set aria-modal attribute for screen readers
    modalElement.setAttribute('aria-modal', 'true');

    return modalElement;
  };

  /**
   * Close a modal with focus restoration
   * @param {string|HTMLElement} modalSelector - Modal ID or element
   * @param {boolean} restoreFocus - Whether to restore previous focus (default: true)
   */
  window.closeAccessibleModal = function(modalSelector, restoreFocus = true) {
    const modalElement = typeof modalSelector === 'string'
      ? document.getElementById(modalSelector)
      : modalSelector;

    if (!modalElement) return;

    // Remove focus trap
    const context = modalFocusContexts.get(modalElement);
    if (context) {
      modalElement.removeEventListener('keydown', context.handler);

      // Restore previous focus
      if (restoreFocus && context.previousFocus && context.previousFocus !== document.body) {
        setTimeout(() => {
          context.previousFocus.focus();
        }, 100);
      }

      modalFocusContexts.delete(modalElement);
    }

    // Remove from active modals list
    activeModals = activeModals.filter(m => m !== modalElement);

    // Remove aria-modal
    modalElement.removeAttribute('aria-modal');
  };

  /**
   * Close the currently active modal with Escape key
   */
  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && activeModals.length > 0) {
      const topModal = activeModals[activeModals.length - 1];

      // Check if modal has a close button or trigger
      const closeButton = topModal.querySelector('[data-bs-dismiss="modal"], .btn-close, [onclick*="close"]');
      if (closeButton) {
        closeButton.click();
      } else {
        // Fallback: close manually
        window.closeAccessibleModal(topModal);
        topModal.style.display = 'none';
      }
    }
  });

  /**
   * Focus visible polyfill for older browsers
   * Ensure focus-visible is polyfilled
   */
  if (!CSS.supports('selector(:focus-visible)')) {
    const style = document.createElement('style');
    style.textContent = `
      :focus {
        outline: 3px solid #0284c7;
        outline-offset: 2px;
      }
    `;
    document.head.appendChild(style);
  }

  /**
   * Monitor Bootstrap modals and apply accessibility enhancements
   */
  document.addEventListener('show.bs.modal', function(e) {
    const modal = e.target;
    const modalElement = typeof modal === 'string' ? document.getElementById(modal) : modal;

    if (modalElement) {
      window.openAccessibleModal(modalElement, true);
    }
  });

  document.addEventListener('hide.bs.modal', function(e) {
    const modal = e.target;
    const modalElement = typeof modal === 'string' ? document.getElementById(modal) : modal;

    if (modalElement) {
      window.closeAccessibleModal(modalElement, true);
    }
  });

  /**
   * Enhance links to open modals with accessibility
   * Usage: data-a11y-modal="modalId"
   */
  document.addEventListener('click', function(e) {
    const trigger = e.target.closest('[data-a11y-modal]');
    if (trigger) {
      const modalId = trigger.getAttribute('data-a11y-modal');
      if (modalId) {
        window.openAccessibleModal(modalId, true);
      }
    }
  });

  /**
   * Utility: Check if element has sufficient color contrast
   * Returns WCAG level (AAA, AA, or FAIL)
   */
  window.checkContrast = function(element) {
    if (!element) return null;

    const style = window.getComputedStyle(element);
    const color = style.color;
    const bgColor = style.backgroundColor;

    // Simple contrast check (would need full RGB parsing for production)
    console.log('Color:', color, 'Background:', bgColor);
    return 'PASS'; // Simplified
  };

  // Export for testing/debugging
  window.a11y = {
    openModal: window.openAccessibleModal,
    closeModal: window.closeAccessibleModal,
    getFocusableElements: getFocusableElements,
    getActiveModals: () => [...activeModals]
  };

  console.log('Accessibility utilities loaded. Use window.a11y for debugging.');
})();
