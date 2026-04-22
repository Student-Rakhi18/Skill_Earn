'use strict';

// ✅ Get current user id from body
const CURRENT_USER_ID = document.body.dataset.userId;

// ── Like / Unlike post ─────────────────────────────────────────
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
         btn.style.transform = 'scale(1.2)';
         setTimeout(() => btn.style.transform = '', 200);
      } else {
         btn.classList.remove('liked');
         heart.textContent = '🤍';
      }

      if (num) num.textContent = data.count;
   })
   .catch(err => console.error('Like error:', err));
}

// ── Image Modal ─────────────────────────────────────────
function openImage(src) {
    document.getElementById("imgModal").style.display = "flex";
    document.getElementById("modalImg").src = src;
}

function closeImage() {
    document.getElementById("imgModal").style.display = "none";
}

// ── Chat Menu (GLOBAL होना जरूरी है) ─────────────────────
let selectedMsgId = null;
let isSender = false;

function openMenu(id, senderId, element) {
  selectedMsgId = id;
  isSender = (senderId == CURRENT_USER_ID);

  const menu = document.getElementById("msgMenu");
  if (!menu) return;

  const rect = element.getBoundingClientRect();
  menu.style.top = (rect.top + window.scrollY) + "px";
  menu.style.left = (rect.left + rect.width / 2) + "px";
  menu.style.transform = "translateX(-50%)";

  menu.style.display = "block";

  const delBtn = document.getElementById("delEveryoneBtn");
  if (delBtn) {
    delBtn.style.display = isSender ? "block" : "none";
  }
}

// ── Delete Message ─────────────────────────────────────
function handleDelete(type) {
  if (!selectedMsgId) return;

  let url = type === 'all'
    ? `/delete_for_everyone/${selectedMsgId}`
    : `/delete_for_me/${selectedMsgId}`;

  fetch(url, { method: "POST" })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'expired') {
        alert("⏰ You can delete for everyone only within 1 hour!");
      } else if (data.status === 'deleted') {
        location.reload();
      } else {
        alert("❌ Something went wrong");
      }
    })
    .catch(err => {
      console.error(err);
      alert("Error occurred");
    });
}

// ── DOM Loaded Stuff ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

  // Toast auto remove
  document.querySelectorAll('.toast').forEach(t => {
    setTimeout(() => {
      t.style.transition = 'opacity .4s, transform .4s';
      t.style.opacity = '0';
      t.style.transform = 'translateX(16px)';
      setTimeout(() => t.remove(), 400);
    }, 4500);
  });

  // Password toggle
  document.querySelectorAll('.pw-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.dataset.target);
      if (!input) return;

      input.type = input.type === 'password' ? 'text' : 'password';
      btn.style.opacity = input.type === 'text' ? '1' : '0.5';
    });
  });

  // Video lazy load
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

  // Close menu on outside click
  document.addEventListener("click", function(e) {
    if (!e.target.closest(".msg")) {
      const menu = document.getElementById("msgMenu");
      if (menu) menu.style.display = "none";
    }
  });

});