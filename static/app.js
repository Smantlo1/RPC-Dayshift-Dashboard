/**
 * app.js — Client-side helpers for RPC Operating Dashboard.
 *
 * Key responsibilities:
 *  1. Live clock
 *  2. Block expand/collapse with open-state tracking
 *  3. Optimistic checklist UI (visual update before server confirms)
 *  4. Badge counter update after checklist change
 *  5. Re-open blocks after HTMX status-card swap (outerHTML)
 *  6. Auto-expand current/next block when timeline loads
 *  7. Keyboard shortcut (?) → quick-add task
 */

// ── 1. Live clock ─────────────────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById('live-clock');
  if (el) {
    el.textContent = new Date().toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  }
}
updateClock();
setInterval(updateClock, 1000);

// ── 2. Open-block state tracker ───────────────────────────────────────────────
// Persists which blocks are currently expanded so we can restore after swaps.
window._openBlocks = new Set();

/**
 * Toggle a block open/closed.  Updates _openBlocks so the set stays accurate.
 * Called by inline onclick on header buttons AND programmatically on auto-expand.
 */
window.toggleBlock = function (id) {
  const body    = document.getElementById('body-'    + id);
  const chevron = document.getElementById('chevron-' + id);
  if (!body) return;

  const isOpen = !body.classList.contains('hidden');
  body.classList.toggle('hidden', isOpen);   // isOpen=true → add hidden (close)

  if (chevron) {
    chevron.style.transform = isOpen ? '' : 'rotate(180deg)';
  }

  // Keep the tracking set consistent
  if (isOpen) {
    window._openBlocks.delete(id);
  } else {
    window._openBlocks.add(id);
  }
};

/** Open a block without toggling (idempotent — safe to call repeatedly). */
function openBlock(id) {
  const body    = document.getElementById('body-'    + id);
  const chevron = document.getElementById('chevron-' + id);
  if (!body || !body.classList.contains('hidden')) return; // already open
  body.classList.remove('hidden');
  if (chevron) chevron.style.transform = 'rotate(180deg)';
  window._openBlocks.add(id);
}

// ── 3 & 4. Checklist optimistic update + badge counter ───────────────────────
/**
 * Called from onchange on checklist checkboxes.
 * Immediately updates the label styling and badge counter, then lets HTMX
 * submit the form in the background (hx-swap="none" — server just persists).
 *
 * @param {HTMLInputElement} checkbox
 * @param {Event}            event
 */
window.handleChecklistChange = function (checkbox, event) {
  event.stopPropagation();

  // ── Visual: toggle strikethrough on the adjacent label
  const label = checkbox.nextElementSibling;
  if (label && label.tagName === 'LABEL') {
    if (checkbox.checked) {
      label.classList.add('line-through', 'text-wm-gray100');
      label.classList.remove('text-wm-gray160');
    } else {
      label.classList.remove('line-through', 'text-wm-gray100');
      label.classList.add('text-wm-gray160');
    }
  }

  // ── Badge: recount all checkboxes in this block and update the badge
  const blockId = _blockIdFor(checkbox);
  if (blockId) _updateBadge(blockId);

  // ── Persist: submit via HTMX (hx-swap="none" means no DOM side-effects)
  // Use requestSubmit so HTMX's submit listener is triggered properly.
  if (checkbox.form) checkbox.form.requestSubmit();
};

/** Walk up the DOM to find the block id from data-block-id attribute. */
function _blockIdFor(el) {
  const card = el.closest('[data-block-id]');
  return card ? card.dataset.blockId : null;
}

/**
 * Recount checked checkboxes inside a block's checklist and update the badge.
 * Uses only DOM state (no server call) so it's synchronous and instant.
 */
function _updateBadge(blockId) {
  const checklist = document.getElementById('checklist-' + blockId);
  const badge     = document.getElementById('badge-'     + blockId);
  if (!checklist || !badge) return;

  const boxes = checklist.querySelectorAll('input[type="checkbox"][name="checked"]');
  const done  = Array.from(boxes).filter(cb => cb.checked).length;
  const total = boxes.length;

  badge.textContent = `${done}/${total}`;

  // Update badge colour class
  badge.className = [
    'text-xs px-2 py-0.5 rounded-full font-medium',
    done === total ? 'bg-green-100 text-green-700' :
    done > 0      ? 'bg-blue-100 text-blue-700'  :
                    'bg-gray-100 text-gray-600',
  ].join(' ');
}

// ── 5. Re-open block after status card swap ───────────────────────────────────
// When Update Status fires, hx-swap="outerHTML" replaces #block-{id}.
// htmx:afterSwap fires after the new card is in the DOM — evt.detail.target
// is the OLD card element (detached, but its dataset is still readable).
// We use its blockId to find and re-open the new card if it was open.
//
// When a tab loads (hx-swap="innerHTML" on #tab-content), the target is
// #tab-content itself.  We check whether the new content has a timeline.
document.body.addEventListener('htmx:afterSwap', (evt) => {
  const el = evt.detail.target;  // swap target — may be detached for outerHTML
  if (!el) return;

  // Case A: a single block card was replaced (status update)
  // The old card element is detached but its dataset is still accessible.
  if (el.dataset && el.dataset.blockId) {
    const id = el.dataset.blockId;
    if (window._openBlocks.has(id)) openBlock(id);
    return;
  }

  // Case B: any innerHTML swap — check if timeline-container landed inside it.
  // Works for initial timeline tab load AND for date-change navigations.
  const container = el.querySelector && el.querySelector('#timeline-container');
  if (container) _autoExpandTimeline(container);
});

// ── 6. Auto-expand current/next block on timeline load ───────────────────────
function _autoExpandTimeline(container) {
  const now  = new Date();
  const hour = now.getHours() + now.getMinutes() / 60;

  const cards = Array.from(container.querySelectorAll('[data-block-id]'));
  if (!cards.length) return;

  // Find the block whose window contains right now
  let target = cards.find(c => {
    const s = parseFloat(c.dataset.start);
    const e = parseFloat(c.dataset.end);
    return s <= hour && hour < e;
  });

  // Fall back to next upcoming block
  if (!target) {
    target = cards.find(c => parseFloat(c.dataset.start) > hour);
  }

  if (target) openBlock(target.dataset.blockId);
}

// Also run on initial DOMContentLoaded for the case where the timeline is
// server-rendered inline (not loaded via HTMX).
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('timeline-container');
  if (container) _autoExpandTimeline(container);
});

// ── 7. Keyboard shortcut: ? → focus quick-add task input ─────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === '?' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
    e.preventDefault();
    const input = document.querySelector('input[name="text"][placeholder]');
    if (input) input.focus();
  }
});

// ── 8. Nudge bar: refresh every 5 min on timeline tab only ───────────────────
setInterval(() => {
  const tab = new URL(window.location.href).searchParams.get('tab');
  if (!tab || tab === 'timeline') window.location.reload();
}, 5 * 60 * 1000);
