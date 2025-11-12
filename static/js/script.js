// Закриття flash повідомлень
document.addEventListener('DOMContentLoaded', function() {
    const closeButtons = document.querySelectorAll('.close-alert');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.style.display = 'none';
        });
    });

    // Автоматичне закриття flash повідомлень через 5 секунд
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(() => alert.remove(), 500);
        });
    }, 5000);
});

// Динамічне оновлення статистики на головній сторінці
function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            console.log('Статистика оновлена:', data);
        })
        .catch(error => console.error('Помилка:', error));
}

// Валідація форм
const forms = document.querySelectorAll('form');
forms.forEach(form => {
    form.addEventListener('submit', function(e) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.style.borderColor = '#e74c3c';
            } else {
                field.style.borderColor = '#ddd';
            }
        });

        if (!isValid) {
            e.preventDefault();
            alert('Будь ласка, заповніть всі обовʼязкові поля');
        }
    });
});

// Попередній перегляд зображення
const imageInputs = document.querySelectorAll('input[type="file"]');
imageInputs.forEach(input => {
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                console.log('Зображення завантажено');
                // Можна додати попередній перегляд
            };
            reader.readAsDataURL(file);
        }
    });
});

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Lazy loading для зображень
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });

    const lazyImages = document.querySelectorAll('img.lazy');
    lazyImages.forEach(img => imageObserver.observe(img));
}

// Копіювання посилання на подію
function copyEventLink(eventId) {
    const url = window.location.origin + '/events/' + eventId;
    navigator.clipboard.writeText(url).then(() => {
        alert('Посилання скопійовано!');
    });
}

// Підтвердження видалення
document.querySelectorAll('[data-confirm]').forEach(element => {
    element.addEventListener('click', function(e) {
        if (!confirm(this.dataset.confirm)) {
            e.preventDefault();
        }
    });
});

// Мобільне меню
const menuToggle = document.createElement('button');
menuToggle.className = 'mobile-menu-toggle';
menuToggle.innerHTML = '☰';
menuToggle.style.display = 'none';
menuToggle.style.fontSize = '1.5rem';
menuToggle.style.background = 'none';
menuToggle.style.border = 'none';
menuToggle.style.cursor = 'pointer';

if (window.innerWidth <= 768) {
    const navbar = document.querySelector('.navbar .container');
    const navMenu = document.querySelector('.nav-menu');

    if (navbar && navMenu) {
        navbar.insertBefore(menuToggle, navMenu);
        menuToggle.style.display = 'block';

        menuToggle.addEventListener('click', () => {
            navMenu.style.display = navMenu.style.display === 'flex' ? 'none' : 'flex';
        });
    }
}

// Анімація появи елементів при скролі
const animateOnScroll = () => {
    const elements = document.querySelectorAll('.event-card, .feature-card, .stat-card');

    elements.forEach(element => {
        const elementTop = element.getBoundingClientRect().top;
        const windowHeight = window.innerHeight;

        if (elementTop < windowHeight - 100) {
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }
    });
};

// Ініціалізація анімацій
document.querySelectorAll('.event-card, .feature-card, .stat-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.5s, transform 0.5s';
});

window.addEventListener('scroll', animateOnScroll);
window.addEventListener('load', animateOnScroll);

console.log('🌿 Толока - платформа завантажена успішно!');