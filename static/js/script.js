// static/js/script.js
document.addEventListener('DOMContentLoaded', () => {

    // --- Edit Project Modal Logic ---
    const editModal = document.getElementById('edit-project-modal');
    const editForm = document.getElementById('edit-project-form');
    const closeModalBtns = document.querySelectorAll('.modal .close-btn'); // Can have multiple modals later

    // Function to open and populate the edit project modal
    function openEditProjectModal(event) {
        const button = event.target;
        const projectId = button.dataset.projectId;
        // Use try-catch for parsing potentially invalid JSON
        try {
            const projectData = JSON.parse(button.dataset.projectData);

            // Set the form action dynamically
            editForm.action = `/projects/edit/${projectId}`;

            // Populate form fields
            editForm.querySelector('#edit-project-name').value = projectData.name || '';
            editForm.querySelector('#edit-project-desc').value = projectData.description || '';
            editForm.querySelector('#edit-project-status').value = projectData.status || '';
            // Dates need careful handling because json_util outputs {"$date": ...}
            editForm.querySelector('#edit-project-start').value = projectData.start_date ? formatDateForInput(projectData.start_date) : '';
            editForm.querySelector('#edit-project-end').value = projectData.end_date ? formatDateForInput(projectData.end_date) : '';

            // Display the modal
            if(editModal) {
                editModal.style.display = 'block';
            }
        } catch (e) {
            console.error("Error parsing project data:", e);
            alert("Could not load project data for editing.");
        }
    }

    // Attach listeners to all edit project buttons
    document.querySelectorAll('.edit-project-btn').forEach(button => {
        button.addEventListener('click', openEditProjectModal);
    });

    // Function to close any modal
    function closeModal(modal) {
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Add listeners to all close buttons
    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            closeModal(btn.closest('.modal')); // Find the parent modal and close it
        });
    });

    // Close modal if clicking outside the modal content
    window.addEventListener('click', (event) => {
        if (event.target.classList.contains('modal')) { // Check if the click target is the modal background itself
            closeModal(event.target);
        }
    });

    // Helper function to format date for <input type="date">
    // Input can be a datetime object or the {"$date": milliseconds} structure from json_util
    function formatDateForInput(dateValue) {
        let date;
        if (!dateValue) return '';

        if (typeof dateValue === 'object' && dateValue !== null && '$date' in dateValue) {
             // Handle {"$date": milliseconds} format
             const timestamp = dateValue.$date;
             if (typeof timestamp === 'number') {
                 date = new Date(timestamp);
             } else { return ''; } // Invalid date format
        } else if (dateValue instanceof Date) {
            // Handle Date objects directly (less likely from json_util but good practice)
            date = dateValue;
        } else {
            // Try parsing as ISO string just in case
            try { date = new Date(dateValue); } catch(e) { return '';}
        }

        if (isNaN(date.getTime())) { // Check if date is valid
             return '';
        }

        // Format to YYYY-MM-DD
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0'); // Month is 0-indexed
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // --- Add more JS logic here ---
    // - Edit Task Modal
    // - Delete Task Confirmation (could use inline JS or a modal)
    // - Log Time Modal
    // - Optional: AJAX for dynamic task loading without page refresh

}); // End DOMContentLoaded