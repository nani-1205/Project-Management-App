// static/js/script.js
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM ready - Space Theme");

    // --- Helper function to format date for <input type="date"> ---
    function formatDateForInput(dateValue) {
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

    // --- Generic Modal Closing Logic ---
    function closeModal(modal) {
        if (modal) modal.style.display = 'none';
    }
    document.querySelectorAll('.modal .close-btn').forEach(btn => {
        btn.addEventListener('click', () => closeModal(btn.closest('.modal')));
    });
    window.addEventListener('click', (event) => {
        if (event.target.classList.contains('modal')) closeModal(event.target);
    });

    // --- Edit Project Modal Logic ---
    const editProjectModal = document.getElementById('edit-project-modal');
    if (editProjectModal) {
        const editProjectForm = document.getElementById('edit-project-form');
        function openEditProjectModal(event) {
            const button = event.target.closest('.edit-project-btn');
            if (!button) return;
            const projectId = button.dataset.projectId;
            try {
                const projectData = JSON.parse(button.dataset.projectData);
                editProjectForm.action = `/projects/edit/${projectId}`;
                editProjectForm.querySelector('#edit-project-name').value = projectData.name || '';
                editProjectForm.querySelector('#edit-project-desc').value = projectData.description || '';
                editProjectForm.querySelector('#edit-project-status').value = projectData.status || '';
                editProjectForm.querySelector('#edit-project-start').value = projectData.start_date ? formatDateForInput(projectData.start_date) : '';
                editProjectForm.querySelector('#edit-project-end').value = projectData.end_date ? formatDateForInput(projectData.end_date) : '';
                editProjectModal.style.display = 'block';
            } catch (e) { console.error("Error parsing project data:", e); alert("Could not load project data."); }
        }
        document.querySelector('.project-list')?.addEventListener('click', (event) => {
            if (event.target.closest('.edit-project-btn')) openEditProjectModal(event);
        });
    }

    // --- Edit Task Modal Logic ---
    const editTaskModal = document.getElementById('edit-task-modal');
    if (editTaskModal) {
        const editTaskForm = document.getElementById('edit-task-form');
        function openEditTaskModal(event) {
             const button = event.target.closest('.edit-task-btn');
             if (!button) return;
             const taskId = button.dataset.taskId;
             try {
                const taskData = JSON.parse(button.dataset.taskData);
                editTaskForm.action = `/tasks/edit/${taskId}`;
                editTaskForm.querySelector('#edit-task-name').value = taskData.name || '';
                editTaskForm.querySelector('#edit-task-desc').value = taskData.description || '';
                editTaskForm.querySelector('#edit-task-status').value = taskData.status || '';
                editTaskForm.querySelector('#edit-task-priority').value = taskData.priority || '';
                editTaskForm.querySelector('#edit-task-due').value = taskData.due_date ? formatDateForInput(taskData.due_date) : '';
                // Handle estimated_hours which might be null
                const estHours = taskData.estimated_hours;
                editTaskForm.querySelector('#edit-task-hours').value = (estHours !== null && estHours !== undefined) ? estHours : '';
                // Hidden project ID is set in template, no need to set here unless needed dynamically
                editTaskModal.style.display = 'block';
             } catch (e) { console.error("Error parsing task data:", e, button.dataset.taskData); alert("Could not load task data for editing."); }
        }
        document.querySelector('#task-table tbody')?.addEventListener('click', (event) => {
             if (event.target.closest('.edit-task-btn')) openEditTaskModal(event);
        });
    }

    // --- Log Time Modal Logic ---
    const logTimeModal = document.getElementById('log-time-modal');
    if (logTimeModal) {
        const logTimeForm = document.getElementById('log-time-form');
        const logTimeTaskNameSpan = document.getElementById('log-time-task-name');
        function openLogTimeModal(event) {
            const button = event.target.closest('.log-time-btn');
            if (!button) return;
            const taskId = button.dataset.taskId;
            const taskName = button.dataset.taskName;
            logTimeForm.action = `/tasks/log_time/${taskId}`;
            logTimeTaskNameSpan.textContent = taskName || 'Selected Task';
            logTimeForm.querySelector('#log-duration').value = '';
            logTimeForm.querySelector('#log-date').value = ''; // Default to empty (today)
            logTimeForm.querySelector('#log-notes').value = '';
            // Hidden project ID is set in template
            logTimeModal.style.display = 'block';
        }
        document.querySelector('#task-table tbody')?.addEventListener('click', (event) => {
             if (event.target.closest('.log-time-btn')) openLogTimeModal(event);
        });
    }

}); // End DOMContentLoaded

// --- Starfield Effect ---
function createStars() {
  const starfield = document.getElementById('starfield');
  if (!starfield) { return; }
  starfield.innerHTML = '';
  const starCount = 150;
  for (let i = 0; i < starCount; i++) {
    const star = document.createElement('div');
    star.classList.add('star');
    const x = Math.random() * 100;
    const y = Math.random() * 100;
    const size = Math.random() * 2 + 0.5;
    const opacity = Math.random() * 0.5 + 0.1;
    star.style.left = `${x}%`;
    star.style.top = `${y}%`;
    star.style.width = `${size}px`;
    star.style.height = `${size}px`;
    star.style.opacity = opacity;
    const delay = Math.random() * 5;
    const duration = Math.random() * 5 + 3;
    star.style.animation = `twinkle ${duration}s infinite alternate ${delay}s`;
    starfield.appendChild(star);
  }
}
createStars(); // Initialize stars on load