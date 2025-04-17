// static/js/script.js
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM ready - Space Theme");

    // --- Edit Project Modal Logic (Keep from previous version if using) ---
    const editModal = document.getElementById('edit-project-modal');
    if (editModal) { // Check if modal exists before adding listeners
        const editForm = document.getElementById('edit-project-form');
        const closeModalBtns = document.querySelectorAll('.modal .close-btn');

        function openEditProjectModal(event) {
            const button = event.target.closest('.edit-project-btn'); // Use closest to handle clicks on icons inside button if any
            if (!button) return; // Exit if the click wasn't on an edit button

            const projectId = button.dataset.projectId;
            try {
                const projectData = JSON.parse(button.dataset.projectData);
                editForm.action = `/projects/edit/${projectId}`;
                editForm.querySelector('#edit-project-name').value = projectData.name || '';
                editForm.querySelector('#edit-project-desc').value = projectData.description || '';
                editForm.querySelector('#edit-project-status').value = projectData.status || '';
                editForm.querySelector('#edit-project-start').value = projectData.start_date ? formatDateForInput(projectData.start_date) : '';
                editForm.querySelector('#edit-project-end').value = projectData.end_date ? formatDateForInput(projectData.end_date) : '';
                editModal.style.display = 'block';
            } catch (e) {
                console.error("Error parsing project data:", e, button.dataset.projectData);
                alert("Could not load project data for editing.");
            }
        }

        // Use event delegation on a parent container for better performance if list changes dynamically
        const projectListContainer = document.querySelector('.project-list'); // Adjust selector if needed
        if (projectListContainer) {
             projectListContainer.addEventListener('click', (event) => {
                 if (event.target.closest('.edit-project-btn')) {
                     openEditProjectModal(event);
                 }
             });
        } else { // Fallback for static buttons if delegation target not found
             document.querySelectorAll('.edit-project-btn').forEach(button => {
                 button.addEventListener('click', openEditProjectModal);
             });
        }


        function closeModal(modal) {
            if (modal) modal.style.display = 'none';
        }

        closeModalBtns.forEach(btn => {
            btn.addEventListener('click', () => closeModal(btn.closest('.modal')));
        });

        window.addEventListener('click', (event) => {
            if (event.target.classList.contains('modal')) closeModal(event.target);
        });

        // Helper function to format date for <input type="date">
        function formatDateForInput(dateValue) {
            // (Keep the implementation from the previous version)
            let date;
            if (!dateValue) return '';
            if (typeof dateValue === 'object' && dateValue !== null && '$date' in dateValue) {
                 const timestamp = dateValue.$date;
                 if (typeof timestamp === 'number') date = new Date(timestamp);
                 else return '';
            } else if (dateValue instanceof Date) { date = dateValue; }
            else { try { date = new Date(dateValue); } catch(e) { return '';} }
            if (isNaN(date.getTime())) return '';
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
    } // End if(editModal)

    // --- Add JS for Edit Task, Delete Task, Log Time Modals/Confirmations here ---


}); // End DOMContentLoaded


// --- Starfield Effect (Add this *outside* DOMContentLoaded) ---
function createStars() {
  const starfield = document.getElementById('starfield');
  // Avoid creating stars if the element doesn't exist
  if (!starfield) {
      console.warn("Starfield element not found, skipping star creation.");
      return;
  }
  // Clear existing stars if resizing or re-calling
  starfield.innerHTML = '';

  const starCount = 150; // Increase star count slightly

  for (let i = 0; i < starCount; i++) {
    const star = document.createElement('div');
    star.classList.add('star');

    const x = Math.random() * 100;
    const y = Math.random() * 100;
    const size = Math.random() * 2 + 0.5; // Allow smaller stars
    const opacity = Math.random() * 0.5 + 0.1; // Lower max opacity

    star.style.left = `${x}%`;
    star.style.top = `${y}%`;
    star.style.width = `${size}px`;
    star.style.height = `${size}px`;
    star.style.opacity = opacity;

    // Random delay and duration for twinkle
    const delay = Math.random() * 5; // Delay up to 5s
    const duration = Math.random() * 5 + 3; // Duration 3s to 8s

    // Apply animation with random delay/duration
    star.style.animation = `twinkle ${duration}s infinite alternate ${delay}s`;

    starfield.appendChild(star);
  }
}

// Add CSS animation keyframes dynamically if not in CSS file (already in CSS)
/*
const style = document.createElement('style');
if (!document.querySelector('style#twinkle-animation')) { // Prevent adding multiple times
    style.id = 'twinkle-animation';
    style.textContent = `
      @keyframes twinkle {
        0%, 100% { opacity: var(--start-opacity, 0.2); transform: scale(0.8); }
        50% { opacity: var(--end-opacity, 0.8); transform: scale(1.1); }
      }
    `;
    document.head.appendChild(style);
}
*/

// Initialize stars on load
createStars();

// Optional: Regenerate stars on resize for better distribution, but can be costly
// let resizeTimeout;
// window.addEventListener('resize', () => {
//   clearTimeout(resizeTimeout);
//   resizeTimeout = setTimeout(createStars, 500); // Debounce resize
// });