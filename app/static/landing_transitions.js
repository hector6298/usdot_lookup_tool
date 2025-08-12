// Smooth scrolling function for feature cards
function scrollToSection(sectionId) {
    const element = document.getElementById(sectionId);
    if (element) {
        element.scrollIntoView({ 
            behavior: 'smooth',
            block: 'center'
        });
    }
}

// Intersection Observer for animating how-it-works cards
const observerOptions = {
    threshold: 0.2,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, observerOptions);

// Observe all how-it-works cards
document.addEventListener('DOMContentLoaded', () => {
    const howItWorksCards = document.querySelectorAll('.how-it-works-card');
    howItWorksCards.forEach(card => {
        observer.observe(card);
    });
});

// Prevent default anchor behavior since we're using custom scrolling
document.querySelectorAll('.feature').forEach(feature => {
    feature.addEventListener('click', (e) => {
        e.preventDefault();
        const href = feature.getAttribute('href');
        if (href && href.startsWith('#')) {
            scrollToSection(href.substring(1));
        }
    });
});