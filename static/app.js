/**
 * app.js — Minimal client-side helpers for RPC Operating Dashboard.
 * Keeps this thin: server renders everything, HTMX handles dynamics.
 */

// ── Live clock ────────────────────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById('live-clock');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  });
}
updateClock();
setInterval(updateClock, 1000);

// ── Refresh nudge bar every 5 minutes ────────────────────────────────────────
// Nudges are time-sensitive — a full page refresh keeps them accurate.
setInterval(() => {
  const url = new URL(window.location.href);
  // Only auto-refresh if we're on the timeline tab (least disruptive)
  if (url.searchParams.get('tab') === 'timeline' || !url.searchParams.get('tab')) {
    window.location.reload();
  }
}, 5 * 60 * 1000);

// ── Block expand/collapse ─────────────────────────────────────────────────────
// Defined globally so inline onclick handlers work even after HTMX swaps.
window.toggleBlock = function(id) {
  const body    = document.getElementById('body-'    + id);
  const chevron = document.getElementById('chevron-' + id);
  if (!body) return;
  const isOpen  = !body.classList.contains('hidden');
  body.classList.toggle('hidden', isOpen);
  if (chevron) {
    chevron.style.transform = isOpen ? '' : 'rotate(180deg)';
  }
};

// ── HTMX: after every swap, re-run auto-expand logic ─────────────────────────
document.body.addEventListener('htmx:afterSwap', (evt) => {
  // If the timeline container was swapped in, auto-expand current block
  const container = evt.target;
  if (!container || !container.id?.includes('timeline')) return;

  const now  = new Date();
  const hour = now.getHours() + now.getMinutes() / 60;

  // We can't access Python's block data post-swap, so we use data attributes
  // The timeline template renders data-start and data-end on each card
  const cards = container.querySelectorAll('[data-start]');
  let opened = false;
  for (const card of cards) {
    const start = parseFloat(card.dataset.start);
    const end   = parseFloat(card.dataset.end);
    const id    = card.dataset.blockId;
    if (!opened && start <= hour && hour < end) {
      window.toggleBlock(id);
      opened = true;
    }
  }
  // If nothing is current, open next upcoming block
  if (!opened) {
    for (const card of cards) {
      const start = parseFloat(card.dataset.start);
      const id    = card.dataset.blockId;
      if (start > hour) {
        window.toggleBlock(id);
        break;
      }
    }
  }
});

// ── Keyboard shortcut: ? → focus quick-add task input ─────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === '?' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
    e.preventDefault();
    const input = document.querySelector('input[name="text"][placeholder]');
    if (input) input.focus();
  }
});

// ── Flash saved confirmation ──────────────────────────────────────────────────
document.body.addEventListener('htmx:afterRequest', (evt) => {
  const elt = evt.detail.elt;
  if (elt && elt.dataset.flashTarget) {
    const target = document.querySelector(elt.dataset.flashTarget);
    if (target) {
      target.textContent = '✓ Saved';
      target.className = 'text-green-600 text-xs font-medium';
      setTimeout(() => { target.textContent = ''; }, 2000);
    }
  }
});
