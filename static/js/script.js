// static/js/script.js
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM ready - Space Theme v3 - Debugging Edit/Log"); // Log script start

    // --- Helper function to format date for <input type="date"> ---
    function formatDateForInput(dateValue) {
        let date;
        if (!dateValue) return '';
        try { // Add try-catch around date parsing
            if (typeof dateValue === 'object' && dateValue !== null && '$date' in dateValue) {
                const timestamp = dateValue.$date;
                // Handle BSON v2 int64 represented as string in newer json_util
                const tsNumber = typeof timestamp === 'string' ? parseInt(timestamp, 10) : timestamp;
                if (typeof tsNumber === 'number' && !isNaN(tsNumber)) date = new Date(tsNumber);
                else return '';
            } else if (dateValue instanceof Date) { date = dateValue; }
            else { date = new Date(dateValue); } // Try parsing string/number
            if (isNaN(date.getTime())) return ''; // Check validity
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        } catch (e) {
             console.error("Error in formatDateForInput:", e, "Input:", dateValue);
             return ""; // Return empty string on error
        }
    }

    // --- Generic Modal Closing Logic ---
    function closeModal(modal) {
        if (modal && modal instanceof Element) { // Check if it's a valid element
            console.log("Closing modal:", modal.id);
            modal.style.display = 'none';
        } else {
             console.error("Attempted to close an invalid or null modal:", modal);
        }
    }
    document.querySelectorAll('.modal .close-btn').forEach(btn => {
        // Ensure button exists before adding listener
        if(btn) btn.addEventListener('click', () => closeModal(btn.closest('.modal')));
    });
    window.addEventListener('click', (event) => {
        if (event.target.classList.contains('modal')) closeModal(event.target);
    });


    // --- Edit Project Modal Logic ---
    const editProjectModal = document.getElementById('edit-project-modal');
    const editProjectForm = document.getElementById('edit-project-form');
    const projectList = document.querySelector('.project-list'); // Needed for delegation

    if (editProjectModal && editProjectForm && projectList) { // Check all elements exist
        function openEditProjectModal(event) {
            console.log("openEditProjectModal triggered");
            const button = event.target.closest('.edit-project-btn');
            if (!button) { console.log("Edit project button not found in event path"); return; }

            const projectId = button.dataset.projectId;
            const projectDataRaw = button.dataset.projectData;
            console.log("Project ID:", projectId);
            // console.log("Raw Project Data:", projectDataRaw); // Be careful logging potentially large data

            if(!projectId || !projectDataRaw) {
                console.error("Missing data attributes on project button");
                alert("Cannot edit project: Data missing.");
                return;
            }

            try {
                const projectData = JSON.parse(projectDataRaw);
                console.log("Parsed Project Data:", projectData);

                editProjectForm.action = `/projects/edit/${projectId}`; // Set form action
                console.log("Set project form action to:", editProjectForm.action);

                // Populate project form, check elements exist
                const nameInput = editProjectForm.querySelector('#edit-project-name');
                const descInput = editProjectForm.querySelector('#edit-project-desc');
                const statusSelect = editProjectForm.querySelector('#edit-project-status');
                const startInput = editProjectForm.querySelector('#edit-project-start');
                const endInput = editProjectForm.querySelector('#edit-project-end');

                if(nameInput) nameInput.value = projectData.name || ''; else console.error("#edit-project-name not found");
                if(descInput) descInput.value = projectData.description || ''; else console.error("#edit-project-desc not found");
                if(statusSelect) statusSelect.value = projectData.status || ''; else console.error("#edit-project-status not found");
                if(startInput) startInput.value = formatDateForInput(projectData.start_date); else console.error("#edit-project-start not found");
                if(endInput) endInput.value = formatDateForInput(projectData.end_date); else console.error("#edit-project-end not found");

                console.log("Populated project form fields");
                editProjectModal.style.display = 'block';
                console.log("Displayed edit project modal");

            } catch (e) {
                console.error("Error parsing project data or populating form:", e);
                console.error("Problematic raw data:", projectDataRaw); // Log raw data on parse error
                alert("Could not load project data for editing. Check console.");
            }
        }
        // Event delegation for project edit buttons
        projectList.addEventListener('click', (event) => {
             if (event.target.closest('.edit-project-btn')) {
                console.log("Edit project button clicked (delegated)");
                openEditProjectModal(event);
             }
        });
    } else {
        console.warn("Edit Project Modal or related elements not found. Edit Project JS may not work.");
        if (!editProjectModal) console.warn("- edit-project-modal missing");
        if (!editProjectForm) console.warn("- edit-project-form missing");
        if (!projectList) console.warn("- project-list missing");
    }


    // --- Edit Task Modal Logic ---
    const editTaskModal = document.getElementById('edit-task-modal');
    const editTaskForm = document.getElementById('edit-task-form');
    const taskTableBody = document.querySelector('#task-table tbody'); // Target table body

    if (editTaskModal && editTaskForm && taskTableBody) { // Check all elements exist
        function openEditTaskModal(event) {
             console.log("openEditTaskModal triggered");
             const button = event.target.closest('.edit-task-btn');
             if (!button) { console.log("Edit task button not found in event path"); return; }

             const taskId = button.dataset.taskId;
             const taskDataRaw = button.dataset.taskData;
             console.log("Attempting to edit Task ID:", taskId);
             if (!taskId || !taskDataRaw) { console.error("Missing data attributes on task edit button"); return; }

             try {
                const taskData = JSON.parse(taskDataRaw);
                console.log("Parsed Task Data:", taskData);
                editTaskForm.action = `/tasks/edit/${taskId}`;
                console.log("Set task form action to:", editTaskForm.action);

                // Check if elements exist before setting value
                const nameInput = editTaskForm.querySelector('#edit-task-name');
                const descInput = editTaskForm.querySelector('#edit-task-desc');
                const statusSelect = editTaskForm.querySelector('#edit-task-status');
                const prioritySelect = editTaskForm.querySelector('#edit-task-priority');
                const dueInput = editTaskForm.querySelector('#edit-task-due');
                const hoursInput = editTaskForm.querySelector('#edit-task-hours');
                const projectIdInput = editTaskForm.querySelector('#edit-task-project-id'); // Check hidden field too

                if(nameInput) nameInput.value = taskData.name || ''; else console.error("#edit-task-name not found");
                if(descInput) descInput.value = taskData.description || ''; else console.error("#edit-task-desc not found");
                if(statusSelect) statusSelect.value = taskData.status || ''; else console.error("#edit-task-status not found");
                if(prioritySelect) prioritySelect.value = taskData.priority || ''; else console.error("#edit-task-priority not found");
                if(dueInput) dueInput.value = formatDateForInput(taskData.due_date); else console.error("#edit-task-due not found");
                if(hoursInput) {
                    const estHours = taskData.estimated_hours;
                    hoursInput.value = (estHours !== null && estHours !== undefined) ? estHours : '';
                } else { console.error("#edit-task-hours not found"); }

                if(!projectIdInput) {
                     console.error("Hidden project ID field (#edit-task-project-id) not found in edit task modal!");
                } else if (!projectIdInput.value) { // Check if it has a value (should be set by Jinja)
                     console.warn("Hidden project ID field is empty in edit task modal! Attempting fallback.");
                     // Try to get it from task data as fallback
                     if(taskData.project_id && taskData.project_id.$oid) {
                         projectIdInput.value = taskData.project_id.$oid;
                         console.log("Set hidden project ID from task data fallback.");
                     } else {
                          console.error("Could not determine project ID for redirect!");
                          // You might need to grab it from the URL or another source if Jinja fails
                     }
                }

                console.log("Populated task form fields");
                editTaskModal.style.display = 'block';
                console.log("Displayed edit task modal");
             } catch (e) {
                 console.error("Error processing task data:", e);
                 console.error("Problematic raw data:", taskDataRaw); // Log raw data on parse error
                 alert("Could not load task data for editing. Check console.");
             }
        }
        // Event delegation for task edit buttons
        taskTableBody.addEventListener('click', (event) => {
             if (event.target.closest('.edit-task-btn')) {
                 console.log("Edit task button clicked (delegated)");
                 openEditTaskModal(event);
             }
        });
    } else {
        console.warn("Edit Task Modal or related elements not found. Edit Task JS may not work.");
        if (!editTaskModal) console.warn("- edit-task-modal missing");
        if (!editTaskForm) console.warn("- edit-task-form missing");
        if (!taskTableBody) console.warn("- task-table tbody missing");
    }


    // --- Log Time Modal Logic ---
    const logTimeModal = document.getElementById('log-time-modal');
    const logTimeForm = document.getElementById('log-time-form');
    const logTimeTaskNameSpan = document.getElementById('log-time-task-name');
    // Re-use taskTableBody selector from above

    if (logTimeModal && logTimeForm && logTimeTaskNameSpan && taskTableBody) { // Check all elements
        function openLogTimeModal(event) {
            console.log("openLogTimeModal triggered");
            const button = event.target.closest('.log-time-btn');
            if (!button) { console.log("Log time button not found in event path"); return; }

            const taskId = button.dataset.taskId;
            const taskName = button.dataset.taskName;
            console.log("Attempting to log time for Task ID:", taskId, "Name:", taskName);
            if (!taskId) { console.error("Missing task ID on log time button"); return; }

            logTimeForm.action = `/tasks/log_time/${taskId}`;
            console.log("Set log time form action to:", logTimeForm.action);

            if(logTimeTaskNameSpan) logTimeTaskNameSpan.textContent = taskName || 'Selected Task'; else console.error("#log-time-task-name span not found");

            // Reset form fields, checking elements
            const durationInput = logTimeForm.querySelector('#log-duration');
            const dateInput = logTimeForm.querySelector('#log-date');
            const notesInput = logTimeForm.querySelector('#log-notes');
            const projectIdInput = logTimeForm.querySelector('#log-time-project-id');

            if(durationInput) durationInput.value = ''; else console.error("#log-duration input not found");
            if(dateInput) dateInput.value = ''; else console.error("#log-date input not found");
            if(notesInput) notesInput.value = ''; else console.error("#log-notes textarea not found");
            if(!projectIdInput || !projectIdInput.value) {
                console.warn("Hidden project ID field is missing or empty in log time modal!");
            }

            console.log("Reset log time form fields");
            logTimeModal.style.display = 'block';
            console.log("Displayed log time modal");
        }
        // Event delegation for log time buttons
         taskTableBody.addEventListener('click', (event) => {
             if (event.target.closest('.log-time-btn')) {
                  console.log("Log time button clicked (delegated)");
                  openLogTimeModal(event);
             }
        });
    } else {
        console.warn("Log Time Modal or related elements not found. Log Time JS may not work.");
        if (!logTimeModal) console.warn("- log-time-modal missing");
        if (!logTimeForm) console.warn("- log-time-form missing");
        if (!logTimeTaskNameSpan) console.warn("- log-time-task-name missing");
        if (!taskTableBody) console.warn("- task-table tbody missing"); // Reuse check
    }

}); // End DOMContentLoaded

