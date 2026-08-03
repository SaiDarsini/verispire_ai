document.addEventListener('DOMContentLoaded', () => {
  redirectIfAuthed();

  spawnParticles(document.getElementById('hero-particles'), 30);

  // Navbar scroll shadow
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    navbar.style.boxShadow = window.scrollY > 20 ? '0 8px 30px rgba(0,0,0,0.35)' : 'none';
  });

  // Count-up stats when visible
  const counters = document.querySelectorAll('[data-count]');
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        countUp(entry.target, parseInt(entry.target.dataset.count, 10));
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.4 });
  counters.forEach(el => io.observe(el));

  // FAQ accordion
  document.querySelectorAll('.faq-item').forEach(item => {
    item.querySelector('.faq-q').addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));
      if (!isOpen) item.classList.add('open');
    });
  });

  // Mobile nav
  const toggle = document.getElementById('nav-toggle-btn');
  const mobileLinks = document.getElementById('mobile-nav-links');
  toggle?.addEventListener('click', () => mobileLinks.classList.toggle('show'));

  // Reveal-on-scroll for cards
  const revealTargets = document.querySelectorAll('.feature-card, .price-card, .testimonial-card, .counter-card');
  const revealIo = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('fade-in');
        revealIo.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });
  revealTargets.forEach(el => revealIo.observe(el));
});
