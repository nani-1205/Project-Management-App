document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded and parsed");

    // --- Edit Project Modal Logic ---
    const editModal = document.getElementById('edit-project-modal');
    const editForm = document.getElementById('edit-project-form');
    const closeModalBtn = editModal.querySelector('.close-btn');

    document.querySelectorAll('.edit-project-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const projectData = JSON.parse(event.target.dataset.projectData);
            const projectId = event.target.dataset.projectId;

            // Populate the form
            editForm.action = `/projects/edit/${projectId}`; // Set form action URL
            editForm.querySelector('#edit-project-name').value = projectData.name || '';
            editForm.querySelector('#edit-project-desc').value = projectData.description || '';
            editForm.querySelector('#edit-project-status').value = projectData.status || '';
            // Format dates correctly for input type="date" (YYYY-MM-DD)
            editForm.querySelector('#edit-project-start').value = projectData.start_date ? formatDateForInput(projectData.start_date.$date) : '';
            editForm.querySelector('#edit-project-end').value = projectData.end_date ? formatDateForInput(projectData.end_date.$date) : '';

            // Show the modal
            editModal.style.display = 'block';
        });
    });

    // Close modal functionality
    closeModalBtn.addEventListener('click', () => {
        editModal.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target == editModal) { // Click outside the modal content
            editModal.style.display = 'none';
        }
    });

    // Helper to format MongoDB ISODate ($date) for HTML date input
    function formatDateForInput(isoDateLong) {
        if (!isoDateLong) return '';
        // Convert the millisecond timestamp to a Date object
        const date = new Date(isoDateLong);
         // Get parts, ensuring leading zeros
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0'); // Month is 0-indexed
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }


    // Add similar modal logic for Edit Task, Delete Task confirmation, Log Time etc.
    // ... (Left as exercise)

}); // End DOMContentLoaded

// --- Add Helper functions outside DOMContentLoaded if needed globally ---
// Function to format duration (example)
function formatDuration(totalMinutes) {
     if (totalMinutes === null || totalMinutes < 0) {
         return "N/A";
     }
     if (totalMinutes === 0) {
         return "0m";
     }
     const hours = Math.floor(totalMinutes / 60);
     const minutes = totalMinutes % 60;
     const parts = [];
     if (hours > 0) {
         parts.push(`${hours}h`);
     }
     if (minutes > 0) {
         parts.push(`${minutes}m`);
     }
     return parts.join(" ");
 }

 // Function to format date (example)
 function formatDate(isoDateLong) {
     if (!isoDateLong) return '';
     const date = new Date(isoDateLong);
     // Simple format, adjust as needed
     return date.toLocaleDateString();
 }