// --- Starfield Effect ---
function createStars() {
  const starfield = document.getElementById('starfield');
  if (!starfield) { return; }
  starfield.innerHTML = ''; // Clear existing stars
  const starCount = 150;
  for (let i = 0; i < starCount; i++) {
    const star = document.createElement('div');
    star.classList.add('star');
    const x = Math.random() * 100; const y = Math.random() * 100;
    const size = Math.random() * 2 + 0.5; const opacity = Math.random() * 0.5 + 0.1;
    star.style.left = `${x}%`; star.style.top = `${y}%`;
    star.style.width = `${size}px`; star.style.height = `${size}px`; star.style.opacity = opacity;
    const delay = Math.random() * 5; const duration = Math.random() * 5 + 3;
    star.style.animation = `twinkle ${duration}s infinite alternate ${delay}s`;
    starfield.appendChild(star);
  }
}
// Add CSS for twinkle animation if not already in style.css
if (!document.styleSheets[0].cssRules || ![...document.styleSheets[0].cssRules].some(rule => rule.name === 'twinkle')) {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes twinkle {
        0%, 100% { opacity: var(--start-opacity, 0.2); transform: scale(0.8); }
        50% { opacity: var(--end-opacity, 0.8); transform: scale(1.1); }
      }
    `;
    document.head.appendChild(style);
}
createStars(); // Initialize stars on load