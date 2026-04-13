/* SkillEarn – main.js */
'use strict';

// ── Toast auto-dismiss ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.toast').forEach(t => {
    setTimeout(() => {
      t.style.transition = 'opacity .4s, transform .4s';
      t.style.opacity = '0';
      t.style.transform = 'translateX(16px)';
      setTimeout(() => t.remove(), 400);
    }, 4500);
  });
});

// ── Password toggle ───────────────────────────────────────────────────────────
document.querySelectorAll('.pw-toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = document.getElementById(btn.dataset.target);
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
    btn.style.opacity = input.type === 'text' ? '1' : '0.5';
  });
});

// ── Like / Unlike post ────────────────────────────────────────────────────────
function likePost(postId, btn) {
  fetch(`/like/${postId}`, {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
    .then(r => r.json())
    .then(data => {
      const heart = btn.querySelector('.like-heart');
      const num   = btn.querySelector('.like-num');
      if (data.liked) {
        btn.classList.add('liked');
        heart.textContent = '❤️';
        // Pulse animation
        btn.style.transform = 'scale(1.2)';
        setTimeout(() => btn.style.transform = '', 200);
      } else {
        btn.classList.remove('liked');
        heart.textContent = '🤍';
      }
      if (num) num.textContent = data.count;
    })
    .catch(() => {});
}

// ── Video lazy-load via IntersectionObserver ──────────────────────────────────
const videoObs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      const v = e.target;
      v.setAttribute('preload', 'metadata');
      videoObs.unobserve(v);
    }
  });
}, { rootMargin: '200px' });

document.querySelectorAll('video[preload="none"]').forEach(v => videoObs.observe(v));

function openImage(src) {
    document.getElementById("imgModal").style.display = "flex";
    document.getElementById("modalImg").src = src;
}

function closeImage() {
    document.getElementById("imgModal").style.display = "none";
}